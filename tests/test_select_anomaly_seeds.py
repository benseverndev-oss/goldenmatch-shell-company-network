"""Phase 11 — anomaly-seed selector tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "select_anomaly_seeds.py"


def _load():
    spec = importlib.util.spec_from_file_location("select_anomaly_seeds", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["select_anomaly_seeds"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load()


def _make_anomalies(rows: list[tuple[int, float]]) -> pl.DataFrame:
    """(community_id, anomaly_score) tuples."""
    return pl.DataFrame(
        {
            "community_id": [r[0] for r in rows],
            "anomaly_score": [r[1] for r in rows],
        }
    )


def _make_communities(rows: list[tuple[str, int]], threshold: float = 0.9) -> pl.DataFrame:
    """(node_uid, community_id) tuples at the given threshold."""
    return pl.DataFrame(
        {
            "node_uid": [r[0] for r in rows],
            "threshold": [threshold] * len(rows),
            "community_id": [r[1] for r in rows],
        }
    )


def test_picks_top_n_by_anomaly_score(mod):
    anomalies = _make_anomalies([(10, 0.9), (20, 0.85), (30, 0.7), (40, 0.55), (50, 0.4)])
    communities = _make_communities(
        [
            ("a", 10),
            ("b", 10),
            ("c", 20),
            ("d", 30),
            ("e", 40),
            ("f", 50),
        ]
    )
    out = mod.select(anomalies, communities, top_n=2, min_anomaly_score=0.5)
    uids = set(out["uid"].to_list())
    # Top 2 anomaly communities are 10 and 20 -> uids a, b, c.
    assert uids == {"a", "b", "c"}, uids


def test_min_anomaly_score_filter(mod):
    anomalies = _make_anomalies([(10, 0.9), (20, 0.6), (30, 0.3)])
    communities = _make_communities([("a", 10), ("b", 20), ("c", 30)])
    out = mod.select(anomalies, communities, top_n=10, min_anomaly_score=0.65)
    assert set(out["uid"].to_list()) == {"a"}


def test_returns_unique_uids(mod):
    """A UID appearing in multiple top communities surfaces only once."""
    anomalies = _make_anomalies([(10, 0.9), (20, 0.85)])
    communities = _make_communities(
        [
            ("a", 10),
            ("a", 20),  # same uid in two top communities — rare but possible
            ("b", 10),
        ]
    )
    out = mod.select(anomalies, communities, top_n=10, min_anomaly_score=0.5)
    assert sorted(out["uid"].to_list()) == ["a", "b"]


def test_empty_when_no_communities_meet_threshold(mod):
    anomalies = _make_anomalies([(10, 0.3), (20, 0.2)])
    communities = _make_communities([("a", 10), ("b", 20)])
    out = mod.select(anomalies, communities, top_n=10, min_anomaly_score=0.5)
    assert out.is_empty()
    assert set(out.columns) == {"uid", "community_id", "anomaly_score"}


def test_threshold_filter(mod):
    """Communities outside the requested threshold are ignored."""
    anomalies = _make_anomalies([(10, 0.9)])
    # Two memberships for community 10, at thresholds 0.5 and 0.9.
    communities = pl.DataFrame(
        {
            "node_uid": ["a", "b"],
            "threshold": [0.5, 0.9],
            "community_id": [10, 10],
        }
    )
    out = mod.select(anomalies, communities, top_n=10, threshold=0.9)
    # Only the 0.9-threshold member b.
    assert out["uid"].to_list() == ["b"]


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
