# Validation queue — top candidates for manual deep-review

_Generated 2026-05-18 04:25 UTC from `processed/validation_queue.parquet` and
`processed/validation_queue_summary.json`._

This is the **input to Step 3 (manual validation)** of the four-step
discovery workflow. Each candidate below is a cluster ranked by a
single composite score combining four axes; the per-candidate cards
provide the supporting evidence a reviewer needs to start the workbook
in [`docs/validation/template.md`](../validation/template.md).

**This report is not a validation.** No cluster below has been
journalist-confirmed. The ranking is a triage queue.

## The composite score

```
priority = (strange ^ α) × (confident ^ β) × (connected ^ γ) × (underreported ^ δ)
```

with weights:

| Axis | Variable | Default weight | What it captures |
| --- | --- | ---: | --- |
| Structurally strange | α | **1.2** | Anomaly score from `confidence_community_anomalies.parquet` — high seed-density + isolation + size-deviation |
| High-confidence | β | **1.0** | `cluster_confidence` from formal uncertainty propagation (mean credibility × contradiction penalty) |
| Highly connected | γ | **0.7** | log(size) / log(max_size) — large clusters score higher |
| Underreported | δ | **1.3** | 1 − fraction of member names appearing in OS / GLEIF / UK PSC / UK disqualified |

Defaults privilege **weird + unreported** over **big + safe**. The α/δ
weighting was chosen so a strange-but-small cluster outranks a
large-but-attested one, on the basis that step 3 validation has the
most leverage on findings that are unreachable from single-source
search.

## Scope

Drawn from the dossier-anchored confidence subgraph (2-hop around 363 dossier seeds, ~7-8k nodes). This is more analytically rigorous than corpus-wide because it has the full uncertainty-propagation stack computed (mean_edge_credibility, contradiction_density, cluster_confidence). A v2 covering the full 3.3M-edge corpus would require running confidence-graph scoring at corpus scale, which is parked.

| Stat | Value |
| --- | ---: |
| Communities eligible (size ≥ 3) | 35 |
| Top-N surfaced here | 20 |
| Max cluster size in scope | 204 |
| Priority score — max | 0.5623 |
| Priority score — p95 | 0.4927 |
| Priority score — median | 0.2461 |
| Priority score — min | 0.0954 |

Attestation pools (size of each name set used for the underreported axis):

| Source | Names |
| --- | ---: |
| OpenSanctions | 116,542 |
| GLEIF | 0 |
| UK PSC | 0 |
| UK disqualified | 222 |
| Union | 116,764 |

## How to use this queue

1. Open [`docs/validation/template.md`](../validation/template.md).
2. For each candidate below, copy the template to
   `docs/validation/cluster_{community_id}.md` and fill in the
   structured sections (discovery path, graph evolution, provenance
   chain, contradictory evidence, uncertainty preserved, verdict).
3. After validation, the confirmed candidates feed into the
   publication template at
   [`docs/reports/publication_template.md`](publication_template.md).

## Candidates

### 1. Community #47

**Priority score:** **0.5623**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.773 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.791 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **67** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `EMBLA LTD`
- `MAYFAIR CAPITAL LTD`
- `INTEGRATED-CAPABILITIES LTD`
- `NG HOLDINGS LTD`
- `DAIKON INVESTMENTS LIMITED`
- `KALINA LTD (MALTA BRANCH)`
- `VERA YACHTING LTD`
- `CUDDY LTD`
- `Prism Lights Ltd.`
- `Crowd Shout Holdings Ltd.`

**Validation workbook:** create `docs/validation/cluster_47.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 2. Community #40

**Priority score:** **0.5571**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.687 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.956 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **161** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `HARTSWOOD INVESTMENTS LIMITED`
- `KIBLA INVESTMENTS LIMITED`
- `AUROUS INVESTMENTS LIMITED`
- `SAINT GEORGE DREDGING LIMITED`
- `SORBIT LIMITED`
- `SATIVA PROPERTIES LIMITED`
- `SABENA LIMITED`
- `SERRATA PROPERTIES LIMITED`
- `CLONARD INVESTMENTS LIMITED`
- `NORTHERN SKIES LIMITED`

**Validation workbook:** create `docs/validation/cluster_40.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 3. Community #38

**Priority score:** **0.4927**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.604 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 1.000 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **204** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `CUTTING EDGE MEDIA LIMITED`
- `TREVALI INVESTMENTS LIMITED`
- `MARE SERVICES LIMITED`
- `CROSSROADS HOLDINGS LIMITED`
- `8DEVICES EUROPE LIMITED`
- `icij:58030471`
- `DICK DASTARDLY CAPITAL MALTA LTD`
- `DUKE INVESTMENTS LIMITED`
- `XYLON LIMITED`
- `PETERBURI HOLDING LIMITED`

