"""Phase 10 — SEC<->ICIJ name-bridge tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_sec_icij_by_name.py"


def _load():
    spec = importlib.util.spec_from_file_location("bridge_sec_icij_by_name", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["bridge_sec_icij_by_name"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load()


def test_normalize_collapses_punct_and_spaces(mod):
    expr = mod._normalize_name_series(pl.col("name"))
    df = pl.DataFrame({"name": ["ACME, Inc.", "ACME    INC", "acme inc"]}).with_columns(
        expr.alias("normalized")
    )
    out = df["normalized"].to_list()
    assert out == ["acme inc", "acme inc", "acme inc"], out


def test_build_bridges_exact_match(mod, tmp_path):
    """A SEC filer name matching an ICIJ entity (any jurisdiction)
    emits a bridge. Multi-token names get past the name-shape gate."""
    sec_edges = pl.DataFrame(
        {
            "accession": ["A1"],
            "form": ["SCHEDULE 13D"],
            "filed_date": ["2025-11-21"],
            # 3+ tokens, >=12 chars normalised: passes the shape gate.
            "filer_cik": ["0001234567"],
            "filer_name": ["Corvus Capital Partners LP"],
            "subject_cik": ["0009999999"],
            "subject_name": ["Some Target Co"],
        }
    )
    icij = pl.DataFrame(
        {
            "source_id": ["99", "100"],
            "name": ["Corvus Capital Partners LP", "Different Co"],
            "jurisdiction": ["vg", "mt"],  # offshore
        }
    )
    sec_path = tmp_path / "sec.parquet"
    icij_path = tmp_path / "icij.parquet"
    sec_edges.write_parquet(sec_path)
    icij.write_parquet(icij_path)

    sec_df = mod.load_sec_names(sec_path)
    icij_df = mod.load_icij_us_entities(icij_path)
    bridges = mod.build_bridges(sec_df, icij_df)

    assert bridges.height == 1
    row = bridges.row(0, named=True)
    assert row["src_uid"] == "sec:0001234567"
    assert row["dst_uid"] == "icij:99"
    # Only filer-side matches are emitted now.
    assert row["sec_role"] == "filer"


def test_build_bridges_rejects_subject_side(mod, tmp_path):
    """SEC subject (US-listed issuer) is never emitted as a bridge —
    even if the name happens to match an ICIJ entity. Subjects on US
    exchanges aren't expected in ICIJ's offshore corpus, so any match
    on that side is more likely coincidence than identity."""
    sec_edges = pl.DataFrame(
        {
            "accession": ["A1"],
            "form": ["SCHEDULE 13D"],
            "filed_date": ["2025-11-21"],
            "filer_cik": ["0001"],
            "filer_name": ["Some Boring Filer LLC"],
            "subject_cik": ["0002"],
            "subject_name": ["Corvus Capital Partners LP"],
        }
    )
    icij = pl.DataFrame(
        {
            "source_id": ["99"],
            "name": ["Corvus Capital Partners LP"],
            "jurisdiction": ["vg"],
        }
    )
    sec_path = tmp_path / "sec.parquet"
    icij_path = tmp_path / "icij.parquet"
    sec_edges.write_parquet(sec_path)
    icij.write_parquet(icij_path)

    sec_df = mod.load_sec_names(sec_path)
    icij_df = mod.load_icij_us_entities(icij_path)
    bridges = mod.build_bridges(sec_df, icij_df)
    assert bridges.height == 0


def test_build_bridges_rejects_short_names(mod, tmp_path):
    """Short or single-token names get dropped by the name-shape gate.
    "Acme Inc" is a common-coincidence trap; only substantive multi-token
    names produce bridges."""
    sec_edges = pl.DataFrame(
        {
            "accession": ["A1", "A2"],
            "form": ["SCHEDULE 13D"] * 2,
            "filed_date": ["2025-11-21"] * 2,
            "filer_cik": ["0001", "0002"],
            "filer_name": ["Acme Inc", "Corvus Capital Partners LP"],
            "subject_cik": ["0099", "0099"],
            "subject_name": ["Target Co"] * 2,
        }
    )
    icij = pl.DataFrame(
        {
            "source_id": ["10", "20"],
            "name": ["Acme Inc", "Corvus Capital Partners LP"],
            "jurisdiction": ["gb", "vg"],
        }
    )
    sec_path = tmp_path / "sec.parquet"
    icij_path = tmp_path / "icij.parquet"
    sec_edges.write_parquet(sec_path)
    icij.write_parquet(icij_path)

    sec_df = mod.load_sec_names(sec_path)
    icij_df = mod.load_icij_us_entities(icij_path)
    bridges = mod.build_bridges(sec_df, icij_df)
    # Only the "Corvus Capital Partners LP" match survives.
    assert bridges.height == 1
    assert bridges.row(0, named=True)["src_uid"] == "sec:0002"


def test_build_bridges_dedups_per_pair(mod, tmp_path):
    """A SEC filer appearing on multiple filings should produce one
    bridge row per (sec_uid, icij_uid), not one per filing."""
    sec_edges = pl.DataFrame(
        {
            "accession": ["A1", "A2", "A3"],
            "form": ["SCHEDULE 13D"] * 3,
            "filed_date": ["2025-11-21"] * 3,
            "filer_cik": ["0001"] * 3,
            "filer_name": ["Recurring Offshore Filer LLC"] * 3,
            "subject_cik": ["0002", "0003", "0004"],
            "subject_name": ["Target A", "Target B", "Target C"],
        }
    )
    icij = pl.DataFrame(
        {
            "source_id": ["100"],
            "name": ["Recurring Offshore Filer LLC"],
            "jurisdiction": ["vg"],
        }
    )
    sec_path = tmp_path / "sec.parquet"
    icij_path = tmp_path / "icij.parquet"
    sec_edges.write_parquet(sec_path)
    icij.write_parquet(icij_path)

    sec_df = mod.load_sec_names(sec_path)
    icij_df = mod.load_icij_us_entities(icij_path)
    bridges = mod.build_bridges(sec_df, icij_df)
    assert bridges.height == 1


def test_build_bridges_emits_on_any_juris(mod, tmp_path):
    """ICIJ's offshore-only corpus has zero US-juris rows; the policy
    accepts any jurisdiction on the ICIJ side as long as the name-shape
    gates pass."""
    sec_edges = pl.DataFrame(
        {
            "accession": ["A1"],
            "form": ["SCHEDULE 13D"],
            "filed_date": ["2025-11-21"],
            "filer_cik": ["0001"],
            "filer_name": ["Multi Token Offshore Holdings"],
            "subject_cik": ["0002"],
            "subject_name": ["Some Target"],
        }
    )
    icij = pl.DataFrame(
        {
            "source_id": ["1"],
            "name": ["Multi Token Offshore Holdings"],
            "jurisdiction": ["mt"],
        }
    )
    sec_path = tmp_path / "sec.parquet"
    icij_path = tmp_path / "icij.parquet"
    sec_edges.write_parquet(sec_path)
    icij.write_parquet(icij_path)

    sec_df = mod.load_sec_names(sec_path)
    icij_df = mod.load_icij_us_entities(icij_path)
    bridges = mod.build_bridges(sec_df, icij_df)
    assert bridges.height == 1


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
