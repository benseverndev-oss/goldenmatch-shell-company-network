"""Expand each named-thread case study with new structural lenses.

For each of the 5 threads from probe_named_threads_deepdive
(plus FENLAND from its own probe), produce:

  1. FULL title list (not a sample): every OCOD row's full
     property address, postcode, price-paid, acquisition date,
     plus proprietor correspondence address.

  2. Proprietor-address hub-check: every distinct proprietor
     correspondence address used by the thread, and for each
     address how many OTHER non-compliant OCOD proprietors
     share it. Hub-address co-tenancy is the strongest signal
     that the thread is part of a wider serviced-address
     cluster (rather than standalone).

  3. Officer-edge expansion: for each ICIJ-named officer
     connected to the thread, walk the leak graph and surface
     every OTHER entity that officer is also tied to. Turns
     "Lilian Fenech is connected to FENLAND LIMITED" into
     "Lilian Fenech is connected to FENLAND LIMITED + X + Y + Z."

Output: ``/data/processed/probes/named_threads_expand.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_named_threads_expand")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_OE = Path("/data/processed/uk_ch_overseas_entities.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")

_TARGETS = [
    {"key": "fenland", "ocod_pattern": "fenland", "icij_officer_pattern": "fenech"},
    {"key": "edokpolo", "ocod_pattern": "eko ire", "icij_officer_pattern": "edokpolo"},
    {
        "key": "embassy_development",
        "ocod_pattern": "embassy development",
        "icij_officer_pattern": None,
    },
    {"key": "harmony_ridge", "ocod_pattern": "harmony ridge", "icij_officer_pattern": None},
    {"key": "ledra_trustee", "ocod_pattern": "ledra trustee", "icij_officer_pattern": "ledra"},
]


def _norm_expr(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(
            r"\b(ltd|limited|llc|inc|corp|corporation|sa|spa|gmbh|bv|ag|plc|llp|lp)\b", ""
        )
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


def _addr_key(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"\b(po box|p\.o\. box)[^,]*,?", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/named_threads_expand.json"),
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # --- Set up non-compliant set + address index across whole corpus ---
    oe = pl.read_parquet(_OE).with_columns(_norm_expr("name").alias("match_key"))
    oe_keys = set(oe["match_key"].to_list())
    ocod = pl.read_parquet(_OCOD)
    name_col = next(
        c for c in ("proprietor_name", "normalized_name", "proprietor", "name") if c in ocod.columns
    )
    addr_col = next(
        (c for c in ("proprietor_address", "registered_address") if c in ocod.columns), None
    )
    ocod = ocod.with_columns(_norm_expr(name_col).alias("match_key"))
    nc_ocod = ocod.filter(
        ~pl.col("match_key").is_in(list(oe_keys)) & (pl.col("match_key").str.len_chars() > 3)
    )
    log.info(
        "non-compliant OCOD rows: %d, name col: %s, addr col: %s",
        nc_ocod.height,
        name_col,
        addr_col,
    )

    # Build address index — for each addr-key in non-compliant rows,
    # how many distinct proprietors share it?
    if addr_col:
        nc_ocod = nc_ocod.with_columns(
            pl.col(addr_col).map_elements(_addr_key, return_dtype=pl.Utf8).alias("addr_key")
        )
        addr_index = (
            nc_ocod.filter(pl.col("addr_key").str.len_chars() > 10)
            .group_by("addr_key")
            .agg(
                [
                    pl.col(name_col).n_unique().alias("n_distinct_proprietors"),
                    pl.len().alias("n_titles"),
                    pl.col(name_col).unique().alias("proprietors"),
                ]
            )
        )
        addr_to_count = {r["addr_key"]: r for r in addr_index.iter_rows(named=True)}
    else:
        addr_to_count = {}

    # --- ICIJ load ---
    icij_e = pl.read_parquet(_ICIJ_ENTITIES)
    icij_o = pl.read_parquet(_ICIJ_OFFICERS)
    edges = pl.read_parquet(_ICIJ_EDGES)

    results: list[dict] = []
    for t in _TARGETS:
        log.info("=== %s ===", t["key"])
        pattern = t["ocod_pattern"]
        target_rows = ocod.filter(pl.col(name_col).str.to_lowercase().str.contains(pattern))
        log.info("  OCOD titles for %s: %d", t["key"], target_rows.height)

        # Full title list (cap at 400 to keep JSON sane)
        full_titles = target_rows.head(400).to_dicts()

        # Address co-tenancy: for each proprietor-correspondence address
        # in the thread, how many other non-compliant proprietors share it?
        addr_cotenancy: list[dict] = []
        if addr_col:
            for addr in target_rows[addr_col].unique().to_list():
                ak = _addr_key(addr)
                if not ak or len(ak) <= 10:
                    continue
                hit = addr_to_count.get(ak)
                if not hit:
                    continue
                # Filter out self-co-tenancy (only keep OTHER proprietors)
                others = [
                    p for p in hit["proprietors"] if not re.search(pattern, (p or "").lower())
                ]
                if others or hit["n_distinct_proprietors"] > 1:
                    addr_cotenancy.append(
                        {
                            "address_raw": addr,
                            "address_key": ak,
                            "n_distinct_noncompliant_proprietors_at_addr": int(
                                hit["n_distinct_proprietors"]
                            ),
                            "n_noncompliant_titles_at_addr": int(hit["n_titles"]),
                            "other_proprietors_at_addr": others[:20],
                        }
                    )

        # ICIJ officer expansion
        officer_expansion: list[dict] = []
        if t["icij_officer_pattern"]:
            off_pat = t["icij_officer_pattern"]
            off_hits = icij_o.filter(pl.col("name").str.to_lowercase().str.contains(off_pat))
            log.info("  ICIJ officer hits for /%s/: %d", off_pat, off_hits.height)
            for off in off_hits.head(40).iter_rows(named=True):
                off_uid = "icij:" + off["source_id"]
                out_edges = edges.filter(
                    (pl.col("src_node") == off_uid)
                    & (
                        pl.col("kind_raw").is_in(
                            ["officer_of", "intermediary_of", "beneficiary_of"]
                        )
                    )
                )
                ent_uids = [
                    e["dst_node"].replace("icij:", "") for e in out_edges.iter_rows(named=True)
                ]
                if not ent_uids:
                    continue
                ents = icij_e.filter(pl.col("source_id").is_in(ent_uids))
                officer_expansion.append(
                    {
                        "officer_name": off.get("name"),
                        "officer_country": off.get("country"),
                        "officer_source_label": off.get("source_id_label"),
                        "connected_entities": [
                            {
                                "name": e.get("name"),
                                "jurisdiction": e.get("jurisdiction"),
                                "source_label": e.get("source_label"),
                            }
                            for e in ents.head(15).iter_rows(named=True)
                        ],
                    }
                )

        results.append(
            {
                "target_key": t["key"],
                "ocod_pattern": pattern,
                "ocod_n_titles": int(target_rows.height),
                "full_titles": full_titles,
                "proprietor_address_cotenancy": addr_cotenancy[:25],
                "icij_officer_expansion": officer_expansion,
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"targets": results}, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
