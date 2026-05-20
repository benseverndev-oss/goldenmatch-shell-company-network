"""Ingest Open Ownership's processed UK PSC BODS bundle into our pipeline.

Open Ownership publishes the UK Persons with Significant Control register
+ Register of Overseas Entities pre-processed into BODS v0.4 Parquet
files. License is CC0 (public domain dedication). Bundle URL::

    https://oo-bodsdata.s3.amazonaws.com/data/uk_version_0_4/parquet.zip
    (~3.5 GB, last refreshed 2025-03-11 at time of writing)

The bundle is Flatterer-flattened — one parquet per BODS table. We
project the three tables we actually use into our normalized pipeline
shape:

- ``entity_statement.parquet``       → ``oo_uk_psc_entities.parquet``
- ``person_statement.parquet``       → ``oo_uk_psc_persons.parquet``
- ``relationship_statement.parquet`` → ``oo_uk_psc_relationships.parquet``

The output columns mirror the conventions of our existing
``icij_*.parquet`` files so the discovery pipeline can join on
``entity_uid`` and walk ownership edges without further work.

Heavy compute — designed to run on Railway via the job server.

Usage (Railway)::

    POST /run-script?name=ingest_openownership_uk_psc

Usage (local, with a pre-downloaded zip)::

    uv run python scripts/ingest_openownership_uk_psc.py \\
        --bundle-zip /data/raw/openownership/uk_psc_v0_4.zip \\
        --out-dir /data/processed
"""

from __future__ import annotations

import argparse
import logging
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
import polars as pl

log = logging.getLogger("ingest_openownership_uk_psc")

BUNDLE_URL = "https://oo-bodsdata.s3.amazonaws.com/data/uk_version_0_4/parquet.zip"
SOURCE_LABEL = "Open Ownership UK PSC (BODS v0.4)"
LICENSE = "CC0-1.0"


# ---------------------------------------------------------------------------
# Download + unzip
# ---------------------------------------------------------------------------


def ensure_bundle(bundle_zip: Path, *, url: str = BUNDLE_URL, force: bool = False) -> Path:
    """Download the bundle if not already present. Returns the local zip path."""

    if bundle_zip.exists() and not force:
        log.info(
            "bundle already present at %s (%.1f MB)",
            bundle_zip,
            bundle_zip.stat().st_size / 1024 / 1024,
        )
        return bundle_zip
    bundle_zip.parent.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s -> %s", url, bundle_zip)
    tmp = bundle_zip.with_suffix(".zip.partial")
    with (
        httpx.stream("GET", url, timeout=None, follow_redirects=True) as r,
        tmp.open("wb") as f,
    ):
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        written = 0
        for chunk in r.iter_bytes(8 * 1024 * 1024):
            f.write(chunk)
            written += len(chunk)
            if total:
                pct = 100 * written / total
                if int(pct) % 5 == 0:
                    log.info(
                        "  %.0f%% (%.1f MB / %.1f MB)",
                        pct,
                        written / 1024 / 1024,
                        total / 1024 / 1024,
                    )
    tmp.replace(bundle_zip)
    return bundle_zip


def extract_bundle(bundle_zip: Path, out_dir: Path) -> Path:
    """Unzip the bundle. Returns the directory containing the parquets."""

    out_dir.mkdir(parents=True, exist_ok=True)
    log.info("extracting %s -> %s", bundle_zip, out_dir)
    with zipfile.ZipFile(bundle_zip) as zf:
        zf.extractall(out_dir)
    # OO ships everything at the top level of the zip; no subdir prefix.
    return out_dir


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def _entity_uid(bods_subject: str | None) -> str:
    """Convert a BODS declarationSubject (e.g. ``GB-COH-14040750``) to an
    entity_uid suitable for our pipeline."""
    if not bods_subject:
        return ""
    # Convention: keep the BODS form, lowercased, prefixed `oo:` so it
    # never collides with icij:, gleif:, etc.
    return f"oo:{bods_subject.lower()}"


