# Baseline comparison — vs ICIJ search, naive fuzzy, and analyst time

_Generated 2026-05-17 01:35 UTC from `processed/baseline_comparison.parquet` + summary JSON.
Companion to [`discovery_lift.md`](discovery_lift.md): that report compares
nested goldenmatch baselines; this one compares **against tools an analyst
might actually use today**._

## Setup

- **Anchor set under evaluation**: a 500-anchor sample of the
  B3 rare-filtered tier from `discovery_lift.parquet` (full B3 population: 3,838;
  extrapolation factor: ×7.676). Sampling is deterministic with `--seed 42`.
- **Fuzzy threshold**: rapidfuzz `token_set_ratio` ≥ 85/100. Same threshold for B5 and B6.
- **Per-source name indexes**: `normalized_name` from `person_entities.parquet` per source.

## 1. ICIJ-search-equivalent coverage (B5)

> Approximates ICIJ Offshore Leaks Database's name search: fuzzy-match each
> anchor against the local ICIJ name index. **A journalist using ICIJ DB
> alone** would see one of those records as a starting point, but **no
> overlay** against UK PSC / OS / GLEIF (ICIJ doesn't ingest them).

| Metric | Value |
|---|---:|
| Anchors with ≥1 ICIJ fuzzy match | **465** of 500 (93.0%) |
| Anchors invisible to ICIJ search | **35** (7.0%) |

**Structural finding:** even when ICIJ search returns a record for the
name, it cannot show the journalist that the same name also appears in UK
PSC / OS / GLEIF. The cross-source overlay is **0/500 reachable** through
ICIJ search alone, regardless of fuzzy-match success.

## 2. Naive fuzzy match across sources (B6)

> The fuzzy-match equivalent of B2's exact-after-normalize comparison.
> Approximates "what would a generic fuzzy-dedupe tool (rapidfuzz / dedupe.io
> / Splink-without-blocking) find without our normalize + suffix-strip
> pipeline."

| Metric | Value |
|---|---:|
| Anchors fuzzy-matched in ≥2 sources | **500** (100.0%) |
| Anchors fuzzy-matched in ≥3 sources | 292 |

Per-source-count distribution of the sample:

| Sources matched | Anchors |
|---:|---:|
| 2 | 208 |
| 3 | 292 |


**Reading**: at threshold 85/100, naive fuzzy recovers
100.0% of B3's cross-source overlaps. The remaining
0.0% require the legal-suffix-strip / ASCII-fold
pipeline of B2 (see `discovery_lift.md`). The fuzzy baseline also produces
false-positive hits not counted here — token-set-ratio at 0.85 will match
"Mark Taylor" to dozens of unrelated entities. The discovery-lift report
quantifies the precision side via `max_per_source` filtering.

## 3. Analyst review reduction (model)

> **This section is a model, not a measurement.** Per-source wall-clock
> estimates are operator priors based on routine investigative-journalism
> workflow assumptions; treat them as a Fermi estimate.

### Per-anchor cost model

| Step | Estimate |
|---|---:|
| Manual UI query (each of 4 sources) | 30s × 4 = 120s |
| Manual cross-reference (compare + notes) | 120s |
| **Manual total per anchor** | **240s** |
| Pipeline: dossier read + verification follow-up | 90s |
| **Pipeline total per anchor** | **90s** |

Manual sources assumed: ICIJ DB, Companies House, OpenSanctions, GLEIF.

### Extrapolated to the B3 population

| Workload | Manual baseline | Pipeline | Reduction |
|---|---:|---:|---:|
| Per-anchor seconds | 240 | 90 | ×2.7 |
| Total for B3 (3,838 anchors) | **255.9 hours** | **96.0 hours** | **62.5%** |

For the top-tier 50 dossier set specifically, the equivalent
manual workload is 200.0 minutes vs. the pipeline's
75.0 minutes.

### Caveats

1. **The model ignores false-positive cost.** A journalist running manual
   queries also has to discard irrelevant hits — that time is rolled into
   the cross-reference estimate, but the value depends on the name. Common
   names cost more.
2. **The model assumes the analyst knows what to query**. The pipeline's
   ranked candidate list pre-selects names worth investigating; the manual
   baseline doesn't. If you include "time to decide which names to
   investigate," the manual cost is higher than reported.
3. **No social loafing / context-switching cost**. Real investigators
   batch and switch between tasks; this model assumes serial single-anchor
   attention. Both numbers are floor estimates.

## What this benchmark adds vs `discovery_lift.md`

| Question | discovery_lift answers | this report answers |
|---|---|---|
| Does the normalize layer rescue recall? | Yes, +11% (B1→B2). | — |
| What's the overlap with a fuzzy-dedupe tool? | — | 100% of B3 reachable by naive fuzzy. |
| What about a journalist using ICIJ DB? | — | 93% of B3 surfaces in ICIJ search, but 0% with the cross-source overlay. |
| How much human time is saved? | — | ~62.5% reduction at scale; ×2.7 faster per anchor. |

## Reproduce

```bash
just job-run build_baseline_comparison
just job-fetch processed/baseline_comparison.parquet docs/reports/data/
just job-fetch processed/baseline_comparison_summary.json docs/reports/data/

uv run python scripts/render_baseline_comparison.py \
    --parquet docs/reports/data/baseline_comparison.parquet \
    --summary docs/reports/data/baseline_comparison_summary.json \
    --out docs/reports/baseline_comparison.md
```

Or trigger `.github/workflows/build-baseline-comparison.yml`.
