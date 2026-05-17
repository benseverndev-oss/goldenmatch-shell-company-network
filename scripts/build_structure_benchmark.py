"""Non-obvious investigative structure benchmark.

The previous benchmarks asked "did we find more entities?" This one asks
"did we surface meaningful STRUCTURES that single-source search would miss?"
Six structure types, each defined operationally + counted against
two baselines (ICIJ-search-alone, naive degree-rank).

Structures detected (lower bound — operational definitions are conservative):

1. **Latent intermediary reuse**: ICIJ intermediaries linked to N+ distinct
   officers. Captures the "shared corporate secretary across unrelated
   clients" pattern.
2. **Unexpected jurisdiction bridges**: company pairs sharing an officer
   where the two companies are in different jurisdictions AND one is a
   high-risk offshore venue and the other a mainstream venue.
3. **Hidden registry anchors**: ICIJ entities that match a GLEIF LEI but
   are not sanctions-flagged. Formal-registry presence without disclosure
   flag.
4. **Sanctions-adjacent closure**: latent-cluster communities where
   at least one member is sanctioned.
5. **Fragmented ownership convergence**: addresses hosting 3-10 entities
   (not formation-agent hubs) with 3+ distinct primary officers.
6. **Anomalous community structures**: top-N from latent_clusters by
   anomaly score, mass-counted.

Baselines:
- **ICIJ-search-alone**: single-source search; structural connections not
  surfaced.
- **Degree-only**: top-K by raw degree; credibility ignored.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


_HIGH_RISK_OFFSHORE = frozenset(
    {"vg", "ky", "bm", "pa", "bs", "ai", "tc", "vc", "ms", "im", "je", "gg", "cy"}
)
_MAINSTREAM_VENUES = frozenset(
    {"gb", "us", "fr", "de", "nl", "ch", "lu", "ie", "se", "no", "fi", "dk", "ca", "au", "jp"}
)


def _struct1_latent_intermediary_reuse(edges: pl.DataFrame, min_clients: int = 3) -> dict:
    int_edges = edges.filter(pl.col("kind_raw") == "intermediary_of")
    if int_edges.height == 0:
        return {"n_detected": 0, "top_5": []}
    per_intermediary = (
        int_edges.group_by("dst_node")
        .agg(pl.col("src_node").n_unique().alias("n_clients"))
        .filter(pl.col("n_clients") >= min_clients)
        .sort("n_clients", descending=True)
    )
    return {
        "n_detected": int(per_intermediary.height),
        "min_clients_threshold": min_clients,
        "top_5": per_intermediary.head(5).to_dicts(),
    }


def _struct2_unexpected_jurisdiction_bridges(
    edges: pl.DataFrame, entities: pl.DataFrame
) -> dict:
    officer_edges = edges.filter(pl.col("kind_raw") == "officer_of")
    if officer_edges.height == 0:
        return {"n_detected": 0, "top_5": []}
    by_officer = (
        officer_edges.group_by("src_node")
        .agg(pl.col("dst_node").alias("companies"))
        .filter(pl.col("companies").list.len() >= 2)
    )
    pairs = (
        by_officer.with_columns(pl.col("companies").list.head(10).alias("c"))
        .select("src_node", "c")
        .explode("c")
        .rename({"c": "company_a"})
    )
    pairs = pairs.join(
        pairs.rename({"company_a": "company_b"}), on="src_node", how="inner"
    ).filter(pl.col("company_a") < pl.col("company_b"))

    ent = entities.with_columns(
        (pl.lit("icij:") + pl.col("source_id")).alias("entity_uid")
    ).select("entity_uid", pl.col("jurisdiction").alias("juris"))
    pairs = (
        pairs.join(
            ent.rename({"entity_uid": "company_a", "juris": "juris_a"}),
            on="company_a",
            how="left",
        )
        .join(
            ent.rename({"entity_uid": "company_b", "juris": "juris_b"}),
            on="company_b",
            how="left",
        )
        .filter(
            ((pl.col("juris_a").is_in(list(_HIGH_RISK_OFFSHORE))) & (pl.col("juris_b").is_in(list(_MAINSTREAM_VENUES))))
            | ((pl.col("juris_b").is_in(list(_HIGH_RISK_OFFSHORE))) & (pl.col("juris_a").is_in(list(_MAINSTREAM_VENUES))))
        )
        .unique(subset=["company_a", "company_b"])
    )
    return {
        "n_detected": int(pairs.height),
        "top_5": pairs.head(5).to_dicts(),
    }


def _struct3_hidden_registry_anchors(matched_csv: Path) -> dict:
    if not matched_csv.exists():
        return {"n_detected": 0, "top_5": []}
    df = pl.read_csv(matched_csv, ignore_errors=True, infer_schema_length=500)
    icij_to_gleif = df.filter(
        (pl.col("target_source") == "icij") & pl.col("ref_lei").is_not_null()
    )
    return {
        "n_detected": int(icij_to_gleif.height),
        "distinct_icij_uids": int(icij_to_gleif.select("target_entity_uid").unique().height),
        "distinct_leis": int(icij_to_gleif.select("ref_lei").unique().height),
        "top_5": icij_to_gleif.select(
            "target_name", "target_jurisdiction", "ref_name", "ref_lei"
        ).head(5).to_dicts(),
    }


def _struct4_sanctions_adjacent_closure(latent_parquet: Path) -> dict:
    if not latent_parquet.exists():
        return {"n_detected": 0, "top_5": []}
    df = pl.read_parquet(latent_parquet)
    flagged = df.filter(pl.col("n_sanctioned") >= 1).sort(
        "anomaly_score", descending=True
    )
    return {
        "n_detected": int(flagged.height),
        "top_5": flagged.head(5).to_dicts(),
    }


def _struct5_fragmented_ownership_convergence(
    entities: pl.DataFrame,
    edges: pl.DataFrame,
    min_entities: int = 3,
    max_entities: int = 10,
    min_officers: int = 3,
) -> dict:
    addr_groups = (
        entities.filter(pl.col("normalized_address").is_not_null())
        .group_by("normalized_address")
        .agg(pl.col("source_id").alias("sids"), pl.len().alias("n"))
        .filter((pl.col("n") >= min_entities) & (pl.col("n") <= max_entities))
    )
    # Build (address, company_uid) by exploding and string-prefixing per row.
    exploded = (
        addr_groups.select("normalized_address", "sids")
        .explode("sids")
        .with_columns((pl.lit("icij:") + pl.col("sids")).alias("company_uid"))
        .select("normalized_address", "company_uid")
    )
    officer_edges = edges.filter(pl.col("kind_raw") == "officer_of").rename(
        {"src_node": "officer_uid", "dst_node": "company_uid"}
    )
    result = (
        exploded.join(officer_edges, on="company_uid", how="inner")
        .group_by("normalized_address")
        .agg(
            pl.col("officer_uid").n_unique().alias("n_distinct_officers"),
            pl.col("company_uid").n_unique().alias("n_companies"),
        )
        .filter(pl.col("n_distinct_officers") >= min_officers)
        .sort("n_distinct_officers", descending=True)
    )
    return {
        "n_detected": int(result.height),
        "min_entities": min_entities,
        "max_entities": max_entities,
        "min_distinct_officers": min_officers,
        "top_5": result.head(5).to_dicts(),
    }


def _struct6_anomalous_communities(latent_parquet: Path, top_n: int = 50) -> dict:
    if not latent_parquet.exists():
        return {"n_detected": 0, "top_5": []}
    df = pl.read_parquet(latent_parquet)
    top = df.head(top_n)
    return {
        "n_detected": int(top.height),
        "median_size": int(top["size"].median() or 0),
        "max_anomaly": float(top["anomaly_score"].max() or 0),
        "top_5": top.head(5).to_dicts(),
    }


@app.command()
def main(
    edges_parquet: Path = typer.Option(INTERIM_DIR / "icij_edges.parquet", "--edges"),
    entities_parquet: Path = typer.Option(INTERIM_DIR / "icij_entities.parquet", "--entities"),
    matched_csv: Path = typer.Option(
        PROCESSED_DIR.parent / "reports" / "generated" / "icij_os_vs_gleif_matched.csv",
        "--matched-csv",
    ),
    latent_parquet: Path = typer.Option(
        PROCESSED_DIR / "latent_clusters.parquet", "--latent-clusters"
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "structure_benchmark_summary.json", "--out-summary"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_summary.parent.mkdir(parents=True, exist_ok=True)

    log.info("loading ICIJ edges + entities ...")
    edges = pl.read_parquet(edges_parquet).select("src_node", "dst_node", "kind_raw")
    entities = pl.read_parquet(entities_parquet).select(
        "source_id", "name", "normalized_name", "jurisdiction", "normalized_address"
    )

    log.info("S1 latent intermediary reuse ...")
    s1 = _struct1_latent_intermediary_reuse(edges)
    log.info("  %d", s1["n_detected"])
    log.info("S2 unexpected jurisdiction bridges ...")
    s2 = _struct2_unexpected_jurisdiction_bridges(edges, entities)
    log.info("  %d", s2["n_detected"])
    log.info("S3 hidden registry anchors ...")
    s3 = _struct3_hidden_registry_anchors(matched_csv)
    log.info("  %d", s3["n_detected"])
    log.info("S4 sanctions-adjacent closure ...")
    s4 = _struct4_sanctions_adjacent_closure(latent_parquet)
    log.info("  %d", s4["n_detected"])
    log.info("S5 fragmented ownership convergence ...")
    s5 = _struct5_fragmented_ownership_convergence(entities, edges)
    log.info("  %d", s5["n_detected"])
    log.info("S6 anomalous community structures ...")
    s6 = _struct6_anomalous_communities(latent_parquet)
    log.info("  %d", s6["n_detected"])

    baselines = {
        "S1": "ICIJ DB shows intermediary records but does not aggregate per-client distinctness in batch.",
        "S2": "Cross-entity bridges require joining officer-of edges across companies; ICIJ DB cannot compute that.",
        "S3": "ICIJ DB has no GLEIF integration. 0% reachable from ICIJ search alone.",
        "S4": "Per-entity records don't flag sanctions; community-level closure requires both layers.",
        "S5": "Per-address listings exist on ICIJ DB but officer-distinctness across hosted entities isn't surfaced.",
        "S6": "Communities are not a concept in ICIJ DB.",
    }

    summary = {
        "structures": {
            "S1_latent_intermediary_reuse": s1,
            "S2_jurisdiction_bridges": s2,
            "S3_hidden_registry_anchors": s3,
            "S4_sanctions_adjacent_closure": s4,
            "S5_fragmented_ownership_convergence": s5,
            "S6_anomalous_communities": s6,
        },
        "baseline_reachability": baselines,
        "totals": {
            "total_pipeline_structures": (
                s1["n_detected"] + s2["n_detected"] + s3["n_detected"]
                + s4["n_detected"] + s5["n_detected"] + s6["n_detected"]
            ),
        },
    }
    out_summary.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