def project_entities(bundle_dir: Path) -> pl.DataFrame:
    """Project entity_statement.parquet into our pipeline shape.

    OO's BODS export tracks the BODS spec. In v0.4 the schema flattened —
    ``recordDetails_subject`` moved up to ``declarationSubject``,
    ``recordDetails_entityType_subtype`` collapsed into
    ``recordDetails_entityType_type``, and ``recordDetails_dissolutionDate``
    was removed. We accept both shapes so a future schema bump doesn't
    silently lose the older one.
    """

    src = bundle_dir / "entity_statement.parquet"
    log.info("reading %s", src)
    cols = set(pl.scan_parquet(src).collect_schema().names())
    subject_col = "declarationSubject" if "declarationSubject" in cols else "recordDetails_subject"
    entity_type_col = (
        "recordDetails_entityType_type"
        if "recordDetails_entityType_type" in cols
        else "recordDetails_entityType_subtype"
    )
    has_dissolution = "recordDetails_dissolutionDate" in cols

    selects = [
        pl.col(subject_col).alias("bods_subject"),
        pl.col("recordDetails_name").alias("name"),
        pl.col(entity_type_col).alias("entity_type"),
        pl.col("recordDetails_jurisdiction_code").alias("jurisdiction"),
        pl.col("recordDetails_foundingDate").alias("incorporation_date"),
        pl.col("statementDate").alias("statement_date"),
        pl.col("publicationDetails_publicationDate").alias("publication_date"),
    ]
    if has_dissolution:
        selects.insert(
            5, pl.col("recordDetails_dissolutionDate").alias("dissolution_date")
        )
    else:
        selects.insert(5, pl.lit(None).cast(pl.String).alias("dissolution_date"))

    out = (
        pl.scan_parquet(src)
        .select(*selects)
        .with_columns(
            (pl.lit("oo:") + pl.col("bods_subject").str.to_lowercase()).alias("entity_uid"),
            pl.lit("oo_uk_psc").alias("source"),
            pl.lit(SOURCE_LABEL).alias("source_label"),
        )
        .collect()
    )
    log.info("  %d entity rows (subject_col=%s)", out.shape[0], subject_col)
    return out


def project_persons(bundle_dir: Path) -> pl.DataFrame:
    """Project person_statement.parquet + the names table into our shape."""

    stmt = pl.scan_parquet(bundle_dir / "person_statement.parquet")
    names = pl.scan_parquet(bundle_dir / "person_recorddetails_names.parquet")
    nat = None
    nat_path = bundle_dir / "person_recorddetails_nationalities.parquet"
    if nat_path.exists():
        nat = pl.scan_parquet(nat_path)

    # Take the "individual" full name where present.
    name_df = (
        names.filter(pl.col("type") == "individual")
        .group_by("_link")
        .agg(
            pl.col("fullName").first().alias("name"),
            pl.col("givenName").first().alias("given_name"),
            pl.col("familyName").first().alias("family_name"),
        )
    )

    nat_df = None
    if nat is not None:
        nat_df = nat.group_by("_link").agg(pl.col("code").first().alias("nationality"))

    base = stmt.select(
        pl.col("_link"),
        pl.col("recordDetails_personType").alias("person_type"),
        pl.col("recordDetails_birthDate").alias("birth_date"),
        pl.col("statementDate").alias("statement_date"),
        pl.col("publicationDetails_publicationDate").alias("publication_date"),
        pl.col("recordId"),
    )
    joined = base.join(name_df, on="_link", how="left")
    if nat_df is not None:
        joined = joined.join(nat_df, on="_link", how="left")

    out = joined.with_columns(
        (pl.lit("oo:") + pl.col("recordId").str.to_lowercase()).alias("entity_uid"),
        pl.lit("oo_uk_psc").alias("source"),
        pl.lit(SOURCE_LABEL).alias("source_label"),
    ).collect()
    log.info("  %d person rows", out.shape[0])
    return out


