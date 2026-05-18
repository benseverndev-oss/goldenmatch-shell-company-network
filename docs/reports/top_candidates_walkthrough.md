# Top-candidate walkthrough — per-entity novelty proof

_Generated 2026-05-18 00:22 UTC from `processed/top_candidates_walkthrough.json`.
Companion to [`discovery_advantage.md`](discovery_advantage.md)._

## What this report does

The Discovery Advantage Report quantifies the delta between baseline
and pipeline workflows across the corpus. This report drills down: it
picks **11 specific candidates** from 5 surfacing
channels and, for each one, shows exactly which sources confirm it,
what each single-source query would have returned, and why the
pipeline's view is the novel one.

This is the closing argument made entity-by-entity, not in aggregate.

## How to read each candidate

Each candidate below has:

- **Channel** — which surfacing channel ranked it
- **Source attestation** — `✓`/`✗` against OpenSanctions, GLEIF, UK
  PSC, UK disqualified, with hit counts
- **Baseline view** — what a journalist using single-source search
  would see today
- **Pipeline view** — what GoldenMatch surfaces
- **Novelty proof** — the structural reason the pipeline's view is
  not reachable from any single source

Source attestation is by **name-equality (casefold)** on the canonical
name column of each source. A `✓` means the name appears in that
source; a `✗` means it does not. Hits do not imply the entity is the
same individual — name collisions exist. They prove the lower bound
that single-source search returns *something*.

## Channels covered

| Channel | Candidates |
|---|---:|
| Cross-jurisdiction officer bridge | 2 |
| Louvain community (anomaly-only) | 2 |
| Louvain community (sanctions-adjacent) | 1 |
| Non-obviousness-ranked rare officer | 3 |
| Shared intermediary reuse | 3 |

## Candidates

### 1. Shared intermediary: CF INDUSTRIES (BARBADOS) SRL

**Channel:** `shared_agent_reuse` — Shared intermediary reuse

**UID:** `icij:101300076`

**Metadata:** `name` = CF INDUSTRIES (BARBADOS) SRL · `jurisdiction` = Barbados · `type` = entity · `source_label` = Paradise Papers - Barbados corporate registry

**Metric:**

- `n_clients`: 5

**Client sample:** `icij:135015260`, `icij:135029244`, `icij:135044324`, `icij:135047559`, `icij:130000006`

**Source attestation:** `opensanctions` ✗ (0) · `gleif` ✗ (0)

**Baseline view (single-source):** ICIJ Offshore Leaks search for "CF INDUSTRIES (BARBADOS) SRL" returns the intermediary entity itself, but does not aggregate that this intermediary acts for 5 distinct officers across the leak corpus. OpenSanctions and GLEIF have no entry — this intermediary is not sanctioned and not LEI-registered, so single-source search filters it out as non-actionable.

**Pipeline view:** The pipeline ranks this intermediary by client multiplicity (5 distinct officers), surfacing it as a shared-agent hub the single-source view cannot compute. Combined with the absence of sanctions/LEI registration, the structural pattern (reuse without formal-registry trace) is the investigative signal.

**Novelty proof:** Structural aggregation across ICIJ edges. Single-source views are per-entity; the multiplicity count requires walking the edges, which no source's search UI exposes.

---

### 2. Shared intermediary: Rhombus No.2 Limited

**Channel:** `shared_agent_reuse` — Shared intermediary reuse

**UID:** `icij:82019585`

**Metadata:** `name` = Rhombus No.2 Limited · `jurisdiction` = gg · `type` = entity · `source_label` = Paradise Papers - Appleby

**Metric:**

- `n_clients`: 4

**Client sample:** `icij:80010696`, `icij:80043197`, `icij:80069418`, `icij:80109672`

**Source attestation:** `opensanctions` ✗ (0) · `gleif` ✗ (0)

**Baseline view (single-source):** ICIJ Offshore Leaks search for "Rhombus No.2 Limited" returns the intermediary entity itself, but does not aggregate that this intermediary acts for 4 distinct officers across the leak corpus. OpenSanctions and GLEIF have no entry — this intermediary is not sanctioned and not LEI-registered, so single-source search filters it out as non-actionable.

**Pipeline view:** The pipeline ranks this intermediary by client multiplicity (4 distinct officers), surfacing it as a shared-agent hub the single-source view cannot compute. Combined with the absence of sanctions/LEI registration, the structural pattern (reuse without formal-registry trace) is the investigative signal.

