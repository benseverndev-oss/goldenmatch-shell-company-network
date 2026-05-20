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
    """A subject_name matching an ICIJ US-juris entity emits a bridge."""
    sec_edges = pl.DataFrame(
        {
            "accession": ["A1"],
            "form": ["SCHEDULE 13D"],
            "filed_date": ["2025-11-21"],
            "filer_cik": ["0002022852"],
            "filer_name": ["Catsimatidis John A. Jr"],
            "subject_cik": ["0001600641"],
            "subject_name": ["1stdibs.com, Inc."],
        }
    )
    icij = pl.DataFrame(
        {
            "source_id": ["12345", "67890"],
            "name": ["1stdibs.com Inc", "Unrelated UK Holdings"],
            "jurisdiction": ["us", "gb"],
        }
    )
    sec_path = tmp_path / "sec.parquet"
    icij_path = tmp_path / "icij.parquet"
    sec_edges.write_parquet(sec_path)
    icij.write_parquet(icij_path)

    sec_df = mod.load_sec_names(sec_path)
    icij_df = mod.load_icij_us_entities(icij_path)
    bridges = mod.build_bridges(sec_df, icij_df)

    assert bridges.height >= 1
    row = bridges.row(0, named=True)
    assert row["src_uid"] == "sec:0001600641"
    assert row["dst_uid"] == "icij:12345"
    assert row["sec_role"] == "subject"


def test_build_bridges_rejects_non_us_icij(mod, tmp_path):
    """Same-name ICIJ entity in GB jurisdiction must NOT match (Corvus rule)."""
    sec_edges = pl.DataFrame(
        {
            "accession": ["A1"],
            "form": ["SCHEDULE 13D"],
            "filed_date": ["2025-11-21"],
            "filer_cik": ["0001"],
            "filer_name": ["Corvus Capital LLC"],
            "subject_cik": ["0002"],
            "subject_name": ["Target Co"],
        }
    )
    icij = pl.DataFrame(
        {
            "source_id": ["99"],
            "name": ["Corvus Capital LLC"],
            "jurisdiction": ["gb"],  # UK same-name coincidence
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


def test_build_bridges_dedups_per_pair(mod, tmp_path):
    """A SEC entity appearing on multiple filings should produce one
    bridge row per (sec_uid, icij_uid), not one per filing."""
    sec_edges = pl.DataFrame(
        {
            "accession": ["A1", "A2", "A3"],
            "form": ["SCHEDULE 13D"] * 3,
            "filed_date": ["2025-11-21"] * 3,
            "filer_cik": ["0001"] * 3,
            "filer_name": ["Same Filer Inc"] * 3,
            "subject_cik": ["0002"] * 3,
            "subject_name": ["Same Subject Inc"] * 3,
        }
    )
    icij = pl.DataFrame(
        {
            "source_id": ["100"],
            "name": ["Same Subject Inc"],
            "jurisdiction": ["us"],
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


def test_build_bridges_min_length_4_chars(mod, tmp_path):
    """Names shorter than 4 normalised chars (e.g. 'AB') must not match;
    one-letter normalisations are pure noise at corpus scale."""
    sec_edges = pl.DataFrame(
        {
            "accession": ["A1"],
            "form": ["SCHEDULE 13D"],
            "filed_date": ["2025-11-21"],
            "filer_cik": ["0001"],
            "filer_name": ["AB"],
            "subject_cik": ["0002"],
            "subject_name": ["XY"],
        }
    )
    icij = pl.DataFrame(
        {
            "source_id": ["1"],
            "name": ["AB"],
            "jurisdiction": ["us"],
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


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
