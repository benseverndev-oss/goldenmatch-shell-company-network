"""Expand the Gulbenkian-dynasty ICIJ network.

The 128 Ebury Street probe surfaced 'MICAEL PAUL SARKIS GULBENKIAN'
as officer of three Malta-incorporated entities (GULBENKIAN FINANCE
LIMITED, Panhold Limited, MPSG SERVICES LIMITED). The middle name
'Sarkis' matches the dynasty patronymic from founder Calouste
Sarkis Gulbenkian (1869-1955). This probe expands the network.

For each Gulbenkian-surnamed officer:
  1. Every entity they control in ICIJ.
  2. Every co-officer at those entities.
  3. Cross-reference each entity name against HMLR OCOD.
  4. Cross-reference each entity name against ICIJ wide search to
     catch related vehicles in the dynasty's structure.

Output: ``/data/processed/probes/gulbenkian_network.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_gulbenkian_network")


def _norm(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out", type=Path, default=Path("/data/processed/probes/gulbenkian_network.json")
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    log.info("loading source tables...")
    icij_entities = (
        pl.scan_parquet(Path("/data/interim/icij_entities.parquet"))
        .with_columns(_norm("name").alias("entity_normalized"))
        .collect()
    )
    icij_officers = pl.read_parquet(Path("/data/interim/icij_officers.parquet"))
    icij_edges = pl.read_parquet(Path("/data/interim/icij_edges.parquet"))
    ocod = pl.read_parquet(Path("/data/processed/hmlr_ocod.parquet"))

    # 1. Wide Gulbenkian scan — officers + entities with the surname
    log.info("=== wide Gulbenkian surname scan ===")
    gul_officers = icij_officers.filter(
        pl.col("normalized_name").str.contains("(?i)gulbenkian|guilbenkian")
    )
    log.info("  officers matching gulbenkian: %d", gul_officers.height)
    gul_entities_by_name = icij_entities.filter(
        pl.col("entity_normalized").str.contains("(?i)gulbenkian|guilbenkian")
    )
    log.info("  entities with 'gulbenkian' in name: %d", gul_entities_by_name.height)

    # 2. Per-officer expansion — every entity each Gulbenkian-named officer
    #    is an officer of, plus co-officers
    by_officer = []
    all_controlled_uids: set[str] = set()
    edges_by_src: dict[str, list[dict]] = {}
    gul_officer_uids = ["icij:" + s for s in gul_officers["source_id"].to_list()]
    if gul_officer_uids:
        out_edges = icij_edges.filter(pl.col("src_node").is_in(gul_officer_uids))
        for r in out_edges.iter_rows(named=True):
            edges_by_src.setdefault(r["src_node"], []).append(r)
        all_controlled_uids = {
            r["dst_node"].replace("icij:", "") for r in out_edges.iter_rows(named=True)
        }

    controlled = icij_entities.filter(pl.col("source_id").is_in(list(all_controlled_uids)))
    ent_by_uid = {e["source_id"]: e for e in controlled.iter_rows(named=True)}

    for o in gul_officers.iter_rows(named=True):
        uid = "icij:" + o["source_id"]
        ents = []
        for r in edges_by_src.get(uid, []):
            e = ent_by_uid.get(r["dst_node"].replace("icij:", ""), {})
            ents.append(
                {
                    "kind": r["kind_raw"],
                    "entity_source_id": e.get("source_id"),
                    "entity_name": e.get("name"),
                    "entity_jurisdiction": e.get("jurisdiction"),
                    "entity_incorporation": e.get("incorporation_date"),
                    "entity_status": e.get("status"),
                }
            )
        by_officer.append(
            {
                "officer_name": o["name"],
                "officer_normalized": o["normalized_name"],
                "officer_country": o.get("country"),
                "officer_source": o.get("source_id_label"),
                "controlled_entities": ents,
            }
        )

    # 3. Co-officers at the Gulbenkian-controlled entities
    controlled_node_uids = ["icij:" + s for s in controlled["source_id"].to_list()]
    co_off_uids: list[str] = []
    if controlled_node_uids:
        co_edges = icij_edges.filter(
            pl.col("dst_node").is_in(controlled_node_uids) & (pl.col("kind_raw") == "officer_of")
        )
        co_off_uids = sorted(
            {
                e["src_node"].replace("icij:", "")
                for e in co_edges.iter_rows(named=True)
                if e["src_node"] not in gul_officer_uids
            }
        )
    co_officers = icij_officers.filter(pl.col("source_id").is_in(co_off_uids))
    log.info("co-officers at Gulbenkian-controlled entities: %d", co_officers.height)

    # 4. UK property cross-reference for the controlled entities + the
    #    surname-named entities
    controlled_names = controlled.with_columns(_norm("name").alias("_nn"))["_nn"].to_list()
    surname_names = gul_entities_by_name["entity_normalized"].to_list()
    all_names = sorted(set(controlled_names + surname_names))
    ocod_hits = ocod.filter(pl.col("normalized_name").is_in(all_names))
    log.info("OCOD property holdings owned by Gulbenkian network entities: %d", ocod_hits.height)

    result = {
        "officers_count": int(gul_officers.height),
        "entities_with_surname_count": int(gul_entities_by_name.height),
        "controlled_entities_count": int(controlled.height),
        "co_officers_count": int(co_officers.height),
        "ocod_property_holdings_count": int(ocod_hits.height),
        "officers": gul_officers.to_dicts(),
        "entities_with_surname": gul_entities_by_name.to_dicts(),
        "by_officer": by_officer,
        "co_officers": co_officers.head(50).to_dicts(),
        "ocod_property_holdings": ocod_hits.head(50).to_dicts(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
