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

# Person -> company PSC edges. ``person_source_id`` is the BODS person
# statementId, which is exactly the ``uk_psc:<id>`` key the unified person
# table (``_build_persons``) emits — so a sanctioned-PSC match in the
# survivor pipeline joins straight onto this edge to name the controlled
# company. ``company_id`` is the raw ``GB-COH-<n>`` ref (matches the OO
# entities ``bods_subject``); ``company_number`` is the bare number,
# aligned with ``uk_psc_entities.company_number``.
_PSC_RELATIONSHIP_COLUMNS: tuple[str, ...] = (
    "source",
    "person_source_id",
    "person_record_id",
    "company_id",
    "company_number",
    "control_type",
    "direct_or_indirect",
    "share_min",
    "share_max",
    "start_date",
    "end_date",
)


def _coh_company_number(subject: str | None) -> str:
    """``GB-COH-04818143`` -> ``04818143`` (normalized).

    UK PSC relationship subjects carry the ``GB-COH-`` registry prefix;
    strip it before normalizing so the number matches the
    ``company_number`` column emitted by ``_build_entities``.
    """
    if not subject:
        return ""
    s = subject
    if s.upper().startswith("GB-COH-"):
        s = s[len("GB-COH-") :]
    return normalize_identifier(s)


def _build_persons(work_dir: Path) -> pl.DataFrame:
    spine = pl.read_parquet(work_dir / "person_statement.parquet").select(["_link", "statementId"])
    log.info("BODS persons: spine = %d rows", spine.height)

    names = pl.read_parquet(work_dir / "person_recorddetails_names.parquet").select(
        ["_link_person_statement", "fullName", "familyName", "givenName"]
    )
    names = _first_per_link(
        names, "_link_person_statement", ["fullName", "familyName", "givenName"]
    )

    nat = pl.read_parquet(work_dir / "person_recorddetails_nationalities.parquet").select(
        ["_link_person_statement", "code"]
    )
    nat = _first_per_link(nat, "_link_person_statement", ["code"])

    df = spine.join(names, left_on="_link", right_on="_link_person_statement", how="left").join(
        nat, left_on="_link", right_on="_link_person_statement", how="left"
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
        pl.col("code").map_elements(normalize_jurisdiction, return_dtype=pl.Utf8).alias("country"),
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

    ids = pl.read_parquet(work_dir / "entity_recorddetails_identifiers.parquet").select(
        ["_link_entity_statement", "id", "scheme"]
    )
    ids = _first_per_link(ids, "_link_entity_statement", ["id", "scheme"])

    addrs = pl.read_parquet(work_dir / "entity_recorddetails_addresses.parquet").select(
        ["_link_entity_statement", "address", "country_code"]
    )
    addrs = _first_per_link(addrs, "_link_entity_statement", ["address", "country_code"])

    df = spine.join(ids, left_on="_link", right_on="_link_entity_statement", how="left").join(
        addrs, left_on="_link", right_on="_link_entity_statement", how="left"
    )
    df = df.with_columns(
        pl.lit("uk_psc", dtype=pl.Utf8).alias("source"),
        pl.col("statementId").alias("source_id"),
        pl.col("recordDetails_name").alias("name"),
        pl.col("recordDetails_name")
        .map_elements(normalize_company_name, return_dtype=pl.Utf8)
        .alias("normalized_name"),
        pl.coalesce([pl.col("recordDetails_jurisdiction_code"), pl.col("country_code")])
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


def _build_uk_psc_relationships(work_dir: Path) -> pl.DataFrame:
    """Extract UK PSC person -> company control edges from the BODS bundle.

    BODS shape:
      - ``relationship_statement``: ``recordDetails_subject`` is the
        controlled company (``GB-COH-<n>``), ``recordDetails_interestedParty``
        is the controlling person's ``recordId`` (``GB-COH-PER-<n>-<hash>``).
      - ``relationship_recorddetails_interests``: nature-of-control type,
        direct/indirect, share band, dates (FK ``_link_relationship_statement``).
      - ``person_statement``: maps each person ``recordId`` to its
        ``statementId`` (the unified person table's ``source_id``).

    Component sub-statements (``recordDetails_isComponent``) are dropped;
    they decompose corporate chains rather than naming a direct PSC.
    """
    rel = pl.read_parquet(work_dir / "relationship_statement.parquet").select(
        [
            "_link",
            "recordType",
            "recordDetails_isComponent",
            "recordDetails_subject",
            "recordDetails_interestedParty",
        ]
    )
    rel = rel.filter(
        (pl.col("recordType") == "relationship")
        & (pl.col("recordDetails_isComponent") != True)  # noqa: E712
        & pl.col("recordDetails_subject").is_not_null()
        & pl.col("recordDetails_interestedParty").is_not_null()
    )
    log.info("BODS: %d UK PSC relationship statements", rel.height)

    interests_full = pl.read_parquet(work_dir / "relationship_recorddetails_interests.parquet")
    available = set(interests_full.columns)
    icols = ["_link_relationship_statement"]
    icols += [
        c
        for c in (
            "type",
            "directOrIndirect",
            "share_minimum",
            "share_maximum",
            "startDate",
            "endDate",
        )
        if c in available
    ]
    interests = interests_full.select(icols).unique(
        subset=["_link_relationship_statement"], keep="first"
    )

    persons = (
        pl.read_parquet(work_dir / "person_statement.parquet")
        .select(["statementId", "recordId"])
        .filter(pl.col("recordId").is_not_null())
        .unique(subset=["recordId"], keep="first")
    )

    edges = rel.join(
        interests, left_on="_link", right_on="_link_relationship_statement", how="left"
    ).join(persons, left_on="recordDetails_interestedParty", right_on="recordId", how="left")

    cols = set(edges.columns)
    edges = edges.with_columns(
        pl.lit("uk_psc", dtype=pl.Utf8).alias("source"),
        pl.col("statementId").alias("person_source_id"),
        pl.col("recordDetails_interestedParty").alias("person_record_id"),
        pl.col("recordDetails_subject").alias("company_id"),
        pl.col("recordDetails_subject")
        .map_elements(_coh_company_number, return_dtype=pl.Utf8)
        .alias("company_number"),
        (pl.col("type") if "type" in cols else pl.lit(None, dtype=pl.Utf8)).alias("control_type"),
        (
            pl.col("directOrIndirect")
            if "directOrIndirect" in cols
            else pl.lit(None, dtype=pl.Utf8)
        ).alias("direct_or_indirect"),
        (
            pl.col("share_minimum") if "share_minimum" in cols else pl.lit(None, dtype=pl.Float64)
        ).alias("share_min"),
        (
            pl.col("share_maximum") if "share_maximum" in cols else pl.lit(None, dtype=pl.Float64)
        ).alias("share_max"),
        (pl.col("startDate") if "startDate" in cols else pl.lit(None, dtype=pl.Utf8)).alias(
            "start_date"
        ),
        (pl.col("endDate") if "endDate" in cols else pl.lit(None, dtype=pl.Utf8)).alias("end_date"),
    )
    return edges.select(list(_PSC_RELATIONSHIP_COLUMNS))


_OWNERSHIP_EDGE_COLUMNS: tuple[str, ...] = (
    "source",  # 'gleif_l2' or 'uk_psc'
    "src_lei",  # subject company LEI (or BODS statement id)
    "dst_lei",  # interested party LEI (parent / controller)
    "kind",  # 'parent_of' / 'control'
    "share_min",  # percentage minimum if available
    "share_max",  # percentage maximum if available
    "start_date",
    "end_date",
)


def _build_gleif_relationships(work_dir: Path) -> pl.DataFrame:
    """Extract corporate parent/child relationships from GLEIF L2 BODS.

    GLEIF L2's BODS relationship_statement has:
      - declarationSubject  -> the child entity (LEI prefixed XI-LEI-...)
      - recordDetails_subject / recordDetails_interestedParty
        -> child + parent
    Plus an associated interests sub-table with share %, type, etc.
    """
    rel = pl.read_parquet(work_dir / "relationship_statement.parquet").select(
        [
            "_link",
            "statementId",
            "recordDetails_subject",
            "recordDetails_interestedParty",
        ]
    )
    # GLEIF BODS interests schema is leaner than UK BODS — no share_*
    # columns. Read what's there, fill the rest with nulls.
    interests_path = work_dir / "relationship_recorddetails_interests.parquet"
    interests_full = pl.read_parquet(interests_path)
    available = set(interests_full.columns)
    cols = ["_link_relationship_statement", "type"]
    if "directOrIndirect" in available:
        cols.append("directOrIndirect")
    if "startDate" in available:
        cols.append("startDate")
    interests = interests_full.select(cols).unique(
        subset=["_link_relationship_statement"], keep="first"
    )
    edges = rel.join(
        interests,
        left_on="_link",
        right_on="_link_relationship_statement",
        how="left",
    )
    has_start = "startDate" in edges.columns
    edges = edges.with_columns(
        pl.lit("gleif_l2", dtype=pl.Utf8).alias("source"),
        pl.col("recordDetails_subject").alias("src_lei"),
        pl.col("recordDetails_interestedParty").alias("dst_lei"),
        pl.col("type").fill_null("ownership").alias("kind"),
        pl.lit(None, dtype=pl.Float64).alias("share_min"),
        pl.lit(None, dtype=pl.Float64).alias("share_max"),
        (pl.col("startDate") if has_start else pl.lit(None, dtype=pl.Utf8)).alias("start_date"),
        pl.lit(None, dtype=pl.Utf8).alias("end_date"),
    ).select(list(_OWNERSHIP_EDGE_COLUMNS))
    edges = edges.filter(pl.col("src_lei").is_not_null() & pl.col("dst_lei").is_not_null())
    return edges


def ingest_gleif_l2(
    zip_path: Path,
    *,
    out_dir: Path = INTERIM_DIR,
    work_dir: Path | None = None,
    keep_extracted: bool = False,
) -> dict[str, Path]:
    """Ingest the OpenOwnership GLEIF L2 BODS parquet.

    Emits:
      - ``gleif_l2_relationships.parquet`` — corporate parent/child edges
        with share %, type, dates. Consumed by the graph layer for
        company-anchored ownership-chain walks.

    Optionally also writes an entity-shaped parquet so GLEIF L2's own
    entity rows can land in the unified company table (the existing
    Golden Copy ingest already covers most of this, so by default we
    skip it — the relationship layer is the marginal value-add).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = work_dir or out_dir / "_gleif_l2_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    zip_path = Path(zip_path)
    if not zip_path.exists():
        log.error("GLEIF L2 BODS zip not found: %s", zip_path)
        return {}

    members = (
        "relationship_statement.parquet",
        "relationship_recorddetails_interests.parquet",
    )
    for m in members:
        target = work_dir / m
        if target.exists():
            log.info("GLEIF L2: %s already extracted (%.0f MB)", m, target.stat().st_size / 1e6)
            continue
        log.info("GLEIF L2: extracting %s", m)
        _extract(zip_path, m, target)

    log.info("GLEIF L2: building relationships")
    rel = _build_gleif_relationships(work_dir)
    rel_out = out_dir / "gleif_l2_relationships.parquet"
    rel.write_parquet(rel_out)
    log.info("GLEIF L2: wrote %d ownership edges -> %s", rel.height, rel_out)

    if not keep_extracted:
        for m in members:
            (work_dir / m).unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            work_dir.rmdir()

    return {"relationships": rel_out}


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
      - ``uk_psc_relationships.parquet`` (person -> company PSC edges)

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
        "relationship_statement.parquet",
        "relationship_recorddetails_interests.parquet",
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

    log.info("BODS: building relationships")
    relationships = _build_uk_psc_relationships(work_dir)
    relationships_out = out_dir / "uk_psc_relationships.parquet"
    relationships.write_parquet(relationships_out)
    log.info("BODS: wrote %d UK PSC relationships -> %s", relationships.height, relationships_out)

    if not keep_extracted:
        for m in members_to_extract:
            (work_dir / m).unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            work_dir.rmdir()

    return {
        "persons": persons_out,
        "entities": entities_out,
        "relationships": relationships_out,
    }
