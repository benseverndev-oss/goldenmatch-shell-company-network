"""Render docs/reports/calibration_benchmark.md from the Railway artifacts.

Pure templating. Reads calibration_metrics.parquet + calibration_summary.json,
emits markdown with both raw and calibrated reliability tables.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


def _ascii_bar(width: int, fill: float) -> str:
    """Tiny inline 'reliability bar' for the markdown table — fill in [0,1]."""
    n = max(0, min(width, int(round(width * fill))))
    return "█" * n + "·" * (width - n)


def _bin_table(bins: list[dict], kind: str) -> str:
    rows = [
        "| Bin | Range | n | Mean score | Fraction positive | Gap |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for b in bins:
        n = int(b[f"{kind}_n"] or 0)
        if n == 0:
            rows.append(
                f"| {b['bin_idx']} | {b['bin_lo']:.1f}–{b['bin_hi']:.1f} | 0 | — | — | _(empty)_ |"
            )
            continue
        m = float(b[f"{kind}_mean_score"])
        f = float(b[f"{kind}_frac_positive"])
        gap = f - m
        bar_score = _ascii_bar(10, m)
        bar_pos = _ascii_bar(10, f)
        sign = "+" if gap >= 0 else ""
        rows.append(
            f"| {b['bin_idx']} | {b['bin_lo']:.1f}–{b['bin_hi']:.1f} | {n:,} | `{bar_score}` {m:.3f} | `{bar_pos}` {f:.3f} | {sign}{gap:.3f} |"
        )
    return "\n".join(rows)


@app.command()
def main(
    metrics: Path = typer.Option(..., "--metrics", help="calibration_metrics.parquet"),
    summary: Path = typer.Option(..., "--summary", help="calibration_summary.json"),
    out: Path = typer.Option(
        Path("docs/reports/calibration_benchmark.md"), "--out"
    ),
) -> None:
    df = pl.read_parquet(metrics)
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    bins = df.to_dicts()
    raw = s["raw"]
    cal = s["calibrated"]
    imp = s["improvement"]

    body = f"""# ER score calibration benchmark

_Generated {now} by `scripts/render_calibration_benchmark.py` from a Railway-side
build of `scripts/build_calibration_benchmark.py`. Spec:
[`2026-05-16-discovery-lift-benchmark.md`](../superpowers/specs/2026-05-16-discovery-lift-benchmark.md) (note: companion to discovery_lift)._

## What this measures

Goldenmatch's `__match_score__` is opaque — a score of 0.85 doesn't necessarily
mean "85% chance these are the same entity." This benchmark uses **DOB-year
agreement** as external supervision: pairs where both sides carry a
date-of-birth that *agrees on the year* are positives; pairs where both sides
carry a DOB but the years *disagree* are negatives (same name, different
person). DOB enrichment is upstream of the name score — independent signal.

- **Positive class** ({s["n_positives"]:,} pairs): `dob_match == "both_present_year_match"`
  in `matched_dob_scored.csv`.
- **Negative class** ({s["n_negatives"]:,} pairs, sampled from {s["neg_pool_size"]:,}):
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
| Brier score (lower better) | {raw["brier"]:.4f} | {cal["brier"]:.4f} | {imp["brier_pct"]:+.1f}% |
| Log-loss (lower better) | {raw["log_loss"]:.4f} | {cal["log_loss"]:.4f} | {imp["log_loss_pct"]:+.1f}% |
| Expected calibration error (lower better) | {raw["ece"]:.4f} | {cal["ece"]:.4f} | {imp["ece_pct"]:+.1f}% |

The Brier-score improvement is the proper-scoring-rule reading: how much
better-calibrated the probabilities are once mapped through the
isotonic regression. ECE is the operator-readable version: "on average,
the calibrated score is off by X points of probability."

PAV produced **{s["n_checkpoints"]:,} monotone segments** mapping raw → calibrated.

## Raw reliability table (before calibration)

Each row is a score-decile bin: how many pairs fall in that bin, the mean
raw score within the bin, and the actual fraction of LEI-matches within
the bin. A perfectly calibrated raw score would have `Gap = 0` everywhere
— `Frac positive` equals `Mean score`.

{_bin_table(bins, "raw")}

## Calibrated reliability table (after PAV)

Same bins, but using the calibrated probability. Gap should be smaller
across the board — that's what isotonic regression buys us.

{_bin_table(bins, "cal")}

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
   {s["n_positives"]:,} positives there's no out-of-fold cross-validation. The
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

uv run python scripts/render_calibration_benchmark.py \\
    --metrics docs/reports/data/calibration_metrics.parquet \\
    --summary docs/reports/data/calibration_summary.json \\
    --out docs/reports/calibration_benchmark.md
```

Or trigger `.github/workflows/build-calibration-benchmark.yml` for the
end-to-end refresh.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
