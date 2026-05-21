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


def _bridges_df(rows: list[tuple[str, str]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "src_uid": [r[0] for r in rows],
            "dst_uid": [r[1] for r in rows],
            "sec_name": ["x"] * len(rows),
            "icij_name": ["y"] * len(rows),
            "normalized": ["z"] * len(rows),
            "sec_role": ["filer"] * len(rows),
        }
    )


def _metadata_df(rows: list[dict]) -> pl.DataFrame:
    """Helper: takes [{cik, sic, category, tickers}, ...]."""
    schema = {
        "cik": pl.String,
        "sic": pl.String,
        "category": pl.String,
        "tickers": pl.String,
    }
    return pl.DataFrame(rows, schema=schema)


def test_filter_large_cap_filers_drops_large_accelerated(mod):
    """Phase 17a: a Large Accelerated Filer (e.g. Royal Bank of Canada)
    must be dropped even when its bridge passes the name match. SEC
    emits the category in lowercase ("Large accelerated filer") with
    optional HTML linebreaks appended — verify the substring match
    handles both."""
    bridges = _bridges_df(
        [
            ("sec:0001000275", "icij:rbc-coincidence"),
            ("sec:0001234567", "icij:rbc2-variant"),
            ("sec:0002022852", "icij:offshore-match"),
        ]
    )
    meta = _metadata_df(
        [
            {
                "cik": "0001000275",
                "sic": "6020",
                # Real SEC string per data.sec.gov 2026-05-21.
                "category": "Large accelerated filer",
                "tickers": "RY",
            },
            {
                "cik": "0001234567",
                "sic": "6770",
                # Concatenated variant with HTML linebreak suffix.
                "category": "Large accelerated filer<br>Well-known seasoned issuer",
                "tickers": "",
            },
            {
                "cik": "0002022852",
                "sic": "6770",
                "category": "Non-accelerated filer",
                "tickers": "",
            },
        ]
    )
    kept, counts = mod.filter_large_cap_filers(bridges, meta)
    assert kept.height == 1, f"only the non-accelerated bridge should survive: {kept}"
    assert kept["src_uid"].to_list() == ["sec:0002022852"]
    assert counts["dropped_large_filer"] == 2
    assert counts["kept"] == 1


def test_filer_category_helper_non_accelerated_not_flagged(mod):
    """The substring 'accelerated filer' must NOT fire for
    'Non-accelerated filer' (the common SEC string for small filers)."""

    assert mod._filer_category_is_large_cap("Non-accelerated filer") is False
    assert mod._filer_category_is_large_cap("non-accelerated filer") is False
    assert mod._filer_category_is_large_cap("Smaller reporting company") is False
    assert mod._filer_category_is_large_cap("") is False
    # And the positive cases
    assert mod._filer_category_is_large_cap("Large accelerated filer") is True
    assert mod._filer_category_is_large_cap("Accelerated filer") is True
    assert (
        mod._filer_category_is_large_cap("Large accelerated filer<br>Well-known seasoned issuer")
        is True
    )


def test_filter_drops_blocked_sic(mod):
    """A filer with SIC 6020 (commercial banks) is dropped even if not
    Large Accelerated and ticker is empty (rare but possible)."""
    bridges = _bridges_df(
        [
            ("sec:0001", "icij:bank-noise"),
            ("sec:0002", "icij:real-match"),
        ]
    )
    meta = _metadata_df(
        [
            {
                "cik": "0001",
                "sic": "6020",
                "category": "Non-accelerated Filer",
                "tickers": "",
            },
            {
                "cik": "0002",
                "sic": "6770",
                "category": "Non-accelerated Filer",
                "tickers": "",
            },
        ]
    )
    kept, counts = mod.filter_large_cap_filers(bridges, meta)
    assert kept["src_uid"].to_list() == ["sec:0002"]
    assert counts["dropped_blocked_sic"] == 1


def test_filter_drops_us_ticker(mod):
    """Any filer with a US-exchange ticker is dropped."""
    bridges = _bridges_df([("sec:0001", "icij:noise"), ("sec:0002", "icij:keep")])
    meta = _metadata_df(
        [
            {
                "cik": "0001",
                "sic": "6770",
                "category": "Smaller Reporting Company",
                "tickers": "AAPL",
            },
            {
                "cik": "0002",
                "sic": "6770",
                "category": "Smaller Reporting Company",
                "tickers": "",
            },
        ]
    )
    kept, counts = mod.filter_large_cap_filers(bridges, meta)
    assert kept["src_uid"].to_list() == ["sec:0002"]
    assert counts["dropped_us_ticker"] == 1


def test_filter_missing_metadata_keeps_bridge(mod):
    """A bridge whose filer has no metadata row is kept (no signal to
    drop it on). This avoids losing real offshore shells just because
    SEC submissions API returned 404."""
    bridges = _bridges_df([("sec:0099999999", "icij:keep")])
    meta = _metadata_df([])
    kept, counts = mod.filter_large_cap_filers(bridges, meta)
    assert kept.height == 1
    assert counts["kept"] == 1


def test_filter_empty_input_returns_empty(mod):
    """No bridges in -> no bridges out, no error."""
    empty = pl.DataFrame(
        schema={
            "src_uid": pl.String,
            "dst_uid": pl.String,
            "sec_name": pl.String,
            "icij_name": pl.String,
            "normalized": pl.String,
            "sec_role": pl.String,
        }
    )
    meta = _metadata_df(
        [{"cik": "x", "sic": "6020", "category": "Large Accelerated Filer", "tickers": ""}]
    )
    kept, counts = mod.filter_large_cap_filers(empty, meta)
    assert kept.is_empty()
    assert counts["input_rows"] == 0
