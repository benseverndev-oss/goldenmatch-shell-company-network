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
        --out /tmp/rare_dossiers_v1.parquet \\
        --top-n 50 --verbose
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import PROCESSED_DIR, ensure_dirs

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
    out: Path = typer.Option(
        PROCESSED_DIR / "rare_officer_dossiers.parquet",
        "--out",
        help="Output parquet path for dossier stub rows.",
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
    _ = max_degree  # used in task 3

    seeds = _seed_names(officer_overlap, top_n)
    log.info("seeds selected: %d", seeds.height)

    stubs = _stub_rows(seeds, person_table)
    log.info("stub rows: %d (one per matched person)", stubs.height)

    stubs.write_parquet(out)
    typer.echo(f"Wrote: {out}")
    typer.echo(f"  {stubs.height} stub rows across {seeds.height} seed names")


if __name__ == "__main__":
    app()
