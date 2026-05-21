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
        # Disable archive_sources here: this test validates bundle
        # assembly, not the archiver. The default-on archive would
        # (a) hit ICIJ for real ~50+ times and (b) write an
        # archived_sources/ directory inside the repo's pack dir,
        # which leaks into other tests' globs.
        archive_sources=False,
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


def test_bundle_includes_archived_sources(b, tmp_path, monkeypatch):
    """Phase 18: the bundle must include archived ICIJ source-page HTML
    captures, not just URLs. Uses dependency-injected fetcher so the
    test never touches the network. Builds a minimal pack on disk."""
    import json

    pack = tmp_path / "pack"
    data = pack / "data"
    data.mkdir(parents=True)

    # Minimal FTM with one Person entity referencing an ICIJ URL.
    ftm_lines = [
        json.dumps(
            {
                "id": "gm-c99-p-icij-12345",
                "schema": "Person",
                "properties": {
                    "name": ["Test Person"],
                    "sourceUrl": ["https://offshoreleaks.icij.org/nodes/12345"],
                    "publisher": ["GoldenMatch test"],
                },
            }
        ),
        json.dumps(
            {
                "id": "gm-c99-co-icij-67890",
                "schema": "Company",
                "properties": {
                    "name": ["Test Company Ltd"],
                    "sourceUrl": ["https://offshoreleaks.icij.org/nodes/67890"],
                    "publisher": ["GoldenMatch test"],
                },
            }
        ),
    ]
    (data / "cluster_99_ftm.json").write_text("\n".join(ftm_lines), encoding="utf-8")

    # Stub the archiver's HTTP fetcher so no real network IO happens.
    import shellnet.archive.icij_archiver as archiver

    def fake_factory():
        def fake_fetcher(url: str, ua: str) -> tuple[int, bytes]:
            return (200, f"<html><body>captured {url}</body></html>".encode())

        return fake_fetcher

    monkeypatch.setattr(archiver, "_http_fetcher_factory", fake_factory)

    out = tmp_path / "out.zip"
    b.build_bundle(
        community_id=99,
        person="test person",
        pack_dir=pack,
        out_path=out,
        archive_min_interval_s=0.0,
        archive_request_wayback=False,
    )

    import zipfile

    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
        # Both ICIJ pages captured under archived_sources/icij/nodes/
        assert "archived_sources/icij/nodes/12345.html" in names, sorted(names)
        assert "archived_sources/icij/nodes/67890.html" in names
        # Manifest documents the captures.
        assert "archived_sources/icij/manifest.json" in names
        manifest = json.loads(zf.read("archived_sources/icij/manifest.json"))
        assert len(manifest["entries"]) == 2
        assert all(e["status_code"] == 200 for e in manifest["entries"])
        # Bundle manifest carries the archive summary.
        bundle_manifest = json.loads(zf.read("manifest.json"))
        archive_stats = bundle_manifest["stats"]["archived_sources"]
        assert archive_stats["succeeded"] == 2
        assert archive_stats["failed"] == 0


def test_no_archive_sources_flag_skips_archival(b, tmp_path):
    """The --no-archive-sources flag (archive_sources=False) skips the
    fetch step entirely — no archived_sources/ subtree in the zip."""
    import json

    pack = tmp_path / "pack"
    data = pack / "data"
    data.mkdir(parents=True)
    (data / "cluster_99_ftm.json").write_text(
        json.dumps(
            {
                "id": "x",
                "schema": "Person",
                "properties": {
                    "name": ["X"],
                    "sourceUrl": ["https://offshoreleaks.icij.org/nodes/1"],
                },
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.zip"
    b.build_bundle(
        community_id=99,
        person="x",
        pack_dir=pack,
        out_path=out,
        archive_sources=False,
    )

    import zipfile

    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert not any(n.startswith("archived_sources/") for n in names), names
        # Bundle manifest still has the field, with zero counts.
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["stats"]["archived_sources"]["succeeded"] == 0
