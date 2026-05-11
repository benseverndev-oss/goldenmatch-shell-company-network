"""Ingest the ICIJ Offshore Leaks CSV bundle into interim parquet.

Usage:
    uv run python scripts/ingest_icij.py
    uv run python scripts/ingest_icij.py --raw-dir /custom/path

The script never downloads anything; the user is expected to fetch the
files manually from https://offshoreleaks.icij.org/pages/database and
place them under data/raw/icij/ (or pass --raw-dir).
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import ICIJ_RAW, INTERIM_DIR, ensure_dirs
from shellnet.sources import icij

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    raw_dir: Path = typer.Option(ICIJ_RAW, help="Directory containing ICIJ CSV files."),
    out_dir: Path = typer.Option(INTERIM_DIR, help="Where to write interim parquet files."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    written = icij.ingest(raw_dir=raw_dir, out_dir=out_dir)
    if not written:
        typer.echo(
            f"No ICIJ files found in {raw_dir}. Download the Offshore Leaks bundle from "
            "https://offshoreleaks.icij.org/pages/database and unzip it there, then re-run."
        )
        raise typer.Exit(code=0)
    for label, path in written.items():
        typer.echo(f"  {label}: {path}")


if __name__ == "__main__":
    app()
