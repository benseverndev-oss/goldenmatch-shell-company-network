"""Bridge SEC `sec:CIK` UIDs to ICIJ `icij:*` UIDs via normalised name match.

Phase 10 of the data-source-utilization roadmap. Without bridge edges,
the Phase-6 SEC 13D/G corpus sits in a topologically disconnected
namespace: the dossier-anchored BFS that builds the confidence-graph
subgraph starts from ``icij:*`` seeds and never visits any ``sec:``
node, so the 13D/G edges contribute zero discovery.

This script emits ``sec_icij_bridges.parquet`` — one row per matched
SEC issuer/filer ↔ ICIJ entity pair, shaped to drop straight into
``build_confidence_graph`` as a ``same_company_as`` edge type.

Matching policy (conservative — the Corvus / John B. Marsh III lesson
from PR #61 is the cautionary tale):

* Both sides must normalise to the same string via
  :func:`shellnet.normalize.normalize_company_name`.
* **Only the SEC filer side** is matched — SEC subjects are by
  definition US-listed and so unlikely to appear in ICIJ's
  offshore-only corpus. Filers, however, are often offshore vehicles
  (BVI / Malta / Cyprus holdings) that DO appear in ICIJ. This
  filer-only direction is the discovery-aligned cut.
* Multi-token name requirement (≥ 3 normalised tokens, ≥ 12 chars).
  Drops the most common same-name coincidences ("ACME Inc" exists in
  every jurisdiction) while preserving substantive matches like
  "Corvus Capital Partners LP".
* No fuzzy matching, no abbreviation expansion. Names are not
  identities — anything looser invites defamation hazard.
* Emitted edge credibility is **0.60** (deliberately low) so the
  reviewer is reminded that the match is heuristic.

Inputs:
* ``/data/processed/sec_13dg_edges.parquet`` — Phase-6 output.
* ``/data/interim/icij_entities.parquet`` — ICIJ entity table.

Output:
* ``/data/processed/sec_icij_bridges.parquet`` columns::

    src_uid       str    sec:CIK on the SEC side
    dst_uid       str    icij:source_id on the ICIJ side
    sec_name      str    SEC issuer/filer name that matched
    icij_name     str    ICIJ entity name that matched
    normalized    str    the canonical string both sides resolved to
    sec_role      str    "subject" or "filer" — which side of the SEC
                         row produced this bridge

Heavy data; Railway-side. Local dev for tests only.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import polars as pl

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from shellnet.normalize import normalize_company_name  # noqa: E402

log = logging.getLogger("bridge_sec_icij_by_name")

# Minimum normalised-name length AND token count for an emitted bridge.
# ICIJ's corpus is offshore-only (top jurisdictions: VG, MT, AW, BM —
# no US-juris rows at all in the 814k entity table), so the original
# US-only filter on the ICIJ side rejected every candidate. The
# discovery-aligned cut is the opposite: SEC FILERS are often offshore
# vehicles (BVI / Malta / Cyprus holdings) that DO appear in ICIJ, and
# matching them is the lift. We trade US-juris gating for stronger
# name-shape gating to keep the defamation hazard bounded.
_MIN_NAME_CHARS = 12
_MIN_NAME_TOKENS = 3

# Phase 17a — SIC ranges with zero overlap with ICIJ's offshore corpus.
# Drop any SEC filer whose 4-digit SIC starts with one of these prefixes.
# Sourced from SEC EDGAR's published SIC code list. Includes commercial
# banks, broker-dealers, insurance carriers, air transportation,
# telecoms, utilities. These are large-cap regulated US issuers that
# show up in the bridge purely by name-coincidence ("First Finance Ltd"
# the BVI shell vs. a real ICIJ entity sharing the name).
_BLOCKLIST_SIC_PREFIXES: tuple[str, ...] = (
    "60",  # depository institutions / commercial banks
    "61",  # non-depository credit
    "62",  # security/commodity brokers, dealers
    "63",  # insurance carriers
    "451",  # air transportation, scheduled
    "452",  # air transportation, non-scheduled
    "481",  # telephone communications
    "482",  # telegraph
    "489",  # other communications
    "491",  # electric services
    "492",  # gas distribution
    "493",  # combination utility
)

# Filer-category strings that signal a large-cap US public issuer.
# SEC categories (per data.sec.gov submissions docs): "Large Accelerated
# Filer", "Accelerated Filer", "Non-accelerated Filer", "Smaller
# Reporting Company". The first two are the noise source.
_BLOCKLIST_FILER_CATEGORIES: frozenset[str] = frozenset(
    {"Large Accelerated Filer", "Accelerated Filer"}
)


def _normalize_name_series(col: pl.Expr) -> pl.Expr:
    """Polars-native equivalent of normalize_company_name for the parts
    that matter here: lowercase, strip punctuation, collapse whitespace.

    Note: we don't reuse the Python helper directly because it's a
    map_elements UDF (slow + memory-heavy on million-row inputs). The
    rules below mirror the Python helper for the cases that matter for
    SEC/ICIJ matching — letters/digits preserved, everything else
    becomes whitespace, multiple spaces collapse to one.
    """

    return (
        col.fill_null("")
        .str.to_lowercase()
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


def load_sec_names(sec_edges_path: Path) -> pl.DataFrame:
    """Project the SEC 13D/G edges parquet into one row per (CIK, name,
    role) tuple. Only the filer side is emitted — SEC subjects are
    US-listed and very unlikely to appear in ICIJ's offshore-only corpus.
    """

    df = pl.read_parquet(sec_edges_path)
    log.info("loaded %d SEC edges from %s", df.height, sec_edges_path)

    filers = df.select(
        pl.col("filer_cik").alias("cik"),
        pl.col("filer_name").alias("name"),
        pl.lit("filer").alias("role"),
    ).unique(subset=["cik"])
    combined = filers.with_columns(
        _normalize_name_series(pl.col("name")).alias("normalized"),
    ).filter(
        (pl.col("normalized").str.len_chars() >= _MIN_NAME_CHARS)
        & ((pl.col("normalized").str.count_matches(" ") + 1) >= _MIN_NAME_TOKENS)
    )
    log.info(
        "  -> %d unique SEC filers passing name-shape gates (>=%d chars, >=%d tokens)",
        combined.height,
        _MIN_NAME_CHARS,
        _MIN_NAME_TOKENS,
    )
    return combined


def load_icij_us_entities(icij_path: Path) -> pl.DataFrame:
    """Project ICIJ entities to (source_id, name, normalized) for rows
    that pass the multi-token name-shape gates.

    ICIJ Offshore Leaks is dominated by VG / MT / AW / BM (offshore)
    with zero US-juris rows, so the previous US-only filter rejected
    every candidate. The name-shape gates (multi-token, ≥12 chars) are
    the substitute defamation guard: most cross-border same-name
    coincidences are short single-token names that don't pass.
    """

    df = pl.read_parquet(icij_path)
    log.info("loaded %d ICIJ entities from %s", df.height, icij_path)
    df = df.with_columns(
        _normalize_name_series(pl.col("name")).alias("normalized"),
    ).filter(
        (pl.col("normalized").str.len_chars() >= _MIN_NAME_CHARS)
        & ((pl.col("normalized").str.count_matches(" ") + 1) >= _MIN_NAME_TOKENS)
    )
    log.info(
        "  -> %d ICIJ entities passing name-shape gates (>=%d chars, >=%d tokens)",
        df.height,
        _MIN_NAME_CHARS,
        _MIN_NAME_TOKENS,
    )
    return df


def build_bridges(sec_df: pl.DataFrame, icij_df: pl.DataFrame) -> pl.DataFrame:
    """Inner-join SEC (cik, normalized, role) against ICIJ
    (source_id, normalized) on the normalized name.

    Same-key semi-join shrinks both sides to shared normalised names
    before the materialising join — same pattern that fixed Phase 3
    OOM at corpus scale.
    """

    shared = (
        sec_df.select("normalized")
        .unique()
        .join(icij_df.select("normalized").unique(), on="normalized", how="inner")
    )
    log.info("  -> %d shared normalised names", shared.height)
    sec_df = sec_df.join(shared, on="normalized", how="inner")
    icij_df = icij_df.join(shared, on="normalized", how="inner")

    joined = sec_df.join(icij_df, on="normalized", how="inner", suffix="_icij")
    log.info("  -> %d candidate bridge rows pre-dedup", joined.height)

    bridges = joined.select(
        (pl.lit("sec:") + pl.col("cik")).alias("src_uid"),
        (pl.lit("icij:") + pl.col("source_id").cast(pl.String)).alias("dst_uid"),
        pl.col("name").alias("sec_name"),
        pl.col("name_icij").alias("icij_name"),
        pl.col("normalized"),
        pl.col("role").alias("sec_role"),
    ).unique(subset=["src_uid", "dst_uid"])
    log.info("  -> %d unique bridge pairs", bridges.height)
    return bridges


# ---------------------------------------------------------------------------
# Phase 17a — drop bridges where the SEC filer is a large-cap US issuer
# ---------------------------------------------------------------------------


def filter_large_cap_filers(
    bridges: pl.DataFrame,
    filer_metadata: pl.DataFrame,
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Drop bridge rows where the SEC filer is a large-cap US issuer.

    A filer is "large-cap" if any of:
      * its filer category is ``Large Accelerated Filer`` or ``Accelerated Filer``
      * its US-exchange ticker list is non-empty
      * its 4-digit SIC code prefix is in ``_BLOCKLIST_SIC_PREFIXES``
        (banks, airlines, insurers, telecoms, utilities).

    Args:
        bridges: output of :func:`build_bridges`. Must carry ``src_uid``
            in the form ``sec:<cik>``.
        filer_metadata: output of ``scripts/enrich_sec_filer_metadata.py``.
            Must carry ``cik``, ``sic``, ``category``, ``tickers``.

    Returns: (filtered_bridges, counts_dict) where counts_dict has keys
    ``input_rows``, ``dropped_large_filer``, ``dropped_us_ticker``,
    ``dropped_blocked_sic``, ``kept``.
    """

    counts = {
        "input_rows": bridges.height,
        "dropped_large_filer": 0,
        "dropped_us_ticker": 0,
        "dropped_blocked_sic": 0,
        "kept": 0,
    }
    if bridges.is_empty() or filer_metadata.is_empty():
        counts["kept"] = bridges.height
        return bridges, counts

    # Project metadata to (cik, drop_reason) — pick the first reason
    # the row trips so the dropped tally is unambiguous.
    meta = filer_metadata.with_columns(
        # SIC blocklist: starts-with-any of the prefixes.
        pl.col("sic")
        .fill_null("")
        .map_elements(
            lambda s: any(s.startswith(p) for p in _BLOCKLIST_SIC_PREFIXES),
            return_dtype=pl.Boolean,
        )
        .alias("_blocked_sic"),
        pl.col("category")
        .fill_null("")
        .is_in(list(_BLOCKLIST_FILER_CATEGORIES))
        .alias("_large_filer"),
        (pl.col("tickers").fill_null("").str.len_chars() > 0).alias("_has_ticker"),
    )
    drop_rules = meta.with_columns(
        pl.when(pl.col("_large_filer"))
        .then(pl.lit("large_filer"))
        .when(pl.col("_has_ticker"))
        .then(pl.lit("us_ticker"))
        .when(pl.col("_blocked_sic"))
        .then(pl.lit("blocked_sic"))
        .otherwise(pl.lit(""))
        .alias("drop_reason"),
    ).select("cik", "drop_reason")

    # Match bridges' src_uid (sec:<cik>) against metadata cik.
    annotated = (
        bridges.with_columns(pl.col("src_uid").str.replace("^sec:", "").alias("_cik"))
        .join(drop_rules.rename({"cik": "_cik"}), on="_cik", how="left")
        .with_columns(pl.col("drop_reason").fill_null(""))
    )

    counts["dropped_large_filer"] = int(
        annotated.filter(pl.col("drop_reason") == "large_filer").height
    )
    counts["dropped_us_ticker"] = int(annotated.filter(pl.col("drop_reason") == "us_ticker").height)
    counts["dropped_blocked_sic"] = int(
        annotated.filter(pl.col("drop_reason") == "blocked_sic").height
    )
    kept = annotated.filter(pl.col("drop_reason") == "").drop("_cik", "drop_reason")
    counts["kept"] = kept.height
    log.info(
        "Phase 17a filter: %d input -> %d kept "
        "(dropped: %d large-cap filer, %d US ticker, %d blocked SIC)",
        counts["input_rows"],
        counts["kept"],
        counts["dropped_large_filer"],
        counts["dropped_us_ticker"],
        counts["dropped_blocked_sic"],
    )
    return kept, counts


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--sec-edges",
        type=Path,
        default=Path("/data/processed/sec_13dg_edges.parquet"),
    )
    p.add_argument(
        "--icij-entities",
        type=Path,
        default=Path("/data/interim/icij_entities.parquet"),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/sec_icij_bridges.parquet"),
    )
    p.add_argument(
        "--filer-metadata",
        type=Path,
        default=None,
        help=(
            "Phase 17a: parquet from enrich_sec_filer_metadata.py. If "
            "present, drop bridge rows where the SEC filer is a "
            "Large/Accelerated Filer, has a US-exchange ticker, or has "
            "a blocked SIC prefix (banks/airlines/insurers/etc)."
        ),
    )
    p.add_argument(
        "--use-goldenmatch",
        action="store_true",
        help=(
            "Phase 15a: instead of exact normalised-name match, run "
            "GoldenMatch's calibrated fuzzy matcher and surface a per-"
            "row `prob` column. Default off so a regression in the "
            "matcher doesn't silently change the credibility graph."
        ),
    )
    p.add_argument(
        "--gm-threshold",
        type=float,
        default=0.92,
        help="Fuzzy threshold passed to GoldenMatch when --use-goldenmatch is on.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.sec_edges.exists():
        raise SystemExit(f"[fatal] {args.sec_edges} missing (run Phase 6 first)")
    if not args.icij_entities.exists():
        raise SystemExit(f"[fatal] {args.icij_entities} missing")

    sec_df = load_sec_names(args.sec_edges)
    icij_df = load_icij_us_entities(args.icij_entities)

    if args.use_goldenmatch:
        log.info("running GoldenMatch fuzzy matcher (threshold=%.2f)", args.gm_threshold)
        from shellnet.matching.goldenmatch_runner import match_names

        # GoldenMatch's match_df requires identical column sets on both
        # sides. Project both frames to a common (id, name, normalized)
        # schema, run the matcher, then rejoin against the original
        # frames to recover the SEC role + ICIJ source_id full rows.
        sec_for_gm = sec_df.select(
            pl.col("cik").alias("id"),
            pl.col("name"),
            pl.col("normalized"),
        )
        icij_for_gm = icij_df.select(
            pl.col("source_id").cast(pl.String).alias("id"),
            pl.col("name"),
            pl.col("normalized"),
        )
        gm_out = match_names(
            sec_for_gm,
            icij_for_gm,
            name_col="normalized",
            fuzzy_threshold=args.gm_threshold,
        )
        log.info("  -> %d candidate matches from GoldenMatch", gm_out.height)

        # GoldenMatch's current version prefixes columns: target_*
        # for the left side, ref_* for the right side. We projected to
        # an "id" column on both sides, so they surface as target_id +
        # ref_id. Stay robust to future suffix changes by accepting
        # either pattern.
        def _find_col(prefix: str, base: str) -> str:
            for cand in (f"{prefix}_{base}", f"{base}_{prefix}", f"{base}_right", base):
                if cand in gm_out.columns:
                    return cand
            return ""

        if gm_out.is_empty():
            bridges = pl.DataFrame(
                schema={
                    "src_uid": pl.String,
                    "dst_uid": pl.String,
                    "sec_name": pl.String,
                    "icij_name": pl.String,
                    "normalized": pl.String,
                    "sec_role": pl.String,
                    "prob": pl.Float64,
                }
            )
        else:
            tgt_id = _find_col("target", "id")
            tgt_name = _find_col("target", "name")
            ref_id = _find_col("ref", "id")
            ref_name = _find_col("ref", "name")
            tgt_norm = _find_col("target", "normalized") or _find_col("ref", "normalized")
            if not (tgt_id and ref_id):
                raise SystemExit(
                    f"[fatal] GoldenMatch output missing id columns; got {gm_out.columns}"
                )

            sec_lookup = sec_df.select(
                pl.col("cik").alias(tgt_id),
                pl.col("role").alias("sec_role"),
            )
            bridges = (
                gm_out.join(sec_lookup, on=tgt_id, how="left")
                .select(
                    (pl.lit("sec:") + pl.col(tgt_id)).alias("src_uid"),
                    (pl.lit("icij:") + pl.col(ref_id)).alias("dst_uid"),
                    pl.col(tgt_name).alias("sec_name"),
                    pl.col(ref_name).alias("icij_name"),
                    pl.col(tgt_norm).alias("normalized"),
                    pl.col("sec_role"),
                    pl.col("prob"),
                )
                .unique(subset=["src_uid", "dst_uid"])
            )
        log.info("  -> %d unique bridge pairs after dedup", bridges.height)
    else:
        bridges = build_bridges(sec_df, icij_df)

    # Phase 17a: drop large-cap US issuer false positives.
    if args.filer_metadata:
        if not args.filer_metadata.exists():
            log.warning(
                "--filer-metadata %s missing; skipping Phase-17a filter "
                "(run scripts/enrich_sec_filer_metadata.py first)",
                args.filer_metadata,
            )
        else:
            meta_df = pl.read_parquet(args.filer_metadata)
            bridges, _counts = filter_large_cap_filers(bridges, meta_df)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bridges.write_parquet(args.out)
    log.info("wrote %d bridge rows to %s", bridges.height, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Make the Python normalize helper discoverable from import-based tests.
_normalize_company_name = normalize_company_name
