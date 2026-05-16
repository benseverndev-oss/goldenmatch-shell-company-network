"""Cross-reference the UK Insolvency Service struck-off director register
against the full unified person + company entity tables.

The original join inside the novelty report only looked at the 200-row
report-internal slice, which is too narrow — any actual overlap with
shell-network officers would be in the full person_entities table,
not the pre-filtered sample.

This script:

1. Reads ``interim/uk_disqualified_directors.parquet`` (~222 rows).
2. Scans the full ``processed/person_entities.parquet`` for rows whose
   ``normalized_name`` matches a disqualified-director name.
3. Same against ``processed/company_entities.parquet`` for the
   disqualified-director's **company** name (the struck-off director
   probably had multiple companies; only one is in the source CSV,
   but the company-table scan catches more).
4. Emits ``processed/disqualified_overlaps.parquet`` with provenance
   so the novelty report can include this as a separate signal.

Designed to run on Railway (``/data`` paths in the allowlist). Memory
footprint is bounded — we read disq into Python sets, then use
``scan_parquet().filter(is_in(...)).collect()`` to avoid loading the
multi-GB tables fully.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


@app.command()
def main(
    disqualified: Path = typer.Option(
        INTERIM_DIR / "uk_disqualified_directors.parquet",
        "--disqualified",
        help="Parquet from ingest_uk_disqualified_directors.py.",
    ),
    person_table: Path = typer.Option(
        PROCESSED_DIR / "person_entities.parquet",
        "--person-table",
    ),
    company_table: Path = typer.Option(
        PROCESSED_DIR / "company_entities.parquet",
        "--company-table",
    ),
    out: Path = typer.Option(
        PROCESSED_DIR / "disqualified_overlaps.parquet",
        "--out",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out.parent.mkdir(parents=True, exist_ok=True)

    disq = pl.read_parquet(disqualified)
    log.info("loaded %d disqualified-director rows", disq.height)

    person_names = (
        disq.filter(pl.col("normalized_person_name").is_not_null())
        .select("normalized_person_name")
        .to_series()
        .to_list()
    )
    company_names = (
        disq.filter(pl.col("normalized_company_name").is_not_null())
        .select("normalized_company_name")
        .to_series()
        .to_list()
    )
    log.info("scanning person table for %d names...", len(set(person_names)))

    person_hits = (
        pl.scan_parquet(person_table)
        .filter(pl.col("normalized_name").is_in(person_names))
        .select(
            pl.lit("person").alias("overlap_kind"),
            pl.col("entity_uid"),
            pl.col("source"),
            pl.col("name"),
            pl.col("normalized_name"),
            pl.col("country"),
        )
        .collect()
    )
    log.info("person table overlaps: %d", person_hits.height)

    company_hits = (
        pl.scan_parquet(company_table)
        .filter(pl.col("normalized_name").is_in(company_names))
        .select(
            pl.lit("company").alias("overlap_kind"),
            pl.col("entity_uid"),
            pl.col("source"),
            pl.col("name"),
            pl.col("normalized_name"),
            pl.col("jurisdiction").alias("country"),
        )
        .collect()
    )
    log.info("company table overlaps: %d", company_hits.height)

    # Carry the disq-side context with each match so a reviewer can read
    # one row and see both halves of the overlap.
    disq_person_lookup = disq.select(
        pl.col("normalized_person_name").alias("normalized_name"),
        pl.col("person_name").alias("disq_person_name"),
        pl.col("date_of_birth").alias("disq_dob"),
        pl.col("disqualification_length").alias("disq_length"),
        pl.col("source_id").alias("disq_case_number"),
    ).unique(subset=["normalized_name"])
    disq_company_lookup = disq.select(
        pl.col("normalized_company_name").alias("normalized_name"),
        pl.col("company_name").alias("disq_company_name"),
        pl.col("person_name").alias("disq_person_name"),
        pl.col("date_of_birth").alias("disq_dob"),
        pl.col("disqualification_length").alias("disq_length"),
        pl.col("source_id").alias("disq_case_number"),
    ).unique(subset=["normalized_name"])

    person_joined = person_hits.join(disq_person_lookup, on="normalized_name", how="left")
    company_joined = company_hits.join(disq_company_lookup, on="normalized_name", how="left")

    combined = pl.concat([person_joined, company_joined], how="diagonal_relaxed")
    combined.write_parquet(out)
    log.info("wrote %d total overlap rows to %s", combined.height, out)
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
