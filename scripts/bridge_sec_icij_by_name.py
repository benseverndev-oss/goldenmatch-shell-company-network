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
* Both sides must declare US jurisdiction. SEC filings are US-only;
  ICIJ entities matching by US jurisdiction filter most of the
  same-name-across-borders false positives.
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

# US-jurisdiction codes we accept on the ICIJ side. ICIJ uses both ISO
# alpha-2 ("us") and the older 3-letter codes; accept both.
_US_JURIS = frozenset({"us", "usa"})


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
    role) tuple. A single accession produces two rows: one subject and
    one filer."""

    df = pl.read_parquet(sec_edges_path)
    log.info("loaded %d SEC edges from %s", df.height, sec_edges_path)

    subjects = df.select(
        pl.col("subject_cik").alias("cik"),
        pl.col("subject_name").alias("name"),
        pl.lit("subject").alias("role"),
    )
    filers = df.select(
        pl.col("filer_cik").alias("cik"),
        pl.col("filer_name").alias("name"),
        pl.lit("filer").alias("role"),
    )
    combined = pl.concat([subjects, filers], how="vertical").unique(subset=["cik", "role"])
    combined = combined.with_columns(
        _normalize_name_series(pl.col("name")).alias("normalized"),
    ).filter(pl.col("normalized").str.len_chars() >= 4)
    log.info("  -> %d unique (cik, role) candidates with normalisable names", combined.height)
    return combined


def load_icij_us_entities(icij_path: Path) -> pl.DataFrame:
    """Project ICIJ entities to (source_id, name, normalized) for US-only
    rows.

    SEC is US-only, so we drop everything else upfront. This is the
    primary defamation-hazard mitigation — without it, a UK "Corvus
    Capital LLC" matches the SEC's US "Corvus Capital LLC" purely on
    name and we'd emit a false bridge.
    """

    df = pl.read_parquet(icij_path)
    log.info("loaded %d ICIJ entities from %s", df.height, icij_path)
    # Schema in this repo: source_id, name, jurisdiction (lowercase).
    df = df.with_columns(
        pl.col("jurisdiction").fill_null("").str.to_lowercase().str.strip_chars().alias("juris"),
    ).filter(pl.col("juris").is_in(list(_US_JURIS)))
    df = df.with_columns(
        _normalize_name_series(pl.col("name")).alias("normalized"),
    ).filter(pl.col("normalized").str.len_chars() >= 4)
    log.info("  -> %d US-jurisdiction ICIJ entities with normalisable names", df.height)
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
