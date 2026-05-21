"""Tests for OpenCorporates + Wayback fallback probe."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "probe_mbr_company.py"


def _load():
    spec = importlib.util.spec_from_file_location("probe_mbr_company", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["probe_mbr_company"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load()


def _oc_search_payload(name: str, number: str = "C12345") -> dict:
    """Shape of an OpenCorporates /companies/search response."""
    return {
        "results": {
            "companies": [
                {
                    "company": {
                        "name": name,
                        "company_number": number,
                        "jurisdiction_code": "mt",
                        "current_status": "Active",
                        "incorporation_date": "2000-05-25",
                        "registered_address_in_full": (
                            "125 Mercury House, Old Mint Street, Valletta, Malta"
                        ),
                        "opencorporates_url": f"https://opencorporates.com/companies/mt/{number}",
                    }
                }
            ]
        }
    }


def _oc_detail_payload(
    name: str, number: str = "C12345", officers: list[dict] | None = None
) -> dict:
    return {
        "results": {
            "company": {
                "name": name,
                "company_number": number,
                "current_status": "Active",
                "incorporation_date": "2000-05-25",
                "registered_address_in_full": (
                    "125 Mercury House, Old Mint Street, Valletta, Malta"
                ),
                "officers": [
                    {"officer": o}
                    for o in (officers or [{"name": "PLAMEN DIONISSIEV", "position": "Director"}])
                ],
                "opencorporates_url": f"https://opencorporates.com/companies/mt/{number}",
            }
        }
    }


def test_search_opencorporates_returns_top_match(mod):
    def fake_fetcher(url: str, params: dict | None = None):
        assert "companies/search" in url
        assert (params or {}).get("jurisdiction_code") == "mt"
        return (200, _oc_search_payload("RHEA MARINE LTD"), b"")

    result = mod.search_opencorporates("RHEA MARINE LTD", jurisdiction="mt", fetcher=fake_fetcher)
    assert result is not None
    company = result["company"]
    assert company["name"] == "RHEA MARINE LTD"
    assert company["company_number"] == "C12345"


def test_search_opencorporates_no_match_returns_none(mod):
    def fake_fetcher(url: str, params: dict | None = None):
        return (200, {"results": {"companies": []}}, b"")

    assert mod.search_opencorporates("NOPE LTD", jurisdiction="mt", fetcher=fake_fetcher) is None


def test_fetch_opencorporates_detail(mod):
    def fake_fetcher(url: str, params: dict | None = None):
        return (200, _oc_detail_payload("RHEA MARINE LTD"), b"")

    detail = mod.fetch_opencorporates_detail("mt", "C12345", fetcher=fake_fetcher)
    assert detail is not None
    assert detail["company_number"] == "C12345"
    assert len(detail["officers"]) == 1


def test_find_wayback_snapshot(mod):
    def fake_fetcher(url: str, params: dict | None = None):
        assert "wayback/available" in url
        return (
            200,
            {
                "archived_snapshots": {
                    "closest": {
                        "url": "https://web.archive.org/web/2024/https://opencorporates.com/companies/mt/C12345",
                        "available": True,
                    }
                }
            },
            b"",
        )

    snap = mod.find_wayback_snapshot(
        "https://opencorporates.com/companies/mt/C12345", fetcher=fake_fetcher
    )
    assert snap == (
        "https://web.archive.org/web/2024/https://opencorporates.com/companies/mt/C12345"
    )


def test_find_wayback_snapshot_no_archive(mod):
    """Wayback returns ``{}`` for never-archived URLs; treat as None."""

    def fake_fetcher(url: str, params: dict | None = None):
        return (200, {"archived_snapshots": {}}, b"")

    assert mod.find_wayback_snapshot("https://example.com", fetcher=fake_fetcher) is None


def test_probe_writes_artefacts(mod, tmp_path):
    """End-to-end: probe() should write opencorporates_search.json,
    opencorporates_company.json, wayback_snapshots.json, and
    evidence_record.yaml under <out_dir>/<slug>/."""

    def fake_fetcher(url: str, params: dict | None = None):
        if "companies/search" in url:
            return (200, _oc_search_payload("RHEA MARINE LTD"), b"")
        if "companies/mt/" in url:
            return (200, _oc_detail_payload("RHEA MARINE LTD"), b"")
        if "wayback/available" in url:
            return (
                200,
                {"archived_snapshots": {"closest": {"url": "https://web.archive.org/x"}}},
                b"",
            )
        raise AssertionError(f"unexpected fetch: {url}")

    result = mod.probe(
        "RHEA MARINE LTD",
        slug="rhea_marine",
        jurisdiction="mt",
        out_dir=tmp_path,
        icij_context={
            "officers": ["PLAMEN DIONISSIEV"],
            "registered_address": "125 Mercury House Valletta MT",
            "incorporation_date": "2000-05-25",
        },
        fetcher=fake_fetcher,
        min_interval_s=0.0,
    )

    sub = tmp_path / "rhea_marine"
    assert (sub / "opencorporates_search.json").exists()
    assert (sub / "opencorporates_company.json").exists()
    assert (sub / "wayback_snapshots.json").exists()
    assert (sub / "evidence_record.yaml").exists()

    record = json.loads((sub / "evidence_record.yaml").read_text("utf-8"))
    assert record["entity"] == "RHEA MARINE LTD"
    assert record["opencorporates"]["found"] is True
    assert record["opencorporates"]["registration_number"] == "C12345"
    assert record["icij_context"]["officers"] == ["PLAMEN DIONISSIEV"]
    assert record["verdict"] == "pending_review"
    assert result.error is None


def test_probe_handles_no_opencorporates_match(mod, tmp_path):
    """A name with no MT match still writes evidence_record.yaml so the
    investigator sees what was tried."""

    def fake_fetcher(url: str, params: dict | None = None):
        return (200, {"results": {"companies": []}}, b"")

    result = mod.probe(
        "NONEXISTENT LTD",
        slug="nonexistent",
        out_dir=tmp_path,
        fetcher=fake_fetcher,
        min_interval_s=0.0,
    )
    sub = tmp_path / "nonexistent"
    assert (sub / "evidence_record.yaml").exists()
    assert (sub / "opencorporates_search.json").exists()
    record = json.loads((sub / "evidence_record.yaml").read_text("utf-8"))
    assert record["opencorporates"]["found"] is False
    assert result.error == "opencorporates: no match"


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