**Novelty proof:** Structural aggregation across ICIJ edges. Single-source views are per-entity; the multiplicity count requires walking the edges, which no source's search UI exposes.

---

### 3. Shared intermediary: GULFSTREAM PETROLEUM SRL

**Channel:** `shared_agent_reuse` — Shared intermediary reuse

**UID:** `icij:101300442`

**Metadata:** `name` = GULFSTREAM PETROLEUM SRL · `jurisdiction` = Barbados · `type` = entity · `source_label` = Paradise Papers - Barbados corporate registry

**Metric:**

- `n_clients`: 4

**Client sample:** `icij:135031894`, `icij:135066503`, `icij:135089016`, `icij:130000012`

**Source attestation:** `opensanctions` ✗ (0) · `gleif` ✗ (0)

**Baseline view (single-source):** ICIJ Offshore Leaks search for "GULFSTREAM PETROLEUM SRL" returns the intermediary entity itself, but does not aggregate that this intermediary acts for 4 distinct officers across the leak corpus. OpenSanctions and GLEIF have no entry — this intermediary is not sanctioned and not LEI-registered, so single-source search filters it out as non-actionable.

**Pipeline view:** The pipeline ranks this intermediary by client multiplicity (4 distinct officers), surfacing it as a shared-agent hub the single-source view cannot compute. Combined with the absence of sanctions/LEI registration, the structural pattern (reuse without formal-registry trace) is the investigative signal.

**Novelty proof:** Structural aggregation across ICIJ edges. Single-source views are per-entity; the multiplicity count requires walking the edges, which no source's search UI exposes.

---

### 4. Bridge officer: Banks - Samuel Andrew (us ↔ ky)

**Channel:** `jurisdiction_bridge` — Cross-jurisdiction officer bridge

**UID:** `icij:80033141`

**Metadata:** `name` = Banks - Samuel Andrew · `type` = officer · `source_label` = Paradise Papers - Appleby

**Metric:**

- `juris_a`: us
- `juris_b`: ky
- `company_a`: Paradigm USA Consulting Inc
- `company_b`: DM Holdings GP Limited

**Source attestation:** `opensanctions` ✗ (0) · `uk_psc` ✗ (0) · `uk_disqualified` ✗ (0)

**Baseline view (single-source):** ICIJ search for "Banks - Samuel Andrew" returns the two companies separately — `Paradigm USA Consulting Inc` (us) and `DM Holdings GP Limited` (ky) — but does not flag the offshore-mainstream jurisdictional bridge as a structural pattern. UK PSC, UK disqualified-directors, and OpenSanctions would each be queried independently with no automatic correlation.

**Pipeline view:** The pipeline flags this officer because two companies they control span an offshore venue (us) and a mainstream venue (ky). The bridge is the structural pattern, not the per-company filings.

**Novelty proof:** Cross-jurisdiction pair detection requires (a) officer-deduplication across companies and (b) jurisdiction classification — neither is an out-of-the-box capability in any source's interface.

---

### 5. Bridge officer: Pullen - Douglas H. (bm ↔ us)

**Channel:** `jurisdiction_bridge` — Cross-jurisdiction officer bridge

**UID:** `icij:80114736`

**Metadata:** `name` = Pullen - Douglas H. · `jurisdiction` = bm · `type` = officer · `source_label` = Paradise Papers - Appleby

**Metric:**

- `juris_a`: bm
- `juris_b`: us
- `company_a`: North American Manufacturers Insurance Company Limited
- `company_b`: Numar Honduras, Ltd.

**Source attestation:** `opensanctions` ✗ (0) · `uk_psc` ✗ (0) · `uk_disqualified` ✗ (0)

**Baseline view (single-source):** ICIJ search for "Pullen - Douglas H." returns the two companies separately — `North American Manufacturers Insurance Company Limited` (bm) and `Numar Honduras, Ltd.` (us) — but does not flag the offshore-mainstream jurisdictional bridge as a structural pattern. UK PSC, UK disqualified-directors, and OpenSanctions would each be queried independently with no automatic correlation.

**Pipeline view:** The pipeline flags this officer because two companies they control span an offshore venue (bm) and a mainstream venue (us). The bridge is the structural pattern, not the per-company filings.

**Novelty proof:** Cross-jurisdiction pair detection requires (a) officer-deduplication across companies and (b) jurisdiction classification — neither is an out-of-the-box capability in any source's interface.

---

### 6. Community #2762: 173-entity sanctions-adjacent cluster

**Channel:** `louvain_sanctions_adjacent` — Louvain community (sanctions-adjacent)

