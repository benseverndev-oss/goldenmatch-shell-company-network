"""Deep-dive: expand the Emanuela Barilla / Maya International Foundation
ICIJ network.

For each focal officer:
  1. Find their ICIJ officer record
  2. Every entity they're an officer of
  3. Every co-officer at those entities (the network reach)
  4. Whether any of those entities own UK property per OCOD

Outputs ``/data/processed/probes/barilla_network.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_barilla_network")

# Focal officer needles (case-insensitive substring on normalized_name)
_FOCAL_OFFICERS = (
    "emanuela barilla",
    "maya international foundation",
)

# Cast a wider Barilla net — any officer with 'barilla' surname,
# any entity with 'barilla' in the name. Helps surface other family
# members (Guido, Luca, Paolo, Pietro, etc.) if they appear in ICIJ.
_BARILLA_WIDE = "barilla"


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
    p.add_argument("--out", type=Path, default=Path("/data/processed/probes/barilla_network.json"))
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
    log.info(
        "  entities=%d officers=%d edges=%d ocod=%d",
        icij_entities.height,
        icij_officers.height,
        icij_edges.height,
        ocod.height,
    )

    # ---- 1. Wide Barilla scan ----
    log.info("=== wide barilla scan ===")
    barilla_officers = icij_officers.filter(pl.col("normalized_name").str.contains(_BARILLA_WIDE))
    log.info("  officers matching 'barilla': %d", barilla_officers.height)
    barilla_entities = icij_entities.filter(pl.col("entity_normalized").str.contains(_BARILLA_WIDE))
    log.info("  entities matching 'barilla': %d", barilla_entities.height)

    # ---- 2. Per-focal-officer expansion ----
    focal_results = {}
    for needle in _FOCAL_OFFICERS:
        log.info("--- focal: %s ---", needle)
        off = icij_officers.filter(pl.col("normalized_name").str.contains(needle))
        log.info("  officer rows: %d", off.height)
        if off.is_empty():
            focal_results[needle] = {
                "officer_rows": [],
                "controlled_entities": [],
                "co_officers": [],
                "uk_properties": [],
            }
            continue

        officer_uids = ["icij:" + s for s in off["source_id"].to_list()]
        # Entities they are officer/beneficiary/intermediary of (src side)
        outbound = icij_edges.filter(pl.col("src_node").is_in(officer_uids))
        controlled_uids = sorted(
            {r["dst_node"].replace("icij:", "") for r in outbound.iter_rows(named=True)}
        )
        controlled = icij_entities.filter(pl.col("source_id").is_in(controlled_uids))
        log.info("  controlled entities: %d", controlled.height)

        # Co-officers at those same entities
        controlled_node_uids = ["icij:" + s for s in controlled["source_id"].to_list()]
        co_edges = icij_edges.filter(
            pl.col("dst_node").is_in(controlled_node_uids) & (pl.col("kind_raw") == "officer_of")
        )
        co_officer_uids = sorted(
            {r["src_node"].replace("icij:", "") for r in co_edges.iter_rows(named=True)}
            - set(off["source_id"].to_list())
        )
        co_officers = icij_officers.filter(pl.col("source_id").is_in(co_officer_uids))
        log.info("  co-officers: %d", co_officers.height)

        # UK properties owned by any of these entities (name-match)
        controlled_names = controlled.with_columns(_norm("name").alias("normalized_name"))[
            "normalized_name"
        ].to_list()
        uk_property = (
            ocod.filter(pl.col("normalized_name").is_in(controlled_names))
            if controlled_names
            else pl.DataFrame()
        )
        log.info("  UK properties owned by network: %d", uk_property.height)

        focal_results[needle] = {
            "officer_rows": off.to_dicts(),
            "controlled_entities": controlled.to_dicts(),
            "co_officers": co_officers.head(50).to_dicts(),
            "uk_properties": uk_property.to_dicts(),
        }

    result = {
        "wide_barilla_scan": {
            "officers": barilla_officers.to_dicts(),
            "entities": barilla_entities.to_dicts(),
        },
        "focal": focal_results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
