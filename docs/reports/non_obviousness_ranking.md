# Non-obviousness ranking

_Generated 2026-05-17 04:32 UTC from `processed/non_obviousness_scores.parquet`.
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
| `rarity` | 0.30 | Inverse log of how many times the normalized name appears in the corpus. Rarer = harder to dismiss as a coincidence. |
| `jurisdiction_span` | 0.25 | Distinct jurisdictions touched by linked companies. More spread = less easily explained by a single registry environment. |
| `graph_surprise` | 0.20 | Edge density of the anchor's 1-hop ICIJ neighbourhood. Densely-interconnected sub-networks are atypical. |
| `shared_intermediary` | 0.15 | How many *other* dossier anchors share an ICIJ intermediary with this anchor. Captures the "shared corporate secretary" pattern. |
| `pattern_uniqueness` | 0.10 | How rare this anchor's (source-set, jurisdiction-set) combination is across the dossier set. |

## Distribution

| Statistic | Score |
|---|---:|
| Anchors scored | 50 |
| Min | 0.241 |
| Median | 0.394 |
| Mean | 0.402 |
| Max | 0.533 |

## Top 25 by non-obviousness

| Rank | Name | Score | Rarity | Juris span | Graph surprise | Shared int. | Pattern unique |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | philippe le gall | **0.533** | 0.57 | 1 | 1.00 | 0 | 0.78 |
| 2 | javed ali khan | **0.511** | 0.57 | 1 | 1.00 | 0 | 0.56 |
| 3 | john o connor | **0.508** | 0.49 | 1 | 1.00 | 0 | 0.78 |
| 4 | david mark cooper | **0.507** | 0.52 | 1 | 1.00 | 0 | 0.67 |
| 5 | nils peter grut | **0.507** | 0.52 | 1 | 1.00 | 0 | 0.67 |
| 6 | patrick gerard mckillen | **0.507** | 0.52 | 1 | 1.00 | 0 | 0.67 |
| 7 | calvin edward ayre | **0.507** | 0.52 | 1 | 1.00 | 0 | 0.67 |
| 8 | erbil mehmet arkin | **0.507** | 0.52 | 1 | 1.00 | 0 | 0.67 |
| 9 | muhammad umar khan | **0.496** | 0.52 | 1 | 1.00 | 0 | 0.56 |
| 10 | michael john rooney | **0.496** | 0.52 | 1 | 1.00 | 0 | 0.56 |
| 11 | james michael green | **0.479** | 0.52 | 1 | 0.80 | 0 | 0.78 |
| 12 | michael o sullivan | **0.466** | 0.57 | 1 | 0.67 | 0 | 0.78 |
| 13 | ali raza khan | **0.461** | 0.57 | 0 | 1.00 | 0 | 0.89 |
| 14 | mohamed nazir bin abdul razak | **0.446** | 0.52 | 1 | 1.00 | 0 | 0.06 |
| 15 | keith roger neville | **0.446** | 0.52 | 1 | 1.00 | 0 | 0.06 |
| 16 | ryan john lee | **0.444** | 0.57 | 1 | 0.67 | 0 | 0.56 |
| 17 | abdul hamid khan | **0.444** | 0.57 | 1 | 0.67 | 0 | 0.56 |
| 18 | ms bin zhang | **0.441** | 0.52 | 0 | 1.00 | 0 | 0.83 |
| 19 | peter kevin perry | **0.427** | 0.52 | 1 | 0.60 | 0 | 0.67 |
| 20 | luiz alberto rodrigues | **0.411** | 0.57 | 1 | 0.50 | 0 | 0.56 |
| 21 | david james mason | **0.403** | 0.57 | 1 | 0.35 | 0 | 0.78 |
| 22 | stephen john wheeler | **0.396** | 0.52 | 1 | 0.50 | 0 | 0.56 |
| 23 | mr vadim samoylenko | **0.396** | 0.52 | 1 | 0.50 | 0 | 0.56 |
| 24 | rajesh kumar gupta | **0.396** | 0.52 | 1 | 0.50 | 0 | 0.56 |
| 25 | alan richard taylor | **0.394** | 0.57 | 0 | 0.67 | 0 | 0.89 |


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

uv run python scripts/render_non_obviousness.py \
    --parquet docs/reports/data/non_obviousness_scores.parquet \
    --summary docs/reports/data/non_obviousness_summary.json \
    --out docs/reports/non_obviousness_ranking.md
```

Or trigger `.github/workflows/build-non-obviousness.yml`.
