"""Drill the remaining two high-confidence OS sanctions hits.

Same shape as probe_metalloinvest_verify, applied to:

  - "AAR International" — flagged crime.traffick in OS.
    The name is ambiguous: could be AAR Corp (US aerospace),
    the Alfa Group's AAR consortium (Aven, Khan, Fridman, Friedman
    Russian oligarchs), or something else entirely. The probe
    surfaces what OS knows + any ICIJ presence.

  - "Igt Intergestions Trust Reg" — flagged debarment+sanction in
    OS, jurisdiction Liechtenstein (li). Liechtenstein "Trust Reg"
    is an Anstalt-style vehicle. Probably a nominee/trustee shop
    similar to Ledra's role in the Metalloinvest structure.

For each, we pull:
  - Full ICIJ records matching the entity-name pattern
  - All inbound + outbound leak-graph edges
  - All OS records matching the name pattern (with full topics,
    jurisdictions, datasets)
  - The OCOD title list for the non-compliant proprietor
    (to confirm what UK property the entity holds)

Output: ``/data/processed/probes/aar_igt_verify.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_aar_igt_verify")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")
_OS_ENTITIES = Path("/data/interim/opensanctions_entities.parquet")

_TARGETS = [
    {
        "key": "aar_international",
        "ocod_pattern": "aar international",
        "icij_entity_pattern": "aar international|aar corp|alfa group",
        "icij_officer_pattern": "aven|fridman|khan|friedman",
        "os_pattern": "aar international|alfa group|aar corp",
    },
    {
        "key": "igt_intergestions",
        "ocod_pattern": "igt intergestions|intergestions",
        "icij_entity_pattern": "intergestions|igt",
        "icij_officer_pattern": None,
        "os_pattern": "intergestions|igt",
    },
]


def _drill(
    ocod: pl.DataFrame,
    name_col: str,
    icij_e: pl.DataFrame,
    icij_o: pl.DataFrame,
    edges: pl.DataFrame,
    os_lazy: pl.LazyFrame | None,
    target: dict,
) -> dict:
    log.info("=== %s ===", target["key"])
    out: dict = {"target_key": target["key"]}

    # OCOD
    ocod_hits = ocod.filter(
        pl.col(name_col).str.to_lowercase().str.contains(target["ocod_pattern"])
    )
    log.info("  OCOD titles: %d", ocod_hits.height)
    out["ocod_titles"] = ocod_hits.head(50).to_dicts()
    out["ocod_n_titles"] = int(ocod_hits.height)
    out["ocod_distinct_proprietors"] = ocod_hits[name_col].unique().to_list()

    # ICIJ entities
    icij_pat = target["icij_entity_pattern"]
    ent_hits = icij_e.filter(pl.col("name").str.to_lowercase().str.contains(icij_pat))
    log.info("  ICIJ entity hits: %d", ent_hits.height)
    out["icij_entities"] = ent_hits.head(25).to_dicts()
    ent_uids = ["icij:" + s for s in ent_hits["source_id"].to_list()]

    # Leak edges around the ICIJ entities
    in_edges = edges.filter(pl.col("dst_node").is_in(ent_uids)) if ent_uids else edges.head(0)
    out_edges = edges.filter(pl.col("src_node").is_in(ent_uids)) if ent_uids else edges.head(0)
    log.info("  edges inbound=%d, outbound=%d", in_edges.height, out_edges.height)

    in_src_uids = sorted(
        {r["src_node"].replace("icij:", "") for r in in_edges.iter_rows(named=True)}
    )
    connected_officers = (
        icij_o.filter(pl.col("source_id").is_in(in_src_uids)) if in_src_uids else icij_o.head(0)
    )
    out["icij_connected_officers"] = connected_officers.head(30).to_dicts()

    # ICIJ officer pattern hits
    if target["icij_officer_pattern"]:
        off_hits = icij_o.filter(
            pl.col("name").str.to_lowercase().str.contains(target["icij_officer_pattern"])
        )
        out["icij_officer_pattern_hits"] = off_hits.head(20).to_dicts()
    else:
        out["icij_officer_pattern_hits"] = []

    # OS
    if os_lazy is not None:
        try:
            os_hits = os_lazy.filter(
                pl.col("name").str.to_lowercase().str.contains(target["os_pattern"])
            ).collect()
            log.info("  OS hits: %d", os_hits.height)
            out["os_hits"] = os_hits.head(25).to_dicts()
        except Exception as exc:  # noqa: BLE001
            log.warning("  OS load failed: %s", exc)
            out["os_hits"] = []
    else:
        out["os_hits"] = []
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/aar_igt_verify.json"),
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    ocod = pl.read_parquet(_OCOD)
    name_col = next(
        c for c in ("proprietor_name", "normalized_name", "proprietor", "name") if c in ocod.columns
    )
    icij_e = pl.read_parquet(_ICIJ_ENTITIES)
    icij_o = pl.read_parquet(_ICIJ_OFFICERS)
    edges = pl.read_parquet(_ICIJ_EDGES)
    os_lazy = pl.scan_parquet(_OS_ENTITIES) if _OS_ENTITIES.exists() else None

    results = [_drill(ocod, name_col, icij_e, icij_o, edges, os_lazy, t) for t in _TARGETS]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"targets": results}, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
