# Publication template — confirmed cluster {COMMUNITY_ID}

_Copy this file to `cluster_{COMMUNITY_ID}_findings.md` (replacing
the placeholder) **only after** the matching validation workbook in
[`docs/validation/cluster_{COMMUNITY_ID}.md`](../validation/) has
verdict = **Confirmed novel**. Fill each section from the workbook,
not from re-deriving the values._

This template is the **output of Step 4** (publish) in the 4-step
discovery workflow. It is not auto-generated. The structure exists so
that every published finding carries the discovery path, graph
evolution, provenance chain, contradictory evidence considered, and
preserved uncertainty.

**Author:** _____
**Date published:** YYYY-MM-DD
**Validation workbook:** [`cluster_{COMMUNITY_ID}.md`](../validation/cluster_{COMMUNITY_ID}.md)

---

## Headline finding

_(One sentence. The most defensible claim the uncertainty numbers
support. No more than the validation workbook §7 "minimum publishable
claim" justifies.)_

> _e.g., "Cluster #2762 shows a 173-entity HK/MT/VG community in
> which a single sanctioned entity sits at the centre of an officer-
> reuse pattern not surfaced by OFAC or HM Treasury sanctions
> searches, with mean edge credibility 0.83 and zero internal
> contradictions."_

---

## Why this matters

_(2–4 sentences. Why is this finding investigatively interesting?
What does it enable that single-source search did not?)_

---

## 1. Discovery path

Step-by-step trace of how the pipeline surfaced this cluster:

1. _e.g., Build started from rare-officer dossier seed
   `john.doe@icij:80012345`._
2. _e.g., Two-hop graph walk on `icij_edges.parquet` produced the
   subgraph; cluster #2762 emerged at Louvain threshold 0.9._
3. _e.g., Anomaly scorer flagged it (anomaly_score=0.42, seed_density=0.10,
   isolation=0.98) — top 5% by anomaly._
4. _e.g., Confidence-aware reasoning gave cluster_confidence=0.74 with
   contradiction_density=0._
5. _e.g., Validation queue ranked it #3 by composite priority._

Each step references the specific report:
[`discovery_lift.md`](discovery_lift.md) ·
[`latent_clusters.md`](latent_clusters.md) ·
[`confidence_graph.md`](confidence_graph.md) ·
[`validation_queue.md`](validation_queue.md).

**Counterfactual:** What would a baseline single-source workflow have
surfaced from the same seed? _(quote the baseline_comparison.md
numbers or describe the ICIJ-search-alone view)_

---

## 2. Graph evolution

Timeline of when the cluster's structural edges entered the corpus:

| Year | New edges | Cluster size after | Key event |
| ---: | ---: | ---: | --- |
| 2014 | 12 | 12 | First Panama Papers entities |
| 2017 | 38 | 50 | Paradise Papers expansion |
| ... | ... | ... | ... |

_(Pull from `confidence_graph_edges.parquet` joined on
`source_label` / `start_date`)_

**Interpretation:** _(steady accretion, single-event formation, or
recent reactivation?)_

---

## 3. Provenance chain

Every load-bearing claim traces to specific source-rows:

### Claim 1: _(e.g., entity X is part of the cluster)_

| Field | Value |
| --- | --- |
| Source | ICIJ Offshore Leaks |
| source_label | Panama Papers |
| Source row | `icij_entities` `source_id`=... |
| kind_raw | `officer_of` |
| cred_kind × cred_source | 0.90 × 0.95 = **0.855** |

### Claim 2: _(e.g., X shares an address with Y)_

_(repeat the structure)_

### Cluster-level aggregate

| Provenance distribution | Edges | Mean cred(e) |
| --- | ---: | ---: |
| Panama Papers | _ | _ |
| Paradise Papers | _ | _ |
| OpenSanctions | _ | _ |
| GLEIF | _ | _ |
| Other | _ | _ |

---

## 4. Contradictory evidence considered

Every falsifier the validation workbook §4 listed, with the outcome:

### Falsifier 1: _(e.g., bulk-incorporation by a single corporate-
### secretary firm)_

- **Hypothesis:** the cluster could be a corporate-secretary's client
  book, not coordinated activity.
- **Check performed:** _____
- **Outcome:** _refuted / partially supported / supported_
- **Evidence:** _____

### Falsifier 2: _(e.g., name-similarity artefact)_

_(repeat)_

### Contradictions inside the cluster

Pulled from `confidence_contradictions.parquet`:

| Pair | Loose community | Strict A | Strict B | Resolution |
| --- | --- | --- | --- | --- |
| (a, b) | C_lo | C_a | C_b | the splitting edge was inferred (`same_name_as`); manual review confirmed the names refer to the same person on the basis of DOB + jurisdiction |

---

## 5. Uncertainty preserved

The published claim is bounded by the formal uncertainty propagation
described in
[`docs/paper/uncertainty_propagation.md`](../paper/uncertainty_propagation.md).

| Metric | Value | Reading |
| --- | ---: | --- |
| Cluster confidence (λ=0.5) | _____ | _____ |
| Mean edge credibility | _____ | _____ |
| Contradiction density | _____ | _____ |
| Worst-case path probability to seed | _____ | _____ |
| Subgraph entropy contribution | _____ | _____ |

**Verdict per the 4-cell matrix** (from `uncertainty_propagation.md` §4):
_____ → _____

**Honest reading of what this allows us to claim:**

- We can claim: _(specific defensible statement)_
- We cannot claim: _(overreach the numbers do not support)_

---

## 6. External corroboration

| Source | Query | Result | URL / reference |
| --- | --- | --- | --- |
| _e.g., ICIJ Offshore Leaks UI_ | name + juris | hit | https://... |
| _e.g., SEC EDGAR_ | _____ | _____ | _____ |
| _e.g., court records_ | _____ | _____ | _____ |

---

## 7. What this report does NOT prove

The validation workbook's verdict was "Confirmed novel" — but novelty
is bounded:

1. **No journalist confirmation panel.** The structural pattern
   survives every falsifier we checked; it has not been reviewed by
   an external investigative-journalism panel.
2. **Source priors are operator-set.** The credibilities used are
   defensible but not learned from labelled data.
3. **Scope is the dossier-anchored subgraph.** Generalising to the
   full 3.3M-edge corpus would require re-running confidence-graph
   scoring at corpus scale.
4. _(any other domain-specific caveat that emerged during validation)_

---

## 8. Reproducibility appendix

Every number in this report should be reproducible by running:

```bash
# 1. Refresh the confidence graph + uncertainty propagation
gh workflow run build-confidence-graph.yml

# 2. Refresh the validation queue ranking
gh workflow run build-validation-queue.yml

# 3. The validation workbook itself is manual — see
#    docs/validation/cluster_{COMMUNITY_ID}.md
```

Specific parquet rows backing this report:

- `confidence_cluster_scored.parquet` row: community_id=_____
- Member list: `confidence_communities.parquet` filter
  `community_id={COMMUNITY_ID} AND threshold=0.9`
- Internal edges: `confidence_graph_edges.parquet` filter both
  endpoints in member set
- Contradictions: `confidence_contradictions.parquet` filter
  `lo_community={LO_COMMUNITY_ID}`

---

## 9. Cross-references

- Validation workbook: [`docs/validation/cluster_{COMMUNITY_ID}.md`](../validation/cluster_{COMMUNITY_ID}.md)
- Discovery Advantage Report: [`discovery_advantage.md`](discovery_advantage.md)
- Top-candidates walkthrough: [`top_candidates_walkthrough.md`](top_candidates_walkthrough.md)
- Methodology paper: [`../paper/methodology.md`](../paper/methodology.md)
- Uncertainty propagation: [`../paper/uncertainty_propagation.md`](../paper/uncertainty_propagation.md)
