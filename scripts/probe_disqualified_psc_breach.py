"""Disqualified-director-still-acting probe (roadmap Phase 4, issue #159).

Crosses the UK disqualified-directors register against the uk_psc_relationships
layer to flag disqualified people who are *currently* PSCs of UK companies
(candidate s.11 CDDA 1986 breach). Emits a ``regulatory_breach`` signal parquet
the Phase-2 ranker consumes via ``--extra-signals``.

    uv run python scripts/probe_disqualified_psc_breach.py \\
        --disqualified  /data/interim/uk_disqualified_directors.parquet \\
        --persons       /data/interim/uk_psc_persons.parquet \\
        --psc-dob       /data/processed/uk_psc_dob.parquet \\
        --relationships /data/interim/uk_psc_relationships.parquet \\
        --out           /data/processed/regulatory_breach.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.investigations import harm
from shellnet.investigations import regulatory_breach as rb

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _norm_dob(col: str) -> pl.Expr:
    return pl.col(col).map_elements(rb.normalize_dob_ym, return_dtype=pl.Utf8)


@app.command()
def main(
    disqualified: Path = typer.Option(..., "--disqualified"),
    persons: Path = typer.Option(..., "--persons", help="uk_psc_persons.parquet"),
    psc_dob: Path = typer.Option(..., "--psc-dob", help="uk_psc_dob.parquet (statementId, dob)"),
    relationships: Path = typer.Option(..., "--relationships"),
    out: Path = typer.Option(..., "--out"),
) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    disq = pl.read_parquet(disqualified).select(
        pl.col("normalized_person_name").alias("norm_name"),
        _norm_dob("date_of_birth").alias("dob_ym"),
        pl.col("conduct"),
    )

    ppl = pl.read_parquet(persons).select(
        pl.col("source_id").alias("person_source_id"),
        pl.col("normalized_name").alias("norm_name"),
    )
    dob = pl.read_parquet(psc_dob).select(
        pl.col("statementId").alias("person_source_id"),
        _norm_dob("dob").alias("dob_ym"),
    )
    psc_identity = ppl.join(dob, on="person_source_id", how="inner")

    rels = pl.read_parquet(relationships).select("person_source_id", "company_id", "end_date")

    breaches = rb.detect_disqualified_psc(disq, psc_identity, rels)
    # Mine the disqualification narrative for conduct severity (precision P4):
    # the register is dominated by Covid Bounce Back Loan fraud (public money).
    if breaches.height:
        breaches = breaches.with_columns(
            pl.col("conduct")
            .map_elements(harm.classify_conduct, return_dtype=pl.Utf8)
            .alias("conduct_category")
        ).with_columns(
            pl.when(pl.col("conduct_category") == "public_funds_fraud")
            .then(1.0)
            .otherwise(0.0)
            .alias("public_funds_fraud")
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    breaches.write_parquet(out)
    log.info("wrote %d disqualified-PSC breach leads -> %s", breaches.height, out)
    typer.echo(f"{breaches.height} breach leads -> {out}")


if __name__ == "__main__":
    app()
