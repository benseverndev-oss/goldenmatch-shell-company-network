"""Three US-angle probes in one pass.

Tests whether the UK-centric methodology can surface US-relevant
findings from existing data, without a fresh US-property dataset
ingestion (NYC ACRIS or similar).

A. US-incorporated proprietors in UK OCOD.
   Group HMLR OCOD by country_incorporated for US + US-state
   variants. Counts, distinct proprietors, recorded value, top
   proprietors by title count.

B. Sanctioned-person → ICIJ officer → OCOD overlap.
   Load OpenSanctions person rows from sanction-publishing sources
   (us_ofac_sdn, us_sam_exclusions, gb_fcdo_sanctions, eu_*_sanctions).
   Name-match against ICIJ officers with a defamation guard
   (Person, ≥2 tokens, ≥8 chars). For each match, walk the ICIJ
   officer_of edges to find the controlled entities, then check
   whether any of those entities' names match OCOD proprietor
   names.

C. SEC 13D/G filer → ICIJ entity overlap (filtered).
   Load sec_13dg_edges + sec_filer_metadata. Filter out large
   public US issuers (Large Accelerated Filers + US-exchange
   tickers + financial-sector SIC blocklist — the same filter
   as bridge_sec_icij_by_name). Then name-match surviving filers
   against ICIJ entities.

Output: ``/data/processed/probes/us_angles.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections import Counter
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_us_angles")


_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")
_OS_DIR = Path("/data/processed/os")  # OpenSanctions
_SEC_EDGES = Path("/data/processed/sec_13dg_edges.parquet")
_SEC_META = Path("/data/processed/sec_filer_metadata.parquet")


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# US-incorporated country labels in OCOD.
_US_LABELS = {
    "UNITED STATES OF AMERICA",
    "UNITED STATES",
    "USA",
    "U.S.A.",
    "DELAWARE",
    "NEVADA",
    "WYOMING",
    "FLORIDA",
    "CALIFORNIA",
    "NEW YORK",
    "TEXAS",
}


# Sanction-publishing datasets (NOT sanction.linked which is adjacency-only).
_SANCTION_SOURCES = {
    "us_ofac_sdn",
    "us_ofac_consolidated",
    "us_sam_exclusions",
    "gb_fcdo_sanctions",
    "gb_hmt_sanctions",
    "eu_eeas_sanctions",
    "eu_fsf",
    "un_sc_sanctions",
}


# SIC blocklist for SEC bridge filter — industries with zero overlap
# with ICIJ's offshore corpus.
_SIC_BLOCKLIST = {
    "6020",  # State commercial banks
    "6021",  # National commercial banks
    "6022",  # State commercial banks
    "6029",  # Commercial banks NEC
    "6199",  # Finance services
    "6311",  # Life insurance
    "6321",  # Accident & health insurance
    "6411",  # Insurance agents
    "4512",  # Air transportation, scheduled
    "4513",  # Air courier
    "4011",  # Railroads
    "4612",  # Pipeline transport
}


def _is_filtered_sec_filer(meta_row: dict) -> bool:
    """True if we should DROP this filer from the bridge (big public US issuer)."""
    if (meta_row.get("category") or "").startswith("Large Accelerated"):
        return True
    if meta_row.get("tickers") and (meta_row.get("exchanges") or ""):
        # US exchange = ticker present
        exch = meta_row["exchanges"].upper()
        if "NASDAQ" in exch or "NYSE" in exch or "AMEX" in exch:
            return True
    return meta_row.get("sic") in _SIC_BLOCKLIST


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("/data/processed/probes/us_angles.json"))
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result: dict = {}

    # ============================================================
    # A. US-incorporated OCOD proprietors
    # ============================================================
    log.info("=== A — US-incorporated OCOD proprietors ===")
    ocod = pl.read_parquet(_OCOD)
    us_mask = pl.col("country_incorporated").str.to_uppercase().is_in(list(_US_LABELS))
    us_ocod = ocod.filter(us_mask)
    log.info("  US-incorporated OCOD rows: %d", us_ocod.height)

    # Top proprietors
    top_props = (
        us_ocod.group_by("proprietor_name")
        .agg(pl.len().alias("n_titles"))
        .sort("n_titles", descending=True)
        .head(50)
        .to_dicts()
    )
    # Country mix (within US labels)
    country_mix = Counter()
    state_mix = Counter()
    for r in us_ocod.iter_rows(named=True):
        c = (r.get("country_incorporated") or "").strip().upper()
        country_mix[c] += 1
        # Proprietor address often contains a US state
        addr = (r.get("proprietor_address") or "").upper()
        for st in (
            "DELAWARE",
            "NEVADA",
            "WYOMING",
            "FLORIDA",
            "CALIFORNIA",
            "NEW YORK",
            "TEXAS",
            "ILLINOIS",
        ):
            if st in addr:
                state_mix[st] += 1
                break

    # Sum of recorded price_paid
    prices: list[int] = []
    for r in us_ocod.iter_rows(named=True):
        pp = (r.get("price_paid") or "").strip()
        if pp.isdigit():
            prices.append(int(pp))

    result["A_us_incorporated_in_ocod"] = {
        "total_titles": int(us_ocod.height),
        "distinct_proprietors": int(us_ocod["proprietor_name"].n_unique()),
        "country_mix": country_mix.most_common(),
        "state_mix_via_address": state_mix.most_common(),
        "recorded_value_gbp": sum(prices),
        "n_titles_with_price": len(prices),
        "max_price_gbp": max(prices) if prices else 0,
        "top_proprietors_by_title_count": top_props,
    }

    # ============================================================
    # B. Sanctioned-person → ICIJ officer → OCOD overlap
    # ============================================================
    log.info("=== B — Sanctioned-person → ICIJ → OCOD overlap ===")
    sanctioned_persons: list[dict] = []
    if _OS_DIR.exists():
        for parquet in _OS_DIR.glob("*.parquet"):
            try:
                df = pl.read_parquet(parquet)
                if "source_id" not in df.columns:
                    continue
                if "topics" not in df.columns or "entity_schema" not in df.columns:
                    continue
                # Sanction-publishing sources + Person schema + sanction topic
                filtered = df.filter(
                    pl.col("source_id").is_in(list(_SANCTION_SOURCES))
                    & (pl.col("entity_schema") == "Person")
                    & pl.col("topics").str.contains("sanction(?!\\.linked)")
                )
                for row in filtered.iter_rows(named=True):
                    nm = row.get("normalized_name") or _norm(row.get("name"))
                    # Defamation guard: ≥2 tokens, ≥8 chars
                    tokens = nm.split() if nm else []
                    if len(tokens) >= 2 and len(nm) >= 8:
                        sanctioned_persons.append(
                            {
                                "source_id": row.get("source_id"),
                                "name": row.get("name"),
                                "normalized_name": nm,
                                "topics": row.get("topics"),
                                "countries": row.get("countries"),
                            }
                        )
            except Exception as exc:  # noqa: BLE001
                log.warning("  skipping %s: %s", parquet.name, exc)
    log.info("  sanctioned-person names loaded: %d", len(sanctioned_persons))
    sanctioned_normset = {s["normalized_name"] for s in sanctioned_persons}

    # Match ICIJ officers
    icij_officers = pl.read_parquet(_ICIJ_OFFICERS)
    icij_matches = icij_officers.filter(pl.col("normalized_name").is_in(list(sanctioned_normset)))
    log.info("  ICIJ officers matching sanctioned persons: %d", icij_matches.height)

    # For each matched officer, walk their officer_of edges to find controlled entities
    matched_officer_uids = ["icij:" + s for s in icij_matches["source_id"].to_list()]
    sanction_entity_hits: list[dict] = []
    if matched_officer_uids:
        icij_edges = pl.read_parquet(_ICIJ_EDGES)
        edges_to_entities = icij_edges.filter(
            pl.col("src_node").is_in(matched_officer_uids) & (pl.col("kind_raw") == "officer_of")
        )
        controlled_uids = sorted(
            {e["dst_node"].replace("icij:", "") for e in edges_to_entities.iter_rows(named=True)}
        )
        if controlled_uids:
            icij_entities = pl.read_parquet(_ICIJ_ENTITIES)
            controlled = icij_entities.filter(pl.col("source_id").is_in(controlled_uids))
            # Cross-check controlled entity names against OCOD
            controlled_norms = [_norm(e["name"]) for e in controlled.iter_rows(named=True)]
            controlled_norms = [n for n in controlled_norms if n]
            ocod_hits = ocod.filter(pl.col("normalized_name").is_in(controlled_norms))
            for r in ocod_hits.head(50).iter_rows(named=True):
                sanction_entity_hits.append(
                    {
                        "ocod_proprietor": r.get("proprietor_name"),
                        "property_address": r.get("property_address"),
                        "postcode": r.get("postcode"),
                        "country_incorporated": r.get("country_incorporated"),
                    }
                )

    result["B_sanctioned_persons_via_icij_to_ocod"] = {
        "sanctioned_persons_loaded": len(sanctioned_persons),
        "icij_officer_name_matches": int(icij_matches.height),
        "ocod_property_hits_via_their_entities": len(sanction_entity_hits),
        "sample_sanctioned_persons": sanctioned_persons[:30],
        "sample_icij_matches": icij_matches.head(30).to_dicts(),
        "ocod_hits": sanction_entity_hits,
    }

    # ============================================================
    # C. SEC 13D/G filer → ICIJ entity overlap (filtered)
    # ============================================================
    log.info("=== C — SEC 13D/G filer → ICIJ entity (filtered) ===")
    if _SEC_EDGES.exists() and _SEC_META.exists():
        sec_meta = pl.read_parquet(_SEC_META)
        sec_edges = pl.read_parquet(_SEC_EDGES)
        # Build filter set: filer_ciks that are "small enough" to be plausibly ICIJ-matched
        meta_by_cik = {}
        for r in sec_meta.iter_rows(named=True):
            meta_by_cik[r["cik"]] = r
        # Filer CIKs that survive the filter
        surviving_ciks = set()
        for r in sec_edges.iter_rows(named=True):
            cik = r.get("filer_cik")
            if not cik:
                continue
            mm = meta_by_cik.get(cik)
            if mm and not _is_filtered_sec_filer(mm):
                surviving_ciks.add(cik)
        log.info("  filers surviving public-issuer filter: %d", len(surviving_ciks))

        # Get the filer-names of surviving CIKs from sec_edges
        sec_filer_names: dict[str, str] = {}
        for r in sec_edges.iter_rows(named=True):
            cik = r.get("filer_cik")
            if cik and cik in surviving_ciks and cik not in sec_filer_names:
                sec_filer_names[cik] = r.get("filer_name") or ""

        # Name-match surviving filer names against ICIJ entities
        icij_entities = pl.read_parquet(_ICIJ_ENTITIES)
        icij_norm_set = {_norm(e): e for e in icij_entities["name"].to_list() if _norm(e)}
        sec_icij_hits: list[dict] = []
        for cik, fname in sec_filer_names.items():
            nm = _norm(fname)
            if not nm or nm not in icij_norm_set:
                continue
            mm = meta_by_cik.get(cik, {})
            sec_icij_hits.append(
                {
                    "filer_cik": cik,
                    "filer_name": fname,
                    "filer_sic_description": mm.get("sic_description"),
                    "filer_state_of_incorporation": mm.get("state_of_incorporation"),
                    "icij_entity_name": icij_norm_set[nm],
                }
            )
        log.info("  SEC ↔ ICIJ name-match hits (filtered): %d", len(sec_icij_hits))
        result["C_sec_13dg_to_icij_filtered"] = {
            "surviving_filers_after_public_issuer_filter": len(surviving_ciks),
            "sec_icij_name_match_hits": len(sec_icij_hits),
            "hits": sec_icij_hits[:50],
        }
    else:
        log.warning("  SEC parquets not found; skipping C")
        result["C_sec_13dg_to_icij_filtered"] = {"skipped": "sec parquets missing"}

    # ============================================================
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
