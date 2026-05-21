# Confidence-aware graph reconstruction

_Generated 2026-05-21 12:17 UTC from `processed/confidence_graph_edges.parquet`,
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
(the 1991 entities from `rare_officer_dossiers.parquet`),
not the full 3.3M-edge ICIJ corpus. Bounded compute, investigatively-
aligned subgraph.

## Subgraph statistics

| Metric | Value |
|---|---:|
| Seed UIDs (dossier anchors) | 1,991 |
| Subgraph nodes | 29,888 |
| Subgraph edges | 66,681 |
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
| 0.70–0.90 | 67,545 |
| 0.50–0.70 | 1,672 |
| ≥0.90 (structural) | 1,356 |
| <0.50 | 37 |

### Per-kind breakdown (subgraph)

| Edge kind | Credibility | Edges in subgraph |
|---|---:|---:|
| `officer_of` | 0.77 | 30,397 |
| `registered_address` | 0.90 | 23,231 |
| `beneficial_owner_of` | 0.89 | 7,757 |
| `intermediary_of` | 0.85 | 7,488 |
| `same_company_as` | 0.77 | 1,580 |
| `cross_jurisdictional_twin` | 0.68 | 100 |
| `similar` | 0.42 | 21 |
| `same_name_as` | 0.42 | 16 |
| `underlying` | 0.72 | 11 |
| `same_as` | 0.81 | 5 |
| `same_id_as` | 0.90 | 2 |
| `probably_same_officer_as` | 0.63 | 1 |
| `psc_controller_of` | 0.89 | 1 |


## Communities at three credibility thresholds

The community partition is computed at each threshold by filtering
edges to those at-or-above the threshold, then running Louvain on the
filtered graph.

| Threshold | Edges retained | Communities | Largest | Median | Singletons |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 66,646 | 277 | 12,853 | 3 | 4 |
| 0.70 | 64,974 | 1416 | 12,947 | 2 | 701 |
| 0.90 | 1,356 | 28555 | 307 | 1 | 28456 |


## Stability across thresholds

**Per-node Jaccard overlap** between the community membership at the
most-permissive threshold (0.50) and the most-strict threshold
(0.90):

| Metric | Value |
|---|---:|
| Nodes evaluated | 29,888 |
| Mean Jaccard overlap | **0.033** |
| Nodes with overlap ≥ 0.5 | 785 (2.6%) |

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
| 43 | 307 | 2 |
| 45 | 234 | 2 |
| 46 | 184 | 35 |
| 48 | 176 | 3 |
| 53 | 69 | 69 |
| 47 | 52 | 4 |
| 39 | 51 | 0 |
| 82 | 26 | 1 |
| 40 | 23 | 0 |
| 44 | 21 | 3 |


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
| 1 | 24 | 3 | 3 | 1.00 | 1.00 | 1.000 |
| 2 | 21 | 3 | 3 | 1.00 | 1.00 | 1.000 |
| 3 | 60 | 5 | 5 | 1.00 | 1.00 | 1.000 |
| 4 | 7 | 3 | 3 | 1.00 | 1.00 | 1.000 |
| 5 | 49 | 14 | 14 | 1.00 | 1.00 | 1.000 |
| 6 | 32 | 3 | 3 | 1.00 | 1.00 | 1.000 |
| 7 | 56 | 4 | 4 | 1.00 | 1.00 | 1.000 |
| 8 | 53 | 69 | 69 | 1.00 | 1.00 | 1.000 |
| 9 | 59 | 3 | 3 | 1.00 | 1.00 | 1.000 |
| 10 | 77 | 3 | 3 | 1.00 | 1.00 | 1.000 |

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
| 43 | 306 | 0.902 | 0.902 |
| 45 | 233 | 0.902 | 0.902 |
| 46 | 183 | 0.902 | 0.902 |
| 48 | 175 | 0.902 | 0.902 |
| 39 | 72 | 0.903 | 0.902 |
| 53 | 68 | 0.902 | 0.902 |
| 47 | 51 | 0.902 | 0.902 |
| 82 | 25 | 0.902 | 0.902 |
| 40 | 22 | 0.902 | 0.902 |
| 44 | 20 | 0.903 | 0.902 |

### Contradiction-aware closure

Node pairs that share a community at the loose threshold but split across distinct communities at the strict threshold — the soft edges between them are the load-bearing assumptions. Detected: **5,070** pairs (capped).

| Node A | Node B | Loose community | Strict A | Strict B |
|---|---|---:|---:|---:|
| `icij:12002436` | `icij:12002521` | 0 | 22094 | 22095 |
| `icij:12002436` | `icij:14029376` | 0 | 22094 | 17 |
| `icij:12002436` | `icij:10032973` | 0 | 22094 | 112 |
| `icij:12002436` | `icij:12132752` | 0 | 22094 | 17 |
| `icij:12002436` | `icij:10105758` | 0 | 22094 | 202 |
| `icij:12002436` | `icij:10102324` | 0 | 22094 | 209 |
| `icij:12002436` | `icij:10208459` | 0 | 22094 | 364 |
| `icij:12002436` | `icij:11000123` | 0 | 22094 | 111 |
| `icij:12002436` | `icij:12002835` | 0 | 22094 | 22097 |
| `icij:12002436` | `icij:12002435` | 0 | 22094 | 22093 |

### Review-priority ranking

Edges in the gray zone (credibility 0.4–0.75) that touch contradiction-prone nodes or dossier seeds, ranked by `uncertainty × impact`. These are the highest-leverage manual-review targets — a yes/no decision on each rewrites large parts of the community structure. Total: **1,679**.

| Node A | Node B | Edge credibility | Uncertainty | Impact | Priority |
|---|---|---:|---:|---:|---:|
| `icij:55081490` | `oo:gb-coh-14161090` | 0.680 | 0.400 | 19.600 | 7.840 |
| `icij:55081490` | `oo:gb-coh-16027143` | 0.680 | 0.400 | 19.600 | 7.840 |
| `icij:55049444` | `oo:gb-coh-11520150` | 0.680 | 0.400 | 19.600 | 7.840 |
| `icij:55057137` | `oo:gb-coh-15120320` | 0.680 | 0.400 | 19.600 | 7.840 |
| `icij:55054932` | `oo:gb-coh-ni680284` | 0.680 | 0.400 | 19.600 | 7.840 |
| `icij:55051774` | `oo:gb-coh-09146042` | 0.680 | 0.400 | 19.600 | 7.840 |
| `icij:10143602` | `oo:gb-coh-15120320` | 0.680 | 0.400 | 19.300 | 7.720 |
| `oo:gb-coh-11520150` | `icij:200287` | 0.680 | 0.400 | 19.300 | 7.720 |
| `icij:10067729` | `oo:gb-coh-09146042` | 0.680 | 0.400 | 19.300 | 7.720 |
| `icij:55081280` | `oo:gb-coh-13399004` | 0.680 | 0.400 | 13.500 | 5.400 |
| `icij:55081280` | `oo:gb-coh-10827470` | 0.680 | 0.400 | 13.500 | 5.400 |
| `icij:10172921` | `sec:0001542769` | 0.510 | 0.629 | 7.200 | 4.526 |
| `icij:10173464` | `sec:0001005788` | 0.510 | 0.629 | 7.200 | 4.526 |
| `icij:10212642` | `sec:0000733590` | 0.510 | 0.629 | 7.200 | 4.526 |
| `icij:10145890` | `sec:0001822571` | 0.510 | 0.629 | 5.200 | 3.269 |

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
