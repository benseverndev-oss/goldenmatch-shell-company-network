"""Per-target deepdive for non-compliant entities that warrant attention.

Same shape as probe_fenland_deepdive but parameterised across a small
list of hard-coded targets. Each target gets:

  - All OCOD title rows whose proprietor name contains the pattern
    (full property address, postcode, price-paid, acquisition date,
    proprietor country + correspondence address)
  - Postcode-outward concentration
  - Country-of-incorporation breakdown
  - ICIJ entities + officers whose name contains the pattern
  - Inbound + outbound leak-graph edges around those entities

Targets:

  - "edokpolo" — family cluster behind EKO IRE LIMITED (BVI, Pandora)
  - "embassy development" — OS-flagged debarment+sanction (GB/JE)
  - "harmony ridge" — OS-flagged corp.offshore+sanction.linked (BVI)
  - "ledra trustee" — OS-flagged debarment+sanction (Cyprus trustee)

Output: ``/data/processed/probes/named_threads_deepdive.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_named_threads_deepdive")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")

_TARGETS = [
    {"key": "edokpolo", "ocod_pattern": "edokpolo|eko ire", "icij_pattern": "edokpolo|eko ire"},
    {
        "key": "embassy_development",
        "ocod_pattern": "embassy development",
        "icij_pattern": "embassy development",
    },
    {"key": "harmony_ridge", "ocod_pattern": "harmony ridge", "icij_pattern": "harmony ridge"},
    {"key": "ledra_trustee", "ocod_pattern": "ledra trustee", "icij_pattern": "ledra"},
]


def _drill_one(
    ocod: pl.DataFrame,
    name_col: str,
    pc_col: str | None,
    icij_e: pl.DataFrame,
    icij_o: pl.DataFrame,
    edges: pl.DataFrame,
    target: dict,
) -> dict:
    log.info("=== %s ===", target["key"])
    ocod_pat = target["ocod_pattern"]
    icij_pat = target["icij_pattern"]

    ocod_hits = ocod.filter(pl.col(name_col).str.to_lowercase().str.contains(ocod_pat))
    log.info("  OCOD hits: %d", ocod_hits.height)

    geo: list[dict] = []
    if pc_col and ocod_hits.height > 0:
        geo = (
            ocod_hits.with_columns(
                pl.col(pc_col).fill_null("").str.head(4).str.strip_chars().alias("pc_out")
            )
            .group_by("pc_out")
            .len()
            .sort("len", descending=True)
            .head(15)
            .to_dicts()
        )

    country = []
    if "country_incorporated" in ocod.columns and ocod_hits.height > 0:
        country = (
            ocod_hits.group_by("country_incorporated").len().sort("len", descending=True).to_dicts()
        )

    ent_hits = icij_e.filter(pl.col("name").str.to_lowercase().str.contains(icij_pat))
    log.info("  ICIJ entities: %d", ent_hits.height)
    off_hits = icij_o.filter(pl.col("name").str.to_lowercase().str.contains(icij_pat))
    log.info("  ICIJ officers: %d", off_hits.height)

    ent_uids = ["icij:" + s for s in ent_hits["source_id"].to_list()]
    in_edges = edges.filter(pl.col("dst_node").is_in(ent_uids)) if ent_uids else edges.head(0)
    out_edges = edges.filter(pl.col("src_node").is_in(ent_uids)) if ent_uids else edges.head(0)

    sample_titles = ocod_hits.head(30).to_dicts()

    return {
        "target_key": target["key"],
        "ocod_pattern": ocod_pat,
        "icij_pattern": icij_pat,
        "ocod_n_titles": int(ocod_hits.height),
        "ocod_distinct_proprietors": ocod_hits[name_col].unique().to_list()[:30],
        "ocod_country_breakdown": country,
        "ocod_postcode_concentration": geo,
        "ocod_sample_titles": sample_titles,
        "icij_entity_hits": ent_hits.head(20).to_dicts(),
        "icij_officer_hits": off_hits.head(40).to_dicts(),
        "icij_inbound_edges_sample": in_edges.head(40).to_dicts(),
        "icij_outbound_edges_sample": out_edges.head(20).to_dicts(),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/named_threads_deepdive.json"),
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    ocod = pl.read_parquet(_OCOD)
    name_col = next(
        c for c in ("proprietor_name", "normalized_name", "proprietor", "name") if c in ocod.columns
    )
    pc_col = next(
        (c for c in ("postcode", "property_postcode", "postal_code") if c in ocod.columns), None
    )
    icij_e = pl.read_parquet(_ICIJ_ENTITIES)
    icij_o = pl.read_parquet(_ICIJ_OFFICERS)
    edges = pl.read_parquet(_ICIJ_EDGES)

    results = [_drill_one(ocod, name_col, pc_col, icij_e, icij_o, edges, t) for t in _TARGETS]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"targets": results}, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
