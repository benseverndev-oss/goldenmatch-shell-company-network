"""Ingest a GLEIF Golden Copy snapshot (JSON or JSONL) into interim parquet.

Usage:
    uv run python scripts/ingest_gleif.py --input data/raw/gleif/sample.json
    uv run python scripts/ingest_gleif.py --input data/raw/gleif/full.jsonl --sample 10000

XML snapshots aren't supported yet — convert to JSON/JSONL first.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import INTERIM_DIR, ensure_dirs
from shellnet.sources import gleif

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    input: Path = typer.Option(
        ..., "--input", "-i", exists=False, help="Path to a GLEIF JSON/JSONL file."
    ),
    sample: int = typer.Option(0, "--sample", "-n", help="Truncate to N records (0 = all)."),
    out_dir: Path = typer.Option(INTERIM_DIR, help="Where to write interim parquet."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out = gleif.ingest(input_path=input, sample=sample, out_dir=out_dir)
    if out is None:
        raise typer.Exit(code=1)
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
