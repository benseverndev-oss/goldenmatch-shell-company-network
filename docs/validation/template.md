# Validation workbook — Cluster #{COMMUNITY_ID}

_Copy this file to `cluster_{COMMUNITY_ID}.md` (replacing the
placeholder) when starting a manual review. Fill in each section.
Leave a section blank with `_(not investigated yet)_` rather than
fabricating content._

**Reviewer:** _____
**Date started:** YYYY-MM-DD
**Date completed:** YYYY-MM-DD

---

## Pre-validation snapshot

Paste the corresponding row from
[`docs/reports/validation_queue.md`](../reports/validation_queue.md):

- **Priority score:** _____
- **Size:** _____ entities
- **Anomaly score:** _____
- **Cluster confidence:** _____
- **Contradiction density:** _____
- **Attestation density:** _____
- **Underreportedness:** _____
- **Member sample (first 10):** _____

---

## 1. Discovery path

How did the pipeline surface this cluster? Trace the surfacing channel(s)
in order:

- [ ] **Seed-driven** (dossier anchor → 2-hop graph walk → community)
- [ ] **Latent-cluster mining** (Louvain → anomaly score → top-N)
- [ ] **Structure benchmark** — which structure type? (S1/S2/S3/S4/S5/S6)
- [ ] **Non-obviousness ranking** (rare-officer scoring)
- [ ] **Confidence-aware reasoning** (cluster confidence + contradiction
      analysis)

Order matters: what surfaced it *first*?

**Free-form:**
_(narrate the discovery path — which channel hit it first, what
escalated it through the queue)_

---

## 2. Graph evolution

When did each edge in this cluster enter the corpus? This matters for
two reasons: (a) it tells you whether the cluster is a recent
formation or a long-lived structure, and (b) it tells you whether the
cluster's discoverability has changed over the lifetime of the
pipeline.

Pull from `confidence_graph_edges.parquet` filtered to this community:

| Edge kind | Earliest start_date | Latest start_date | n |
| --- | --- | --- | ---: |
| `officer_of` | YYYY | YYYY | _ |
| `intermediary_of` | YYYY | YYYY | _ |
| `registered_address` | YYYY | YYYY | _ |
| `same_name_as` | YYYY | YYYY | _ |
| _other_ | YYYY | YYYY | _ |

**Free-form:**
_(does the cluster look like a one-off formation event, a steady
accretion, or a recent reactivation? cross-reference temporal_patterns.md)_

---

## 3. Provenance chain

For each load-bearing claim about this cluster, which sources back it
and at what credibility? Use the formal uncertainty propagation:

> `cred(e) = cred_kind(kind_raw) × cred_source(source_label)`

| Claim | Backing source(s) | source_label | cred_kind | cred_source | cred(e) |
| --- | --- | --- | ---: | ---: | ---: |
| Entity X is in cluster | ICIJ | Panama Papers | 0.90 | 0.95 | 0.855 |
| X shares address with Y | ICIJ | Panama Papers | 0.95 | 0.95 | 0.903 |
| X also appears as Z in OS | OpenSanctions | OpenSanctions | 0.85 | 0.98 | 0.833 |
| _add rows for every load-bearing claim_ | | | | | |

**Per-cluster aggregate:**

- Mean edge credibility: _____
- Number of edges from each source:
  - Panama / Paradise / Pandora / Bahamas / Offshore: _____
  - GLEIF / OpenSanctions: _____
  - UK PSC / UK disqualified: _____

---

## 4. Contradictory evidence considered

The architecture tracks contradictions explicitly via
`confidence_contradictions.parquet`. For each contradiction touching
this cluster, document:

| Contradiction | Loose-threshold community | Strict A | Strict B | What it implies |
| --- | --- | --- | --- | --- |
| nodes (a, b) split | C_lo | C_a | C_b | the edge that held them together is a soft link; is it structural or inferred? |

**What would falsify the cluster's investigative interest?** _List
the specific findings that would make you reject this cluster:_

1. _e.g., all members trace to a single corporate-secretary firm that
   bulk-incorporates for unrelated clients_
2. _e.g., the apparent jurisdiction bridge is a transliteration
   artefact, not real cross-border activity_
3. _e.g., the anomaly score is driven entirely by `same_name_as`
   inference edges that don't survive name re-canonicalisation_

**Evidence pursued (and outcome):**
_(narrate what falsifiers you actually checked and whether they hit)_

---

## 5. Uncertainty preserved

Quote the relevant formal-uncertainty numbers from
[`docs/reports/uncertainty_propagation.md`](../reports/uncertainty_propagation.md):

- Cluster confidence: _____  (λ-penalised)
- Mean edge credibility: _____
- Contradiction density: _____
- Path probabilities to any seed (sample): _____
- Cluster's contribution to graph entropy: _____

**Reading per the 4-cell verdict matrix:**
- [ ] High credibility + low entropy → **publication-grade**
- [ ] High credibility + high entropy → **gray-zone edges to investigate**
- [ ] Low credibility + low entropy → **confidently weak, do not publish**
- [ ] Low credibility + high entropy → **exploratory only**

---

## 6. External corroboration attempted

| Source | Query attempted | Result |
| --- | --- | --- |
| ICIJ Offshore Leaks UI | _(name)_ | _hits / no hits_ |
| OpenCorporates | _(name + juris)_ | _hits / no hits_ |
| OpenSanctions UI | _(name)_ | _hits / no hits_ |
| GLEIF | _(name or LEI)_ | _hits / no hits_ |
| UK Companies House | _(name or company number)_ | _hits / no hits_ |
| News / SEC filings / court records | _(query)_ | _hits / no hits_ |
| Other | _____ | _____ |

---

## 7. Verdict

Mark exactly one:

- [ ] **Confirmed novel.** Structural pattern survives every falsifier
      checked; not surfaceable from any single source; uncertainty
      preserved at publication-grade. → Feeds into
      [`docs/reports/publication_template.md`](../reports/publication_template.md).
- [ ] **Confirmed known.** Structural pattern is real but has been
      reported elsewhere. Useful as a calibration positive; not
      novel.
- [ ] **Rejected.** A specific falsifier hit (document below);
      cluster is an artefact.
- [ ] **Inconclusive.** Insufficient external evidence after
      reasonable search; revisit later.

**Reasoning:**
_(2–4 sentence justification for the verdict)_

**If confirmed novel — minimum publishable claim:**
_(write the single most defensible sentence about this cluster that
the uncertainty numbers support, without overreaching)_

---

## 8. Follow-up actions

- [ ] Add to publication report? (link the section)
- [ ] Add to `failed_investigations.md`? (if rejected)
- [ ] Add to calibration label set? (with confirm/reject label)
- [ ] Update edge / source priors based on findings?
- [ ] Open follow-up tickets:
  - _____

---

## Appendix — raw data references

- Cluster row in `confidence_cluster_scored.parquet`: community_id=_____
- Anomaly row in `confidence_community_anomalies.parquet`: community_id=_____
- Member list at threshold 0.9: `confidence_communities.parquet` filter
  `community_id == _____ AND threshold == 0.9`
- Internal edges: `confidence_graph_edges.parquet` filter both
  endpoints in member set
- Contradictions touching this cluster: `confidence_contradictions.parquet`
  filter `lo_community == _____`
- Review-priority edges to inspect: `confidence_review_priority.parquet`
  filter endpoints in member set
