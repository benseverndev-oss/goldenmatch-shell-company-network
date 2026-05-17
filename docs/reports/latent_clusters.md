# Latent-cluster mining — anomalous communities on the full ICIJ graph

_Generated 2026-05-17 19:07 UTC from `processed/latent_clusters.parquet`. Companion to
[`confidence_graph.md`](confidence_graph.md): that report anchors on the
dossier seed set; this one mines the **entire ICIJ relationship graph**
with no seed bias._

## What this is

The first lead-generation output that doesn't require a journalist to know
where to look. Louvain community detection on the full 3.3M-edge ICIJ
corpus (filtered to high-credibility structural edges + nodes with
degree ≥ 5), then anomaly-scoring every community by the combination
of features below.

## Pipeline

| Step | Outcome |
|---|---:|
| High-credibility ICIJ edges | 1,072,355 (after kind filter) |
| Nodes at degree ≥ 3 | 513,664 |
| Communities found | 10,262 |
| Communities with size ≥ 3 (eligible) | 6,606 |
| Top-N written | 200 |

**Edge kinds kept** (high-credibility only): `intermediary_of`, `officer_of`, `registered_address`, `same_as`, `same_company_as`, `same_id_as`, `shareholder_of`, `underlying`. Inferred kinds (`same_name_as`, `similar`) excluded — they'd otherwise dominate communities with name-collision noise.

## Anomaly score components

| Component | Weight | Reading |
|---|---:|---|
| `jurisdiction_span` | 0.30 | More distinct jurisdictions = harder to explain by a single registrar's local activity |
| `sanctions_density` | 0.25 | Fraction of community members whose normalized name appears in the sanctions overlay alias set |
| `size_sweet_spot` | 0.20 | Triangular: peaks at ~50 members; tiny clusters and giant hubs are both deprioritised |
| `intermediary_density` | 0.15 | Fraction of internal edges that are `intermediary_of` — the "shared corporate secretary" signature |
| `address_density` | 0.10 | Fraction of internal edges that are `registered_address` — the "shell-cluster at a shared address" signature |

## Score distribution

| Statistic | Anomaly score |
|---|---:|
| Min | 0.273 |
| Median | 0.312 |
| Max | 0.454 |

## Top 25 anomalous communities

| Rank | Community | Size | Jurisdictions | Sanctioned | Int. density | Addr. density | Anomaly |
|---:|---:|---:|---|---:|---:|---:|---:|
| 1 | 1878 | 78 | pa;us;vg | 0 | 0.00 | 0.85 | **0.454** |
| 2 | 377 | 115 | cy;vg | 0 | 1.00 | 0.00 | **0.444** |
| 3 | 3557 | 107 | hk;vg | 0 | 0.94 | 0.03 | **0.440** |
| 4 | 308 | 64 | uk;vg | 0 | 0.68 | 0.09 | **0.426** |
| 5 | 2762 | 173 | hk;mt;vg | 1 | 0.50 | 0.13 | **0.420** |
| 6 | 125 | 54 | vg | 0 | 1.00 | 0.00 | **0.408** |
| 7 | 255 | 54 | vg | 0 | 1.00 | 0.00 | **0.408** |
| 8 | 215 | 66 | vg | 0 | 1.00 | 0.00 | **0.404** |
| 9 | 289 | 66 | vg | 0 | 1.00 | 0.00 | **0.404** |
| 10 | 173 | 68 | vg | 0 | 1.00 | 0.00 | **0.403** |
| 11 | 450 | 46 | hk;vg | 0 | 0.62 | 0.04 | **0.401** |
| 12 | 2073 | 74 | gb;vg | 0 | 0.00 | 0.86 | **0.397** |
| 13 | 2125 | 1771 | ae;ch;gb;hk;us;vg | 3 | 0.00 | 0.94 | **0.394** |
| 14 | 3401 | 4014 | cy;hk;mt;nz;uk;uy;vg | 5 | 0.58 | 0.06 | **0.393** |
| 15 | 3423 | 100 | nz;vg | 0 | 0.58 | 0.05 | **0.392** |
| 16 | 184 | 57 | vg | 0 | 0.90 | 0.00 | **0.392** |
| 17 | 1740 | 60 | vg | 0 | 0.89 | 0.02 | **0.391** |
| 18 | 267 | 76 | vg | 0 | 0.94 | 0.00 | **0.390** |
| 19 | 1308 | 58 | vg | 0 | 0.85 | 0.05 | **0.390** |
| 20 | 3737 | 113 | vg | 0 | 0.98 | 0.00 | **0.382** |
| 21 | 2679 | 50 | vg | 0 | 0.80 | 0.02 | **0.381** |
| 22 | 411 | 70 | vg | 0 | 0.81 | 0.04 | **0.377** |
| 23 | 134 | 117 | vg | 0 | 0.94 | 0.01 | **0.375** |
| 24 | 708 | 108 | vg | 0 | 0.81 | 0.16 | **0.374** |
| 25 | 201 | 46 | vg | 0 | 0.82 | 0.00 | **0.367** |


## Reading

The top communities are the **graph's own recommendations** for what to
investigate, derived without any seed bias. A community ranked highly here
is *not* a community that contains a dossier-pipeline anchor; it's a
structurally unusual cluster the data surfaces on its own.

Three patterns the top-25 tend to fit:

- **Cross-jurisdiction intermediary hubs.** High `jurisdiction_span` and
  near-1.0 `intermediary_density` = formation-agent service clusters
  that bridge registries — these are the "shared corporate secretary"
  pattern across multiple offshore venues.
- **Sanctions-adjacent shell clusters.** Any community with
  `n_sanctioned ≥ 1` is worth opening — at the size-50 sweet spot it
  often means a sanctioned principal plus a fan of related shells the
  sanction list itself hasn't enumerated.
- **Pure-jurisdiction shell groupings.** Single-jurisdiction (often `vg`)
  communities at the size sweet spot with high intermediary density =
  classic BVI shell-pool registered through one formation agent.

## What this report does NOT prove

1. **Anomaly is a structural signal, not investigative confirmation.**
   Top-ranked communities still need human review; structural
   unusualness ≠ guilt.
2. **Single-jurisdiction clusters dominate the top.** Of the eligible
   communities, most span only one jurisdiction. This is a property of
   the corpus (Panama Papers / Paradise / Pandora ingest is heaviest
   on BVI/Bermuda/Panama), not the metric.
3. **Sanctions match is via normalized-name alias lookup.** The same
   false-positive risk as discussed in `baseline_comparison.md` applies:
   a community member matching a common sanctioned-name alias may not
   be the sanctioned person.
4. **No temporal info.** A community here is a static snapshot. The
   [`temporal_patterns.md`](temporal_patterns.md) report covers the
   evolution side.

## Reproduce

```bash
just job-run build_latent_clusters
just job-fetch processed/latent_clusters.parquet docs/reports/data/
just job-fetch processed/latent_clusters_summary.json docs/reports/data/

uv run python scripts/render_latent_clusters.py \
    --parquet docs/reports/data/latent_clusters.parquet \
    --summary docs/reports/data/latent_clusters_summary.json \
    --out docs/reports/latent_clusters.md
```

Or trigger `.github/workflows/build-latent-clusters.yml`.
