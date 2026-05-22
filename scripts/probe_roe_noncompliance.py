"""ROE non-compliance — surface OCOD foreign owners with no UK CH OE record.

Under the UK Economic Crime (Transparency and Enforcement) Act 2022
(s.3 + s.4), every overseas-incorporated entity that owns a UK
qualifying-estate (freehold or leasehold >7 years) since the Feb
2022 cut-over must register on the Register of Overseas Entities
at UK Companies House. Failure to register is a **criminal offence**
under s.34/s.42 — daily fines, criminal liability for officers,
plus restrictions on dealing with the property until compliant.

This probe does the proper anti-join:

  - OCOD = HM Land Registry's Overseas Companies Ownership Data,
    ~365k UK property titles held by overseas-incorporated entities.
  - UK CH OE registry = 30,221 overseas entities registered under
    ECTEA 2022 (extracted from the May 2026 bulk download).

For every distinct OCOD proprietor name, we check whether a
UK CH OE entity with a matching normalised name exists. If not,
that proprietor is **potentially non-compliant**.

Output: ``/data/processed/probes/roe_noncompliance.json``.

This is a lead list — the same overseas entity may appear under
slightly different names in OCOD vs UK CH (e.g. "LTD" vs
"LIMITED"), so name-matching false negatives are possible. The
verification step is then per-name on UK CH.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_roe_noncompliance")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_OE = Path("/data/processed/uk_ch_overseas_entities.parquet")


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
        default=Path("/data/processed/probes/roe_noncompliance.json"),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    log.info("loading UK CH OE registry...")
    oe = pl.read_parquet(_OE)
    log.info("  OE entities: %d", oe.height)
    oe = oe.with_columns(_norm_expr("name").alias("ocod_match_key"))
    oe_keys = set(oe["ocod_match_key"].to_list())
    log.info("  distinct OE match-keys: %d", len(oe_keys))

    log.info("loading OCOD...")
    ocod = pl.read_parquet(_OCOD)
    log.info("  OCOD titles: %d", ocod.height)

    # Find the name + country columns
    name_col = next(
        c for c in ("proprietor_name", "normalized_name", "proprietor", "name") if c in ocod.columns
    )
    log.info("  proprietor name col: %s", name_col)
    ocod = ocod.with_columns(_norm_expr(name_col).alias("ocod_match_key"))

    # Get distinct proprietors and tally their title counts
    proprietor_summary = (
        ocod.group_by("ocod_match_key")
        .agg(
            [
                pl.col(name_col).first().alias("name"),
                pl.len().alias("n_titles"),
                pl.col("country_incorporated").first().alias("country_incorporated")
                if "country_incorporated" in ocod.columns
                else pl.lit(None).alias("country_incorporated"),
            ]
        )
        .filter(pl.col("ocod_match_key").str.len_chars() > 3)
        .sort("n_titles", descending=True)
    )
    log.info("  distinct proprietor match-keys: %d", proprietor_summary.height)

    # Anti-join — proprietors NOT in the OE registry
    noncompliant = proprietor_summary.filter(~pl.col("ocod_match_key").is_in(list(oe_keys)))
    compliant = proprietor_summary.filter(pl.col("ocod_match_key").is_in(list(oe_keys)))

    n_titles_compliant = int(compliant["n_titles"].sum())
    n_titles_noncompliant = int(noncompliant["n_titles"].sum())
    log.info(
        "  COMPLIANT proprietors: %d (%d titles)",
        compliant.height,
        n_titles_compliant,
    )
    log.info(
        "  NON-COMPLIANT proprietors: %d (%d titles)",
        noncompliant.height,
        n_titles_noncompliant,
    )

    # Top non-compliant by title count
    top_nc = noncompliant.head(200)

    # Country breakdown of non-compliant titles
    country_breakdown = (
        noncompliant.group_by("country_incorporated")
        .agg([pl.len().alias("n_entities"), pl.col("n_titles").sum().alias("n_titles")])
        .sort("n_titles", descending=True)
        .head(20)
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "uk_ch_oe_entities": int(oe.height),
                    "ocod_distinct_proprietors": int(proprietor_summary.height),
                    "ocod_total_titles": int(ocod.height),
                    "compliant_proprietors": int(compliant.height),
                    "noncompliant_proprietors": int(noncompliant.height),
                    "compliant_titles": n_titles_compliant,
                    "noncompliant_titles": n_titles_noncompliant,
                    "noncompliance_rate_by_proprietor": (
                        noncompliant.height / max(1, proprietor_summary.height)
                    ),
                    "noncompliance_rate_by_title": (
                        n_titles_noncompliant / max(1, n_titles_compliant + n_titles_noncompliant)
                    ),
                },
                "top_noncompliant_by_title_count": top_nc.to_dicts(),
                "country_breakdown_noncompliant": country_breakdown.to_dicts(),
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
