"""Build first-pass RU and US shortlists for the reconcile fan-outs.

Reads ``processed/sanctions_overlay.parquet`` and emits two CSVs that
``reconcile_ru_companies.py`` / ``reconcile_sec_filings.py`` can consume:

- ``ru_shortlist.csv``  : column ``CompanyName``, ru-jurisdiction
  Company/Organization/LegalEntity rows that appear on a single
  government sanction list AND are absent from OFAC SDN (the
  Sovcomflot-style evasion signal documented in CLAUDE.md and the
  Layer 1 design notes).
- ``us_shortlist.csv``  : column ``name``, us-jurisdiction
  Company/Organization/LegalEntity rows (no n_datasets filter; SEC
  EDGAR will return empty for non-issuers, that's OK).

Capped at ``--limit`` per shortlist (default 50) because the reconcile
fan-outs are sequential and the FTS / SEC endpoints are rate-limited.
Bump the limit once a first pass confirms the wiring + hit rate.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import DATA_DIR, PROCESSED_DIR, ensure_dirs

# Reconcile allowlist entries read from /data/reports/generated; REPORTS_DIR
# from paths.py resolves to /app/reports/generated (ephemeral on Railway), so
# anchor on DATA_DIR instead.
_RAILWAY_REPORTS = DATA_DIR / "reports" / "generated"

app = typer.Typer(add_completion=False, no_args_is_help=False)

_COMPANY_SCHEMAS = ("Company", "Organization", "LegalEntity")


def _filter_ru(df: pl.DataFrame) -> pl.DataFrame:
    return df.filter(
        pl.col("jurisdictions").str.contains("ru")
        & pl.col("schema").is_in(_COMPANY_SCHEMAS)
        & (pl.col("n_datasets") == 1)
        & ~pl.col("datasets").str.contains("us_ofac_sdn")
        & (pl.col("caption").str.len_chars() > 0)
    )


def _filter_us(df: pl.DataFrame) -> pl.DataFrame:
    return df.filter(
        pl.col("jurisdictions").str.contains("us")
        & pl.col("schema").is_in(_COMPANY_SCHEMAS)
        & (pl.col("caption").str.len_chars() > 0)
    )


@app.command()
def main(
    overlay: Path = typer.Option(
        PROCESSED_DIR / "sanctions_overlay.parquet",
        "--overlay",
        help="Sanctions overlay parquet from build_sanctions_overlay.py.",
    ),
    out_dir: Path = typer.Option(
        _RAILWAY_REPORTS,
        "--out-dir",
        help="Directory to write ru_shortlist.csv and us_shortlist.csv.",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        help="Max rows per shortlist. Reconcile fan-outs are slow; keep small for first pass.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not overlay.exists():
        raise typer.BadParameter(
            f"sanctions overlay missing: {overlay}. Run build_sanctions_overlay.py first."
        )

    df = pl.read_parquet(overlay)

    ru = _filter_ru(df).unique(subset=["caption"]).head(limit)
    ru_out = out_dir / "ru_shortlist.csv"
    ru.select(pl.col("caption").alias("CompanyName"), pl.col("os_id")).write_csv(ru_out)
    typer.echo(f"Wrote {ru.height} rows to {ru_out}")

    us = _filter_us(df).unique(subset=["caption"]).head(limit)
    us_out = out_dir / "us_shortlist.csv"
    us.select(pl.col("caption").alias("name"), pl.col("os_id")).write_csv(us_out)
    typer.echo(f"Wrote {us.height} rows to {us_out}")


if __name__ == "__main__":
    app()
