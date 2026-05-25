"""Disqualified-director grading: PSC vs. acting director (precision roadmap P1-P3).

The Phase-4 ``regulatory_breach`` signal flags a disqualified person who is a
**PSC** (>25% owner) of a UK company. But s.11 CDDA 1986 bans *directing /
managing*, not *owning shares* — so a disqualified PSC is only a candidate breach
if they are also acting as a director. This module reads a company's live
Companies House **officers** page (fetched via Firecrawl) and grades each lead:

- ``acting_director``  — the disqualified person is a current (Active) director
  (strong s.11 breach candidate);
- ``resigned_director`` — they were a director but have resigned (weaker: stepped
  off the board, may retain ownership);
- ``psc_only``         — not an officer at all, just a >25% shareholder (s.11 does
  not ban this);
- ``none``             — no name match on the officer list.

The same scrape also yields the officer's DOB (month+year), correspondence
address, and live status, so it doubles as identity confirmation (P2) and
currency confirmation (P3). Kept pure so the parser/grader are testable without
network.
"""

from __future__ import annotations

import re

import polars as pl

__all__ = [
    "DIRECTOR_BREACH_COLUMNS",
    "normalize_person",
    "parse_ch_officers",
    "grade_company",
]

DIRECTOR_BREACH_COLUMNS: tuple[str, ...] = (
    "lead_id",
    "breach_grade",
    "acting_director_breach",
    "identity_confidence",
    "live_confirmed",
    "matched_role",
    "matched_officer_name",
)

_MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
        start=1,
    )
}


def normalize_person(name: str | None) -> str:
    """Normalise to ``"forename surname"``, lowercase, punctuation -> space.

    Handles the CH ``"SURNAME, Forename"`` heading form and hyphenated names
    (``"ASANTE-FRIMPONG, Henry"`` -> ``"henry asante frimpong"``) so it lines up
    with the disqualified register's ``normalized_person_name``.
    """
    if not name:
        return ""
    s = name.strip()
    if "," in s:
        sur, _, fore = s.partition(",")
        s = f"{fore} {sur}"
    s = re.sub(r"[^a-z\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def _dob_ym(value: str | None) -> str | None:
    """``"January 1968"`` -> ``"1968-01"``."""
    if not value:
        return None
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", value)
    if m and m.group(1).lower() in _MONTHS:
        return f"{m.group(2)}-{_MONTHS[m.group(1).lower()]:02d}"
    return None


def _addr_tokens(addr: str | None) -> set[str]:
    if not addr:
        return set()
    toks = re.sub(r"[^a-z0-9\s]", " ", addr.lower()).split()
    return {t for t in toks if len(t) > 1}


def parse_ch_officers(markdown: str) -> list[dict[str, object]]:
    """Parse a CH ``/company/<n>/officers`` page markdown into officer records.

    Each officer is a ``## [SURNAME, Forename](url)`` heading followed by
    label/value lines (``Role`` -> status then kind, ``Date of birth``,
    ``Correspondence address``, ``Appointed on``).
    """
    md = markdown or ""
    blocks = re.split(r"^##\s+\[", md, flags=re.M)[1:]
    out: list[dict[str, object]] = []
    for b in blocks:
        head, _, rest = b.partition("\n")
        name = head.split("](")[0].strip()
        if not name:
            continue
        lines = [ln.strip() for ln in rest.splitlines()]

        def _after(label: str, _lines: list[str] = lines) -> str | None:
            for i, ln in enumerate(_lines):
                if ln == label:
                    for nxt in _lines[i + 1 :]:
                        if nxt:
                            return nxt
            return None

        status = kind = None
        for i, ln in enumerate(lines):
            if ln == "Role":
                vals = [x for x in lines[i + 1 : i + 5] if x]
                status = vals[0] if vals else None
                kind = vals[1] if len(vals) > 1 else None
                break

        out.append(
            {
                "name": name,
                "norm_name": normalize_person(name),
                "status": (status or "").lower() or None,
                "kind": (kind or "").lower() or None,
                "dob_ym": _dob_ym(_after("Date of birth")),
                "appointed_on": _after("Appointed on"),
                "address": _after("Correspondence address"),
            }
        )
    return out


def _officer_rank(o: dict[str, object]) -> int:
    return (2 if o["status"] == "active" else 0) + (1 if o["kind"] == "director" else 0)


def grade_company(
    officers: list[dict[str, object]],
    disq_name: str,
    disq_dob_ym: str | None,
    disq_address: str | None = None,
) -> dict[str, object]:
    """Grade one disqualified-PSC lead against the company's officer list."""
    dn = normalize_person(disq_name)
    da = _addr_tokens(disq_address)
    matches = [o for o in officers if o["norm_name"] == dn]
    if not matches:
        # Disqualified person is a PSC but not on the officer list -> shareholder.
        return {
            "breach_grade": "psc_only",
            "acting_director_breach": 0.0,
            "identity_confidence": 0.5,  # name+dob_ym matched upstream; unconfirmed here
            "live_confirmed": False,
            "matched_role": None,
            "matched_officer_name": None,
        }
    best = max(matches, key=_officer_rank)
    conf = 0.5  # name match
    if best["dob_ym"] and disq_dob_ym and best["dob_ym"] == disq_dob_ym:
        conf += 0.3
    if da and len(da & _addr_tokens(best["address"])) >= 3:
        conf += 0.2
    active = best["status"] == "active"
    director = best["kind"] == "director"
    if active and director:
        grade = "acting_director"
    elif director:
        grade = "resigned_director"
    else:
        grade = "officer_other"
    return {
        "breach_grade": grade,
        "acting_director_breach": 1.0 if grade == "acting_director" else 0.0,
        "identity_confidence": round(min(conf, 1.0), 2),
        "live_confirmed": active,
        "matched_role": f"{best['status'] or '?'} {best['kind'] or '?'}".strip(),
        "matched_officer_name": str(best["name"]),
    }


_GRADE_ORDER = ["acting_director", "resigned_director", "officer_other", "psc_only", "unknown"]


def summarize(graded: pl.DataFrame) -> dict[str, int]:
    """Counts per ``breach_grade`` (precision roadmap P6 systemic aggregate)."""
    if not graded.height:
        return {g: 0 for g in _GRADE_ORDER}
    vc = graded["breach_grade"].value_counts()
    counts = {r["breach_grade"]: r["count"] for r in vc.iter_rows(named=True)}
    return {g: int(counts.get(g, 0)) for g in _GRADE_ORDER}


def grade_to_frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    """Build the director-breach signal frame (one row per lead)."""
    if not rows:
        schema = {c: pl.Utf8 for c in DIRECTOR_BREACH_COLUMNS}
        schema["acting_director_breach"] = pl.Float64
        schema["identity_confidence"] = pl.Float64
        schema["live_confirmed"] = pl.Boolean
        return pl.DataFrame(schema=schema)
    return pl.DataFrame(rows).select(list(DIRECTOR_BREACH_COLUMNS))
