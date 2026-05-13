"""OpenOwnership BODS (Beneficial Ownership Data Standard) adapter.

The OpenOwnership UK BODS bundle is distributed as a ZIP of separate
parquet files in a normalized layout. The relevant tables are:

  person_statement.parquet               (spine; statementId, _link)
  person_recorddetails_names.parquet     (FK _link_person_statement)
  person_recorddetails_nationalities     (FK _link_person_statement)
  person_recorddetails_addresses         (FK _link_person_statement)
  entity_statement.parquet               (spine; statementId, _link)
  entity_recorddetails_identifiers       (FK _link_entity_statement)
  entity_recorddetails_addresses         (FK _link_entity_statement)
  relationship_statement.parquet         (subject + interestedParty)
  relationship_recorddetails_interests   (share %, type, dates)

This adapter joins the person / entity spines with their first-name +
first-nationality + first-address sub-rows and emits two parquets in
the unified persons / companies shape. Relationship statements are
kept on disk as a separate parquet for the graph layer.
"""

from __future__ import annotations

import contextlib
import logging
import zipfile
from pathlib import Path

import polars as pl

from shellnet.normalize import (
    normalize_address_text,
    normalize_company_name,
    normalize_identifier,
    normalize_jurisdiction,
)
from shellnet.paths import INTERIM_DIR

log = logging.getLogger(__name__)


