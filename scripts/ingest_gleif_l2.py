"""Ingest the OpenOwnership GLEIF L2 BODS parquet bundle.

    uv run python scripts/ingest_gleif_l2.py \\
        --input data/raw/openownership/gleif_bods.zip

Writes ``data/interim/gleif_l2_relationships.parquet`` — corporate
parent/child ownership edges with share %, type, and dates. Consumed
downstream by the graph layer.
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
        DATA_DIR / "raw" / "openownership" / "gleif_bods.zip",
        "--input",
        "-i",
        help="Path to the OpenOwnership GLEIF L2 BODS zip bundle.",
    ),
    out_dir: Path = typer.Option(
        INTERIM_DIR,
        "--out-dir",
        help="Where to write `gleif_l2_relationships.parquet`.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    written = bods.ingest_gleif_l2(zip_path=zip_path, out_dir=out_dir)
    if not written:
        raise typer.Exit(code=1)
    for kind, path in written.items():
        typer.echo(f"Wrote {kind}: {path}")


if __name__ == "__main__":
    app()
