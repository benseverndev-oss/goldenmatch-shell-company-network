"""Archive ICIJ Offshore Leaks source pages alongside a validation bundle.

The bundle's FollowTheMoney ndjson and the BODS export carry
``sourceUrl`` references pointing at ``offshoreleaks.icij.org``. URLs
are not evidence — ICIJ retires pages and rebuilds the database
periodically, and the case study has already seen the page layout
change once during this project. To be self-contained, the bundle
captures the HTML at build time and ships it alongside the FTM.

Capture format::

    archived_sources/
        icij/
            manifest.json
            nodes/
                <icij_id>.html        # raw response body
                ...
            errors.json               # urls that failed to fetch

``manifest.json`` schema (one row per attempted URL)::

    {
        "url": "https://offshoreleaks.icij.org/nodes/12345",
        "file": "icij/nodes/12345.html"     # relative to archived_sources/
        "fetched_at": "2026-05-21T13:45:12Z",
        "status_code": 200,
        "sha256": "<hex>",
        "wayback_url": "https://web.archive.org/web/.../<url>"
    }

The reviewer can confirm the captured HTML matches what ICIJ served
by checking the sha256 against an independent retrieval, or by
following ``wayback_url`` (best-effort; we ask the Wayback Machine
to save the page but don't fail the bundle build if it 5xxs).

Rate limit is 1 req/s to be polite to ICIJ (a small NGO). For a
typical 50-100 URL cluster that's < 2 min.

This module is pure-Python with one dependency: httpx. No FTM
parsing — the caller passes a list of URLs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

# Polite User-Agent. ICIJ pages do not have a fair-use policy
# document we can cite, but courtesy norms apply.
DEFAULT_USER_AGENT = (
    "GoldenMatch case-study archiver "
    "https://github.com/benseverndev-oss/goldenmatch-shell-company-network "
    "bsevern@mjhlifesciences.com"
)

# Match a Wayback Machine "save" endpoint. We hit this best-effort
# so each captured page also lives on web.archive.org as a backstop.
_WAYBACK_SAVE_URL = "https://web.archive.org/save/{target}"

# ICIJ node URL parser. Anchor at offshoreleaks.icij.org/nodes/<id>.
_ICIJ_NODE_RE = re.compile(
    r"^https://offshoreleaks\.icij\.org/nodes/(?P<node_id>[A-Za-z0-9_\-]+)/?\s*$"
)


@dataclass(frozen=True)
class ArchiveEntry:
    """One archived URL — successful or failed."""

    url: str
    file: str | None  # None if fetch failed
    fetched_at: str
    status_code: int | None  # None if request never completed
    sha256: str | None
    wayback_url: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "file": self.file,
            "fetched_at": self.fetched_at,
            "status_code": self.status_code,
            "sha256": self.sha256,
            "wayback_url": self.wayback_url,
            "error": self.error,
        }


@dataclass
class ArchiveResult:
    """Aggregate output of an archive_urls call."""

    entries: list[ArchiveEntry] = field(default_factory=list)

    @property
    def successes(self) -> list[ArchiveEntry]:
        return [e for e in self.entries if e.file is not None]

    @property
    def failures(self) -> list[ArchiveEntry]:
        return [e for e in self.entries if e.file is None]


# ---------------------------------------------------------------------------
# URL extraction
# ---------------------------------------------------------------------------


def parse_icij_urls_from_ftm(ftm_path: Path) -> list[str]:
    """Pull every unique ICIJ Offshore-Leaks URL out of an FTM ndjson.

    The exporter emits ICIJ pages under ``sourceUrl``. Same URL may
    appear on multiple entities; we dedupe and return sorted.
    """

    seen: set[str] = set()
    if not ftm_path.exists():
        return []
    with ftm_path.open(encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entity = json.loads(raw)
            except json.JSONDecodeError:
                continue
            urls = entity.get("properties", {}).get("sourceUrl", [])
            for url in urls:
                if isinstance(url, str) and _ICIJ_NODE_RE.match(url):
                    seen.add(url)
    return sorted(seen)


def _node_id_from_url(url: str) -> str | None:
    m = _ICIJ_NODE_RE.match(url)
    return m.group("node_id") if m else None


# ---------------------------------------------------------------------------
# Archiving driver
# ---------------------------------------------------------------------------


def archive_urls(
    urls: Iterable[str],
    out_dir: Path,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    min_interval_s: float = 1.0,
    request_wayback_save: bool = True,
    fetch_filing: callable[[str, str], tuple[int, bytes]] | None = None,
) -> ArchiveResult:
    """Fetch each URL, save the body, write a manifest.

    Args:
        urls: ICIJ Offshore Leaks node URLs.
        out_dir: directory to write into. The function creates
            ``out_dir/icij/nodes/*.html`` and ``out_dir/icij/manifest.json``.
        user_agent: HTTP UA. Default is the project's case-study UA.
        min_interval_s: minimum delay between requests in seconds.
            Default 1.0 = 1 req/s (polite for ICIJ).
        request_wayback_save: also POST to web.archive.org/save/ so
            each page has an independent backstop. Best-effort;
            failures don't propagate.
        fetch_filing: optional dependency-injected fetcher with
            signature ``(url, user_agent) -> (status_code, body)``.
            Provided so unit tests can run offline. When None, the
            function lazily imports httpx and uses a real client.

    Returns: :class:`ArchiveResult` with one :class:`ArchiveEntry`
    per attempted URL. Always writes the manifest, even when every
    URL failed, so the bundle reviewer can see what was attempted.
    """

    nodes_dir = out_dir / "icij" / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)

    if fetch_filing is None:
        fetch_filing = _http_fetcher_factory()

    result = ArchiveResult()
    last_call = 0.0

    urls_list = list(urls)
    log.info("archiving %d ICIJ URLs into %s", len(urls_list), out_dir)
    for i, url in enumerate(urls_list, start=1):
        # Pace
        elapsed = time.monotonic() - last_call
        if elapsed < min_interval_s:
            time.sleep(min_interval_s - elapsed)
        last_call = time.monotonic()

        fetched_at = _now()
        try:
            status_code, body = fetch_filing(url, user_agent)
        except Exception as exc:  # noqa: BLE001 — log + continue
            result.entries.append(
                ArchiveEntry(
                    url=url,
                    file=None,
                    fetched_at=fetched_at,
                    status_code=None,
                    sha256=None,
                    wayback_url=None,
                    error=repr(exc),
                )
            )
            log.warning("[%d/%d] fetch error %s: %s", i, len(urls_list), url, exc)
            continue

        node_id = _node_id_from_url(url) or _safe_slug(url)
        out_path = nodes_dir / f"{node_id}.html"
        sha256: str | None = None
        rel_path: str | None = None

        if status_code == 200 and body:
            out_path.write_bytes(body)
            sha256 = hashlib.sha256(body).hexdigest()
            rel_path = str(out_path.relative_to(out_dir)).replace("\\", "/")
            log.debug("[%d/%d] %s -> %s (%d bytes)", i, len(urls_list), url, rel_path, len(body))
        else:
            log.warning("[%d/%d] HTTP %s on %s", i, len(urls_list), status_code, url)

        wayback_url: str | None = None
        if request_wayback_save and rel_path is not None:
            wayback_url = _save_wayback(url, fetch_filing, user_agent)

        result.entries.append(
            ArchiveEntry(
                url=url,
                file=rel_path,
                fetched_at=fetched_at,
                status_code=status_code,
                sha256=sha256,
                wayback_url=wayback_url,
                error=None if status_code == 200 else f"http {status_code}",
            )
        )

    # Manifest + errors
    manifest_path = out_dir / "icij" / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "generator": "shellnet.archive.icij_archiver",
                "user_agent": user_agent,
                "entries": [e.to_dict() for e in result.entries],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    errors_path = out_dir / "icij" / "errors.json"
    failures = result.failures
    errors_path.write_text(
        json.dumps([e.to_dict() for e in failures], indent=2, sort_keys=True),
        encoding="utf-8",
    )

    log.info(
        "archived %d / %d ICIJ URLs (%d failures); manifest -> %s",
        len(result.successes),
        len(urls_list),
        len(failures),
        manifest_path,
    )
    return result


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_slug(s: str) -> str:
    """Filename-safe slug for an arbitrary URL when we can't parse a node id."""
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", s)[:120]


def _http_fetcher_factory():
    """Returns a ``(url, user_agent) -> (status, bytes)`` fetcher."""

    import httpx

    def fetcher(url: str, user_agent: str) -> tuple[int, bytes]:
        with httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Encoding": "gzip"},
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            return r.status_code, r.content

    return fetcher


def _save_wayback(url: str, fetcher, user_agent: str) -> str | None:
    """Ask the Wayback Machine to save ``url``. Best-effort; returns the
    canonical archive URL on success, None otherwise. Wayback's save API
    is GET-with-side-effects."""
    save_url = _WAYBACK_SAVE_URL.format(target=url)
    try:
        status, _ = fetcher(save_url, user_agent)
    except Exception as exc:  # noqa: BLE001
        log.debug("wayback save failed for %s: %s", url, exc)
        return None
    if status in (200, 302):
        return save_url
    return None
