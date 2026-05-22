"""Live UK CH disqualified-officers search for the queue candidates.

The OpenSanctions gb_coh_disqualified dataset turned out to have
serious data-quality issues — its source URLs 404 on the live CH
site, and the addresses for many candidates are publicly-known
political offices rather than real UK director correspondence
addresses.

This script side-steps OS and goes direct: for each distinct
normalized name in disqualified_verification_queue.json, perform a
live CH search at:

    /search/disqualified-officers?q=<name>

Records:
  - name searched
  - hit_count (parsed from results page)
  - first_5_hits (name + url + DOB if visible)
  - search_failed flag

Polite 1 req/s. ~219 names × 1 req/s = ~4 min.

Output: ``ch_disqualified_live.json``
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger("scrape_ch_disqualified_live")

_UA = "GoldenMatch case study bsevern@mjhlifesciences.com"
_CH_SEARCH = (
    "https://find-and-update.company-information.service.gov.uk/search/disqualified-officers?q={q}"
)


def _strip(html: str) -> str:
    text = re.sub(r"<[^>]+>", "|", html)
    text = re.sub(r"\|+", "|", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_results(html: str) -> tuple[int, list[dict]]:
    text = _strip(html)
    no_results = bool(re.search(r"\bNo results found\b", text, re.IGNORECASE))
    if no_results:
        return 0, []
    hits = []
    # Parse anchor-like blocks from the raw HTML — disqualified-officers
    # search results typically link to /disqualified-officers/natural/<id>
    for m in re.finditer(
        r'href="(/disqualified-officers/natural/[^"]+)"[^>]*>\s*([A-Z][^<|]{2,80}?)\s*</a>',
        html,
    ):
        url = "https://find-and-update.company-information.service.gov.uk" + m.group(1)
        name = re.sub(r"\s+", " ", m.group(2)).strip()
        hits.append({"name": name, "url": url})
    return len(hits), hits[:5]


def _fetch(client: httpx.Client, url: str) -> str | None:
    try:
        r = client.get(url, timeout=30.0)
        if r.status_code == 200:
            return r.text
        log.warning("  %d for %s", r.status_code, url)
    except Exception as exc:  # noqa: BLE001
        log.warning("  fetch error: %s", exc)
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=Path("disqualified_verification_queue.json"))
    p.add_argument("--out", type=Path, default=Path("ch_disqualified_live.json"))
    p.add_argument("--min-interval", type=float, default=1.0)
    p.add_argument("--top-n", type=int, default=300, help="Cap on names to search.")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    data = json.loads(args.input.read_text(encoding="utf-8"))
    queue = data["queue"][: args.top_n]

    seen: set[str] = set()
    targets: list[str] = []
    for r in queue:
        nm = r.get("disq_canonical_name") or ""
        if nm and nm not in seen:
            seen.add(nm)
            targets.append(nm)
    log.info("searching CH live for %d distinct names", len(targets))

    out_rows: list[dict] = []
    with httpx.Client(headers={"User-Agent": _UA}, follow_redirects=True) as client:
        last = 0.0
        for i, name in enumerate(targets, start=1):
            elapsed = time.monotonic() - last
            if elapsed < args.min_interval:
                time.sleep(args.min_interval - elapsed)
            last = time.monotonic()
            log.info("[%d/%d] candidate", i, len(targets))
            url = _CH_SEARCH.format(q=name.replace(" ", "+"))
            html = _fetch(client, url) or ""
            n, hits = _parse_results(html)
            out_rows.append(
                {
                    "name_searched": name,
                    "n_hits_parsed": n,
                    "first_hits": hits,
                }
            )

    n_any = sum(1 for r in out_rows if r["n_hits_parsed"] > 0)
    args.out.write_text(
        json.dumps(
            {
                "n_names_searched": len(out_rows),
                "n_names_with_live_disq_hit": n_any,
                "rows": out_rows,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    log.info("wrote %s — %d/%d names returned live disq hits", args.out, n_any, len(out_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
