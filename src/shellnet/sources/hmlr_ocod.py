"""Project HM Land Registry OCOD (Overseas Companies Ownership Data)
CSV into a parquet shaped like our other corporate-ownership sources.

OCOD lists every UK property (England + Wales) owned by an
overseas-incorporated company. Each row is one Title Number; a title
can have up to 4 co-proprietors. We unpivot the 4-proprietor columns
into one row per (title, proprietor) pair so downstream joins and
filters are simple.

Source columns (per HMLR's published schema, 2024+ format)::

    Title Number
    Tenure
    Property Address
    District
    County
    Region
    Postcode
    Multiple Address Indicator
    Price Paid
    Proprietor Name (1..4)
    Company Registration No. (1..4)
    Proprietorship Category (1..4)
    Country Incorporated (1..4)
    Proprietor (1..4) Address (1..3)
    Date Proprietor Added
    Additional Proprietor Indicator
    Change Indicator
    Change Date

Output schema (one row per non-null proprietor)::

    title_number               str
    property_address           str
    postcode                   str
    price_paid                 str
    tenure                     str
    proprietor_index           i32   (1..4)
    proprietor_name            str
    normalized_name            str
    proprietor_address         str
    normalized_address         str
    company_registration_no    str
    country_incorporated       str   ISO-ish country name as HMLR records it
    proprietorship_category    str
    date_proprietor_added      str   ISO date
    source                     str   "hmlr_ocod"
    source_label               str   "HM Land Registry Overseas Companies Ownership Data"
    snapshot_date              str   the file's release month, e.g. "2024-Q4"

Heavy-data note: OCOD is ~80 MB CSV, ~150k rows post-unpivot. Easily
fits in memory but we use ``pl.scan_csv`` for consistency with the
rest of the pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from shellnet.normalize import normalize_address_text, normalize_company_name

log = logging.getLogger(__name__)

SOURCE = "hmlr_ocod"
SOURCE_LABEL = "HM Land Registry Overseas Companies Ownership Data"


def _unpivot_proprietors(df: pl.DataFrame) -> pl.DataFrame:
    """Convert OCOD's 4 proprietor columns per row into 4x rows.

    For each proprietor index 1..4 we create a row carrying that
    proprietor's name + address + registration + country. Rows where
    the proprietor name is null are dropped.
    """

    blocks: list[pl.DataFrame] = []
    for i in (1, 2, 3, 4):
        block = df.select(
            pl.col("Title Number").alias("title_number"),
            pl.col("Property Address").alias("property_address"),
            pl.col("Postcode").alias("postcode"),
            pl.col("Price Paid").alias("price_paid"),
            pl.col("Tenure").alias("tenure"),
            pl.col("Date Proprietor Added").alias("date_proprietor_added"),
            pl.lit(i, dtype=pl.Int32).alias("proprietor_index"),
            pl.col(f"Proprietor Name ({i})").alias("proprietor_name"),
            pl.col(f"Company Registration No. ({i})").alias("company_registration_no"),
            pl.col(f"Proprietorship Category ({i})").alias("proprietorship_category"),
            pl.col(f"Country Incorporated ({i})").alias("country_incorporated"),
            # OCOD stores up to 3 address lines per proprietor; we
            # concat them with comma separators (matching HMLR's own
            # display convention).
            pl.concat_str(
                [
                    pl.col(f"Proprietor ({i}) Address (1)").fill_null(""),
                    pl.col(f"Proprietor ({i}) Address (2)").fill_null(""),
                    pl.col(f"Proprietor ({i}) Address (3)").fill_null(""),
                ],
                separator=", ",
                ignore_nulls=False,
            )
            .str.replace_all(r"(, ){2,}", ", ")
            .str.strip_chars(", ")
            .alias("proprietor_address"),
        ).filter(pl.col("proprietor_name").is_not_null())
        blocks.append(block)

    return pl.concat(blocks, how="vertical")


def ingest(csv_path: Path, *, out: Path, snapshot_date: str | None = None) -> Path:
    """Read the OCOD CSV, unpivot, normalize, write parquet."""

    if not csv_path.exists():
        raise FileNotFoundError(f"OCOD CSV missing: {csv_path}")

    log.info("reading %s", csv_path)
    df = pl.read_csv(
        csv_path,
        infer_schema_length=0,  # all columns as Utf8 — preserves leading zeros etc.
        try_parse_dates=False,
    )
    log.info("  raw rows: %d", df.height)

    unpivoted = _unpivot_proprietors(df)
    log.info("  unpivoted rows (one per proprietor): %d", unpivoted.height)

    normalized = unpivoted.with_columns(
        pl.col("proprietor_name")
        .map_elements(normalize_company_name, return_dtype=pl.String)
        .alias("normalized_name"),
        pl.col("proprietor_address")
        .map_elements(normalize_address_text, return_dtype=pl.String)
        .alias("normalized_address"),
        pl.lit(SOURCE).alias("source"),
        pl.lit(SOURCE_LABEL).alias("source_label"),
        pl.lit(snapshot_date or "").alias("snapshot_date"),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_parquet(out)
    log.info("wrote %d rows to %s", normalized.height, out)
    return out
