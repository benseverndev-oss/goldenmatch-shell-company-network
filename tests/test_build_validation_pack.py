"""Smoke tests for scripts/build_validation_pack.py.

These run against the real source parquets when present (so the test
exercises the full code path on the actual cluster-47 / Perry pair),
and fall back to skipping when the data files are not available — the
script is for an analyst's machine, not a hermetic CI runner.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_validation_pack.py"
COMMUNITIES_PARQUET = REPO_ROOT / "docs" / "reports" / "data" / "confidence_communities.parquet"
DOSSIER_FILE = REPO_ROOT / "docs" / "reports" / "dossiers" / "peter-kevin-perry.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_validation_pack", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can resolve cls.__module__ via sys.modules.
    sys.modules["build_validation_pack"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bvp():
    return _load_module()


# ---- pure-function tests (always run) ------------------------------------


def test_normalize_person_query(bvp):
    assert bvp.normalize_person_query("  Peter   Kevin\tPerry ") == "peter kevin perry"
    assert bvp.normalize_person_query("PETER KEVIN PERRY") == "peter kevin perry"


def test_parse_dossier_companies(bvp):
    sample = (
        "## linked\n"
        "- AWEIGH YACHTING LTD (mt) — address: `—`\n"
        "- Prism Lights Ltd. (mt) — address: `1 High St`\n"
        "- something unrelated\n"
    )
    rows = bvp.parse_dossier_companies(sample)
    assert len(rows) == 2
    names = {r["name"] for r in rows}
    assert "AWEIGH YACHTING LTD" in names
    assert all(r["jurisdiction"] == "mt" for r in rows)


def test_classify_themes_picks_keyword(bvp):
    member = bvp.MemberEntity(
        uid="icij:1",
        name="DOLPHIN YACHTING LTD",
        normalized_name="dolphin yachting",
        jurisdiction="mt",
        address=None,
        source_id="1",
        is_seed=False,
    )
    rows = bvp.classify_themes([member])
    assert rows[0]["theme"] == "yachting / charter / vessel"
    assert rows[0]["needs_manual_review"] == "true"


def test_csv_headers_match_constants(bvp):
    # Sanity: the public header lists are non-empty and unique.
    for headers in (
        bvp.OVERLAP_HEADERS,
        bvp.ROLES_HEADERS,
        bvp.ADDR_HEADERS,
        bvp.OFFICER_HEADERS,
        bvp.AGENT_HEADERS,
        bvp.THEME_HEADERS,
        bvp.QUERY_HEADERS,
    ):
        assert len(headers) >= 4
        assert len(set(headers)) == len(headers)


# ---- end-to-end (real-data) ----------------------------------------------


pytestmark_e2e = pytest.mark.skipif(
    not (COMMUNITIES_PARQUET.exists() and DOSSIER_FILE.exists()),
    reason="real source data not available",
)


@pytestmark_e2e
def test_build_pack_runs_cluster_47(bvp, tmp_path):
    paths = bvp.build_pack(
        community_id=47,
        person="peter kevin perry",
        out_dir=tmp_path,
    )
    assert paths["markdown"].exists()
    md = paths["markdown"].read_text(encoding="utf-8")
    assert "Cluster 47 Validation Pack" in md
    assert "Human review required" in md
    assert "peter kevin perry" in md.lower()

    # Every CSV exists and has the right header row.
    csv_checks = {
        "overlap_csv": bvp.OVERLAP_HEADERS,
        "roles_csv": bvp.ROLES_HEADERS,
        "addresses_csv": bvp.ADDR_HEADERS,
        "officers_csv": bvp.OFFICER_HEADERS,
        "agents_csv": bvp.AGENT_HEADERS,
        "themes_csv": bvp.THEME_HEADERS,
        "queries_csv": bvp.QUERY_HEADERS,
    }
    for key, expected_headers in csv_checks.items():
        p = paths[key]
        assert p.exists(), f"missing {p}"
        with p.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            actual = next(reader)
        assert actual == expected_headers, f"{key} header mismatch"

    assert paths["graph_paths_md"].exists()
    assert paths["profile_json"].exists()
    profile = json.loads(paths["profile_json"].read_text(encoding="utf-8"))
    assert profile["community_id"] == 47
    assert profile["person_normalized"] == "peter kevin perry"
    assert profile["n_members"] >= 3  # cluster 47 has 67 members

    # Idempotent: running again on the same out_dir should not raise.
    bvp.build_pack(community_id=47, person="peter kevin perry", out_dir=tmp_path)


@pytestmark_e2e
def test_build_pack_unknown_person_raises(bvp, tmp_path):
    with pytest.raises(SystemExit):
        bvp.build_pack(
            community_id=47,
            person="zzz nonexistent person zzz",
            out_dir=tmp_path,
        )


@pytestmark_e2e
def test_build_pack_unknown_community_raises(bvp, tmp_path):
    with pytest.raises(SystemExit):
        bvp.build_pack(
            community_id=999_999,
            person="peter kevin perry",
            out_dir=tmp_path,
        )


def test_no_hardcoded_absolute_paths():
    """The script must work from any checkout location."""
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden = ("C:\\Users", "/home/", "/Users/")
    for token in forbidden:
        assert token not in src, f"absolute path {token!r} found in script"
