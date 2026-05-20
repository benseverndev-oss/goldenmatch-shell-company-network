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

# Forms we want. Anything with prefix "SC 13D" or "SC 13G" (including /A).
_INTERESTING_FORM_PREFIXES = ("SC 13D", "SC 13G")

_FULL_INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/form.idx"

# An EDGAR full-index "form.idx" row is fixed-width text:
#   Form Type      Company Name          CIK    Date Filed   Filename
#   12 chars       62 chars              12     12           remainder
_IDX_ROW_RE = re.compile(
    r"^(?P<form>.{12})(?P<company>.{62})(?P<cik>\d+)\s+(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<path>\S+)\s*$"
)

# SGML header field markers in a .txt filing.
_SGML_FIELD_RE = re.compile(r"<(?P<tag>[A-Z\-]+)>(?P<value>[^\n<]+)")


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

    The filing wraps the actual documents but the header block at the top
    has FILER / SUBJECT-COMPANY sub-sections with COMPANY-DATA / CIK /
    CONFORMED-NAME tags. We only care about a few of these.
    """

    fields: dict[str, str] = {}
    section: str | None = None
    # Maps the canonical block-header forms EDGAR emits to our normalised
    # section keys. Both bracketed (``<FILER>``) and colon-terminated
    # (``SUBJECT COMPANY:``) styles appear across vintages.
    _section_aliases = {
        "<SUBJECT-COMPANY>": "subject-company",
        "SUBJECT COMPANY:": "subject-company",
        "<FILER>": "filer",
        "FILER:": "filer",
        "<REPORTING-OWNER>": "reporting-owner",
        "REPORTING-OWNER:": "reporting-owner",
        "REPORTING OWNER:": "reporting-owner",
    }
    for line in text.splitlines():
        s = line.strip()
        if s in _section_aliases:
            section = _section_aliases[s]
            continue
        m = _SGML_FIELD_RE.match(s)
        if not m:
            continue
        tag = m.group("tag")
        value = m.group("value").strip()
        prefix = (section or "header") + "."
        # Only collect the *first* occurrence per scoped key to avoid the
        # OPERATING-DATA / FILING-VALUES blocks overwriting things.
        key = f"{prefix}{tag}"
        if key not in fields:
            fields[key] = value
    return fields


def extract_edge_from_sgml(
    fields: dict[str, str], *, accession: str, form: str, filed_date: str
) -> Filing13DGEdge | None:
    """Construct a single filer->subject edge from parsed SGML header
    fields. Returns None if either side is missing."""

    filer_cik = fields.get("filer.CIK") or fields.get("reporting-owner.CIK")
    filer_name = (
        fields.get("filer.COMPANY-CONFORMED-NAME")
        or fields.get("reporting-owner.COMPANY-CONFORMED-NAME")
        or ""
    )
    subject_cik = fields.get("subject-company.CIK")
    subject_name = fields.get("subject-company.COMPANY-CONFORMED-NAME") or ""

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
