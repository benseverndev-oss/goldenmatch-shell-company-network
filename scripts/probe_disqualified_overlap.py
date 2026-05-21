"""Railway-side probe: cross-reference UK disqualified directors
against UK PSC persons (by name + DOB) and ICIJ Paradise Papers
officers (by name only).

The UK Insolvency Service maintains a register of people legally
banned from being a company director — usually for fraud, insolvency
violations, or breach of fiduciary duty. Acting as a PSC of a UK
company while disqualified is a Companies Act offence; appearing as
an officer of an offshore entity is not illegal under UK law but is
publishable public-interest information.

Two probes:

* ``disqualified_vs_uk_psc.json`` — strong identity matches on
  (normalized_name, birth_date_year_month). UK PSC persons have a
  birth_date in YYYY-MM format; disqualified records have a
  date_of_birth that we trim to the same precision. A match
  establishes identity beyond reasonable doubt.

* ``disqualified_vs_icij.json`` — weaker name-equality matches against
  ICIJ Paradise Papers officers. ICIJ officers lack DOB so this is
  candidate-grade, not identity-grade.

For each match we also surface the disqualified person's
company_name / address / disqualification_length / conduct so the
reviewer has full context.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_disqualified_overlap")

_DISQ = Path("/data/interim/uk_disqualified_directors.parquet")
_PSC_PERSONS = Path("/data/processed/oo_uk_psc_persons.parquet")
_PSC_RELS = Path("/data/processed/oo_uk_psc_relationships.parquet")
_PSC_ENTITIES = Path("/data/processed/oo_uk_psc_entities.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")


def _trim_dob_to_year_month(dob: str | None) -> str | None:
    """Disqualified DOB is e.g. ``05 / 04 / 1965`` (dd/mm/yyyy with
    spaces). UK PSC birth_date is ``YYYY-MM``. Reduce both to YYYY-MM
    so they can be joined."""
    if not dob:
        return None
    dob = dob.strip()
    # 05 / 04 / 1965 -> 1965-04
    m = re.match(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", dob)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}"
    # 1965-04-05 -> 1965-04
    m = re.match(r"(\d{4})-(\d{1,2})", dob)
    if m:
        y, mo = m.groups()
        return f"{y}-{int(mo):02d}"
    # 1965-04 already
    if re.match(r"^\d{4}-\d{2}$", dob):
        return dob
    return None


def probe_uk_psc_overlap() -> dict:
    log.info("loading disqualified register + UK PSC persons...")
    disq = pl.read_parquet(_DISQ)
    log.info("  %d disqualified directors", disq.height)
    # Trim disqualified DOB to YYYY-MM via map_elements (one-off, 222 rows)
    disq = disq.with_columns(
        pl.col("date_of_birth")
        .map_elements(_trim_dob_to_year_month, return_dtype=pl.String)
        .alias("dob_ym")
    ).filter(pl.col("dob_ym").is_not_null())
    log.info("  %d disqualified directors with parseable DOB", disq.height)

    if disq.is_empty():
        return {"matches": [], "matches_total": 0, "n_disqualified": 0}

    # Build the join keys
    disq_keys = disq.select(
        pl.col("normalized_person_name").alias("normalized"),
        pl.col("dob_ym").alias("birth_date"),
    ).unique()
    log.info("  %d unique (name, dob_ym) keys", disq_keys.height)

    psc = (
        pl.scan_parquet(_PSC_PERSONS)
        .filter(pl.col("birth_date").is_not_null() & pl.col("name").is_not_null())
        .select("entity_uid", "name", "given_name", "family_name", "nationality", "birth_date")
        .with_columns(
            pl.col("name")
            .str.to_lowercase()
            .str.replace_all(r"[^a-z0-9]+", " ")
            .str.replace_all(r"\s+", " ")
            .str.strip_chars()
            .alias("normalized")
        )
        .collect()
    )
    log.info("  %d UK PSC persons with name + DOB", psc.height)

    matched = psc.join(disq_keys, on=["normalized", "birth_date"], how="inner")
    log.info("  %d matched PSC persons by (normalized_name, birth_date_ym)", matched.height)

    if matched.is_empty():
        return {"matches": [], "matches_total": 0, "n_disqualified": int(disq.height)}

    # For each matched person, find their controlled UK companies via
    # relationships (psc_controller_of edges).
    matched_uids = matched["entity_uid"].to_list()
    rels = (
        pl.scan_parquet(_PSC_RELS)
        .filter(pl.col("src_node").is_in(matched_uids))
        .select("src_node", "dst_node", "kind_raw", "start_date", "end_date")
        .collect()
    )
    log.info("  %d controlled-company edges from matched persons", rels.height)

    controlled_uids = rels["dst_node"].unique().to_list()
    companies = (
        pl.scan_parquet(_PSC_ENTITIES)
        .filter(pl.col("entity_uid").is_in(controlled_uids))
        .select("entity_uid", "name", "jurisdiction", "incorporation_date", "dissolution_date")
        .collect()
    )

    # Build the final per-match record
    matches = []
    disq_lookup = {
        (r["normalized_person_name"], r["dob_ym"]): r for r in disq.iter_rows(named=True)
    }
    rels_by_src = {}
    for r in rels.iter_rows(named=True):
        rels_by_src.setdefault(r["src_node"], []).append(r)
    co_lookup = {c["entity_uid"]: c for c in companies.iter_rows(named=True)}

    for m in matched.iter_rows(named=True):
        d = disq_lookup.get((m["normalized"], m["birth_date"]), {})
        cos = []
        for r in rels_by_src.get(m["entity_uid"], []):
            c = co_lookup.get(r["dst_node"], {})
            cos.append(
                {
                    "company_uid": r["dst_node"],
                    "company_name": c.get("name"),
                    "psc_start": r["start_date"],
                    "psc_end": r["end_date"],
                    "company_incorporation": c.get("incorporation_date"),
                    "company_dissolution": c.get("dissolution_date"),
                }
            )
        matches.append(
            {
                "matched_name": m["name"],
                "normalized_name": m["normalized"],
                "birth_date": m["birth_date"],
                "nationality": m.get("nationality"),
                "psc_entity_uid": m["entity_uid"],
                "disqualified_company_name": d.get("company_name"),
                "disqualified_address": d.get("address_raw"),
                "disqualification_starts": d.get("date_order_starts"),
                "disqualification_length": d.get("disqualification_length"),
                "conduct": d.get("conduct"),
                "current_psc_companies": cos,
            }
        )

    return {
        "n_disqualified": int(disq.height),
        "n_psc_persons_with_dob": int(psc.height),
        "matches_total": int(matched.height),
        "matches": matches[:100],
    }


def probe_icij_overlap() -> dict:
    log.info("loading disqualified register + ICIJ officers...")
    disq = pl.read_parquet(_DISQ)
    disq_names = (
        disq.filter(pl.col("normalized_person_name").is_not_null())
        .select("normalized_person_name")
        .to_series()
        .to_list()
    )
    log.info("  %d disqualified-name needles", len(disq_names))

    off = (
        pl.scan_parquet(_ICIJ_OFFICERS)
        .filter(pl.col("normalized_name").is_in(disq_names))
        .collect()
    )
    log.info("  %d ICIJ officers matching disqualified-name", off.height)

    if off.is_empty():
        return {"matches": [], "matches_total": 0}

    # For each matched ICIJ officer, find their connected entities via edges
    icij_off_uids = ["icij:" + s for s in off["source_id"].to_list()]
    edges = (
        pl.scan_parquet(_ICIJ_EDGES)
        .filter(pl.col("src_node").is_in(icij_off_uids))
        .select("src_node", "dst_node", "kind_raw")
        .collect()
    )

    connected_bare = sorted(
        {r["dst_node"].replace("icij:", "") for r in edges.iter_rows(named=True)}
    )
    ent = (
        pl.scan_parquet(_ICIJ_ENTITIES)
        .filter(pl.col("source_id").is_in(connected_bare))
        .select("source_id", "name", "jurisdiction", "source_label")
        .collect()
    )

    disq_lookup = {
        r["normalized_person_name"]: r
        for r in disq.iter_rows(named=True)
        if r.get("normalized_person_name")
    }
    ent_lookup = {e["source_id"]: e for e in ent.iter_rows(named=True)}
    edges_by_off = {}
    for r in edges.iter_rows(named=True):
        edges_by_off.setdefault(r["src_node"], []).append(r)

    matches = []
    for o in off.iter_rows(named=True):
        d = disq_lookup.get(o["normalized_name"], {})
        connections = []
        for r in edges_by_off.get("icij:" + o["source_id"], []):
            e = ent_lookup.get(r["dst_node"].replace("icij:", ""), {})
            connections.append(
                {
                    "kind": r["kind_raw"],
                    "linked_uid": r["dst_node"],
                    "linked_name": e.get("name"),
                    "linked_jurisdiction": e.get("jurisdiction"),
                    "linked_source_label": e.get("source_label"),
                }
            )
        matches.append(
            {
                "icij_officer_name": o["name"],
                "icij_officer_normalized": o["normalized_name"],
                "icij_officer_country": o.get("country"),
                "icij_source_label": o.get("source_id_label"),
                "disqualified_company_name": d.get("company_name"),
                "disqualified_address": d.get("address_raw"),
                "disqualification_starts": d.get("date_order_starts"),
                "disqualification_length": d.get("disqualification_length"),
                "icij_connections": connections,
            }
        )

    return {
        "n_disqualified": int(disq.height),
        "matches_total": int(off.height),
        "matches": matches[:100],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=Path("/data/processed/probes"))
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for slug, fn in [
        ("disqualified_vs_uk_psc", probe_uk_psc_overlap),
        ("disqualified_vs_icij", probe_icij_overlap),
    ]:
        log.info("=== %s ===", slug)
        result = fn()
        out_path = args.out_dir / f"{slug}.json"
        out_path.write_text(
            json.dumps(result, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        log.info("wrote %s; %d matches", out_path, result.get("matches_total", 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
