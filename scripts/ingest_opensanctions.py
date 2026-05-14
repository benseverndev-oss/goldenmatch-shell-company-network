"""Ingest an OpenSanctions FtM JSON / NDJSON export.

Usage:
    uv run python scripts/ingest_opensanctions.py --input data/raw/opensanctions/entities.ftm.json
    uv run python scripts/ingest_opensanctions.py --download   # only with OPENSANCTIONS_DATASET_URL set

Treats this source as enrichment, not ground truth — see docs/methodology.md.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import INTERIM_DIR, ensure_dirs
from shellnet.sources import opensanctions

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    input: Path = typer.Option(None, "--input", "-i", help="Local export file."),
    download: bool = typer.Option(
        False, "--download", help="Fetch from OPENSANCTIONS_DATASET_URL first."
    ),
    out_dir: Path = typer.Option(INTERIM_DIR, help="Where to write interim parquet."),
    schemas: str | None = typer.Option(
        None,
        "--schemas",
        help="Comma-separated FtM schema filter (e.g. 'Person,Company,Organization,LegalEntity'). "
        "Default: keep everything. Useful on the 2.7 GB consolidated 'default' collection "
        "where you don't need vehicles, addresses-as-entities, etc.",
    ),
    batch_size: int = typer.Option(
        50_000,
        "--batch-size",
        help="How many FtM records to accumulate per parquet write. Lower if memory is tight.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    target = input
    if download:
        target = opensanctions.download()
    schema_tuple = tuple(s.strip() for s in schemas.split(",")) if schemas else None
    out = opensanctions.ingest(
        input_path=target,
        out_dir=out_dir,
        schemas=schema_tuple,
        batch_size=batch_size,
    )
    if out is None:
        raise typer.Exit(code=1)
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
