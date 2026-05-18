# Uncertainty propagation through investigative graph space

_Formal definitions of edge, path, cluster, and graph-level uncertainty
in the GoldenMatch shell-network pipeline. Companion to
[`methodology.md`](methodology.md) and the operational report at
[`docs/reports/uncertainty_propagation.md`](../reports/uncertainty_propagation.md)._

This document fills the gap between the operational
"uncertainty-preserving" architecture (provenance retention, edge
typing, contradiction tracking) and the formal mathematical statement
of how uncertainty flows from edge priors to cluster and graph-level
conclusions.

## Notation

- **G = (V, E)** — the credibility-weighted undirected graph on the
  2-hop dossier-anchored subgraph (~1k–8k nodes).
- **e ∈ E** — an edge with credibility `cred(e) ∈ [0, 1]`.
- **C ⊆ V** — a community (Louvain partition output).
- **E(C) ⊆ E** — edges with both endpoints in `C`.
- **kind(e)** — the structural type (`officer_of`, `same_name_as`, …).
- **src(e)** — the leak / registry the edge originates from
  (`Panama Papers`, `GLEIF`, …).

## 1. Edge credibility (provenance-weighted)

Each edge carries a credibility derived from two priors — one per edge
kind, one per source corpus — combined multiplicatively:

> **cred(e) = cred_kind(kind(e)) × cred_source(src(e))**

The priors are operator-set, not learned from labels. Rationale and
values are tabulated in [`methodology.md` §6.2](methodology.md) and the
runtime values appear in
[`docs/reports/confidence_graph.md`](../reports/confidence_graph.md).

**Properties:**

- **Bounded.** `cred(e) ∈ [0, 1]`.
- **Monotone in either prior.** Increasing either factor never lowers
  `cred(e)`.
- **Provenance-discriminating.** Two edges with identical kind but
  different sources receive different credibilities, so registry
  evidence outweighs older-leak evidence on the same kind.

**Limitation.** Priors are not calibrated against the labelled
marginal-pair review set yet (see § Open work below). A v2 would
estimate `cred_kind` and `cred_source` jointly via logistic regression
against `labels.csv`.

## 2. Path-probability propagation

For two non-adjacent nodes `(u, v)`, define the **path probability**
along a path `π = (e_1, …, e_k)` as the product of edge credibilities:

> **P(connection | π) = ∏_{i=1..k} cred(e_i)**

Equivalently, on the negated-log graph where `w(e) = -log cred(e)`, the
log-path-probability is the sum of edge weights — so the maximum-
probability path is the shortest path in `-log cred` space. This is
what the indirect-links computation in `build_confidence_graph.py` does
(Dijkstra on negated-log weights, cutoff at `-log 0.05 ≈ 3.0`).

**Independence assumption.** The formula assumes edges along the path
are **conditionally independent** given the underlying truth of the
connection. Real-world edges correlate (a single leak document may
generate multiple edges), so:

> **The computed path probability is a *conservative* lower bound on
> the true posterior probability of connection.**

This matters for thresholding: a 0.5 path-probability is
investigatively strong, not borderline.

**Properties:**

- **Monotone in path-length.** Adding any edge with `cred < 1` to the
  path strictly decreases the path probability.
- **Monotone in edge credibilities.** Improving any single edge along
  the path never decreases the path probability.
- **Reduces to direct credibility** when `k = 1`.

## 3. Cluster confidence with contradiction penalty

A community `C` has two competing signals: how credible are its
internal edges, and how often do its members appear on contradiction
boundaries (pairs that share a community at the loose threshold but
split at the strict threshold).

> **conf(C) = mean_cred(C) × (1 − λ · contradiction_density(C))**

where:

- **mean_cred(C)** = average `cred(e)` over `E(C)`
- **contradiction_density(C)** = `|C ∩ N_contradict| / |C|`
- **N_contradict** = the set of nodes appearing in any
  contradiction pair
- **λ ∈ [0, 1]** = contradiction-penalty weight; default **λ = 0.5**

**Properties:**

- **λ = 0** reduces to plain `mean_cred(C)` (the previous
  `confidence_community_aggregates` metric).
- **λ = 1** zeros out `conf(C)` for any cluster where every node
  participates in a contradiction.
- **Monotone in mean credibility.** A cluster of higher-credibility
  edges always scores at least as well as one of lower-credibility
  edges with the same contradiction density.