**Validation workbook:** create `docs/validation/cluster_38.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 4. Community #41

**Priority score:** **0.4814**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.607 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.958 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **163** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `PEREGON TRADING LIMITED`
- `HAAGSE POORT (HOLDINGS)(MALTA) PLC`
- `FTFIP A320 (Paris) LIMITED`
- `KANTARA ECLIPSE 1 LTD`
- `Sea Capital Holding Malta Limited`
- `TROY CAPITAL III LIMITED`
- `MENA JIF HOLDCO I LIMITED`
- `Frogmore Capital Limited`
- `ARCTICMED HOLDING LIMITED`
- `EUROPEAN CONVERGENCE DEVELOPMENT (MALTA) LIMITED`

**Validation workbook:** create `docs/validation/cluster_41.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 5. Community #42

**Priority score:** **0.4777**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.886 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.496 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **14** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `BUENAVISTA PROPERTIES LIMITED`
- `CASSELLA SERVICE COMPANY LIMITED`
- `CROSSKEY COMPUTERS LIMITED`
- `KRYPTON SERVICE COMPANY LIMITED`
- `DESMOND PROPERTIES LIMITED`
- `SAHARA PROPERTIES LIMITED`
- `AQUATICA PROPERTIES LIMITED`
- `CALDER ENTERPRISES LIMITED`
- `SUFFOLK INTERNATIONAL LIMITED`
- `VOXDALE PROPERTIES LIMITED`

**Validation workbook:** create `docs/validation/cluster_42.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 6. Community #36

**Priority score:** **0.4748**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.605 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.945 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **152** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `MAXIMILIAN STOCK LTD`
- `WEST QUAY LTD`
- `PLS HOLDING LIMITED`
- `COLUSSEUM HOLDINGS LIMITED`
- `CONSULTING ACE HOLDING LTD.`
- `FUNDATIO INTERNATIONAL LTD`
- `INDUSTRIAL SHIPPING SUPPLIES VEGA MARINE LIMITED`
- `SEPTAGON HOLDINGS LTD`
- `GLOBAL EBS GROUP LTD`
- `MERLINO YACHTING LTD`

**Validation workbook:** create `docs/validation/cluster_36.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 7. Community #39

**Priority score:** **0.4135**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.636 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.712 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **44** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `LINDA PROPERTIES LIMITED`
- `EVERIA CONSULTING LIMITED`
- `FLEXUS LIMITED`
- `RF MANAGEMENT LIMITED`
- `CLEAR WATER HOLDING LIMITED`
- `PRINCESS MANAGEMENT LIMITED`
- `PARK & FLY DEVELOPMENTS LIMITED`
- `SYNERIUM HOLDING LIMITED`
- `AMUSNET GAMING LIMITED`
- `IVESTA HOLDINGS LIMITED`

**Validation workbook:** create `docs/validation/cluster_39.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 8. Community #45

**Priority score:** **0.3671**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.723 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.482 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **13** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `SHERNON HOLDINGS LIMITED`
- `BELLA VISTA LIMITED`
- `icij:58016802`
- `M K MALTA LIMITED`
- `PRIMA DONNA LIMITED`
- `ENIGMA LIMITED`
- `INTERNATIONAL PARTICIPATIONS HOLDINGS LIMITED`
- `INTERNET MARKETING LIMITED`
- `MATCON INVESTMENTS LIMITED`
- `ARBOREA PROPERTIES LIMITED`

**Validation workbook:** create `docs/validation/cluster_45.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 9. Community #37

**Priority score:** **0.3645**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.663 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.554 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **19** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `LYON FINANCE LIMITED`
- `Bodog Music (Europe) Limited`
- `ROMAR FINANCE LIMITED`
- `Aragon Finance Limited`
- `Kiel Finance Limited`
- `STRATHAM FINANCE LIMITED`
- `COSMO (MALTA) LIMITED`
- `ESSER FINANCE LIMITED`
- `Nelson Finance Limited`
- `SAVOY FINANCE LIMITED`

**Validation workbook:** create `docs/validation/cluster_37.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 10. Community #51

**Priority score:** **0.3453**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.700 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.467 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **12** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `BRAINTREE PROPERTIES LIMITED`
- `ABBEYGLEN LIMITED`
- `RIGHT IMAGE LIMITED`
- `HARBOUR CORPORATE MALTA LIMITED`
- `IPROPERTY LIMITED`
- `IPM (MALTA) LIMITED`
- `CONFIANCE MALTA SERVICES LIMITED`
- `MARLBOROUGH T ADVISORY LIMITED`
- `MKI MALTA LIMITED`
- `BIELEFELD PROPERTIES LIMITED`

**Validation workbook:** create `docs/validation/cluster_51.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 11. Community #69

**Priority score:** **0.3212**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.627 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.509 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **15** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `AVIOS HOLDINGS LIMITED`
- `icij:58007511`
- `AGHINAGH LIMITED`
- `NUDE ESTATES MALTA LIMITED`
- `Agate International Finance Limited`
- `ABBIS INVESTMENTS LIMITED`
- `AVIOS LIMITED`
- `Agate Holdings Limited`
- `MEDITERRANEAN TEXTILES LIMITED`
- `FITZCARRALDO LIMITED`

