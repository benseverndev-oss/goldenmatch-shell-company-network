"""Extend discovery-lift with realistic-baseline comparisons.

Adds three tiers on top of the B1-B4 hierarchy in build_discovery_lift.py:

- **B5 ICIJ-search-equivalent**: for each B3 rare-anchor, simulate ICIJ's
  search by fuzzy-matching the name against the local ICIJ name index
  (token-set-ratio >= 0.85). Approximates "what would a journalist
  using ICIJ Offshore Leaks Database's search box find."
- **B6 Naive fuzzy match**: for each B3 anchor, fuzzy-match against
  every source's name index. Approximates "what would a generic
  fuzzy-match tool (FuzzyWuzzy / dedupe.io) find without our normalize
  + suffix-strip + jurisdiction-blocking pipeline."
- **B7 Analyst review reduction**: model-based estimate of human work
  saved per anchor. Manual baseline = 4 separate UI queries (ICIJ,
  Companies House, OpenSanctions, GLEIF) + 2 min cross-reference =
  ~4 min/anchor. Our pipeline = 1 dossier read = ~1.5 min/anchor.

Computed against B3 (the rare-filtered ~3,800-anchor set) for cost
control. Scales linearly in B3 size; ~5-10 min on Railway.

Outputs (small, git-trackable):
- `processed/baseline_comparison.parquet` — per-anchor coverage flags
- `processed/baseline_comparison_summary.json` — aggregate counts +
  analyst-reduction model output
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import polars as pl
import typer
from rapidfuzz import fuzz, process

from shellnet.paths import PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


# ---- analyst review-reduction model ------------------------------------------
# Per-anchor wall-clock estimates. Numbers are operator estimates, not measured.
_MANUAL_PER_QUERY_SECS = 30  # type "name", load page, scan results
_MANUAL_CROSS_REFERENCE_SECS = 120  # compare + take notes
_MANUAL_SOURCES = ("ICIJ DB", "Companies House", "OpenSanctions", "GLEIF")
_PIPELINE_PER_ANCHOR_SECS = 90  # dossier read + 1 verification follow-up


def _per_anchor_manual_secs() -> int:
    return len(_MANUAL_SOURCES) * _MANUAL_PER_QUERY_SECS + _MANUAL_CROSS_REFERENCE_SECS


def _per_anchor_pipeline_secs() -> int:
    return _PIPELINE_PER_ANCHOR_SECS


# ---- fuzzy baselines ---------------------------------------------------------


def _fuzzy_count(
    query: str,
    targets: list[str],
    *,
    threshold: int = 85,
) -> int:
    """Count target names with rapidfuzz token-set-ratio >= threshold."""
    if not query:
        return 0
    # process.extract scores with token_set_ratio and trims by score_cutoff.
    # limit=None returns all matches above the threshold; cap defensively at 50.
    hits = process.extract(
        query, targets, scorer=fuzz.token_set_ratio, score_cutoff=threshold, limit=50
    )
    return len(hits)


@app.command()
def main(
    discovery_parquet: Path = typer.Option(
        PROCESSED_DIR / "discovery_lift.parquet",
        "--discovery-parquet",
        help="Output of build_discovery_lift — provides the B3 anchor set.",
    ),
    person_table: Path = typer.Option(
        PROCESSED_DIR / "person_entities.parquet",
        "--person-table",
    ),
    dossier_parquet: Path = typer.Option(
        PROCESSED_DIR / "rare_officer_dossiers.parquet",
        "--dossier-parquet",
        help="Used only to count dossier-tier anchors for the analyst model.",
    ),
    out_parquet: Path = typer.Option(
        PROCESSED_DIR / "baseline_comparison.parquet",
        "--out-parquet",
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "baseline_comparison_summary.json",
        "--out-summary",
    ),
    fuzzy_threshold: int = typer.Option(
        85,
        "--fuzzy-threshold",
        help="rapidfuzz token-set-ratio threshold (0-100).",
    ),
    sample_size: int = typer.Option(
        200,
        "--sample-size",
        help=(
            "Subsample of B3 anchors to evaluate. 200 finishes in ~13 min on "
            "Railway against the full 4-source corpus; bump higher if you want "
            "tighter confidence at the cost of wall-clock."
        ),
    ),
    seed: int = typer.Option(42, "--seed"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_parquet.parent.mkdir(parents=True, exist_ok=True)

    # B3 anchor set from discovery_lift.parquet
    disc = pl.read_parquet(discovery_parquet)
    b3 = disc.filter(pl.col("reachable_b3"))
    log.info("B3 anchor set: %d", b3.height)

    # Sample to bound compute.
    if b3.height > sample_size:
        b3_sample = b3.sample(n=sample_size, seed=seed)
        log.info("subsampled to %d anchors (--sample-size)", b3_sample.height)
    else:
        b3_sample = b3
    anchor_names = b3_sample.select("name_b2").to_series().to_list()

    # Per-source name indexes.
    log.info("scanning %s ...", person_table)
    base = pl.scan_parquet(person_table).filter(
        pl.col("normalized_name").is_not_null() & (pl.col("normalized_name").str.len_chars() > 0)
    )
    by_source: dict[str, list[str]] = {}
    for src in ("icij", "uk_psc", "opensanctions", "gleif"):
        names = (
            base.filter(pl.col("source") == src)
            .select(pl.col("normalized_name").unique())
            .collect()
            .to_series()
            .to_list()
        )
        by_source[src] = names
        log.info("  %s: %d unique normalized names", src, len(names))

    # Per-anchor coverage at each baseline.
    rows: list[dict] = []
    for i, name in enumerate(anchor_names, start=1):
        if i % 50 == 0 or i == len(anchor_names):
            log.info("[%d/%d] %r", i, len(anchor_names), name)
        per_anchor = {"name_b2": name}
        # B5: ICIJ-search-equivalent
        per_anchor["b5_icij_hits"] = _fuzzy_count(
            name, by_source["icij"], threshold=fuzzy_threshold
        )
        # B6: naive fuzzy across every source. Count anchors where 2+ sources
        # produce at least one fuzzy hit.
        src_hits = 0
        for src in ("icij", "uk_psc", "opensanctions", "gleif"):
            cnt = _fuzzy_count(name, by_source[src], threshold=fuzzy_threshold)
            per_anchor[f"b6_{src}_fuzzy_hits"] = cnt
            if cnt > 0:
                src_hits += 1
        per_anchor["b6_n_sources_fuzzy"] = src_hits
        rows.append(per_anchor)

    df = pl.DataFrame(rows)

    # Aggregate metrics.
    b5_reachable = df.filter(pl.col("b5_icij_hits") > 0).height
    b6_reachable = df.filter(pl.col("b6_n_sources_fuzzy") >= 2).height
    b6_all_sources = df.filter(pl.col("b6_n_sources_fuzzy") >= 3).height

    # Per-anchor analyst time model: assumes anchors are looked up in the
    # 4-source manual baseline. Multiplied by the B3 population (extrapolated
    # from sample if subsampled).
    extrapolation_factor = b3.height / b3_sample.height
    manual_secs_total = b3.height * _per_anchor_manual_secs()
    pipeline_secs_total = b3.height * _per_anchor_pipeline_secs()

    # Dossier tier (B4) — anchor count to also surface in the model.
    if dossier_parquet.exists():
        n_dossiers = pl.read_parquet(dossier_parquet).select("rare_name").unique().height
    else:
        n_dossiers = 0

    df.write_parquet(out_parquet)
    summary = {
        "sample_size": len(anchor_names),
        "b3_population": int(b3.height),
        "extrapolation_factor": round(extrapolation_factor, 3),
        "fuzzy_threshold": fuzzy_threshold,
        "tiers": {
            "B5_icij_search_equivalent": {
                "n_anchors_with_icij_match": int(b5_reachable),
                "fraction_of_sample": (
                    round(b5_reachable / len(anchor_names), 3) if anchor_names else 0
                ),
                "description": (
                    "Anchors where token-set-ratio >= 0.85 against ICIJ's local "
                    "name index returns at least one record. Proxy for "
                    "ICIJ Offshore Leaks Database's search-by-name."
                ),
            },
            "B6_naive_fuzzy_cross_source": {
                "n_anchors_2_plus_sources": int(b6_reachable),
                "n_anchors_3_plus_sources": int(b6_all_sources),
                "fraction_2plus_of_sample": (
                    round(b6_reachable / len(anchor_names), 3) if anchor_names else 0
                ),
                "description": (
                    "Anchors that fuzzy-match (threshold 0.85) at least one row "
                    "in 2+ source name indexes. The naive-fuzzy analog of B2's "
                    "exact-after-normalize match."
                ),
            },
        },
        "analyst_review_reduction": {
            "model_assumptions": {
                "per_manual_query_seconds": _MANUAL_PER_QUERY_SECS,
                "per_cross_reference_seconds": _MANUAL_CROSS_REFERENCE_SECS,
                "manual_sources": list(_MANUAL_SOURCES),
                "per_pipeline_anchor_seconds": _PIPELINE_PER_ANCHOR_SECS,
            },
            "per_anchor_manual_seconds": _per_anchor_manual_secs(),
            "per_anchor_pipeline_seconds": _per_anchor_pipeline_secs(),
            "b3_population": int(b3.height),
            "n_dossiers_top_tier": int(n_dossiers),
            "totals": {
                "manual_seconds_b3": int(manual_secs_total),
                "pipeline_seconds_b3": int(pipeline_secs_total),
                "manual_hours_b3": round(manual_secs_total / 3600, 1),
                "pipeline_hours_b3": round(pipeline_secs_total / 3600, 1),
                "reduction_factor": round(manual_secs_total / pipeline_secs_total, 1)
                if pipeline_secs_total
                else 0,
                "reduction_pct": round((1 - pipeline_secs_total / manual_secs_total) * 100, 1)
                if manual_secs_total
                else 0,
            },
        },
    }
    out_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    typer.echo(f"Wrote: {out_parquet}")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
