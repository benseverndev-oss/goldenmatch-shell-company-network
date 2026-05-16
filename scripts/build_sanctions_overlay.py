"""Build the cross-list sanctions overlay parquet.

    uv run python scripts/build_sanctions_overlay.py
    uv run python scripts/build_sanctions_overlay.py --external data/raw/sanctions_recon/records.parquet

Without ``--external``, recomputes the overlay from our existing
OpenSanctions interim parquet using the curated government-sanction
dataset filter (see ``sanctions_overlay.SANCTION_DATASET_PREFIXES``).

With ``--external``, left-joins a ``records.parquet`` produced by the
sister repo https://github.com/benseverndev-oss/goldenmatch-sanctions-reconciliation
and prefers its aggregation columns.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs
from shellnet.sources import sanctions_overlay

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    os_parquet: Path = typer.Option(
        INTERIM_DIR / "opensanctions_entities.parquet",
        "--os-parquet",
        help="Path to the OpenSanctions interim parquet.",
    ),
    external: Path | None = typer.Option(
        None,
        "--external",
        help="Optional external records.parquet from goldenmatch-sanctions-reconciliation.",
    ),
    out: Path = typer.Option(
        PROCESSED_DIR / "sanctions_overlay.parquet",
        "--out",
        help="Output parquet path.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_path = sanctions_overlay.build(
        os_parquet=os_parquet,
        external_parquet=external,
        out_path=out,
    )
    typer.echo(f"Wrote: {out_path}")


if __name__ == "__main__":
    app()
