"""Geographic deepdive on the SE1 non-compliant cluster.

SE1 holds 690 non-compliant titles — the largest single outward-
postcode cluster in the anti-join. Covers the South Bank,
Bermondsey, Borough, Waterloo, and Lambeth-fringe regeneration
zones. This probe unpacks it:

  1. Top proprietors by title count within SE1.
  2. Property-address concentration — which buildings or
     developments dominate (Park Plaza Westminster Bridge, etc.)
  3. Postcode-sector breakdown (SE1 1, SE1 2 ... SE1 9) — South
     Bank vs Bermondsey vs Borough.
  4. Country-of-incorporation breakdown for SE1 specifically.
  5. ICIJ leak overlap within SE1.
  6. Acquisition-date distribution (peaks around regeneration
     waves).

Output: ``/data/processed/probes/se1_deepdive.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_se1_deepdive")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_OE = Path("/data/processed/uk_ch_overseas_entities.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")


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


def _building_key(addr: str | None) -> str:
    """Extract a coarse building key — drop unit/flat/floor + lowercase."""
    if not addr:
        return ""
    s = addr.lower()
    s = re.sub(r"\b(flat|apartment|apt|unit|suite|room|floor)\s*\w+\s*,?", "", s)
    s = re.sub(r"\b\d+[a-z]?[-\d]*\s*[-,]", "", s, count=1)  # strip leading street number
    s = re.sub(r"\s*\(.*?\)\s*", "", s)  # strip parens (e.g. postcode in parens)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:80]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/se1_deepdive.json"),
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    oe = pl.read_parquet(_OE).with_columns(_norm_expr("name").alias("match_key"))
    oe_keys = set(oe["match_key"].to_list())

    ocod = pl.read_parquet(_OCOD)
    name_col = next(
        c for c in ("proprietor_name", "normalized_name", "proprietor", "name") if c in ocod.columns
    )
    pc_col = next(
        (c for c in ("postcode", "property_postcode", "postal_code") if c in ocod.columns), None
    )
    addr_col = next((c for c in ("property_address", "address") if c in ocod.columns), None)
    if pc_col is None:
        log.error("OCOD has no postcode column; cols=%s", ocod.columns)
        return 1
    ocod = ocod.with_columns(_norm_expr(name_col).alias("match_key"))

    # Filter to non-compliant + SE1 (any sector)
    se1 = ocod.filter(
        ~pl.col("match_key").is_in(list(oe_keys))
        & (pl.col("match_key").str.len_chars() > 3)
        & pl.col(pc_col).fill_null("").str.starts_with("SE1 ")
    )
    log.info("SE1 non-compliant titles: %d", se1.height)

    # 1. Top proprietors
    top_props = (
        se1.group_by(name_col)
        .agg(
            [
                pl.len().alias("n_titles"),
                pl.col("country_incorporated").first().alias("country")
                if "country_incorporated" in se1.columns
                else pl.lit(None).alias("country"),
            ]
        )
        .sort("n_titles", descending=True)
        .head(30)
        .to_dicts()
    )

    # 2. Building address concentration
    buildings: list[dict] = []
    if addr_col:
        bd = (
            se1.with_columns(
                pl.col(addr_col).map_elements(_building_key, return_dtype=pl.Utf8).alias("bkey")
            )
            .filter(pl.col("bkey").str.len_chars() > 8)
            .group_by("bkey")
            .agg(
                [
                    pl.len().alias("n_titles"),
                    pl.col(addr_col).first().alias("sample_address"),
                    pl.col(name_col).n_unique().alias("n_distinct_proprietors"),
                ]
            )
            .sort("n_titles", descending=True)
            .head(25)
        )
        buildings = bd.to_dicts()

    # 3. Postcode sector breakdown (full inward — SE1 0..9)
    pc_sector = (
        se1.with_columns(pl.col(pc_col).fill_null("").str.head(5).alias("pc_full_sector"))
        .group_by("pc_full_sector")
        .len()
        .sort("len", descending=True)
        .head(15)
        .to_dicts()
    )

    # 4. Country breakdown
    country_bd = []
    if "country_incorporated" in se1.columns:
        country_bd = (
            se1.group_by("country_incorporated")
            .len()
            .sort("len", descending=True)
            .head(15)
            .to_dicts()
        )

    # 5. ICIJ leak overlap within SE1
    se1_keys = set(se1["match_key"].unique().to_list())
    icij = pl.read_parquet(_ICIJ_ENTITIES).with_columns(_norm_expr("name").alias("match_key"))
    se1_icij_hits = icij.filter(pl.col("match_key").is_in(list(se1_keys)))
    log.info(
        "  SE1 non-compliant entities also in ICIJ: %d (distinct names: %d)",
        se1_icij_hits.height,
        se1_icij_hits["match_key"].n_unique(),
    )
    icij_hit_keys = set(se1_icij_hits["match_key"].to_list())

    # Top SE1 ICIJ-flagged proprietors (by title count) + their leak record
    icij_flagged = []
    for r in top_props:
        nm_norm = re.sub(
            r"\b(ltd|limited|llc|inc|corp|corporation|sa|spa|gmbh|bv|ag|plc|llp|lp)\b",
            "",
            (r.get(name_col) or "").lower(),
        )
        nm_norm = re.sub(r"[^a-z0-9]+", " ", nm_norm)
        nm_norm = re.sub(r"\s+", " ", nm_norm).strip()
        if nm_norm in icij_hit_keys:
            ic_rows = se1_icij_hits.filter(pl.col("match_key") == nm_norm).head(3).to_dicts()
            icij_flagged.append(
                {
                    "name": r.get(name_col),
                    "n_titles_se1": r["n_titles"],
                    "country_incorporated": r.get("country"),
                    "icij_records": [
                        {
                            "name": ic.get("name"),
                            "jurisdiction": ic.get("jurisdiction"),
                            "source_label": ic.get("source_label"),
                        }
                        for ic in ic_rows
                    ],
                }
            )

    # 6. Acquisition-date distribution by year
    year_dist: list[dict] = []
    date_col = "date_proprietor_added"
    if date_col in se1.columns:
        with_year = se1.with_columns(
            pl.coalesce(
                [
                    pl.col(date_col).str.to_date("%d-%m-%Y", strict=False),
                    pl.col(date_col).str.to_date("%d/%m/%Y", strict=False),
                    pl.col(date_col).str.to_date("%Y-%m-%d", strict=False),
                ]
            )
            .dt.year()
            .alias("yr")
        )
        year_dist = (
            with_year.filter(pl.col("yr").is_not_null()).group_by("yr").len().sort("yr").to_dicts()
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "se1_noncompliant_titles": int(se1.height),
                    "se1_icij_overlap_distinct_names": len(icij_hit_keys),
                    "n_distinct_proprietors": int(se1[name_col].n_unique()),
                },
                "top_proprietors": top_props,
                "top_buildings": buildings,
                "postcode_sectors": pc_sector,
                "country_incorporated": country_bd,
                "icij_flagged_in_se1": icij_flagged,
                "acquisition_year_distribution": year_dist,
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
