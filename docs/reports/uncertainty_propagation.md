# Uncertainty propagation — operational values

_Generated 2026-05-18 03:55 UTC from `processed/confidence_graph_summary.json` and
`processed/confidence_cluster_scored.parquet`. Formal definitions in
[`docs/paper/uncertainty_propagation.md`](../paper/uncertainty_propagation.md)._

This report shows the values the four formal uncertainty-propagation
metrics produce on the current dossier-anchored subgraph. It is the
operational companion to the methodology document.

## Subgraph scope

| Metric | Value |
| --- | ---: |
| Seed UIDs (dossier anchors) | 363 |
| Subgraph nodes | 7,888 |
| Subgraph edges | 23,677 |
| BFS depth | 2 hops |

## 1. Edge credibility (provenance-weighted)

```
cred(e) = cred_kind(kind_raw) × cred_source(source_label)
```

The kind priors live in `confidence_graph_summary.json` under
`edge_credibility_priors`. The source priors are tabulated below
(values from `source_credibility_priors`):

| Source | Prior | Rationale |
| --- | ---: | --- |
| `GLEIF` | 0.99 | Authoritative registry; highest fidelity |
| `OpenSanctions` | 0.98 | Curated overlay; high fidelity |
| `Panama Papers` | 0.95 | Well-documented leak; high fidelity |
| `Paradise Papers - Appleby` | 0.95 | Well-documented; firm-level provenance |
| `Paradise Papers - Bahamas corporate registry` | 0.95 | Well-documented leak; firm/registry-level provenance |
| `Paradise Papers - Barbados corporate registry` | 0.95 | Well-documented leak; firm/registry-level provenance |
| `Paradise Papers - Aruba corporate registry` | 0.95 | Well-documented leak; firm/registry-level provenance |
| `Paradise Papers - Cook Islands corporate registry` | 0.95 | Well-documented leak; firm/registry-level provenance |
| `Paradise Papers - Lebanon corporate registry` | 0.95 | Well-documented leak; firm/registry-level provenance |
| `Paradise Papers - Malta corporate registry` | 0.95 | Well-documented leak; firm/registry-level provenance |
| `Paradise Papers - Samoa corporate registry` | 0.95 | Well-documented leak; firm/registry-level provenance |
| `UK PSC` | 0.95 | Statutory registry; high fidelity |
| `UK disqualified` | 0.95 | Statutory regulatory action; high fidelity |
| `Pandora Papers` | 0.92 | Recent leak; mid-to-high fidelity |
| `Bahamas Leaks` | 0.90 | Single-jurisdiction leak; mid fidelity |
| `Offshore Leaks` | 0.85 | Oldest leak; lowest fidelity |
| _(unknown source)_ | 0.85 | _Fallback_ |

## 2. Path-probability propagation

```
P(connection | π) = ∏_{i=1..k} cred(e_i)
```

Computed by Dijkstra on the negated-log graph, cutoff at
`-log 0.05 ≈ 3.0` (so paths weaker than 5% are dropped). Full
indirect-link list in
[`confidence_graph.md`](confidence_graph.md) §"Indirect links".

**Independence assumption (explicit):**
Path propagation assumes conditional independence of edges given underlying truth. This is conservative — real-world edges correlate, so the computed path probability is a lower bound on the true probability.

## 3. Cluster confidence with contradiction penalty

```
conf(C) = mean_cred(C) × (1 - λ · contradiction_density(C))
```

with **λ = 0.50** by default.

- **Clusters scored:** 6,933
- **Clean clusters** (`contradiction_density = 0`): **6,558**
- **Penalised clusters** (any contradiction-touching member): **375**
- **Mean cluster confidence:** 0.008

**Top-10 clusters by confidence:**

| Community | Size | Mean cred | Contradiction density | Cluster conf |
|---:|---:|---:|---:|---:|
| 36 | 152 | 0.902 | 0.000 | **0.902** |
| 37 | 19 | 0.902 | 0.000 | **0.902** |
| 38 | 204 | 0.902 | 0.000 | **0.902** |
| 39 | 44 | 0.902 | 0.000 | **0.902** |
| 40 | 161 | 0.902 | 0.000 | **0.902** |
| 41 | 163 | 0.902 | 0.000 | **0.902** |
| 42 | 14 | 0.902 | 0.000 | **0.902** |
| 43 | 2 | 0.902 | 0.000 | **0.902** |
| 44 | 2 | 0.902 | 0.000 | **0.902** |
| 45 | 13 | 0.902 | 0.000 | **0.902** |

**Top-5 most-penalised clusters** (largest contradiction density):

| Community | Size | Mean cred | Contradiction density | Cluster conf |
|---:|---:|---:|---:|---:|
| 0 | 2 | 0.902 | **1.000** | 0.451 |
| 1 | 2 | 0.902 | **1.000** | 0.451 |
| 2 | 4 | 0.902 | **1.000** | 0.451 |
| 3 | 2 | 0.902 | **1.000** | 0.451 |
| 4 | 2 | 0.902 | **1.000** | 0.451 |

## 4. Graph-level uncertainty

```
H(G) = (1/|E|) · Σ_e [-p log p - (1-p) log(1-p)]    (nats)
```

- **Total entropy:** 11832.6494 nats
- **Mean entropy per edge:** 0.4998 nats
- **Normalised entropy** (divided by `log 2`): **0.7210** ∈ [0, 1]
- **Mean edge credibility:** 0.7963

**Verdict:** **Intermediate epistemic state. Read the per-cluster and per-edge confidence numbers before treating any single finding as load-bearing.**

## 5. Combined decision rule

Read together with the formal definitions, the four metrics yield a
single threshold rule for whether a finding is publication-grade:

1. **Edge level.** Direct edges with `cred(e) ≥ 0.9` are publication-grade.
2. **Path level.** Indirect links with `P(connection | π) ≥ 0.5` are investigatively worth pursuing.
3. **Cluster level.** Communities with `conf(C) ≥ 0.7` AND `contradiction_density = 0` are publication-grade.
4. **Graph level.** The whole graph carries a `mean_cred(G)` / `H(G)` verdict (above).

## What this report does NOT prove

- **The priors are operator-set, not learned.** Calibrating `cred_kind`
  and `cred_source` against the labelled `marginal_pair_review`
  set is the documented v2 follow-up.
- **λ = 0.5 is a default.** The contradiction-penalty weight has not
  been swept against held-out analyst judgements.
- **Path-probability is a conservative lower bound.** The independence
  assumption is documented and explicit.

## Reproduce

```bash
just job-run build_confidence_graph
just job-fetch processed/confidence_graph_summary.json docs/reports/data/
just job-fetch processed/confidence_cluster_scored.parquet docs/reports/data/

uv run python scripts/render_uncertainty_propagation.py \
    --summary docs/reports/data/confidence_graph_summary.json \
    --cluster-parquet docs/reports/data/confidence_cluster_scored.parquet \
    --out docs/reports/uncertainty_propagation.md
```

Or trigger `.github/workflows/build-confidence-graph.yml` (renders both
`confidence_graph.md` and this report).
