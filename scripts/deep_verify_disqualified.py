"""Deep verification for the top-N disqualified-directors candidates.

Fetches the full UK Companies House disqualified-director page for
each candidate and extracts the chargeable-evidence fields:

  - Confirmed full name
  - Date of birth
  - Nationality
  - Last known address (often masked on CH; partial post-codes OK)
  - Disqualification start date + length + active/expired status
  - The Reason / Conduct findings paragraph (verbatim)
  - The list of UK companies they were directing at time of conduct

Optionally fetches the ICIJ node page for additional context
(connected entities, the leak that named them).

Output: ``disqualified_deep_verification.json`` — one row per
candidate with everything a reporter needs to assess the lead.

Reads the verification queue ``disqualified_verification_queue.json``
and walks the top --top-n rows.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger("deep_verify_disqualified")

_UA = "GoldenMatch case study bsevern@mjhlifesciences.com"


def _strip(html: str) -> str:
    """Strip HTML tags, normalize whitespace."""
    text = re.sub(r"<[^>]+>", "|", html)
    text = re.sub(r"&nbsp;|&amp;", " ", text)
    text = re.sub(r"\|+", "|", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_ch_disq_deep(text: str) -> dict:
    """Best-effort deep extraction from a CH disqualified-director page.

    The CH page layout (find-and-update.company-information.service.gov.uk/
    disqualified-officers/<id>):

      Officer details:
        Name, DOB, Nationality, Last known address
      Disqualification details:
        Date of order, Disqualification length, Status, Court,
        Reasons for disqualification (conduct paragraph),
        Companies they were directing at time of conduct
    """

    def m(pat: str) -> str | None:
        rm = re.search(pat, text)
        return rm.group(1).strip() if rm else None

    # Find companies block — typically listed as company names + numbers
    companies = []
    for cm in re.finditer(
        r"(\b[A-Z0-9][A-Z0-9 &.,'-]{3,80}(?:LIMITED|LTD|PLC|LLP|GROUP|COMPANY))\b\s*(?:\|\s*([0-9]{6,8}))?",
        text[:50000],
    ):
        nm = cm.group(1).strip()
        if any(skip in nm.upper() for skip in ("INFORMATION", "REGISTRY", "GOV.UK", "SERVICE")):
            continue
        if len(companies) >= 30:
            break
        companies.append({"name": nm, "company_number": cm.group(2)})

    # Status keywords
    status = None
    if re.search(r"(?i)\bcurrently disqualified\b", text):
        status = "currently_disqualified"
    elif re.search(r"(?i)\bdisqualification (?:has )?ended\b|\bExpired\b", text):
        status = "expired"

    return {
        "full_name": m(
            r"Disqualified officer details\s*\|\s*(?:\|\s*)?([A-Z][A-Za-z'\-\. ]+?(?: [A-Z][A-Za-z'\-\. ]+){0,4})\s*\|\s*Date of birth"
        ),
        "dob": m(r"Date of birth\s*\|+\s*(\d{1,2} \w+ \d{4})"),
        "nationality": m(r"Nationality\s*\|+\s*([A-Za-z, ]+?)(?=\s*\|)"),
        "address": m(
            r"Last known address\s*\|+\s*(.{10,300}?)(?=Date of order|Disqualification|\|\s*Disqualification|\|\s*Date)"
        ),
        "disq_start": m(r"Date of order starts?\s*\|+\s*(\d{1,2} \w+ \d{4})"),
        "disq_end": m(r"Date order (?:ends?|expires?)\s*\|+\s*(\d{1,2} \w+ \d{4})"),
        "disq_length": m(r"Disqualification length\s*\|+\s*([0-9]+ years?(?: \d+ months?)?)"),
        "court": m(r"Court\s*\|+\s*([A-Za-z ,'-]+?)(?=\s*\||$)"),
        "status": status,
        "reasons_conduct": (
            m(r"Reasons for disqualification\s*\|+\s*(.{50,4000}?)(?=\s*\|\s*Companies|$)") or ""
        )[:2000],
        "companies_named": companies,
    }


def _extract_icij_deep(text: str) -> dict:
    return {
        "icij_name": (
            re.search(r"name\s*\|+\s*([A-Z][^|]{2,100}?)(?=\s*\||$)", text) or [None, None]
        )[1],
        "icij_country": (
            re.search(r"Countries?\s*\|+\s*([A-Za-z, ]+?)(?=\s*\||$)", text) or [None, None]
        )[1],
        "icij_source": (re.search(r"Data from:?\s*([A-Za-z ]+)", text) or [None, None])[1],
        "icij_related_entities": list(
            set(re.findall(r"Connected to\s+\|+\s*([A-Z][A-Z0-9 &.,'-]{3,80})", text))
        )[:15],
        "icij_addresses": list(set(re.findall(r"Address\s*\|+\s*([^|]{10,200})", text)))[:5],
    }


def _fetch(client: httpx.Client, url: str) -> str | None:
    try:
        r = client.get(url, timeout=30.0)
        if r.status_code == 200:
            return r.text
        log.warning("  %d for %s", r.status_code, url)
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("  fetch error: %s", exc)
        return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=Path("disqualified_verification_queue.json"))
    p.add_argument("--out", type=Path, default=Path("disqualified_deep_verification.json"))
    p.add_argument("--top-n", type=int, default=50)
    p.add_argument("--min-interval", type=float, default=1.0)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    data = json.loads(args.input.read_text(encoding="utf-8"))
    queue = data["queue"][: args.top_n]
    log.info("deep-verifying top %d candidates", len(queue))

    out_rows: list[dict] = []
    with httpx.Client(headers={"User-Agent": _UA}, follow_redirects=True) as client:
        last = 0.0
        for i, row in enumerate(queue, start=1):
            log.info("[%d/%d] candidate", i, len(queue))

            # CH side
            ch_url = row.get("disq_source_url")
            ch: dict = {}
            if ch_url:
                elapsed = time.monotonic() - last
                if elapsed < args.min_interval:
                    time.sleep(args.min_interval - elapsed)
                last = time.monotonic()
                html = _fetch(client, ch_url)
                if html:
                    ch = _extract_ch_disq_deep(_strip(html))

            # ICIJ side — first record only
            icij = row.get("icij_records") or []
            icij_extracted: dict = {}
            if icij:
                ic_url = icij[0].get("icij_url")
                if ic_url:
                    elapsed = time.monotonic() - last
                    if elapsed < args.min_interval:
                        time.sleep(args.min_interval - elapsed)
                    last = time.monotonic()
                    html = _fetch(client, ic_url)
                    if html:
                        icij_extracted = _extract_icij_deep(_strip(html))

            out_rows.append(
                {
                    "name": row.get("disq_canonical_name"),
                    "queue_score": row.get("score"),
                    "queue_dob": row.get("disq_birth_date"),
                    "queue_nationality": row.get("disq_nationality"),
                    "queue_address": row.get("disq_addresses"),
                    "ch_source_url": ch_url,
                    "ch_extracted": ch,
                    "icij_records": icij,
                    "icij_extracted": icij_extracted,
                }
            )

    args.out.write_text(
        json.dumps({"n": len(out_rows), "rows": out_rows}, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