- **Monotone (anti-) in contradiction density.** Adding a
  contradiction-touching node to `C` cannot increase `conf(C)`.
- **Reducibility.** Communities with `contradiction_density = 0` are
  "clean" — their confidence equals their mean credibility, so a
  reviewer can trust the partition directly.

**λ-sensitivity.** The default 0.5 was chosen so a cluster with 50%
of its members on contradiction boundaries gets its confidence cut by
25% — meaningful, not catastrophic. v2 should sweep λ against held-out
analyst judgements once a labelled set exists.

## 4. Graph-level uncertainty (Shannon entropy)

The single-scalar summary of how much of the graph rests on uncertain
edges:

> **H(G) = (1/|E|) · Σ_{e ∈ E} h(cred(e))**

where **h(p) = -p log p - (1-p) log(1-p)** is the per-edge binary
entropy in nats. Normalised by `log 2`, `H(G) ∈ [0, 1]`.

**Properties:**

- **H(G) = 0** ⇔ every edge is certain (`cred ∈ {0, 1}`).
- **H(G) maximised at p = 0.5** for every edge — i.e., the graph is
  maximally uncertain when every edge is "coin-flip" credible.
- **Decoupled from credibility direction.** `H(G)` is the same for a
  graph of `cred = 0.1` edges and `cred = 0.9` edges; both are
  *certain in opposite directions*. The companion metric is
  `mean_cred(G)`, reported alongside.
- **Decomposable.** `H(G) = (1/|E|) · Σ h(cred(e))` summed over any
  partition of edges (per-kind, per-source) — so the entropy can be
  attributed to specific edge classes when investigating.

**Interpretation.** Read `H(G)` together with `mean_cred(G)`:

| `mean_cred(G)` | `H(G)` | What it means |
| :---: | :---: | --- |
| high (>0.9) | low (<0.3) | Graph is dominated by credible structural edges. Conclusions are well-supported. |
| high (>0.9) | high (>0.5) | A few edges at `~0.5` credibility are pulling the entropy up despite a credible majority. Investigate the gray-zone edges. |
| low (<0.6) | low (<0.3) | Graph is dominated by low-credibility edges that the system is *confident* are weak. Conclusions are weakly supported but consistent. |
| low (<0.6) | high (>0.5) | Graph is genuinely uncertain. Treat the partition output as exploratory only. |

## 5. Combining the metrics

The four metrics compose into a single decision rule for whether a
finding is publication-grade:

1. **Edge level.** Direct edges with `cred(e) ≥ 0.9` are
   publication-grade.
2. **Path level.** Indirect links with `P(connection | π) ≥ 0.5` are
   investigatively worth pursuing.
3. **Cluster level.** Communities with `conf(C) ≥ 0.7` are
   structurally coherent. Communities with `conf(C) ≥ 0.7` AND
   `contradiction_density = 0` are publication-grade.
4. **Graph level.** Reports drawn from a graph with `H(G) ≤ 0.3` and
   `mean_cred(G) ≥ 0.85` come with the strongest epistemic guarantee
   the architecture can provide.

The operational values for the current dossier-anchored subgraph are
emitted to `processed/confidence_graph_summary.json` and rendered in
[`docs/reports/uncertainty_propagation.md`](../reports/uncertainty_propagation.md).

## 6. Open work

- **Calibrate the priors against `labels.csv`.** Currently
  operator-set; the labelled marginal-pair review set is the obvious
  calibration target.
- **λ sweep against analyst judgements.** Default λ = 0.5 is a
  guess; a labelled "this cluster is real / not real" panel would
  pin it.
- **Path-correlation correction.** Current path-probability formula
  assumes edge independence. A v2 with co-source / co-document
  decorrelation would tighten the bound.
- **Hierarchical entropy decomposition.** `H(G)` can be split into
  per-kind / per-source / per-community contributions; the report
  currently surfaces the whole-graph scalar only.

## 7. Relationship to operational architecture

The pipeline already had every architectural ingredient: provenance is
retained in `source_label`, edges are typed in `kind_raw`, contradictions
are tracked in `confidence_contradictions.parquet`, communities are
detected at multiple thresholds. This document is the **formalisation
layer on top of that architecture**, not a change to it.

Said precisely: the architecture supports *uncertainty-aware
investigative graph reasoning*; this document and the new computed
columns supply the *mathematically formalised uncertainty propagation*
on top of it.
