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

Implementation note: 46M parties is too large for Python set-based
`is_in` checks. We use polars lazy semi-joins instead, which stream
the data and avoid materialising the cartesian intermediate.

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


_DEED_TYPES = [
    "DEED",
    "DEED, BARGAIN AND SALE",
    "DEED, EXECUTOR'S",
    "DEED, REFEREE'S",
    "DEED, OTHER",
    "DEED, CORRECTION",
    "DEEDS, OTHER",
    "DEED, IN LIEU OF FORECLOSURE",
]


def _norm_expr(col: str) -> pl.Expr:
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
    p.add_argument(
        "--out", type=Path, default=Path("/data/processed/probes/nyc_acris_offshore.json")
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # ------------------------------------------------------------
    # Build lazy frames; let polars stream the joins.
    # ------------------------------------------------------------
    log.info("scanning ACRIS Master + Parties + Legals (lazy)...")
    deeds_lf = (
        pl.scan_parquet(_MASTER)
        .filter(pl.col("doc_type").is_in(_DEED_TYPES))
        .select("doc_id", "doc_type", "doc_date", "doc_amount_usd")
    )
    parties_lf = (
        pl.scan_parquet(_PARTIES)
        .filter((pl.col("party_type") == "2") & (pl.col("normalized_name") != ""))
        .select(
            "doc_id",
            "name",
            "normalized_name",
            "address_1",
            "city",
            "state",
            "country",
            "zip",
        )
    )
    icij_lf = (
        pl.scan_parquet(_ICIJ_ENTITIES)
        .with_columns(_norm_expr("name").alias("normalized_name"))
        .filter(pl.col("normalized_name") != "")
        .select(
            "normalized_name", pl.col("name").alias("icij_name"), "jurisdiction", "source_label"
        )
        .unique(subset=["normalized_name"])
    )

    # ------------------------------------------------------------
    # 1. Deed-grantee parties (inner join with deeds to restrict)
    # ------------------------------------------------------------
    log.info("step 1: filter parties to deed grantees (lazy semi-join with deeds)")
    deed_grantees_lf = parties_lf.join(deeds_lf, on="doc_id", how="inner")

    # ------------------------------------------------------------
    # 2. ICIJ match — semi-join on normalized_name
    # ------------------------------------------------------------
    log.info("step 2: ACRIS deed grantee x ICIJ name-match")
    icij_hits_lf = deed_grantees_lf.join(icij_lf, on="normalized_name", how="inner")
    icij_hits = icij_hits_lf.collect(engine="streaming")
    log.info("  ICIJ-matched grantee rows: %d", icij_hits.height)
    log.info(
        "  distinct ICIJ-matched grantee names: %d",
        icij_hits["normalized_name"].n_unique(),
    )

    # ------------------------------------------------------------
    # 3. Sanctioned-person match
    # ------------------------------------------------------------
    sanctioned_hits = pl.DataFrame()
    n_sanctioned = 0
    if _OS_SANCTIONED_PERSONS.exists():
        log.info("step 3: ACRIS deed grantee x OFAC SDN sanctioned persons")
        os_lf = (
            pl.scan_parquet(_OS_SANCTIONED_PERSONS)
            .filter(
                (pl.col("normalized_name").str.len_chars() >= 8)
                & (pl.col("normalized_name").str.count_matches(r"\s") >= 1)
            )
            .select(
                pl.col("normalized_name"),
                pl.col("name").alias("sanctioned_name"),
                pl.col("source").alias("sanctioned_source"),
            )
            .unique(subset=["normalized_name"])
        )
        sanctioned_hits = deed_grantees_lf.join(os_lf, on="normalized_name", how="inner").collect(
            engine="streaming"
        )
        n_sanctioned = sanctioned_hits.height
        log.info("  sanctioned-grantee rows: %d", n_sanctioned)
        log.info(
            "  distinct sanctioned-grantee names: %d",
            sanctioned_hits["normalized_name"].n_unique() if n_sanctioned else 0,
        )

    # ------------------------------------------------------------
    # 4. Join matched docs to property addresses (Legals)
    # ------------------------------------------------------------
    log.info("step 4: join matched docs to property addresses (Legals)")
    matched_doc_ids = (
        pl.concat(
            [
                icij_hits.select("doc_id"),
                sanctioned_hits.select("doc_id") if n_sanctioned else pl.DataFrame({"doc_id": []}),
            ]
        )
        .unique()
        .lazy()
    )
    legals_lf = pl.scan_parquet(_LEGALS).join(matched_doc_ids, on="doc_id", how="inner")
    legals = legals_lf.collect(engine="streaming")
    log.info("  legals rows for matched docs: %d", legals.height)

    icij_w_addr = icij_hits.join(legals, on="doc_id", how="left").head(100).to_dicts()
    sanc_w_addr = (
        sanctioned_hits.join(legals, on="doc_id", how="left").head(100).to_dicts()
        if n_sanctioned
        else []
    )

    # ------------------------------------------------------------
    # 5. Grantee correspondence-address hubs (sample 1M for memory)
    # ------------------------------------------------------------
    log.info("step 5: grantee correspondence-address hub counter (stream)")
    hub_counter: Counter[str] = Counter()
    # Stream by collecting only the hub columns
    addr_lf = deed_grantees_lf.select("address_1", "city", "zip")
    addr_df = addr_lf.collect(engine="streaming")
    for r in addr_df.iter_rows(named=True):
        addr = (r.get("address_1") or "").strip()
        city = (r.get("city") or "").strip()
        zip_ = (r.get("zip") or "").strip()
        if not addr:
            continue
        key = f"{addr.upper()} | {city.upper()} {zip_}"[:120]
        hub_counter[key] += 1
    log.info("  distinct grantee correspondence keys: %d", len(hub_counter))
    top_hubs = hub_counter.most_common(50)
    n_deed_grantees = int(addr_df.height)

    # ------------------------------------------------------------
    # Write result
    # ------------------------------------------------------------
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "deed_grantee_party_rows": n_deed_grantees,
                },
                "icij_matches": {
                    "n_rows": int(icij_hits.height),
                    "n_distinct_names": int(icij_hits["normalized_name"].n_unique()),
                    "sample": icij_w_addr,
                },
                "sanctioned_matches": {
                    "n_rows": n_sanctioned,
                    "n_distinct_names": int(sanctioned_hits["normalized_name"].n_unique())
                    if n_sanctioned
                    else 0,
                    "sample": sanc_w_addr,
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
