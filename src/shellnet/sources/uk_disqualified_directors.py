"""UK disqualified-directors adapter.

Parses the CSV produced by ``scripts/scrape_disqualified_directors.py``
(thin wrap over https://github.com/maxharlow/scrape-disqualified-directors,
which scrapes ``insolvencydirect.bis.gov.uk``).

Upstream columns:
    caseNumber, companyName, personName, dateOfBirth, dateOrderStarts,
    disqualificationLength, lastKnownAddress, informationCorrectAsOf,
    conduct

We project into a parquet keyed by ``caseNumber`` and add normalized
name + address columns so the result can be left-joined against our
person and company tables. The investigative signal is an exact match
between (normalized_person_name, date_of_birth) on this list and the
same pair anywhere in our shell-network officer set.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from shellnet.normalize import normalize_address_text, normalize_company_name
from shellnet.paths import INTERIM_DIR

log = logging.getLogger(__name__)


_OUTPUT_SCHEMA: dict[str, type[pl.DataType]] = {
    "source": pl.Utf8,
    "source_id": pl.Utf8,
    "person_name": pl.Utf8,
    "normalized_person_name": pl.Utf8,
    "date_of_birth": pl.Utf8,
    "company_name": pl.Utf8,
    "normalized_company_name": pl.Utf8,
    "address_raw": pl.Utf8,
    "normalized_address": pl.Utf8,
    "date_order_starts": pl.Utf8,
    "disqualification_length": pl.Utf8,
    "conduct": pl.Utf8,
    "information_correct_as_of": pl.Utf8,
}


def ingest(
    input_csv: Path,
    *,
    out_dir: Path = INTERIM_DIR,
) -> Path:
    """Read the scraper CSV and write the projected parquet."""
    if not input_csv.exists():
        raise FileNotFoundError(f"disqualified-directors CSV missing: {input_csv}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "uk_disqualified_directors.parquet"

    # Force all columns to Utf8: case numbers look numeric but other ID-shaped
    # fields (e.g. dates with " / " separators, addresses) must not be inferred.
    df = pl.read_csv(input_csv, ignore_errors=True, infer_schema_length=0)
    # Upstream produces JS camelCase headers; rename to snake_case for the
    # join-side schema while keeping the raw values intact.
    renamed = df.rename(
        {
            "caseNumber": "source_id",
            "personName": "person_name",
            "dateOfBirth": "date_of_birth",
            "companyName": "company_name",
            "lastKnownAddress": "address_raw",
            "dateOrderStarts": "date_order_starts",
            "disqualificationLength": "disqualification_length",
            "informationCorrectAsOf": "information_correct_as_of",
            "conduct": "conduct",
        }
    )

    projected = renamed.with_columns(
        pl.lit("uk_disqualified_directors").alias("source"),
        pl.col("person_name")
        .map_elements(normalize_company_name, return_dtype=pl.Utf8)
        .alias("normalized_person_name"),
        pl.col("company_name")
        .map_elements(normalize_company_name, return_dtype=pl.Utf8)
        .alias("normalized_company_name"),
        pl.col("address_raw")
        .map_elements(normalize_address_text, return_dtype=pl.Utf8)
        .alias("normalized_address"),
    ).select(list(_OUTPUT_SCHEMA.keys()))

    projected.write_parquet(out)
    log.info("Wrote %d disqualified-director rows to %s", projected.height, out)
    return out
