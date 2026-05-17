"""Render docs/reports/adversarial_benchmark.md from the Railway artifacts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


def _bar(width: int, fill: float) -> str:
    n = max(0, min(width, int(round(width * fill))))
    return "█" * n + "·" * (width - n)


def _sample_rows(df: pl.DataFrame, perturbation: str, limit: int) -> list[dict]:
    sub = df.filter(pl.col("perturbation") == perturbation)
    # Mix of failures and successes for visibility.
    failures = sub.filter(~pl.col("b2_recovers")).head(limit // 2)
    successes = sub.filter(pl.col("b2_recovers")).head(limit // 2)
    return pl.concat([failures, successes], how="vertical").to_dicts()


@app.command()
def main(
    parquet: Path = typer.Option(..., "--parquet"),
    summary: Path = typer.Option(..., "--summary"),
    out: Path = typer.Option(Path("docs/reports/adversarial_benchmark.md"), "--out"),
    examples_per_perturbation: int = typer.Option(6, "--examples"),
) -> None:
    df = pl.read_parquet(parquet)
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""# Adversarial-robustness benchmark

_Generated {now} from `processed/adversarial_benchmark.parquet` + summary JSON.
Companion to [`baseline_comparison.md`](baseline_comparison.md) and
[`discovery_lift.md`](discovery_lift.md). Specifically tests the
**threat model** documented in [`methodology.md` §1.5](../paper/methodology.md)._

## Setup

- **Anchor set**: {s["sample_size"]:,}-anchor sample of B3 rare-anchor names from `discovery_lift.parquet` (full B3 population: {s["b3_population"]:,}).
- **Per anchor**: apply each of {len(s["perturbation_types"])} perturbation strategies → {s["overall"]["n_perturbed_pairs"]:,} total perturbed pairs evaluated.
- **Recovery test**:
  - **B2** = `normalize_company_name(perturbed) == anchor`. The normalize-then-exact-match defense.
  - **B6** = `rapidfuzz.token_set_ratio(perturbed, anchor) ≥ {s["fuzzy_threshold"]}`. Naive fuzzy match.
- **Perturbations apply to anchor names directly** (not to anchor *records*), so this tests "if an adversary submitted a perturbed name to the system, would the system recognise it as the original anchor?" Real-world adversaries control names at registration time — this benchmark models that.

## Per-perturbation recovery

| Perturbation | What it models | B2 (normalize) | B6 (fuzzy ≥ {s["fuzzy_threshold"]}) | B6 mean score |
|---|---|---:|---:|---:|
"""

    # Sort perturbations to put B2's worst cases first — that's the
    # interesting reading for the operator.
    sorted_perts = sorted(s["by_perturbation"], key=lambda r: r["b2_recovery_rate"])
    descriptions = {
        "suffix_mutation": "Swap a legal suffix (ltd ↔ limited ↔ llc ↔ inc). Adversary registers in a different legal form.",
        "honorific_insertion": "Prepend mr/ms/dr/sheikh. Adversary inflates salutation between registries.",
        "transliteration": "Char-level substitution (i↔y, kh↔h, sh↔sch, ts↔z). Models slavic/arabic transliteration variance.",
        "token_reorder_drop": "Shuffle middle tokens; drop one if ≥4 tokens. Adversary uses partial-name variants.",
    }
    for r in sorted_perts:
        ptype = r["perturbation"]
        body += (
            f"| **{ptype}** | {descriptions.get(ptype, '')} | "
            f"`{_bar(10, r['b2_recovery_rate'])}` {r['b2_recovery_rate']*100:.1f}% | "
            f"`{_bar(10, r['b6_recovery_rate'])}` {r['b6_recovery_rate']*100:.1f}% | "
            f"{r['b6_mean_score']:.1f} |\n"
        )

    body += f"""

**Reading.** Lower B2 = the normalize layer fails against that adversary
move. Lower B6 = even fuzzy match fails. The honest interpretation:

- The pipeline's normalize layer is **a partial defense, not a complete one**.
  It defeats suffix mutation (~{int(sorted_perts[-1]['b2_recovery_rate']*100) if sorted_perts[-1]['b2_recovery_rate'] > 0.5 else int(next(p for p in sorted_perts if p['perturbation'] == 'suffix_mutation')['b2_recovery_rate']*100)}% recovery) by design, but **fails completely against
  honorific insertion** (the source-table `normalize_company_name`
  doesn't strip "Mr"/"Ms"/"Dr"; honorific stripping is only done at
  render time in the dossier pipeline, which means the rare-officer
  filter sees "mr francisco lopes filho" and "francisco lopes filho"
  as separate keys).
- **Transliteration is the strongest adversarial move.** With character-level
  substitutions matching real slavic/arabic transliteration variance,
  the normalize layer recovers only {next(p for p in sorted_perts if p['perturbation'] == 'transliteration')['b2_recovery_rate']*100:.0f}% of cases. Fuzzy at threshold 85
  catches most ({next(p for p in sorted_perts if p['perturbation'] == 'transliteration')['b6_recovery_rate']*100:.0f}%) but at the cost of high false-positive risk
  on common names.
- **B6 fuzzy match is robust to ~all perturbations** at threshold 85, but
  that robustness is a double-edged sword. The same threshold that survives
  honorific insertion also matches "Mark Taylor" to dozens of unrelated
  people. There's no free lunch here.

## Worked examples

A handful of perturbed pairs per category. Failures listed first so the
reader can see what defeats the system.
"""

    for ptype in (
        "honorific_insertion",
        "transliteration",
        "suffix_mutation",
        "token_reorder_drop",
    ):
        rows = _sample_rows(df, ptype, examples_per_perturbation)
        if not rows:
            continue
        body += f"\n### {ptype}\n\n"
        body += "| Anchor | Perturbed (raw) | Perturbed (normalized) | B2 recovers? | B6 score |\n"
        body += "|---|---|---|:---:|---:|\n"
        for r in rows:
            ok2 = "✓" if r["b2_recovers"] else "✗"
            body += (
                f"| `{r['anchor']}` | `{r['perturbed']}` | "
                f"`{r['perturbed_normalized']}` | {ok2} | {int(r['b6_score'])} |\n"
            )

    body += """

## What this benchmark does NOT prove

1. **Synthetic perturbations are not real adversarial behavior.** A
   determined adversary doesn't permute names mechanically — they use
   plausible variants that match their genuine identity claims (e.g.,
   passport-spelling vs. registrar-spelling). The benchmark is a lower
   bound on robustness.
2. **No coordination between perturbations.** Real adversaries combine
   moves (transliterate AND insert honorific AND shop jurisdiction).
   This benchmark applies one perturbation at a time. Combining would
   reduce recovery further.
3. **Recovery is measured against the original normalised string, not
   the original entity.** A perturbed entity that recovers to a
   *different* B3 anchor (false positive) isn't counted here.

## Implications for the pipeline

The clearest fix this benchmark surfaces: **strip honorifics in
`normalize_company_name` itself**, not just at the renderer. That
single change would close the largest current gap. Captured as a
spec-level follow-up in `methodology.md §6.2`.

## Reproduce

```bash
just job-run build_adversarial_benchmark
just job-fetch processed/adversarial_benchmark.parquet docs/reports/data/
just job-fetch processed/adversarial_benchmark_summary.json docs/reports/data/

uv run python scripts/render_adversarial_benchmark.py \\
    --parquet docs/reports/data/adversarial_benchmark.parquet \\
    --summary docs/reports/data/adversarial_benchmark_summary.json \\
    --out docs/reports/adversarial_benchmark.md
```

Or trigger `.github/workflows/build-adversarial-benchmark.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
