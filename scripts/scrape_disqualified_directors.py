"""Scrape the UK Insolvency Service register of disqualified directors.

    uv run python scripts/scrape_disqualified_directors.py

Wraps https://github.com/maxharlow/scrape-disqualified-directors. The
upstream scraper hits ``insolvencydirect.bis.gov.uk`` sequentially
(``maxParallel: 1``) and writes ``disqualified-directors.csv`` to
CWD; this wrapper runs it in a managed workdir under
``data/raw/scrapers/disqualified-directors/`` so re-runs don't clutter
the project root.

After scraping, run ``scripts/ingest_uk_disqualified_directors.py`` to
project the CSV into our parquet schema for joining against the
person table.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import ensure_dirs
from shellnet.sources import scrapers

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Copy the scraper output CSV to this path. Default: leave in workdir.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    src = scrapers.run(
        "disqualified-directors",
        entry_script="disqualified-directors.js",
        output_csv_name="disqualified-directors.csv",
    )
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(src.read_bytes())
        typer.echo(f"Wrote: {out}")
    else:
        typer.echo(f"Wrote: {src}")


if __name__ == "__main__":
    app()
