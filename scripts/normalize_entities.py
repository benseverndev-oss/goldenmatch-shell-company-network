"""Re-apply normalization to all interim parquet files in place.

    uv run python scripts/normalize_entities.py

Useful after tweaking ``shellnet/normalize.py`` without re-ingesting raw
data. Rewrites each interim parquet listed in `_RENORM_PLAN`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.normalize import (
    normalize_address_text,
    normalize_company_name,
    normalize_jurisdiction,
)
from shellnet.paths import INTERIM_DIR

app = typer.Typer(add_completion=False, no_args_is_help=False)

# Maps file → which columns to renormalize.
_RENORM_PLAN: dict[str, dict[str, str]] = {
    "icij_entities.parquet": {
        "name": "normalized_name",
        "jurisdiction_raw": "jurisdiction",
        "address_raw": "normalized_address",
    },
    "opencorporates_companies.parquet": {
        "name": "normalized_name",
        "jurisdiction_raw": "jurisdiction",
        "address_raw": "normalized_address",
    },
    "gleif_entities.parquet": {
        "name": "normalized_name",
        "jurisdiction_raw": "jurisdiction",
        "legal_address_raw": "normalized_legal_address",
        "headquarters_address_raw": "normalized_headquarters_address",
    },
}


def _norm_for(target_col: str):
    if target_col == "normalized_name":
        return normalize_company_name
    if target_col == "jurisdiction":
        return normalize_jurisdiction
    return normalize_address_text


@app.command()
def main(
    interim_dir: Path = typer.Option(INTERIM_DIR, help="Override the interim-parquet directory."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    for filename, plan in _RENORM_PLAN.items():
        path = interim_dir / filename
        if not path.exists():
            typer.echo(f"skip (missing): {path}")
            continue
        df = pl.read_parquet(path)
        cols_to_replace = []
        for source_col, target_col in plan.items():
            if source_col not in df.columns:
                continue
            fn = _norm_for(target_col)
            cols_to_replace.append(
                pl.col(source_col).map_elements(fn, return_dtype=pl.Utf8).alias(target_col)
            )
        if cols_to_replace:
            df = df.with_columns(cols_to_replace)
            df.write_parquet(path)
            typer.echo(f"renormalized: {path}")


if __name__ == "__main__":
    app()
