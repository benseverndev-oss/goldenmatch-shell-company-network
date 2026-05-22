"""Hand-eyeball verification for the disqualified-x-ICIJ queue.

Reads ``disqualified_verification_queue.json``, walks every
candidate at score >= --min-score (default 1.0, i.e. the unique-on-
both-sides set, ~219 rows), and for each one fetches:

  1. The OS gb_coh_disqualified source URL — the actual UK Companies
     House disqualified-director page for that person. Extracts:
     companies they were directing, disqualification dates,
     disqualification length, conduct findings, current status.

  2. The ICIJ Offshore Leaks node URL — the actual offshoreleaks.icij.org
     node page for that ICIJ officer record. Extracts:
     country, source label, related entities, address, alias.

Polite to both sources at min_interval seconds per request.

Output:
  D:/.../disqualified_verification_report.json — per-candidate full
  details + a top-line summary of which look genuinely same-person
  (DOB / address overlap) vs name-coincidence.

Run locally — writes to repo dir on D:, avoids touching C:.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger("verify_disqualified_queue")

_UA = "GoldenMatch case study bsevern@mjhlifesciences.com"


def _strip_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|&amp;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_ch_disq(text: str) -> dict:
    """Best-effort extraction from a UK CH disqualified-director page.

    Field patterns we look for (CH layout-dependent — may need updates):
      Date of birth, Nationality, Date order starts, Disqualification
      length, Reason for disqualification, conduct findings,
      Company name, Disqualification status.
    """

    def m(pat: str) -> str | None:
        rm = re.search(pat, text)
        return rm.group(1).strip() if rm else None

    return {
        "dob": m(r"Date of birth\s+([A-Za-z0-9 ]+?)(?=\s{2,}|Nationality|Disqualification|Address|$)"),
        "nationality": m(r"Nationality\s+([A-Za-z, ]+?)(?=\s{2,}|Date|Disqualification|Address|$)"),
        "address": m(r"(?:Last known address|Address)\s+([^|]{10,300}?)(?=\s{2,}|Disqualification|$)"),
        "disq_starts": m(r"Date of order starts?\s+(\d{1,2} \w+ \d{4})"),
        "disq_length": m(r"Disqualification length\s+([0-9 a-zA-Z]+?)(?=\s{2,}|$)"),
        "disq_status": m(r"Status\s+([A-Za-z ]+?)(?=\s{2,}|$)"),
        "conduct": (m(r"Reasons for disqualification\s+([^|]{20,2000}?)(?=\s{2,}Companies|$)") or "")[:1000],
        "companies": list(set(re.findall(r"([A-Z0-9 &.,'-]{4,80}?\s+LIMITED)", text)))[:10],
    }


def _extract_icij(text: str) -> dict:
    return {
        "country": _first_capture(text, r"Country[s:]?\s+([A-Za-z, ]+?)(?=\s{2,}|$)"),
        "linked_to": list(set(re.findall(r"connected to\s+([A-Z][A-Za-z0-9 &.,'-]{3,80})", text)))[:10],
        "addresses": list(set(re.findall(r"Address\s+([^|]{10,200})", text)))[:5],
        "sources": list(set(re.findall(r"Data from:\s+([A-Za-z ]+)", text)))[:5],
    }


def _first_capture(text: str, pat: str) -> str | None:
    m = re.search(pat, text)
    return m.group(1).strip() if m else None


def _fetch(client: httpx.Client, url: str) -> str | None:
    try:
        r = client.get(url, timeout=30.0)
        if r.status_code == 200:
            return r.text
        log.warning("  %d for %s", r.status_code, url)
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("  fetch error %s: %s", url, exc)
        return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input",
        type=Path,
        default=Path("disqualified_verification_queue.json"),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("disqualified_verification_report.json"),
    )
    p.add_argument("--min-score", type=float, default=1.0)
    p.add_argument("--max-rows", type=int, default=500)
    p.add_argument("--min-interval", type=float, default=1.0)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    data = json.loads(args.input.read_text(encoding="utf-8"))
    queue = [r for r in data["queue"] if r.get("score", 0) >= args.min_score][: args.max_rows]
    log.info("verifying %d candidates (score >= %.2f)", len(queue), args.min_score)

    out_rows: list[dict] = []
    with httpx.Client(headers={"User-Agent": _UA}, follow_redirects=True) as client:
        last = 0.0
        for i, row in enumerate(queue, start=1):
            log.info("[%d/%d] candidate", i, len(queue))

            # CH side
            ch_url = row.get("disq_source_url")
            ch_summary: dict = {}
            if ch_url:
                elapsed = time.monotonic() - last
                if elapsed < args.min_interval:
                    time.sleep(args.min_interval - elapsed)
                last = time.monotonic()
                html = _fetch(client, ch_url)
                if html:
                    ch_summary = _extract_ch_disq(_strip_text(html))

            # ICIJ side(s) — take the first ICIJ record only (avoid 5x fetches per row)
            icij_records = row.get("icij_records") or []
            icij_summary: dict = {}
            if icij_records:
                ic_url = icij_records[0].get("icij_url")
                if ic_url:
                    elapsed = time.monotonic() - last
                    if elapsed < args.min_interval:
                        time.sleep(args.min_interval - elapsed)
                    last = time.monotonic()
                    html = _fetch(client, ic_url)
                    if html:
                        icij_summary = _extract_icij(_strip_text(html))

            # Same-person hypothesis: if either DOB matches or addresses
            # share a token, mark as 'likely same person'.
            disq_dob = (row.get("disq_birth_date") or "")[:10]
            ch_dob = (ch_summary.get("dob") or "").strip()
            disq_addr = (row.get("disq_addresses") or "").lower()
            icij_addrs = " | ".join(icij_summary.get("addresses") or []).lower()
            verdict = "name-only"
            if ch_dob and disq_dob and ch_dob.startswith(disq_dob[:4]):
                verdict = "dob-consistent"
            if disq_addr and icij_addrs:
                disq_tokens = set(re.findall(r"\w{4,}", disq_addr))
                icij_tokens = set(re.findall(r"\w{4,}", icij_addrs))
                overlap = disq_tokens & icij_tokens
                if len(overlap) >= 2:
                    verdict = "address-token-overlap"

            out_rows.append(
                {
                    "name": row.get("disq_canonical_name"),
                    "dob": row.get("disq_birth_date"),
                    "nationality": row.get("disq_nationality"),
                    "score": row.get("score"),
                    "addresses": row.get("disq_addresses"),
                    "topics": row.get("disq_topics"),
                    "disq_source_url": ch_url,
                    "ch_extracted": ch_summary,
                    "icij_records": icij_records,
                    "icij_first_extracted": icij_summary,
                    "verdict": verdict,
                }
            )

    args.out.write_text(
        json.dumps(
            {
                "n_verified": len(out_rows),
                "rows": out_rows,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
