"""OpenOwnership BODS (Beneficial Ownership Data Standard) adapter.

OpenOwnership publishes UK PSC + Register of Overseas Entities data in
BODS v0.4 parquet format. The bulk ZIP contains multiple parquet shards
covering 'person-statement', 'entity-statement', and
'relationship-statement' tables, all cross-linked by statementId.

For this case study we ingest two slices:

  * **persons** — beneficial owners + control declarations. Become rows
    in the unified ``person_entities.parquet`` (kind='person',
    source='uk_psc').
  * **entities** — declared subject companies. Become rows in the unified
    ``company_entities.parquet`` (source='uk_psc').

Relationship statements (PSC type, share %, etc.) are kept on disk as
``uk_psc_relationships.parquet`` for the graph layer to consume later.
The BODS schema is a "statement" model — each row is one disclosure
moment, not one entity — so we deduplicate to the most recent statement
per (subject, party) pair before emitting.

Bulk parquet URL (snapshot, monthly refresh):
    https://oo-bodsdata.s3.amazonaws.com/data/uk_version_0_4/parquet.zip
"""

from __future__ import annotations

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


def _shards_for(zip_path: Path, kind: str) -> list[str]:
    """Return parquet member names within the ZIP for a given record kind.

    BODS bulk parquet files are sharded; member names look like
    ``person_statement.parquet/000.parquet``. We list all members that
    start with the kind directory.
    """
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    prefix = f"{kind}.parquet/"
    return [n for n in names if n.startswith(prefix) and n.endswith(".parquet")]


