"""Lead-precision metrics + signal lift (roadmap Phase 6, issue #161).

Joins the ranked queue against the human-review outcomes log and reports
top-N precision, novelty rate, and per-signal lift — the feedback that retunes
the Phase-2 weights.

    uv run python scripts/score_lead_precision.py \\
        --leads    /data/processed/wrongdoing_leads.parquet \\
        --outcomes /data/validation/outcomes.csv \\
        --out-md   /data/reports/generated/lead_precision.md

Outcomes CSV columns: lead_id, reviewed_at, verdict, reviewer_note
(verdict in: genuine | novel | published | rejected | duplicate | not_novel).
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.investigations import lead_outcomes as lo

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _render(metrics: dict, lift: pl.DataFrame, ns: list[int]) -> str:
    lines = [
        "# Lead precision & signal lift",
        "",
        "Feedback metrics from the human-review outcomes log. Precision is the "
        "fraction of *reviewed* top-N leads that survived (genuine / novel / "
        "published). Signal lift drives the Phase-2 weight retuning.",
        "",
        "| top-N | in queue | reviewed | positives | precision | novelty rate |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for n in ns:
        m = metrics[n]
        lines.append(
            f"| {m['n']} | {m['in_top_n']} | {m['reviewed']} | {m['positives']} "
            f"| {m['precision']} | {m['novelty_rate']} |"
        )
    lines += ["", "## Signal lift (positive-rate delta when present)", ""]
    if lift.height:
        lines.append("| signal | n_with | rate_with | rate_without | lift |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for r in lift.iter_rows(named=True):
            lines.append(
                f"| {r['signal']} | {r['n_with']} | {r['rate_with']} "
                f"| {r['rate_without']} | {r['lift']} |"
            )
    else:
        lines.append("_No reviewed leads yet — record verdicts in the outcomes log._")
    lines.append("")
    return "\n".join(lines)


@app.command()
def main(
    leads: Path = typer.Option(..., "--leads"),
    outcomes: Path = typer.Option(..., "--outcomes", help="review outcomes CSV"),
    out_md: Path = typer.Option(..., "--out-md"),
    top_ns: str = typer.Option("10,20,50", "--top-ns", help="comma-separated N values"),
) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    leads_df = pl.read_parquet(leads)
    out_df = (
        pl.read_csv(outcomes)
        if outcomes.exists()
        else pl.DataFrame(schema={c: pl.Utf8 for c in lo.OUTCOME_COLUMNS})
    )
    ns = [int(x) for x in top_ns.split(",")]
    metrics = {n: lo.top_n_precision(leads_df, out_df, n) for n in ns}
    lift = lo.signal_lift(leads_df, out_df)

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(_render(metrics, lift, ns), encoding="utf-8")
    log.info("wrote lead-precision report -> %s", out_md)
    typer.echo(f"precision@{ns[0]} = {metrics[ns[0]]['precision']} -> {out_md}")


if __name__ == "__main__":
    app()
