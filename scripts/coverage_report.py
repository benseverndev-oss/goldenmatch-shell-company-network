"""Write a Markdown column-coverage report for the current interim/processed data.

Default target list covers every parquet the four adapters and the
candidate-table builder can emit. Missing files are flagged in the report
but don't fail the run.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, REPORTS_DIR, ensure_dirs
from shellnet.reporting.coverage import render_report

app = typer.Typer(add_completion=False, no_args_is_help=False)


def _default_targets() -> list[Path]:
    return [
        INTERIM_DIR / "icij_entities.parquet",
        INTERIM_DIR / "icij_addresses.parquet",
        INTERIM_DIR / "icij_edges.parquet",
        INTERIM_DIR / "icij_officers.parquet",
        INTERIM_DIR / "icij_intermediaries.parquet",
        INTERIM_DIR / "opencorporates_companies.parquet",
        INTERIM_DIR / "gleif_entities.parquet",
        INTERIM_DIR / "opensanctions_entities.parquet",
        PROCESSED_DIR / "company_entities.parquet",
        PROCESSED_DIR / "address_entities.parquet",
        PROCESSED_DIR / "person_entities.parquet",
    ]


@app.command()
def main(
    out: Path = typer.Option(REPORTS_DIR / "coverage.md"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    report = render_report(_default_targets())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    typer.echo(f"Wrote {out} ({len(report.splitlines())} lines)")


if __name__ == "__main__":
    app()