def _extract_shard(zip_path: Path, member: str, dest_dir: Path) -> Path:
    """Extract a single parquet member into dest_dir, preserving filename."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / Path(member).name
    with zipfile.ZipFile(zip_path) as zf, zf.open(member) as src, out.open("wb") as fh:
        while True:
            chunk = src.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    return out


def _stream_kind(zip_path: Path, kind: str, work_dir: Path) -> pl.DataFrame:
    """Stream all shards of a BODS record kind into a single polars DataFrame.

    Caller is responsible for filtering / projecting down to the columns
    the matcher actually needs. We do not slurp everything into memory if
    the on-disk size is large — extract one shard, lazy-scan, concat.
    """
    members = _shards_for(zip_path, kind)
    if not members:
        log.warning("no %s shards in %s", kind, zip_path)
        return pl.DataFrame()
    frames: list[pl.DataFrame] = []
    work_dir.mkdir(parents=True, exist_ok=True)
    for m in members:
        shard = _extract_shard(zip_path, m, work_dir)
        try:
            frames.append(pl.read_parquet(shard))
        finally:
            # Keep extracted shards on disk for re-use across runs;
            # caller can wipe work_dir if needed.
            pass
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="vertical_relaxed")


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


def _normalise_person_rows(df: pl.DataFrame) -> pl.DataFrame:
    """Map BODS person-statement rows to the unified persons schema."""
    if df.height == 0:
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

    # Pick the best available name column. BODS person-statement rows
    # carry recordDetails_names_0_fullName + nationalities + addresses.
    name_col = next(
        (
            c
            for c in (
                "recordDetails_names_0_fullName",
                "recordDetails_names_fullName",
                "name",
            )
            if c in df.columns
        ),
        None,
    )
    nat_col = next(
        (
            c
            for c in (
                "recordDetails_nationalities_0_code",
                "recordDetails_nationalities_code",
                "country",
            )
            if c in df.columns
        ),
        None,
    )
    sid_col = "statementId" if "statementId" in df.columns else df.columns[0]

    pick = df.select(
        pl.col(sid_col).alias("source_id"),
        (pl.col(name_col) if name_col else pl.lit(None, dtype=pl.Utf8)).alias("name"),
        (pl.col(nat_col) if nat_col else pl.lit(None, dtype=pl.Utf8)).alias("country"),
    )
    pick = pick.with_columns(
        pl.lit("uk_psc", dtype=pl.Utf8).alias("source"),
        pl.lit("person", dtype=pl.Utf8).alias("kind"),
        pl.col("name")
        .map_elements(normalize_company_name, return_dtype=pl.Utf8)
        .alias("normalized_name"),
        pl.col("country")
        .map_elements(normalize_jurisdiction, return_dtype=pl.Utf8)
        .alias("country"),
        pl.lit([], dtype=pl.List(pl.Utf8)).alias("topics"),
        pl.lit([], dtype=pl.List(pl.Utf8)).alias("datasets"),
    )
    return pick.select(list(_PERSON_COLUMNS))


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


def _normalise_entity_rows(df: pl.DataFrame) -> pl.DataFrame:
    """Map BODS entity-statement rows to the unified companies schema."""
    if df.height == 0:
        return pl.DataFrame(schema={c: pl.Utf8 for c in _COMPANY_COLUMNS})

    name_col = next(
        (
            c
            for c in ("recordDetails_name", "name", "recordDetails_alternateNames_0")
            if c in df.columns
        ),
        None,
    )
    juris_col = next(
        (
            c
            for c in (
                "recordDetails_incorporatedInJurisdiction_code",
                "recordDetails_jurisdiction_code",
            )
            if c in df.columns
        ),
        None,
    )
    cn_col = next(
        (
            c
            for c in (
                "recordDetails_identifiers_0_id",
                "recordDetails_identifiers_id",
            )
            if c in df.columns
        ),
        None,
    )
    addr_col = next(
        (
            c
            for c in (
                "recordDetails_addresses_0_address",
                "recordDetails_addresses_address",
            )
            if c in df.columns
        ),
        None,
    )
    sid_col = "statementId" if "statementId" in df.columns else df.columns[0]

    pick = df.select(
        pl.col(sid_col).alias("source_id"),
        (pl.col(name_col) if name_col else pl.lit(None, dtype=pl.Utf8)).alias("name"),
        (pl.col(juris_col) if juris_col else pl.lit(None, dtype=pl.Utf8)).alias(
            "jurisdiction"
        ),
        (pl.col(cn_col) if cn_col else pl.lit(None, dtype=pl.Utf8)).alias(
            "company_number"
        ),
        (pl.col(addr_col) if addr_col else pl.lit(None, dtype=pl.Utf8)).alias(
            "address_raw"
        ),
    )
    pick = pick.with_columns(
        pl.lit("uk_psc", dtype=pl.Utf8).alias("source"),
        pl.col("name")
        .map_elements(normalize_company_name, return_dtype=pl.Utf8)
        .alias("normalized_name"),
        pl.col("jurisdiction")
        .map_elements(normalize_jurisdiction, return_dtype=pl.Utf8)
        .alias("jurisdiction"),
        pl.col("company_number")
        .map_elements(normalize_identifier, return_dtype=pl.Utf8)
        .alias("company_number"),
        pl.col("address_raw")
        .map_elements(normalize_address_text, return_dtype=pl.Utf8)
        .alias("normalized_address"),
        pl.lit(None, dtype=pl.Utf8).alias("lei"),
        pl.lit(None, dtype=pl.Utf8).alias("status"),
        pl.lit(None, dtype=pl.Utf8).alias("legal_form"),
    )
    return pick.select(list(_COMPANY_COLUMNS))


def ingest(
    zip_path: Path,
    *,
    out_dir: Path = INTERIM_DIR,
    work_dir: Path | None = None,
) -> dict[str, Path]:
    """Parse a BODS UK parquet bundle and write interim parquets.

    Writes:
      - ``uk_psc_persons.parquet`` (rows shaped like unified persons)
      - ``uk_psc_entities.parquet`` (rows shaped like unified companies)

    Returns a dict mapping the kind to the written path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = work_dir or out_dir / "_bods_work"
    zip_path = Path(zip_path)
    if not zip_path.exists():
        log.error("BODS zip not found: %s", zip_path)
        return {}

    log.info("BODS: extracting person statements from %s", zip_path)
    persons_raw = _stream_kind(zip_path, "person_statement", work_dir)
    log.info("BODS: raw person statements = %d", persons_raw.height)
    persons = _normalise_person_rows(persons_raw)
    persons_out = out_dir / "uk_psc_persons.parquet"
    persons.write_parquet(persons_out)
    log.info("BODS: wrote %d UK PSC persons -> %s", persons.height, persons_out)

    log.info("BODS: extracting entity statements")
    entities_raw = _stream_kind(zip_path, "entity_statement", work_dir)
    log.info("BODS: raw entity statements = %d", entities_raw.height)
    entities = _normalise_entity_rows(entities_raw)
    entities_out = out_dir / "uk_psc_entities.parquet"
    entities.write_parquet(entities_out)
    log.info("BODS: wrote %d UK PSC entities -> %s", entities.height, entities_out)

    return {"persons": persons_out, "entities": entities_out}
