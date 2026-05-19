"""Smoke tests for scripts/export_validation_pack_ftm.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "export_validation_pack_ftm.py"
EXISTING_PACK = REPO_ROOT / "docs" / "validation" / "data" / "cluster_47_profile.json"


def _load():
    spec = importlib.util.spec_from_file_location("export_validation_pack_ftm", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_validation_pack_ftm"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ftm():
    return _load()


def test_slug(ftm):
    assert ftm._slug("ABC 123!") == "abc-123"
    assert ftm._slug("icij:56077208") == "icij-56077208"
    assert ftm._slug("") == "x"


def test_icij_source_url(ftm):
    assert ftm._icij_source_url("icij:55044834") == "https://offshoreleaks.icij.org/nodes/55044834"
    assert ftm._icij_source_url("name:foo") == ""
    assert ftm._icij_source_url(None) == ""


def test_entity_dedupes_values(ftm):
    e = ftm._Entity("Person", "p1")
    e.add("name", "Alice")
    e.add("name", "Alice")
    e.add("name", "Alice Cooper")
    e.add("name", None)
    e.add("name", "")
    assert e.properties["name"] == ["Alice", "Alice Cooper"]


def test_entity_rejects_unknown_schema(ftm):
    with pytest.raises(ValueError, match="unsupported FTM schema"):
        ftm._Entity("Wombat", "x")


def test_country_from_jurisdiction(ftm):
    assert ftm._country_from_jurisdiction("mt") == "mt"
    assert ftm._country_from_jurisdiction("MT") == "mt"
    assert ftm._country_from_jurisdiction("malta") == ""
    assert ftm._country_from_jurisdiction(None) == ""


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src


@pytest.mark.skipif(not EXISTING_PACK.exists(), reason="cluster 47 pack not present")
def test_export_runs_cluster_47(ftm, tmp_path):
    out = tmp_path / "out.ftm.json"
    result = ftm.export(
        community_id=47,
        person="peter kevin perry",
        out_path=out,
    )
    assert result == out
    assert out.exists()

    with out.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    # At least one of every key schema we use.
    schemas = {r["schema"] for r in rows}
    assert {"Person", "Company", "Address", "Directorship"}.issubset(schemas)

    # Anchor exists and is the Person we asked for.
    person_rows = [r for r in rows if r["schema"] == "Person"]
    anchor = next(
        (r for r in person_rows if "Peter Kevin Perry" in r["properties"].get("name", [])),
        None,
    )
    assert anchor is not None
    assert anchor["properties"]["publisher"] == [ftm.PUBLISHER]
    # ICIJ uids carried through.
    assert any(uid.startswith("icij:") for uid in anchor["properties"]["idNumber"])

    # Every Directorship references entities that exist in the file.
    all_ids = {r["id"] for r in rows}
    for r in rows:
        if r["schema"] != "Directorship":
            continue
        for prop in ("director", "organization"):
            for ref in r["properties"].get(prop, []):
                assert ref in all_ids, f"dangling ref {ref} in {r['id']}"