**Validation workbook:** create `docs/validation/cluster_69.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 12. Community #55

**Priority score:** **0.3103**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.900 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.261 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **4** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `SEVERN HOLDINGS LIMITED`
- `icij:58045206`
- `SEVERN INVESTMENTS LIMITED`
- `CLARENDON PROPERTIES (MALTA) LIMITED`

**Validation workbook:** create `docs/validation/cluster_55.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 13. Community #46

**Priority score:** **0.2694**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.800 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.261 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **4** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `TRACY JANE POZO`
- `icij:58044872`
- `icij:58045753`
- `TRACY JANE POZO`

**Validation workbook:** create `docs/validation/cluster_46.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 14. Community #52

**Priority score:** **0.2694**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.800 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.261 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **4** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `BEGNA CAPITAL AS`
- `TRINITY TRADING LIMITED`
- `TRINITY HOLDINGS LIMITED`
- `icij:58080709`

**Validation workbook:** create `docs/validation/cluster_52.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 15. Community #50

**Priority score:** **0.2520**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.867 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.207 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **3** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `PETER KEVIN PERRY`
- `PETER KEVIN PERRY`
- `icij:58031372`

**Validation workbook:** create `docs/validation/cluster_50.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 16. Community #64

**Priority score:** **0.2520**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.867 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.207 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **3** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `icij:58029412`
- `NILS PETER GRUT`
- `NILS PETER GRUT`

**Validation workbook:** create `docs/validation/cluster_64.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 17. Community #72

**Priority score:** **0.2520**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.867 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.207 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **3** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `TEMPUS FUGIT LTD`
- `icij:58021661`
- `DAIMA YACHTING LIMITED`

**Validation workbook:** create `docs/validation/cluster_72.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 18. Community #65

**Priority score:** **0.2461**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.680 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.303 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **5** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `icij:58073250`
- `icij:58057066`
- `DAVID JAMES MASON`
- `icij:58045194`
- `SEVERN INVESTMENTS LIMITED`

**Validation workbook:** create `docs/validation/cluster_65.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 19. Community #70

**Priority score:** **0.2118**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.600 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.303 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **5** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `ADRIANO CEFAI`
- `CHRISTIAN ELLUL`
- `FIDES FIDUCIARY LIMITED`
- `icij:58038552`
- `FIDES CORPORATE SERVICES LIMITED`

**Validation workbook:** create `docs/validation/cluster_70.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

### 20. Community #49

**Priority score:** **0.2062**

**Score breakdown:**

| Axis | Value |
| --- | ---: |
| Structurally strange (anomaly) | 0.733 |
| High-confidence (cluster_confidence) | 0.902 |
| Highly connected (log-size norm) | 0.207 |
| Underreported (1 − attestation density) | 1.000 |

**Cluster diagnostics:**

- Size: **3** entities
- Mean edge credibility: 0.902
- Contradiction density: 0.000
- Seed nodes (from dossier set): 0
- Isolation: 1.000
- Attestation density: 0.000 (low = underreported)

**Member sample (first 10):**

- `AB YACHTING LTD`
- `icij:58042501`
- `SANTHILL LIMITED`

**Validation workbook:** create `docs/validation/cluster_49.md` from [`docs/validation/template.md`](../validation/template.md) and complete the structured review.

---

## Caveats

1. **Scope is dossier-anchored.** The confidence subgraph anchors on
   363 dossier seeds. A truly corpus-wide variant (running confidence-
   graph scoring on all 3.3M edges) would change the queue
   composition; that's parked because it requires non-trivial Railway
   re-architecture.
2. **Attestation is name-equality.** A name matching in OS / GLEIF /
   UK PSC does not confirm same-entity; it only proves the lower bound
   that something with the same name is in that registry. Used here as
   a *very* conservative "is this entity even reachable from formal
   sources" proxy.
3. **Priority ≠ truth.** A high priority score means the cluster is
   the highest-leverage candidate for manual review; it does not mean
   the cluster represents real coordinated activity. Step 3 is where
   that determination happens.
4. **Weights are operator-set.** Defaults (α=1.2, β=1.0, γ=0.7,
   δ=1.3) are documented choices, not learned. Re-rank with different
   exponents by passing `--alpha / --beta / --gamma / --delta` to
   `build_validation_queue.py`.

## Reproduce

```bash
just job-run build_validation_queue
just job-fetch processed/validation_queue.parquet docs/reports/data/
just job-fetch processed/validation_queue_summary.json docs/reports/data/

uv run python scripts/render_validation_queue.py \
    --queue docs/reports/data/validation_queue.parquet \
    --summary docs/reports/data/validation_queue_summary.json \
    --out docs/reports/validation_queue.md
```

Or trigger `.github/workflows/build-validation-queue.yml`.
