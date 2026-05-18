"""Discovery Advantage Report — synthesis benchmark.

Pulls together every existing baseline-vs-pipeline measurement into one
canonical summary, so the novelty argument can be made in a single
artifact instead of cross-referencing eight reports.

This is **synthesis, not new compute**: it reads existing summary JSONs
from `/data/processed/` and emits one consolidated
`discovery_advantage_summary.json`. The renderer then produces a
publication-style report.

Inputs (all read; missing inputs degrade gracefully):
  - discovery_lift_summary.json         (B1..B4 tier funnel)
  - baseline_comparison_summary.json    (B5/B6 + analyst-hour model)
  - calibration_summary.json            (PAV Brier/ECE before/after)
  - adversarial_benchmark_summary.json  (B2 vs B6 perturbation recovery)
  - structure_benchmark_summary.json    (6 non-obvious structure types)
  - non_obviousness_summary.json        (per-anchor 5-factor scoring)
  - confidence_graph_summary.json       (community stability)
  - latent_clusters_summary.json        (unsupervised anomaly mining)
  - temporal_patterns_summary.json      (resurrection / burst / long-lived)
  - join_novelty_summary.json           (cross-source join novelty)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from shellnet.paths import PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


_INPUT_NAMES = [
    "discovery_lift_summary.json",
    "baseline_comparison_summary.json",
    "calibration_summary.json",
    "adversarial_benchmark_summary.json",
    "structure_benchmark_summary.json",
    "non_obviousness_summary.json",
    "confidence_graph_summary.json",
    "latent_clusters_summary.json",
    "temporal_patterns_summary.json",
    "join_novelty_summary.json",
]


def _load(p: Path) -> dict | None:
    if not p.exists():
        log.warning("missing input: %s", p.name)
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _safe(d: dict | None, *keys, default=None):
    cur = d
    for k in keys:
        if cur is None or not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


@app.command()
def main(
    inputs_dir: Path = typer.Option(PROCESSED_DIR, "--inputs-dir"),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "discovery_advantage_summary.json", "--out-summary"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    ensure_dirs()

    inputs = {name: _load(inputs_dir / name) for name in _INPUT_NAMES}
    present = sorted(name for name, val in inputs.items() if val is not None)
    log.info("loaded %d/%d inputs", len(present), len(_INPUT_NAMES))

    discovery = inputs["discovery_lift_summary.json"]
    baseline = inputs["baseline_comparison_summary.json"]
    calibration = inputs["calibration_summary.json"]
    adversarial = inputs["adversarial_benchmark_summary.json"]
    structure = inputs["structure_benchmark_summary.json"]
    non_obvious = inputs["non_obviousness_summary.json"]
    confidence = inputs["confidence_graph_summary.json"]
    latent = inputs["latent_clusters_summary.json"]
    temporal = inputs["temporal_patterns_summary.json"]
    join = inputs["join_novelty_summary.json"]

    # Headline delta table. Each row: (axis, baseline_value, pipeline_value,
    # delta, baseline_source, pipeline_source).
    deltas: list[dict] = []

    # 1. Multi-source anchor count: naive casefold vs goldenmatch normalize.
    b1 = _safe(discovery, "tiers", "B1_naive_casefold", "n_anchors_multisource")
    b2 = _safe(discovery, "tiers", "B2_goldenmatch_normalize", "n_anchors_multisource")
    if b1 is not None and b2 is not None:
        deltas.append(
            {
                "axis": "Multi-source anchors surfaced (whole corpus)",
                "baseline": b1,
                "pipeline": b2,
                "absolute_delta": b2 - b1,
                "relative_delta_pct": round(100.0 * (b2 - b1) / b1, 1) if b1 else None,
                "baseline_label": "naive casefold",
                "pipeline_label": "normalize_company_name",
                "source": "discovery_lift_summary.json",
            }
        )

    # 2. ICIJ-search-equivalent vs cross-source recall on B3 sample.
    icij_search = _safe(baseline, "tiers", "B5_icij_search_equivalent", "n_anchors_with_icij_match")
    naive_fuzzy = _safe(
        baseline, "tiers", "B6_naive_fuzzy_cross_source", "n_anchors_2_plus_sources"
    )
    sample = _safe(baseline, "sample_size")
    if icij_search is not None and naive_fuzzy is not None and sample:
        deltas.append(
            {
                "axis": "Anchors with cross-source evidence (B3 sample N=" + str(sample) + ")",
                "baseline": icij_search,
                "pipeline": naive_fuzzy,
                "absolute_delta": naive_fuzzy - icij_search,
                "relative_delta_pct": round(100.0 * (naive_fuzzy - icij_search) / icij_search, 1)
                if icij_search
                else None,
                "baseline_label": "ICIJ name-search alone",
                "pipeline_label": "GoldenMatch cross-source fuzzy",
                "source": "baseline_comparison_summary.json",
            }
        )

    # 3. Analyst hours (manual vs pipeline).
    manual_h = _safe(baseline, "analyst_review_reduction", "totals", "manual_hours_b3")
    pipeline_h = _safe(baseline, "analyst_review_reduction", "totals", "pipeline_hours_b3")
    if manual_h is not None and pipeline_h is not None:
        deltas.append(
            {
                "axis": "Analyst-hours to triage B3 population",
                "baseline": manual_h,
                "pipeline": pipeline_h,
                "absolute_delta": round(manual_h - pipeline_h, 1),
                "relative_delta_pct": round(100.0 * (manual_h - pipeline_h) / manual_h, 1)
                if manual_h
                else None,
                "baseline_label": "Manual cross-reference",
                "pipeline_label": "GoldenMatch dossier review",
                "source": "baseline_comparison_summary.json",
                "lower_is_better": True,
            }
        )

    # 4. Adversarial recovery rate (overall).
    b2_rec = _safe(adversarial, "overall", "b2_recovery_rate")
    b6_rec = _safe(adversarial, "overall", "b6_recovery_rate")
    if b2_rec is not None and b6_rec is not None:
        deltas.append(
            {
                "axis": "Perturbation recovery rate (adversarial)",
                "baseline": b2_rec,
                "pipeline": b6_rec,
                "absolute_delta": round(b6_rec - b2_rec, 4),
                "relative_delta_pct": round(100.0 * (b6_rec - b2_rec) / b2_rec, 1)
                if b2_rec
                else None,
                "baseline_label": "B2 exact-after-normalize",
                "pipeline_label": "B6 fuzzy (token-set 85)",
                "source": "adversarial_benchmark_summary.json",
            }
        )

    # 5. Probability calibration (expected calibration error). Lower is better.
    ece_raw = _safe(calibration, "raw", "ece")
    ece_cal = _safe(calibration, "calibrated", "ece")
    if ece_raw is not None and ece_cal is not None:
        deltas.append(
            {
                "axis": "Expected calibration error (ECE)",
                "baseline": round(ece_raw, 4),
                "pipeline": round(ece_cal, 6),
                "absolute_delta": round(ece_raw - ece_cal, 4),
                "relative_delta_pct": round(
                    100.0 * _safe(calibration, "improvement", "ece_pct", default=0.0), 4
                )
                / 100.0,
                "baseline_label": "Raw ER score",
                "pipeline_label": "PAV-calibrated",
                "source": "calibration_summary.json",
                "lower_is_better": True,
            }
        )

    # 6. Brier score (lower is better).
    brier_raw = _safe(calibration, "raw", "brier")
    brier_cal = _safe(calibration, "calibrated", "brier")
    if brier_raw is not None and brier_cal is not None:
        deltas.append(
            {
                "axis": "Brier score",
                "baseline": round(brier_raw, 4),
                "pipeline": round(brier_cal, 4),
                "absolute_delta": round(brier_raw - brier_cal, 4),
                "relative_delta_pct": _safe(calibration, "improvement", "brier_pct"),
                "baseline_label": "Raw ER score",
                "pipeline_label": "PAV-calibrated",
                "source": "calibration_summary.json",
                "lower_is_better": True,
            }
        )

    # Latent structures surfaced (counts from structure_benchmark).
    surfaced_structures: list[dict] = []
    if structure is not None:
        for k, st in (structure.get("structures") or {}).items():
            surfaced_structures.append(
                {
                    "id": k,
                    "n_detected": int(st.get("n_detected", 0)),
                    "icij_reachable": structure.get("baseline_reachability", {}).get(k[:2], "—"),
                }
            )

    # Latent / unsupervised mining (community-anomaly + temporal).
    latent_mining = {
        "louvain_total_communities": _safe(latent, "total_communities"),
        "annotated_communities": _safe(latent, "annotated_communities"),
        "max_anomaly_score": _safe(latent, "anomaly_score_distribution", "max"),
        "temporal_resurrections": _safe(temporal, "resurrections", "n_pairs"),
        "temporal_bursts": _safe(temporal, "bursts", "n_addresses"),
        "long_lived_anchors": _safe(temporal, "long_lived_anchors", "n"),
    }

    # Non-obviousness ranking (top-anchor scores).
    non_obviousness = {
        "n_anchors_scored": _safe(non_obvious, "n_anchors"),
        "top_10": _safe(non_obvious, "top_10") or [],
    }

    # Confidence-graph reasoning stability.
    confidence_stats = {
        "subgraph_nodes": _safe(confidence, "subgraph", "n_nodes"),
        "subgraph_edges": _safe(confidence, "subgraph", "n_edges"),
        "n_seeds": _safe(confidence, "subgraph", "n_seed_uids"),
        "stability_mean_jaccard": _safe(confidence, "stability", "mean_jaccard"),
        "stability_n_stable_nodes": _safe(confidence, "stability", "n_nodes_overlap_ge_0_5"),
        "stability_n_evaluated": _safe(confidence, "stability", "n_nodes_evaluated"),
    }

    # Join novelty: things not in the original ICIJ join set.
    join_novelty_stats = {}
    if join is not None:
        for k, v in join.items():
            if isinstance(v, dict):
                join_novelty_stats[k] = {
                    inner_k: inner_v
                    for inner_k, inner_v in v.items()
                    if isinstance(inner_v, (int, float, str))
                }

    summary = {
        "report": "discovery_advantage",
        "inputs_present": present,
        "inputs_missing": sorted(set(_INPUT_NAMES) - set(present)),
        "headline_deltas": deltas,
        "surfaced_structures": surfaced_structures,
        "latent_mining": latent_mining,
        "non_obviousness": non_obviousness,
        "confidence_reasoning": confidence_stats,
        "join_novelty": join_novelty_stats,
        "analyst_review_outcomes": {
            "status": "v2_gap_explicit",
            "note": (
                "No labelled analyst-review panel exists yet. The repo has "
                "no human-confirmed 'this is novel and investigatively "
                "relevant' annotations on the surfaced anchors. The "
                "structure_benchmark and non_obviousness scores are "
                "operational proxies, not ground truth. A v2 should send "
                "top-N from each surfacing channel to a panel of "
                "investigative journalists and record (a) confirm/reject, "
                "(b) novel-vs-known, (c) actionable-vs-noise."
            ),
            "operational_proxies_available": {
                "structure_benchmark_total": _safe(
                    structure, "totals", "total_pipeline_structures"
                ),
                "non_obviousness_anchors": _safe(non_obvious, "n_anchors"),
                "marginal_pair_review_labels": _safe(calibration, "n_positives"),
            },
        },
        "false_positive_lens": {
            "calibrated_ece": _safe(calibration, "calibrated", "ece"),
            "raw_ece": _safe(calibration, "raw", "ece"),
            "n_labelled_pairs": (_safe(calibration, "n_positives") or 0)
            + (_safe(calibration, "n_negatives") or 0),
            "interpretation": (
                "Calibrated ECE ~0 means pipeline output probabilities are "
                "trustworthy as confidence scores. A reviewer can rank by "
                "calibrated probability and expect approximately that "
                "fraction of top-k to be true positives. Raw ECE ~0.38 "
                "means uncalibrated scores were not trustworthy."
            ),
        },
    }

    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_summary.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log.info("wrote: %s", out_summary)
    log.info(
        "headline_deltas: %d  structures: %d",
        len(deltas),
        len(surfaced_structures),
    )


if __name__ == "__main__":
    app()
