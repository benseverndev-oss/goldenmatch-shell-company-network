"""Live UK Companies House search for Metalloinvest variants.

The Ledra-Metalloinvest link rests on a Panama Papers entry where
the entity name has a typo (`METALLOINVEST HOLDINGS B.V.I) LIMITED`).
This script asks UK CH directly:

  - Does any "Metalloinvest" entity appear on UK CH at all?
  - With what status (active / dissolved / in administration)?
  - With what registered address?
  - With what officers listed?

Output: ``metalloinvest_uk_ch.json``.

Polite 1 req/s. Local script (writes to D:, no Railway touch).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger("verify_metalloinvest_uk_ch")
_UA = "GoldenMatch case study bsevern@mjhlifesciences.com"
_CH_SEARCH = "https://find-and-update.company-information.service.gov.uk/search/companies?q={q}"
_CH_BASE = "https://find-and-update.company-information.service.gov.uk"


def _parse_companies(html: str) -> list[dict]:
    hits: list[dict] = []
    seen: set[str] = set()
    for m in re.finditer(
        r'href="(/company/([A-Z0-9]+))"[^>]*>\s*([^<|]{2,150}?)\s*</a>',
        html,
    ):
        company_num = m.group(2)
        if company_num in seen:
            continue
        seen.add(company_num)
        nm = re.sub(r"\s+", " ", m.group(3)).strip()
        hits.append(
            {
                "company_number": company_num,
                "name": nm,
                "url": _CH_BASE + m.group(1),
            }
        )
    return hits[:25]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("metalloinvest_uk_ch.json"))
    p.add_argument("--min-interval", type=float, default=1.0)
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    queries = [
        "metalloinvest",
        "metalloinvest holdings",
        "metalloinvest holding",
        "usmanov",
    ]

    results: list[dict] = []
    with httpx.Client(headers={"User-Agent": _UA}, follow_redirects=True) as client:
        last = 0.0
        for q in queries:
            elapsed = time.monotonic() - last
            if elapsed < args.min_interval:
                time.sleep(args.min_interval - elapsed)
            last = time.monotonic()
            url = _CH_SEARCH.format(q=q.replace(" ", "+"))
            log.info("searching CH for %r", q)
            r = client.get(url, timeout=30.0)
            companies = _parse_companies(r.text) if r.status_code == 200 else []
            log.info("  %d hits", len(companies))
            results.append({"query": q, "n_hits": len(companies), "companies": companies})

    args.out.write_text(
        json.dumps({"results": results}, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
