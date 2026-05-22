"""Tightened ROE non-compliance matcher with a fuzzy second pass.

The v1 anti-join uses exact-equality on a normalised name key
(lowercase + suffix-strip + alphanum-only). That misses cases
where the OCOD and OE registry use different suffix forms
(e.g. "Deutsche Bank AG" vs "Deutsche Bank Aktiengesellschaft"
or "PROFITABLE PLOTS PTE LTD" vs "Profitable Plots Pte. Ltd.").

This v2 probe adds a *fuzzy second pass*:

  1. Run the exact-key anti-join (same as v1) — produces the
     "exact-mismatch" set of candidate non-compliant proprietors.
  2. For each candidate, compute a token-set against every OE
     entity sharing at least one 4-char token prefix (blocking).
  3. If Jaccard token-set similarity >= --jaccard-threshold
     (default 0.7), reclassify as "compliant via fuzzy match"
     and record the OE entity matched.
  4. Output: (a) reduced non-compliant set, (b) the fuzzy-
     matched pairs (so a reader can spot-check name-mismatches
     that the suffix-stripper didn't catch).

Each fuzzy match is a *suspected* same-entity — final
verification would still be a manual CH lookup. But the
fuzzy second pass shrinks the false-positive headline.

Output: ``/data/processed/probes/roe_noncompliance_strict.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_roe_noncompliance_strict")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_OE = Path("/data/processed/uk_ch_overseas_entities.parquet")


def _norm_expr(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(
            r"\b(ltd|limited|llc|inc|corp|corporation|sa|spa|gmbh|bv|ag|plc|llp|lp|"
            r"aktiengesellschaft|sarl|sarL|srl|pte|pty|nv|kft|oy|ab|as)\b",
            "",
        )
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


def _tokens(s: str) -> frozenset[str]:
    return frozenset(t for t in s.split() if len(t) >= 2)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/roe_noncompliance_strict.json"),
    )
    p.add_argument("--jaccard-threshold", type=float, default=0.7)
    p.add_argument(
        "--block-prefix-len",
        type=int,
        default=4,
        help="Block candidate OE entities by sharing a token prefix of this length.",
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    oe = pl.read_parquet(_OE).with_columns(_norm_expr("name").alias("match_key"))
    oe_keys = set(oe["match_key"].to_list())
    log.info("OE entities: %d, distinct keys: %d", oe.height, len(oe_keys))

    ocod = pl.read_parquet(_OCOD)
    name_col = next(
        c for c in ("proprietor_name", "normalized_name", "proprietor", "name") if c in ocod.columns
    )
    ocod = ocod.with_columns(_norm_expr(name_col).alias("match_key"))

    # v1 anti-join
    nc_titles = ocod.filter(
        ~pl.col("match_key").is_in(list(oe_keys)) & (pl.col("match_key").str.len_chars() > 3)
    )
    nc_props = (
        nc_titles.group_by("match_key")
        .agg([pl.col(name_col).first().alias("name"), pl.len().alias("n_titles")])
        .sort("n_titles", descending=True)
    )
    log.info("v1 non-compliant proprietors: %d (%d titles)", nc_props.height, nc_titles.height)

    # Build blocking index on OE side
    log.info("building OE blocking index...")
    oe_token_sets: dict[str, frozenset[str]] = {}
    block_idx: dict[str, list[str]] = defaultdict(list)
    block_len = args.block_prefix_len
    for r in oe.iter_rows(named=True):
        key = r["match_key"]
        if not key:
            continue
        toks = _tokens(key)
        if not toks:
            continue
        oe_token_sets[key] = toks
        for t in toks:
            if len(t) >= block_len:
                block_idx[t[:block_len]].append(key)
    log.info("  OE blocks: %d, distinct OE keys: %d", len(block_idx), len(oe_token_sets))

    # Fuzzy second pass over v1 non-compliant proprietors
    fuzzy_matches: list[dict] = []
    fuzzy_matched_keys: set[str] = set()
    log.info("running fuzzy second pass (jaccard >= %.2f)...", args.jaccard_threshold)
    for i, row in enumerate(nc_props.iter_rows(named=True)):
        if i % 1000 == 0:
            log.info("  scanned %d / %d", i, nc_props.height)
        key = row["match_key"]
        toks = _tokens(key)
        if not toks:
            continue
        candidates: set[str] = set()
        for t in toks:
            if len(t) >= block_len:
                candidates.update(block_idx.get(t[:block_len], []))
        if not candidates:
            continue
        best_jac = 0.0
        best_oe_key = None
        for cand_key in candidates:
            jac = _jaccard(toks, oe_token_sets[cand_key])
            if jac > best_jac:
                best_jac = jac
                best_oe_key = cand_key
        if best_jac >= args.jaccard_threshold and best_oe_key is not None:
            fuzzy_matches.append(
                {
                    "ocod_name": row["name"],
                    "ocod_match_key": key,
                    "oe_match_key": best_oe_key,
                    "jaccard": round(best_jac, 3),
                    "n_titles": row["n_titles"],
                }
            )
            fuzzy_matched_keys.add(key)

    log.info("fuzzy matches: %d proprietors reclassified as likely-compliant", len(fuzzy_matches))

    # Reduced non-compliant set
    strict_nc_props = nc_props.filter(~pl.col("match_key").is_in(list(fuzzy_matched_keys)))
    titles_in_strict = int(
        nc_titles.filter(~pl.col("match_key").is_in(list(fuzzy_matched_keys))).height
    )
    log.info(
        "after fuzzy: %d non-compliant proprietors (%d titles)",
        strict_nc_props.height,
        titles_in_strict,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "v1_noncompliant_proprietors": int(nc_props.height),
                    "v1_noncompliant_titles": int(nc_titles.height),
                    "fuzzy_reclassified_proprietors": len(fuzzy_matches),
                    "strict_noncompliant_proprietors": int(strict_nc_props.height),
                    "strict_noncompliant_titles": titles_in_strict,
                    "jaccard_threshold": args.jaccard_threshold,
                },
                "fuzzy_match_pairs_top": sorted(fuzzy_matches, key=lambda x: -x["n_titles"])[:200],
                "strict_top_noncompliant": strict_nc_props.head(50).to_dicts(),
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
