# Confidence-aware graph reconstruction

_Generated 2026-05-17 21:36 UTC from `processed/confidence_graph_edges.parquet`,
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
| `officer_of` | 0.90 | 17,417 |
| `registered_address` | 0.95 | 7,143 |
| `intermediary_of` | 0.90 | 2,032 |
| `similar` | 0.50 | 21 |
| `same_name_as` | 0.50 | 13 |
| `same_company_as` | 0.85 | 9 |
| `same_id_as` | 0.95 | 2 |
| `same_as` | 0.95 | 2 |
| `underlying` | 0.85 | 1 |


## Communities at three credibility thresholds

The community partition is computed at each threshold by filtering
edges to those at-or-above the threshold, then running Louvain on the
filtered graph.

| Threshold | Edges retained | Communities | Largest | Median | Singletons |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 23,677 | 44 | 3,138 | 12 | 0 |
| 0.70 | 23,644 | 50 | 3,138 | 11 | 3 |
| 0.90 | 23,634 | 53 | 3,138 | 11 | 3 |


## Stability across thresholds

**Per-node Jaccard overlap** between the community membership at the
most-permissive threshold (0.50) and the most-strict threshold
(0.90):

| Metric | Value |
|---|---:|
| Nodes evaluated | 7,888 |
| Mean Jaccard overlap | **0.992** |
| Nodes with overlap ≥ 0.5 | 7,821 (99.2%) |

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
| 31 | 3,138 | 0 |
| 33 | 1,352 | 2 |
| 29 | 894 | 0 |
| 40 | 440 | 52 |
| 41 | 423 | 5 |
| 30 | 322 | 2 |
| 45 | 231 | 5 |
| 43 | 182 | 7 |
| 39 | 159 | 3 |
| 46 | 126 | 35 |


## Anomaly-ranked communities at threshold 0.90

The size-ranked table above is a baseline. The investigatively-relevant
ranking is by **anomaly score**, which combines:

- **Seed density** (40% weight) — fraction of community members that are
  dossier-anchor seeds. High = community is investigatively-aligned.
- **Isolation** (35%) — fraction of community edges that are internal vs.
  bridging out to other communities. High = self-contained cluster, a
  shell-network signature.
- **Size deviation** (25%) — log-size distance from the median community
  size. Communities much smaller (tight clusters) or much larger (sprawling
  hubs) than the median are more anomalous than typical-sized ones.

Top 10:

| Rank | Community | Size | Seeds | Seed density | Isolation | Anomaly score |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 46 | 126 | 35 | 0.28 | 1.00 | 0.711 |
| 2 | 21 | 4 | 2 | 0.50 | 1.00 | 0.655 |
| 3 | 25 | 4 | 2 | 0.50 | 1.00 | 0.655 |
| 4 | 19 | 4 | 2 | 0.50 | 1.00 | 0.655 |
| 5 | 22 | 4 | 2 | 0.50 | 1.00 | 0.655 |
| 6 | 28 | 4 | 2 | 0.50 | 1.00 | 0.655 |
| 7 | 8 | 4 | 2 | 0.50 | 1.00 | 0.655 |
| 8 | 40 | 440 | 52 | 0.12 | 0.99 | 0.644 |
| 9 | 23 | 13 | 8 | 0.62 | 1.00 | 0.614 |
| 10 | 48 | 6 | 3 | 0.50 | 1.00 | 0.613 |

The top-ranked community here is the lead-generation engine's graph-level recommendation: investigate **this cluster** because its structural signature (isolated + seed-dense + size-distinctive) is most unlike everything else in the subgraph.


## Multi-hop indirect links between seeds

Pairs of dossier-anchor seeds that are **not directly connected** but are
reachable through a 2-3 hop path whose probability (product of edge
credibilities along the path) is ≥ 0.05. These are the "uncertain but
compelling" indirect links the per-anchor dossier walks miss.

| Metric | Value |
|---|---:|
| Indirect pairs surfaced | 5,032 |
| Pairs with path probability ≥ 0.5 (strong) | 3,592 |

### Top 10 strongest indirect links

| src_uid | dst_uid | Path probability |
|---|---|---:|
| `icij:55081482` | `icij:55081490` | **0.902** |
| `icij:55023121` | `icij:55024976` | **0.902** |
| `icij:55023121` | `icij:55025237` | **0.902** |
| `icij:55023121` | `icij:55025414` | **0.902** |
| `icij:55023121` | `icij:55023806` | **0.902** |
| `icij:55023121` | `icij:55025295` | **0.902** |
| `icij:55023121` | `icij:55025149` | **0.902** |
| `icij:55023121` | `icij:55024979` | **0.902** |
| `icij:55023121` | `icij:55025060` | **0.902** |
| `icij:55023121` | `icij:55024946` | **0.902** |

