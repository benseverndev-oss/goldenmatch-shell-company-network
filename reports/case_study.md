# A reproducible case study: linking offshore-leak entities to the LEI registry

**Subject:** Phoenix Spree Deutschland — a series of Jersey-incorporated SPVs
that appear simultaneously in the Paradise Papers (Appleby) leak and in the
GLEIF authoritative LEI registry. The case study uses this cluster to
demonstrate end-to-end entity resolution across four public datasets, and
documents how an initial pass produced widespread leading-token false
positives that a tightened configuration removed.

This is research-engineering output. Membership in the ICIJ Offshore Leaks
Database does **not** imply wrongdoing. Many entities here are legitimate
corporate structures. Findings below are hypotheses produced by a fuzzy
matcher and a heuristic precision review; nothing here should be treated as
proof of anything about any specific company or individual without
independent human review.

---

## 1. Motivation

Offshore-entity records published by the ICIJ are noisy by design: the
same legal entity often appears under slight name variants across multiple
leaks, and many entries lack a registry identifier. Linking those records
to the GLEIF Legal Entity Identifier (LEI) registry — which is
authoritative and CC0-licensed — gives investigators a stable anchor to
hang further analysis from.

The case study answers three concrete questions:

1. Can a modest entity-resolution pipeline link real ICIJ entities to
   their GLEIF counterparts at scale, without supervision?
2. How much does a sensible-looking starter configuration over-link
   (false positives) on this kind of data?
3. What does a tightened configuration buy you, in measurable precision
   and recall numbers?

## 2. Data

