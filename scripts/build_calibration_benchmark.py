"""Calibrate goldenmatch's __match_score__ via DOB-confirmation supervision.

The repo has no human-labeled match/no-match pairs; the `labels.py`
infrastructure exists but `labels.csv` was never produced. Tried:

- **LEI ground truth** — failed: ICIJ/OS targets in the GLEIF match file
  never carry an LEI (LEI is only on the GLEIF ref side).
- **Company number** — failed: not populated cross-source.
- **DOB-confirmation** — the path that works.

Uses `matched_dob_scored.csv` (OS-sanctioned-person ↔ ICIJ+UK_PSC name
matches enriched with DOB scoring):

- **Positive class** — `dob_match == "both_present_year_match"`. Both sides
  have DOBs and the years agree. ~340 examples in current corpus.
- **Negative class** — `dob_match == "both_present_year_mismatch"`. Both
  sides have DOBs, years disagree → same name, different person. Sampled
  to match positive count. ~8,941 in the pool.

Fits a PAV-isotonic-regression calibrator (hand-rolled — no sklearn dep).
Reports Brier score, log-loss, ECE, and 10-bin reliability stats.

Important caveat: this measures "does the score discriminate between
SAME-NAMED-SAME-PERSON and SAME-NAMED-DIFFERENT-PERSON pairs." The score
is computed from name + country features and was never designed to do
that discrimination — the DOB enrichment was added LATER precisely
because the name score alone couldn't tell them apart. So the headline
finding may well be "the raw score is uninformative on this task,
and isotonic-regression collapses it toward the base rate." That's
a valid honest finding for the methodology paper.

Outputs (small, git-trackable):
- `processed/calibration_metrics.parquet` — per-bin reliability stats.
- `processed/erscore_calibrator.json` — serialised PAV calibrator.
- `processed/calibration_summary.json` — Brier, log-loss, ECE, n_pos/n_neg.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import polars as pl
import typer

from shellnet.paths import PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _pav(scores: list[float], labels: list[int]) -> list[tuple[float, float]]:
    """Pool-Adjacent-Violators isotonic regression.

    Sorts (score, label) pairs by score then iteratively merges adjacent
    runs where the right run's mean is lower than the left's, until the
    sequence is non-decreasing. Returns a sorted list of
    ``(threshold_score, calibrated_prob)`` checkpoints. Linear in n.
    """
    pairs = sorted(zip(scores, labels, strict=False), key=lambda p: p[0])
    # Each "block" = (count, sum_labels, max_score_in_block)
    blocks: list[tuple[int, float, float]] = []
    for s, y in pairs:
        blocks.append((1, float(y), s))
        # Merge while the new block's mean is less than the previous block's mean.
        while len(blocks) >= 2:
            n_a, sum_a, _ = blocks[-2]
            n_b, sum_b, max_b = blocks[-1]
            if sum_a / n_a <= sum_b / n_b:
                break
            blocks[-2] = (n_a + n_b, sum_a + sum_b, max_b)
            blocks.pop()
    # Emit threshold + calibrated probability per block.
    return [(max_s, sum_y / n) for n, sum_y, max_s in blocks]


def _apply_calibrator(checkpoints: list[tuple[float, float]], score: float) -> float:
    """Look up the calibrated probability for a single score."""
    if not checkpoints:
        return 0.0
    # Binary search on threshold.
    lo, hi = 0, len(checkpoints)
    while lo < hi:
        mid = (lo + hi) // 2
        if checkpoints[mid][0] < score:
            lo = mid + 1
        else:
            hi = mid
    if lo >= len(checkpoints):
        return checkpoints[-1][1]
    return checkpoints[lo][1]


def _brier(scores: list[float], labels: list[int]) -> float:
    return sum((s - y) ** 2 for s, y in zip(scores, labels, strict=False)) / len(scores)


def _log_loss(scores: list[float], labels: list[int]) -> float:
    eps = 1e-15
    total = 0.0
    for s, y in zip(scores, labels, strict=False):
        s = min(max(s, eps), 1 - eps)
        total += -(y * math.log(s) + (1 - y) * math.log(1 - s))
    return total / len(scores)


def _ece(scores: list[float], labels: list[int], n_bins: int = 10) -> tuple[float, list[dict[str, Any]]]:
    """Expected calibration error + per-bin stats for the reliability table."""
    bins: list[dict[str, Any]] = [
        {"lo": i / n_bins, "hi": (i + 1) / n_bins, "n": 0, "sum_s": 0.0, "sum_y": 0}
        for i in range(n_bins)
    ]
    for s, y in zip(scores, labels, strict=False):
        idx = min(int(s * n_bins), n_bins - 1)
        bins[idx]["n"] += 1
        bins[idx]["sum_s"] += s
        bins[idx]["sum_y"] += y
    n_total = len(scores)
    ece = 0.0
    out = []
    for b in bins:
        if b["n"] == 0:
            out.append({**b, "mean_score": None, "frac_positive": None, "weight": 0.0})
            continue
        mean_score = b["sum_s"] / b["n"]
        frac_pos = b["sum_y"] / b["n"]
        weight = b["n"] / n_total
        ece += weight * abs(mean_score - frac_pos)
        out.append(
            {**b, "mean_score": mean_score, "frac_positive": frac_pos, "weight": weight}
        )
    return ece, out


@app.command()
def main(
    matched_csv: Path = typer.Option(
        PROCESSED_DIR.parent / "reports" / "generated" / "matched_dob_scored.csv",
        "--matched-csv",
        help="DOB-scored match CSV. Positive class = year_match; negative = year_mismatch.",
    ),
    out_metrics: Path = typer.Option(
        PROCESSED_DIR / "calibration_metrics.parquet",
        "--out-metrics",
    ),
    out_calibrator: Path = typer.Option(
        PROCESSED_DIR / "erscore_calibrator.json",
        "--out-calibrator",
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "calibration_summary.json",
        "--out-summary",
    ),
    neg_per_pos: float = typer.Option(
        1.0, "--neg-per-pos", help="Negative sampling ratio (default 1:1)."
    ),
    n_bins: int = typer.Option(10, "--n-bins"),
    seed: int = typer.Option(42, "--seed"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_metrics.parent.mkdir(parents=True, exist_ok=True)

    df = pl.read_csv(matched_csv, ignore_errors=True, infer_schema_length=500)
    log.info("loaded %d match rows", df.height)

    # Positive class: DOB year matches on both sides (independent of name score).
    pos = (
        df.filter(pl.col("dob_match") == "both_present_year_match")
        .select("__match_score__")
        .to_series()
        .to_list()
    )
    # Negative class: DOB years mismatch (same name, different person).
    neg_pool = (
        df.filter(pl.col("dob_match") == "both_present_year_mismatch")
        .select("__match_score__")
        .to_series()
        .to_list()
    )
    target_neg = int(len(pos) * neg_per_pos)
    if len(neg_pool) > target_neg:
        import random as _r

        _r.seed(seed)
        neg = _r.sample(neg_pool, target_neg)
    else:
        neg = neg_pool

    log.info("positives: %d  negatives: %d (pool %d)", len(pos), len(neg), len(neg_pool))

    if not pos or not neg:
        raise typer.BadParameter(
            "Need both positive and negative examples. "
            "Check that the match file has populated target_lei / ref_lei."
        )

    raw_scores = pos + neg
    labels = [1] * len(pos) + [0] * len(neg)

    # Fit PAV on full set (small enough, no train/test for v1).
    checkpoints = _pav(raw_scores, labels)
    log.info("calibrator checkpoints: %d", len(checkpoints))

    cal_scores = [_apply_calibrator(checkpoints, s) for s in raw_scores]

    raw_brier = _brier(raw_scores, labels)
    raw_ll = _log_loss(raw_scores, labels)
    raw_ece, raw_bins = _ece(raw_scores, labels, n_bins=n_bins)
    cal_brier = _brier(cal_scores, labels)
    cal_ll = _log_loss(cal_scores, labels)
    cal_ece, cal_bins = _ece(cal_scores, labels, n_bins=n_bins)

    log.info(
        "raw  : brier=%.4f log_loss=%.4f ece=%.4f", raw_brier, raw_ll, raw_ece
    )
    log.info(
        "cal  : brier=%.4f log_loss=%.4f ece=%.4f", cal_brier, cal_ll, cal_ece
    )

    # Reliability stats — both raw and calibrated, for the markdown table.
    metrics_rows = []
    for i, (rb, cb) in enumerate(zip(raw_bins, cal_bins, strict=False)):
        metrics_rows.append(
            {
                "bin_idx": i,
                "bin_lo": rb["lo"],
                "bin_hi": rb["hi"],
                "raw_n": rb["n"],
                "raw_mean_score": rb["mean_score"],
                "raw_frac_positive": rb["frac_positive"],
                "cal_n": cb["n"],
                "cal_mean_score": cb["mean_score"],
                "cal_frac_positive": cb["frac_positive"],
            }
        )
    pl.DataFrame(metrics_rows).write_parquet(out_metrics)

    out_calibrator.write_text(
        json.dumps(
            {
                "kind": "pav_isotonic",
                "checkpoints": [
                    {"max_score": s, "calibrated_prob": p} for s, p in checkpoints
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = {
        "n_positives": len(pos),
        "n_negatives": len(neg),
        "neg_pool_size": len(neg_pool),
        "raw": {"brier": raw_brier, "log_loss": raw_ll, "ece": raw_ece},
        "calibrated": {"brier": cal_brier, "log_loss": cal_ll, "ece": cal_ece},
        "improvement": {
            "brier_pct": (
                (raw_brier - cal_brier) / raw_brier * 100 if raw_brier > 0 else 0
            ),
            "log_loss_pct": (raw_ll - cal_ll) / raw_ll * 100 if raw_ll > 0 else 0,
            "ece_pct": (raw_ece - cal_ece) / raw_ece * 100 if raw_ece > 0 else 0,
        },
        "n_checkpoints": len(checkpoints),
    }
    out_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    typer.echo(f"Wrote: {out_metrics}")
    typer.echo(f"Wrote: {out_calibrator}")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
