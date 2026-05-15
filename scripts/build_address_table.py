"""Build the unified address table from all available source parquets.

    uv run python scripts/build_address_table.py

Fuses every address-bearing interim parquet (ICIJ + OpenSanctions today)
into ``data/processed/address_entities.parquet``. Idempotent; safe to
re-run after any ingestion.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.matching.address_features import build_address_table
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    interim_dir: Path = typer.Option(INTERIM_DIR, help="Override the interim-parquet directory."),
    out_dir: Path = typer.Option(PROCESSED_DIR, help="Where to write `address_entities.parquet`."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out = build_address_table(interim_dir=interim_dir, out_dir=out_dir)
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
