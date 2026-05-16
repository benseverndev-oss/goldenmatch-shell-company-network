"""Scrape the UK MPs' Register of Members' Financial Interests.

    uv run python scripts/scrape_mp_interests.py

Wraps https://github.com/maxharlow/scrape-members-financial-interests.
The upstream scraper caches per-URL SHA1s under ``cache/`` in CWD;
this wrapper runs it in a stable workdir under
``data/raw/scrapers/members-financial-interests/`` so the cache
survives across runs and we don't re-hit Parliament's site needlessly.

The output is intended as a PEP / political-exposure overlay against
investigative shortlists; we don't (yet) bulk-ingest it into the
unified person table.
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
        "members-financial-interests",
        entry_script="members-financial-interests.js",
        output_csv_name="members-financial-interests.csv",
    )
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(src.read_bytes())
        typer.echo(f"Wrote: {out}")
    else:
        typer.echo(f"Wrote: {src}")


if __name__ == "__main__":
    app()
