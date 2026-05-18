"""Quantify the discovery lift of the goldenmatch+dossier pipeline vs baselines.

Spec: docs/superpowers/specs/2026-05-16-discovery-lift-benchmark.md

Reads person_entities.parquet, computes four nested baselines:

- B1: Naive case-fold pairwise — `name.lower().strip()`, count distinct sources.
- B2: Goldenmatch-normalized — same but using `normalize_company_name`.
- B3: Rare-filter applied — B2 narrowed to max_per_source ≤ 2, n_tokens ≥ 3.
- B4: Dossier pipeline — B3 names that pass through `build_rare_officer_dossiers`.

Emits a small parquet (one row per name across the union of all tiers) and a
summary JSON the renderer consumes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.normalize import normalize_company_name
from shellnet.paths import PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _naive_normalize(s: str | None) -> str:
    if not s:
        return ""
    return " ".join(s.lower().strip().split())


def _per_source_counts(df: pl.DataFrame, name_col: str) -> pl.DataFrame:
    """Aggregate per (source, normalized_name) → row count. Returns wide-form."""
    per = (
        df.filter(pl.col(name_col).is_not_null() & (pl.col(name_col).str.len_chars() > 0))
        .group_by(["source", name_col])
        .agg(pl.len().alias("n"))
    )
    wide = per.pivot(values="n", index=name_col, on="source").fill_null(0)
    source_cols = [c for c in wide.columns if c != name_col]
    return wide.with_columns(
        pl.sum_horizontal([(pl.col(c) > 0).cast(pl.Int32) for c in source_cols]).alias("n_sources"),
        pl.max_horizontal([pl.col(c) for c in source_cols]).alias("max_per_source"),
        pl.col(name_col).str.split(" ").list.len().alias("n_tokens"),
    )


@app.command()
def main(
    person_table: Path = typer.Option(
        PROCESSED_DIR / "person_entities.parquet",
        "--person-table",
    ),
    dossier_parquet: Path = typer.Option(
        PROCESSED_DIR / "rare_officer_dossiers.parquet",
        "--dossier-parquet",
        help="The B4 input — produced by build_rare_officer_dossiers.py.",
    ),
    out_parquet: Path = typer.Option(
        PROCESSED_DIR / "discovery_lift.parquet",
        "--out-parquet",
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "discovery_lift_summary.json",
        "--out-summary",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_parquet.parent.mkdir(parents=True, exist_ok=True)

    log.info("loading %s ...", person_table)
    base = pl.scan_parquet(person_table).filter(pl.col("name").is_not_null()).collect()
    log.info("person rows: %d", base.height)

    # B1: naive case-fold pairwise
    log.info("B1: naive case-fold normalization ...")
    b1_base = base.with_columns(
        pl.col("name").map_elements(_naive_normalize, return_dtype=pl.Utf8).alias("name_b1")
    ).filter(pl.col("name_b1").str.len_chars() > 0)
    b1_wide = _per_source_counts(b1_base, "name_b1")
    b1_multi = b1_wide.filter(pl.col("n_sources") >= 2)
    log.info("B1 multi-source anchors: %d", b1_multi.height)

    # B2: goldenmatch-normalized
    log.info("B2: goldenmatch normalize_company_name ...")
    b2_base = base.with_columns(
        pl.col("name").map_elements(normalize_company_name, return_dtype=pl.Utf8).alias("name_b2")
    ).filter(pl.col("name_b2").str.len_chars() > 0)
    b2_wide = _per_source_counts(b2_base, "name_b2")
    b2_multi = b2_wide.filter(pl.col("n_sources") >= 2)
    log.info("B2 multi-source anchors: %d", b2_multi.height)

    # B3: rare-filter applied
    b3 = b2_multi.filter(
        (pl.col("max_per_source") <= 2) & (pl.col("n_tokens") >= 3) & (pl.col("n_sources") >= 2)
    )
    log.info("B3 rare-filtered anchors: %d", b3.height)

    # B4: dossier pipeline — seeds that actually became dossiers
    dossier_seeds = (
        pl.read_parquet(dossier_parquet).select(pl.col("rare_name").alias("name_b2")).unique()
    )
    b4 = dossier_seeds.join(b3, on="name_b2", how="left")
    log.info("B4 dossier seeds: %d (all should be subset of B3)", b4.height)

    # Per-anchor signal: from the dossier parquet, did the seed get any linked
    # companies OR any sanctions adjacency?
    d_with_signal = (
        pl.read_parquet(dossier_parquet)
        .filter(pl.col("company_entity_uid").is_not_null())
        .select(pl.col("rare_name").alias("name_b2"))
        .unique()
    )
    d_sanc = (
        pl.read_parquet(dossier_parquet)
        .filter(pl.col("sanction_datasets").is_not_null())
        .select(pl.col("rare_name").alias("name_b2"))
        .unique()
    )

    # Build the union table: one row per name across all tiers.
    # B1 uses its own name col; we need to map naive→goldenmatch via the
    # base table so we can align. For each base row we have both name_b1
    # and name_b2 (different normalizations of the same original).
    b1_to_b2 = (
        b2_base.with_columns(
            pl.col("name").map_elements(_naive_normalize, return_dtype=pl.Utf8).alias("name_b1"),
        )
        .select("name_b1", "name_b2")
        .unique()
    )

    # Anchors reachable at each tier, keyed on canonical name_b2 where possible.
    # IMPORTANT: reachable_b2 means "name is multi-source at B2", NOT "name
    # exists in b2_wide" — every name exists in the wide pivot. Use b2_multi.
    reach = b2_multi.select(pl.col("name_b2")).with_columns(pl.lit(True).alias("reachable_b2"))
    # B1 reachability: take b1_multi names → join to b1_to_b2 to get name_b2.
    b1_in_b2 = (
        b1_to_b2.join(
            b1_multi.select(pl.col("name_b1")).with_columns(pl.lit(True).alias("reachable_b1")),
            on="name_b1",
            how="inner",
        )
        .select("name_b2", "reachable_b1")
        .unique()
    )
    reach = reach.join(b1_in_b2, on="name_b2", how="left")
    reach = reach.with_columns(pl.col("reachable_b1").fill_null(False))

    reach = reach.join(
        b3.select(pl.col("name_b2")).with_columns(pl.lit(True).alias("reachable_b3")),
        on="name_b2",
        how="left",
    ).with_columns(pl.col("reachable_b3").fill_null(False))

    reach = reach.join(
        b4.select(pl.col("name_b2")).with_columns(pl.lit(True).alias("reachable_b4")),
        on="name_b2",
        how="left",
    ).with_columns(pl.col("reachable_b4").fill_null(False))

    reach = reach.join(
        d_with_signal.with_columns(pl.lit(True).alias("dossier_has_signal")),
        on="name_b2",
        how="left",
    ).with_columns(pl.col("dossier_has_signal").fill_null(False))

    reach = reach.join(
        d_sanc.with_columns(pl.lit(True).alias("dossier_has_sanc")),
        on="name_b2",
        how="left",
    ).with_columns(pl.col("dossier_has_sanc").fill_null(False))

    # Keep only rows that were reachable at any tier — drops single-source
    # singletons that nobody surfaces.
    reach = reach.filter(
        pl.col("reachable_b1")
        | pl.col("reachable_b2")
        | pl.col("reachable_b3")
        | pl.col("reachable_b4")
    )
    log.info("union reachable anchors (B1 ∪ B2 ∪ B3 ∪ B4): %d", reach.height)
    reach.write_parquet(out_parquet)

    summary = {
        "tiers": {
            "B1_naive_casefold": {
                "n_anchors_multisource": int(b1_multi.height),
                "description": "Names appearing in 2+ sources after only lower().strip()",
            },
            "B2_goldenmatch_normalize": {
                "n_anchors_multisource": int(b2_multi.height),
                "description": "Names appearing in 2+ sources after normalize_company_name",
            },
            "B3_rare_filtered": {
                "n_anchors_multisource": int(b3.height),
                "description": "B2 narrowed to max_per_source <= 2, n_tokens >= 3",
            },
            "B4_dossier_pipeline": {
                "n_anchors_multisource": int(b4.height),
                "n_anchors_with_signal": int(d_with_signal.height),
                "n_anchors_with_sanctions": int(d_sanc.height),
                "description": "B3 seeds that actually became dossiers + graph-walk signal",
            },
        },
        "deltas": {
            "B2_minus_B1": int(b2_multi.height - b1_multi.height),
            "B3_minus_B2": int(b3.height - b2_multi.height),
            "B4_minus_B3": int(b4.height - b3.height),
        },
        "reachable_by_tier": {
            "b1_only": int(
                reach.filter(
                    pl.col("reachable_b1")
                    & ~pl.col("reachable_b2")
                    & ~pl.col("reachable_b3")
                    & ~pl.col("reachable_b4")
                ).height
            ),
            "b2_only": int(
                reach.filter(
                    ~pl.col("reachable_b1")
                    & pl.col("reachable_b2")
                    & ~pl.col("reachable_b3")
                    & ~pl.col("reachable_b4")
                ).height
            ),
            "b4_seeds_naive_unreachable": int(
                reach.filter(pl.col("reachable_b4") & ~pl.col("reachable_b1")).height
            ),
        },
    }
    out_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    typer.echo(f"Wrote: {out_parquet}")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
