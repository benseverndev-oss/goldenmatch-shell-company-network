"""Railway-side probe: pull the named PSCs of a specific UK PSC
company UID.

Companion to scripts/probe_psc_for_names.py. Where that script
substring-matches names, this one looks up by entity_uid so we can
ask "for company X, who are all its declared PSCs and what are their
names?" without scanning the whole corpus.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_psc_by_uid")


def probe(
    entity_uids: list[str],
    *,
    persons_path: Path = Path("/data/processed/oo_uk_psc_persons.parquet"),
    entities_path: Path = Path("/data/processed/oo_uk_psc_entities.parquet"),
    relationships_path: Path = Path("/data/processed/oo_uk_psc_relationships.parquet"),
) -> dict:
    log.info("probing PSC for entity_uids=%s", entity_uids)

    # All relationships where the company is the dst_node (PSC ->
    # controlled-by-company edges)
    rels = (
        pl.scan_parquet(relationships_path).filter(pl.col("dst_node").is_in(entity_uids)).collect()
    )
    log.info("relationships pointing at our entities: %d", rels.height)

    src_uids = sorted(set(rels["src_node"].to_list()))
    log.info("distinct PSC src_node UIDs: %d", len(src_uids))

    # Look up each source UID in BOTH persons and entities tables (the
    # PSC may be a natural person OR a corporate entity)
    persons = (
        pl.scan_parquet(persons_path)
        .filter(pl.col("entity_uid").is_in(src_uids))
        .select(
            "entity_uid",
            "name",
            "given_name",
            "family_name",
            "nationality",
            "birth_date",
            "source_label",
        )
        .collect()
    )
    entities = (
        pl.scan_parquet(entities_path)
        .filter(pl.col("entity_uid").is_in(src_uids))
        .select(
            "entity_uid",
            "name",
            "jurisdiction",
            "incorporation_date",
            "dissolution_date",
            "source_label",
        )
        .collect()
    )

    return {
        "asked_for": entity_uids,
        "relationships": rels.to_dicts(),
        "psc_persons": persons.to_dicts(),
        "psc_entities": entities.to_dicts(),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--uid", action="append", required=True, help="entity_uid to look up. Repeatable."
    )
    p.add_argument("--slug", required=True)
    p.add_argument("--out-dir", type=Path, default=Path("/data/processed/probes"))
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result = probe(args.uid)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"{args.slug}.json"
    out_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s", out_path)
    log.info(
        "summary: %d relationships, %d psc_persons, %d psc_entities",
        len(result["relationships"]),
        len(result["psc_persons"]),
        len(result["psc_entities"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
