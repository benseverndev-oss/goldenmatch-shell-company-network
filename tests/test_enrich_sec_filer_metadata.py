"""Phase 17a — SEC filer metadata enrichment tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "enrich_sec_filer_metadata.py"


def _load():
    spec = importlib.util.spec_from_file_location("enrich_sec_filer_metadata", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["enrich_sec_filer_metadata"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load()


def test_fetch_metadata_parses_full_payload(mod):
    """A typical EDGAR submissions document maps cleanly to FilerMetadata."""

    payload = {
        "name": "Apex Management Ltd",
        "sic": "6770",
        "sicDescription": "Blank Checks",
        "category": "Smaller Reporting Company",
        "stateOfIncorporation": "VG",
        "tickers": [],
        "exchanges": [],
    }

    def fake_fetch(url: str):
        return (200, payload)

    meta = mod.fetch_metadata("0001234567", fake_fetch)
    assert meta.cik == "0001234567"
    assert meta.name == "Apex Management Ltd"
    assert meta.sic == "6770"
    assert meta.sic_description == "Blank Checks"
    assert meta.category == "Smaller Reporting Company"
    assert meta.state_of_incorporation == "VG"
    assert meta.tickers == []
    assert meta.exchanges == []
    assert meta.status_code == 200

    row = meta.to_row()
    assert row["sic"] == "6770"
    assert row["tickers"] == ""
    assert row["exchanges"] == ""


def test_fetch_metadata_handles_large_cap_with_tickers(mod):
    """A NYSE-listed bank produces non-empty tickers + Large Accelerated."""

    payload = {
        "name": "ROYAL BANK OF CANADA",
        "sic": "6020",
        "sicDescription": "Commercial Banks NEC",
        "category": "Large Accelerated Filer",
        "tickers": ["RY"],
        "exchanges": ["NYSE"],
    }

    def fake_fetch(url: str):
        return (200, payload)

    meta = mod.fetch_metadata("0000888888", fake_fetch)
    row = meta.to_row()
    assert row["tickers"] == "RY"
    assert row["exchanges"] == "NYSE"
    assert row["category"] == "Large Accelerated Filer"
    assert row["sic"] == "6020"


def test_fetch_metadata_handles_404(mod):
    """A 404 yields a row with status=404 + empty fields."""

    def fake_fetch(url: str):
        return (404, {})

    meta = mod.fetch_metadata("0000000001", fake_fetch)
    assert meta.status_code == 404
    assert meta.name == ""
    assert meta.sic == ""


def test_fetch_metadata_handles_exception(mod):
    """An httpx-level exception yields status=0, not a crash."""

    def fake_fetch(url: str):
        raise RuntimeError("network down")

    meta = mod.fetch_metadata("0000000001", fake_fetch)
    assert meta.status_code == 0


def test_enrich_builds_dataframe(mod):
    """``enrich`` returns a DataFrame with one row per CIK + expected columns."""

    def fake_fetch(url: str):
        # Extract CIK from URL for distinct payloads.
        return (200, {"name": f"co-{url[-15:-5]}", "sic": "6770"})

    out = mod.enrich(
        ["0000000001", "0000000002", "0000000003"], fetcher=fake_fetch, min_interval_s=0.0
    )
    assert isinstance(out, pl.DataFrame)
    assert out.height == 3
    assert {"cik", "name", "sic", "category", "tickers", "status_code"}.issubset(set(out.columns))


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
