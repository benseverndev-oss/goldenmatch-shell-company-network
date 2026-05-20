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
_SGML_PLAIN_FIELD_RE = re.compile(
    r"^\s*(?P<tag>[A-Z][A-Z\s\-]*[A-Z]):\s+(?P<value>\S.*?)\s*$"
)


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


def _http_fetcher(user_agent: str):
    """Returns ``(fetch_idx, fetch_filing)`` using httpx + the SEC's
    required User-Agent header."""

    import httpx

    client = httpx.Client(
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip"},
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
    )

    def fetch_idx(year: int, quarter: int) -> str:
        url = _FULL_INDEX_URL.format(year=year, quarter=quarter)
        r = client.get(url)
        r.raise_for_status()
        return r.text

    def fetch_filing(path: str) -> str:
        url = f"https://www.sec.gov/Archives/{path}"
        r = client.get(url)
        r.raise_for_status()
        return r.text

    return fetch_idx, fetch_filing


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--quarter", type=int, required=True, choices=(1, 2, 3, 4))
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
        help="optional cap on number of filings to fetch (0 = no cap).",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    fetch_idx, fetch_filing = _http_fetcher(args.user_agent)
    log.info("fetching form.idx for %d Q%d", args.year, args.quarter)
    idx_text = fetch_idx(args.year, args.quarter)
    entries = parse_form_idx(idx_text)
    log.info("found %d 13D/G entries in form.idx", len(entries))
    if args.limit:
        entries = entries[: args.limit]
        log.info("limiting to first %d entries", len(entries))

    edges = build_edges(entries, fetch_filing)
    log.info("extracted %d filer->subject edges", len(edges))
    edges_to_parquet(edges, args.out)
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
