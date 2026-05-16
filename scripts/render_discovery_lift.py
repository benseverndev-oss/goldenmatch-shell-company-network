"""Render docs/reports/discovery_lift.md from the Railway-produced benchmark.

Templates only — no compute. Spec:
docs/superpowers/specs/2026-05-16-discovery-lift-benchmark.md
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
    parquet: Path = typer.Option(..., "--parquet", help="discovery_lift.parquet"),
    summary: Path = typer.Option(..., "--summary", help="discovery_lift_summary.json"),
    out: Path = typer.Option(
        Path("docs/reports/discovery_lift.md"), "--out", help="Markdown destination."
    ),
) -> None:
    df = pl.read_parquet(parquet)
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    t = s["tiers"]
    d = s["deltas"]
    r = s["reachable_by_tier"]

    body = f"""# Discovery-lift benchmark

_Generated {now} by `scripts/render_discovery_lift.py` from a Railway-side
build of `scripts/build_discovery_lift.py`. Spec:
[`2026-05-16-discovery-lift-benchmark.md`](../superpowers/specs/2026-05-16-discovery-lift-benchmark.md)._

## What this measures

How much of the cross-source-overlap signal the goldenmatch + dossier
pipeline surfaces vs. simpler baselines. The repo's earlier reports
demonstrate _methodology_; this one quantifies _lift_.

## Tier-by-tier anchor counts

| Tier | What it does | Multi-source anchors |
|---|---|---:|
| **B1** Naive case-fold pairwise | Lowercase + whitespace-strip only. No legal-suffix removal, no ASCII fold. | {t["B1_naive_casefold"]["n_anchors_multisource"]:,} |
| **B2** Goldenmatch-normalized | Adds `normalize_company_name` — legal-suffix strip, ASCII fold, tokenize. | {t["B2_goldenmatch_normalize"]["n_anchors_multisource"]:,} |
| **B3** + Rare-filter | Drops common-name explosions (`max_per_source ≤ 2`, `n_tokens ≥ 3`). | {t["B3_rare_filtered"]["n_anchors_multisource"]:,} |
| **B4** + Dossier pipeline | B3 seeds enriched with 2-hop ICIJ graph + sanctions overlay. | {t["B4_dossier_pipeline"]["n_anchors_multisource"]:,} |

## Tier deltas (incremental gain)

| Step | Delta | Reading |
|---|---:|---|
| B1 → B2 | {d["B2_minus_B1"]:+,} | Anchors rescued by goldenmatch's normalization step (legal-suffix strip + ASCII fold). The recall lift. |
| B2 → B3 | {d["B3_minus_B2"]:+,} | Anchors *cut* by the rare-filter. The precision move — common-name explosions removed. Negative by design. |
| B3 → B4 | {d["B4_minus_B3"]:+,} | B4 is the top-N sample (default 50) of B3 enriched with the 2-hop graph walk. The negative delta is the top-N cap, not a real precision loss. The lift here is qualitative (linked companies + addresses + sanctions adjacency), not numerical. Bump `--top-n` to operate at B3's full scale. |

**Anchors with investigative signal at B4:**
{t["B4_dossier_pipeline"]["n_anchors_with_signal"]:,} of {t["B4_dossier_pipeline"]["n_anchors_multisource"]:,} dossier seeds have ≥1 linked company surfaced by the ICIJ 2-hop walk
({t["B4_dossier_pipeline"]["n_anchors_with_sanctions"]:,} with sanctions adjacency hit).

## Reachability cross-tabulation

Of the **union of all tiers' multi-source anchors** ({df.height:,} distinct names total):

- **{r["b1_only"]:,}** are reachable only by the naive baseline. These are likely *spurious* — names that happen to match across sources without the normalize step but that goldenmatch deliberately rejects (e.g. variants where one side has an unstripped legal suffix that B1 keeps and B2 strips, creating a difference).
- **{r["b2_only"]:,}** are reachable at B2 but not B1. These are the *recall lift* — real cross-source overlaps that naive case-folding misses because of legal-suffix differences or ASCII-fold issues.
- **{r["b4_seeds_naive_unreachable"]:,}** of the {t["B4_dossier_pipeline"]["n_anchors_multisource"]} dossier seeds would be **invisible to a naive baseline**. That's the headline lift number for the dossier pipeline specifically.

## Honest framing

- **The biggest absolute lift is at the B1→B2 step**, not at the dossier walk. Normalization is what does most of the work. The graph walk's contribution is qualitative (richer dossiers), not quantitative (more anchors).
- The B2→B3 reduction is **intentional**. Without it, the dossier set is dominated by common-name buckets ("Mark Taylor", "Anthony Smith") that carry zero investigative signal.
- "Reachable at tier N" here means **"the name string appears in ≥2 sources at that tier"** — it does NOT mean "a journalist sitting in a single source's UI would find the cross-source overlap." That stronger claim needs separate work (the prior-art comparison doc covers it qualitatively).

## What this benchmark does NOT prove

1. That the dossier pipeline finds *previously-unreported beneficial owners*. It finds *cross-source overlaps not surfaced by simpler matching*. Verification of newness per-lead requires manual review or the firecrawl step in `build-exposes-candidates.yml`.
2. That goldenmatch is better than embedding-based or fuzzy matching. That's a different baseline class; would need a 5th tier (B5).
3. That this benchmark is reproducible across other corpora. It's specific to the ICIJ + OpenSanctions + UK PSC + GLEIF mix this repo ingests.

## Reproduce

```bash
# Railway:
just job-run build_discovery_lift
just job-fetch processed/discovery_lift.parquet docs/reports/data/
just job-fetch processed/discovery_lift_summary.json docs/reports/data/

# Render (anywhere):
uv run python scripts/render_discovery_lift.py \\
    --parquet docs/reports/data/discovery_lift.parquet \\
    --summary docs/reports/data/discovery_lift_summary.json \\
    --out docs/reports/discovery_lift.md
```

Or trigger `.github/workflows/build-discovery-lift.yml` for the end-to-end refresh.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
