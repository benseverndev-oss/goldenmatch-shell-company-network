# Adversarial-robustness benchmark

_Generated 2026-05-17 02:01 UTC from `processed/adversarial_benchmark.parquet` + summary JSON.
Companion to [`baseline_comparison.md`](baseline_comparison.md) and
[`discovery_lift.md`](discovery_lift.md). Specifically tests the
**threat model** documented in [`methodology.md` §1.5](../paper/methodology.md)._

## Setup

- **Anchor set**: 500-anchor sample of B3 rare-anchor names from `discovery_lift.parquet` (full B3 population: 3,838).
- **Per anchor**: apply each of 4 perturbation strategies → 2,000 total perturbed pairs evaluated.
- **Recovery test**:
  - **B2** = `normalize_company_name(perturbed) == anchor`. The normalize-then-exact-match defense.
  - **B6** = `rapidfuzz.token_set_ratio(perturbed, anchor) ≥ 85`. Naive fuzzy match.
- **Perturbations apply to anchor names directly** (not to anchor *records*), so this tests "if an adversary submitted a perturbed name to the system, would the system recognise it as the original anchor?" Real-world adversaries control names at registration time — this benchmark models that.

## Per-perturbation recovery

| Perturbation | What it models | B2 (normalize) | B6 (fuzzy ≥ 85) | B6 mean score |
|---|---|---:|---:|---:|
| **honorific_insertion** | Prepend mr/ms/dr/sheikh. Adversary inflates salutation between registries. | `··········` 0.0% | `██████████` 99.8% | 98.3 |
| **transliteration** | Char-level substitution (i↔y, kh↔h, sh↔sch, ts↔z). Models slavic/arabic transliteration variance. | `··········` 2.4% | `██████████` 96.0% | 92.4 |
| **suffix_mutation** | Swap a legal suffix (ltd ↔ limited ↔ llc ↔ inc). Adversary registers in a different legal form. | `████████··` 80.2% | `██████████` 100.0% | 100.0 |
| **token_reorder_drop** | Shuffle middle tokens; drop one if ≥4 tokens. Adversary uses partial-name variants. | `█████████·` 87.2% | `██████████` 100.0% | 100.0 |


**Reading.** Lower B2 = the normalize layer fails against that adversary
move. Lower B6 = even fuzzy match fails. The honest interpretation:

- The pipeline's normalize layer is **a partial defense, not a complete one**.
  It defeats suffix mutation (~87% recovery) by design, but **fails completely against
  honorific insertion** (the source-table `normalize_company_name`
  doesn't strip "Mr"/"Ms"/"Dr"; honorific stripping is only done at
  render time in the dossier pipeline, which means the rare-officer
  filter sees "mr francisco lopes filho" and "francisco lopes filho"
  as separate keys).
- **Transliteration is the strongest adversarial move.** With character-level
  substitutions matching real slavic/arabic transliteration variance,
  the normalize layer recovers only 2% of cases. Fuzzy at threshold 85
  catches most (96%) but at the cost of high false-positive risk
  on common names.
- **B6 fuzzy match is robust to ~all perturbations** at threshold 85, but
  that robustness is a double-edged sword. The same threshold that survives
  honorific insertion also matches "Mark Taylor" to dozens of unrelated
  people. There's no free lunch here.

## Worked examples

A handful of perturbed pairs per category. Failures listed first so the
reader can see what defeats the system.

### honorific_insertion

| Anchor | Perturbed (raw) | Perturbed (normalized) | B2 recovers? | B6 score |
|---|---|---|:---:|---:|
| `scott john wilcox` | `mr scott john wilcox` | `mr scott john wilcox` | ✗ | 100 |
| `mark anthony sammut` | `ms mark anthony sammut` | `ms mark anthony sammut` | ✗ | 100 |
| `jose alberto rodriguez rodriguez` | `sir jose alberto rodriguez rodriguez` | `sir jose alberto rodriguez rodriguez` | ✗ | 100 |

### transliteration

| Anchor | Perturbed (raw) | Perturbed (normalized) | B2 recovers? | B6 score |
|---|---|---|:---:|---:|
| `scott john wilcox` | `scott john wylcox` | `scott john wylcox` | ✗ | 94 |
| `mark anthony sammut` | `mark anthoni sammut` | `mark anthoni sammut` | ✗ | 94 |
| `jose alberto rodriguez rodriguez` | `jose alberto rodryguez rodriguez` | `jose alberto rodryguez rodriguez` | ✗ | 100 |
| `jean jacques meunier` | `jean jacques meunier` | `jean jacques meunier` | ✓ | 100 |
| `mr karan mehta` | `mr karan mehta` | `mr karan mehta` | ✓ | 100 |
| `mr micheal porter` | `mr micheal porter` | `mr micheal porter` | ✓ | 100 |

### suffix_mutation

| Anchor | Perturbed (raw) | Perturbed (normalized) | B2 recovers? | B6 score |
|---|---|---|:---:|---:|
| `scott john wilcox` | `scott john wilcox co` | `scott john wilcox co` | ✗ | 100 |
| `jose alberto rodriguez rodriguez` | `jose alberto rodriguez rodriguez co` | `jose alberto rodriguez rodriguez co` | ✗ | 100 |
| `jorg gerold bucherer` | `jorg gerold bucherer co` | `jorg gerold bucherer co` | ✗ | 100 |
| `mark anthony sammut` | `mark anthony sammut inc` | `mark anthony sammut` | ✓ | 100 |
| `bruno da silva` | `bruno da silva inc` | `bruno da silva` | ✓ | 100 |
| `chen ming tang` | `chen ming tang corporation` | `chen ming tang` | ✓ | 100 |

### token_reorder_drop

| Anchor | Perturbed (raw) | Perturbed (normalized) | B2 recovers? | B6 score |
|---|---|---|:---:|---:|
| `jose alberto rodriguez rodriguez` | `jose rodriguez rodriguez` | `jose rodriguez rodriguez` | ✗ | 100 |
| `mr firoz amirali jafar` | `mr firoz jafar` | `mr firoz jafar` | ✗ | 100 |
| `mirlene helen loraine taljaard` | `mirlene helen taljaard` | `mirlene helen taljaard` | ✗ | 100 |
| `scott john wilcox` | `scott john wilcox` | `scott john wilcox` | ✓ | 100 |
| `mark anthony sammut` | `mark anthony sammut` | `mark anthony sammut` | ✓ | 100 |
| `bruno da silva` | `bruno da silva` | `bruno da silva` | ✓ | 100 |


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

uv run python scripts/render_adversarial_benchmark.py \
    --parquet docs/reports/data/adversarial_benchmark.parquet \
    --summary docs/reports/data/adversarial_benchmark_summary.json \
    --out docs/reports/adversarial_benchmark.md
```

Or trigger `.github/workflows/build-adversarial-benchmark.yml`.
