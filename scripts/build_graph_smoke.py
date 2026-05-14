"""Build the company/officer/address graph and dump a JSON summary.

    uv run python scripts/build_graph_smoke.py

Reads from data/processed/ and data/interim/ — i.e. it expects the ingest
+ candidate-table scripts to have run first. Outputs reports/generated/
graph_smoke_summary.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from shellnet.graph.build import add_same_as_edges, build_graph, summarize, write_summary
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, REPORTS_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    processed_dir: Path = typer.Option(
        PROCESSED_DIR, help="Override the processed-parquet directory."
    ),
    interim_dir: Path = typer.Option(INTERIM_DIR, help="Override the interim-parquet directory."),
    out_path: Path = typer.Option(None, help="Override the summary output path."),
    overlay_same_as: bool = typer.Option(
        True,
        "--overlay-same-as/--no-overlay-same-as",
        help="Layer GoldenMatch same_as edges from reports/generated/ if present.",
    ),
    run_name: str = typer.Option(
        "company",
        "--run-name",
        help="GoldenMatch run name whose same_as edges to overlay (matches the run-name passed to `run_goldenmatch_full.py`).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    g = build_graph(processed_dir=processed_dir, interim_dir=interim_dir)
    if overlay_same_as:
        add_same_as_edges(g, output_dir=REPORTS_DIR, run_name=run_name)
    out = write_summary(g, out_path=out_path)
    typer.echo(json.dumps(summarize(g), indent=2))
    typer.echo(f"\nWrote: {out}")


if __name__ == "__main__":
    app()
