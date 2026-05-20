"""Phase 3 — cross-jurisdictional twin detector tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "detect_cross_jurisdiction_twins.py"


def _load():
    spec = importlib.util.spec_from_file_location("detect_cross_jurisdiction_twins", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["detect_cross_jurisdiction_twins"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load()


def test_normalize_strips_legal_suffix(mod):
    assert mod._normalize("PROBUTEC LTD") == "probutec"
    assert mod._normalize("PROBUTEC LIMITED") == "probutec"
    assert mod._normalize("ACME HOLDINGS PLC") == "acme"


def test_normalize_strips_jurisdictional_qualifier(mod):
    assert mod._normalize("PROBUTEC (MALTA) LTD") == "probutec"
    assert mod._normalize("INTEGRATED-CAPABILITIES (MALTA) LTD") == "integrated capabilities"
    assert mod._normalize("FOO MT") == "foo"


def test_abbreviation_root(mod):
    assert mod._abbreviation_root("INTEGRATED CAPABILITIES") == "ic"
    assert mod._abbreviation_root("I-CAP MARINE SERVICES LIMITED") == "icms"
    # Single token: empty.
    assert mod._abbreviation_root("PROBUTEC") == ""


def test_strict_root_twin_detected(mod):
    icij = pl.DataFrame(
        {
            "entity_uid": ["icij:1"],
            "name": ["PROBUTEC (MALTA) LTD"],
            "jurisdiction": ["mt"],
        }
    )
    oo = pl.DataFrame(
        {
            "entity_uid": ["oo:gb-coh-04102334"],
            "name": ["PROBUTEC LTD"],
            "jurisdiction": ["gb"],
        }
    )
    icij_idx = mod.build_name_index(
        icij, name_col="name", uid_col="entity_uid", jurisdiction_col="jurisdiction"
    )
    oo_idx = mod.build_name_index(
        oo, name_col="name", uid_col="entity_uid", jurisdiction_col="jurisdiction"
    )
    twins = mod.detect_twins(icij_idx, oo_idx)
    assert twins.height >= 1
    assert (twins["match_type"] == "strict_root").any()
    row = twins.filter(pl.col("match_type") == "strict_root").row(0, named=True)
    # Both names should appear, in either direction.
    assert "PROBUTEC" in row["src_name"] or "PROBUTEC" in row["dst_name"]
    assert {row["src_jurisdiction"], row["dst_jurisdiction"]} == {"mt", "gb"}


def test_abbreviation_twin_detected(mod):
    """I-CAP MARINE SERVICES (gb) <-> INTEGRATED CAPABILITIES (MALTA) (mt)
    via the abbreviation match path (icms -> integrated capabilities...)."""

    # NOTE: the Perry case is I-CAP <-> INTEGRATED-CAPABILITIES (no MARINE
    # SERVICES on the MT side); test that pattern.
    icij = pl.DataFrame(
        {
            "entity_uid": ["icij:m1"],
            "name": ["INTEGRATED-CAPABILITIES (MALTA) LTD"],
            "jurisdiction": ["mt"],
        }
    )
    oo = pl.DataFrame(
        {
            "entity_uid": ["oo:gb-coh-x"],
            "name": [
                "I CAP LIMITED"
            ],  # i + cap = "ic" -> matches abbrev root of integrated capabilities
            "jurisdiction": ["gb"],
        }
    )
    icij_idx = mod.build_name_index(
        icij, name_col="name", uid_col="entity_uid", jurisdiction_col="jurisdiction"
    )
    oo_idx = mod.build_name_index(
        oo, name_col="name", uid_col="entity_uid", jurisdiction_col="jurisdiction"
    )
    twins = mod.detect_twins(icij_idx, oo_idx)
    # Any abbreviation-based match is fine.
    assert twins.height >= 1
    assert any(
        t in {"abbrev_left", "abbrev_right", "abbrev_both"} for t in twins["match_type"].to_list()
    )


def test_same_jurisdiction_pairs_excluded(mod):
    df = pl.DataFrame(
        {
            "entity_uid": ["icij:1", "icij:2"],
            "name": ["ACME LTD", "ACME LIMITED"],
            "jurisdiction": ["mt", "mt"],
        }
    )
    idx = mod.build_name_index(
        df, name_col="name", uid_col="entity_uid", jurisdiction_col="jurisdiction"
    )
    twins = mod.detect_twins(idx, idx)
    # Same-jurisdiction pairs are filtered out.
    assert twins.height == 0


def test_empty_roots_dont_match_everything(mod):
    df = pl.DataFrame(
        {
            "entity_uid": ["a", "b"],
            "name": ["LTD", "LIMITED"],  # both reduce to empty after suffix stripping
            "jurisdiction": ["mt", "gb"],
        }
    )
    idx = mod.build_name_index(
        df, name_col="name", uid_col="entity_uid", jurisdiction_col="jurisdiction"
    )
    twins = mod.detect_twins(idx, idx)
    assert twins.height == 0


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
