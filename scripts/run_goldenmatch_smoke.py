"""Sanity-check that the GoldenMatch config loads against the unified table.

    uv run python scripts/run_goldenmatch_smoke.py

This is intentionally cheap: it loads the company table, loads the YAML
config, and prints a small summary. Heavy matching runs should go through
the GoldenMatch CLI directly so we don't reinvent its UX here.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from shellnet.matching.goldenmatch_runner import default_config_path, run_match

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    config: Path = typer.Option(
        None,
        "--config",
        "-c",
        help="GoldenMatch YAML config path (defaults to the company config).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    summary = run_match(config_path=config or default_config_path())
    typer.echo(json.dumps(summary, indent=2))


if __name__ == "__main__":
    app()