**UID:** `community:2762`

**Metadata:** `jurisdictions` = hk;mt;vg · `n_sanctioned` = 1

**Metric:**

- `community_id`: 2762
- `size`: 173
- `anomaly_score`: 0.4205
- `jurisdictions`: hk;mt;vg
- `n_sanctioned`: 1

**Baseline view (single-source):** No source surfaces communities — none of ICIJ, OpenSanctions, GLEIF, UK PSC, or UK disqualified-directors expose graph-cluster structure. A journalist could only assemble this cluster by iteratively querying related entities one at a time. The cluster contains 1 sanctioned entity, so only that single entity would surface in OpenSanctions; the surrounding 172 entities would not.

**Pipeline view:** Louvain community detection on credibility-weighted edges surfaces this 173-entity cluster spanning hk;mt;vg with anomaly score 0.420. The community structure is the investigative signal, not any single entity in it.

**Novelty proof:** Unsupervised graph clustering produces a structural finding that has no direct analogue in any source. The community is fully synthesised by the pipeline.

---

### 7. Community #1878: 78-entity pure-anomaly cluster

**Channel:** `louvain_anomaly_only` — Louvain community (anomaly-only)

**UID:** `community:1878`

**Metadata:** `jurisdictions` = pa;us;vg · `n_sanctioned` = 0

**Metric:**

- `community_id`: 1878
- `size`: 78
- `anomaly_score`: 0.4543
- `jurisdictions`: pa;us;vg
- `n_sanctioned`: 0

**Baseline view (single-source):** No source surfaces communities — none of ICIJ, OpenSanctions, GLEIF, UK PSC, or UK disqualified-directors expose graph-cluster structure. A journalist could only assemble this cluster by iteratively querying related entities one at a time. No entity in the cluster is sanctioned, so OpenSanctions search returns nothing — the cluster is invisible to that lens entirely.

**Pipeline view:** Louvain community detection on credibility-weighted edges surfaces this 78-entity cluster spanning pa;us;vg with anomaly score 0.454. The community structure is the investigative signal, not any single entity in it.

**Novelty proof:** Unsupervised graph clustering produces a structural finding that has no direct analogue in any source. The community is fully synthesised by the pipeline.

---

### 8. Community #377: 115-entity pure-anomaly cluster

**Channel:** `louvain_anomaly_only` — Louvain community (anomaly-only)

**UID:** `community:377`

**Metadata:** `jurisdictions` = cy;vg · `n_sanctioned` = 0

**Metric:**

- `community_id`: 377
- `size`: 115
- `anomaly_score`: 0.444
- `jurisdictions`: cy;vg
- `n_sanctioned`: 0

**Baseline view (single-source):** No source surfaces communities — none of ICIJ, OpenSanctions, GLEIF, UK PSC, or UK disqualified-directors expose graph-cluster structure. A journalist could only assemble this cluster by iteratively querying related entities one at a time. No entity in the cluster is sanctioned, so OpenSanctions search returns nothing — the cluster is invisible to that lens entirely.

**Pipeline view:** Louvain community detection on credibility-weighted edges surfaces this 115-entity cluster spanning cy;vg with anomaly score 0.444. The community structure is the investigative signal, not any single entity in it.

**Novelty proof:** Unsupervised graph clustering produces a structural finding that has no direct analogue in any source. The community is fully synthesised by the pipeline.

---

### 9. Rare-officer anchor: philippe le gall

**Channel:** `non_obviousness_rank` — Non-obviousness-ranked rare officer

**UID:** `name:philippe le gall`

**Metric:**

- `non_obviousness_score`: 0.5332
- `rarity`: 0.5735
- `graph_surprise`: 1.0
- `pattern_uniqueness`: 0.7778
- `jurisdiction_span`: 1

**Source attestation:** `opensanctions` ✗ (0) · `uk_psc` ✗ (0) · `uk_disqualified` ✗ (0)

**Baseline view (single-source):** ICIJ search for "philippe le gall" returns the officer record(s). OpenSanctions, UK PSC, and UK disqualified-directors are queried separately; nothing in any single-source UI tells the journalist that this name carries an unusually high 5-factor non-obviousness signal (rarity 0.57, graph-surprise 1.00, pattern-uniqueness 0.78).

**Pipeline view:** The non-obviousness scorer combines name-rarity, jurisdiction-span, graph-surprise, shared-intermediary, and pattern-uniqueness into one ranked score (here 0.533). This anchor is in the top-10 out of 50 scored anchors — without that composite, a journalist would have no reason to prioritise it.

