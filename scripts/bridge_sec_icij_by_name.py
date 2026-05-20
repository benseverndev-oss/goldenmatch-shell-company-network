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
    bridges = build_bridges(sec_df, icij_df)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bridges.write_parquet(args.out)
    log.info("wrote %d bridge rows to %s", bridges.height, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Make the Python normalize helper discoverable from import-based tests.
_normalize_company_name = normalize_company_name
