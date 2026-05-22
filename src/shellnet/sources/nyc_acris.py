"""NYC ACRIS source — Manhattan-and-boroughs property transfer records.

ACRIS = Automated City Register Information System. Run by NYC
Department of Finance. Free via NYC Open Data (Socrata). Five
related datasets:

* Master  (real-property-master)    — one row per recorded document
* Parties (real-property-parties)   — grantor + grantee names per doc
* Legals  (real-property-legals)    — property addresses per doc
* References + Remarks (skipped)    — not needed for entity work

We download three CSVs from NYC Open Data's CSV export endpoints,
normalise the columns we care about (document_id, grantor/grantee
names, address, doc_type, recorded_datetime), and write one parquet
per source.

The probe layer joins them on document_id to ask: "which named
grantees in NYC ACRIS name-match against ICIJ Offshore Leaks or
OFAC SDN?"

Records: ~13M parties, ~17M legals, ~10M master since 1966.
Filtered to deeds + foreign-LLC-pattern grantees, the working set
shrinks to ~500k rows.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

log = logging.getLogger(__name__)

# NYC Open Data CSV export endpoints
NYCOD = "https://data.cityofnewyork.us/api/views"
ACRIS_MASTER_URL = f"{NYCOD}/bnx9-e6tj/rows.csv?accessType=DOWNLOAD"
ACRIS_PARTIES_URL = f"{NYCOD}/636b-3b5g/rows.csv?accessType=DOWNLOAD"
ACRIS_LEGALS_URL = f"{NYCOD}/8h5j-fqxa/rows.csv?accessType=DOWNLOAD"


def project_parties(parties_csv: Path, out: Path) -> int:
    """Project the ACRIS Parties CSV down to (doc_id, party_type, name,
    address, normalized_name). Party types in ACRIS:

       1 = Party 1 (typically grantor / seller)
       2 = Party 2 (typically grantee / buyer)
       3 = Other party (mortgagee, etc.)
    """

    log.info("projecting ACRIS Parties %s -> %s", parties_csv, out)
    # ACRIS Parties columns (per NYC Open Data):
    # DOCUMENT ID, RECORD TYPE, PARTY TYPE, NAME, ADDRESS 1, ADDRESS 2,
    # COUNTRY, CITY, STATE, ZIP, GOOD THROUGH DATE
    lf = pl.scan_csv(
        parties_csv,
        has_header=True,
        ignore_errors=True,
        infer_schema_length=2000,
        null_values=["", "NULL"],
    )
    df = lf.select(
        pl.col("DOCUMENT ID").cast(pl.Utf8).alias("doc_id"),
        pl.col("PARTY TYPE").cast(pl.Utf8).alias("party_type"),
        pl.col("NAME").cast(pl.Utf8).alias("name"),
        pl.col("ADDRESS 1").cast(pl.Utf8).fill_null("").alias("address_1"),
        pl.col("CITY").cast(pl.Utf8).fill_null("").alias("city"),
        pl.col("STATE").cast(pl.Utf8).fill_null("").alias("state"),
        pl.col("COUNTRY").cast(pl.Utf8).fill_null("").alias("country"),
        pl.col("ZIP").cast(pl.Utf8).fill_null("").alias("zip"),
    ).collect()
    # Normalize the party name for matching
    df = df.with_columns(
        pl.col("name")
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .alias("normalized_name")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)
    log.info("  wrote %d party rows", df.height)
    return df.height


def project_master(master_csv: Path, out: Path) -> int:
    """Project ACRIS Master CSV — one row per recorded document.

    We keep: doc_id, doc_type, doc_date, doc_amount, recorded_datetime.
    """

    log.info("projecting ACRIS Master %s -> %s", master_csv, out)
    lf = pl.scan_csv(
        master_csv,
        has_header=True,
        ignore_errors=True,
        infer_schema_length=2000,
        null_values=["", "NULL"],
    )
    df = lf.select(
        pl.col("DOCUMENT ID").cast(pl.Utf8).alias("doc_id"),
        pl.col("DOC. TYPE").cast(pl.Utf8).alias("doc_type"),
        pl.col("DOC. DATE").cast(pl.Utf8).alias("doc_date"),
        pl.col("DOC. AMOUNT").cast(pl.Utf8).alias("doc_amount_usd"),
        pl.col("RECORDED / FILED").cast(pl.Utf8).alias("recorded_datetime"),
    ).collect()
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)
    log.info("  wrote %d master rows", df.height)
    return df.height


def project_legals(legals_csv: Path, out: Path) -> int:
    """Project ACRIS Legals CSV — property address per document."""

    log.info("projecting ACRIS Legals %s -> %s", legals_csv, out)
    lf = pl.scan_csv(
        legals_csv,
        has_header=True,
        ignore_errors=True,
        infer_schema_length=2000,
        null_values=["", "NULL"],
    )
    df = lf.select(
        pl.col("DOCUMENT ID").cast(pl.Utf8).alias("doc_id"),
        pl.col("BOROUGH").cast(pl.Utf8).alias("borough"),
        pl.col("BLOCK").cast(pl.Utf8).alias("block"),
        pl.col("LOT").cast(pl.Utf8).alias("lot"),
        pl.col("STREET NUMBER").cast(pl.Utf8).fill_null("").alias("street_number"),
        pl.col("STREET NAME").cast(pl.Utf8).fill_null("").alias("street_name"),
        pl.col("UNIT").cast(pl.Utf8).fill_null("").alias("unit"),
    ).collect()
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)
    log.info("  wrote %d legals rows", df.height)
    return df.height
