"""Build per-lead verification dossiers (roadmap Phase 5, issue #160).

Turns the ranked wrongdoing queue into one verifiable dossier per lead, with
primary-source links, the signals that fired, a right-of-reply draft, and a
mandatory verification/defamation checklist. Reports how many dossiers are
cleared for publication (zero until a human ticks the boxes — the gate).

    uv run python scripts/build_lead_dossier.py \\
        --leads   /data/processed/wrongdoing_leads.parquet \\
        --out-dir /data/validation/leads \\
        --top-n   25
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.investigations import lead_dossier

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _safe(lead_id: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in str(lead_id))


@app.command()
def main(
    leads: Path = typer.Option(..., "--leads", help="ranked wrongdoing_leads.parquet"),
    out_dir: Path = typer.Option(..., "--out-dir"),
    top_n: int = typer.Option(25, "--top-n"),
) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    df = pl.read_parquet(leads)
    if "wrongdoing_score" in df.columns:
        df = df.sort("wrongdoing_score", descending=True)
    df = df.head(top_n)

    out_dir.mkdir(parents=True, exist_ok=True)
    cleared = 0
    for r in df.iter_rows(named=True):
        md = lead_dossier.build_dossier(r)
        (out_dir / f"{_safe(r.get('lead_id'))}.md").write_text(md, encoding="utf-8")
        cleared += int(lead_dossier.is_cleared(md))

    log.info("wrote %d dossiers -> %s (%d cleared for publication)", df.height, out_dir, cleared)
    typer.echo(f"{df.height} dossiers, {cleared} cleared (gate: human must tick the checklist)")


if __name__ == "__main__":
    app()