def _extract(zip_path: Path, member: str, dest: Path) -> Path:
    """Extract a ZIP member to dest. Returns the on-disk path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf, zf.open(member) as src, dest.open("wb") as fh:
        while True:
            chunk = src.read(8 * 1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)
    return dest


def _first_per_link(df: pl.DataFrame, link_col: str, keep: list[str]) -> pl.DataFrame:
    """Keep the first sub-row per parent link. The BODS normalized tables
    have N rows per parent (one per name / nationality / address); we
    only need one to seed the unified-table row.
    """
    if df.height == 0:
        return df
    # Sort so the "primary" entry (often type='legal' or first listed)
    # bubbles to the top; ties broken by source order.
    return df.group_by(link_col).agg(*[pl.col(c).first().alias(c) for c in keep])


_PERSON_COLUMNS: tuple[str, ...] = (
    "source",
    "source_id",
    "kind",
    "name",
    "normalized_name",
    "country",
    "topics",
    "datasets",
)

_COMPANY_COLUMNS: tuple[str, ...] = (
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


def _build_persons(work_dir: Path) -> pl.DataFrame:
    spine = pl.read_parquet(work_dir / "person_statement.parquet").select(
        ["_link", "statementId"]
    )
    log.info("BODS persons: spine = %d rows", spine.height)

    names = pl.read_parquet(work_dir / "person_recorddetails_names.parquet").select(
        ["_link_person_statement", "fullName", "familyName", "givenName"]
    )
    names = _first_per_link(
        names, "_link_person_statement", ["fullName", "familyName", "givenName"]
    )

    nat = pl.read_parquet(
        work_dir / "person_recorddetails_nationalities.parquet"
    ).select(["_link_person_statement", "code"])
    nat = _first_per_link(nat, "_link_person_statement", ["code"])

    df = (
        spine.join(
            names, left_on="_link", right_on="_link_person_statement", how="left"
        ).join(nat, left_on="_link", right_on="_link_person_statement", how="left")
    )
    # Prefer fullName, fall back to "given family".
    df = df.with_columns(
        pl.when(pl.col("fullName").is_not_null() & (pl.col("fullName") != ""))
        .then(pl.col("fullName"))
        .otherwise(
            pl.coalesce(
                [
                    pl.col("givenName").fill_null("")
                    + pl.lit(" ")
                    + pl.col("familyName").fill_null(""),
                    pl.col("familyName"),
                    pl.col("givenName"),
                ]
            )
        )
        .str.strip_chars()
        .alias("name")
    )
    df = df.with_columns(
        pl.lit("uk_psc", dtype=pl.Utf8).alias("source"),
        pl.col("statementId").alias("source_id"),
        pl.lit("person", dtype=pl.Utf8).alias("kind"),
        pl.col("name")
        .map_elements(normalize_company_name, return_dtype=pl.Utf8)
        .alias("normalized_name"),
        pl.col("code")
        .map_elements(normalize_jurisdiction, return_dtype=pl.Utf8)
        .alias("country"),
        pl.lit([], dtype=pl.List(pl.Utf8)).alias("topics"),
        pl.lit([], dtype=pl.List(pl.Utf8)).alias("datasets"),
    )
    df = df.filter(pl.col("name").is_not_null() & (pl.col("name") != ""))
    return df.select(list(_PERSON_COLUMNS))


def _build_entities(work_dir: Path) -> pl.DataFrame:
    spine = pl.read_parquet(work_dir / "entity_statement.parquet").select(
        [
            "_link",
            "statementId",
            "recordDetails_name",
            "recordDetails_jurisdiction_code",
            "recordDetails_entityType_type",
        ]
    )
    log.info("BODS entities: spine = %d rows", spine.height)

    ids = pl.read_parquet(
        work_dir / "entity_recorddetails_identifiers.parquet"
    ).select(["_link_entity_statement", "id", "scheme"])
    ids = _first_per_link(ids, "_link_entity_statement", ["id", "scheme"])

    addrs = pl.read_parquet(
        work_dir / "entity_recorddetails_addresses.parquet"
    ).select(["_link_entity_statement", "address", "country_code"])
    addrs = _first_per_link(addrs, "_link_entity_statement", ["address", "country_code"])

    df = (
        spine.join(
            ids, left_on="_link", right_on="_link_entity_statement", how="left"
        ).join(addrs, left_on="_link", right_on="_link_entity_statement", how="left")
    )
    df = df.with_columns(
        pl.lit("uk_psc", dtype=pl.Utf8).alias("source"),
        pl.col("statementId").alias("source_id"),
        pl.col("recordDetails_name").alias("name"),
        pl.col("recordDetails_name")
        .map_elements(normalize_company_name, return_dtype=pl.Utf8)
        .alias("normalized_name"),
        pl.coalesce(
            [pl.col("recordDetails_jurisdiction_code"), pl.col("country_code")]
        )
        .map_elements(normalize_jurisdiction, return_dtype=pl.Utf8)
        .alias("jurisdiction"),
        pl.col("id")
        .map_elements(normalize_identifier, return_dtype=pl.Utf8)
        .alias("company_number"),
        pl.col("address")
        .map_elements(normalize_address_text, return_dtype=pl.Utf8)
        .alias("normalized_address"),
        pl.col("address").alias("address_raw"),
        pl.lit(None, dtype=pl.Utf8).alias("lei"),
        pl.lit(None, dtype=pl.Utf8).alias("status"),
        pl.col("recordDetails_entityType_type").alias("legal_form"),
    )
    df = df.filter(pl.col("name").is_not_null() & (pl.col("name") != ""))
    return df.select(list(_COMPANY_COLUMNS))


def ingest(
    zip_path: Path,
    *,
    out_dir: Path = INTERIM_DIR,
    work_dir: Path | None = None,
    keep_extracted: bool = False,
) -> dict[str, Path]:
    """Parse a BODS UK parquet bundle and write interim parquets.

    Writes:
      - ``uk_psc_persons.parquet`` (~12M rows after filtering empties)
      - ``uk_psc_entities.parquet`` (~5.8M rows)

    Caller can keep the extracted sub-table parquets around for the
    relationship-graph layer by passing ``keep_extracted=True``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = work_dir or out_dir / "_bods_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    zip_path = Path(zip_path)
    if not zip_path.exists():
        log.error("BODS zip not found: %s", zip_path)
        return {}

    members_to_extract = (
        "person_statement.parquet",
        "person_recorddetails_names.parquet",
        "person_recorddetails_nationalities.parquet",
        "entity_statement.parquet",
        "entity_recorddetails_identifiers.parquet",
        "entity_recorddetails_addresses.parquet",
    )
    for m in members_to_extract:
        target = work_dir / m
        if target.exists():
            log.info("BODS: %s already extracted (%.0f MB)", m, target.stat().st_size / 1e6)
            continue
        log.info("BODS: extracting %s", m)
        _extract(zip_path, m, target)

    log.info("BODS: building persons")
    persons = _build_persons(work_dir)
    persons_out = out_dir / "uk_psc_persons.parquet"
    persons.write_parquet(persons_out)
    log.info("BODS: wrote %d UK PSC persons -> %s", persons.height, persons_out)

    log.info("BODS: building entities")
    entities = _build_entities(work_dir)
    entities_out = out_dir / "uk_psc_entities.parquet"
    entities.write_parquet(entities_out)
    log.info("BODS: wrote %d UK PSC entities -> %s", entities.height, entities_out)

    if not keep_extracted:
        for m in members_to_extract:
            (work_dir / m).unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            work_dir.rmdir()

    return {"persons": persons_out, "entities": entities_out}
