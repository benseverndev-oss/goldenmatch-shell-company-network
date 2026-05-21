# Confidence-aware graph reconstruction

_Generated 2026-05-21 00:17 UTC from `processed/confidence_graph_edges.parquet`,
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
(the 415 entities from `rare_officer_dossiers.parquet`),
not the full 3.3M-edge ICIJ corpus. Bounded compute, investigatively-
aligned subgraph.

## Subgraph statistics

| Metric | Value |
|---|---:|
| Seed UIDs (dossier anchors) | 415 |
| Subgraph nodes | 29,888 |
| Subgraph edges | 67,513 |
| BFS depth | 3 hops |

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
| `psc_controller_of` | 0.92 | — |
| `cross_jurisdictional_twin` | 0.85 | — |
| `beneficial_owner_of` | 0.92 | — |
| _(default for unknown kinds)_ | 0.70 | _Fallback_ |

### Distribution in this subgraph

| Credibility bucket | Edges |
|---|---:|
| 0.70–0.90 | 69,171 |
| ≥0.90 (structural) | 1,444 |
| 0.50–0.70 | 112 |
| <0.50 | 35 |

### Per-kind breakdown (subgraph)

| Edge kind | Credibility | Edges in subgraph |
|---|---:|---:|
| `officer_of` | 0.77 | 35,815 |
| `registered_address` | 0.90 | 28,625 |
| `intermediary_of` | 0.85 | 6,147 |
| `cross_jurisdictional_twin` | 0.68 | 111 |
| `similar` | 0.42 | 21 |
| `same_name_as` | 0.42 | 14 |
| `underlying` | 0.72 | 11 |
| `same_company_as` | 0.77 | 10 |
| `same_as` | 0.81 | 4 |
| `same_id_as` | 0.90 | 2 |
| `probably_same_officer_as` | 0.63 | 1 |
| `psc_controller_of` | 0.89 | 1 |


## Communities at three credibility thresholds

The community partition is computed at each threshold by filtering
edges to those at-or-above the threshold, then running Louvain on the
filtered graph.

| Threshold | Edges retained | Communities | Largest | Median | Singletons |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 67,480 | 48 | 17,278 | 19 | 2 |
| 0.70 | 67,368 | 132 | 17,278 | 1 | 83 |
| 0.90 | 1,444 | 28446 | 351 | 1 | 28352 |


## Stability across thresholds

**Per-node Jaccard overlap** between the community membership at the
most-permissive threshold (0.50) and the most-strict threshold
(0.90):

| Metric | Value |
|---|---:|
| Nodes evaluated | 29,888 |
| Mean Jaccard overlap | **0.027** |
| Nodes with overlap ≥ 0.5 | 624 (2.1%) |

A mean Jaccard of 0.03 means **the community structure is
unstable to credibility-threshold changes**.
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
| 41 | 351 | 2 |
| 43 | 260 | 2 |
| 46 | 212 | 3 |
| 44 | 193 | 35 |
| 53 | 69 | 67 |
| 45 | 55 | 4 |
| 48 | 46 | 3 |
| 80 | 40 | 1 |
| 42 | 23 | 3 |
| 61 | 15 | 3 |


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
| 1 | 33 | 3 | 3 | 1.00 | 1.00 | 1.000 |
| 2 | 54 | 4 | 4 | 1.00 | 1.00 | 1.000 |
| 3 | 75 | 3 | 3 | 1.00 | 1.00 | 1.000 |
| 4 | 49 | 14 | 14 | 1.00 | 1.00 | 1.000 |
| 5 | 58 | 3 | 3 | 1.00 | 1.00 | 1.000 |
| 6 | 8 | 3 | 3 | 1.00 | 1.00 | 1.000 |
| 7 | 53 | 69 | 67 | 0.97 | 1.00 | 0.988 |
| 8 | 59 | 5 | 4 | 0.80 | 1.00 | 0.920 |
| 9 | 21 | 3 | 1 | 0.33 | 1.00 | 0.733 |
| 10 | 24 | 3 | 1 | 0.33 | 1.00 | 0.733 |

The top-ranked community here is the lead-generation engine's graph-level recommendation: investigate **this cluster** because its structural signature (isolated + seed-dense + size-distinctive) is most unlike everything else in the subgraph.


## Multi-hop indirect links between seeds

Pairs of dossier-anchor seeds that are **not directly connected** but are
reachable through a 2-3 hop path whose probability (product of edge
credibilities along the path) is ≥ 0.05. These are the "uncertain but
compelling" indirect links the per-anchor dossier walks miss.

| Metric | Value |
|---|---:|
| Indirect pairs surfaced | 5,032 |
| Pairs with path probability ≥ 0.5 (strong) | 2,301 |

### Top 10 strongest indirect links

