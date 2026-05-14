"""Ingest OpenCorporates search results for one query.

Usage:
    uv run python scripts/ingest_opencorporates.py \
        --query "Acme Holdings" --jurisdiction gb --limit 100

Set OPENCORPORATES_API_KEY in your environment for higher rate limits.
Use --dry-run to exercise the pipeline without making any HTTP calls.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import INTERIM_DIR, ensure_dirs
from shellnet.sources import opencorporates

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    query: str = typer.Option(..., "--query", "-q", help="Search string."),
    jurisdiction: str = typer.Option(
        "", "--jurisdiction", "-j", help="ISO country code, optional."
    ),
    limit: int = typer.Option(100, "--limit", "-n", help="Max companies to fetch."),
    per_page: int = typer.Option(
        opencorporates.DEFAULT_PER_PAGE,
        "--per-page",
        help="Results per OpenCorporates API page.",
    ),
    sleep_seconds: float = typer.Option(
        opencorporates.DEFAULT_SLEEP_SECONDS,
        "--sleep",
        help="Pause between paginated requests, in seconds.",
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip the on-disk response cache."),
    dry_run: bool = typer.Option(False, "--dry-run", help="No HTTP; useful for plumbing tests."),
    out_dir: Path = typer.Option(INTERIM_DIR, help="Where to write interim parquet."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out = opencorporates.ingest_query(
        query,
        jurisdiction=(jurisdiction or None),
        limit=limit,
        per_page=per_page,
        sleep_seconds=sleep_seconds,
        use_cache=not no_cache,
        dry_run=dry_run,
        out_dir=out_dir,
    )
    typer.echo(f"Wrote/updated: {out}")


if __name__ == "__main__":
    app()
