"""Spot-check ROE compliance for a sample of OCOD foreign owners.

Under the 2022 UK Economic Crime (Transparency and Enforcement) Act,
every overseas-incorporated company that owns UK property since
Feb 2022 must register on the UK Companies House Register of
Overseas Entities and disclose beneficial ownership. Failure is a
**criminal offence** under s.34 + s.42, with restrictions on the
property's disposability.

A full anti-join requires UK CH bulk data ingestion. This script
does a cheap *spot-check*: sample N random foreign-owner companies
from OCOD, search UK CH for an OE-prefixed entity matching the
name. If no OE record found = the company is potentially
non-compliant.

Input: ``ebury_128_hub.json`` and/or ``ocod_address_hubs.json``
to source the proprietor names, OR a fallback to whatever OCOD
file is locally available. We just need a list of foreign-owner
company names.

Polite 1 req/s. Sampling 300 names = ~5 min.

Output: ``ch_roe_compliance_spotcheck.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger("scrape_ch_roe_compliance")

_UA = "GoldenMatch case study bsevern@mjhlifesciences.com"
_CH_SEARCH = "https://find-and-update.company-information.service.gov.uk/search/companies?q={q}"


def _extract_oe(html: str) -> list[str]:
    return sorted(set(re.findall(r"\b(OE\d{6,})\b", html)))


def _fetch(client: httpx.Client, url: str) -> str | None:
    try:
        r = client.get(url, timeout=30.0)
        if r.status_code == 200:
            return r.text
    except Exception as exc:  # noqa: BLE001
        log.warning("  fetch error: %s", exc)
    return None


def _load_proprietor_names_from_hub_json(path: Path) -> list[str]:
    """Best-effort: extract foreign-owner company names from any of our
    locally-cached probe outputs."""

    data = json.loads(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    # ebury_128_hub.json shape
    rows = data.get("ocod_at_128_ebury", {}).get("rows", [])
    for r in rows:
        nm = (r.get("proprietor_name") or "").strip()
        if nm:
            names.add(nm)
    # hub_deepdive.json shape
    for hub in data.get("hubs", []) or []:
        for t in hub.get("sample_titles", []):
            nm = (t.get("proprietor") or "").strip()
            if nm:
                names.add(nm)
    return sorted(names)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input",
        type=Path,
        default=Path("hub_deepdive.json"),
        help="Source JSON with proprietor names (hub_deepdive.json, ebury_128_hub.json, etc.)",
    )
    p.add_argument("--out", type=Path, default=Path("ch_roe_compliance_spotcheck.json"))
    p.add_argument("--sample-size", type=int, default=300)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-interval", type=float, default=1.0)
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    names = _load_proprietor_names_from_hub_json(args.input)
    log.info("loaded %d distinct proprietor names", len(names))
    rng = random.Random(args.seed)
    sample = rng.sample(names, min(args.sample_size, len(names)))
    log.info("sampling %d", len(sample))

    out_rows: list[dict] = []
    with httpx.Client(headers={"User-Agent": _UA}, follow_redirects=True) as client:
        last = 0.0
        for i, name in enumerate(sample, start=1):
            elapsed = time.monotonic() - last
            if elapsed < args.min_interval:
                time.sleep(args.min_interval - elapsed)
            last = time.monotonic()
            log.info("[%d/%d] candidate", i, len(sample))
            url = _CH_SEARCH.format(q=name.replace(" ", "+").replace(",", ""))
            html = _fetch(client, url) or ""
            oes = _extract_oe(html)
            out_rows.append(
                {
                    "name": name,
                    "n_oe_matches": len(oes),
                    "oe_codes": oes[:5],
                    "compliant": bool(oes),
                }
            )

    n_compliant = sum(1 for r in out_rows if r["compliant"])
    n_noncompliant = len(out_rows) - n_compliant
    args.out.write_text(
        json.dumps(
            {
                "n_sampled": len(out_rows),
                "n_compliant": n_compliant,
                "n_noncompliant": n_noncompliant,
                "noncompliance_rate": (n_noncompliant / len(out_rows)) if out_rows else 0,
                "rows": out_rows,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    log.info(
        "wrote %s — %d/%d (%.1f%%) appear non-compliant (no OE number on CH)",
        args.out,
        n_noncompliant,
        len(out_rows),
        100 * n_noncompliant / max(1, len(out_rows)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
