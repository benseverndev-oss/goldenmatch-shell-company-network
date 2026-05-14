"""Build the unified company table from all available interim parquets.

    uv run python scripts/build_candidate_tables.py

Tolerates missing sources — if you've only ingested ICIJ so far, you'll
still get a (smaller) processed table out the other end. Output lands
at ``data/processed/company_entities.parquet``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.matching.company_features import build_unified_table
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    interim_dir: Path = typer.Option(INTERIM_DIR, help="Override the interim-parquet directory."),
    out_dir: Path = typer.Option(PROCESSED_DIR, help="Where to write `company_entities.parquet`."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out = build_unified_table(interim_dir=interim_dir, out_dir=out_dir)
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
