"""Ingest FinCEN enforcement actions into a parquet.

FinCEN publishes its public enforcement actions at
https://www.fincen.gov/news-room/enforcement-actions. The page lists
each action with: subject (institution / individual name), date, and
action type (consent order, assessment of civil money penalty, etc.).

This script scrapes the public index pages and writes one row per
action:

  date            (ISO date)
  subject         (institution / individual name)
  action_type     (e.g. "Assessment of Civil Money Penalty")
  url             (link to the FinCEN action page)
  fetched_at      (ISO timestamp)

Polite at 1 req/s. The index spans roughly 1 page per year x 25
years; the working set is in the low hundreds of rows.

The probe layer then cross-references the `subject` column against
ICIJ Offshore Leaks for any documented offshore links.
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import polars as pl

log = logging.getLogger("ingest_fincen_enforcement")


_FINCEN_INDEX = "https://www.fincen.gov/news-room/enforcement-actions"
_UA = "GoldenMatch case study bsevern@mjhlifesciences.com"


def _strip_html(html: str) -> str:
    text = re.sub(
        r"<script\b[^>]*>.*?<\s*/\s*script\s*>", " ", html, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(r"<style\b[^>]*>.*?<\s*/\s*style\s*>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "|", text)
    text = re.sub(r"&nbsp;|&amp;", " ", text)
    text = re.sub(r"\|+", "|", text)
    return text


def _parse_index(html: str) -> list[dict]:
    """Parse the FinCEN enforcement-actions index page.

    Each row in the table has columns: Date | Subject | Action Type
    | (link). We extract via a permissive regex over the stripped
    text; if FinCEN restructures the page this needs a refresh.
    """

    rows: list[dict] = []
    # Try a row-by-row scan in the stripped text. Each action card
    # has the pattern:
    #   <date> <subject> ... <action-type> ... href="/news-room/<slug>"
    # Match permissively.
    text = _strip_html(html)
    # Look for date patterns like "January 15, 2024" then the next
    # non-empty content as the subject.
    for m in re.finditer(
        r"(?P<date>(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})\|+(?P<subject>[^|]{3,300})\|+(?P<action>[^|]{3,200})",
        text,
    ):
        date_str = m.group("date").strip()
        subject = re.sub(r"\s+", " ", m.group("subject")).strip()
        action = re.sub(r"\s+", " ", m.group("action")).strip()
        # Filter out non-action rows that match the date regex by accident
        if "menu" in subject.lower() or "search" in subject.lower():
            continue
        try:
            d = datetime.strptime(date_str, "%B %d, %Y").date().isoformat()
        except ValueError:
            d = date_str
        rows.append(
            {
                "date": d,
                "subject": subject[:200],
                "action_type": action[:200],
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out", type=Path, default=Path("/data/processed/fincen_enforcement_actions.parquet")
    )
    p.add_argument("--max-pages", type=int, default=20, help="Maximum index pages to walk.")
    p.add_argument("--min-interval", type=float, default=1.0)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    with httpx.Client(headers={"User-Agent": _UA}, timeout=60.0, follow_redirects=True) as client:
        for page in range(args.max_pages):
            url = _FINCEN_INDEX if page == 0 else f"{_FINCEN_INDEX}?page={page}"
            log.info("fetching %s", url)
            r = client.get(url)
            if r.status_code != 200:
                log.warning("  status %d; stopping", r.status_code)
                break
            page_rows = _parse_index(r.text)
            log.info("  parsed %d rows", len(page_rows))
            if not page_rows:
                break
            all_rows.extend(page_rows)
            time.sleep(args.min_interval)

    if not all_rows:
        log.warning("no FinCEN actions parsed; index format may have changed")
        return 1

    # Dedupe on (date, subject)
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for r in all_rows:
        key = (r["date"], r["subject"])
        if key not in seen:
            seen.add(key)
            r["fetched_at"] = fetched_at
            deduped.append(r)

    df = pl.DataFrame(deduped)
    df = df.with_columns(
        pl.col("subject")
        .str.to_lowercase()
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .alias("normalized_subject")
    )
    df.write_parquet(args.out)
    log.info("wrote %d FinCEN enforcement actions -> %s", df.height, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
