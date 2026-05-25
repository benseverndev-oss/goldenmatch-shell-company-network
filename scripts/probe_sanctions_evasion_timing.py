"""Sanctions-evasion timing probe (roadmap Phase 1, issue #156).

Joins the UK PSC relationship layer (control start/end dates) against
OpenSanctions designation dates to surface control transfers that cluster
around the moment a controller/company was sanctioned — the divestment-to-a-
nominee pattern (e.g. Nikita Mordashov receiving shares after his father's
designation).

    uv run python scripts/probe_sanctions_evasion_timing.py \\
        --survivors    /data/reports/generated/investigative_grade_survivors.csv \\
        --relationships /data/interim/uk_psc_relationships.parquet \\
        --os-entities  /data/interim/opensanctions_entities.parquet \\
        --persons      /data/interim/uk_psc_persons.parquet \\
        --out-parquet  /data/processed/sanctions_evasion_timing.parquet \\
        --out-md       /data/reports/generated/sanctions_evasion_timing.md

Lead list, not a verdict: every row needs human verification of the actual
control change and the relationship between principal and successor.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.investigations import evasion_timing

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _render_md(df: pl.DataFrame, window_days: int) -> str:
    lines = [
        "# Sanctions-evasion timing leads",
        "",
        "> **Lead list, not a verdict.** Each row is a PSC control change that fell "
        f"within ±{window_days} days of a sanctions designation. Confirm the actual "
        "transfer, the principal↔successor relationship, and current company status "
        "before any use.",
        "",
        f"Rows: **{df.height}** (same-surname successors first).",
        "",
        "| Principal | Designated | Date quality | Company | Successor PSC | Δ days | Same surname |",
        "| --- | --- | --- | --- | --- | ---: | :---: |",
    ]
    for r in df.head(200).iter_rows(named=True):
        lines.append(
            f"| {r['principal_name']} | {r['designation_date']} | {r['date_quality']} "
            f"| {r['company_id']} | {r['successor_name'] or '?'} "
            f"| {r['delta_days']} | {'✓' if r['same_surname'] else ''} |"
        )
    lines.append("")
    return "\n".join(lines)


@app.command()
def main(
    survivors: Path = typer.Option(..., "--survivors", help="investigative_grade_survivors.csv"),
    relationships: Path = typer.Option(..., "--relationships", help="uk_psc_relationships.parquet"),
    os_entities: Path = typer.Option(..., "--os-entities", help="opensanctions_entities.parquet"),
    persons: Path = typer.Option(..., "--persons", help="uk_psc_persons.parquet"),
    out_parquet: Path = typer.Option(..., "--out-parquet"),
    out_md: Path = typer.Option(..., "--out-md"),
    window_days: int = typer.Option(180, "--window-days", help="± window around designation"),
) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    surv = (
        pl.read_csv(survivors, infer_schema_length=10000)
        if survivors.suffix == ".csv"
        else pl.read_parquet(survivors)
    )
    rels = pl.read_parquet(relationships)
    desig = evasion_timing.build_designation_dates(pl.read_parquet(os_entities))
    ppl = pl.read_parquet(persons).select("source_id", "name")

    leads = evasion_timing.detect_evasion_timing(surv, rels, desig, ppl, window_days=window_days)

    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    leads.write_parquet(out_parquet)
    out_md.write_text(_render_md(leads, window_days), encoding="utf-8")
    log.info("wrote %d evasion-timing leads -> %s / %s", leads.height, out_parquet, out_md)
    typer.echo(f"{leads.height} leads -> {out_parquet}")


if __name__ == "__main__":
    app()
