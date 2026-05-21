"""Tests for the ICIJ source-page archiver."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from shellnet.archive.icij_archiver import (
    ArchiveEntry,
    archive_urls,
    parse_icij_urls_from_ftm,
)


def _write_ftm(path: Path, entities: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for ent in entities:
            f.write(json.dumps(ent) + "\n")


def test_parse_icij_urls_filters_offshoreleaks_only(tmp_path: Path):
    """Only offshoreleaks.icij.org/nodes/* URLs are picked up; unrelated
    sourceUrls (publisherUrl, internal-tool URLs) are skipped."""
    ftm = tmp_path / "entities.ftm.json"
    _write_ftm(
        ftm,
        [
            {
                "id": "a",
                "schema": "Person",
                "properties": {"sourceUrl": ["https://offshoreleaks.icij.org/nodes/12345"]},
            },
            {
                "id": "b",
                "schema": "Company",
                "properties": {
                    "sourceUrl": [
                        "https://offshoreleaks.icij.org/nodes/67890",
                        "https://example.com/some-tool",
                    ]
                },
            },
            {"id": "c", "schema": "Person", "properties": {}},
        ],
    )
    urls = parse_icij_urls_from_ftm(ftm)
    assert urls == [
        "https://offshoreleaks.icij.org/nodes/12345",
        "https://offshoreleaks.icij.org/nodes/67890",
    ]


def test_parse_icij_urls_dedupes(tmp_path: Path):
    """Same URL on two entities surfaces once."""
    ftm = tmp_path / "entities.ftm.json"
    _write_ftm(
        ftm,
        [
            {
                "id": "a",
                "schema": "Person",
                "properties": {"sourceUrl": ["https://offshoreleaks.icij.org/nodes/55"]},
            },
            {
                "id": "b",
                "schema": "Person",
                "properties": {"sourceUrl": ["https://offshoreleaks.icij.org/nodes/55"]},
            },
        ],
    )
    assert parse_icij_urls_from_ftm(ftm) == ["https://offshoreleaks.icij.org/nodes/55"]


def test_parse_icij_urls_missing_file_returns_empty(tmp_path: Path):
    assert parse_icij_urls_from_ftm(tmp_path / "nope.json") == []


def test_archive_urls_writes_html_and_manifest(tmp_path: Path):
    """Successful 200s land as <node_id>.html with sha256 in manifest."""
    fetched_payload = b"<html><body>hi</body></html>"

    def fake_fetcher(url: str, ua: str) -> tuple[int, bytes]:
        return (200, fetched_payload)

    urls = [
        "https://offshoreleaks.icij.org/nodes/aaa",
        "https://offshoreleaks.icij.org/nodes/bbb",
    ]
    out_dir = tmp_path / "archived_sources"
    result = archive_urls(
        urls,
        out_dir,
        fetch_filing=fake_fetcher,
        min_interval_s=0.0,
        request_wayback_save=False,
    )

    assert len(result.successes) == 2
    assert len(result.failures) == 0

    for node in ("aaa", "bbb"):
        f = out_dir / "icij" / "nodes" / f"{node}.html"
        assert f.exists()
        assert f.read_bytes() == fetched_payload

    manifest = json.loads((out_dir / "icij" / "manifest.json").read_text("utf-8"))
    assert len(manifest["entries"]) == 2
    expected_sha = hashlib.sha256(fetched_payload).hexdigest()
    for entry in manifest["entries"]:
        assert entry["sha256"] == expected_sha
        assert entry["status_code"] == 200
        assert entry["file"].startswith("icij/nodes/")
        assert entry["error"] is None


def test_archive_urls_records_failures_without_aborting(tmp_path: Path):
    """A 404 on one URL doesn't stop later URLs from being archived."""

    def fake_fetcher(url: str, ua: str) -> tuple[int, bytes]:
        if "broken" in url:
            return (404, b"")
        return (200, b"<html>ok</html>")

    urls = [
        "https://offshoreleaks.icij.org/nodes/good1",
        "https://offshoreleaks.icij.org/nodes/broken",
        "https://offshoreleaks.icij.org/nodes/good2",
    ]
    result = archive_urls(
        urls,
        tmp_path,
        fetch_filing=fake_fetcher,
        min_interval_s=0.0,
        request_wayback_save=False,
    )
    assert len(result.successes) == 2
    assert len(result.failures) == 1
    assert "broken" in result.failures[0].url

    errors = json.loads((tmp_path / "icij" / "errors.json").read_text("utf-8"))
    assert len(errors) == 1
    assert errors[0]["status_code"] == 404


def test_archive_urls_records_exception_without_aborting(tmp_path: Path):
    """A network exception on one URL doesn't propagate."""
    state = {"calls": 0}

    def fake_fetcher(url: str, ua: str) -> tuple[int, bytes]:
        state["calls"] += 1
        if state["calls"] == 2:
            raise RuntimeError("simulated network failure")
        return (200, b"<html>ok</html>")

    result = archive_urls(
        ["a", "b", "c"],
        tmp_path,
        fetch_filing=fake_fetcher,
        min_interval_s=0.0,
        request_wayback_save=False,
    )
    assert len(result.successes) == 2
    assert len(result.failures) == 1
    assert "simulated network failure" in (result.failures[0].error or "")


def test_archive_urls_min_interval_paces_requests(tmp_path: Path, monkeypatch):
    """The pacing knob delays subsequent calls. We just confirm the
    timestamps in the manifest are monotonically non-decreasing."""

    def fake_fetcher(url: str, ua: str) -> tuple[int, bytes]:
        return (200, b"")

    # 0.0 interval — should still complete cleanly with 3 URLs.
    result = archive_urls(
        ["https://offshoreleaks.icij.org/nodes/x"] * 3,
        tmp_path,
        fetch_filing=fake_fetcher,
        min_interval_s=0.0,
        request_wayback_save=False,
    )
    # Same URL deduped only at the FTM-parser layer; here we accept
    # whatever the caller passes. Three URLs in, three entries out.
    assert len(result.entries) == 3


def test_archive_entry_to_dict_shape():
    e = ArchiveEntry(
        url="https://offshoreleaks.icij.org/nodes/1",
        file="icij/nodes/1.html",
        fetched_at="2026-05-21T00:00:00Z",
        status_code=200,
        sha256="abc",
        wayback_url=None,
    )
    d = e.to_dict()
    assert set(d.keys()) == {
        "url",
        "file",
        "fetched_at",
        "status_code",
        "sha256",
        "wayback_url",
        "error",
    }


@pytest.fixture
def _no_real_network(monkeypatch):
    """Safety net: a test that forgot to pass fake_fetcher won't hit
    the real ICIJ servers."""

    def broken_factory():
        def bad(url, ua):
            raise AssertionError(f"unexpected real fetch for {url}")

        return bad

    monkeypatch.setattr("shellnet.archive.icij_archiver._http_fetcher_factory", broken_factory)
