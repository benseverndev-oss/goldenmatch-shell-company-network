"""OpenCorporates adapter.

Wraps the public OpenCorporates REST API
(https://api.opencorporates.com/) with two intentional choices:

1. **Local raw cache** — every paginated response gets written verbatim to
   ``data/raw/opencorporates/cache/`` so re-runs don't re-hit the API and so
   the cache becomes the artefact you ship for reproducibility.

2. **Polite by default** — we sleep between pages, cap pages, and never
   hammer the unauthenticated tier. The API key, if any, is read from the
   ``OPENCORPORATES_API_KEY`` env var. We never log the key.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import polars as pl

from shellnet.normalize import (
    normalize_address_text,
    normalize_company_name,
    normalize_identifier,
    normalize_jurisdiction,
)
from shellnet.paths import INTERIM_DIR, OPENCORPORATES_CACHE

log = logging.getLogger(__name__)

API_BASE = "https://api.opencorporates.com/v0.4"
DEFAULT_PER_PAGE = 30
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_MAX_PAGES = 5
USER_AGENT = "shellnet/0.1 (+https://github.com/) GoldenMatch case study"


def _cache_key(params: dict[str, Any]) -> str:
    """Stable filename for a request — sorted params hashed to 16 hex chars."""
    serialized = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()[:16]


def _cache_path(endpoint: str, params: dict[str, Any]) -> Path:
    safe_endpoint = endpoint.strip("/").replace("/", "_")
    return OPENCORPORATES_CACHE / f"{safe_endpoint}__{_cache_key(params)}.json"


def _request(
    client: httpx.Client,
    endpoint: str,
    params: dict[str, Any],
    *,
    use_cache: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """GET ``endpoint`` with ``params``, caching the JSON to disk.

    On cache hit we never touch the network. On dry-run we never touch the
    network either; if there's no cache hit we synthesize an empty
    response so callers can at least exercise the pagination loop.
    """
    OPENCORPORATES_CACHE.mkdir(parents=True, exist_ok=True)
    path = _cache_path(endpoint, params)
    if use_cache and path.exists():
        log.debug("OpenCorporates cache hit: %s", path.name)
        return json.loads(path.read_text("utf-8"))
    if dry_run:
        log.info("Dry-run: skipping HTTP for %s %s", endpoint, params)
        return {"results": {"companies": [], "page": params.get("page", 1), "total_pages": 0}}

    api_key = os.environ.get("OPENCORPORATES_API_KEY") or None
    request_params = dict(params)
    if api_key:
        request_params["api_token"] = api_key

    log.info("OpenCorporates GET %s params=%s", endpoint, {k: v for k, v in params.items()})
    resp = client.get(f"{API_BASE}{endpoint}", params=request_params, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    # Cache without the api_token so the cache key & file stay portable.
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def search_companies(
    query: str,
    *,
    jurisdiction: str | None = None,
    per_page: int = DEFAULT_PER_PAGE,
    max_pages: int = DEFAULT_MAX_PAGES,
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
    use_cache: bool = True,
    dry_run: bool = False,
) -> Iterator[dict[str, Any]]:
    """Yield company dicts from ``/companies/search``.

    Stops at ``max_pages`` even if more pages are available — the public
    tier rate-limits hard, and a conservative cap is the friendly default.
    """
    params_base: dict[str, Any] = {"q": query, "per_page": per_page}
    if jurisdiction:
        params_base["jurisdiction_code"] = jurisdiction

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for page in range(1, max_pages + 1):
            params = {**params_base, "page": page}
            data = _request(
                client,
                "/companies/search",
                params,
                use_cache=use_cache,
                dry_run=dry_run,
            )
            results = (data.get("results") or {}).get("companies") or []
            if not results:
                return
            for wrapper in results:
                # search results are wrapped in {"company": {...}}
                yield wrapper.get("company") or wrapper
            total_pages = (data.get("results") or {}).get("total_pages") or 0
            if page >= total_pages:
                return
            if sleep_seconds and not dry_run:
                time.sleep(sleep_seconds)


def parse_company(record: dict[str, Any]) -> dict[str, Any]:
    """Map an OpenCorporates company record onto the canonical row shape.

    Returns a flat dict matching the columns we write to parquet. Raw
    record is preserved verbatim under ``raw_json``.
    """
    name = record.get("name") or record.get("company_name") or ""
    juris = record.get("jurisdiction_code")
    company_number = record.get("company_number") or ""
    addr = record.get("registered_address_in_full") or ""
    return {
        "source": "opencorporates",
        "source_id": f"{juris or ''}/{company_number}".strip("/"),
        "name": name,
        "normalized_name": normalize_company_name(name),
        "jurisdiction": normalize_jurisdiction(juris),
        "jurisdiction_raw": juris,
        "company_number": normalize_identifier(company_number),
        "status": record.get("current_status") or record.get("inactive"),
        "legal_form": record.get("company_type"),
        "incorporation_date": record.get("incorporation_date"),
        "dissolution_date": record.get("dissolution_date"),
        "address_raw": addr,
        "normalized_address": normalize_address_text(addr),
        "opencorporates_url": record.get("opencorporates_url"),
        "raw_json": json.dumps(record, default=str),
    }


def ingest_query(
    query: str,
    *,
    jurisdiction: str | None = None,
    limit: int = 100,
    per_page: int = DEFAULT_PER_PAGE,
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
    use_cache: bool = True,
    dry_run: bool = False,
    out_dir: Path = INTERIM_DIR,
) -> Path:
    """Run a search-and-parse pass for one query and append parquet output.

    Multiple calls to ``ingest_query`` with different queries produce a
    union under a single output file (``opencorporates_companies.parquet``).
    Existing rows are preserved; we de-duplicate on ``source_id``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "opencorporates_companies.parquet"

    max_pages = max(1, (limit + per_page - 1) // per_page)
    rows: list[dict[str, Any]] = []
    for record in search_companies(
        query,
        jurisdiction=jurisdiction,
        per_page=per_page,
        max_pages=max_pages,
        sleep_seconds=sleep_seconds,
        use_cache=use_cache,
        dry_run=dry_run,
    ):
        rows.append(parse_company(record))
        if len(rows) >= limit:
            break

    if not rows:
        log.warning("OpenCorporates query %r returned no rows.", query)
        # Still write an empty file with the right schema if none exists yet,
        # so downstream code can read it without branching.
        if not out.exists():
            pl.DataFrame(schema=_PARQUET_SCHEMA).write_parquet(out)
        return out

    new_df = pl.DataFrame(rows, schema=_PARQUET_SCHEMA)
    if out.exists():
        existing = pl.read_parquet(out)
        combined = pl.concat([existing, new_df], how="diagonal_relaxed").unique(
            subset=["source_id"], keep="last"
        )
    else:
        combined = new_df
    combined.write_parquet(out)
    log.info("Wrote %d OpenCorporates rows (total %d) to %s", len(rows), combined.height, out)
    return out


_PARQUET_SCHEMA: dict[str, type[pl.DataType]] = {
    "source": pl.Utf8,
    "source_id": pl.Utf8,
    "name": pl.Utf8,
    "normalized_name": pl.Utf8,
    "jurisdiction": pl.Utf8,
    "jurisdiction_raw": pl.Utf8,
    "company_number": pl.Utf8,
    "status": pl.Utf8,
    "legal_form": pl.Utf8,
    "incorporation_date": pl.Utf8,
    "dissolution_date": pl.Utf8,
    "address_raw": pl.Utf8,
    "normalized_address": pl.Utf8,
    "opencorporates_url": pl.Utf8,
    "raw_json": pl.Utf8,
}


def parse_local_file(path: Path) -> pl.DataFrame:
    """Parse a locally cached OpenCorporates JSON response (search or single).

    Useful for tests, for hand-curated fixtures, and for running without
    network access on top of an already-populated cache directory.
    """
    blob = json.loads(Path(path).read_text("utf-8"))
    results = (blob.get("results") or {})
    raw_companies = results.get("companies") or []
    rows: list[dict[str, Any]] = []
    for wrapper in raw_companies:
        record = wrapper.get("company") if isinstance(wrapper, dict) and "company" in wrapper else wrapper
        if isinstance(record, dict):
            rows.append(parse_company(record))
    # Single-company endpoint shape: {"results": {"company": {...}}}
    single = results.get("company")
    if isinstance(single, dict):
        rows.append(parse_company(single))
    if not rows:
        return pl.DataFrame(schema=_PARQUET_SCHEMA)
    return pl.DataFrame(rows, schema=_PARQUET_SCHEMA)
