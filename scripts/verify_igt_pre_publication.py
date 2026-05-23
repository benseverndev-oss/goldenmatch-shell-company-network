"""Pre-publication verification checks for the IGT Intergestions hero example.

Executes the items in `hero_example_igt_intergestions.md` slide 8 that
can be done programmatically:

  - Live UK Companies House search across 11 entity-name variants
    + LEI + Liechtenstein company number, with results parsed and
    HTML saved per query.
  - Submit the key reference pages to the Wayback Machine
    (archive.org/save/) so the published claim has a stable snapshot.
  - Write a tidy local archive of:
      - the 5 OCOD title rows (from aar_igt_verify.json)
      - the OS canonical record (with all identifiers + datasets)
      - the live CH search results (parsed)
  - Try a best-effort OFAC SDN search via the public Treasury
    sanctionssearch.ofac.treas.gov endpoint.

Cannot do (genuinely manual):
  - Buy title registers from HM Land Registry (£3 per title × 5 = £15).
  - Pull the Liechtenstein commercial register via justizportal.li
    (paid lookup, German interface).
  - Run a planning-portal search at the London Borough of Camden.

Output:
  - igt_pre_publication_artefacts/ch_search_<variant>.html
  - igt_pre_publication_artefacts/ch_search_results.json
  - igt_pre_publication_artefacts/ocod_rows.json
  - igt_pre_publication_artefacts/os_record.json
  - igt_pre_publication_artefacts/wayback_submissions.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger("verify_igt_pre_publication")

_UA = "GoldenMatch case study bsevern@mjhlifesciences.com"
_CH_SEARCH = "https://find-and-update.company-information.service.gov.uk/search/companies?q={q}"
_CH_BASE = "https://find-and-update.company-information.service.gov.uk"
_WAYBACK_SAVE = "https://web.archive.org/save/{url}"
_OFAC_SEARCH = "https://sanctionssearch.ofac.treas.gov/Search.aspx"

_NAME_VARIANTS = [
    "IGT Intergestions Trust Reg",
    "IGT Intergestions Trust Reg.",
    "IGT Intergestions Trust",
    "IGT Intergestions",
    "Intergestions Trust Reg",
    "Intergestions",
    "IGT Intergestions Trust Reg AG",
    "IGT-Intergestions",
    "I.G.T. Intergestions Trust Reg",
    "FL00015130568",  # Liechtenstein company number
    "391200PWMHBZMLPKTA05",  # global LEI
]

_WAYBACK_TARGETS = [
    # OFAC SDN search (public — by name)
    "https://sanctionssearch.ofac.treas.gov/Search.aspx",
    # GLEIF LEI lookup
    "https://search.gleif.org/#/record/391200PWMHBZMLPKTA05",
    # OpenSanctions entity page
    "https://www.opensanctions.org/entities/NK-2FYHVi5239jTUiF4iMyFrj/",
    # UK CH register-of-overseas-entities information page
    "https://www.gov.uk/guidance/register-of-overseas-entities",
]


def _parse_ch_results(html: str) -> dict:
    """Extract company hits + total-count from a CH search results page."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    total_m = re.search(r"([0-9,]+)\s+results?\s+found", text, re.IGNORECASE)
    total = int(total_m.group(1).replace(",", "")) if total_m else None
    no_results = bool(re.search(r"\bNo results found\b", text, re.IGNORECASE))
    hits: list[dict] = []
    seen: set[str] = set()
    for m in re.finditer(
        r'href="(/company/([A-Z0-9]+))"[^>]*>\s*([^<|]{2,150}?)\s*</a>',
        html,
    ):
        num = m.group(2)
        if num in seen:
            continue
        seen.add(num)
        nm = re.sub(r"\s+", " ", m.group(3)).strip()
        hits.append({"company_number": num, "name": nm, "url": _CH_BASE + m.group(1)})
    return {
        "no_results_flag": no_results,
        "total_count": total,
        "hits": hits[:20],
    }


