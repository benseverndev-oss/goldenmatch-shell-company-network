"""Build per-lead exposé-candidate dossiers from rare cross-source officer names.

Spec: docs/superpowers/specs/2026-05-16-expose-candidates-design.md

Reads officer_overlap.parquet (the section-4 source from join_novelty.md),
re-applies the rare-name filter (the on-disk filter is permissive per
build_officer_overlap.py), picks top-N seeds, and emits one denormalized
parquet row per (rare_name × person × company × attribute-snapshot).

For ICIJ-source persons, walks icij_edges to expand into linked
companies + co-officers + sanctions adjacency (only for OS-sourced
linked companies — see spec Limitations table). For UK PSC / OS
persons, emits only stub rows (no relations parquet exists today).

Usage examples
--------------
# Default paths (Railway /data/processed):
    uv run python scripts/build_rare_officer_dossiers.py

# Custom paths + verbose:
    uv run python scripts/build_rare_officer_dossiers.py \\
        --officer-overlap data/processed/officer_overlap.parquet \\
        --person-table data/processed/person_entities.parquet \\
        --icij-edges data/interim/icij_edges.parquet \\
        --company-table data/processed/company_entities.parquet \\
        --sanctions-overlay data/processed/sanctions_overlay.parquet \\
        --out /tmp/rare_dossiers_v2.parquet \\
        --top-n 50 --max-degree 25 --verbose
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


# Rare-name filter from spec. On-disk officer_overlap.parquet has the
# permissive build-time filter (max_per_source <= 50, n_tokens >= 2);
# the tight one we want lives downstream in build_join_novelty_report.
_MAX_PER_SOURCE = 2
_MIN_TOKENS = 3


def _seed_names(officer_overlap: Path, top_n: int) -> pl.DataFrame:
    """Read officer_overlap, apply rare filter, return top-N seeds."""
    raw = pl.read_parquet(officer_overlap)
    return (
        raw.filter(
            (pl.col("max_per_source") <= _MAX_PER_SOURCE)
            & (pl.col("n_tokens") >= _MIN_TOKENS)
            & (pl.col("n_sources") >= 2)
        )
        .sort(by=["n_sources", "total_entities"], descending=[True, True])
        .head(top_n)
    )


def _stub_rows(seeds: pl.DataFrame, person_table: Path) -> pl.DataFrame:
    """One stub row per matched person from person_entities."""
    seed_names = seeds.select("normalized_name").to_series().to_list()
    matched = (
        pl.scan_parquet(person_table)
        .filter(pl.col("normalized_name").is_in(seed_names))
        .select(
            pl.col("normalized_name").alias("rare_name"),
            pl.col("source").alias("person_source"),
            pl.col("entity_uid").alias("person_entity_uid"),
            pl.col("name").alias("person_name"),
            pl.col("country").alias("person_country"),
        )
        .collect()
    )
    return matched.with_columns(
        pl.lit(None).cast(pl.Utf8).alias("company_entity_uid"),
        pl.lit(None).cast(pl.Utf8).alias("company_name"),
        pl.lit(None).cast(pl.Utf8).alias("company_source"),
        pl.lit(None).cast(pl.Utf8).alias("company_jurisdiction"),
        pl.lit(None).cast(pl.Utf8).alias("company_normalized_address"),
        pl.lit(None).cast(pl.List(pl.Utf8)).alias("co_officers"),
        pl.lit(None).cast(pl.Utf8).alias("sanction_datasets"),
        pl.lit(None).cast(pl.Int32).alias("n_sanction_datasets"),
        pl.lit(False).alias("degree_capped"),
    )


def _expanded_icij_rows(
    stubs: pl.DataFrame,
    icij_edges: Path,
    company_table: Path,
    person_table: Path,
    sanctions_overlay: Path,
    max_edges_per_seed: int,
) -> pl.DataFrame:
    """For ICIJ-source person rows in stubs, walk icij_edges to companies.

    Returns rows with the same schema as stubs but with company columns
    populated. Stubs themselves are kept by the caller; this returns the
    extra expanded rows alongside them.
    """
    icij_seeds = stubs.filter(pl.col("person_source") == "icij")
    if icij_seeds.height == 0:
        return stubs.head(0)  # empty same-schema frame

    seed_uids = icij_seeds.select("person_entity_uid").to_series().to_list()

    edges = (
        pl.scan_parquet(icij_edges)
        .filter(
            pl.col("src_node").is_in(seed_uids) | pl.col("dst_node").is_in(seed_uids)
        )
        .collect()
    )

    # Build (seed_uid, other_uid) pairs.
    pairs = (
        pl.concat(
            [
                edges.filter(pl.col("src_node").is_in(seed_uids)).select(
                    pl.col("src_node").alias("seed_uid"),
                    pl.col("dst_node").alias("linked_uid"),
                ),
                edges.filter(pl.col("dst_node").is_in(seed_uids)).select(
                    pl.col("dst_node").alias("seed_uid"),
                    pl.col("src_node").alias("linked_uid"),
                ),
            ],
            how="vertical",
        )
        .unique()
        .filter(pl.col("seed_uid") != pl.col("linked_uid"))
    )

    # Edge-fan-out cap per seed. Note: this caps RAW edges, not linked
    # companies — some edges resolve to addresses or non-company entities
    # and will get filtered out by the company join below. Renaming to
    # max_edges_per_seed for honesty.
    degree_per_seed = pairs.group_by("seed_uid").agg(pl.len().alias("degree"))
    pairs = pairs.join(degree_per_seed, on="seed_uid", how="left")
    capped = pairs.with_columns(
        (pl.col("degree") > max_edges_per_seed).alias("degree_capped")
    )
    capped = capped.sort("linked_uid").group_by("seed_uid").head(max_edges_per_seed)

    # Lookup linked companies (linked_uid that exist in company_entities)
    companies = (
        pl.scan_parquet(company_table)
        .filter(pl.col("entity_uid").is_in(capped.select("linked_uid").to_series().to_list()))
        .select(
            pl.col("entity_uid").alias("company_entity_uid"),
            pl.col("name").alias("company_name"),
            pl.col("source").alias("company_source"),
            pl.col("source_id").alias("company_source_id"),
            pl.col("jurisdiction").alias("company_jurisdiction"),
            pl.col("normalized_address").alias("company_normalized_address"),
        )
        .collect()
    )

    # Sanctions adjacency: only for OS-sourced companies; strip the prefix.
    overlay = pl.read_parquet(sanctions_overlay).select(
        pl.col("os_id"),
        pl.col("datasets").alias("sanction_datasets"),
        pl.col("n_datasets").alias("n_sanction_datasets"),
    )
    companies = companies.with_columns(
        pl.when(pl.col("company_source") == "opensanctions")
        .then(pl.col("company_source_id").str.replace("^opensanctions:", ""))
        .otherwise(None)
        .alias("_os_key")
    )
    companies = companies.join(
        overlay, left_on="_os_key", right_on="os_id", how="left"
    ).drop("_os_key", "company_source_id")

    # Join companies onto the (seed, linked) pairs.
    expanded = (
        capped.rename({"linked_uid": "company_entity_uid"})
        .join(companies, on="company_entity_uid", how="inner")
    )

    # Co-officers: other persons sharing an edge with this company.
    company_uids = expanded.select("company_entity_uid").to_series().to_list()
    co_edges = (
        pl.scan_parquet(icij_edges)
        .filter(
            pl.col("src_node").is_in(company_uids) | pl.col("dst_node").is_in(company_uids)
        )
        .collect()
    )
    co_pairs = pl.concat(
        [
            co_edges.filter(pl.col("src_node").is_in(company_uids)).select(
                pl.col("src_node").alias("company_entity_uid"),
                pl.col("dst_node").alias("co_uid"),
            ),
            co_edges.filter(pl.col("dst_node").is_in(company_uids)).select(
                pl.col("dst_node").alias("company_entity_uid"),
                pl.col("src_node").alias("co_uid"),
            ),
        ],
        how="vertical",
    ).unique()

    # co_uid -> normalized_name (only those that are persons in person_entities).
    # Use the explicitly-passed person_table path rather than guessing a
    # sibling filename -- the spec doesn't pin layout that strictly.
    co_names = (
        pl.scan_parquet(person_table)
        .filter(pl.col("entity_uid").is_in(co_pairs.select("co_uid").to_series().to_list()))
        .select(
            pl.col("entity_uid").alias("co_uid"),
            pl.col("normalized_name").alias("co_name"),
        )
        .collect()
    )
    co_pairs = co_pairs.join(co_names, on="co_uid", how="inner")
    co_officers = co_pairs.group_by("company_entity_uid").agg(
        pl.col("co_name").unique().alias("co_officers")
    )

    expanded = expanded.join(co_officers, on="company_entity_uid", how="left")

    # Join back to seed person info to fill the dossier schema.
    seed_info = icij_seeds.select(
        pl.col("person_entity_uid").alias("seed_uid"),
        "rare_name",
        "person_source",
        "person_name",
        "person_country",
    )
    out = expanded.join(seed_info, on="seed_uid", how="inner").select(
        "rare_name",
        "person_source",
        pl.col("seed_uid").alias("person_entity_uid"),
        "person_name",
        "person_country",
        "company_entity_uid",
        "company_name",
        "company_source",
        "company_jurisdiction",
        "company_normalized_address",
        "co_officers",
        "sanction_datasets",
        pl.col("n_sanction_datasets").cast(pl.Int32),
        "degree_capped",
    )
    return out


@app.command()
def main(
    officer_overlap: Path = typer.Option(
        PROCESSED_DIR / "officer_overlap.parquet",
        "--officer-overlap",
        help="Path to officer_overlap.parquet (section-4 source).",
    ),
    person_table: Path = typer.Option(
        PROCESSED_DIR / "person_entities.parquet",
        "--person-table",
        help="Path to person_entities.parquet for stub-row expansion.",
    ),
    icij_edges: Path = typer.Option(
        INTERIM_DIR / "icij_edges.parquet",
        "--icij-edges",
        help="Path to icij_edges.parquet for 2-hop walk.",
    ),
    company_table: Path = typer.Option(
        PROCESSED_DIR / "company_entities.parquet",
        "--company-table",
        help="Path to company_entities.parquet.",
    ),
    sanctions_overlay: Path = typer.Option(
        PROCESSED_DIR / "sanctions_overlay.parquet",
        "--sanctions-overlay",
        help="Path to sanctions_overlay.parquet.",
    ),
    out: Path = typer.Option(
        PROCESSED_DIR / "rare_officer_dossiers.parquet",
        "--out",
        help="Output parquet path for dossier rows.",
    ),
    top_n: int = typer.Option(50, "--top-n", help="Number of seed names to select."),
    max_degree: int = typer.Option(
        25,
        "--max-degree",
        help="Max graph-walk degree (reserved for task 3 ICIJ walk).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG logging."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out.parent.mkdir(parents=True, exist_ok=True)

    seeds = _seed_names(officer_overlap, top_n)
    log.info("seeds selected: %d", seeds.height)

    stubs = _stub_rows(seeds, person_table)
    log.info("stub rows: %d", stubs.height)

    expanded = _expanded_icij_rows(
        stubs,
        icij_edges=icij_edges,
        company_table=company_table,
        person_table=person_table,
        sanctions_overlay=sanctions_overlay,
        max_edges_per_seed=max_degree,
    )
    log.info("icij-expanded rows: %d", expanded.height)

    all_rows = pl.concat([stubs, expanded], how="diagonal_relaxed")
    log.info("total dossier rows: %d", all_rows.height)
    all_rows.write_parquet(out)
    typer.echo(f"Wrote: {out}")
    typer.echo(f"  {all_rows.height} total rows ({stubs.height} stubs + {expanded.height} icij-expanded) across {seeds.height} seed names")


if __name__ == "__main__":
    app()