**Novelty proof:** Five orthogonal weak signals composed into one strong ranking. Each input signal is computable from a single source; the composition across sources is the pipeline's contribution.

---

### 10. Rare-officer anchor: javed ali khan

**Channel:** `non_obviousness_rank` — Non-obviousness-ranked rare officer

**UID:** `name:javed ali khan`

**Metric:**

- `non_obviousness_score`: 0.5109
- `rarity`: 0.5735
- `graph_surprise`: 1.0
- `pattern_uniqueness`: 0.5556
- `jurisdiction_span`: 1

**Source attestation:** `opensanctions` ✗ (0) · `uk_psc` ✗ (0) · `uk_disqualified` ✗ (0)

**Baseline view (single-source):** ICIJ search for "javed ali khan" returns the officer record(s). OpenSanctions, UK PSC, and UK disqualified-directors are queried separately; nothing in any single-source UI tells the journalist that this name carries an unusually high 5-factor non-obviousness signal (rarity 0.57, graph-surprise 1.00, pattern-uniqueness 0.56).

**Pipeline view:** The non-obviousness scorer combines name-rarity, jurisdiction-span, graph-surprise, shared-intermediary, and pattern-uniqueness into one ranked score (here 0.511). This anchor is in the top-10 out of 50 scored anchors — without that composite, a journalist would have no reason to prioritise it.

**Novelty proof:** Five orthogonal weak signals composed into one strong ranking. Each input signal is computable from a single source; the composition across sources is the pipeline's contribution.

---

### 11. Rare-officer anchor: john o connor

**Channel:** `non_obviousness_rank` — Non-obviousness-ranked rare officer

**UID:** `name:john o connor`

**Metric:**

- `non_obviousness_score`: 0.5079
- `rarity`: 0.4893
- `graph_surprise`: 1.0
- `pattern_uniqueness`: 0.7778
- `jurisdiction_span`: 1

**Source attestation:** `opensanctions` ✗ (0) · `uk_psc` ✗ (0) · `uk_disqualified` ✗ (0)

**Baseline view (single-source):** ICIJ search for "john o connor" returns the officer record(s). OpenSanctions, UK PSC, and UK disqualified-directors are queried separately; nothing in any single-source UI tells the journalist that this name carries an unusually high 5-factor non-obviousness signal (rarity 0.49, graph-surprise 1.00, pattern-uniqueness 0.78).

**Pipeline view:** The non-obviousness scorer combines name-rarity, jurisdiction-span, graph-surprise, shared-intermediary, and pattern-uniqueness into one ranked score (here 0.508). This anchor is in the top-10 out of 50 scored anchors — without that composite, a journalist would have no reason to prioritise it.

**Novelty proof:** Five orthogonal weak signals composed into one strong ranking. Each input signal is computable from a single source; the composition across sources is the pipeline's contribution.

---

## How to interpret across channels

- **Shared intermediaries** are aggregations: every input edge is in
  ICIJ, but no ICIJ UI surfaces the multiplicity. The pipeline's
  contribution is the count and the ranking.
- **Jurisdiction bridges** require officer deduplication + jurisdiction
  classification. They cannot be queried for in any source.
- **Louvain communities** are entirely synthesised. No source has any
  community structure; the cluster *is* the pipeline's output.
- **Non-obviousness-ranked rare officers** combine five orthogonal
  signals into one score; the composition crosses sources even when
  any single input is single-source.

## Caveats

1. **Source attestation is name-equality.** A `✓` confirms the name is
   present in that source; it does not confirm same-person identity.
   A v2 would resolve via deterministic IDs (LEI, PSC officer number)
   where available.
2. **Member samples are heuristic.** For Louvain communities, member
   samples are first-20-by-row-order, not centrality-ranked. Reading
   them as "the most important members" overstates the resolution.
3. **No journalist confirmation.** These are operational signals, not
   journalist-validated exposés. See
   [`discovery_advantage.md`](discovery_advantage.md) §"Analyst review
   outcomes" for the v2 panel-study gap.

## Reproduce

```bash
just job-run build_top_candidates_walkthrough
just job-fetch processed/top_candidates_walkthrough.json docs/reports/data/

uv run python scripts/render_top_candidates_walkthrough.py \
    --summary docs/reports/data/top_candidates_walkthrough.json \
    --out docs/reports/top_candidates_walkthrough.md
```

Or trigger `.github/workflows/build-top-candidates-walkthrough.yml`.