def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")[:80]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=Path("igt_pre_publication_artefacts"))
    p.add_argument("--min-interval", type=float, default=1.0)
    p.add_argument("--input", type=Path, default=Path("aar_igt_verify.json"))
    p.add_argument(
        "--no-wayback",
        action="store_true",
        help="Skip the Wayback Machine save submissions (slow).",
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(headers={"User-Agent": _UA}, follow_redirects=True) as client:
        last = 0.0

        # ---------------- 1. Live CH search across name variants ----------------
        log.info("=== 1. Live UK Companies House search ===")
        ch_results: list[dict] = []
        for variant in _NAME_VARIANTS:
            elapsed = time.monotonic() - last
            if elapsed < args.min_interval:
                time.sleep(args.min_interval - elapsed)
            last = time.monotonic()
            url = _CH_SEARCH.format(q=variant.replace(" ", "+"))
            log.info("  searching CH for %r", variant)
            try:
                r = client.get(url, timeout=30.0)
                if r.status_code != 200:
                    log.warning("    %d for %s", r.status_code, url)
                    ch_results.append(
                        {"variant": variant, "status_code": r.status_code, "url": url}
                    )
                    continue
            except Exception as exc:  # noqa: BLE001
                log.warning("    fetch error: %s", exc)
                ch_results.append({"variant": variant, "error": str(exc), "url": url})
                continue
            # Save raw HTML for archive
            html_path = args.out_dir / f"ch_search_{_slug(variant)}.html"
            html_path.write_text(r.text, encoding="utf-8")
            parsed = _parse_ch_results(r.text)
            parsed.update({"variant": variant, "url": url, "html_path": str(html_path)})
            ch_results.append(parsed)
            n_hits = len(parsed.get("hits") or [])
            log.info("    %d hits, no-results-flag=%s", n_hits, parsed.get("no_results_flag"))

        (args.out_dir / "ch_search_results.json").write_text(
            json.dumps({"variants": ch_results}, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )

        # ---------------- 2. Wayback Machine snapshots ----------------
        wayback_results: list[dict] = []
        if not args.no_wayback:
            log.info("=== 2. Wayback Machine save submissions ===")
            for target in _WAYBACK_TARGETS:
                elapsed = time.monotonic() - last
                if elapsed < args.min_interval:
                    time.sleep(args.min_interval - elapsed)
                last = time.monotonic()
                url = _WAYBACK_SAVE.format(url=target)
                log.info("  saving %s", target)
                try:
                    r = client.get(url, timeout=60.0)
                    wayback_results.append(
                        {
                            "target": target,
                            "submit_url": url,
                            "status_code": r.status_code,
                            "archive_url": (
                                r.headers.get("content-location")
                                or r.headers.get("location")
                                or None
                            ),
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    log.warning("    fetch error: %s", exc)
                    wayback_results.append({"target": target, "error": str(exc)})

            (args.out_dir / "wayback_submissions.json").write_text(
                json.dumps({"submissions": wayback_results}, indent=2, sort_keys=True, default=str),
                encoding="utf-8",
            )

        # ---------------- 3. Local archive of OCOD rows + OS record ----------------
        log.info("=== 3. Local archive of OCOD + OS records ===")
        if args.input.exists():
            src = json.loads(args.input.read_text(encoding="utf-8"))
            igt = next(t for t in src["targets"] if t["target_key"] == "igt_intergestions")
            (args.out_dir / "ocod_rows.json").write_text(
                json.dumps(
                    {
                        "snapshot_source": "aar_igt_verify.json (May 2026 OCOD)",
                        "n_titles": igt["ocod_n_titles"],
                        "distinct_proprietors": igt.get("ocod_distinct_proprietors"),
                        "titles": igt["ocod_titles"],
                    },
                    indent=2,
                    sort_keys=True,
                    default=str,
                ),
                encoding="utf-8",
            )
            os_record = next(
                (r for r in igt["os_hits"] if "intergestions" in (r.get("name") or "").lower()),
                None,
            )
            if os_record:
                (args.out_dir / "os_record.json").write_text(
                    json.dumps(os_record, indent=2, sort_keys=True, default=str),
                    encoding="utf-8",
                )
            log.info("  wrote ocod_rows.json + os_record.json")

        # ---------------- 4. Best-effort OFAC search ----------------
        log.info("=== 4. OFAC SDN search (best-effort) ===")
        try:
            r = client.get(_OFAC_SEARCH, timeout=30.0)
            (args.out_dir / "ofac_search_page.html").write_text(r.text, encoding="utf-8")
            log.info("  saved OFAC SDN search page (status %d)", r.status_code)
        except Exception as exc:  # noqa: BLE001
            log.warning("  OFAC fetch failed: %s", exc)

    log.info("done — wrote artefacts to %s", args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
