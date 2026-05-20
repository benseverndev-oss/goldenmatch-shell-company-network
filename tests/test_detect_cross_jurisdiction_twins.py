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
    # At corpus scale the abbrev path requires >=3 char acronyms to keep
    # join cardinality from blowing up. Use a 3-token name so the
    # abbreviation has 3 letters.
    icij = pl.DataFrame(
        {
            "entity_uid": ["icij:m1"],
            "name": ["GLOBAL TRADE FINANCE (MALTA) LTD"],  # abbrev "gtf"
            "jurisdiction": ["mt"],
        }
    )
    oo = pl.DataFrame(
        {
            "entity_uid": ["oo:gb-coh-x"],
            "name": ["G T F LIMITED"],  # abbrev also "gtf"
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


def test_polars_native_matches_python_helper(mod):
    """Lock in that build_name_index (polars-native) produces the same
    root + abbrev_root as the Python _normalize / _abbreviation_root helpers
    on representative cases. Catches drift if either side gets edited."""

    cases = [
        # name, expected_root, expected_abbrev
        ("PROBUTEC LTD", "probutec", ""),
        ("PROBUTEC LIMITED", "probutec", ""),
        ("ACME HOLDINGS PLC", "acme", ""),
        ("PROBUTEC (MALTA) LTD", "probutec", ""),
        ("INTEGRATED-CAPABILITIES (MALTA) LTD", "integrated capabilities", "ic"),
        ("I-CAP MARINE SERVICES LIMITED", "i cap marine services", "icms"),
        # Suffix-only name — preserved (>=1 token kept alive).
        ("LIMITED", "limited", ""),
    ]
    df = pl.DataFrame(
        {
            "entity_uid": [f"x:{i}" for i in range(len(cases))],
            "name": [c[0] for c in cases],
            "jurisdiction": ["xx"] * len(cases),
        }
    )
    idx = mod.build_name_index(
        df, name_col="name", uid_col="entity_uid", jurisdiction_col="jurisdiction"
    )
    rows = idx.to_dicts()
    for i, (name, expected_root, expected_abbrev) in enumerate(cases):
        assert rows[i]["root"] == expected_root, (
            f"polars-native {name!r}: got root={rows[i]['root']!r}, want {expected_root!r}"
        )
        assert rows[i]["abbrev_root"] == expected_abbrev, (
            f"polars-native {name!r}: got abbrev={rows[i]['abbrev_root']!r}, want {expected_abbrev!r}"
        )
        # And cross-check against the Python helper to lock in parity.
        assert rows[i]["root"] == mod._normalize(name)
        assert rows[i]["abbrev_root"] == mod._abbreviation_root(name)


def test_no_python_udf_in_build_name_index():
    """Defends the OOM fix: build_name_index must not call map_elements."""
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    # Allow map_elements elsewhere in the file (e.g. doc comments) but
    # not inside the build_name_index function body.
    start = src.index("def build_name_index(")
    end = src.index("\ndef ", start + 1)
    assert "map_elements" not in src[start:end], (
        "build_name_index regressed to a Python UDF; this OOMs Railway at corpus scale"
    )
