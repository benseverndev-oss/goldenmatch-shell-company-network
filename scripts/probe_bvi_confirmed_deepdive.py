"""Deep-dive case study on the three BVI-jurisdiction-confirmed
ICIJ ∩ OCOD bridge candidates.

For each candidate (SULGER ASSETS S.A, JAMERS INTERNATIONAL S.A,
CARDINAL INVESTMENT SERVICES S.A), pull:

1. The full ICIJ entity record (incorporation date, status, address)
2. Every ICIJ officer connected to the entity (directors, beneficial
   owners, intermediaries, registered agents)
3. Every ICIJ edge touching the entity, with the kind_raw role
4. Every other ICIJ entity those officers also serve (the network)
5. Every UK property the OCOD names this company as proprietor of,
   with property address + postcode + tenure + price paid + date
   proprietor added

Outputs ``/data/processed/probes/bvi_deepdive.json`` with one block
per candidate.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_bvi_confirmed_deepdive")

_CANDIDATES = (
    "sulger assets s a",
    "jamers international s a",
    "cardinal investment services s a",
)


def _norm(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


def deepdive_one(
    normalized_name: str,
    *,
    icij_entities: pl.DataFrame,
    icij_officers: pl.DataFrame,
    icij_edges: pl.DataFrame,
    ocod: pl.DataFrame,
) -> dict:
    log.info("=== %s ===", normalized_name)

    # ICIJ entities matching this name + BVI jurisdiction
    icij_match = icij_entities.filter(
        (pl.col("normalized_name") == normalized_name) & (pl.col("jurisdiction") == "vg")
    )
    log.info("  ICIJ entities (vg): %d", icij_match.height)

    icij_uids = ["icij:" + s for s in icij_match["source_id"].to_list()]

    # All edges touching this entity
    edges = icij_edges.filter(
        pl.col("src_node").is_in(icij_uids) | pl.col("dst_node").is_in(icij_uids)
    )
    log.info("  ICIJ edges: %d", edges.height)

    # All connected node UIDs (officers, addresses, intermediaries, other entities)
    connected = sorted(
        {n.replace("icij:", "") for n in edges["src_node"].to_list() + edges["dst_node"].to_list()}
        - set(s for s in icij_match["source_id"].to_list())
    )

    # Officers connected to it
    officers = icij_officers.filter(pl.col("source_id").is_in(connected))
    log.info("  connected officers: %d", officers.height)

    # Other entities the officers serve (the network reach)
    officer_uids = ["icij:" + s for s in officers["source_id"].to_list()]
    network_edges = icij_edges.filter(pl.col("src_node").is_in(officer_uids))
    sibling_entity_uids = sorted(
        {r["dst_node"].replace("icij:", "") for r in network_edges.iter_rows(named=True)}
        - set(s for s in icij_match["source_id"].to_list())
    )
    sibling_entities = icij_entities.filter(pl.col("source_id").is_in(sibling_entity_uids))
    log.info("  sibling entities (network reach): %d", sibling_entities.height)

    # UK property holdings
    properties = ocod.filter(pl.col("normalized_name") == normalized_name)
    log.info("  UK properties: %d", properties.height)

    return {
        "normalized_name": normalized_name,
        "icij_entities": icij_match.to_dicts(),
        "icij_edges": edges.to_dicts(),
        "icij_officers": officers.to_dicts(),
        "sibling_entities_count": int(sibling_entities.height),
        "sibling_entities": sibling_entities.head(50).to_dicts(),
        "uk_properties_count": int(properties.height),
        "uk_properties": properties.to_dicts(),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("/data/processed/probes/bvi_deepdive.json"))
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    log.info("loading source tables...")
    icij_entities = (
        pl.scan_parquet(Path("/data/interim/icij_entities.parquet"))
        .with_columns(_norm("name").alias("normalized_name"))
        .collect()
    )
    icij_officers = pl.read_parquet(Path("/data/interim/icij_officers.parquet"))
    icij_edges = pl.read_parquet(Path("/data/interim/icij_edges.parquet"))
    ocod = pl.read_parquet(Path("/data/processed/hmlr_ocod.parquet"))

    log.info(
        "  icij_entities=%d officers=%d edges=%d ocod=%d",
        icij_entities.height,
        icij_officers.height,
        icij_edges.height,
        ocod.height,
    )

    results = {}
    for name in _CANDIDATES:
        results[name] = deepdive_one(
            name,
            icij_entities=icij_entities,
            icij_officers=icij_officers,
            icij_edges=icij_edges,
            ocod=ocod,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(results, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
