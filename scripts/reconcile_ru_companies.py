"""Enrich a CSV of Russian company names / numbers via FTS + ITSoft.

Two-step fan-out:

    names -> numbers (FTS)        : ru-company-names-to-ru-company-numbers
    numbers -> details (ITSoft)   : ru-company-numbers-to-company-details

Both APIs are public / no credentials. Useful for Sovcomflot-adjacent
shells where the OS sanction lists give us a name but not an OGRN/INN
to cross-reference against UK/Cyprus filings.

    uv run python scripts/reconcile_ru_companies.py \\
        --input /data/reports/generated/ru_shortlist.csv \\
        --name-field CompanyName \\
        --out /data/reports/generated/ru_shortlist_enriched.csv
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
    name_field: str = typer.Option(
        "CompanyName",
        "--name-field",
        help="Column name holding Russian company names. Used for FTS lookup.",
    ),
    out: Path = typer.Option(..., "--out", "-o"),
    skip_details: bool = typer.Option(
        False,
        "--skip-details",
        help="Stop after names→numbers; don't run the ITSoft details step.",
    ),
    cache_dir: Path = typer.Option(
        DATA_DIR / "interim" / "reconcile_cache" / "ru",
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

    intermediate = out.with_suffix(".numbers.csv")
    reconcile.run(
        "ru-company-names-to-ru-company-numbers",
        input,
        intermediate,
        params={"companyNameField": name_field},
        cache_dir=cache_dir,
    )
    if skip_details:
        intermediate.replace(out)
        typer.echo(f"Wrote: {out}")
        return

    # reconcile's names→numbers reconciler appends a column called
    # `ru-company-numbers-to-company-details` is keyed off — the
    # output convention is to use `companyNumber` for the new column.
    reconcile.run(
        "ru-company-numbers-to-company-details",
        intermediate,
        out,
        params={"companyNumberField": "companyNumber"},
        cache_dir=cache_dir,
    )
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
