"""Address-side helpers used during candidate generation.

We do not try to do real address parsing here (libpostal etc.). Instead we
emit a coarse "country + first-token + postal-code" blocking key which is
good enough to narrow the candidate space without hiding genuine matches.

This module also builds the unified address table used by the address-cluster
GoldenMatch pass: one row per (source, source-id, address), with a stable
``address_uid`` and a blocking key that GoldenMatch can group on.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import polars as pl

from shellnet.normalize import normalize_address_text, normalize_jurisdiction
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR

log = logging.getLogger(__name__)

_POSTAL_RE = re.compile(r"\b[A-Z0-9]{3,10}(?:[-\s][A-Z0-9]{2,5})?\b")


def address_blocking_key(addr: str | None, country: str | None) -> str:
    """Return a coarse blocking key for an address line.

    Format: ``"<country>|<first-token>|<postal>"``. Empty parts are kept as
    empty strings so the column shape is stable.
    """
    if not addr:
        return f"{country or ''}||"
    norm = normalize_address_text(addr)
    if not norm:
        return f"{country or ''}||"
    first_token = norm.split(" ", 1)[0]
    upper = addr.upper()
    postal_match = _POSTAL_RE.search(upper)
    postal = postal_match.group(0) if postal_match else ""
    return f"{(country or '').lower()}|{first_token}|{postal}"


def add_address_blocking(df: pl.DataFrame) -> pl.DataFrame:
    """Add an ``address_block`` column to a unified company table."""
    return df.with_columns(
        pl.struct(["normalized_address", "jurisdiction"])
        .map_elements(
            lambda row: address_blocking_key(row["normalized_address"], row["jurisdiction"]),
            return_dtype=pl.Utf8,
        )
        .alias("address_block")
    )


# ── Unified address table ──────────────────────────────────────────────────

ADDRESS_COLUMNS: tuple[str, ...] = (
    "source",
    "source_id",       # the *entity* that owns the address (so we can join back)
    "raw_text",
    "normalized_text",
    "country",
    "block_key",
)


def _empty_addresses() -> pl.DataFrame:
    return pl.DataFrame(schema={c: pl.Utf8 for c in ADDRESS_COLUMNS})


def _from_icij_entities(interim: Path) -> pl.DataFrame | None:
    path = interim / "icij_entities.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path).filter(pl.col("address_raw").is_not_null())
    if df.height == 0:
        return None
    return df.select(
        pl.lit("icij", dtype=pl.Utf8).alias("source"),
        pl.col("source_id"),
        pl.col("address_raw").alias("raw_text"),
        pl.col("normalized_address").alias("normalized_text"),
        pl.col("jurisdiction").alias("country"),
    )


def _from_icij_addresses(interim: Path) -> pl.DataFrame | None:
    path = interim / "icij_addresses.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    if df.height == 0:
        return None
    return df.select(
        pl.lit("icij", dtype=pl.Utf8).alias("source"),
        pl.col("source_id"),
        pl.col("raw_text"),
        pl.col("normalized_text"),
        pl.col("country"),
    )


def _from_opencorporates(interim: Path) -> pl.DataFrame | None:
    path = interim / "opencorporates_companies.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path).filter(pl.col("address_raw").is_not_null())
    if df.height == 0:
        return None
    return df.select(
        pl.lit("opencorporates", dtype=pl.Utf8).alias("source"),
        pl.col("source_id"),
        pl.col("address_raw").alias("raw_text"),
        pl.col("normalized_address").alias("normalized_text"),
        pl.col("jurisdiction").alias("country"),
    )


def _from_gleif(interim: Path) -> pl.DataFrame | None:
    path = interim / "gleif_entities.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    if df.height == 0:
        return None
    legal = df.select(
        pl.lit("gleif", dtype=pl.Utf8).alias("source"),
        pl.col("source_id"),
        pl.col("legal_address_raw").alias("raw_text"),
        pl.col("normalized_legal_address").alias("normalized_text"),
        pl.col("jurisdiction").alias("country"),
    )
    hq = df.select(
        pl.lit("gleif", dtype=pl.Utf8).alias("source"),
        (pl.col("source_id") + pl.lit("#hq")).alias("source_id"),
        pl.col("headquarters_address_raw").alias("raw_text"),
        pl.col("normalized_headquarters_address").alias("normalized_text"),
        pl.col("jurisdiction").alias("country"),
    )
    return pl.concat([legal, hq], how="vertical_relaxed").filter(
        pl.col("raw_text").is_not_null() & (pl.col("raw_text") != "")
    )


def _from_opensanctions(interim: Path) -> pl.DataFrame | None:
    path = interim / "opensanctions_entities.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    if df.height == 0:
        return None
    df = df.with_columns(
        pl.col("addresses_raw").list.first().alias("_raw"),
        pl.col("normalized_addresses").list.first().alias("_norm"),
        pl.col("jurisdictions").list.first().alias("_country"),
    ).filter(pl.col("_raw").is_not_null() & (pl.col("_raw") != ""))
    if df.height == 0:
        return None
    return df.select(
        pl.lit("opensanctions", dtype=pl.Utf8).alias("source"),
        pl.col("source_id"),
        pl.col("_raw").alias("raw_text"),
        pl.col("_norm").alias("normalized_text"),
        pl.col("_country").alias("country"),
    )


def build_address_table(
    interim_dir: Path = INTERIM_DIR,
    out_dir: Path = PROCESSED_DIR,
) -> Path:
    """Concatenate all addresses across sources into a single parquet.

    Output schema: ``address_uid, source, source_id, raw_text,
    normalized_text, country, block_key``. ``address_uid`` is a deterministic
    cross-source identifier so GoldenMatch can use it as the primary key.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[pl.DataFrame] = []
    for loader in (
        _from_icij_entities,
        _from_icij_addresses,
        _from_opencorporates,
        _from_gleif,
        _from_opensanctions,
    ):
        df = loader(interim_dir)
        if df is not None and df.height > 0:
            parts.append(df)
            log.info("Loaded %d address rows from %s", df.height, loader.__name__)

    if not parts:
        out = out_dir / "address_entities.parquet"
        _empty_addresses().write_parquet(out)
        log.warning("No address-bearing tables found; wrote empty table to %s", out)
        return out

    df = pl.concat(parts, how="vertical_relaxed")
    df = df.with_columns(
        pl.col("country").map_elements(normalize_jurisdiction, return_dtype=pl.Utf8).alias("country"),
        pl.col("raw_text").map_elements(normalize_address_text, return_dtype=pl.Utf8).alias("normalized_text"),
    )
    df = df.with_columns(
        pl.struct(["normalized_text", "country"])
        .map_elements(
            lambda row: address_blocking_key(row["normalized_text"], row["country"]),
            return_dtype=pl.Utf8,
        )
        .alias("block_key")
    )
    df = df.with_columns(
        (pl.col("source") + pl.lit(":") + pl.col("source_id") + pl.lit("#addr")).alias("address_uid")
    )
    df = df.unique(subset=["address_uid"], keep="first")
    df = df.select(["address_uid", *ADDRESS_COLUMNS])

    out = out_dir / "address_entities.parquet"
    df.write_parquet(out)
    log.info("Wrote unified address table (%d rows) to %s", df.height, out)
    return out


def shared_address_report(
    address_path: Path,
    top_n: int = 20,
    min_count: int = 3,
) -> pl.DataFrame:
    """Aggregate the address table by normalized_text + country, return the top hosts.

    ``min_count`` is the lower bound on hosted-entity count — single
    entities at a unique address aren't interesting; clusters are.
    """
    df = pl.read_parquet(address_path).filter(
        pl.col("normalized_text").is_not_null() & (pl.col("normalized_text") != "")
    )
    if df.height == 0:
        return df
    grouped = (
        df.group_by(["normalized_text", "country"])
        .agg(
            pl.len().alias("hosted_count"),
            pl.col("source_id").unique().alias("hosted_source_ids"),
            pl.col("source").unique().alias("contributing_sources"),
            pl.col("raw_text").first().alias("sample_raw_text"),
        )
        .filter(pl.col("hosted_count") >= min_count)
        .sort("hosted_count", descending=True)
        .head(top_n)
    )
    return grouped
