"""Cross-reference NYC ACRIS grantees against ICIJ + OFAC SDN.

Now that nyc_acris_{master,parties,legals}.parquet exist on Railway
(~85M rows total), this probe asks the US-equivalent of the UK
"OCOD x ICIJ x ROE" question:

  1. Which NYC ACRIS grantees (Party Type 2 = buyer) name-match
     against ICIJ Offshore Leaks entities? (Panama / Paradise /
     Pandora / Bahamas / Offshore Leaks)
  2. Which NYC ACRIS grantee names name-match against OFAC SDN
     sanctioned persons (Person schema only)?
  3. What NYC property addresses did those matched grantees acquire?
     Joined via document_id to ACRIS Legals.
  4. Are there NYC ACRIS proprietor-address concentrations
     comparable to UK OCOD's 128 Ebury / 1 Royal Plaza hubs?

Restrict to deed-document types (real-property transfers, not
mortgages/refis) to avoid the noise of refinance party entries.

Output: ``/data/processed/probes/nyc_acris_offshore.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_nyc_acris_offshore")


_MASTER = Path("/data/processed/nyc_acris_master.parquet")
_PARTIES = Path("/data/processed/nyc_acris_parties.parquet")
_LEGALS = Path("/data/processed/nyc_acris_legals.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_OS_SANCTIONED_PERSONS = Path("/data/processed/os_sanctioned_persons.parquet")


# ACRIS doc_type values that represent ownership transfers (deeds).
# Common deed types: DEED, DEED, EASEMENT, MEMORANDUM OF LEASE,
# CONDO DECLARATION. Restrict to genuine deeds.
_DEED_TYPES = {
    "DEED",
    "DEED, BARGAIN AND SALE",
    "DEED, EXECUTOR'S",
    "DEED, REFEREE'S",
    "DEED, OTHER",
    "DEED, CORRECTION",
    "DEEDS, OTHER",
    "DEED, IN LIEU OF FORECLOSURE",
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out", type=Path, default=Path("/data/processed/probes/nyc_acris_offshore.json")
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    log.info("loading ACRIS Master (filtering to deed docs)...")
    master = (
        pl.scan_parquet(_MASTER)
        .filter(pl.col("doc_type").is_in(list(_DEED_TYPES)))
        .select("doc_id", "doc_type", "doc_date", "doc_amount_usd")
        .collect()
    )
    log.info("  deed documents: %d", master.height)
    deed_ids = set(master["doc_id"].to_list())

    log.info("loading ACRIS Parties (grantees only, deed docs only)...")
    parties = (
        pl.scan_parquet(_PARTIES)
        .filter(
            (pl.col("party_type") == "2")  # grantee = buyer
            & pl.col("doc_id").is_in(list(deed_ids))
            & (pl.col("normalized_name") != "")
        )
        .select("doc_id", "name", "normalized_name", "address_1", "city", "state", "country", "zip")
        .collect()
    )
    log.info("  deed-grantee party rows: %d", parties.height)
    log.info("  distinct grantee names: %d", parties["normalized_name"].n_unique())

    # ============================================================
    # 1. ACRIS grantee x ICIJ entity overlap
    # ============================================================
    log.info("=== ACRIS grantee x ICIJ entity ===")
    icij_norm_set = set(
        pl.scan_parquet(_ICIJ_ENTITIES)
        .select(
            pl.col("name")
            .fill_null("")
            .str.to_lowercase()
            .str.replace_all(r"[^a-z0-9]+", " ")
            .str.replace_all(r"\s+", " ")
            .str.strip_chars()
            .alias("_norm")
        )
        .filter(pl.col("_norm") != "")
        .collect()["_norm"]
        .to_list()
    )
    log.info("  icij entities (deduped, normalized): %d", len(icij_norm_set))

    icij_grantee_hits = parties.filter(pl.col("normalized_name").is_in(list(icij_norm_set)))
    log.info(
        "  ACRIS grantees in ICIJ: %d (%d distinct names)",
        icij_grantee_hits.height,
        icij_grantee_hits["normalized_name"].n_unique(),
    )

    # ============================================================
    # 2. ACRIS grantee x OFAC SDN (Person schema with guard)
    # ============================================================
    log.info("=== ACRIS grantee x OFAC SDN sanctioned persons ===")
    sanctioned: list[str] = []
    if _OS_SANCTIONED_PERSONS.exists():
        os_df = pl.read_parquet(_OS_SANCTIONED_PERSONS)
        for row in os_df.iter_rows(named=True):
            nm = row.get("normalized_name") or ""
            if len(nm.split()) >= 2 and len(nm) >= 8:
                sanctioned.append(nm)
        log.info("  sanctioned-person names (after defamation guard): %d", len(sanctioned))
    sanctioned_set = set(sanctioned)

    sanctioned_grantee_hits = parties.filter(pl.col("normalized_name").is_in(list(sanctioned_set)))
    log.info(
        "  ACRIS grantees matching sanctioned persons: %d (%d distinct)",
        sanctioned_grantee_hits.height,
        sanctioned_grantee_hits["normalized_name"].n_unique(),
    )

    # ============================================================
    # 3. Join ICIJ-matched grantees to property addresses via Legals
    # ============================================================
    log.info("=== joining matched grantees to property addresses ===")
    matched_doc_ids = set(icij_grantee_hits["doc_id"].to_list()) | set(
        sanctioned_grantee_hits["doc_id"].to_list()
    )
    log.info("  matched doc_ids: %d", len(matched_doc_ids))
    legals = (
        pl.scan_parquet(_LEGALS).filter(pl.col("doc_id").is_in(list(matched_doc_ids))).collect()
    )
    log.info("  legals rows for matched docs: %d", legals.height)

    # Build the result
    icij_hits_w_addr = icij_grantee_hits.join(legals, on="doc_id", how="left").join(
        master, on="doc_id", how="left"
    )
    sanc_hits_w_addr = sanctioned_grantee_hits.join(legals, on="doc_id", how="left").join(
        master, on="doc_id", how="left"
    )

    # ============================================================
    # 4. NYC ACRIS proprietor-address hubs (party correspondence
    #    address concentration analogous to UK OCOD hubs)
    # ============================================================
    log.info("=== ACRIS grantee correspondence-address hubs ===")
    hub_counter: Counter[str] = Counter()
    for r in parties.iter_rows(named=True):
        addr = (r.get("address_1") or "").strip()
        city = (r.get("city") or "").strip()
        zip_ = (r.get("zip") or "").strip()
        if not addr:
            continue
        key = f"{addr.upper()} | {city.upper()} {zip_}"[:120]
        hub_counter[key] += 1
    log.info("  distinct grantee correspondence keys: %d", len(hub_counter))
    top_hubs = hub_counter.most_common(50)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "deed_documents": int(master.height),
                    "grantee_party_rows": int(parties.height),
                    "distinct_grantee_names": int(parties["normalized_name"].n_unique()),
                    "icij_entities_loaded": len(icij_norm_set),
                    "sanctioned_persons_loaded": len(sanctioned),
                },
                "icij_matches": {
                    "n_grantee_rows": int(icij_grantee_hits.height),
                    "n_distinct_grantee_names": int(
                        icij_grantee_hits["normalized_name"].n_unique()
                    ),
                    "sample": icij_hits_w_addr.head(50).to_dicts(),
                },
                "sanctioned_matches": {
                    "n_grantee_rows": int(sanctioned_grantee_hits.height),
                    "n_distinct_grantee_names": int(
                        sanctioned_grantee_hits["normalized_name"].n_unique()
                    ),
                    "sample": sanc_hits_w_addr.head(50).to_dicts(),
                },
                "top_grantee_correspondence_hubs": [
                    {"address_key": k, "n_party_rows": n} for k, n in top_hubs
                ],
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
