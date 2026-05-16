"""Project the UK disqualified-directors scraper CSV into a parquet.

    uv run python scripts/ingest_uk_disqualified_directors.py \\
        --input data/raw/scrapers/disqualified-directors/disqualified-directors.csv

Output: ``data/interim/uk_disqualified_directors.parquet`` with a
normalized person name + DoB suitable for left-joining against the
person table. See ``src/shellnet/sources/uk_disqualified_directors.py``
for the schema and rationale.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import INTERIM_DIR, RAW_DIR, ensure_dirs
from shellnet.sources import uk_disqualified_directors

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    input: Path = typer.Option(
        RAW_DIR / "scrapers" / "disqualified-directors" / "disqualified-directors.csv",
        "--input",
        "-i",
        help="Path to the scraper output CSV.",
    ),
    out_dir: Path = typer.Option(INTERIM_DIR, "--out-dir"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out = uk_disqualified_directors.ingest(input, out_dir=out_dir)
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
