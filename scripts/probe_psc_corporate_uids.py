"""Railway-side probe: resolve corporate-PSC UIDs by scanning the
ingested PSC entities table for matching bods_subject substrings.

The standard probe (probe_psc_by_uid.py) looks up exact entity_uid
matches. For corporate PSC declarations the UID is sometimes a
synthetic ``oo:gb-coh-ent-<co>-<hash>`` that isn't keyed the same
way. This probe substring-matches against bods_subject so anything
mentioning the focal company number surfaces — including the
declared corporate PSCs.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_psc_corporate_uids")

_ENTITIES = Path("/data/processed/oo_uk_psc_entities.parquet")
_PERSONS = Path("/data/processed/oo_uk_psc_persons.parquet")


def probe(
    co_numbers: list[str],
    *,
    entities_path: Path = _ENTITIES,
    persons_path: Path = _PERSONS,
) -> dict:
    log.info("probing PSC tables for entries mentioning %s", co_numbers)

    # Build a regex that matches any of the company numbers
    pattern = "(?i)" + "|".join(co_numbers)

    ent = (
        pl.scan_parquet(entities_path)
        .filter(pl.col("bods_subject").str.contains(pattern))
        .select(
            "entity_uid",
            "bods_subject",
            "name",
            "entity_type",
            "jurisdiction",
            "incorporation_date",
            "statement_date",
            "source_label",
        )
        .collect()
    )
    log.info("entities matched: %d", ent.height)

    per = (
        pl.scan_parquet(persons_path)
        .filter(pl.col("entity_uid").str.contains(pattern))
        .select(
            "entity_uid",
            "name",
            "given_name",
            "family_name",
            "nationality",
            "birth_date",
            "person_type",
            "source_label",
        )
        .collect()
    )
    log.info("persons matched: %d", per.height)

    return {
        "asked_for": co_numbers,
        "entities": ent.to_dicts(),
        "persons": per.to_dicts(),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--co-number",
        action="append",
        required=True,
        help="UK Companies House number (or substring). Repeatable.",
    )
    p.add_argument("--slug", required=True)
    p.add_argument("--out-dir", type=Path, default=Path("/data/processed/probes"))
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result = probe(args.co_number)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"{args.slug}.json"
    out_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    log.info(
        "wrote %s; entities=%d persons=%d",
        out_path,
        len(result["entities"]),
        len(result["persons"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
