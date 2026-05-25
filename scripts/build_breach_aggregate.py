"""Systemic breach aggregate + precision view (precision roadmap P6).

Joins the director-breach grading (P1) with the conduct mining (P4) to produce
the *defensible* systemic finding — "N disqualified directors are currently
acting as directors of UK companies" — separated from passive shareholders, and
broken down by conduct (e.g. Covid Bounce Back Loan fraud). This is the
aggregate that only holds once P1 has distinguished directing from owning.

    uv run python scripts/build_breach_aggregate.py \\
        --graded /data/processed/director_breach.parquet \\
        --breach /data/processed/regulatory_breach.parquet \\
        --out-md /data/reports/generated/breach_aggregate.md
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.investigations import director_breach as db

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


@app.command()
def main(
    graded: Path = typer.Option(..., "--graded", help="director_breach.parquet"),
    breach: Path = typer.Option(..., "--breach", help="regulatory_breach.parquet"),
    out_md: Path = typer.Option(..., "--out-md"),
    min_confidence: float = typer.Option(0.8, "--min-confidence"),
) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    g = pl.read_parquet(graded)
    b = pl.read_parquet(breach)
    conduct_cols = [
        c for c in ("conduct_category", "public_funds_fraud", "disqualified_name") if c in b.columns
    ]
    df = g.join(b.select(["lead_id", *conduct_cols]), on="lead_id", how="left")

    grades = db.summarize(g)
    total = int(g.height)
    acting = grades.get("acting_director", 0)
    acting_hi = df.filter(
        (pl.col("breach_grade") == "acting_director")
        & (pl.col("identity_confidence") >= min_confidence)
    ).height
    bbl_acting = 0
    if "public_funds_fraud" in df.columns:
        bbl_acting = df.filter(
            (pl.col("breach_grade") == "acting_director") & (pl.col("public_funds_fraud") == 1.0)
        ).height

    lines = [
        "# Disqualified-director breach — systemic aggregate",
        "",
        "> **Lead list, not a verdict.** Counts are candidates for verification, "
        "not findings. s.11 CDDA bans *directing/managing*; a disqualified person "
        "who only *owns* shares (`psc_only`) is not in breach.",
        "",
        f"Total disqualified-PSC leads graded: **{total}**.",
        "",
        "| Grade | Count | Meaning |",
        "| --- | ---: | --- |",
        f"| acting_director | {grades['acting_director']} | current director — **candidate s.11 breach** |",
        f"| resigned_director | {grades['resigned_director']} | was a director, since resigned (retains ownership) |",
        f"| psc_only | {grades['psc_only']} | >25% shareholder only — not a directorship breach |",
        f"| officer_other | {grades['officer_other']} | non-director officer (e.g. secretary) |",
        f"| unknown | {grades['unknown']} | officers page unavailable |",
        "",
        "## Defensible headline",
        "",
        f"- **{acting}** disqualified people are currently acting as **directors** "
        "of UK companies (candidate s.11 CDDA breaches).",
        f"- Of those, **{acting_hi}** clear an identity-confidence threshold of "
        f"{min_confidence:g} (name + DOB + address corroborated).",
        f"- **{bbl_acting}** of the acting-director breaches involve **public-funds "
        "(Covid Bounce Back Loan) fraud** conduct.",
        "",
        "_The systemic angle — disqualified directors slipping back onto boards — is "
        "only defensible at the `acting_director` count, not the raw PSC count._",
        "",
    ]
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")
    log.info(
        "breach aggregate: total=%d acting=%d acting_hi_conf=%d bbl_acting=%d -> %s",
        total,
        acting,
        acting_hi,
        bbl_acting,
        out_md,
    )
    typer.echo(f"acting_director={acting} (hi-conf {acting_hi}, bbl {bbl_acting}) -> {out_md}")


if __name__ == "__main__":
    app()
