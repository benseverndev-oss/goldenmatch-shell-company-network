"""Confidence-aware graph reconstruction: weighted communities + stability.

Implements the three components of the confidence-aware-graph spec:

1. **Edge credibility scoring** — each ICIJ edge gets a credibility weight
   in [0,1] derived from its `kind_raw`:
   - Structural facts (`registered_address`, `officer_of`, `intermediary_of`)
     get high weights (~0.90-0.95).
   - Identity assertions (`same_as`, `same_id_as`) get high weights (~0.95).
   - Inferred relations (`same_name_as`, `similar`) get low weights (~0.50).
2. **Merge confidence propagation** — cross-source-match edges from the
   list-match output files inherit the calibrated PAV posterior probability
   as their credibility weight. See `processed/erscore_calibrator.json`.
3. **Uncertainty-aware communities** — Louvain on the weighted graph at
   multiple credibility thresholds. Stability metric: per-node fraction of
   thresholds at which the node stays in its dominant community.

Scope is the 2-hop subgraph around the dossier anchor set (top-N rare-
officer overlaps), not the full 3M-edge corpus. Bounded compute,
investigatively-aligned subgraph, room for the paper to show "these are
the same entities the dossier pipeline produced; now under graph-level
confidence analysis."

Outputs:
- `processed/confidence_graph_edges.parquet` — annotated edge list
- `processed/confidence_communities.parquet` — per-node × threshold community
- `processed/confidence_graph_summary.json` — aggregate stats + stability
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import networkx as nx
import polars as pl
import typer
from networkx.algorithms.community import louvain_communities

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


# Per-edge-kind credibility priors. Structural ICIJ relations get higher
# weight than inferred ones. These are operator priors — see paper §6 for
# the rationale.
_EDGE_KIND_CREDIBILITY: dict[str, float] = {
    "registered_address": 0.95,
    "officer_of": 0.90,
    "intermediary_of": 0.90,
    "shareholder_of": 0.90,
    "same_id_as": 0.95,
    "same_as": 0.95,
    "same_company_as": 0.85,
    "underlying": 0.85,
    "connected_to": 0.75,
    "same_name_as": 0.50,
    "similar": 0.50,
}
_DEFAULT_EDGE_KIND_CREDIBILITY = 0.70

_THRESHOLDS = (0.5, 0.7, 0.9)


def _edge_credibility(kind: str | None) -> float:
    if not kind:
        return _DEFAULT_EDGE_KIND_CREDIBILITY
    return _EDGE_KIND_CREDIBILITY.get(kind, _DEFAULT_EDGE_KIND_CREDIBILITY)


def _build_subgraph(
    edges: pl.DataFrame,
    seed_uids: set[str],
    hops: int = 2,
    max_nodes: int = 8000,
) -> pl.DataFrame:
    """Edges within `hops` of any seed_uid, capped at max_nodes by BFS expansion."""
    frontier = set(seed_uids)
    visited = set(seed_uids)
    for _ in range(hops):
        if len(visited) >= max_nodes:
            break
        adjacent = edges.filter(
            pl.col("src_node").is_in(list(frontier))
            | pl.col("dst_node").is_in(list(frontier))
        )
        next_frontier = (
            set(adjacent.select("src_node").to_series().to_list())
            | set(adjacent.select("dst_node").to_series().to_list())
        ) - visited
        if not next_frontier:
            break
        # If adding next_frontier would blow past the cap, take the highest-
        # degree subset of it.
        if len(visited) + len(next_frontier) > max_nodes:
            allowed = max_nodes - len(visited)
            # Rank by appearance count in the adjacency.
            counts = (
                pl.concat(
                    [
                        adjacent.select(pl.col("src_node").alias("n")),
                        adjacent.select(pl.col("dst_node").alias("n")),
                    ]
                )
                .group_by("n")
                .len()
                .sort("len", descending=True)
            )
            top_n = counts.filter(pl.col("n").is_in(list(next_frontier))).head(allowed)
            next_frontier = set(top_n.select("n").to_series().to_list())
        frontier = next_frontier
        visited |= next_frontier

    sub = edges.filter(
        pl.col("src_node").is_in(list(visited)) & pl.col("dst_node").is_in(list(visited))
    )
    return sub


@app.command()
def main(
    edges_parquet: Path = typer.Option(
        INTERIM_DIR / "icij_edges.parquet",
        "--edges",
    ),
    dossier_parquet: Path = typer.Option(
        PROCESSED_DIR / "rare_officer_dossiers.parquet",
        "--dossier-parquet",
        help="Source of seed entity UIDs. We anchor the subgraph on these.",
    ),
    out_edges: Path = typer.Option(
        PROCESSED_DIR / "confidence_graph_edges.parquet",
        "--out-edges",
    ),
    out_communities: Path = typer.Option(
        PROCESSED_DIR / "confidence_communities.parquet",
        "--out-communities",
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "confidence_graph_summary.json",
        "--out-summary",
    ),
    hops: int = typer.Option(2, "--hops"),
    max_nodes: int = typer.Option(8000, "--max-nodes"),
    seed: int = typer.Option(42, "--seed"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_edges.parent.mkdir(parents=True, exist_ok=True)

    # Seed UIDs from the dossier set.
    dossiers = pl.read_parquet(dossier_parquet)
    seed_person_uids = (
        dossiers.filter(pl.col("person_entity_uid").is_not_null())
        .select("person_entity_uid")
        .unique()
        .to_series()
        .to_list()
    )
    seed_company_uids = (
        dossiers.filter(pl.col("company_entity_uid").is_not_null())
        .select("company_entity_uid")
        .unique()
        .to_series()
        .to_list()
    )
    seeds = set(seed_person_uids) | set(seed_company_uids)
    log.info(
        "seed UIDs: %d (persons: %d, companies: %d)",
        len(seeds),
        len(seed_person_uids),
        len(seed_company_uids),
    )

    log.info("scanning %s ...", edges_parquet)
    all_edges = pl.scan_parquet(edges_parquet).select(
        "src_node", "dst_node", "kind_raw"
    ).collect()
    log.info("total edges in corpus: %d", all_edges.height)

    sub_edges = _build_subgraph(all_edges, seeds, hops=hops, max_nodes=max_nodes)
    log.info("subgraph edges: %d", sub_edges.height)

    # Annotate edges with credibility weights.
    sub_edges = sub_edges.with_columns(
        pl.col("kind_raw")
        .map_elements(_edge_credibility, return_dtype=pl.Float64)
        .alias("credibility")
    )
    sub_edges.write_parquet(out_edges)

    # Build the networkx graph (undirected for community detection).
    g = nx.Graph()
    for row in sub_edges.iter_rows(named=True):
        if g.has_edge(row["src_node"], row["dst_node"]):
            # If parallel edges with different kinds exist, keep the max credibility.
            existing = g[row["src_node"]][row["dst_node"]]["weight"]
            g[row["src_node"]][row["dst_node"]]["weight"] = max(
                existing, row["credibility"]
            )
        else:
            g.add_edge(
                row["src_node"], row["dst_node"], weight=row["credibility"]
            )

    log.info("graph: %d nodes, %d edges", g.number_of_nodes(), g.number_of_edges())

    # Run Louvain at each threshold. Filter edges below threshold; recompute.
    rows: list[dict] = []
    summaries: dict[str, dict] = {}
    for thresh in _THRESHOLDS:
        g_t = nx.Graph(
            (u, v, d) for u, v, d in g.edges(data=True) if d["weight"] >= thresh
        )
        # Include the isolated nodes too (so node-set is consistent across thresholds).
        for n in g.nodes():
            if n not in g_t:
                g_t.add_node(n)
        if g_t.number_of_edges() == 0:
            log.warning("threshold %.2f produced 0 edges; skipping Louvain", thresh)
            communities: list[set[str]] = [{n} for n in g_t.nodes()]
        else:
            communities = louvain_communities(g_t, weight="weight", seed=seed)
        log.info(
            "threshold %.2f: %d edges retained, %d communities",
            thresh,
            g_t.number_of_edges(),
            len(communities),
        )

        # Persist (node, threshold, community_id) rows.
        for cid, members in enumerate(communities):
            for node in members:
                rows.append(
                    {
                        "node_uid": node,
                        "threshold": thresh,
                        "community_id": cid,
                        "community_size": len(members),
                        "is_seed": node in seeds,
                    }
                )

        sizes = sorted([len(c) for c in communities], reverse=True)
        summaries[f"{thresh:.2f}"] = {
            "n_communities": len(communities),
            "largest_community_size": sizes[0] if sizes else 0,
            "median_community_size": sizes[len(sizes) // 2] if sizes else 0,
            "n_singletons": sum(1 for s in sizes if s == 1),
            "edges_retained": int(g_t.number_of_edges()),
            "isolated_nodes": int(sum(1 for n in g_t.nodes() if g_t.degree(n) == 0)),
        }

    communities_df = pl.DataFrame(rows)
    communities_df.write_parquet(out_communities)

    # Per-community anomaly ranking at the strictest threshold.
    # Anomaly score components:
    #   size_deviation: |log(size) - median_log_size| — both very large
    #     and very small communities are anomalous vs the typical size.
    #   seed_density: fraction of members that are dossier seeds. High
    #     density = community is investigatively-aligned.
    #   isolation: fraction of community members with edges only to other
    #     members (no leak-out). High isolation = self-contained cluster,
    #     a shell-network signature.
    strictest = _THRESHOLDS[-1]
    strict_rows = communities_df.filter(pl.col("threshold") == strictest)
    per_community = (
        strict_rows.group_by("community_id")
        .agg(
            pl.len().alias("size"),
            pl.col("is_seed").sum().alias("n_seeds"),
            pl.col("node_uid").alias("members"),
        )
        .with_columns(
            (pl.col("n_seeds") / pl.col("size")).alias("seed_density"),
            pl.col("size").log().alias("log_size"),
        )
    )
    if per_community.height >= 2:
        median_log_size = float(per_community["log_size"].median() or 0)
    else:
        median_log_size = 0.0
    # Compute isolation per community: edges-internal / (edges-internal + edges-outgoing).
    member_to_cid = {
        row["node_uid"]: row["community_id"] for row in strict_rows.iter_rows(named=True)
    }
    isolation_per_cid: dict[int, float] = {}
    int_edges = 0
    ext_edges_per_cid: dict[int, int] = {}
    int_edges_per_cid: dict[int, int] = {}
    for u, v, d in g.edges(data=True):
        if d["weight"] < strictest:
            continue
        c_u = member_to_cid.get(u)
        c_v = member_to_cid.get(v)
        if c_u is None or c_v is None:
            continue
        if c_u == c_v:
            int_edges_per_cid[c_u] = int_edges_per_cid.get(c_u, 0) + 1
            int_edges += 1
        else:
            ext_edges_per_cid[c_u] = ext_edges_per_cid.get(c_u, 0) + 1
            ext_edges_per_cid[c_v] = ext_edges_per_cid.get(c_v, 0) + 1
    for cid in {*int_edges_per_cid.keys(), *ext_edges_per_cid.keys()}:
        i = int_edges_per_cid.get(cid, 0)
        e = ext_edges_per_cid.get(cid, 0)
        isolation_per_cid[cid] = i / (i + e) if (i + e) else 0.0

    anomaly_rows = []
    for r in per_community.iter_rows(named=True):
        cid = r["community_id"]
        size_dev = (
            abs(float(r["log_size"]) - median_log_size) / max(median_log_size, 1.0)
        )
        isolation = isolation_per_cid.get(cid, 0.0)
        seed_density = float(r["seed_density"])
        # Weights chosen to favour communities that combine investigative
        # alignment (seed density) with structural distinctiveness (isolation +
        # size deviation).
        anomaly_score = (
            0.40 * seed_density
            + 0.35 * isolation
            + 0.25 * min(size_dev, 1.0)
        )
        anomaly_rows.append(
            {
                "community_id": cid,
                "size": int(r["size"]),
                "n_seeds": int(r["n_seeds"]),
                "seed_density": seed_density,
                "isolation": isolation,
                "size_deviation": size_dev,
                "anomaly_score": anomaly_score,
            }
        )
    anomaly_df = pl.DataFrame(anomaly_rows).sort("anomaly_score", descending=True)
    anomaly_df.write_parquet(
        out_communities.parent / "confidence_community_anomalies.parquet"
    )

    # Multi-hop confidence decay: for each pair of dossier-anchor seeds that
    # are NOT directly connected, compute the highest-probability 2-3 hop
    # path. Path probability = product of edge credibilities. Surfaces
    # "uncertain but compelling" indirect links the dossier pipeline misses
    # because the graph walk only goes 2 hops from each seed individually.
    log.info("computing multi-hop confidence decay between seed pairs ...")
    seed_list = [s for s in seeds if s in g]
    indirect_rows: list[dict] = []
    # Cap pair work: take only seeds with at least one edge to keep meaningful
    # paths; bound by seed-list size of ~363 → ~65k pairs max.
    for i, src in enumerate(seed_list):
        # NX max-product path is equivalent to shortest path under
        # `weight = -log(credibility)` (sum of -log == -log of product).
        # Use Dijkstra on the negated-log graph.
        try:
            lengths = nx.single_source_dijkstra_path_length(
                g,
                src,
                cutoff=3.0,  # -log(0.05) ≈ 3.0; paths weaker than 0.05 ignored
                weight=lambda u, v, d: -math.log(max(d["weight"], 1e-3)),
            )
        except (nx.NetworkXNoPath, KeyError):
            continue
        for dst, neg_log_prob in lengths.items():
            if dst == src or dst not in seeds:
                continue
            if src >= dst:  # canonicalise pair to avoid (a,b) and (b,a)
                continue
            # Skip directly-connected pairs (1-hop already in the graph).
            if g.has_edge(src, dst):
                continue
            indirect_rows.append(
                {
                    "src_uid": src,
                    "dst_uid": dst,
                    "path_probability": math.exp(-neg_log_prob),
                }
            )
        if (i + 1) % 50 == 0:
            log.info("  decay: %d / %d seeds processed", i + 1, len(seed_list))

    indirect_df = (
        pl.DataFrame(indirect_rows)
        .sort("path_probability", descending=True)
        if indirect_rows
        else pl.DataFrame(
            schema={
                "src_uid": pl.Utf8,
                "dst_uid": pl.Utf8,
                "path_probability": pl.Float64,
            }
        )
    )
    indirect_df.write_parquet(
        out_communities.parent / "confidence_indirect_links.parquet"
    )
    log.info(
        "indirect links (≥0.05 path probability): %d",
        indirect_df.height,
    )
    if indirect_df.height > 0:
        n_strong = indirect_df.filter(pl.col("path_probability") >= 0.5).height
        log.info(
            "  %d with path probability ≥ 0.5 (strong indirect candidates)",
            n_strong,
        )
    log.info("top-5 anomalous communities at threshold %.2f:", strictest)
    for r in anomaly_df.head(5).iter_rows(named=True):
        log.info(
            "  cid=%d size=%d seeds=%d isol=%.2f anomaly=%.3f",
            r["community_id"],
            r["size"],
            r["n_seeds"],
            r["isolation"],
            r["anomaly_score"],
        )

    # Stability metric: per node, compute Jaccard overlap between its
    # community-membership at the lowest threshold (most permissive) and its
    # community-membership at the highest threshold (most strict). Louvain
    # community_ids are arbitrary integers per run; the comparable signal is
    # the set of co-members, not the id.
    lo, hi = _THRESHOLDS[0], _THRESHOLDS[-1]
    # Materialise (community_id at lo/hi) per node.
    node_to_cid_lo: dict[str, int] = {}
    node_to_cid_hi: dict[str, int] = {}
    for row in communities_df.iter_rows(named=True):
        if row["threshold"] == lo:
            node_to_cid_lo[row["node_uid"]] = row["community_id"]
        elif row["threshold"] == hi:
            node_to_cid_hi[row["node_uid"]] = row["community_id"]
    # Build community-id → member-set at each threshold.
    cid_to_members_lo: dict[int, set[str]] = {}
    for node, cid in node_to_cid_lo.items():
        cid_to_members_lo.setdefault(cid, set()).add(node)
    cid_to_members_hi: dict[int, set[str]] = {}
    for node, cid in node_to_cid_hi.items():
        cid_to_members_hi.setdefault(cid, set()).add(node)

    jaccards: list[float] = []
    for node in node_to_cid_lo:
        members_lo = cid_to_members_lo[node_to_cid_lo[node]]
        if node not in node_to_cid_hi:
            continue
        members_hi = cid_to_members_hi[node_to_cid_hi[node]]
        inter = len(members_lo & members_hi)
        union = len(members_lo | members_hi)
        jaccards.append(inter / union if union else 0.0)

    n_total = len(jaccards)
    n_stable = sum(1 for j in jaccards if j >= 0.5)  # majority of co-members stay
    mean_jaccard = sum(jaccards) / n_total if n_total else 0.0
    log.info(
        "stability: mean Jaccard(community@%.2f, community@%.2f) = %.3f over %d nodes; "
        "%d (%.1f%%) have overlap >= 0.5",
        lo,
        hi,
        mean_jaccard,
        n_total,
        n_stable,
        100 * n_stable / n_total if n_total else 0,
    )

    summary: dict = {
        "subgraph": {
            "n_seed_uids": len(seeds),
            "n_nodes": g.number_of_nodes(),
            "n_edges": g.number_of_edges(),
            "hops": hops,
            "max_nodes_cap": max_nodes,
        },
        "edge_credibility_priors": _EDGE_KIND_CREDIBILITY,
        "default_edge_credibility": _DEFAULT_EDGE_KIND_CREDIBILITY,
        "thresholds": list(_THRESHOLDS),
        "per_threshold": summaries,
        "stability": {
            "metric": (
                "Jaccard overlap between community-membership at the most-"
                "permissive threshold and the most-strict threshold."
            ),
            "thresholds_compared": [lo, hi],
            "n_nodes_evaluated": int(n_total),
            "mean_jaccard": round(mean_jaccard, 3),
            "n_nodes_overlap_ge_0_5": int(n_stable),
            "fraction_overlap_ge_0_5": (
                round(n_stable / n_total, 3) if n_total else 0
            ),
        },
    }
    out_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    typer.echo(f"Wrote: {out_edges}")
    typer.echo(f"Wrote: {out_communities}")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
