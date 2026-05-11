"""Build the company/officer/address graph and dump a JSON summary.

Reads from data/processed/ and data/interim/ — i.e. it expects the ingest
+ candidate-table scripts to have run first. Outputs reports/generated/
graph_smoke_summary.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from shellnet.graph.build import build_graph, summarize, write_summary
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    processed_dir: Path = typer.Option(PROCESSED_DIR),
    interim_dir: Path = typer.Option(INTERIM_DIR),
    out_path: Path = typer.Option(None, help="Override the summary output path."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    g = build_graph(processed_dir=processed_dir, interim_dir=interim_dir)
    out = write_summary(g, out_path=out_path)
    typer.echo(json.dumps(summarize(g), indent=2))
    typer.echo(f"\nWrote: {out}")


if __name__ == "__main__":
    app()
