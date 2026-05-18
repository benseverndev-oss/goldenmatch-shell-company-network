"""Render docs/reports/baseline_comparison.md from the Railway artifacts.

Pure templating. Reads baseline_comparison.parquet + baseline_comparison_summary.json.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    parquet: Path = typer.Option(..., "--parquet"),
    summary: Path = typer.Option(..., "--summary"),
    out: Path = typer.Option(Path("docs/reports/baseline_comparison.md"), "--out"),
) -> None:
    df = pl.read_parquet(parquet)
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    b5 = s["tiers"]["B5_icij_search_equivalent"]
    b6 = s["tiers"]["B6_naive_fuzzy_cross_source"]
    a = s["analyst_review_reduction"]
    a_total = a["totals"]
    a_model = a["model_assumptions"]

    # Per-anchor distribution for the fuzzy histogram in the report.
    src_dist = (df.group_by("b6_n_sources_fuzzy").len().sort("b6_n_sources_fuzzy")).to_dicts()

    body = f"""# Baseline comparison — vs ICIJ search, naive fuzzy, and analyst time

_Generated {now} from `processed/baseline_comparison.parquet` + summary JSON.
Companion to [`discovery_lift.md`](discovery_lift.md): that report compares
nested goldenmatch baselines; this one compares **against tools an analyst
might actually use today**._

## Setup

- **Anchor set under evaluation**: a {s["sample_size"]:,}-anchor sample of the
  B3 rare-filtered tier from `discovery_lift.parquet` (full B3 population: {s["b3_population"]:,};
  extrapolation factor: ×{s["extrapolation_factor"]}). Sampling is deterministic with `--seed 42`.
- **Fuzzy threshold**: rapidfuzz `token_set_ratio` ≥ {s["fuzzy_threshold"]}/100. Same threshold for B5 and B6.
- **Per-source name indexes**: `normalized_name` from `person_entities.parquet` per source.

## 1. ICIJ-search-equivalent coverage (B5)

> Approximates ICIJ Offshore Leaks Database's name search: fuzzy-match each
> anchor against the local ICIJ name index. **A journalist using ICIJ DB
> alone** would see one of those records as a starting point, but **no
> overlay** against UK PSC / OS / GLEIF (ICIJ doesn't ingest them).

| Metric | Value |
|---|---:|
| Anchors with ≥1 ICIJ fuzzy match | **{b5["n_anchors_with_icij_match"]:,}** of {s["sample_size"]:,} ({b5["fraction_of_sample"] * 100:.1f}%) |
| Anchors invisible to ICIJ search | **{s["sample_size"] - b5["n_anchors_with_icij_match"]:,}** ({(1 - b5["fraction_of_sample"]) * 100:.1f}%) |

**Structural finding:** even when ICIJ search returns a record for the
name, it cannot show the journalist that the same name also appears in UK
PSC / OS / GLEIF. The cross-source overlay is **0/{s["sample_size"]} reachable** through
ICIJ search alone, regardless of fuzzy-match success.

## 2. Naive fuzzy match across sources (B6)

> The fuzzy-match equivalent of B2's exact-after-normalize comparison.
> Approximates "what would a generic fuzzy-dedupe tool (rapidfuzz / dedupe.io
> / Splink-without-blocking) find without our normalize + suffix-strip
> pipeline."

| Metric | Value |
|---|---:|
| Anchors fuzzy-matched in ≥2 sources | **{b6["n_anchors_2_plus_sources"]:,}** ({b6["fraction_2plus_of_sample"] * 100:.1f}%) |
| Anchors fuzzy-matched in ≥3 sources | {b6["n_anchors_3_plus_sources"]:,} |

Per-source-count distribution of the sample:

| Sources matched | Anchors |
|---:|---:|
"""

    for row in src_dist:
        body += f"| {int(row['b6_n_sources_fuzzy'])} | {int(row['len']):,} |\n"

    body += f"""

**Reading**: at threshold {s["fuzzy_threshold"]}/100, naive fuzzy recovers
{b6["fraction_2plus_of_sample"] * 100:.1f}% of B3's cross-source overlaps. The remaining
{100 - b6["fraction_2plus_of_sample"] * 100:.1f}% require the legal-suffix-strip / ASCII-fold
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
| Manual UI query (each of {len(a_model["manual_sources"])} sources) | {a_model["per_manual_query_seconds"]}s × {len(a_model["manual_sources"])} = {a_model["per_manual_query_seconds"] * len(a_model["manual_sources"])}s |
| Manual cross-reference (compare + notes) | {a_model["per_cross_reference_seconds"]}s |
| **Manual total per anchor** | **{a["per_anchor_manual_seconds"]}s** |
| Pipeline: dossier read + verification follow-up | {a_model["per_pipeline_anchor_seconds"]}s |
| **Pipeline total per anchor** | **{a["per_anchor_pipeline_seconds"]}s** |

Manual sources assumed: {", ".join(a_model["manual_sources"])}.

### Extrapolated to the B3 population

| Workload | Manual baseline | Pipeline | Reduction |
|---|---:|---:|---:|
| Per-anchor seconds | {a["per_anchor_manual_seconds"]} | {a["per_anchor_pipeline_seconds"]} | ×{a_total["reduction_factor"]} |
| Total for B3 ({s["b3_population"]:,} anchors) | **{a_total["manual_hours_b3"]} hours** | **{a_total["pipeline_hours_b3"]} hours** | **{a_total["reduction_pct"]}%** |

For the top-tier {a["n_dossiers_top_tier"]:,} dossier set specifically, the equivalent
manual workload is {a["n_dossiers_top_tier"] * a["per_anchor_manual_seconds"] / 60:.1f} minutes vs. the pipeline's
{a["n_dossiers_top_tier"] * a["per_anchor_pipeline_seconds"] / 60:.1f} minutes.

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
| What's the overlap with a fuzzy-dedupe tool? | — | {b6["fraction_2plus_of_sample"] * 100:.0f}% of B3 reachable by naive fuzzy. |
| What about a journalist using ICIJ DB? | — | {b5["fraction_of_sample"] * 100:.0f}% of B3 surfaces in ICIJ search, but 0% with the cross-source overlay. |
| How much human time is saved? | — | ~{a_total["reduction_pct"]}% reduction at scale; ×{a_total["reduction_factor"]} faster per anchor. |

## Reproduce

```bash
just job-run build_baseline_comparison
just job-fetch processed/baseline_comparison.parquet docs/reports/data/
just job-fetch processed/baseline_comparison_summary.json docs/reports/data/

uv run python scripts/render_baseline_comparison.py \\
    --parquet docs/reports/data/baseline_comparison.parquet \\
    --summary docs/reports/data/baseline_comparison_summary.json \\
    --out docs/reports/baseline_comparison.md
```

Or trigger `.github/workflows/build-baseline-comparison.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
