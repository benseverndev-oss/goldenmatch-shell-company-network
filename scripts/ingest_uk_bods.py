"""Ingest an OpenOwnership UK BODS parquet bundle.

Downloads to /data/raw/openownership/uk_bods.zip via /fetch-url first
(or expects the file already to be there). Writes:

  - /data/interim/uk_psc_persons.parquet
  - /data/interim/uk_psc_entities.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import DATA_DIR, INTERIM_DIR, ensure_dirs
from shellnet.sources import bods

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


@app.command()
def main(
    zip_path: Path = typer.Option(
        DATA_DIR / "raw" / "openownership" / "uk_bods.zip",
        "--input", "-i",
        help="Local ZIP file (UK BODS parquet bundle).",
    ),
    out_dir: Path = typer.Option(INTERIM_DIR, "--out-dir"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    written = bods.ingest(zip_path=zip_path, out_dir=out_dir)
    if not written:
        raise typer.Exit(code=1)
    for kind, path in written.items():
        typer.echo(f"Wrote {kind}: {path}")


if __name__ == "__main__":
    app()
