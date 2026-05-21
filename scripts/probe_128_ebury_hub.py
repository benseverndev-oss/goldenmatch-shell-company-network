"""Systematic scan: every reference to 128 Ebury Street SW1W 9QQ
across ICIJ + HMLR OCOD.

The Belgravia address at 128 Ebury Street appears in ICIJ Panama
Papers as 'C/O Waterbridge Estates' (icij:14033543, with two named
PP officers using it as their registered correspondence point:
Youssef Tohme + Ramez Sarkis) AND in UK Companies House Register
of Overseas Entities as the correspondence address for multiple
declared beneficial owners of UK property held through Panama-
incorporated companies.

This probe surfaces the full address-centred subgraph:

1. Every OCOD title where the proprietor_address contains
   '128 Ebury Street' or 'SW1W 9QQ' — the UK properties.
2. Every ICIJ officer whose source_id maps to a record with
   address text matching 128 Ebury / Waterbridge Estates.
3. Every ICIJ entity those officers serve — the offshore network.
4. The two named PP officers Tohme + Sarkis expanded.

Output: ``/data/processed/probes/ebury_128_hub.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_128_ebury_hub")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("/data/processed/probes/ebury_128_hub.json"))
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    log.info("loading source tables...")
    icij_entities = pl.read_parquet(Path("/data/interim/icij_entities.parquet"))
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

    # --- 1. OCOD records where proprietor_address mentions 128 Ebury ---
    pat = "(?i)128 ebury|sw1w ?9qq|waterbridge estates"
    ocod_hits = ocod.filter(pl.col("proprietor_address").fill_null("").str.contains(pat))
    log.info("OCOD records with 128 Ebury proprietor_address: %d", ocod_hits.height)

    # --- 2. The ICIJ Ebury address node + its connected officers ---
    ebury_address_uid = "14033543"
    ebury_node = icij_entities.filter(pl.col("source_id") == ebury_address_uid)
    edges_to_ebury = icij_edges.filter(pl.col("dst_node") == "icij:" + ebury_address_uid)
    officers_at_ebury_uids = sorted(
        {e["src_node"].replace("icij:", "") for e in edges_to_ebury.iter_rows(named=True)}
    )
    officers_at_ebury = icij_officers.filter(pl.col("source_id").is_in(officers_at_ebury_uids))
    log.info("ICIJ officers using 128 Ebury as address: %d", officers_at_ebury.height)

    # --- 3. Network expansion from those officers (Tohme + Sarkis etc) ---
    officer_node_uids = ["icij:" + s for s in officers_at_ebury["source_id"].to_list()]
    network_edges = icij_edges.filter(pl.col("src_node").is_in(officer_node_uids))
    log.info("network edges from Ebury officers: %d", network_edges.height)

    connected_entity_uids = sorted(
        {e["dst_node"].replace("icij:", "") for e in network_edges.iter_rows(named=True)}
    )
    network_entities = icij_entities.filter(pl.col("source_id").is_in(connected_entity_uids))
    log.info("network entities (Ebury officers control these): %d", network_entities.height)

    # --- 4. Substring scan for any officer whose name matches Tohme/Sarkis
    #         (catches name variants without needing edge traversal) ---
    tohme_sarkis = icij_officers.filter(pl.col("normalized_name").str.contains("(?i)tohme|sarkis"))
    log.info("officers named Tohme/Sarkis (substring): %d", tohme_sarkis.height)

    # --- 5. Cross-check each OCOD-Ebury proprietor name in ICIJ ---
    def _norm(s: str) -> str:
        s = (s or "").lower()
        s = re.sub(r"[^a-z0-9]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    ocod_names = sorted({_norm(n) for n in ocod_hits["proprietor_name"].to_list() if n})
    icij_name_matches = (
        icij_entities.with_columns(
            pl.col("name")
            .fill_null("")
            .str.to_lowercase()
            .str.replace_all(r"[^a-z0-9]+", " ")
            .str.replace_all(r"\s+", " ")
            .str.strip_chars()
            .alias("_norm")
        )
        .filter(pl.col("_norm").is_in(ocod_names))
        .select("source_id", "name", "jurisdiction", "source_label", "_norm")
    )
    log.info("ICIJ name-matches against Ebury OCOD proprietors: %d", icij_name_matches.height)

    result = {
        "ocod_at_128_ebury": {
            "count": int(ocod_hits.height),
            "rows": ocod_hits.head(200).to_dicts(),
        },
        "icij_ebury_address_node": ebury_node.to_dicts(),
        "icij_officers_at_ebury": officers_at_ebury.to_dicts(),
        "icij_network_entities_from_ebury_officers": {
            "count": int(network_entities.height),
            "rows": network_entities.head(100).to_dicts(),
        },
        "icij_tohme_sarkis_substring_matches": tohme_sarkis.head(50).to_dicts(),
        "icij_panama_match_against_ocod_proprietors": {
            "count": int(icij_name_matches.height),
            "rows": icij_name_matches.head(100).to_dicts(),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
