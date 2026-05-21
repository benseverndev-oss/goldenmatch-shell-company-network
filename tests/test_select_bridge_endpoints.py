"""Phase 16 — bridge-endpoint seed selector tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "select_bridge_endpoints.py"


def _load():
    spec = importlib.util.spec_from_file_location("select_bridge_endpoints", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["select_bridge_endpoints"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load()


def _bridges(rows: list[tuple[str, str]]) -> pl.DataFrame:
    """(src_uid, dst_uid) tuples — enough to round-trip the script."""
    return pl.DataFrame(
        {
            "src_uid": [r[0] for r in rows],
            "dst_uid": [r[1] for r in rows],
        }
    )


def test_emits_one_row_per_unique_sec_cik(mod):
    bridges = _bridges(
        [
            ("sec:0001", "icij:100"),
            ("sec:0001", "icij:101"),  # same SEC entity, different ICIJ — dedup
            ("sec:0002", "icij:102"),
        ]
    )
    out = mod.select(bridges)
    assert sorted(out["uid"].to_list()) == ["sec:0001", "sec:0002"]


def test_uid_column_matches_extra_seeds_schema(mod):
    out = mod.select(_bridges([("sec:0001", "icij:100")]))
    assert set(out.columns) == {"uid", "source"}
    assert out.schema["uid"] == pl.String
    # All rows tagged with the same source for provenance.
    assert out["source"].to_list() == ["sec_bridge"]


def test_empty_bridges_returns_empty_with_correct_schema(mod):
    empty = pl.DataFrame(schema={"src_uid": pl.String, "dst_uid": pl.String})
    out = mod.select(empty)
    assert out.is_empty()
    assert set(out.columns) == {"uid", "source"}


def test_drops_null_src_uid(mod):
    bridges = pl.DataFrame({"src_uid": ["sec:0001", None, "sec:0002"], "dst_uid": ["a", "b", "c"]})
    out = mod.select(bridges)
    assert sorted(out["uid"].to_list()) == ["sec:0001", "sec:0002"]


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
