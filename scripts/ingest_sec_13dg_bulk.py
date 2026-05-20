"""Bulk-ingest SEC EDGAR Schedule 13D/13G filings.

Sibling of ``src/shellnet/registries/sec_edgar_13d_13g.py`` (point-query
adapter). This script walks the EDGAR full-index for a date range,
selects ``SC 13D`` / ``SC 13G`` (and amendments) filings, fetches each
filing's SGML header, and emits a parquet of **filer -> subject** edges.

Output schema (``sec_13dg_edges.parquet``)::

    accession        str    SEC accession number (unique key)
    form             str    SC 13D | SC 13D/A | SC 13G | SC 13G/A
    filed_date       str    ISO date
    filer_cik        str    zero-padded CIK10 of the 13D/G filer
    filer_name       str    company name of the filer
    subject_cik      str    zero-padded CIK10 of the issuer / subject
    subject_name     str    issuer / subject company name

Each row becomes a ``beneficial_owner_of`` edge in the confidence graph
(Phase 7 will wire this in). The edge credibility is ``0.92`` —
SEC filings are public, court-admissible, and signed under penalty of
perjury.

Compute lives on Railway (the full index for one quarter is ~50 MB
text; parsing per-filing SGML headers is fan-out across thousands of
files). Local execution is supported but slow.

Usage::

    uv run python scripts/ingest_sec_13dg_bulk.py --year 2025 --quarter 4
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

log = logging.getLogger("ingest_sec_13dg_bulk")

# Forms we want. SEC renamed "SC 13D" / "SC 13G" to "SCHEDULE 13D" /
# "SCHEDULE 13G" (with "/A" amendments). The old prefixes match zero
# 2025 Q4 filings — we keep them in the prefix list as a safety net for
# any archived filings that may still use the old code, but every live
# Phase-6 row should hit the new ones.
_INTERESTING_FORM_PREFIXES = (
    "SCHEDULE 13D",
    "SCHEDULE 13G",
    "SC 13D",
    "SC 13G",
)

_FULL_INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/form.idx"

# EDGAR's full-index form.idx is whitespace-separated rather than strictly
# fixed-width. Form names may contain spaces ("SCHEDULE 13D"), so we anchor
# on 2+ whitespace as the field separator.
_IDX_ROW_RE = re.compile(
    r"^(?P<form>\S.*?)\s{2,}"
    r"(?P<company>\S.*?)\s{2,}"
    r"(?P<cik>\d+)\s+"
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<path>\S+)\s*$"
)

# Legacy bracketed SGML field marker, e.g. ``<CIK>0000999999``. Pre-2010-ish
# vintage; kept for archived filings.
_SGML_BRACKETED_FIELD_RE = re.compile(r"<(?P<tag>[A-Z\-]+)>(?P<value>[^\n<]+)")

# Modern plain-text field marker, e.g. ``COMPANY CONFORMED NAME:\t\tACME``.
# Keys are uppercase words separated by spaces, terminated by a colon.
# Value follows after whitespace.
_SGML_PLAIN_FIELD_RE = re.compile(r"^\s*(?P<tag>[A-Z][A-Z\s\-]*[A-Z]):\s+(?P<value>\S.*?)\s*$")


@dataclass(frozen=True)
class IndexEntry:
    """One row from the EDGAR full-index/form.idx file."""

    form: str
    company: str
    cik: str
    date_filed: str
    path: str  # relative SEC archive path to the filing .txt


@dataclass(frozen=True)
class Filing13DGEdge:
    """One filer -> subject edge extracted from a 13D/G filing."""

    accession: str
    form: str
    filed_date: str
    filer_cik: str
    filer_name: str
    subject_cik: str
    subject_name: str


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_form_idx(text: str) -> list[IndexEntry]:
    """Parse the fixed-width EDGAR full-index ``form.idx`` text into rows
    for 13D/G filings only."""

    rows: list[IndexEntry] = []
    started = False
    for line in text.splitlines():
        # The header ends with a line of dashes. Skip everything above.
        if not started:
            if line.startswith("-"):
                started = True
            continue
        # Cheap pre-filter on form prefix.
        if not any(line.startswith(p) for p in _INTERESTING_FORM_PREFIXES):
            continue
        m = _IDX_ROW_RE.match(line)
        if not m:
            continue
        form = m.group("form").strip()
        # Reject false positives (e.g. "SC 13E3" would also start with "SC 13").
        if not any(form == p or form.startswith(p) for p in _INTERESTING_FORM_PREFIXES):
            continue
        rows.append(
            IndexEntry(
                form=form,
                company=m.group("company").strip(),
                cik=m.group("cik").zfill(10),
                date_filed=m.group("date"),
                path=m.group("path").strip(),
            )
        )
    return rows


def parse_sgml_header(text: str) -> dict[str, str]:
    """Extract the SGML header fields from an EDGAR .txt filing.

    Supports both the legacy bracketed format (``<CIK>0000999999``,
    pre-2010-ish vintage) and the modern plain-text format
    (``CENTRAL INDEX KEY:\\t0000999999``) that all 2025 Q4 SCHEDULE 13D/G
    filings use. The two formats may also be mixed within one filing.

    Section markers in the modern format:
      ``SUBJECT COMPANY:``  -> ``subject-company``
      ``FILED BY:``         -> ``filed-by``  (NOT ``FILER:``)
      ``REPORTING-OWNER:``  -> ``reporting-owner``

    Each field gets a key like ``<section>.<TAG>`` where TAG retains its
    original spacing (e.g. ``subject-company.COMPANY CONFORMED NAME``)
    so downstream consumers can look up either style.
    """

    fields: dict[str, str] = {}
    section: str | None = None
    _section_aliases = {
        # Legacy bracketed-style markers
        "<SUBJECT-COMPANY>": "subject-company",
        "<FILER>": "filer",
        "<REPORTING-OWNER>": "reporting-owner",
        # Modern plain-text markers. Trailing tabs/spaces are stripped
        # before lookup so "SUBJECT COMPANY:" matches "SUBJECT COMPANY:\\t".
        "SUBJECT COMPANY:": "subject-company",
        "FILER:": "filer",
        "FILED BY:": "filed-by",
        "REPORTING-OWNER:": "reporting-owner",
        "REPORTING OWNER:": "reporting-owner",
    }
    for line in text.splitlines():
        s = line.strip()
        if s in _section_aliases:
            section = _section_aliases[s]
            continue

        tag: str | None = None
        value: str | None = None
        # Try the legacy bracketed format first; if it doesn't match,
        # fall back to the modern plain-text format.
        m = _SGML_BRACKETED_FIELD_RE.match(s)
        if m:
            tag = m.group("tag")
            value = m.group("value").strip()
        else:
            m = _SGML_PLAIN_FIELD_RE.match(line)
            if m:
                tag = m.group("tag").strip()
                value = m.group("value").strip()
                # Skip the section sub-headers that look like plain fields
                # but have no value past the colon (e.g. "COMPANY DATA:").
                if not value:
                    continue
        if tag is None or value is None:
            continue
        prefix = (section or "header") + "."
        key = f"{prefix}{tag}"
        # First-occurrence-wins so nested FILING VALUES / BUSINESS ADDRESS
        # blocks don't overwrite the top-level section field.
        if key not in fields:
            fields[key] = value
    return fields


def extract_edge_from_sgml(
    fields: dict[str, str], *, accession: str, form: str, filed_date: str
) -> Filing13DGEdge | None:
    """Construct a single filer->subject edge from parsed SGML header
    fields. Returns None if either side is missing.

    Looks up keys in both the legacy bracketed format (tags like ``CIK``,
    ``COMPANY-CONFORMED-NAME``) and the modern plain-text format (tags
    like ``CENTRAL INDEX KEY``, ``COMPANY CONFORMED NAME``). Also accepts
    the modern ``FILED BY:`` section in addition to the legacy ``FILER:``.
    """

    def _first(*keys: str) -> str:
        for k in keys:
            v = fields.get(k)
            if v:
                return v
        return ""

    filer_cik = _first(
        # modern plain-text style first (live filings)
        "filed-by.CENTRAL INDEX KEY",
        "filer.CENTRAL INDEX KEY",
        "reporting-owner.CENTRAL INDEX KEY",
        # legacy bracketed style
        "filed-by.CIK",
        "filer.CIK",
        "reporting-owner.CIK",
    )
    filer_name = _first(
        "filed-by.COMPANY CONFORMED NAME",
        "filer.COMPANY CONFORMED NAME",
        "reporting-owner.COMPANY CONFORMED NAME",
        "filed-by.COMPANY-CONFORMED-NAME",
        "filer.COMPANY-CONFORMED-NAME",
        "reporting-owner.COMPANY-CONFORMED-NAME",
    )
    subject_cik = _first(
        "subject-company.CENTRAL INDEX KEY",
        "subject-company.CIK",
    )
    subject_name = _first(
        "subject-company.COMPANY CONFORMED NAME",
        "subject-company.COMPANY-CONFORMED-NAME",
    )

    if not filer_cik or not subject_cik:
        return None

    return Filing13DGEdge(
        accession=accession,
        form=form,
        filed_date=filed_date,
        filer_cik=str(filer_cik).zfill(10),
        filer_name=filer_name,
        subject_cik=str(subject_cik).zfill(10),
        subject_name=subject_name,
    )


def accession_from_index_path(path: str) -> str:
    """Extract the canonical accession number from a full-index path.

    Example::

        edgar/data/0000012345/0000012345-25-000067.txt
            -> "0000012345-25-000067"
    """

    name = path.rsplit("/", 1)[-1]
    return name.removesuffix(".txt")


# ---------------------------------------------------------------------------
# Edge builder
# ---------------------------------------------------------------------------


def build_edges(
    index_entries: Iterable[IndexEntry],
    fetch_filing: callable[[str], str],
) -> list[Filing13DGEdge]:
    """Iterate over ``index_entries`` and fetch + parse each filing.

    ``fetch_filing(path) -> sgml_text`` is dependency-injected so the
    HTTP layer can be mocked in tests.
    """

    edges: list[Filing13DGEdge] = []
    for entry in index_entries:
        try:
            sgml = fetch_filing(entry.path)
        except Exception as exc:  # noqa: BLE001 — network errors are skip-and-log.
            log.warning("fetch failed for %s: %s", entry.path, exc)
            continue
        fields = parse_sgml_header(sgml)
        accession = accession_from_index_path(entry.path)
        edge = extract_edge_from_sgml(
            fields,
            accession=accession,
            form=entry.form,
            filed_date=entry.date_filed,
        )
        if edge is None:
            log.debug("skipped %s (missing filer or subject CIK)", accession)
            continue
        edges.append(edge)
    return edges


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def edges_to_parquet(edges: list[Filing13DGEdge], out: Path) -> None:
    import polars as pl

    if not edges:
        # Materialise an empty frame with the right schema for downstream
        # consumers (Phase 7).
        empty = pl.DataFrame(
            schema={
                "accession": pl.String,
                "form": pl.String,
                "filed_date": pl.String,
                "filer_cik": pl.String,
                "filer_name": pl.String,
                "subject_cik": pl.String,
                "subject_name": pl.String,
            }
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        empty.write_parquet(out)
        return
    df = pl.DataFrame([e.__dict__ for e in edges])
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)


# ---------------------------------------------------------------------------
# HTTP driver
# ---------------------------------------------------------------------------


def _http_fetcher(user_agent: str, *, min_interval_s: float = 0.11):
    """Returns ``(fetch_idx, fetch_filing)`` using httpx + the SEC's
    required User-Agent header.

    SEC's fair-use policy caps unauthenticated access at ~10 requests
    per second. Without pacing, an earlier run got 128 edges out of
    5000 attempted filings — most fetches silently 403'd. We enforce
    a minimum inter-request interval (default 110 ms ≈ 9 req/s, safely
    under the threshold) so a long run can sustain throughput without
    tripping the limiter.
    """

    import time

    import httpx

    client = httpx.Client(
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip"},
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
    )

    last_call = [0.0]  # mutable closure cell

    def _pace() -> None:
        elapsed = time.monotonic() - last_call[0]
        if elapsed < min_interval_s:
            time.sleep(min_interval_s - elapsed)
        last_call[0] = time.monotonic()

    def fetch_idx(year: int, quarter: int) -> str:
        _pace()
        url = _FULL_INDEX_URL.format(year=year, quarter=quarter)
        r = client.get(url)
        r.raise_for_status()
        return r.text

    def fetch_filing(path: str) -> str:
        _pace()
        url = f"https://www.sec.gov/Archives/{path}"
        r = client.get(url)
        r.raise_for_status()
        return r.text

    return fetch_idx, fetch_filing


def _parse_year_quarter(spec: str) -> tuple[int, int]:
    """Parse a ``YYYY/Q`` spec like ``2025/4`` into (year, quarter)."""

    try:
        year_s, quarter_s = spec.split("/")
        year, quarter = int(year_s), int(quarter_s)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--year-quarter must be in 'YYYY/Q' form, got {spec!r}"
        ) from exc
    if quarter not in (1, 2, 3, 4):
        raise argparse.ArgumentTypeError(
            f"--year-quarter quarter must be 1-4, got {quarter}"
        )
    return year, quarter


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    # Phase 13: accept one or more year/quarter pairs and concatenate.
    # The legacy --year/--quarter flags are still accepted for backwards
    # compatibility (the workflow may pass either form during the
    # transition).
    p.add_argument(
        "--year-quarter",
        type=_parse_year_quarter,
        nargs="+",
        default=None,
        help=(
            "One or more year/quarter pairs in 'YYYY/Q' form, e.g. "
            "'--year-quarter 2025/1 2025/2 2025/3 2025/4'. Edges from "
            "all quarters are concatenated into a single --out parquet."
        ),
    )
    p.add_argument(
        "--year",
        type=int,
        default=None,
        help=argparse.SUPPRESS,  # legacy
    )
    p.add_argument(
        "--quarter",
        type=int,
        default=None,
        choices=(1, 2, 3, 4),
        help=argparse.SUPPRESS,  # legacy
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/sec_13dg_edges.parquet"),
    )
    p.add_argument(
        "--user-agent",
        type=str,
        default=(
            "GoldenMatch shell-company-network discovery pipeline "
            "https://github.com/benseverndev-oss/goldenmatch-shell-company-network "
            "ben@example.com"
        ),
        help="SEC EDGAR requires a descriptive User-Agent with contact email.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help=(
            "Optional cap on number of filings to fetch PER QUARTER "
            "(0 = no cap). Cap is applied independently per quarter."
        ),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # Resolve which quarters to ingest. New --year-quarter wins; otherwise
    # fall back to the legacy single --year/--quarter pair; otherwise
    # nothing-to-do is an error.
    quarters: list[tuple[int, int]]
    if args.year_quarter:
        quarters = args.year_quarter
    elif args.year is not None and args.quarter is not None:
        quarters = [(args.year, args.quarter)]
    else:
        raise SystemExit(
            "[fatal] must pass --year-quarter (preferred) or --year + --quarter"
        )

    fetch_idx, fetch_filing = _http_fetcher(args.user_agent)
    all_edges: list[Filing13DGEdge] = []
    for year, quarter in quarters:
        log.info("fetching form.idx for %d Q%d", year, quarter)
        try:
            idx_text = fetch_idx(year, quarter)
        except Exception as exc:  # noqa: BLE001
            log.warning("form.idx fetch failed for %d Q%d: %s; skipping", year, quarter, exc)
            continue
        entries = parse_form_idx(idx_text)
        log.info("  %d Q%d -> %d 13D/G entries in form.idx", year, quarter, len(entries))
        if args.limit:
            entries = entries[: args.limit]
            log.info("    capped to %d entries", len(entries))
        edges = build_edges(entries, fetch_filing)
        log.info("    extracted %d filer->subject edges", len(edges))
        all_edges.extend(edges)

    # De-dup by accession in case the same filing appears across quarters
    # (e.g. amendments straddle a quarter boundary in EDGAR's index).
    seen: set[str] = set()
    deduped: list[Filing13DGEdge] = []
    for e in all_edges:
        if e.accession in seen:
            continue
        seen.add(e.accession)
        deduped.append(e)
    log.info(
        "total: %d edges across %d quarters (%d before dedup)",
        len(deduped),
        len(quarters),
        len(all_edges),
    )

    edges_to_parquet(deduped, args.out)
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
