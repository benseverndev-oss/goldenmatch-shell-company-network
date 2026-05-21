"""Enrich SEC filer CIKs with their SEC EDGAR submissions metadata.

Phase 17a of the bridge-disambiguation roadmap. The bridge_sec_icij_by_name
script produces (SEC CIK ↔ ICIJ source_id) pairs purely on name. That
matches large US public companies (Royal Bank of Canada, Delta Air
Lines, Equitable Holdings) that happen to share names with ICIJ
entities — clear false positives that the fuzzy matcher can't
disambiguate.

The signal SEC provides about who a filer actually is lives at
``https://data.sec.gov/submissions/CIK{cik10}.json``. Key fields:

* ``sicDescription`` — industry classification (e.g. "Banks—Commercial",
  "Air Transportation, Scheduled")
* ``sic`` — numeric SIC code
* ``category`` — filer category ("Large Accelerated Filer",
  "Accelerated Filer", "Non-accelerated Filer", etc.)
* ``stateOfIncorporation`` — US state for domestic issuers; foreign
  ISO-3166 for foreign private issuers
* ``tickers`` / ``exchanges`` — US-listed tickers (NYSE, NASDAQ)

The bridge filter then drops any SEC filer that's:
* a Large Accelerated Filer, OR
* has at least one US-exchange ticker, OR
* has a SIC in our blocklist (commercial banks, airlines, life
  insurers, etc. — industries with zero overlap with ICIJ's offshore
  corpus)

This script just produces the enrichment table. The filter logic
lives in bridge_sec_icij_by_name.py.

Output schema (``sec_filer_metadata.parquet``)::

    cik                str    zero-padded CIK10
    name               str    most-recent conformed company name
    sic                str    numeric SIC code or empty
    sic_description    str    human-readable SIC label
    category           str    "Large Accelerated Filer" etc.
    state_of_incorporation  str
    tickers            str    pipe-separated tickers; empty if none
    exchanges          str    pipe-separated exchanges; empty if none
    fetched_at         str    ISO timestamp
    status_code        i32    HTTP status from data.sec.gov

Rate-limited at ~9 req/s (under SEC's 10 req/s fair-use ceiling).
For ~3k unique filers across 4 quarters that's ~6 min Railway-side.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

log = logging.getLogger("enrich_sec_filer_metadata")

_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"

_DEFAULT_USER_AGENT = "Ben Severn bsevern@mjhlifesciences.com"


@dataclass
class FilerMetadata:
    cik: str
    name: str = ""
    sic: str = ""
    sic_description: str = ""
    category: str = ""
    state_of_incorporation: str = ""
    tickers: list[str] = field(default_factory=list)
    exchanges: list[str] = field(default_factory=list)
    fetched_at: str = ""
    status_code: int = 0

    def to_row(self) -> dict[str, str | int]:
        return {
            "cik": self.cik,
            "name": self.name,
            "sic": self.sic,
            "sic_description": self.sic_description,
            "category": self.category,
            "state_of_incorporation": self.state_of_incorporation,
            "tickers": "|".join(self.tickers),
            "exchanges": "|".join(self.exchanges),
            "fetched_at": self.fetched_at,
            "status_code": int(self.status_code),
        }


def fetch_metadata(
    cik: str,
    fetcher: callable[[str], tuple[int, dict]],
) -> FilerMetadata:
    """Fetch one CIK's submissions document, parse the fields we care
    about. ``cik`` must be zero-padded to 10 digits."""

    fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = _SUBMISSIONS_URL.format(cik10=cik)
    try:
        status_code, payload = fetcher(url)
    except Exception as exc:  # noqa: BLE001
        log.warning("metadata fetch failed for cik=%s: %s", cik, exc)
        return FilerMetadata(cik=cik, fetched_at=fetched_at, status_code=0)

    if status_code != 200 or not isinstance(payload, dict):
        return FilerMetadata(cik=cik, fetched_at=fetched_at, status_code=int(status_code))

    return FilerMetadata(
        cik=cik,
        name=str(payload.get("name") or ""),
        sic=str(payload.get("sic") or ""),
        sic_description=str(payload.get("sicDescription") or ""),
        category=str(payload.get("category") or ""),
        state_of_incorporation=str(payload.get("stateOfIncorporation") or ""),
        tickers=[str(t) for t in (payload.get("tickers") or [])],
        exchanges=[str(e) for e in (payload.get("exchanges") or [])],
        fetched_at=fetched_at,
        status_code=200,
    )


def enrich(
    ciks: list[str],
    *,
    fetcher: callable[[str], tuple[int, dict]] | None = None,
    min_interval_s: float = 0.11,
) -> pl.DataFrame:
    """Fetch metadata for every CIK; return a DataFrame.

    ``fetcher`` is dependency-injected so tests run offline.
    ``min_interval_s`` paces requests; default 0.11s ≈ 9 req/s,
    safely under SEC's 10 req/s fair-use cap.
    """

    if fetcher is None:
        fetcher = _http_fetcher_factory()

    rows: list[dict] = []
    last_call = 0.0
    log.info("enriching %d SEC CIKs from data.sec.gov", len(ciks))
    for i, cik in enumerate(ciks, start=1):
        elapsed = time.monotonic() - last_call
        if elapsed < min_interval_s:
            time.sleep(min_interval_s - elapsed)
        last_call = time.monotonic()
        meta = fetch_metadata(cik, fetcher)
        rows.append(meta.to_row())
        if i % 250 == 0:
            log.info("  fetched %d/%d", i, len(ciks))

    return pl.DataFrame(rows)


def _http_fetcher_factory():
    import json as _json

    import httpx

    def fetcher(url: str) -> tuple[int, dict]:
        with httpx.Client(
            headers={
                "User-Agent": _DEFAULT_USER_AGENT,
                "Accept-Encoding": "gzip",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            if r.status_code != 200:
                return r.status_code, {}
            try:
                return r.status_code, r.json()
            except _json.JSONDecodeError:
                return r.status_code, {}

    return fetcher


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--sec-edges",
        type=Path,
        default=Path("/data/processed/sec_13dg_edges.parquet"),
        help="Source of filer_cik values to enrich.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/sec_filer_metadata.parquet"),
    )
    p.add_argument("--limit", type=int, default=0, help="Cap on number of CIKs (0 = no cap).")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.sec_edges.exists():
        raise SystemExit(f"[fatal] {args.sec_edges} missing (run Phase 6 first)")

    sec_df = pl.read_parquet(args.sec_edges)
    ciks = sec_df.select("filer_cik").drop_nulls().unique().to_series().to_list()
    log.info("found %d unique SEC filer CIKs in %s", len(ciks), args.sec_edges)
    if args.limit:
        ciks = ciks[: args.limit]
        log.info("limiting to first %d", len(ciks))

    out = enrich(ciks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(args.out)
    log.info("wrote %d rows to %s", out.height, args.out)
    # Tally outcomes.
    by_status = out.group_by("status_code").len().sort("len", descending=True)
    for row in by_status.iter_rows(named=True):
        log.info("  status=%d: %d", row["status_code"], row["len"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
