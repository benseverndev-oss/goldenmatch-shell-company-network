"""Entry point for the ``shellnet`` console script.

We deliberately keep the in-package CLI tiny — the real ingest / build
pipelines live in ``scripts/`` so they're easy to inspect and modify.
This top-level command just points users at them.
"""

from __future__ import annotations

import typer

app = typer.Typer(add_completion=False, help="GoldenMatch shell-company case study toolkit.")


@app.command()
def info() -> None:
    """Print a pointer to the script-based commands."""
    typer.echo(
        "shellnet is a library + scripts. Use the per-task scripts:\n"
        "  scripts/ingest_icij.py\n"
        "  scripts/ingest_opencorporates.py\n"
        "  scripts/ingest_gleif.py\n"
        "  scripts/ingest_opensanctions.py\n"
        "  scripts/build_candidate_tables.py\n"
        "  scripts/run_goldenmatch_smoke.py\n"
        "  scripts/build_graph_smoke.py\n"
        "Or run `just --list` for the full menu."
    )


if __name__ == "__main__":
    app()