| Source | Role | License | Snapshot | Rows |
| --- | --- | --- | --- | ---: |
| [ICIJ Offshore Leaks](https://offshoreleaks.icij.org/) | Primary entities + relationships | Non-commercial research | 2025-03-31 (`full-oldb.LATEST.zip`) | 814,344 entities; 402,246 addresses; 771,315 officers; 25,629 intermediaries; 3,339,267 edges |
| [GLEIF Golden Copy](https://www.gleif.org/en/lei-data) | Authoritative LEI records | CC0 | 2026-05-11 | 3,304,422 LEI records |
| [OpenSanctions](https://www.opensanctions.org/) `us_ofac_sdn` | Enrichment (sanctions) | CC-BY 4.0 | 2026-05-11 | 70,301 FtM entities (~9,611 of `Company`/`Organization`/`LegalEntity` schema) |
| [OpenCorporates](https://opencorporates.com/) | Registry-anchored companies | API + per-jurisdiction licences | _not ingested in this pass_ | — |

After ingestion the company-side records were fused into a single unified
table of 4,128,377 rows in the schema
`entity_uid, source, source_id, name, normalized_name, jurisdiction,
company_number, lei, status, legal_form, address_raw, normalized_address`.

The GLEIF Golden Copy is distributed as a ~13 GB single-document JSON in
the CDF format. The repo's original v1-API adapter reads files via
`Path.read_text()`, which would OOM on this input, so a streaming adapter
(`shellnet.sources.gleif_golden_copy`) was built around `ijson` with
100k-row parquet chunking; peak memory stayed under 1 GB during the
ingest.

## 3. Method

Pipeline (each stage materialises a parquet/CSV artifact for replay):

```
zip upload  →  unzip  →  ingest (per source)  →  build unified table
                                                            │
filter (drop placeholder names + mega-blocks)  ←  ────────  ┘
            │
            v
        dedupe (GoldenMatch dedupe, ICIJ + OpenSanctions only)
            │
            v
        match-against (target = deduped table; reference = GLEIF unified)
            │
            v
        publish to Postgres (shellnet.runs, .clusters, .same_as_pairs, .list_matches)
```

A full pairwise dedupe of all 4.1M rows (ICIJ + GLEIF + OpenSanctions)
did not fit on a 24 GB / 24 vCPU service — it ran for 76 minutes and
OOM'd during the scoring/clustering phase. List-matching (`goldenmatch
match TARGET --against REFERENCE`) is the supported shape at this
scale: each target row streams against the reference's blocks rather
than holding the full pairwise comparison in memory. The list-match
against GLEIF ran in 10 minutes and peaked at ~7 GB.

### Configuration tighten: v1 → v2

The v1 configuration used `jaro_winkler` on `normalized_name` with
threshold 0.85 — a sensible-looking starter. Spot-checking the first
matches revealed a systematic failure mode: clusters of unrelated
companies grouped by a shared leading word (`CRYSTAL FINANCE LTD.`,
`CRYSTAL BAY INTERNATIONAL INC.`, `CRYSTAL INVESTMENTS LIMITED` — all
British Virgin Islands, all in the Panama Papers, all different
shell companies). `jaro_winkler` over-rewards prefix agreement.

v2 swapped the name scorer to `token_sort` (which compares the bag of
tokens after sort, ignoring leading-position bias) and raised the
threshold to 0.92. Two `negative_evidence` clauses on `lei` and
`company_number` were configured but disabled — they crashed the
`match` subcommand with a polars schema error in GoldenMatch 1.12.x
even though they work in `dedupe`. The scorer + threshold change
alone is the load-bearing precision improvement.

Pre-filtering removes 4 mega-blocks (`stichtin||nl`, `the trus||au`,
two JP master-trust patterns) that exceed `max_block_size=5000` on the
`(substring:0:8, jurisdiction)` blocking key — about 53,000 rows
total, or 1.3% of the unified table. These rows are legitimate (Dutch
foundations, Australian trustee companies, Japanese custody vehicles)
but they collide on the blocking key in numbers that make pairwise
scoring intractable. The same filter applies to the GLEIF reference
file.

## 4. The spotlight cluster — Phoenix Spree Deutschland

**Cluster `503264` in v2 dedupe run `ba237a6c-...`.** Nine ICIJ
entries, all Jersey-incorporated, all from the Paradise Papers
(Appleby leak). Eight of the nine map to GLEIF LEI records at score
1.0; the ninth (Phoenix Spree Deutschland VI) maps to its closest
available GLEIF reference at score 0.987 (more on that below).

### 4.1 Members

| # | ICIJ entity | jurisdiction | matched GLEIF LEI | GLEIF legal name |
| ---: | --- | --- | --- | --- |
| 1 | Phoenix Spree Deutschland I Limited | je | `529900MQU3XI11P2FM74` | PHOENIX SPREE DEUTSCHLAND I LIMITED |
| 2 | Phoenix Spree Deutschland II Limited | je | `529900Z5VU6N5X7FKD32` | PHOENIX SPREE DEUTSCHLAND II LIMITED |
| 3 | Phoenix Spree Deutschland III Limited | je | `529900J6YOTOZ4XU6086` | PHOENIX SPREE DEUTSCHLAND III LIMITED |
| 4 | Phoenix Spree Deutschland IV Limited | je | `529900HE7LFLCQMZ7Y77` | PHOENIX SPREE DEUTSCHLAND IV LIMITED |
| 5 | Phoenix Spree Deutschland V Limited | je | `529900MYUEKOW0KRP666` | PHOENIX SPREE DEUTSCHLAND V LIMITED |
| 6 | Phoenix Spree Deutschland VI Limited | je | `529900ZH4XA9K4B3EP79` ⚠ | PHOENIX SPREE DEUTSCHLAND **VII** LIMITED |
| 7 | Phoenix Spree Deutschland VII Limited | je | `529900ZH4XA9K4B3EP79` | PHOENIX SPREE DEUTSCHLAND VII LIMITED |
| 8 | Phoenix Spree Deutschland IX Limited | je | `529900D1RM39KSHWIV43` | PHOENIX SPREE DEUTSCHLAND IX LIMITED |
| 9 | Phoenix Spree Deutschland Limited (parent) | je | `213800OR6IIJPG98AG39` | PHOENIX SPREE DEUTSCHLAND LIMITED |

Phoenix Spree Deutschland Limited (the parent in row 9) was a
publicly-listed real-estate investment company that held Berlin and
Frankfurt residential property through this series of Jersey SPVs.
The roman-numeral sub-funds are a textbook structured-finance pattern.

### 4.2 An honest edge case: VI → VII

Row 6 is the only non-perfect match in the cluster, and worth
calling out. The matcher links ICIJ's `Phoenix Spree Deutschland VI
Limited` to GLEIF's `PHOENIX SPREE DEUTSCHLAND VII LIMITED` at
score 0.987. The reason: with `--match-mode best`, each target row
receives the single best reference match available. GLEIF appears
not to have an LEI record for Phoenix Spree Deutschland **VI**, so
the closest available reference for VI is VII.

This is **not** a claim that VI and VII are the same entity. It is
a structural observation: VI exists in the leak but seemingly never
acquired (or has since let lapse) an LEI registration. VIII is also
absent on both sides. A reader of the case study should treat the
VI row as an unresolved lookup and downgrade their confidence in
that single line.

### 4.3 Why the cluster is internally trustworthy

The eight Phoenix Spree rows that map to their own LEI at score
1.0 are mutually consistent on every available signal: same legal
name (modulo case), same jurisdiction (Jersey), same parent
(Phoenix Spree Deutschland Limited), and they share officer
relationships across the leak. Each member entity carries 20–46
officer / address / power-of-attorney edges in the Paradise
Papers data; the shared officers (`icij:80061377`, `icij:80061378`,
`icij:80061382`, `icij:80114532`) appear as `director_of` on
multiple members. That officer overlap is independent corroboration
that the entities share a corporate-services backbone, which is the
Appleby pattern these SPVs were structured under.

The full edge list for each member is in
[`reports/case_studies/503264_phoenix_spree_deutschland.md`](case_studies/503264_phoenix_spree_deutschland.md).

## 5. Evaluation

A precision/recall comparison of v1 vs v2 requires a ground-truth
label set. We sampled 300 pairs across four buckets stratified to
make the most leveraged validation questions answerable:

| bucket | n | what it samples |
| --- | ---: | --- |
| `v1_dropped` | 100 | pairs in v1 with score 0.85–0.92; v2's threshold raise removed these |
| `v2_marginal` | 100 | pairs v2 kept in the 0.92–0.97 band |
| `perfect_sanity` | 50 | random pairs from v1 with score ≥ 0.99 |
| `v2_borderline_class` | 50 | v2 keeps in the `jur_close` + `jur_loose` heuristic classes |

The labels are AI-assisted research labels, **not human ground truth**.
The labeller's methodology, sources of evidence, and limitations are
documented in
[`data/labels/marginal_v1_methodology.md`](../data/labels/marginal_v1_methodology.md).
Treat all eval findings below as preliminary and flag for human review
before any external publication.

### 5.1 Headline

| metric | v1 (jaro_winkler, 0.85) | v2 (token_sort, 0.92) | delta |
| --- | ---: | ---: | ---: |
| matched pairs | 20,297 | 5,630 | -14,667 |
| estimated precision (strict) | 43.7% | **94.4%** | +50.7 pp |
| estimated precision (generous) | 54.1% | 95.6% | +41.5 pp |

The strict/generous spread is the contribution of pairs the labeller
marked `unsure` (treat as drop / treat as match respectively). The
v1 estimate is conservative — see the eval report for the
borderline-band caveat.

### 5.2 Per-band precision in v2

Precision computed on the labelled sample's intersection with the
published v2 run, stratified by score band:

| v2 band | label-match | label-no_match | label-unsure | strict | generous |
| --- | ---: | ---: | ---: | ---: | ---: |
| perfect (≥ 0.99) | 58 | 0 | 0 | **1.000** | 1.000 |
| high (0.95–0.99) | 14 | 33 | 10 | 0.298 | 0.421 |
| borderline (0.92–0.95) | 30 | 34 | 21 | 0.469 | 0.600 |

The perfect band is effectively 100% precision. The high band is
the surprising one — its precision in this sample is lower than the
borderline band. That's a sampling artefact: I deliberately
over-sampled heuristic-flagged (`jur_close` + `jur_loose`) pairs in
the `v2_borderline_class` bucket, and many of them land in the
0.95–0.99 score range. So the high-band number is *not* a fair
estimate of v2's overall precision in that band — it's a fair
estimate of v2's precision in the heuristic-flagged subset of that
band, which is what we wanted to know.

### 5.3 Recall cost

Of the 100 `v1_dropped` pairs (v1 had them at 0.85–0.92, v2
removed them):

- **81** labelled `no_match` — v2 correctly killed an FP.
- **6** labelled `match` — v2 lost real signal.
- **13** labelled `unsure`.

So v2's threshold raise lost between **6% and 19% recall** in the
0.85–0.92 band, depending on how you treat `unsure`. The 6
confirmed losses share a single pattern: identical legal name +
same jurisdiction, with the address-component score depressed
below 0.92 because the two leak captures recorded different
point-in-time addresses for the same company. That's a specific,
addressable failure mode — a future iteration could special-case
"name-equal + jurisdiction-equal with address conflict" rather
than averaging the address divergence into the weighted score.

### 5.4 Failure modes worth flagging for the next iteration

From inspecting the unsure and FP rows across the four buckets:

1. **Sequential sub-vehicles in the same jurisdiction.** `PA Grand
   Opportunity II Limited` vs `PA Grand Opportunity Limited`,
   `Mapeley Beta Acquisition Co (4) Limited` vs `(1)`, `Windsor
   Properties (6)` vs `Windsor Properties Limited`. Token-sort
   doesn't penalise the missing or differing `(N)` / roman-numeral
   suffix because token-sort is, by construction, order-invariant.
   A scorer that treats numeric or parenthetical suffixes as
   required-equal would catch this class — the dominant FP pattern
   in the v2_marginal band.
2. **CLO `Trust` vs `Ltd` ICIJ recording artefact.** Multiple ICIJ
   entries record one CLO as both `Foo CLO Ltd` and `Foo CLO Ltd.
   Trust`. These could be the same legal entity recorded twice or
   distinct trust + Ltd vehicles. A normalisation rule that strips
   trailing `Trust` and treats those rows as duplicates would
   reduce noise.
3. **Refinanced CLOs `(M)-R`.** `Golub Capital Partners CLO 21(M)`
   vs `21(M)-R` — same underlying CLO, refinanced. Probably the
   same legal entity post-refi but possibly distinct vehicles.
4. **Address divergence on identical names** (the 6 v1_dropped
   confirmed matches). Covered above.

## 6. Structural findings

Beyond the cluster level, the merged graph surfaces structural
patterns that name-matching alone can't.

The merged graph has 2.03M nodes (823K company nodes + 1.2M
person/officer nodes) and roughly 3.4M edges from the ICIJ source
relationships plus 4,272 `same_as` edges layered on top from the
cross-source list-match.

Running centrality on the **cluster sub-graph** (the 18,003
multi-member-cluster members plus their direct ICIJ neighbours =
50,998 nodes, 75,011 edges) finishes in under a minute on the
Railway service. Louvain detection finds 3,018 communities; the
top-degree nodes are dominated by *officers and registered agents*
who recur across many entities:

| node | incoming edges | role |
| --- | ---: | --- |
| `icij:240000001` | 1,615 | shared officer / registered agent |
| `icij:236724` | 1,067 | shared officer / registered agent |
| `icij:54662` | 1,065 | shared officer / registered agent (mirror, outgoing) |
| `icij:81027146` | 987 | shared officer / registered agent |

These nodes are the structural backbone of the offshore-services
network. They are not by themselves evidence of wrongdoing — they
are exactly what you would expect to see if a small number of
corporate-services firms each handle hundreds or thousands of
client SPVs. The shared-address report identified the same pattern
on the address side (Portcullis TrustNet Chambers, Tortola, hosts
33,858 entities; Mossack Fonseca offices follow in a long tail).

Among named *company* nodes in the top 30 by degree, the recurring
families are:

- Caribbean Mercantile Bank N.V. (Aruba): 5+ cluster members.
- Warburg Pincus (Bermuda) Private Equity series.
- Coller International Partners IV-D / V-A / V-B (Cayman).
- The Phoenix Spree Deutschland cluster from this case study sits
  in the broader sub-graph but does not crack the top 30 by raw
  degree — its members each have 20–46 edges, which is busy
  enough to be defensible without dominating the graph.

The Louvain communities cluster these fund families together with
their shared officers and agents. Community 503 contains the two
highest-degree shared officers (`icij:236724` and `icij:54662`);
their community spans hundreds of related entities. Community 613
contains the Warburg Pincus cluster plus the high-out-degree node
`icij:80011301` (an officer connected to many Bermuda entities).

The per-node centrality + community parquet at
`/data/processed/cluster_centrality.parquet` (on the Railway
volume) and the top-30 tables in
[`reports/centrality_top.md`](centrality_top.md) carry the
detail.

## 7. Limitations

- **Labels are AI-assisted, not human ground truth.** All eval
  numbers are preliminary. A small human review of the 300-pair
  sample would substantially harden the eval. The
  `v1_dropped` bucket (the most leveraged validation question)
  was labelled with explicit per-pair rationale and is the easiest
  to spot-check.
- **Sampling bias in the precision estimate.** The 300 pairs were
  deliberately stratified to over-sample marginal score bands. The
  band-weighted v2 overall precision estimate (94.4%) combines
  per-band precision from the labelled sample with the actual band
  sizes in the published run, which mitigates but does not
  eliminate this. Inspecting the `high` band specifically would
  require a fresh random sample from that band — my over-sampling
  of `jur_close`/`jur_loose` in that band biases the number low.
- **negative_evidence is disabled.** The two `negative_evidence`
  clauses on `lei` and `company_number` crash GoldenMatch 1.12.x's
  `match` subcommand with a polars schema-build error
  (`could not append value: 'HE322854' of type: str to the builder`).
  The feature works in `dedupe` but not `match`. They are left in
  the config as commented-out lines so the next config-version
  pass can re-enable them once upstream is fixed.
- **GLEIF VI gap.** Phoenix Spree Deutschland VI exists in the
  leak but seemingly has no LEI in GLEIF. The match assignment to
  VII is a *closest available reference* artifact of
  `--match-mode best`; it is not a claim that VI = VII.
- **Snapshot dates.** The findings are anchored to the ICIJ bundle
  dated 2025-03-31, the GLEIF Golden Copy dated 2026-05-11, and
  the OpenSanctions US OFAC SDN dataset fetched 2026-05-11. LEIs,
  statuses, and addresses change over time. Any claim derived
  from this snapshot should be re-verified against current data
  before publication.
- **Single jurisdiction skew.** The defensibility-ranked top
  clusters are heavily concentrated in BVI, Bermuda, Cayman,
  Jersey, and Malta — the jurisdictions that dominate the ICIJ
  leak. Findings do not generalise to the long tail of less-
  represented jurisdictions.

## 8. What's next

In rough order of leverage:

1. **Human spot-check** of ~30 rows from the existing 300-pair
   label set against company registries. Would harden the eval and
   surface any systematic labelling mistakes.
2. **Fix the `(N)` / roman-numeral suffix FP class.** Either
   pre-process names to strip trailing numeric tokens into a
   separate field, or write a custom scorer that requires
   numeric-suffix equality. Highest precision lever still on the
   table.
3. **Re-enable `negative_evidence`** once GoldenMatch fixes the
   `match`-subcommand crash, or work around with a post-filter
   that drops pairs where both sides have a non-null LEI that
   disagrees.
4. **OpenCorporates seed ingest** for a curated 20-name set in
   GB / DE / US jurisdictions. Cross-checks the GLEIF anchors
   against an independent registry source.
5. **Investigation writeup** on a second, structurally different
   cluster — e.g. a Cayman CLO family or one of the Caribbean
   Mercantile Bank Aruba entities — to confirm the pipeline
   generalises beyond the Phoenix Spree case.

---

### Reproducibility

All artifacts in this writeup are reproducible from the code in this
repository:

- Pipeline scripts under `scripts/`
- Match configuration at `configs/goldenmatch_company.yml`
- Cluster ranker at `scripts/rank_clusters.py`
- Provenance report at `scripts/provenance_report.py`
- Label set at `data/labels/marginal_v1.csv` + methodology doc
- Eval at `scripts/eval_v1_vs_v2.py`
- Centrality at `scripts/compute_centrality.py`
- Executable notebook at [`notebooks/01_case_study.ipynb`](../notebooks/01_case_study.ipynb)

A Railway control plane (`src/shellnet/job_server.py` + `Dockerfile`)
wraps each stage as an HTTP endpoint so a third party can re-run the
full pipeline against the published parquet on a 24 GB service.
