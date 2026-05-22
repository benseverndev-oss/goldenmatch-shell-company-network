"""Drill into the FENLAND / Fenech (Malta) thread.

FENLAND LIMITED is the largest single non-compliant owner in our
ROE anti-join: 313 UK property titles held by an Isle of Man /
Malta-registered entity with no UK CH OE filing. It appears in
both the Panama Papers (as "FENLAND INC.") and the Paradise Papers
(as "FENLAND LIMITED", Malta). The Paradise Papers record names
LILIAN FENECH and LAWRENCE FENECH as officers.

This probe:

  1. Pulls every FENLAND-named title from OCOD with full address
     + acquisition date + title number.
  2. Joins to country-incorporated + proprietor variants.
  3. Pulls every ICIJ record matching the FENLAND name (entity
     and officer side) plus their connected nodes.
  4. Produces a single per-thread JSON the case-study writeup
     can quote directly.

Output: ``/data/processed/probes/fenland_deepdive.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_fenland_deepdive")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/fenland_deepdive.json"),
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    ocod = pl.read_parquet(_OCOD)
    name_col = next(
        c for c in ("proprietor_name", "normalized_name", "proprietor", "name") if c in ocod.columns
    )
    log.info("OCOD rows: %d, name col: %s", ocod.height, name_col)

    # Find all FENLAND-named rows (case-insensitive)
    fenland = ocod.filter(pl.col(name_col).str.to_lowercase().str.contains("fenland"))
    log.info("FENLAND OCOD rows: %d", fenland.height)
    log.info("  distinct exact names: %s", fenland[name_col].unique().to_list())

    # Postcode concentration
    pc_col = next(
        (c for c in ("postcode", "property_postcode", "postal_code") if c in ocod.columns), None
    )
    geo = []
    if pc_col:
        geo = (
            fenland.with_columns(
                pl.col(pc_col).fill_null("").str.head(4).str.strip_chars().alias("pc_out")
            )
            .group_by("pc_out")
            .len()
            .sort("len", descending=True)
            .head(20)
            .to_dicts()
        )

    # Country incorporated
    country = None
    if "country_incorporated" in ocod.columns:
        country = (
            fenland.group_by("country_incorporated").len().sort("len", descending=True).to_dicts()
        )

    # ICIJ side
    icij_e = pl.read_parquet(_ICIJ_ENTITIES)
    icij_e_hits = icij_e.filter(pl.col("name").str.to_lowercase().str.contains("fenland"))
    log.info("ICIJ entities with 'fenland' in name: %d", icij_e_hits.height)

    icij_o = pl.read_parquet(_ICIJ_OFFICERS)
    icij_o_hits = icij_o.filter(pl.col("name").str.to_lowercase().str.contains("fenech"))
    log.info("ICIJ officers with 'fenech' in name: %d", icij_o_hits.height)

    # Walk edges out from FENLAND entities
    edges = pl.read_parquet(_ICIJ_EDGES)
    fenland_uids = ["icij:" + s for s in icij_e_hits["source_id"].to_list()]
    in_edges = edges.filter(pl.col("dst_node").is_in(fenland_uids))
    out_edges = edges.filter(pl.col("src_node").is_in(fenland_uids))
    log.info("inbound edges: %d, outbound: %d", in_edges.height, out_edges.height)

    # Compose detailed per-title view (a sample of 50 properties)
    title_rows = fenland.head(50).to_dicts()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "fenland_ocod_titles": int(fenland.height),
                    "icij_fenland_entities": int(icij_e_hits.height),
                    "icij_fenech_officers": int(icij_o_hits.height),
                    "icij_inbound_edges": int(in_edges.height),
                    "icij_outbound_edges": int(out_edges.height),
                },
                "ocod_distinct_proprietors": fenland[name_col].unique().to_list(),
                "ocod_country_breakdown": country,
                "ocod_postcode_concentration": geo,
                "ocod_sample_titles": title_rows,
                "icij_fenland_entities": icij_e_hits.to_dicts(),
                "icij_fenech_officers": icij_o_hits.to_dicts(),
                "icij_inbound_edge_sample": in_edges.head(40).to_dicts(),
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
