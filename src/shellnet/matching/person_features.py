"""Build the unified persons table.

Persons come from two places today:

  * **ICIJ** — officer and intermediary CSV rows. Officers are usually
    natural persons (directors, shareholders). Intermediaries are usually
    law firms or registered agents — entities, not persons — but we keep
    them in the same table because they participate in person-shaped
    relationships and they're not registry-anchored.
  * **OpenSanctions** — entities with schema ``Person``.

We deliberately keep this looser than the company table. Personal names
are noisier and harder to dedupe; ER on them is a Phase-5 problem and
this is just the input it'll consume.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from shellnet.normalize import normalize_company_name, normalize_jurisdiction
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR

log = logging.getLogger(__name__)

UNIFIED_COLUMNS: tuple[str, ...] = (
    "source",
    "source_id",
    "kind",          # "officer", "intermediary", "person"
    "name",
    "normalized_name",
    "country",
    "topics",        # opensanctions: ["pep", "sanction", ...]
    "datasets",      # opensanctions: source datasets
)


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "source": pl.Utf8,
            "source_id": pl.Utf8,
            "kind": pl.Utf8,
            "name": pl.Utf8,
            "normalized_name": pl.Utf8,
            "country": pl.Utf8,
            "topics": pl.List(pl.Utf8),
            "datasets": pl.List(pl.Utf8),
        }
    )


def _load_icij(interim: Path, filename: str, kind: str) -> pl.DataFrame | None:
    path = interim / filename
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    if df.height == 0:
        return None
    return df.with_columns(
        pl.lit(kind, dtype=pl.Utf8).alias("kind"),
        pl.lit([], dtype=pl.List(pl.Utf8)).alias("topics"),
        pl.lit([], dtype=pl.List(pl.Utf8)).alias("datasets"),
    ).select(list(UNIFIED_COLUMNS))


def _load_opensanctions(interim: Path) -> pl.DataFrame | None:
    path = interim / "opensanctions_entities.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path).filter(pl.col("entity_schema") == "Person")
    if df.height == 0:
        return None
    return df.with_columns(
        pl.lit("person", dtype=pl.Utf8).alias("kind"),
        pl.col("jurisdictions").list.first().alias("country"),
    ).select(
        "source", "source_id", "kind", "name", "normalized_name",
        "country", "topics", "datasets",
    )


def build_person_table(
    interim_dir: Path = INTERIM_DIR,
    out_dir: Path = PROCESSED_DIR,
) -> Path:
    """Concatenate all available person-shaped rows into one parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[pl.DataFrame] = []
    for filename, kind in (
        ("icij_officers.parquet", "officer"),
        ("icij_intermediaries.parquet", "intermediary"),
    ):
        df = _load_icij(interim_dir, filename, kind)
        if df is not None:
            parts.append(df)
            log.info("Loaded %d %s rows from ICIJ", df.height, kind)
    os_df = _load_opensanctions(interim_dir)
    if os_df is not None:
        parts.append(os_df)
        log.info("Loaded %d Person rows from OpenSanctions", os_df.height)

    if not parts:
        log.warning("No person-shaped tables found under %s", interim_dir)
        out = out_dir / "person_entities.parquet"
        _empty().write_parquet(out)
        return out

    df = pl.concat(parts, how="vertical_relaxed")
    df = df.with_columns(
        pl.col("name").map_elements(normalize_company_name, return_dtype=pl.Utf8).alias(
            "normalized_name"
        ),
        pl.col("country").map_elements(normalize_jurisdiction, return_dtype=pl.Utf8).alias(
            "country"
        ),
    )
    df = df.with_columns(
        (pl.col("source") + pl.lit(":") + pl.col("source_id")).alias("entity_uid")
    ).select(["entity_uid", *UNIFIED_COLUMNS])

    out = out_dir / "person_entities.parquet"
    df.write_parquet(out)
    log.info("Wrote unified person table (%d rows) to %s", df.height, out)
    return out