A path probability of 0.5 means the chain of edge credibilities between the two seeds multiplies out to 0.5 — strong enough that the pair is worth investigating as if it were a direct link, even though no single edge connects them. Lower values are weaker but still surface candidates a 1-hop search would miss.


## Confidence-aware reasoning extensions

These extensions sit on top of the threshold-stability analysis and turn
the credibility-weighted graph into actionable reviewer signal.

### Per-community confidence aggregates

Mean / min edge credibility within each community at the strict threshold (0.90). Communities with high mean credibility are structurally grounded; low-mean ones rest on inferred edges and deserve review before publication.

| Community | Internal edges | Mean credibility | Min credibility |
|---:|---:|---:|---:|
| 31 | 9198 | 0.917 | 0.900 |
| 33 | 2083 | 0.900 | 0.900 |
| 40 | 1435 | 0.907 | 0.900 |
| 29 | 1311 | 0.931 | 0.900 |
| 45 | 784 | 0.913 | 0.900 |
| 41 | 766 | 0.911 | 0.900 |
| 46 | 482 | 0.908 | 0.900 |
| 39 | 453 | 0.917 | 0.900 |
| 30 | 332 | 0.902 | 0.900 |
| 43 | 323 | 0.905 | 0.900 |

### Contradiction-aware closure

Node pairs that share a community at the loose threshold but split across distinct communities at the strict threshold — the soft edges between them are the load-bearing assumptions. Detected: **1,506** pairs (capped).

| Node A | Node B | Loose community | Strict A | Strict B |
|---|---|---:|---:|---:|
| `icij:12084634` | `icij:10184310` | 1 | 1 | 15 |
| `icij:12084634` | `icij:10183032` | 1 | 1 | 17 |
| `icij:12084634` | `icij:10182507` | 1 | 1 | 15 |
| `icij:12084634` | `icij:14021135` | 1 | 1 | 17 |
| `icij:12084634` | `icij:11002367` | 1 | 1 | 15 |
| `icij:12084634` | `icij:20096636` | 1 | 1 | 49 |
| `icij:12084634` | `icij:20161123` | 1 | 1 | 49 |
| `icij:12084634` | `icij:11011526` | 1 | 1 | 17 |
| `icij:12084634` | `icij:10188921` | 1 | 1 | 15 |
| `icij:12084634` | `icij:10213667` | 1 | 1 | 15 |

### Review-priority ranking

Edges in the gray zone (credibility 0.4–0.75) that touch contradiction-prone nodes or dossier seeds, ranked by `uncertainty × impact`. These are the highest-leverage manual-review targets — a yes/no decision on each rewrites large parts of the community structure. Total: **27**.

| Node A | Node B | Edge credibility | Uncertainty | Impact | Priority |
|---|---|---:|---:|---:|---:|
| `icij:12134060` | `icij:12136622` | 0.500 | 0.571 | 9.900 | 5.657 |
| `icij:12123045` | `icij:12120890` | 0.500 | 0.571 | 9.000 | 5.143 |
| `icij:12123045` | `icij:12122234` | 0.500 | 0.571 | 9.000 | 5.143 |
| `icij:12120890` | `icij:12120889` | 0.500 | 0.571 | 9.000 | 5.143 |
| `icij:12120890` | `icij:12122234` | 0.500 | 0.571 | 9.000 | 5.143 |
| `icij:12122234` | `icij:12120889` | 0.500 | 0.571 | 9.000 | 5.143 |
| `icij:12123045` | `icij:12120889` | 0.500 | 0.571 | 8.000 | 4.571 |
| `icij:240083540` | `icij:240031907` | 0.500 | 0.571 | 3.500 | 2.000 |
| `icij:240101127` | `icij:240040945` | 0.500 | 0.571 | 3.500 | 2.000 |
| `icij:240105164` | `icij:240057006` | 0.500 | 0.571 | 3.500 | 2.000 |
| `icij:240043094` | `icij:240043096` | 0.500 | 0.571 | 2.600 | 1.486 |
| `icij:240475232` | `icij:240477817` | 0.500 | 0.571 | 2.100 | 1.200 |
| `icij:240475232` | `icij:240477818` | 0.500 | 0.571 | 2.100 | 1.200 |
| `icij:40538` | `icij:24063` | 0.500 | 0.571 | 2.000 | 1.143 |
| `icij:240511694` | `icij:240512919` | 0.500 | 0.571 | 1.900 | 1.086 |

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
