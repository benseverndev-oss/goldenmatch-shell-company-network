"""Latent-cluster mining: anomalous communities on the full ICIJ corpus.

Distinct from `build_confidence_graph.py` (which anchors a subgraph on the
dossier seed set). This script mines the **full ICIJ relationship graph**
with no seed bias — the system's first lead-generation output that
doesn't require a journalist to know where to look.

Pipeline:

1. Load all 3.3M edges from `interim/icij_edges.parquet`.
2. Filter to **high-credibility structural edges** (kind ∈ {officer_of,
   registered_address, intermediary_of, shareholder_of, same_id_as,
   same_as, same_company_as, underlying}). Drop `same_name_as` /
   `similar` / low-credibility kinds to bound noise.
3. Filter to nodes with degree ≥ `--min-degree` (default 3) to bound
   graph size.
4. Run Louvain on the resulting graph.
5. Annotate every community with:
   - **size**
   - **n_jurisdictions** spanned by member ICIJ entities
   - **n_sanctioned** members appearing in `sanctions_overlay.parquet`
     (lookup via icij_entities → normalized_name → overlay alias set)
   - **intermediary_density** — fraction of edges that are
     `intermediary_of` (high density = the "shared corporate secretary"
     pattern)
   - **address_density** — fraction of edges that are
     `registered_address` (high = shell-cluster at a shared address)
6. Anomaly score = weighted combination favouring multi-jurisdiction
   sanctions-adjacent intermediary-dense communities.
7. Emit `processed/latent_clusters.parquet` (one row per community in
   top-200) + JSON summary.

The output isn't "seeds we knew about." It's "communities the data
itself surfaces as structurally anomalous." The journalist's job is
to look at the top-K and decide which deserve investigation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import networkx as nx
import polars as pl
import typer
from networkx.algorithms.community import louvain_communities

from shellnet.normalize import normalize_company_name
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


# Same credibility priors as build_confidence_graph; kept inline rather than
# imported because importing across script modules creates a tighter coupling
# than this pipeline wants. If the priors change there, change them here too.
_HIGH_CREDIBILITY_KINDS = frozenset(
    {
        "registered_address",
        "officer_of",
        "intermediary_of",
        "shareholder_of",
        "same_id_as",
        "same_as",
        "same_company_as",
        "underlying",
    }
)


def _build_filtered_graph(
    edges_parquet: Path, min_degree: int
) -> tuple[nx.Graph, pl.DataFrame]:
    """Load, filter, build a degree-thresholded undirected graph.

    Returns the graph plus the filtered edge DataFrame for downstream
    annotation (we want both the structural object and the columns).
    """
    edges = (
        pl.scan_parquet(edges_parquet)
        .filter(pl.col("kind_raw").is_in(list(_HIGH_CREDIBILITY_KINDS)))
        .select("src_node", "dst_node", "kind_raw")
        .collect()
    )
    log.info("high-credibility edges loaded: %d", edges.height)

    # Degree filter — drop nodes with very few connections; reduces noise
    # and makes Louvain tractable on the corpus scale.
    degrees: dict[str, int] = {}
    for r in edges.iter_rows(named=True):
        degrees[r["src_node"]] = degrees.get(r["src_node"], 0) + 1
        degrees[r["dst_node"]] = degrees.get(r["dst_node"], 0) + 1
    keep = {n for n, d in degrees.items() if d >= min_degree}
    log.info(
        "kept %d / %d nodes at degree >= %d", len(keep), len(degrees), min_degree
    )

    edges = edges.filter(
        pl.col("src_node").is_in(list(keep)) & pl.col("dst_node").is_in(list(keep))
    )
    log.info("edges after degree filter: %d", edges.height)

    g = nx.Graph()
    for r in edges.iter_rows(named=True):
        g.add_edge(r["src_node"], r["dst_node"], kind=r["kind_raw"])
    log.info("graph built: %d nodes, %d edges", g.number_of_nodes(), g.number_of_edges())
    return g, edges


def _annotate_communities(
    communities: list[set[str]],
    edges_df: pl.DataFrame,
    icij_entities: pl.DataFrame,
    sanctions_aliases: set[str],
) -> list[dict]:
    """Per-community: size, jurisdiction span, sanctions adjacency, edge mix."""
    # Build a node→community map for fast edge-kind aggregation.
    node_to_cid: dict[str, int] = {}
    for cid, members in enumerate(communities):
        for n in members:
            node_to_cid[n] = cid

    # Per-community edge-kind histograms.
    int_edges_by_cid: dict[int, dict[str, int]] = {}
    for r in edges_df.iter_rows(named=True):
        c_src = node_to_cid.get(r["src_node"])
        c_dst = node_to_cid.get(r["dst_node"])
        if c_src is None or c_dst is None or c_src != c_dst:
            continue
        kind_hist = int_edges_by_cid.setdefault(c_src, {})
        kind_hist[r["kind_raw"]] = kind_hist.get(r["kind_raw"], 0) + 1

    # Entity lookup keyed by entity_uid (which equals src/dst_node).
    # icij_entities.source_id is the bare numeric; entity_uid format is icij:<source_id>.
    ent = icij_entities.with_columns(
        (pl.lit("icij:") + pl.col("source_id")).alias("entity_uid")
    ).select(
        "entity_uid",
        pl.col("jurisdiction").alias("juris"),
        pl.col("normalized_name").alias("nname"),
    )
    ent_dict: dict[str, tuple[str | None, str | None]] = {
        r["entity_uid"]: (r["juris"], r["nname"]) for r in ent.iter_rows(named=True)
    }

    rows: list[dict] = []
    for cid, members in enumerate(communities):
        size = len(members)
        if size < 3:
            continue  # 2-node communities are degenerate
        jurisdictions: set[str] = set()
        n_sanctioned = 0
        for n in members:
            info = ent_dict.get(n)
            if info is None:
                continue
            juris, nname = info
            if juris:
                jurisdictions.add(juris)
            if nname and nname in sanctions_aliases:
                n_sanctioned += 1

        kind_hist = int_edges_by_cid.get(cid, {})
        n_int = sum(kind_hist.values()) or 1
        addr_frac = kind_hist.get("registered_address", 0) / n_int
        int_frac = kind_hist.get("intermediary_of", 0) / n_int
        officer_frac = kind_hist.get("officer_of", 0) / n_int

        # Bridge density via jurisdiction span — communities spanning ≥3
        # jurisdictions are the cross-border ones that are hardest to assemble
        # manually.
        juris_span = len(jurisdictions)

        # Anomaly: prioritize moderate size + multi-jurisdiction + sanctions-
        # adjacent + intermediary-dense (the shared-secretary pattern).
        # Size term peaks at ~50 members — both tiny clusters and giant hubs
        # are deprioritised.
        size_term = min(size / 50, 1.0) if size <= 50 else max(0.0, 1.0 - (size - 50) / 500)
        anomaly = (
            0.30 * min(juris_span / 5, 1.0)
            + 0.25 * (n_sanctioned / size if size else 0)
            + 0.20 * size_term
            + 0.15 * int_frac
            + 0.10 * addr_frac
        )

        rows.append(
            {
                "community_id": cid,
                "size": size,
                "n_jurisdictions": juris_span,
                "jurisdictions": ";".join(sorted(jurisdictions)) or None,
                "n_sanctioned": n_sanctioned,
                "address_density": round(addr_frac, 3),
                "intermediary_density": round(int_frac, 3),
                "officer_density": round(officer_frac, 3),
                "anomaly_score": round(anomaly, 4),
            }
        )
    return rows


@app.command()
def main(
    edges_parquet: Path = typer.Option(
        INTERIM_DIR / "icij_edges.parquet",
        "--edges",
    ),
    entities_parquet: Path = typer.Option(
        INTERIM_DIR / "icij_entities.parquet",
        "--entities",
    ),
    sanctions_overlay: Path = typer.Option(
        PROCESSED_DIR / "sanctions_overlay.parquet",
        "--sanctions-overlay",
    ),
    out_parquet: Path = typer.Option(
        PROCESSED_DIR / "latent_clusters.parquet",
        "--out-parquet",
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "latent_clusters_summary.json",
        "--out-summary",
    ),
    min_degree: int = typer.Option(3, "--min-degree"),
    top_n: int = typer.Option(200, "--top-n"),
    seed: int = typer.Option(42, "--seed"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_parquet.parent.mkdir(parents=True, exist_ok=True)

    g, edges_df = _build_filtered_graph(edges_parquet, min_degree=min_degree)

    log.info("running Louvain on full filtered graph ...")
    communities = louvain_communities(g, seed=seed)
    log.info("found %d communities", len(communities))

    # Load sanctions overlay alias set for adjacency lookup.
    overlay = pl.read_parquet(sanctions_overlay)
    aliases: set[str] = set()
    for r in overlay.iter_rows(named=True):
        cap = r.get("caption")
        if cap:
            aliases.add(normalize_company_name(cap))
        names = (r.get("names") or "").split(";")
        for n in names:
            n = n.strip()
            if n:
                aliases.add(normalize_company_name(n))
    aliases.discard("")
    log.info("sanctions alias set: %d", len(aliases))

    # Load icij_entities for jurisdiction + name lookup.
    icij_entities = pl.read_parquet(entities_parquet).select(
        "source_id", "jurisdiction", "normalized_name"
    )

    rows = _annotate_communities(communities, edges_df, icij_entities, aliases)
    df = pl.DataFrame(rows).sort("anomaly_score", descending=True).head(top_n)
    df.write_parquet(out_parquet)
    log.info("wrote top-%d anomalous communities (of %d eligible)", df.height, len(rows))

    summary = {
        "total_communities": len(communities),
        "annotated_communities": len(rows),  # post-size-filter
        "top_n_written": int(df.height),
        "graph": {
            "nodes": g.number_of_nodes(),
            "edges": g.number_of_edges(),
            "min_degree": min_degree,
            "high_credibility_kinds": sorted(_HIGH_CREDIBILITY_KINDS),
        },
        "anomaly_score_weights": {
            "jurisdiction_span": 0.30,
            "sanctions_density": 0.25,
            "size_sweet_spot": 0.20,
            "intermediary_density": 0.15,
            "address_density": 0.10,
        },
        "top_5": df.head(5).to_dicts(),
        "anomaly_score_distribution": {
            "min": float(df["anomaly_score"].min() or 0),
            "median": float(df["anomaly_score"].median() or 0),
            "max": float(df["anomaly_score"].max() or 0),
        },
    }
    out_summary.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    typer.echo(f"Wrote: {out_parquet}")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
