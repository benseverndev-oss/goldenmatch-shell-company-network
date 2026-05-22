"""Drill into the ROE non-compliance finding.

Augments the per-proprietor non-compliance list from
probe_roe_noncompliance with:

  1. ICIJ leak overlap — non-compliant entity name-matches against
     ICIJ entities (Panama / Paradise / Pandora / Offshore Leaks).
  2. OpenSanctions overlap — non-compliant entity name-matches
     against the consolidated OS sanctions/PEP/crime-tagged
     entity set we already have on Railway.
  3. Geographic concentration — top postcodes/LADs where
     non-compliant titles cluster.
  4. Title acquisition recency — flag titles acquired post-Feb-2022
     (the ECTEA cut-over) since those owners had a fixed deadline
     and are unambiguously in breach.

Output: ``/data/processed/probes/roe_noncompliance_drill.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_roe_noncompliance_drill")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_OE = Path("/data/processed/uk_ch_overseas_entities.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_OS_ENTITIES = Path("/data/interim/opensanctions_entities.parquet")


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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/roe_noncompliance_drill.json"),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    log.info("loading OE registry...")
    oe = pl.read_parquet(_OE)
    oe = oe.with_columns(_norm_expr("name").alias("match_key"))
    oe_keys = set(oe["match_key"].to_list())
    log.info("  OE entities: %d", oe.height)

    log.info("loading OCOD...")
    ocod = pl.read_parquet(_OCOD)
    name_col = next(
        c for c in ("proprietor_name", "normalized_name", "proprietor", "name") if c in ocod.columns
    )
    ocod = ocod.with_columns(_norm_expr(name_col).alias("match_key"))
    log.info("  OCOD titles: %d (proprietor col: %s)", ocod.height, name_col)
    log.info("  OCOD columns: %s", ocod.columns)

    # Non-compliant titles
    nc_titles = ocod.filter(
        ~pl.col("match_key").is_in(list(oe_keys)) & (pl.col("match_key").str.len_chars() > 3)
    )
    log.info("  non-compliant titles: %d", nc_titles.height)

    # Per-proprietor aggregation
    agg_cols = [
        pl.col(name_col).first().alias("name"),
        pl.len().alias("n_titles"),
    ]
    for c in ("country_incorporated", "title_number"):
        if c in ocod.columns:
            pass  # available
    if "country_incorporated" in ocod.columns:
        agg_cols.append(pl.col("country_incorporated").first().alias("country_incorporated"))
    # Try to include acquisition-date column if present
    date_col = next(
        (
            c
            for c in ("date_proprietor_added", "date_added", "registration_date")
            if c in ocod.columns
        ),
        None,
    )
    if date_col:
        agg_cols.append(pl.col(date_col).max().alias("latest_acquired"))
        log.info("  using acquisition-date column: %s", date_col)
    nc_props = nc_titles.group_by("match_key").agg(agg_cols).sort("n_titles", descending=True)
    log.info("  non-compliant distinct proprietors: %d", nc_props.height)
    nc_keys = set(nc_props["match_key"].to_list())

    # ---------------- 1. ICIJ overlap ----------------
    log.info("=== 1. ICIJ overlap ===")
    icij = pl.read_parquet(_ICIJ_ENTITIES).with_columns(_norm_expr("name").alias("match_key"))
    icij_hits = icij.filter(pl.col("match_key").is_in(list(nc_keys)))
    log.info("  ICIJ entity name-matches against non-compliant: %d", icij_hits.height)
    icij_match_keys = set(icij_hits["match_key"].to_list())

    # ---------------- 2. OS sanctions overlap ----------------
    log.info("=== 2. OpenSanctions overlap ===")
    os_hits_match_keys: set[str] = set()
    os_examples: list[dict] = []
    if _OS_ENTITIES.exists():
        try:
            os_ents = (
                pl.scan_parquet(_OS_ENTITIES)
                .filter(pl.col("schema").is_in(["Company", "Organization", "LegalEntity"]))
                .with_columns(_norm_expr("name").alias("match_key"))
                .filter(pl.col("match_key").is_in(list(nc_keys)))
                .collect()
            )
            log.info("  OS entity name-matches: %d", os_ents.height)
            os_hits_match_keys = set(os_ents["match_key"].to_list())
            os_examples = os_ents.head(50).to_dicts()
        except Exception as exc:  # noqa: BLE001
            log.warning("  OS load failed: %s", exc)
    else:
        log.warning("  OS entities file not present at %s", _OS_ENTITIES)

    # ---------------- 3. Geographic concentration ----------------
    log.info("=== 3. Geographic concentration ===")
    geo_concentration: list[dict] = []
    pc_col = next(
        (c for c in ("postcode", "property_postcode", "postal_code") if c in ocod.columns), None
    )
    if pc_col:
        geo = (
            nc_titles.with_columns(
                pl.col(pc_col).fill_null("").str.head(4).str.strip_chars().alias("postcode_outward")
            )
            .group_by("postcode_outward")
            .len()
            .sort("len", descending=True)
            .filter(pl.col("postcode_outward").str.len_chars() >= 2)
            .head(25)
        )
        geo_concentration = geo.to_dicts()
        log.info("  postcode-outward concentration computed")

    # ---------------- 4. Title acquisition recency ----------------
    log.info("=== 4. Title acquisition recency ===")
    post_2022: int | None = None
    pre_2022: int | None = None
    if date_col:
        try:
            with_date = nc_titles.with_columns(pl.col(date_col).cast(pl.Date, strict=False))
            post_2022 = int(with_date.filter(pl.col(date_col) >= pl.date(2022, 8, 1)).height)
            pre_2022 = int(with_date.filter(pl.col(date_col) < pl.date(2022, 8, 1)).height)
            log.info("  titles acquired post-Aug-2022: %d, pre-Aug-2022: %d", post_2022, pre_2022)
        except Exception as exc:  # noqa: BLE001
            log.warning("  date cast failed: %s", exc)

    # ---------------- Stitched output ----------------
    flagged: list[dict] = []
    for r in nc_props.head(500).iter_rows(named=True):
        key = r["match_key"]
        flagged.append(
            {
                "name": r.get("name"),
                "n_titles": r.get("n_titles"),
                "country_incorporated": r.get("country_incorporated"),
                "latest_acquired": str(r.get("latest_acquired"))
                if "latest_acquired" in r
                else None,
                "in_icij": key in icij_match_keys,
                "in_opensanctions": key in os_hits_match_keys,
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "noncompliant_proprietors": int(nc_props.height),
                    "noncompliant_titles": int(nc_titles.height),
                    "icij_overlap_distinct_names": len(icij_match_keys),
                    "os_overlap_distinct_names": len(os_hits_match_keys),
                    "titles_acquired_post_aug_2022": post_2022,
                    "titles_acquired_pre_aug_2022": pre_2022,
                },
                "top_flagged_proprietors": flagged,
                "icij_hits_sample": icij_hits.head(50).to_dicts(),
                "os_hits_sample": os_examples,
                "postcode_outward_concentration": geo_concentration,
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
