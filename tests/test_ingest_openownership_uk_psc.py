"""Smoke tests for scripts/ingest_openownership_uk_psc.py.

Can't hit the 3.5 GB live bundle from CI, so we synthesise small
fixture parquets that match the BODS v0.4 column shape and run the
projection helpers against them.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ingest_openownership_uk_psc.py"


def _load():
    spec = importlib.util.spec_from_file_location("ingest_openownership_uk_psc", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["ingest_openownership_uk_psc"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def oo():
    return _load()


@pytest.fixture
def fixture_bundle(tmp_path):
    """Synthesise a minimal BODS bundle directory with the three tables
    the projector reads. Schemas mirror the OO output."""

    bundle = tmp_path / "bundle"
    bundle.mkdir()

    # Two companies + one PSC person + one ownership relationship.
    entities = pl.DataFrame(
        {
            "recordDetails_subject": ["GB-COH-00001", "GB-COH-00002"],
            "recordDetails_name": ["ACME LTD", "WIDGETS PLC"],
            "recordDetails_entityType_subtype": ["LimitedCompany", "PublicCompany"],
            "recordDetails_jurisdiction_code": ["GB", "GB"],
            "recordDetails_foundingDate": ["2010-01-01", "2015-06-01"],
            "recordDetails_dissolutionDate": [None, None],
            "statementDate": ["2024-03-01", "2024-04-01"],
            "publicationDetails_publicationDate": ["2025-03-05", "2025-03-05"],
        }
    )
    entities.write_parquet(bundle / "entity_statement.parquet")

    person_stmt = pl.DataFrame(
        {
            "_link": ["p1"],
            "recordDetails_personType": ["knownPerson"],
            "recordDetails_birthDate": ["1970-04"],
            "statementDate": ["2024-05-01"],
            "publicationDetails_publicationDate": ["2025-03-05"],
            "recordId": ["GB-COH-PER-00001-xyz"],
        }
    )
    person_stmt.write_parquet(bundle / "person_statement.parquet")

    person_names = pl.DataFrame(
        {
            "_link": ["p1"],
            "type": ["individual"],
            "fullName": ["John Doe"],
            "givenName": ["John"],
            "familyName": ["Doe"],
        }
    )
    person_names.write_parquet(bundle / "person_recorddetails_names.parquet")

    person_nat = pl.DataFrame({"_link": ["p1"], "code": ["GB"]})
    person_nat.write_parquet(bundle / "person_recorddetails_nationalities.parquet")

    relationships = pl.DataFrame(
        {
            "recordDetails_subject": ["GB-COH-00001"],
            "recordDetails_interestedParty": ["GB-COH-PER-00001-xyz"],
            "recordDetails_isComponent": [False],
            "statementDate": ["2024-05-01"],
            "publicationDetails_publicationDate": ["2025-03-05"],
            "recordId": ["GB-COH-REL-00001-xyz"],
        }
    )
    relationships.write_parquet(bundle / "relationship_statement.parquet")

    return bundle


def test_entity_uid_helper(oo):
    assert oo._entity_uid("GB-COH-14040750") == "oo:gb-coh-14040750"
    assert oo._entity_uid(None) == ""
    assert oo._entity_uid("") == ""


def test_project_entities(oo, fixture_bundle):
    df = oo.project_entities(fixture_bundle)
    assert df.shape[0] == 2
    assert set(df["entity_uid"].to_list()) == {"oo:gb-coh-00001", "oo:gb-coh-00002"}
    assert set(df.columns) >= {
        "entity_uid",
        "name",
        "jurisdiction",
        "source",
        "source_label",
    }
    assert (df["source"] == "oo_uk_psc").all()


def test_project_persons(oo, fixture_bundle):
    df = oo.project_persons(fixture_bundle)
    assert df.shape[0] == 1
    row = df.row(0, named=True)
    assert row["name"] == "John Doe"
    assert row["nationality"] == "GB"
    assert row["entity_uid"].startswith("oo:gb-coh-per-00001")


def test_project_relationships(oo, fixture_bundle):
    df = oo.project_relationships(fixture_bundle)
    assert df.shape[0] == 1
    row = df.row(0, named=True)
    assert row["src_node"].startswith("oo:gb-coh-per-")
    assert row["dst_node"] == "oo:gb-coh-00001"
    assert row["kind_raw"] == "psc_controller_of"
    assert row["source"] == "oo_uk_psc"


def test_ingest_end_to_end(oo, fixture_bundle, tmp_path):
    # Skip download by pre-populating the zip slot, then point the work
    # dir at the already-extracted fixture bundle so extract_bundle is a no-op.
    fake_zip = tmp_path / "noop.zip"
    fake_zip.write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # minimal empty zip

    out_dir = tmp_path / "out"
    work = tmp_path / "work"
    work.mkdir()
    # Copy fixture parquets into the work dir so extract_bundle finds them.
    for p in fixture_bundle.iterdir():
        (work / p.name).write_bytes(p.read_bytes())

    # We patch extract_bundle to a no-op since we pre-populated work.
    orig_extract = oo.extract_bundle
    oo.extract_bundle = lambda zip_path, out: out
    try:
        paths = oo.ingest(
            bundle_zip=fake_zip,
            out_dir=out_dir,
            work_dir=work,
            download_if_missing=False,
            cleanup_extracted=False,
        )
    finally:
        oo.extract_bundle = orig_extract

    assert all(p.exists() for p in paths.values())
    ents = pl.read_parquet(paths["entities"])
    assert ents.shape[0] == 2


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
