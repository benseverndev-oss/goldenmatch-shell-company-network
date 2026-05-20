"""Phase 4 — BODS v0.4 exporter tests."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "export_validation_pack_bods.py"


def _load():
    spec = importlib.util.spec_from_file_location("export_validation_pack_bods", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["export_validation_pack_bods"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load()


@pytest.fixture
def fake_pack(tmp_path: Path) -> Path:
    """Materialise a minimal validation pack on disk."""
    data = tmp_path / "data"
    data.mkdir()

    profile = {
        "person_uids": ["icij:E12345"],
        "members_sample": [
            {
                "uid": "icij:CO-1",
                "name": "PROBUTEC (MALTA) LTD",
                "jurisdiction": "MT",
                "seed": True,
            },
            {
                "uid": "icij:CO-2",
                "name": "I-CAP MARINE SERVICES LIMITED",
                "jurisdiction": "GB",
                "seed": False,
            },
        ],
    }
    (data / "cluster_42_profile.json").write_text(json.dumps(profile), encoding="utf-8")

    with (data / "cluster_42_person_company_roles.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "company_name",
                "company_record_id",
                "role",
                "start_date",
                "end_date",
                "leak",
                "notes",
                "person_record_id",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "company_name": "PROBUTEC (MALTA) LTD",
                "company_record_id": "icij:CO-1",
                "role": "Shareholder",
                "start_date": "2001-01-01",
                "end_date": "",
                "leak": "Paradise Papers",
                "notes": "",
                "person_record_id": "icij:E12345",
            }
        )

    with (data / "cluster_42_repeated_addresses.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["address", "n_linked_companies", "linked_companies"])
        w.writeheader()

    with (data / "cluster_42_repeated_officers.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "officer_name",
                "n_linked_companies",
                "roles",
                "linked_companies",
                "source_label",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "officer_name": "JANE Q DOE",
                "n_linked_companies": "2",
                "roles": "Director",
                "linked_companies": "PROBUTEC (MALTA) LTD;I-CAP MARINE SERVICES LIMITED",
                "source_label": "Paradise Papers",
            }
        )

    return tmp_path


def test_export_emits_valid_ndjson(mod, fake_pack):
    out = mod.export(
        community_id=42,
        person="calvin edward ayre",
        pack_dir=fake_pack,
    )
    assert out.exists()
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 3
    for line in lines:
        json.loads(line)  # each line must be parseable JSON.


def test_export_statement_shape(mod, fake_pack):
    out = mod.export(community_id=42, person="calvin edward ayre", pack_dir=fake_pack)
    stmts = [json.loads(line) for line in out.read_text(encoding="utf-8").strip().splitlines()]

    types = {s["statementType"] for s in stmts}
    assert "personStatement" in types
    assert "entityStatement" in types
    assert "ownershipOrControlStatement" in types

    for s in stmts:
        assert "statementId" in s
        assert s["statementId"].startswith("openownership-")
        assert s["publicationDetails"]["bodsVersion"] == "0.4"
        assert s["publicationDetails"]["publisher"]["url"].startswith("https://github.com/")


def test_entity_statement_carries_jurisdiction(mod, fake_pack):
    out = mod.export(community_id=42, person="calvin edward ayre", pack_dir=fake_pack)
    stmts = [json.loads(line) for line in out.read_text(encoding="utf-8").strip().splitlines()]
    ents = [s for s in stmts if s["statementType"] == "entityStatement"]
    by_name = {e["name"]: e for e in ents}
    assert "PROBUTEC (MALTA) LTD" in by_name
    assert by_name["PROBUTEC (MALTA) LTD"]["jurisdiction"]["code"] == "MT"


def test_ooc_statement_links_subject_and_interested(mod, fake_pack):
    out = mod.export(community_id=42, person="calvin edward ayre", pack_dir=fake_pack)
    stmts = [json.loads(line) for line in out.read_text(encoding="utf-8").strip().splitlines()]
    oocs = [s for s in stmts if s["statementType"] == "ownershipOrControlStatement"]
    assert oocs
    for o in oocs:
        # subject must point at an entityStatement.
        assert "describedByEntityStatement" in o["subject"]
        # interestedParty must point at either a person- or entity-statement.
        ip = o["interestedParty"]
        assert ("describedByPersonStatement" in ip) or ("describedByEntityStatement" in ip)
        assert o["interests"][0]["type"] in {
            "shareholding",
            "voting-rights",
            "appointment-of-board",
            "other-influence-or-control",
        }


def test_export_is_deterministic(mod, fake_pack):
    """Running twice must produce identical output (statementIds are content-hashed)."""
    out1 = mod.export(
        community_id=42,
        person="calvin edward ayre",
        pack_dir=fake_pack,
        out_path=fake_pack / "data" / "out_a.json",
    )
    out2 = mod.export(
        community_id=42,
        person="calvin edward ayre",
        pack_dir=fake_pack,
        out_path=fake_pack / "data" / "out_b.json",
    )
    assert out1.read_bytes() == out2.read_bytes()


def test_shareholder_role_maps_to_shareholding(mod):
    s = mod._ooc_statement(
        subject_uid="icij:CO-1",
        interested_uid="icij:E12345",
        interested_is_person=True,
        role="Shareholder",
    )
    assert s["interests"][0]["type"] == "shareholding"


def test_director_role_maps_to_voting_rights(mod):
    s = mod._ooc_statement(
        subject_uid="icij:CO-1",
        interested_uid="icij:E12345",
        interested_is_person=True,
        role="Director",
    )
    assert s["interests"][0]["type"] == "voting-rights"


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
