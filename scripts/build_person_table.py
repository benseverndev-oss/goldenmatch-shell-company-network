"""Build the unified person table from ICIJ officers/intermediaries + OpenSanctions Persons."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.matching.person_features import build_person_table
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    interim_dir: Path = typer.Option(INTERIM_DIR),
    out_dir: Path = typer.Option(PROCESSED_DIR),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out = build_person_table(interim_dir=interim_dir, out_dir=out_dir)
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
