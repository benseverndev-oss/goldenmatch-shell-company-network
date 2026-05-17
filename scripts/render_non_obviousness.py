"""Render docs/reports/non_obviousness_ranking.md from the scoring parquet."""

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
    out: Path = typer.Option(Path("docs/reports/non_obviousness_ranking.md"), "--out"),
) -> None:
    df = pl.read_parquet(parquet).sort("non_obviousness_score", descending=True)
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    dist = s["score_distribution"]
    w = s["weights"]

    body = f"""# Non-obviousness ranking

_Generated {now} from `processed/non_obviousness_scores.parquet`.
Companion to [`exposes_candidates.md`](exposes_candidates.md): the
exposé candidates index orders dossiers by **novelty** (low web-coverage +
high shell density). This file orders the same 50 anchors by
**non-obviousness** — the structural rarity of the cross-source pattern,
independent of whether the entity has been web-indexed._

## Why a second ranking

Novelty scoring asks: "is this lead unreported?"
Non-obviousness scoring asks: "is the underlying pattern structurally
unusual?" The two questions are orthogonal — a heavily-reported entity
(low novelty) can still have a structurally non-obvious cross-source
shape (high non-obviousness), and vice versa.

For a journalist deciding which dossiers to investigate first, the
**intersection** of both rankings is the highest-value zone.

## Score components (per anchor)

| Component | Weight | What it measures |
|---|---:|---|
| `rarity` | {w["rarity"]:.2f} | Inverse log of how many times the normalized name appears in the corpus. Rarer = harder to dismiss as a coincidence. |
| `jurisdiction_span` | {w["jurisdiction_span"]:.2f} | Distinct jurisdictions touched by linked companies. More spread = less easily explained by a single registry environment. |
| `graph_surprise` | {w["graph_surprise"]:.2f} | Edge density of the anchor's 1-hop ICIJ neighbourhood. Densely-interconnected sub-networks are atypical. |
| `shared_intermediary` | {w["shared_intermediary"]:.2f} | How many *other* dossier anchors share an ICIJ intermediary with this anchor. Captures the "shared corporate secretary" pattern. |
| `pattern_uniqueness` | {w["pattern_uniqueness"]:.2f} | How rare this anchor's (source-set, jurisdiction-set) combination is across the dossier set. |

## Distribution

| Statistic | Score |
|---|---:|
| Anchors scored | {s["n_anchors"]:,} |
| Min | {dist["min"]:.3f} |
| Median | {dist["median"]:.3f} |
| Mean | {dist["mean"]:.3f} |
| Max | {dist["max"]:.3f} |

## Top 25 by non-obviousness

| Rank | Name | Score | Rarity | Juris span | Graph surprise | Shared int. | Pattern unique |
|---:|---|---:|---:|---:|---:|---:|---:|
"""

    for i, r in enumerate(df.head(25).iter_rows(named=True), start=1):
        body += (
            f"| {i} | {r['rare_name']} | **{float(r['non_obviousness_score']):.3f}** | "
            f"{float(r['rarity']):.2f} | {int(r['jurisdiction_span'])} | "
            f"{float(r['graph_surprise']):.2f} | {int(r['shared_intermediary'])} | "
            f"{float(r['pattern_uniqueness']):.2f} |\n"
        )

    body += """

## Honest reading

The score is **operator-weighted and unsupervised**. We have no ground-
truth for "non-obviousness"; the weights in the table above are priors,
not learned. A v2 would either (a) calibrate against expert ratings
from a small panel of investigative journalists, or (b) treat this
score as a *retrieval* signal and let the user re-weight components
interactively.

For now: use this ranking as a re-ordering filter alongside the
exposé-candidates novelty ranking. Anchors that score in the top quartile
on *both* are the strongest leads. Disagreements (high on one, low on
the other) are interesting in their own right — they highlight cases
where conventional reportability and structural distinctiveness pull
in different directions.

## What this report does NOT prove

1. **No ground truth for non-obviousness.** The five components are
   investigator-defensible priors, but the linear-weighted-sum
   combination is operator choice. A reviewer can reasonably ask
   "why these weights?"
2. **Single-snapshot graph.** `graph_surprise` is computed on the
   2026-05-16 corpus snapshot only. A temporally-evolving signal would
   be stronger.
3. **`shared_intermediary` is ICIJ-only.** UK PSC and OS person-to-
   company relations aren't materialised in this repo, so the metric
   only fires on ICIJ-source anchors.

## Reproduce

```bash
just job-run build_non_obviousness_score
just job-fetch processed/non_obviousness_scores.parquet docs/reports/data/
just job-fetch processed/non_obviousness_summary.json docs/reports/data/

uv run python scripts/render_non_obviousness.py \\
    --parquet docs/reports/data/non_obviousness_scores.parquet \\
    --summary docs/reports/data/non_obviousness_summary.json \\
    --out docs/reports/non_obviousness_ranking.md
```

Or trigger `.github/workflows/build-non-obviousness.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
