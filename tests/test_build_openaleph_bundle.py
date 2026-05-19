"""Smoke tests for scripts/build_openaleph_bundle.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_openaleph_bundle.py"
EXISTING_FTM = REPO_ROOT / "docs" / "validation" / "data" / "cluster_47_ftm.json"


def _load():
    spec = importlib.util.spec_from_file_location("build_openaleph_bundle", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_openaleph_bundle"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def b():
    return _load()


def test_manifest_shape(b):
    m = b.build_manifest(
        community_id=37,
        person="calvin edward ayre",
        profile={
            "n_members": 19,
            "queue_row": {"priority_score": 0.364},
            "ordinary_vs_unusual": {"officer_reuse_rate": 0.95, "address_reuse_rate": 0.95},
        },
        file_count=10,
        entity_count=106,
    )
    assert m["foreign_id"] == "gm-cluster-37-bundle"
    assert "calvin edward ayre".lower() in m["label"].lower()
    assert m["countries"] == ["mt"]
    assert m["stats"]["cluster_size"] == 19
    assert m["stats"]["n_ftm_entities"] == 106
    assert m["human_review_required"] is True


def test_describe_classifies_known_files(b):
    assert "narrative" in b._describe("documents/research_brief.md").lower()
    assert "dated" in b._describe("documents/timeline.md").lower()
    assert "claim" in b._describe("documents/evidence_ledger.csv").lower()
    assert "publicly" in b._describe("documents/discovery_delta.csv").lower()
    # Unknown files get the fallback description.
    assert b._describe("documents/unknown.xyz") == "Supporting artefact."


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src


@pytest.mark.skipif(not EXISTING_FTM.exists(), reason="cluster 47 FTM pack not present")
def test_bundle_runs_cluster_47(b, tmp_path):
    out = tmp_path / "bundle.zip"
    result = b.build_bundle(
        community_id=47,
        person="peter kevin perry",
        out_path=out,
    )
    assert result == out
    assert out.exists()

    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
        # Top-level required files.
        assert "manifest.json" in names
        assert "entities.ftm.json" in names
        assert "README.md" in names
        assert "_index.csv" in names
        # At least the research brief + evidence ledger should be in there.
        assert "documents/research_brief.md" in names
        assert "documents/evidence_ledger.csv" in names

        # Manifest parses + has expected stats.
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["foreign_id"] == "gm-cluster-47-bundle"
        assert manifest["stats"]["n_ftm_entities"] > 0

        # FTM file is non-empty ndjson.
        ftm_body = zf.read("entities.ftm.json").decode("utf-8")
        lines = [line for line in ftm_body.splitlines() if line.strip()]
        assert len(lines) >= 10
        # Every line should parse as a dict with id/schema.
        first = json.loads(lines[0])
        assert "id" in first and "schema" in first

        # README mentions the cluster + has the alephclient command.
        readme = zf.read("README.md").decode("utf-8")
        assert "Cluster 47" in readme
        assert "alephclient" in readme