| src_uid | dst_uid | Path probability |
|---|---|---:|
| `icij:55025149` | `icij:55025237` | **0.815** |
| `icij:55025149` | `icij:55025414` | **0.815** |
| `icij:55025149` | `icij:55025295` | **0.815** |
| `icij:55025149` | `icij:55025605` | **0.815** |
| `icij:55025149` | `icij:55025262` | **0.815** |
| `icij:55025149` | `icij:55025187` | **0.815** |
| `icij:55025149` | `icij:55025296` | **0.815** |
| `icij:55081116` | `icij:55081482` | **0.815** |
| `icij:55081116` | `icij:55081490` | **0.815** |
| `icij:55061260` | `icij:55062091` | **0.815** |

A path probability of 0.5 means the chain of edge credibilities between the two seeds multiplies out to 0.5 — strong enough that the pair is worth investigating as if it were a direct link, even though no single edge connects them. Lower values are weaker but still surface candidates a 1-hop search would miss.


## Confidence-aware reasoning extensions

These extensions sit on top of the threshold-stability analysis and turn
the credibility-weighted graph into actionable reviewer signal.

### Per-community confidence aggregates

Mean / min edge credibility within each community at the strict threshold (0.90). Communities with high mean credibility are structurally grounded; low-mean ones rest on inferred edges and deserve review before publication.

| Community | Internal edges | Mean credibility | Min credibility |
|---:|---:|---:|---:|
| 41 | 350 | 0.902 | 0.902 |
| 43 | 259 | 0.902 | 0.902 |
| 46 | 211 | 0.902 | 0.902 |
| 44 | 192 | 0.902 | 0.902 |
| 53 | 68 | 0.902 | 0.902 |
| 45 | 54 | 0.902 | 0.902 |
| 48 | 45 | 0.902 | 0.902 |
| 80 | 39 | 0.902 | 0.902 |
| 42 | 22 | 0.902 | 0.902 |
| 47 | 14 | 0.902 | 0.902 |

### Contradiction-aware closure

Node pairs that share a community at the loose threshold but split across distinct communities at the strict threshold — the soft edges between them are the load-bearing assumptions. Detected: **5,117** pairs (capped).

| Node A | Node B | Loose community | Strict A | Strict B |
|---|---|---:|---:|---:|
| `icij:10114366` | `icij:12122088` | 0 | 128 | 19 |
| `icij:10114366` | `icij:10118625` | 0 | 128 | 144 |
| `icij:10114366` | `icij:10206072` | 0 | 128 | 221 |
| `icij:10114366` | `icij:10123404` | 0 | 128 | 153 |
| `icij:10114366` | `icij:10203723` | 0 | 128 | 219 |
| `icij:10114366` | `icij:10207772` | 0 | 128 | 227 |
| `icij:10114366` | `icij:10111617` | 0 | 128 | 123 |
| `icij:10114366` | `icij:10120894` | 0 | 128 | 142 |
| `icij:10114366` | `icij:10118483` | 0 | 128 | 137 |
| `icij:10114366` | `icij:10206071` | 0 | 128 | 220 |

### Review-priority ranking

Edges in the gray zone (credibility 0.4–0.75) that touch contradiction-prone nodes or dossier seeds, ranked by `uncertainty × impact`. These are the highest-leverage manual-review targets — a yes/no decision on each rewrites large parts of the community structure. Total: **100**.

| Node A | Node B | Edge credibility | Uncertainty | Impact | Priority |
|---|---|---:|---:|---:|---:|
| `icij:10203410` | `oo:gb-coh-03894052` | 0.680 | 0.400 | 11.000 | 4.400 |
| `icij:10142285` | `oo:gb-coh-04333597` | 0.680 | 0.400 | 6.000 | 2.400 |
| `icij:240083540` | `oo:gb-coh-11782738` | 0.680 | 0.400 | 5.000 | 2.000 |
| `icij:240031341` | `oo:gb-coh-ni601357` | 0.680 | 0.400 | 5.000 | 2.000 |
| `icij:240031341` | `oo:gb-coh-15526522` | 0.680 | 0.400 | 5.000 | 2.000 |
| `icij:240020686` | `oo:gb-coh-oe014681` | 0.680 | 0.400 | 5.000 | 2.000 |
| `icij:12122088` | `icij:12118435` | 0.425 | 0.143 | 13.400 | 1.914 |
| `icij:240031907` | `oo:gb-coh-11782738` | 0.680 | 0.400 | 4.000 | 1.600 |
| `icij:10093416` | `oo:gb-coh-oe010705` | 0.680 | 0.400 | 3.400 | 1.360 |
| `icij:240083540` | `icij:240031907` | 0.425 | 0.143 | 5.000 | 0.714 |
| `icij:240105164` | `icij:240057006` | 0.425 | 0.143 | 5.000 | 0.714 |
| `icij:240043094` | `icij:240043096` | 0.425 | 0.143 | 5.000 | 0.714 |
| `icij:13006329` | `icij:13001554` | 0.425 | 0.143 | 4.400 | 0.629 |
| `icij:13007559` | `icij:13009254` | 0.425 | 0.143 | 3.600 | 0.514 |
| `icij:13002058` | `icij:13009992` | 0.425 | 0.143 | 3.600 | 0.514 |

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
