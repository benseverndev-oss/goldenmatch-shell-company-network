"""Verify the Ledra-Metalloinvest link found in the named-threads expand.

The expand probe surfaced a Panama Papers entry where a Cyprus
"Ledra Services" nominee is officer-of-record for a BVI entity
named "METALLOINVEST HOLDINGS B.V.I) LIMITED" (with a typo in
the name). This probe answers:

  1. What does the ICIJ leak record ACTUALLY say about that BVI
     entity? Full fields: jurisdiction, registration date, full
     address, status_date, source_label, all officers and
     intermediaries connected to it, all addresses.

  2. Does OpenSanctions have a Metalloinvest entity in its
     sanctioned/PEP/crime-flagged set? With what topics +
     jurisdictions + listing dates?

  3. Does OpenSanctions name Alisher Usmanov (sanctioned Russian
     metals oligarch)? With what details?

  4. Does the ICIJ edge graph place the Metalloinvest BVI entity
     in proximity to any Usmanov-named officer or related
     entities?

Output: ``/data/processed/probes/metalloinvest_verify.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_metalloinvest_verify")

_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")
_ICIJ_ADDRESSES = Path("/data/interim/icij_addresses.parquet")
_OS_ENTITIES = Path("/data/interim/opensanctions_entities.parquet")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/metalloinvest_verify.json"),
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # ---------------- 1. ICIJ Metalloinvest entity records ----------------
    log.info("=== 1. ICIJ Metalloinvest entities ===")
    icij_e = pl.read_parquet(_ICIJ_ENTITIES)
    metal_ents = icij_e.filter(pl.col("name").str.to_lowercase().str.contains("metalloinvest"))
    log.info("  metalloinvest-named ICIJ entities: %d", metal_ents.height)
    metal_uids = ["icij:" + s for s in metal_ents["source_id"].to_list()]

    # ---------------- 2. ICIJ edges touching the metalloinvest entity ----------------
    log.info("=== 2. ICIJ edges around metalloinvest ===")
    edges = pl.read_parquet(_ICIJ_EDGES)
    in_edges = edges.filter(pl.col("dst_node").is_in(metal_uids)) if metal_uids else edges.head(0)
    out_edges = edges.filter(pl.col("src_node").is_in(metal_uids)) if metal_uids else edges.head(0)
    log.info("  inbound: %d, outbound: %d", in_edges.height, out_edges.height)

    # Look up connected officers + entities
    in_src_uids = sorted(
        {r["src_node"].replace("icij:", "") for r in in_edges.iter_rows(named=True)}
    )
    out_dst_uids = sorted(
        {r["dst_node"].replace("icij:", "") for r in out_edges.iter_rows(named=True)}
    )

    icij_o = pl.read_parquet(_ICIJ_OFFICERS)
    connected_officers = icij_o.filter(pl.col("source_id").is_in(in_src_uids))
    connected_entities = icij_e.filter(pl.col("source_id").is_in(in_src_uids + out_dst_uids))
    log.info(
        "  connected officers: %d, connected entities: %d",
        connected_officers.height,
        connected_entities.height,
    )

    # ---------------- 3. ICIJ Usmanov officer records ----------------
    log.info("=== 3. ICIJ Usmanov officer records ===")
    usmanov_offs = icij_o.filter(pl.col("name").str.to_lowercase().str.contains("usmanov"))
    log.info("  usmanov-named officers: %d", usmanov_offs.height)
    # Do any of these Usmanov officers appear in edges connected to metalloinvest?
    if usmanov_offs.height > 0 and metal_uids:
        usmanov_uids = ["icij:" + s for s in usmanov_offs["source_id"].to_list()]
        usmanov_metal_edges = edges.filter(
            pl.col("src_node").is_in(usmanov_uids) & pl.col("dst_node").is_in(metal_uids)
        )
        log.info("  usmanov-metalloinvest direct edges: %d", usmanov_metal_edges.height)
    else:
        usmanov_metal_edges = edges.head(0)

    # ---------------- 4. OS Metalloinvest + Usmanov records ----------------
    log.info("=== 4. OpenSanctions Metalloinvest + Usmanov ===")
    os_metal: list[dict] = []
    os_usmanov: list[dict] = []
    if _OS_ENTITIES.exists():
        try:
            os_metal_df = (
                pl.scan_parquet(_OS_ENTITIES)
                .filter(pl.col("name").str.to_lowercase().str.contains("metalloinvest"))
                .collect()
            )
            log.info("  OS metalloinvest entities: %d", os_metal_df.height)
            os_metal = os_metal_df.head(20).to_dicts()

            os_usmanov_df = (
                pl.scan_parquet(_OS_ENTITIES)
                .filter(pl.col("name").str.to_lowercase().str.contains("usmanov"))
                .collect()
            )
            log.info("  OS usmanov entities: %d", os_usmanov_df.height)
            os_usmanov = os_usmanov_df.head(20).to_dicts()
        except Exception as exc:  # noqa: BLE001
            log.warning("  OS load failed: %s", exc)
    else:
        log.warning("  OS file missing")

    # ---------------- 5. ICIJ addresses for the metalloinvest entity ----------------
    log.info("=== 5. ICIJ addresses around metalloinvest ===")
    addresses: list[dict] = []
    if _ICIJ_ADDRESSES.exists() and metal_uids:
        try:
            addr_df = pl.read_parquet(_ICIJ_ADDRESSES)
            # Find address edges (kind 'registered_address' etc.) for metalloinvest
            addr_edges = edges.filter(
                pl.col("src_node").is_in(metal_uids) & pl.col("kind_raw").str.contains("address")
            )
            addr_uids = sorted(
                {r["dst_node"].replace("icij:", "") for r in addr_edges.iter_rows(named=True)}
            )
            if addr_uids:
                addr_hits = addr_df.filter(pl.col("source_id").is_in(addr_uids))
                addresses = addr_hits.head(10).to_dicts()
                log.info("  addresses found: %d", len(addresses))
        except Exception as exc:  # noqa: BLE001
            log.warning("  address lookup failed: %s", exc)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "icij_metalloinvest_entities": int(metal_ents.height),
                    "icij_inbound_edges": int(in_edges.height),
                    "icij_outbound_edges": int(out_edges.height),
                    "icij_connected_officers": int(connected_officers.height),
                    "icij_connected_entities": int(connected_entities.height),
                    "icij_usmanov_officers": int(usmanov_offs.height),
                    "icij_usmanov_metalloinvest_direct_edges": int(usmanov_metal_edges.height),
                    "os_metalloinvest_entities": len(os_metal),
                    "os_usmanov_entities": len(os_usmanov),
                },
                "icij_metalloinvest_entities": metal_ents.to_dicts(),
                "icij_connected_officers": connected_officers.head(50).to_dicts(),
                "icij_connected_entities": connected_entities.head(50).to_dicts(),
                "icij_usmanov_officers": usmanov_offs.head(20).to_dicts(),
                "icij_usmanov_metalloinvest_direct_edges": usmanov_metal_edges.to_dicts(),
                "icij_addresses": addresses,
                "os_metalloinvest": os_metal,
                "os_usmanov": os_usmanov,
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
