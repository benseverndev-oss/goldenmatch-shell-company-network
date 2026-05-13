"""Build the canonical company table that GoldenMatch consumes.

We expect interim parquet files from each source with a (mostly) common
shape. This module loads what's available, harmonises columns, and emits
``data/processed/company_entities.parquet``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from shellnet.normalize import (
    normalize_address_text,
    normalize_company_name,
    normalize_jurisdiction,
)
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR

log = logging.getLogger(__name__)

# Columns every row in the unified company table must have. Sources that
# don't carry a particular value contribute null.
UNIFIED_COLUMNS: tuple[str, ...] = (
    "source",
    "source_id",
    "name",
    "normalized_name",
    "jurisdiction",
    "company_number",
    "lei",
    "status",
    "legal_form",
    "address_raw",
    "normalized_address",
)


def _ensure_columns(df: pl.DataFrame, required: tuple[str, ...]) -> pl.DataFrame:
    """Add any missing columns as null Utf8 so concatenation stays clean."""
    missing = [c for c in required if c not in df.columns]
    if not missing:
        return df.select(list(required))
    df = df.with_columns([pl.lit(None, dtype=pl.Utf8).alias(c) for c in missing])
    return df.select(list(required))


def _load_icij(interim: Path) -> pl.DataFrame | None:
    path = interim / "icij_entities.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    return _ensure_columns(
        df.with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("company_number"),
            pl.lit(None, dtype=pl.Utf8).alias("lei"),
        ),
        UNIFIED_COLUMNS,
    )


def _load_opencorporates(interim: Path) -> pl.DataFrame | None:
    path = interim / "opencorporates_companies.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    return _ensure_columns(
        df.with_columns(pl.lit(None, dtype=pl.Utf8).alias("lei")),
        UNIFIED_COLUMNS,
    )


def _load_gleif(interim: Path) -> pl.DataFrame | None:
    path = interim / "gleif_entities.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    return _ensure_columns(
        df.with_columns(
            pl.col("legal_address_raw").alias("address_raw"),
            pl.col("normalized_legal_address").alias("normalized_address"),
            pl.lit(None, dtype=pl.Utf8).alias("company_number"),
        ),
        UNIFIED_COLUMNS,
    )


def _load_opensanctions(interim: Path) -> pl.DataFrame | None:
    """Pull only Company-shaped OpenSanctions rows into the company table."""
    path = interim / "opensanctions_entities.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path).filter(
        pl.col("entity_schema").is_in(["Company", "Organization", "LegalEntity"])
    )
    if df.height == 0:
        return None
    return _ensure_columns(
        df.with_columns(
            pl.col("jurisdictions").list.first().alias("jurisdiction"),
            pl.col("addresses_raw").list.first().alias("address_raw"),
            pl.col("normalized_addresses").list.first().alias("normalized_address"),
            pl.col("identifiers").list.first().alias("company_number"),
            pl.lit(None, dtype=pl.Utf8).alias("lei"),
            pl.lit(None, dtype=pl.Utf8).alias("legal_form"),
            pl.lit(None, dtype=pl.Utf8).alias("status"),
        ),
        UNIFIED_COLUMNS,
    )


def build_unified_table(
    interim_dir: Path = INTERIM_DIR,
    out_dir: Path = PROCESSED_DIR,
) -> Path:
    """Concatenate all available source tables into one company table.

    Re-normalises ``normalized_name`` / ``jurisdiction`` / ``normalized_address``
    even if the source already filled them, so a config tweak in
    :mod:`shellnet.normalize` propagates without re-ingestion.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[pl.DataFrame] = []
    for loader in (_load_icij, _load_opencorporates, _load_gleif, _load_opensanctions):
        df = loader(interim_dir)
        if df is not None and df.height > 0:
            parts.append(df)
            log.info("Loaded %d rows from %s", df.height, loader.__name__)
    bods_path = interim_dir / "uk_psc_entities.parquet"
    if bods_path.exists():
        bods_df = pl.read_parquet(bods_path)
        if bods_df.height:
            parts.append(bods_df.select(list(UNIFIED_COLUMNS)))
            log.info("Loaded %d rows from uk_psc_entities (BODS)", bods_df.height)

    if not parts:
        log.warning("No source tables found in %s. Running adapters first?", interim_dir)
        empty = pl.DataFrame(schema={c: pl.Utf8 for c in UNIFIED_COLUMNS})
        out = out_dir / "company_entities.parquet"
        empty.write_parquet(out)
        return out

    df = pl.concat(parts, how="vertical_relaxed")
    df = df.with_columns(
        pl.col("name").map_elements(normalize_company_name, return_dtype=pl.Utf8).alias(
            "normalized_name"
        ),
        pl.col("jurisdiction").map_elements(normalize_jurisdiction, return_dtype=pl.Utf8).alias(
            "jurisdiction"
        ),
        pl.col("address_raw").map_elements(normalize_address_text, return_dtype=pl.Utf8).alias(
            "normalized_address"
        ),
    )
    # Stable cross-source row id so GoldenMatch has a primary key it trusts.
    df = df.with_columns(
        (pl.col("source") + pl.lit(":") + pl.col("source_id")).alias("entity_uid")
    ).select(["entity_uid", *UNIFIED_COLUMNS])

    out = out_dir / "company_entities.parquet"
    df.write_parquet(out)
    log.info("Wrote unified company table (%d rows) to %s", df.height, out)
    return out
