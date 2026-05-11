"""ICIJ Offshore Leaks adapter.

Reads the CSV bundle the user manually downloads from
https://offshoreleaks.icij.org/pages/database into ``data/raw/icij/``.
The export historically uses files like:

    nodes-entities.csv
    nodes-officers.csv
    nodes-intermediaries.csv
    nodes-addresses.csv
    relationships.csv

Filenames have varied across releases (some include leak-name prefixes),
so we match by *fuzzy* substring rather than by exact name.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from shellnet.normalize import (
    normalize_address_text,
    normalize_company_name,
    normalize_jurisdiction,
)
from shellnet.paths import ICIJ_RAW, INTERIM_DIR

log = logging.getLogger(__name__)

# Filename keyword → output kind.
# Keywords are matched case-insensitively as substrings against the filename
# stem so we tolerate prefixes like "panama_papers." or suffixes like ".v2".
_FILE_PATTERNS: dict[str, str] = {
    "entit": "entities",
    "officer": "officers",
    "intermediar": "intermediaries",
    "address": "addresses",
    "relationship": "relationships",
}


@dataclass(frozen=True)
class ICIJFiles:
    """Discovered raw files for the ICIJ leak dataset."""

    entities: Path | None = None
    officers: Path | None = None
    intermediaries: Path | None = None
    addresses: Path | None = None
    relationships: Path | None = None

    def is_empty(self) -> bool:
        return all(getattr(self, f.name) is None for f in self.__dataclass_fields__.values())  # type: ignore[arg-type]


def discover_files(raw_dir: Path = ICIJ_RAW) -> ICIJFiles:
    """Find ICIJ CSV files in ``raw_dir`` by fuzzy filename match.

    Returns an :class:`ICIJFiles` with whichever files were located. Missing
    files are simply ``None`` — callers decide how to handle that.
    """
    if not raw_dir.exists():
        return ICIJFiles()
    found: dict[str, Path] = {}
    for path in sorted(raw_dir.glob("*.csv")):
        stem = path.stem.lower()
        for pattern, kind in _FILE_PATTERNS.items():
            if pattern in stem and kind not in found:
                found[kind] = path
                break
    return ICIJFiles(**found)


# ── Field maps ─────────────────────────────────────────────────────────────
# These names mirror what ICIJ has shipped in recent CSV releases. We keep
# the lookup tolerant: any column we want that isn't present becomes null.

_ENTITY_COLS = {
    "node_id": "node_id",
    "name": "name",
    "jurisdiction": "jurisdiction",
    "jurisdiction_description": "jurisdiction_description",
    "country_codes": "country_codes",
    "incorporation_date": "incorporation_date",
    "inactivation_date": "inactivation_date",
    "struck_off_date": "struck_off_date",
    "status": "status",
    "company_type": "company_type",
    "address": "address",
    "sourceID": "source_id_label",
}

_ADDRESS_COLS = {
    "node_id": "node_id",
    "address": "address",
    "country_codes": "country_codes",
    "countries": "countries",
    "sourceID": "source_id_label",
}

_RELATIONSHIP_COLS = {
    "node_id_start": "src_node_id",
    "node_id_end": "dst_node_id",
    "rel_type": "rel_type",
    "link": "link",
    "start_date": "start_date",
    "end_date": "end_date",
    "sourceID": "source_id_label",
}


def _read_csv_subset(path: Path, wanted: dict[str, str]) -> pl.DataFrame:
    """Read a CSV but only the columns we care about, renaming as we go.

    Missing columns are silently filled with nulls so we can stay tolerant
    of schema drift across ICIJ leak releases.
    """
    # Read header first to figure out which wanted columns are actually present.
    header = pl.read_csv(path, n_rows=0, infer_schema_length=0).columns
    present = [c for c in wanted if c in header]
    df = pl.read_csv(
        path,
        columns=present,
        infer_schema_length=0,  # everything as Utf8; we cast deliberately later
        ignore_errors=True,
    )
    df = df.rename({c: wanted[c] for c in present})
    # Add missing wanted columns as null Utf8 so downstream code can rely
    # on a stable schema.
    for dst in wanted.values():
        if dst not in df.columns:
            df = df.with_columns(pl.lit(None, dtype=pl.Utf8).alias(dst))
    return df.select(list(wanted.values()))


def load_entities(path: Path) -> pl.DataFrame:
    """Read the ICIJ entities CSV and add normalized fields.

    Returns a Polars DataFrame with these columns (all Utf8 unless noted):

      source, source_id, name, normalized_name, jurisdiction,
      jurisdiction_raw, status, legal_form, address_raw, normalized_address,
      incorporation_date, dissolution_date, source_label
    """
    df = _read_csv_subset(path, _ENTITY_COLS)

    norm_name = pl.col("name").map_elements(normalize_company_name, return_dtype=pl.Utf8)
    norm_juris = (
        pl.coalesce([pl.col("jurisdiction"), pl.col("country_codes")])
        .map_elements(normalize_jurisdiction, return_dtype=pl.Utf8)
    )
    norm_addr = pl.col("address").map_elements(normalize_address_text, return_dtype=pl.Utf8)
    dissolution = pl.coalesce([pl.col("struck_off_date"), pl.col("inactivation_date")])

    return df.with_columns(
        pl.lit("icij").alias("source"),
        pl.col("node_id").alias("source_id"),
        norm_name.alias("normalized_name"),
        norm_juris.alias("jurisdiction"),
        pl.coalesce([pl.col("jurisdiction_description"), pl.col("jurisdiction")]).alias(
            "jurisdiction_raw"
        ),
        pl.col("status").alias("status"),
        pl.col("company_type").alias("legal_form"),
        pl.col("address").alias("address_raw"),
        norm_addr.alias("normalized_address"),
        pl.col("incorporation_date").alias("incorporation_date"),
        dissolution.alias("dissolution_date"),
        pl.col("source_id_label").alias("source_label"),
    ).select(
        "source",
        "source_id",
        "name",
        "normalized_name",
        "jurisdiction",
        "jurisdiction_raw",
        "status",
        "legal_form",
        "address_raw",
        "normalized_address",
        "incorporation_date",
        "dissolution_date",
        "source_label",
    )


def load_addresses(path: Path) -> pl.DataFrame:
    df = _read_csv_subset(path, _ADDRESS_COLS)
    norm_addr = pl.col("address").map_elements(normalize_address_text, return_dtype=pl.Utf8)
    norm_country = (
        pl.coalesce([pl.col("country_codes"), pl.col("countries")])
        .map_elements(normalize_jurisdiction, return_dtype=pl.Utf8)
    )
    return df.with_columns(
        pl.lit("icij").alias("source"),
        pl.col("node_id").alias("source_id"),
        pl.col("address").alias("raw_text"),
        norm_addr.alias("normalized_text"),
        norm_country.alias("country"),
        pl.col("source_id_label").alias("source_label"),
    ).select("source", "source_id", "raw_text", "normalized_text", "country", "source_label")


def load_relationships(path: Path) -> pl.DataFrame:
    df = _read_csv_subset(path, _RELATIONSHIP_COLS)
    return df.with_columns(
        pl.lit("icij").alias("source"),
        ("icij:" + pl.col("src_node_id")).alias("src_node"),
        ("icij:" + pl.col("dst_node_id")).alias("dst_node"),
        pl.col("rel_type").alias("kind_raw"),
        pl.col("link").alias("role"),
        pl.col("start_date").alias("start_date"),
        pl.col("end_date").alias("end_date"),
        pl.col("source_id_label").alias("source_label"),
    ).select(
        "source",
        "src_node",
        "dst_node",
        "kind_raw",
        "role",
        "start_date",
        "end_date",
        "source_label",
    )


def ingest(raw_dir: Path = ICIJ_RAW, out_dir: Path = INTERIM_DIR) -> dict[str, Path]:
    """Run the full ICIJ ingest, writing parquet files under ``out_dir``.

    Returns a dict mapping logical name to written path. If a particular
    file isn't present in ``raw_dir`` we skip it and don't include it in
    the result (caller can detect the partial state).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    files = discover_files(raw_dir)

    if files.is_empty():
        log.warning(
            "No ICIJ CSV files found in %s. Download the Offshore Leaks bundle "
            "from https://offshoreleaks.icij.org/pages/database and unzip it there.",
            raw_dir,
        )
        return {}

    written: dict[str, Path] = {}

    if files.entities is not None:
        df = load_entities(files.entities)
        out = out_dir / "icij_entities.parquet"
        df.write_parquet(out)
        written["entities"] = out
        log.info("Wrote %d ICIJ entity rows to %s", df.height, out)

    if files.addresses is not None:
        df = load_addresses(files.addresses)
        out = out_dir / "icij_addresses.parquet"
        df.write_parquet(out)
        written["addresses"] = out
        log.info("Wrote %d ICIJ address rows to %s", df.height, out)

    if files.relationships is not None:
        df = load_relationships(files.relationships)
        out = out_dir / "icij_edges.parquet"
        df.write_parquet(out)
        written["edges"] = out
        log.info("Wrote %d ICIJ edge rows to %s", df.height, out)

    return written
