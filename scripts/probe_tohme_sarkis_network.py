"""Expand the Tohme + Sarkis family ICIJ network.

The 128 Ebury Street hub probe surfaced ~20 ICIJ officer records
named Tohme or Sarkis (across Panama Papers — UK, Saudi, and
unspecified countries). This probe pulls the network expansion:

  1. For each officer named Tohme or Sarkis, every entity they're
     an officer of in ICIJ.
  2. Every co-officer at those entities.
  3. Cross-check each controlled entity's name against HMLR OCOD
     to find any UK property they own.

Output: ``/data/processed/probes/tohme_sarkis_network.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_tohme_sarkis_network")


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
        "--out", type=Path, default=Path("/data/processed/probes/tohme_sarkis_network.json")
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
        .with_columns(_norm("name").alias("_norm"))
        .collect()
    )
    icij_officers = pl.read_parquet(Path("/data/interim/icij_officers.parquet"))
    icij_edges = pl.read_parquet(Path("/data/interim/icij_edges.parquet"))
    ocod = pl.read_parquet(Path("/data/processed/hmlr_ocod.parquet"))

    # All Tohme/Sarkis officers
    tohme_sarkis = icij_officers.filter(pl.col("normalized_name").str.contains("(?i)tohme|sarkis"))
    log.info("Tohme/Sarkis officers: %d", tohme_sarkis.height)

    ts_uids = ["icij:" + s for s in tohme_sarkis["source_id"].to_list()]

    # Every entity any Tohme/Sarkis is an officer of (outbound edges)
    out_edges = icij_edges.filter(pl.col("src_node").is_in(ts_uids))
    controlled_uids = sorted(
        {e["dst_node"].replace("icij:", "") for e in out_edges.iter_rows(named=True)}
    )
    controlled = icij_entities.filter(pl.col("source_id").is_in(controlled_uids))
    log.info("entities controlled by Tohme/Sarkis: %d", controlled.height)

    # Every co-officer at those entities
    controlled_uids_full = ["icij:" + s for s in controlled["source_id"].to_list()]
    co_edges = icij_edges.filter(
        pl.col("dst_node").is_in(controlled_uids_full) & (pl.col("kind_raw") == "officer_of")
    )
    co_off_uids = sorted(
        {
            e["src_node"].replace("icij:", "")
            for e in co_edges.iter_rows(named=True)
            if e["src_node"] not in ts_uids
        }
    )
    co_officers = icij_officers.filter(pl.col("source_id").is_in(co_off_uids))
    log.info("co-officers: %d", co_officers.height)

    # Cross-check controlled entity names against OCOD
    controlled_names = controlled["_norm"].to_list()
    ocod_hits = ocod.filter(pl.col("normalized_name").is_in(controlled_names))
    log.info(
        "OCOD property holdings owned by Tohme/Sarkis-controlled entities: %d", ocod_hits.height
    )

    # Per-officer breakdown — who controls what
    by_officer = []
    edges_by_src = {}
    for r in out_edges.iter_rows(named=True):
        edges_by_src.setdefault(r["src_node"], []).append(r)
    ent_by_uid = {e["source_id"]: e for e in controlled.iter_rows(named=True)}
    for o in tohme_sarkis.iter_rows(named=True):
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

    return _write(
        args.out,
        {
            "tohme_sarkis_officers_count": int(tohme_sarkis.height),
            "controlled_entities_count": int(controlled.height),
            "co_officers_count": int(co_officers.height),
            "ocod_property_holdings_count": int(ocod_hits.height),
            "by_officer": by_officer,
            "co_officers": co_officers.head(100).to_dicts(),
            "ocod_property_holdings": ocod_hits.head(100).to_dicts(),
        },
    )


def _write(out: Path, data: dict) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log.info("wrote %s", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
