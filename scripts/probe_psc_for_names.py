"""Railway-side substring probe for UK PSC entities + persons.

Investigative drill-down: given one or more name needles
(case-insensitive substring), scan the OO UK PSC parquets via
``pl.scan_parquet`` with filter pushdown so the laptop never needs
to download the 1.5 GB corpus.

Outputs a small JSON to /data/processed/probes/<slug>.json with:

    {
        "needles": ["angermayer", "apeiron", "werner", ...],
        "entities": [<row dict>, ...],          // PSC entities matching any needle
        "persons":  [<row dict>, ...],          // PSC persons matching any needle
        "entity_relationships": [...],           // edges where either endpoint matches
    }

Used by the Apeiron / Angermayer investigation. Generalised so the
next bridge candidate can reuse the same probe with new needles.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_psc_for_names")

_DEFAULT_ENTITIES = Path("/data/processed/oo_uk_psc_entities.parquet")
_DEFAULT_PERSONS = Path("/data/processed/oo_uk_psc_persons.parquet")
_DEFAULT_RELATIONSHIPS = Path("/data/processed/oo_uk_psc_relationships.parquet")


def _ci_substring_match(col: str, needles: list[str]) -> pl.Expr:
    """One polars expression matching any of the needles via
    case-insensitive substring."""
    if not needles:
        return pl.lit(False)
    expr = pl.col(col).fill_null("").str.contains(f"(?i){needles[0]}")
    for n in needles[1:]:
        expr = expr | pl.col(col).fill_null("").str.contains(f"(?i){n}")
    return expr


def probe(
    needles: list[str],
    *,
    entities_path: Path = _DEFAULT_ENTITIES,
    persons_path: Path = _DEFAULT_PERSONS,
    relationships_path: Path = _DEFAULT_RELATIONSHIPS,
    sample_cap: int = 200,
) -> dict:
    """Scan PSC entities/persons/relationships for any rows whose
    name matches any needle. Cap each list at ``sample_cap`` for the
    JSON output."""

    log.info("probing UK PSC for needles=%s", needles)

    entities = (
        pl.scan_parquet(entities_path)
        .filter(_ci_substring_match("name", needles))
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
    log.info("entities match: %d rows", entities.height)

    persons = (
        pl.scan_parquet(persons_path)
        .filter(_ci_substring_match("name", needles))
        .select(
            "name",
            "given_name",
            "family_name",
            "nationality",
            "birth_date",
            "entity_uid",
            "source_label",
        )
        .collect()
    )
    log.info("persons match: %d rows", persons.height)

    # Pull relationships where either endpoint references a matched entity.
    matched_uids = set(entities["entity_uid"].to_list()) | set(persons["entity_uid"].to_list())
    log.info("collected %d matched entity_uids", len(matched_uids))

    if matched_uids:
        uid_list = list(matched_uids)
        rels = (
            pl.scan_parquet(relationships_path)
            .filter(pl.col("src_node").is_in(uid_list) | pl.col("dst_node").is_in(uid_list))
            .select(
                "src_node", "dst_node", "kind_raw", "role", "start_date", "end_date", "source_label"
            )
            .collect()
        )
        log.info("relationships match: %d rows", rels.height)
    else:
        rels = pl.DataFrame()

    return {
        "needles": needles,
        "entities": entities.head(sample_cap).to_dicts(),
        "entities_total": int(entities.height),
        "persons": persons.head(sample_cap).to_dicts(),
        "persons_total": int(persons.height),
        "entity_relationships": rels.head(sample_cap).to_dicts() if rels.height else [],
        "relationships_total": int(rels.height) if rels.height else 0,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--needle",
        action="append",
        default=[],
        required=True,
        help="Case-insensitive substring to search for. Repeatable.",
    )
    p.add_argument("--slug", required=True, help="Filename-safe slug for the output JSON.")
    p.add_argument("--out-dir", type=Path, default=Path("/data/processed/probes"))
    p.add_argument("--entities", type=Path, default=_DEFAULT_ENTITIES)
    p.add_argument("--persons", type=Path, default=_DEFAULT_PERSONS)
    p.add_argument("--relationships", type=Path, default=_DEFAULT_RELATIONSHIPS)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result = probe(
        args.needle,
        entities_path=args.entities,
        persons_path=args.persons,
        relationships_path=args.relationships,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"{args.slug}.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log.info("wrote %s", out_path)
    log.info(
        "summary: entities=%d/%d, persons=%d/%d, relationships=%d/%d",
        len(result["entities"]),
        result["entities_total"],
        len(result["persons"]),
        result["persons_total"],
        len(result["entity_relationships"]),
        result["relationships_total"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
