# Confidence-aware graph reconstruction

_Generated 2026-05-17 02:58 UTC from `processed/confidence_graph_edges.parquet`,
`processed/confidence_communities.parquet`, and
`processed/confidence_graph_summary.json`. Companion to
[`methodology.md` §6](../paper/methodology.md)._

## What this report measures

Standard community detection treats edges as binary present/absent. In an
adversarial ER setting, every edge carries uncertainty: structural ICIJ
relations (`officer_of`, `registered_address`) are firm; inferred
relations (`same_name_as`, `similar`) are soft. This report:

1. **Scores each edge's credibility** based on its `kind_raw` (operator
   priors documented below).
2. **Runs Louvain community detection at multiple credibility thresholds**,
   producing a partition per threshold.
3. **Quantifies stability** — does the community structure survive when
   we drop low-credibility edges?

The scope is the 2-hop subgraph anchored on the **dossier seed set**
(the 363 entities from `rare_officer_dossiers.parquet`),
not the full 3.3M-edge ICIJ corpus. Bounded compute, investigatively-
aligned subgraph.

## Subgraph statistics

| Metric | Value |
|---|---:|
| Seed UIDs (dossier anchors) | 363 |
| Subgraph nodes | 7,888 |
| Subgraph edges | 23,677 |
| BFS depth | 2 hops |

## Edge-credibility priors

| Edge kind | Credibility | Rationale |
|---|---:|---|
| `registered_address` | 0.95 | Structural fact from leak documents |
| `officer_of` | 0.90 | Structural fact from leak documents |
| `intermediary_of` | 0.90 | Structural fact from leak documents |
| `shareholder_of` | 0.90 | Structural fact from leak documents |
| `same_id_as` | 0.95 | Identifier-based merge by ICIJ |
| `same_as` | 0.95 | Manual ICIJ deduplication |
| `same_company_as` | 0.85 | Cross-leak company identity |
| `underlying` | 0.85 | Structural ownership relation |
| `connected_to` | 0.75 | Generic relation, weaker than typed kinds |
| `same_name_as` | 0.50 | Name-similarity inference, weakest |
| `similar` | 0.50 | ICIJ vague relation, weakest |
| _(default for unknown kinds)_ | 0.70 | _Fallback_ |

### Distribution in this subgraph

| Credibility bucket | Edges |
|---|---:|
| ≥0.90 (structural) | 26,596 |
| 0.50–0.70 | 34 |
| 0.70–0.90 | 10 |

### Per-kind breakdown (subgraph)

| Edge kind | Credibility | Edges in subgraph |
|---|---:|---:|
| `officer_of` | 0.90 | 17,414 |
| `registered_address` | 0.95 | 7,142 |
| `intermediary_of` | 0.90 | 2,036 |
| `similar` | 0.50 | 21 |
| `same_name_as` | 0.50 | 13 |
| `same_company_as` | 0.85 | 9 |
| `same_as` | 0.95 | 2 |
| `same_id_as` | 0.95 | 2 |
| `underlying` | 0.85 | 1 |


## Communities at three credibility thresholds

The community partition is computed at each threshold by filtering
edges to those at-or-above the threshold, then running Louvain on the
filtered graph.

| Threshold | Edges retained | Communities | Largest | Median | Singletons |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 23,677 | 44 | 3,132 | 12 | 0 |
| 0.70 | 23,644 | 50 | 3,132 | 11 | 3 |
| 0.90 | 23,634 | 53 | 3,132 | 11 | 3 |


## Stability across thresholds

**Per-node Jaccard overlap** between the community membership at the
most-permissive threshold (0.50) and the most-strict threshold
(0.90):

| Metric | Value |
|---|---:|
| Nodes evaluated | 7,888 |
| Mean Jaccard overlap | **0.993** |
| Nodes with overlap ≥ 0.5 | 7,823 (99.2%) |

A mean Jaccard of 0.99 means **the community structure is
highly stable to credibility-threshold changes**.
The dominant communities are anchored by structural ICIJ edges
(`officer_of`, `registered_address`) which all have credibility ≥ 0.9
and survive any threshold in this range. Inferred edges (`same_name_as`,
`similar`, credibility 0.5) get filtered out at threshold ≥ 0.7,
producing the small change in community count visible above.

**The honest methodological claim**: the community partition reported
here is not an artifact of an arbitrary credibility cut-off. If the
mean Jaccard were ~0.5, it would be.

## Top 10 communities at threshold 0.90

Communities ranked by size. `n_seeds` = how many dossier-anchor UIDs
fall into this community (a signal that the community is investigatively
relevant, not just structurally large).

| Community ID | Size | Seed members |
|---:|---:|---:|
| 32 | 3,132 | 0 |
| 31 | 1,352 | 2 |
| 29 | 892 | 0 |
| 39 | 438 | 52 |
| 40 | 420 | 5 |
| 38 | 323 | 2 |
| 41 | 232 | 5 |
| 43 | 185 | 7 |
| 42 | 163 | 3 |
| 45 | 125 | 35 |


## What this report does NOT prove

1. **Credibility priors are operator estimates.** The per-edge-kind
   numbers in §"Edge-credibility priors" are hand-set, not learned. A
   v2 would calibrate them against the labelled marginal-pair review
   set (`labels.csv`) — which the repo doesn't yet have.
2. **Cross-source match edges are absent from this run.** The
   `confidence_graph_edges.parquet` here is ICIJ-only because the
   subgraph BFS walks `icij_edges`. Merging in cross-source-match edges
   (`icij_os_vs_gleif_matched.csv` etc.) with PAV-calibrated weights is
   a v2 follow-up; it would let the same threshold analysis run on
   cross-registry-merged identities.
3. **Stability ≠ correctness.** A stable community can still be wrong
   if the edge priors are systematically miscalibrated.
4. **The 2-hop subgraph is investigatively biased.** It anchors on
   dossier anchors that are *already* of interest. A baseline community
   analysis on a random-anchor subgraph would tell us if the stability
   here is general or specific to the dossier seeds.

## Reproduce

```bash
just job-run build_confidence_graph
for p in processed/confidence_graph_edges.parquet \
         processed/confidence_communities.parquet \
         processed/confidence_graph_summary.json; do
    just job-fetch "$p" docs/reports/data/
done

uv run python scripts/render_confidence_graph.py \
    --edges docs/reports/data/confidence_graph_edges.parquet \
    --communities docs/reports/data/confidence_communities.parquet \
    --summary docs/reports/data/confidence_graph_summary.json \
    --out docs/reports/confidence_graph.md
```

Or trigger `.github/workflows/build-confidence-graph.yml`.
