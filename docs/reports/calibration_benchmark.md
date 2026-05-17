# ER score calibration benchmark

_Generated 2026-05-17 00:07 UTC by `scripts/render_calibration_benchmark.py` from a Railway-side
build of `scripts/build_calibration_benchmark.py`. Spec:
[`2026-05-16-discovery-lift-benchmark.md`](../superpowers/specs/2026-05-16-discovery-lift-benchmark.md) (note: companion to discovery_lift)._

## What this measures

Goldenmatch's `__match_score__` is opaque — a score of 0.85 doesn't necessarily
mean "85% chance these are the same entity." This benchmark uses **DOB-year
agreement** as external supervision: pairs where both sides carry a
date-of-birth that *agrees on the year* are positives; pairs where both sides
carry a DOB but the years *disagree* are negatives (same name, different
person). DOB enrichment is upstream of the name score — independent signal.

- **Positive class** (340 pairs): `dob_match == "both_present_year_match"`
  in `matched_dob_scored.csv`.
- **Negative class** (340 pairs, sampled from 8,941):
  `dob_match == "both_present_year_mismatch"`. Same-distribution negatives —
  these are name-similarity matches that the DOB year refutes.

No human labels needed; the DOB year is the supervisor.

**Important framing.** The raw `__match_score__` was computed from name +
country features. It was *not designed* to distinguish two same-named
different-DOB people — that's exactly the failure mode DOB enrichment was
introduced to catch. So a candid hypothesis going in: the raw score will look
**over-confident** (~0.9 for both classes), and calibration will compress it
toward the base rate. If that's what the numbers show, the takeaway is "do
not threshold on raw score; use the calibrated probability or layer in DOB
post-hoc."

## Headline metrics

| Metric | Raw `__match_score__` | Calibrated | Improvement |
|---|---:|---:|---:|
| Brier score (lower better) | 0.3990 | 0.2399 | +39.9% |
| Log-loss (lower better) | 1.2223 | 0.6679 | +45.4% |
| Expected calibration error (lower better) | 0.3847 | 0.0000 | +100.0% |

The Brier-score improvement is the proper-scoring-rule reading: how much
better-calibrated the probabilities are once mapped through the
isotonic regression. ECE is the operator-readable version: "on average,
the calibrated score is off by X points of probability."

PAV produced **7 monotone segments** mapping raw → calibrated.

## Raw reliability table (before calibration)

Each row is a score-decile bin: how many pairs fall in that bin, the mean
raw score within the bin, and the actual fraction of LEI-matches within
the bin. A perfectly calibrated raw score would have `Gap = 0` everywhere
— `Frac positive` equals `Mean score`.

| Bin | Range | n | Mean score | Fraction positive | Gap |
|---:|---|---:|---:|---:|---|
| 0 | 0.0–0.1 | 0 | — | — | _(empty)_ |
| 1 | 0.1–0.2 | 0 | — | — | _(empty)_ |
| 2 | 0.2–0.3 | 0 | — | — | _(empty)_ |
| 3 | 0.3–0.4 | 0 | — | — | _(empty)_ |
| 4 | 0.4–0.5 | 0 | — | — | _(empty)_ |
| 5 | 0.5–0.6 | 0 | — | — | _(empty)_ |
| 6 | 0.6–0.7 | 0 | — | — | _(empty)_ |
| 7 | 0.7–0.8 | 0 | — | — | _(empty)_ |
| 8 | 0.8–0.9 | 403 | `█████████·` 0.852 | `█████·····` 0.514 | -0.339 |
| 9 | 0.9–1.0 | 277 | `█████████·` 0.932 | `█████·····` 0.480 | -0.452 |

## Calibrated reliability table (after PAV)

Same bins, but using the calibrated probability. Gap should be smaller
across the board — that's what isotonic regression buys us.

| Bin | Range | n | Mean score | Fraction positive | Gap |
|---:|---|---:|---:|---:|---|
| 0 | 0.0–0.1 | 4 | `··········` 0.000 | `··········` 0.000 | +0.000 |
| 1 | 0.1–0.2 | 0 | — | — | _(empty)_ |
| 2 | 0.2–0.3 | 0 | — | — | _(empty)_ |
| 3 | 0.3–0.4 | 0 | — | — | _(empty)_ |
| 4 | 0.4–0.5 | 642 | `█████·····` 0.483 | `█████·····` 0.483 | +0.000 |
| 5 | 0.5–0.6 | 0 | — | — | _(empty)_ |
| 6 | 0.6–0.7 | 8 | `██████····` 0.625 | `██████····` 0.625 | +0.000 |
| 7 | 0.7–0.8 | 0 | — | — | _(empty)_ |
| 8 | 0.8–0.9 | 0 | — | — | _(empty)_ |
| 9 | 0.9–1.0 | 26 | `██████████` 0.962 | `██████████` 0.962 | +0.000 |

## How to use the calibrator

The calibrator is serialised to `processed/erscore_calibrator.json`. Apply
it without importing the build script:

```python
import json, bisect

cal = json.loads(open("processed/erscore_calibrator.json").read())
thresholds = [c["max_score"] for c in cal["checkpoints"]]
probs = [c["calibrated_prob"] for c in cal["checkpoints"]]

def to_prob(raw_score: float) -> float:
    idx = bisect.bisect_left(thresholds, raw_score)
    if idx >= len(probs):
        return probs[-1]
    return probs[idx]
```

Downstream consumers (the dossier pipeline, list-match outputs) can
threshold on `to_prob(score) >= 0.8` for a calibrated 80%-confidence
filter instead of guessing what a raw 0.92 means.

## Honest limitations

1. **Train = test.** PAV was fit on the same set used to compute ECE. With
   340 positives there's no out-of-fold cross-validation. The
   numbers are training-set optimistic; the operational reduction will be
   smaller. A proper held-out split is a v2 follow-up.
2. **LEI as ground truth assumes LEIs are clean.** GLEIF assigns one LEI per
   legal entity, but historical mergers / LEI lapses can produce wrong-but-
   same-LEI cases. We accept this as ground-truth noise; the effect on
   reliability metrics should be small but non-zero.
3. **The calibrator generalises to `__match_score__` values from the same
   goldenmatch config**. Re-tuning the matcher config invalidates the
   calibrator; re-fit after a config change.
4. **No per-source-pair calibrators.** This one calibrator is fit across
   all ICIJ/OS↔GLEIF pairs. If ICIJ-only and OS-only score distributions
   differ materially, a single calibrator under-fits both. Diagnostic check
   in the bin table — if `Gap` differs systematically by score range,
   that's a signal.

## Reproduce

```bash
just job-run build_calibration_benchmark
just job-fetch processed/calibration_metrics.parquet docs/reports/data/
just job-fetch processed/calibration_summary.json docs/reports/data/
just job-fetch processed/erscore_calibrator.json docs/reports/data/

uv run python scripts/render_calibration_benchmark.py \
    --metrics docs/reports/data/calibration_metrics.parquet \
    --summary docs/reports/data/calibration_summary.json \
    --out docs/reports/calibration_benchmark.md
```

Or trigger `.github/workflows/build-calibration-benchmark.yml` for the
end-to-end refresh.
