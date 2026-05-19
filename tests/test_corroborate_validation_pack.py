"""Smoke tests for scripts/corroborate_validation_pack.py.

Pure helpers always run; the end-to-end test runs when an existing
validation pack is present on disk (the same path the build_validation_pack
test uses).
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "corroborate_validation_pack.py"
EXISTING_PACK = REPO_ROOT / "docs" / "validation" / "data" / "cluster_47_profile.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("corroborate_validation_pack", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["corroborate_validation_pack"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def cvp():
    return _load_module()


def test_extract_domain(cvp):
    assert cvp._extract_domain("https://www.icij.org/projects/paradise") == "icij.org"
    assert cvp._extract_domain("http://timesofmalta.com/articles/x") == "timesofmalta.com"
    assert cvp._extract_domain("") == ""


def test_classify_domain(cvp):
    d, t, s = cvp._classify_domain("https://offshoreleaks.icij.org/nodes/55044834")
    assert t == "leak_primary"
    assert s > 0.9
    d, t, s = cvp._classify_domain("https://medium.com/@someone/post")
    assert t == "blog"
    assert s < 0.5
    d, t, s = cvp._classify_domain("https://example.com/page")
    assert t == "unknown"


def test_norm_date(cvp):
    assert cvp._norm_date("2014-08-12") == "2014-08-12"
    assert cvp._norm_date("2014-08") == "2014-08-01"
    assert cvp._norm_date("2014") == "2014-01-01"
    assert cvp._norm_date("") == ""
    assert cvp._norm_date(None) == ""


def test_score_hits_supports_edge(cvp):
    results = [
        {
            "query": "test",
            "target_name": "STRATHAM FINANCE LIMITED",
            "result_title": "Calvin Ayre and Stratham Finance Limited",
            "url": "https://www.icij.org/x",
            "snippet": "calvin ayre is listed as officer of stratham finance limited in malta",
        }
    ]
    scored = cvp.score_hits(
        results,
        person="calvin edward ayre",
        member_names=["STRATHAM FINANCE LIMITED"],
    )
    assert len(scored) == 1
    assert scored[0]["supports_edge"] == "true"
    assert scored[0]["source_type"] == "leak_primary"
    assert "person" in scored[0]["matched_terms"]


def test_score_hits_low_quality(cvp):
    results = [
        {
            "query": "test",
            "target_name": "RANDOM CO LTD",
            "result_title": "Random blog post",
            "url": "https://example.com/blog",
            "snippet": "unrelated content",
        }
    ]
    scored = cvp.score_hits(results, person="ben", member_names=["RANDOM CO LTD"])
    assert scored[0]["needs_human_review"] == "true"
    assert scored[0]["relevance_score"] < 0.75


def test_csv_headers_unique(cvp):
    for hdrs in (
        cvp.SEARCH_RESULTS_HEADERS,
        cvp.HIT_SCORES_HEADERS,
        cvp.DISCOVERY_DELTA_HEADERS,
        cvp.TIMELINE_HEADERS,
        cvp.EVIDENCE_LEDGER_HEADERS,
        cvp.UNDERREPORTED_HEADERS,
    ):
        assert len(hdrs) >= 4
        assert len(set(hdrs)) == len(hdrs)


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src, f"absolute path {token!r} found"


@pytest.mark.skipif(not EXISTING_PACK.exists(), reason="cluster 47 pack not present")
def test_corroborate_runs_cluster_47(cvp, tmp_path):
    # Copy the cluster 47 pack into a tmp location so the test does not
    # write into the repo-tracked docs/validation/.
    src_data = EXISTING_PACK.parent
    src_md = src_data.parent / "cluster_47.md"
    dst_pack = tmp_path / "validation"
    dst_data = dst_pack / "data"
    dst_data.mkdir(parents=True)
    for f in src_data.glob("cluster_47_*"):
        (dst_data / f.name).write_bytes(f.read_bytes())
    (dst_pack / "cluster_47.md").write_bytes(src_md.read_bytes())

    paths = cvp.corroborate(
        community_id=47,
        person="peter kevin perry",
        pack_dir=dst_pack,
        run_external_search=False,
    )

    # Every expected output exists with the right header row (CSVs) or
    # non-trivial content (markdown).
    csv_checks = {
        "search_csv": cvp.SEARCH_RESULTS_HEADERS,
        "hit_scores": cvp.HIT_SCORES_HEADERS,
        "discovery_delta": cvp.DISCOVERY_DELTA_HEADERS,
        "timeline_csv": cvp.TIMELINE_HEADERS,
        "evidence_ledger": cvp.EVIDENCE_LEDGER_HEADERS,
        "underreported": cvp.UNDERREPORTED_HEADERS,
    }
    for key, expected in csv_checks.items():
        p = paths[key]
        assert p.exists(), f"missing {p}"
        with p.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            actual = next(reader)
        assert actual == expected

    for key in ("research_brief", "timeline_md", "graph_paths_md"):
        body = paths[key].read_text(encoding="utf-8")
        assert "cluster" in body.lower()
        assert "47" in body

    # Skeleton search (no Tavily) produces empty search_json + non-empty
    # discovery_delta (because structural facts always populate).
    raw = json.loads(paths["search_json"].read_text(encoding="utf-8"))
    assert raw == []

    with paths["discovery_delta"].open(encoding="utf-8") as f:
        delta_rows = list(csv.DictReader(f))
    assert any(r["category"] == "structural" for r in delta_rows)
