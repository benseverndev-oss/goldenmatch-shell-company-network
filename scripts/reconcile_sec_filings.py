"""Enrich a CSV of company names with SEC EDGAR CIKs + recent filings.

    uv run python scripts/reconcile_sec_filings.py \\
        --input /data/reports/generated/us_shortlist.csv \\
        --name-field name \\
        --filing-type 10-K \\
        --out /data/reports/generated/us_shortlist_sec.csv

Two-step: names → CIKs (free, no auth) → CIK filings of a given type.
Useful for entities that GLEIF places in the US but where we don't
yet have a registrant identifier.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.paths import DATA_DIR, ensure_dirs
from shellnet.sources import reconcile

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    input: Path = typer.Option(..., "--input", "-i"),
    name_field: str = typer.Option("name", "--name-field"),
    filing_type: str = typer.Option(
        "10-K", "--filing-type", help="SEC form type, e.g. 10-K, 10-Q, 8-K, SC 13D."
    ),
    out: Path = typer.Option(..., "--out", "-o"),
    cache_dir: Path = typer.Option(
        DATA_DIR / "interim" / "reconcile_cache" / "sec",
        "--cache-dir",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out.parent.mkdir(parents=True, exist_ok=True)

    intermediate = out.with_suffix(".ciks.csv")
    reconcile.run(
        "names-to-sec-ciks",
        input,
        intermediate,
        params={"nameField": name_field},
        cache_dir=cache_dir,
    )
    reconcile.run(
        "sec-ciks-to-sec-filings",
        intermediate,
        out,
        params={"cikField": "cik", "filingType": filing_type},
        cache_dir=cache_dir,
    )
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
