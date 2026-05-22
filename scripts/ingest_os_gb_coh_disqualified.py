"""Ingest the OpenSanctions ``gb_coh_disqualified`` dataset.

The UK Companies House disqualified-directors register, exposed by
OpenSanctions as a structured FtM dataset:

    https://www.opensanctions.org/datasets/gb_coh_disqualified/

This is much richer than the partial 222-row scrape we previously
had. The full register has ~3,000-5,000 active disqualifications
at any time, with structured fields per Person:

  - name + normalized name
  - aliases / weakAlias
  - DOB
  - nationality
  - addresses
  - topics (includes 'reg.disqual')
  - sourceUrl back to Companies House

Output: ``/data/processed/uk_coh_disqualified_full.parquet``.

The wrongdoing-track probe reads this parquet for name-matching
against ICIJ + OCOD + OFAC, with DOB/address available for
disambiguation.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import httpx
import polars as pl

log = logging.getLogger("ingest_os_gb_coh_disqualified")


_FTM_URL = "https://data.opensanctions.org/datasets/latest/gb_coh_disqualified/entities.ftm.json"
_UA = "GoldenMatch case study bsevern@mjhlifesciences.com"


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _first(lst: list | None) -> str | None:
    return lst[0] if lst else None


def _join(lst: list | None) -> str:
    return " | ".join(str(x) for x in lst) if lst else ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/uk_coh_disqualified_full.parquet"),
    )
    p.add_argument(
        "--raw",
        type=Path,
        default=Path("/data/raw/opensanctions/gb_coh_disqualified.ftm.json"),
    )
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.skip_download:
        args.raw.parent.mkdir(parents=True, exist_ok=True)
        log.info("downloading %s -> %s", _FTM_URL, args.raw)
        with httpx.stream(
            "GET", _FTM_URL, follow_redirects=True, headers={"User-Agent": _UA}, timeout=None
        ) as r:
            r.raise_for_status()
            total = 0
            with args.raw.open("wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
                    total += len(chunk)
            log.info("  wrote %d bytes", total)

    rows: list[dict] = []
    n_total = 0
    with args.raw.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_total += 1
            try:
                ent = json.loads(line)
            except json.JSONDecodeError:
                continue
            schema = ent.get("schema")
            if schema != "Person":
                continue
            props = ent.get("properties", {})
            name = _first(props.get("name"))
            if not name:
                continue
            rows.append(
                {
                    "os_id": ent.get("id"),
                    "name": name,
                    "normalized_name": _norm(name),
                    "first_name": _first(props.get("firstName")),
                    "last_name": _first(props.get("lastName")),
                    "alias": _join(props.get("alias")),
                    "weak_alias": _join(props.get("weakAlias")),
                    "birth_date": _first(props.get("birthDate")),
                    "nationality": _join(props.get("nationality")),
                    "addresses": _join(props.get("address")),
                    "topics": _join(props.get("topics")),
                    "source_url": _first(props.get("sourceUrl")),
                    "notes": _join(props.get("notes"))[:1000],
                }
            )
    log.info("FTM rows scanned: %d, Person rows kept: %d", n_total, len(rows))

    df = pl.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(args.out)
    log.info("wrote %d rows -> %s", df.height, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