def project_relationships(bundle_dir: Path) -> pl.DataFrame:
    """Project the relationship_statement parquet into edge shape that
    matches our existing icij_edges layout."""

    src = bundle_dir / "relationship_statement.parquet"
    log.info("reading %s", src)
    cols = set(pl.scan_parquet(src).collect_schema().names())
    # BODS 0.4 flattened recordDetails_subject -> declarationSubject and
    # recordDetails_interestedParty -> interestedParty (and may have split
    # the interestedParty into recordDetails_interests_* sub-fields). We
    # accept both old and new top-level names.
    subject_col = (
        "declarationSubject" if "declarationSubject" in cols else "recordDetails_subject"
    )
    interested_col = (
        "interestedParty"
        if "interestedParty" in cols
        else "recordDetails_interestedParty"
    )
    df = pl.scan_parquet(src)
    out = (
        df.select(
            pl.col(subject_col).alias("subject"),
            pl.col(interested_col).alias("interested_party"),
            pl.col("recordDetails_isComponent").alias("is_component"),
            pl.col("statementDate").alias("start_date"),
            pl.col("publicationDetails_publicationDate").alias("publication_date"),
            pl.col("recordId"),
        )
        .with_columns(
            (pl.lit("oo:") + pl.col("interested_party").str.to_lowercase()).alias("src_node"),
            (pl.lit("oo:") + pl.col("subject").str.to_lowercase()).alias("dst_node"),
            pl.lit("psc_controller_of").alias("kind_raw"),
            pl.lit("").alias("role"),
            pl.lit("").alias("end_date"),
            pl.lit(SOURCE_LABEL).alias("source_label"),
            pl.lit("oo_uk_psc").alias("source"),
        )
        .filter(pl.col("interested_party").is_not_null())
        .select(
            "source",
            "src_node",
            "dst_node",
            "kind_raw",
            "role",
            "start_date",
            "end_date",
            "source_label",
            "is_component",
            "recordId",
        )
        .collect()
    )
    log.info("  %d relationship rows", out.shape[0])
    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def ingest(
    *,
    bundle_zip: Path,
    out_dir: Path,
    work_dir: Path | None = None,
    download_if_missing: bool = True,
    cleanup_extracted: bool = True,
) -> dict[str, Path]:
    """Top-level driver. Returns a dict of {kind: output_parquet_path}."""

    if download_if_missing:
        ensure_bundle(bundle_zip)
    if not bundle_zip.exists():
        raise SystemExit(f"[fatal] bundle missing: {bundle_zip}")

    work = work_dir or Path(tempfile.mkdtemp(prefix="oo-uk-psc-"))
    try:
        extract_bundle(bundle_zip, work)
        entities = project_entities(work)
        persons = project_persons(work)
        relationships = project_relationships(work)
    finally:
        if cleanup_extracted and work_dir is None and work.exists():
            shutil.rmtree(work, ignore_errors=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "entities": out_dir / "oo_uk_psc_entities.parquet",
        "persons": out_dir / "oo_uk_psc_persons.parquet",
        "relationships": out_dir / "oo_uk_psc_relationships.parquet",
    }
    entities.write_parquet(paths["entities"])
    persons.write_parquet(paths["persons"])
    relationships.write_parquet(paths["relationships"])
    log.info(
        "wrote %d entities, %d persons, %d relationships at %s",
        entities.shape[0],
        persons.shape[0],
        relationships.shape[0],
        datetime.now(UTC).isoformat(timespec="seconds"),
    )
    return paths


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Ingest Open Ownership's processed UK PSC BODS v0.4 bundle "
            "into the project's pipeline. Heavy compute; intended for "
            "Railway-side execution."
        )
    )
    p.add_argument(
        "--bundle-zip",
        type=Path,
        default=Path("/data/raw/openownership/uk_psc_v0_4.zip"),
        help="Local path for the bundle zip (downloaded if missing).",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("/data/processed"),
        help="Where to write the projected parquets.",
    )
    p.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Optional persistent extraction directory; defaults to a tempdir.",
    )
    p.add_argument(
        "--no-download",
        action="store_true",
        help="Fail if the bundle is missing rather than downloading.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    paths = ingest(
        bundle_zip=args.bundle_zip,
        out_dir=args.out_dir,
        work_dir=args.work_dir,
        download_if_missing=not args.no_download,
    )
    for kind, path in paths.items():
        print(f"{kind:14s} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
