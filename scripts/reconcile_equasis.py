"""Enrich a CSV of IMO numbers with Equasis ship details.

    uv run python scripts/reconcile_equasis.py \\
        --input /data/reports/generated/shortlist_imos.csv \\
        --imo-field IMO \\
        --out /data/reports/generated/shortlist_imos_enriched.csv

Hard-capped by Equasis to ~500 lookups/day; exceeding twice gets a
7-day block. Feed it deduped shortlists from ``rank_clusters.py`` /
investigative reports, never the full corpus.

Credentials: ``EQUASIS_CREDENTIALS=email@example.com:password`` in env.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import typer

from shellnet.paths import DATA_DIR, ensure_dirs
from shellnet.sources import reconcile

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    input: Path = typer.Option(..., "--input", "-i", help="Input CSV with an IMO column."),
    imo_field: str = typer.Option("IMO", "--imo-field", help="Column name holding the IMO number."),
    out: Path = typer.Option(..., "--out", "-o", help="Output CSV path."),
    cache_dir: Path = typer.Option(
        DATA_DIR / "interim" / "reconcile_cache" / "equasis",
        "--cache-dir",
        help="HTTP cache directory; survives across runs to avoid burning the daily quota.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    creds = os.environ.get("EQUASIS_CREDENTIALS")
    if not creds or ":" not in creds:
        raise typer.BadParameter("EQUASIS_CREDENTIALS env var must be set as 'email:password'.")
    out_path = reconcile.run(
        "ship-imo-numbers-to-ship-details",
        input,
        out,
        params={"credentials": creds, "shipIMONumberField": imo_field},
        cache_dir=cache_dir,
    )
    typer.echo(f"Wrote: {out_path}")


if __name__ == "__main__":
    app()
