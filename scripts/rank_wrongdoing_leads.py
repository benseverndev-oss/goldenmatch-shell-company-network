"""Rank wrongdoing leads (roadmap Phase 2, issue #157).

Assembles the per-company wrongdoing-signal table from the available signal
sources, applies the live/harm gates, and emits a short ranked queue. Signal
inputs are pluggable parquets so Phases 1/3/4 feed in without changing this
script:

    uv run python scripts/rank_wrongdoing_leads.py \\
        --evasion      /data/processed/sanctions_evasion_timing.parquet \\
        --status       /data/processed/company_status.parquet  # optional (Phase 3) \\
        --extra-signals /data/processed/regulatory_breach.parquet  # optional, repeatable \\
        --out-parquet  /data/processed/wrongdoing_leads.parquet \\
        --out-md       /data/reports/generated/wrongdoing_leads.md
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.investigations import wrongdoing_signals as ws

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _evasion_signal(path: Path) -> pl.DataFrame:
    """Phase-1 evasion parquet -> per-company signal + a representative summary."""
    ev = pl.read_parquet(path)
    if ev.height == 0:
        return pl.DataFrame({"lead_id": [], "evasion_timing": [], "summary": []})
    return (
        ev.group_by("company_id")
        .agg(
            # same-surname successor near a designation is the strongest form.
            pl.when(pl.col("same_surname").any()).then(1.0).otherwise(0.6).alias("evasion_timing"),
            pl.col("principal_name").first().alias("principal_name"),
            pl.col("successor_name").first().alias("successor_name"),
        )
        .rename({"company_id": "lead_id"})
    )


def _render_md(df: pl.DataFrame) -> str:
    lines = [
        "# Wrongdoing leads (ranked)",
        "",
        "> **Lead list, not a verdict.** Scored by wrongdoing-signal strength, gated to "
        "live targets. Every row needs human verification before any use.",
        "",
        f"Rows: **{df.height}**.",
        "",
        "| # | Lead (company) | Score | Signals | Status | Harm | Note |",
        "| ---: | --- | ---: | --- | --- | --- | --- |",
    ]
    signal_cols = [c for c in ws.DEFAULT_WEIGHTS if c in df.columns]
    for i, r in enumerate(df.head(100).iter_rows(named=True), 1):
        sigs = ", ".join(f"{c}={r[c]:g}" for c in signal_cols if r.get(c))
        note = " / ".join(x for x in [r.get("principal_name"), r.get("successor_name")] if x)
        lines.append(
            f"| {i} | {r.get('company_name') or r['lead_id']} | {r['wrongdoing_score']:.2f} "
            f"| {sigs} | {r.get('active_status') or r.get('active') or '?'} "
            f"| {r.get('harm_category') or '?'} | {note} |"
        )
    lines.append("")
    return "\n".join(lines)


@app.command()
def main(
    evasion: Path = typer.Option(..., "--evasion", help="Phase-1 sanctions_evasion_timing.parquet"),
    status: Path | None = typer.Option(None, "--status", help="Phase-3 company_status.parquet"),
    extra_signals: list[Path] = typer.Option(
        [], "--extra-signals", help="parquet(s) with lead_id + signal columns"
    ),
    out_parquet: Path = typer.Option(..., "--out-parquet"),
    out_md: Path = typer.Option(..., "--out-md"),
    weights_json: Path | None = typer.Option(None, "--weights-json", help="override weights"),
    harm_gate: bool = typer.Option(False, "--harm-gate", help="drop leads with no harm angle"),
) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    leads = _evasion_signal(evasion)

    for sig in extra_signals:
        if not sig.exists():
            log.warning("extra-signals parquet missing, skipping: %s", sig)
            continue
        leads = leads.join(pl.read_parquet(sig), on="lead_id", how="full", coalesce=True)

    if status is not None and status.exists():
        st = pl.read_parquet(status)  # expects lead_id + active/harm_weight/...
        leads = leads.join(st, on="lead_id", how="left")

    weights = json.loads(weights_json.read_text()) if weights_json else None
    scored = ws.score_wrongdoing(leads, weights, harm_gate=harm_gate)

    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    scored.write_parquet(out_parquet)
    out_md.write_text(_render_md(scored), encoding="utf-8")
    log.info("wrote %d ranked wrongdoing leads -> %s", scored.height, out_parquet)
    typer.echo(f"{scored.height} leads -> {out_parquet}")


if __name__ == "__main__":
    app()
