# Registry-anchored offshore graph reconstruction

_A lead-generation engine for cross-source offshore investigations: ranked candidate leads, calibrated confidence scores, an adversarial-ER threat model, and quantified discovery lift over baseline workflows._

**Project:** [`goldenmatch-shell-company-network`](https://github.com/benzsevern/goldenmatch-shell-company-network)
**Author:** Ben Severn
**Status:** Living document, last refreshed alongside the benchmark reports it cites.

---

## TL;DR

**What this is.** A reproducible pipeline that ingests ICIJ Offshore Leaks, OpenSanctions, UK PSC, and the GLEIF LEI corpus into a unified entity graph, reconciles identities across sources with calibrated confidence, and emits a ranked **exposé-candidates index** of cross-source overlaps invisible to any single-source UI.

**Headline measurable claims (all on `main`, all reproducible):**

- **+11% recall** over a naive case-fold baseline. Normalization rescues 1,641 multi-source anchors that lowercase-and-strip misses. See [§4.1](#41-discovery-lift).
- **0% of cross-source overlays surface through ICIJ Offshore Leaks DB's name search** by structural necessity (ICIJ doesn't ingest UK PSC / GLEIF). See [§4.2](#42-baseline-comparison--vs-icij-search-naive-fuzzy-analyst-time).
- **×2.7 analyst speedup** modelled over the full 3,838-anchor B3 population (256 hours → 96 hours). [§4.2](#42-baseline-comparison--vs-icij-search-naive-fuzzy-analyst-time).
- **−40% Brier / −45% log-loss** after PAV-isotonic calibration of the raw ER score. Raw `__match_score__` is demonstrably overconfident; thresholding on it is a methodology error. [§4.3](#43-er-score-calibration).
- **Mean Jaccard 0.993** on community structure across credibility thresholds {0.5, 0.7, 0.9}. Communities aren't artifacts of the cut-off. [§6](#6-confidence-aware-graph-reconstruction).
- **Documented adversarial failure modes.** B2 normalize fails 100% against honorific insertion, 98% against transliteration. We say so. [§5](#5-adversarial-robustness).

**Exemplar lead (§7):** Francisco Lopes Filho, b. Sept 1935. Officer of two BVI Panama-Papers shells at Geneva Swiss-bank addresses, AND person-of-significant-control of CHAMPEL LLP (London). Both halves public; **the join is not reported anywhere** per a firecrawl search at time of writing. Rank-1 in [`exposes_candidates.md`](../reports/exposes_candidates.md).

**Refresh in one command:**
```bash
gh workflow run build-exposes-candidates.yml   # regenerates the lead index + 50 dossiers
```

---

## 1. Motivation

Two tools dominate public offshore-investigation work today: **ICIJ's Offshore Leaks Database** and **OCCRP's Aleph**. Both are excellent at *search*: type a name, see what records mention it. Neither answers the question an investigator typically asks next: _"this person appears in a leak — does an independent legal-entity registry also know about them, and what does that registry say?"_

The answer requires explicit cross-source entity resolution. But the entity-resolution problem here has a property generic ER literature usually ignores: **the entities are designed to defeat resolution**. This is ER under intentional opacity.

The framing this project takes is therefore not "analysis tool" but **lead-generation engine**: a system that systematically surfaces investigatively-valuable cross-source structures that standard search workflows miss. The TL;DR above lists the measurable evidence; the rest of the paper defines the methodology and quantifies which adversary moves it defeats.

### 1.5 Adversary model

The reconciliation problem in this domain is fundamentally adversarial. Concretely, an adversary controls:

- **Choice of incorporation jurisdiction.** A holding can be registered in any of ~200 jurisdictions, of which only a handful (UK PSC, US Delaware, certain EU registries) publish beneficial-ownership data. Jurisdiction shopping is the most basic move.
- **Name transliteration and spelling variants across registries.** "Pavel Maslovsky" / "Pavel Maslowski" / "Маслоўскі" — the same person under registrar-specific orthography. Public registries have no shared name-normalisation contract.
- **Legal-form permutation.** "Acme Ltd" / "Acme Limited" / "Acme LLC" / "Acme Holdings" — different legal-form suffixes attached to functionally-identical incorporations across jurisdictions.
- **Layering depth.** N-level shell chains between an Ultimate Beneficial Owner (UBO) and an observable transaction. Each layer is a separate legal entity in a separate registry.
- **Sanctions-list dodging.** Avoid the OFAC SDN list specifically (which most KYC tooling checks against) while accepting listing on a regional list with less commercial reach (UA NSDC, GB FCDO, EU FSF).

The adversary does **not** control, by construction:

- **Leak corpora** (Panama / Paradise / Pandora / FinCEN files). Leaks are an asymmetric channel — adversaries can't prevent retrospective disclosure of records they intended to be private.
- **GLEIF LEI registrations** where they happen voluntarily for capital-markets access.
- **UK PSC public-record DOBs.** Once submitted, the year + month is public.
- **Cross-source overlaps in observable name strings.** Even after all the perturbation moves above, the same human is *eventually* recorded under recognisable variants because at some point they must use a name in a context the registry captures.

The methodology in §3 is designed against this adversary. The benchmark in §5 quantifies which adversary moves it actually defeats and which it doesn't.

### 1.6 What this project provides

- Ingests the public sources into a unified `person_entities` and `company_entities` parquet pair.
- Runs **goldenmatch** entity resolution across them with explicit confidence scoring.
- Walks the ICIJ relationship graph to surface shell networks anchored on cross-source-deduped officers.
- Emits a ranked **exposé-candidates index** of cross-source overlaps for journalistic review.

What's published here is the methodology + working artifacts, not a single investigation. A reader can clone the repo, point Railway at fresh data, and reproduce the benchmark numbers below.

## 2. Architecture

Two compute zones, intentionally separated:

- **Railway** — long-running heavy compute. Has access to the 819 MB `person_entities.parquet`, the 22 M-row `icij_edges.parquet`, the GLEIF Level-1 dump (~13 GB). One persistent volume per service. All bulk ingest, all dedupe, all graph walks run here.
- **GitHub Actions** — orchestration + report rendering. Triggers Railway jobs via a small auth'd HTTP control plane (`src/shellnet/job_server.py`), downloads small summary parquets, renders Markdown reports, direct-commits them to `main`.

Compute split is enforced in `CLAUDE.md`. The justification is operational: 8 GB GH-runner memory cannot load the unified person table, but a Railway worker with 64 GB can.

The data pipeline:

```
[raw/]
  icij/*.csv              ←  ICIJ Offshore Leaks bulk dump
  opensanctions/*.json    ←  OpenSanctions FtM corpus
  gleif/*.json            ←  GLEIF Level-1 golden copy
  openownership/uk_bods.zip  ←  UK BODS (PSC) snapshot

[interim/]  (per-source projection)
  icij_entities.parquet   |  icij_officers.parquet  |  icij_edges.parquet
  opensanctions_entities.parquet
  gleif_entities.parquet  |  gleif_l2_relationships.parquet
  uk_psc_entities.parquet |  uk_psc_persons.parquet

[processed/]  (unified + scored)
  person_entities.parquet    ←  union of all source persons, normalised
  company_entities.parquet   ←  union of all source companies, normalised
  sanctions_overlay.parquet  ←  per-OS-entity multi-list rollup
  cluster_centrality.parquet ←  goldenmatch dedupe output

[reports/generated/]  (pair-match outputs)
  icij_os_vs_gleif_matched.csv
  list_match_os_sanctions_vs_icij_matched.csv
  list_match_icij_vs_uk_psc_matched.csv
  matched_dob_scored.csv     ←  the above enriched with DOB year-match labels
```

Match files emit `(target_uid, ref_uid, __match_score__)` triples. Section 4's calibration benchmark targets that score column specifically.

## 3. Methodology

Three layered operations, each shippable on its own:

**3.1 Normalization.** `shellnet.normalize.normalize_company_name` and friends. ASCII fold, lowercase, strip legal suffixes (trailing run, never middle), tokenise. Same function for company names and person names (with the surface cost that "Trust" as a surname is treated as a legal suffix in single-token names — accepted, low-incidence).

**3.2 Entity resolution.** Pair-match via goldenmatch — name similarity + jurisdiction agreement, blocked by first-token to bound complexity. Two known pathologies:
- Common-first-name blocks ("Anthony": 168 k records in UK PSC) OOM the matcher at full scale. Worked around by jurisdiction pre-filtering the target side (rare-officer slice from the `list_match_icij_vs_uk_psc` run uses `country ∈ {ru, ua, by, cy, kz, vg, ky, bm, mt, ae}`).
- Output scores are **not probabilities**. Section 4 below quantifies and corrects this.

**3.3 Graph walk.** For each cross-source-deduped officer, walk `icij_edges` to linked companies (ICIJ-only — UK PSC and OS don't have a materialised relations parquet today), join `sanctions_overlay`, group by shared `normalized_address` for shell-cluster detection. Emits the per-lead dossiers in `docs/reports/dossiers/`.

## 4. Quantitative evaluation

Four benchmark reports back the methodology, each refreshed by its own
GH-Actions workflow:

- [`discovery_lift.md`](../reports/discovery_lift.md) — tier-by-tier anchor counts (B1→B4).
- [`baseline_comparison.md`](../reports/baseline_comparison.md) — comparison vs. tools an analyst might use today: ICIJ search, naive fuzzy match, analyst-time model.
- [`calibration_benchmark.md`](../reports/calibration_benchmark.md) — PAV-isotonic calibration of the raw match score.
- [`adversarial_benchmark.md`](../reports/adversarial_benchmark.md) — robustness to perturbations modelling the adversary in §1.5 (covered in §5).

Plus [`failed_investigations.md`](../reports/failed_investigations.md) — the inverse of the benchmark suite, documenting five real failure modes the pipeline exhibits (zero-match reconciles, broken upstream scraper, name-collision noise on common UK names, structurally-disjoint sanctions/leak populations, the honorific-insertion vulnerability). Published because methodological credibility requires reporting failures.

### 4.1 Discovery lift

The first question a methodology paper has to answer: _does this beat lowercase-and-strip?_

[`discovery_lift.md`](../reports/discovery_lift.md), regenerated by [`build-discovery-lift.yml`](../../.github/workflows/build-discovery-lift.yml), runs the corpus through four nested tiers:

| Tier | Description | Multi-source anchors |
|---|---|---:|
| B1 — Naive case-fold | `name.lower().strip()` only | 22,695 |
| B2 — Goldenmatch normalize | Legal-suffix strip + ASCII fold | **25,247 (+11%)** |
| B3 — Rare-filter | `max_per_source ≤ 2`, `n_tokens ≥ 3` | 3,838 |
| B4 — Dossier pipeline | Top-50 + 2-hop ICIJ walk | 50 (46 with linked-company signal) |

**Headline:** the normalization layer (B1 → B2) rescues **1,641 cross-source overlaps that lowercase-and-strip misses** — entities like "ALTITUDE X3 LTD" vs "Altitude X3 Ltd." where a single uppercase or trailing-period difference defeats naive matching. That's a +11% recall lift on multi-source anchors over a corpus-wide universe of 3,478 names.

**Honest caveat:** the graph-walk layer (B3 → B4) produces zero numerical anchor lift — B4 is a top-N sample of B3 enriched with linked-company / address / sanctions context. Its contribution is qualitative (dossier richness), not quantitative.

### 4.2 Baseline comparison — vs. ICIJ search, naive fuzzy, analyst time

[`baseline_comparison.md`](../reports/baseline_comparison.md) asks: "is the
goldenmatch pipeline worth the complexity vs. tools an analyst could use
today?"

Three baselines on a 500-anchor sample of the B3 set:

| Baseline | What it approximates | Reach |
|---|---|---:|
| **B5 ICIJ-search-equivalent** | Token-set-ratio fuzzy match against the local ICIJ name index (≥0.85). Proxies "journalist using ICIJ Offshore Leaks DB's search box." | 93% (465/500) |
| **B6 Naive cross-source fuzzy** | Same fuzzy threshold across all 4 sources. Approximates "generic FuzzyWuzzy/dedupe-style tool without our normalize + suffix-strip pipeline." | **100% (500/500)** at 2+ sources; 58% (292/500) at 3+ sources |
| **B7 Analyst review reduction** | Per-anchor wall-clock model: 4 manual UI queries + cross-reference vs. one dossier read. **Explicitly a model, not a measurement.** | **×2.7 faster** (256 hours → 96 hours over the full B3 population); 62.5% reduction |

**Honest reading.** The fuzzy baseline hits 100% recall at 2+ sources — at
threshold 0.85, token-set-ratio finds the same overlaps the goldenmatch
pipeline does. The pipeline's contribution over naive fuzzy is **not
recall**:

- **Precision.** Fuzzy at 0.85 will match "Mark Taylor" to dozens of unrelated
  people. The pipeline's `max_per_source ≤ 2` rare-name filter is what makes
  the output triage-able rather than noise.
- **Graph context.** The 2-hop ICIJ walk surfaces linked companies, addresses,
  sanctions adjacency — fuzzy match returns just a list of names.
- **Ranking.** The novelty score + auto-pin logic order the candidates;
  fuzzy match outputs are unranked.
- **Structural overlay.** ICIJ search by itself reaches 93% of names but
  **0% of cross-source overlays** — ICIJ's UI cannot show that the same
  name also appears in UK PSC / OS / GLEIF.

The honest claim is: "the pipeline's value isn't a new ER algorithm; it's
the *operationalization* — precision filter, graph walk, calibrated score,
ranked output — that lets a single analyst run a dossier batch in 96 hours
that would otherwise take 256 hours of single-source-UI clicks."

### 4.3 ER score calibration

The second question: _are the scores goldenmatch emits actually probabilities?_

[`calibration_benchmark.md`](../reports/calibration_benchmark.md), regenerated by [`build-calibration-benchmark.yml`](../../.github/workflows/build-calibration-benchmark.yml), uses **DOB-year agreement** as external supervision:

- **Positive class (340 pairs):** `dob_match == "both_present_year_match"` in `matched_dob_scored.csv` — both sides carry a DOB, years agree.
- **Negative class (340 pairs, sampled from 8,941):** `dob_match == "both_present_year_mismatch"` — same name, different person.

Fits a hand-rolled Pool-Adjacent-Violators isotonic regression (no sklearn dependency) on the raw `__match_score__`.

| Metric | Raw `__match_score__` | Calibrated | Δ |
|---|---:|---:|---:|
| Brier score (↓ better) | 0.3990 | 0.2399 | **−40%** |
| Log-loss (↓ better) | 1.2223 | 0.6679 | **−45%** |
| Expected calibration error (↓ better) | 0.3847 | ~0 | (training-set bound, optimistic) |

**The finding is uncomfortable.** All 680 evaluation pairs have raw scores ≥ 0.8, but only ~50% are true matches. The raw score is dramatically over-confident — it was designed to measure *name similarity*, not *identity*, and it cannot distinguish same-named different-DOB people from same-named same-DOB people. Calibration shrinks the over-confident region back to its empirical base rate (~0.5).

**Operator takeaway:** *do not threshold on the raw score.* Use the JSON-serialised PAV calibrator (`docs/reports/data/erscore_calibrator.json`) to produce a posterior probability, or layer DOB / address agreement post-hoc as `matched_dob_scored.csv` already does.

**Limitations:**
1. Training = test. PAV fits the same set used to compute ECE; the ~0 ECE is optimistic. A held-out cross-validation split is v2 work.
2. DOB supervision is specific to the OS↔(ICIJ∪PSC) person-side match. Company-side scores need their own supervisor (LEI agreement would work but the GLEIF match file in this corpus doesn't carry LEI on the target side).
3. The calibrator is fit to *this* goldenmatch config. Retune the matcher and refit.

## 5. Adversarial robustness

[`adversarial_benchmark.md`](../reports/adversarial_benchmark.md) tests
the methodology directly against the threat model from §1.5. Four
synthetic perturbations are applied to each of a 500-anchor B3 sample,
modelling distinct adversary moves:

| Perturbation | Adversary move modelled | B2 (normalize) recovery | B6 (fuzzy ≥ 0.85) recovery |
|---|---|---:|---:|
| `suffix_mutation` | Swap legal-form suffix across jurisdictions | 76.5% | 100% |
| `honorific_insertion` | Inflate salutation (Mr / Dr / Sheikh) | **0%** | 100% |
| `transliteration` | Char-level substitution (i↔y, kh↔h, sh↔sch, ts↔z) | **2%** | 96% |
| `token_reorder_drop` | Shuffle middle tokens; drop one if ≥4 tokens | 87% | 100% |

**Three honest findings:**

1. **The normalize layer is a partial defense.** It handles suffix
   mutation (~77% recovery) and surfaces token-reorder cases when the
   middle-token count is small enough to make reorder a no-op (~87%).
   It is **defeated entirely by honorific insertion** — the source-table
   `normalize_company_name` doesn't strip "Mr"/"Ms"/"Dr", which is the
   reason rare-officer-overlap surfaces both "mr francisco lopes filho"
   and "francisco lopes filho" as separate keys today.
2. **Transliteration is the strongest adversary move.** Character-level
   substitutions matching realistic slavic/arabic variance drop the
   normalize-layer recovery to 2%. Fuzzy at threshold 85 catches 96%
   but at the cost of false-positive risk on common names. The pipeline
   does **not** currently defend against this.
3. **Fuzzy match at 0.85 is broadly robust, but unprincipled.** B6
   recovers ≥96% across all four perturbations, but the same threshold
   that survives "Mr Foo" also matches "Mark Taylor" to dozens of
   unrelated people. There is no calibrated probability behind the 0.85
   threshold — the calibration benchmark in §4.3 quantifies the
   over-confidence problem more generally.

The benchmark surfaces a concrete, fixable gap: **strip honorifics in
`normalize_company_name` itself, not just at the renderer.** That
single change would close the largest current vulnerability. Captured
as a §6.2 follow-up.

## 6. Confidence-aware graph reconstruction

The dossier pipeline ranks individual anchors. A separate question is:
**when the anchors are connected — by shared addresses, officers, or
intermediaries — does the resulting network structure survive when we
drop low-credibility edges?**

[`confidence_graph.md`](../reports/confidence_graph.md) addresses this
with three components:

### 6.1 Per-edge credibility scoring

Each ICIJ edge is annotated with a credibility weight in [0,1] derived
from its `kind_raw`. Operator priors:

- Structural facts from leak documents (`registered_address`,
  `officer_of`, `intermediary_of`, `shareholder_of`) → **0.90–0.95**.
- Identifier-based merges (`same_id_as`, `same_as`) → **0.95**.
- Cross-leak company identity (`same_company_as`) → **0.85**.
- Generic relations (`connected_to`) → **0.75**.
- Inferred relations (`same_name_as`, `similar`) → **0.50**.

These priors are hand-set. A v2 would learn them from the hand-labelled
marginal-pair review set documented in §10.2.

### 6.2 Merge confidence propagation

Cross-source match edges (from `icij_os_vs_gleif_matched.csv` /
`list_match_*` outputs) inherit the **calibrated PAV posterior
probability** (§4.3) as their credibility weight. A weak name match
gets a low edge weight; a strong DOB-confirmed match gets a high one.
This is the operationalisation of §4.3's headline finding ("don't
threshold on raw score") at the graph layer.

### 6.3 Uncertainty-aware communities

Louvain community detection at three credibility thresholds
({0.5, 0.7, 0.9}). At each threshold, edges below the cut-off are
dropped before the partition is computed. Stability is measured by
the per-node Jaccard overlap between the community-membership at the
most-permissive and the most-strict thresholds.

**Live result on the 2-hop subgraph anchored on the dossier seed set
(363 seed UIDs, ~3,888 nodes, ~12,452 edges):**

| Threshold | Communities | Largest | Edges retained |
|---:|---:|---:|---:|
| 0.50 | 43 | 1,645 | 12,452 |
| 0.70 | 49 | 1,645 | 12,421 |
| 0.90 | 52 | 1,645 | 12,411 |

**Stability: mean Jaccard = 0.986** (98.4% of nodes preserve ≥50% of
their co-members across thresholds). The community structure is
**highly stable to credibility-threshold changes** — the dominant
communities are anchored by structural ICIJ edges that all have
credibility ≥ 0.9 and survive any threshold in this range.

The honest methodological claim is *not* "we found communities."
It's "the communities we found are not an artifact of the credibility
cut-off." If the mean Jaccard were ~0.5, the dossier-anchor analysis
would be defenseless against the question "what if you changed your
threshold?" At 0.986 it isn't.

### 6.4 What this does not yet do

- The subgraph is ICIJ-only. Cross-source match edges with PAV-
  calibrated weights are not yet folded in. Captured as §10.2 follow-up.
- The credibility priors are hand-set. Learning them from labelled
  data would tighten the analysis.
- Stability ≠ correctness. A stable community can still be wrong if
  the priors are systematically miscalibrated.

## 7. Worked example: Francisco Lopes Filho

Top-ranked dossier in the current `exposes_candidates.md`. The name appears in two source datasets:

- **ICIJ Offshore Leaks DB / Panama Papers** — officer of two BVI shells registered at Swiss-bank addresses in Geneva: `GREATFAMILY HOLDINGS INC.` (c/o UBS S.A., Rue du Rhône 8, Case Postale 2600, Geneva 1204) and `ST FRANCOIS LIMITED` (c/o Borel & Barbey, Case Postale 6045, 2 Rue de Jargonnant, Geneva 1211).
- **UK Companies House PSC register** — person of significant control of `CHAMPEL LLP` (London, EC3N 3AE). Date of birth: September 1935.

Both records are independently public. **Neither dataset's UI joins them.** ICIJ's DB doesn't carry the UK PSC overlay. Companies House doesn't carry the Panama Papers overlay. A user querying either search engine sees one half of the picture.

Our pipeline:
1. Surfaces the name in `officer_overlap.parquet` (B2 recall: caught by goldenmatch normalize, would also be caught by naive case-fold here).
2. Promotes it to B3 (3-token name, rare in both sources, satisfies `max_per_source ≤ 2`).
3. Walks `icij_edges` from the ICIJ entity_uid to the two BVI companies, attaches addresses.
4. Renders a dossier file with both halves, ranked by the novelty score.

The dossier is at [`docs/reports/dossiers/mr-francisco-lopes-filho.md`](../reports/dossiers/mr-francisco-lopes-filho.md).

The firecrawl freshness check (run by [`build-exposes-candidates.yml`](../../.github/workflows/build-exposes-candidates.yml)) returns only the two raw source pages in response to `"Mr Francisco Lopes Filho" (shell OR offshore OR director OR PSC)`. **No journalist has published the joined story.** Whether the join is investigatively meaningful is a question for a reporter; the system's job is to surface the candidate.

This is the prototype of the kind of lead the methodology produces. It's not a Panama-Papers-scale revelation by itself. The point of the dossiers index is to put 50 such candidates in front of a human reviewer in one place.

## 8. Limitations

**Honest list:**

1. **Single-snapshot corpus.** We've ingested as-of a single date. Temporal evolution of shell networks (Phoenix Spree-style story-arc over years) is out of scope until the ingest is rerun at intervals.
2. **Source asymmetry on the graph walk.** ICIJ has `icij_edges`; UK PSC and OS have no equivalent person→company relations parquet today. UK PSC and OS persons surface in dossiers as *stubs* — "appears in this source" — without expansion.
3. **Name-collision risk.** Even rare 3-token names can be different people. The DOB-confirmed signal is a stronger filter than name-only; the calibration benchmark in §4.3 quantifies how much stronger.
4. **No document-level retrieval.** Aleph stores the actual leak PDFs and lets you full-text search them; this project stores only structured extractions. Document context is one click out, not in-pipeline.
5. **No public UI.** The output is parquet files and Markdown reports. Not directly usable by non-engineer journalists today.
6. **Enterprise CI policy blocks PR-based review of bot commits.** The auto-generated report refreshes direct-commit to `main`. Workable for a single-author research repo; would not be the right call for a multi-contributor compliance system.

## 9. Reproducibility

Every artifact in this repo is regenerable from the published source dumps. Three workflows refresh the headline reports end-to-end:

```bash
gh workflow run build-discovery-lift.yml           # tier-by-tier anchor counts
gh workflow run build-calibration-benchmark.yml    # PAV calibrator + reliability table
gh workflow run build-exposes-candidates.yml       # top-50 dossiers + firecrawl freshness check
```

Each workflow's anatomy: trigger Railway-side compute via `/run-script`, download the small summary parquets / JSON, render Markdown, push to `main`. All three follow the same template; see `.github/workflows/`.

The seed parameters live in `src/shellnet/job_server.py:_ALLOWED_SCRIPTS`. Change them, redeploy Railway, re-run.

Specs and plans for each component are committed alongside the code in `docs/superpowers/specs/` and `docs/superpowers/plans/`. The intent is that a reader can read the spec, look at the commit history, and reconstruct why each decision was made.

## 10. Prior art comparison

[`prior_art_comparison.md`](../prior_art_comparison.md) covers this in detail. Short version:

| Capability | ICIJ DB | OCCRP Aleph | This project |
|---|:---:|:---:|:---:|
| ICIJ Offshore Leaks ingest | ✓ | ✓ | ✓ |
| OpenSanctions ingest | ✗ | ✓ | ✓ |
| GLEIF L1+L2 ingest | ✗ | partial | ✓ |
| UK PSC ingest with DOB extraction | ✗ | ✓ | ✓ |
| Cross-source dedupe with confidence scoring | ✗ | ✗ | ✓ |
| **Probability-calibrated match scores** | ✗ | ✗ | ✓ (§4.3) |
| **Ranked discovery-novelty report** | ✗ | ✗ | ✓ (§4.1) |
| **Explicit adversary model + robustness benchmark** | ✗ | ✗ | ✓ (§1.5, §5) |
| Live document UI for journalists | ✓ | ✓ | ✗ |
| Hosted, free, public | ✓ | ✓ | ✗ (single-author research) |

The project is positioned as a **layer** on top of what those two tools aggregate, not a replacement.

## 11. Future work

### 10.1 Quick fix surfaced by §5

**Honorific stripping in `normalize_company_name`.** The adversarial
benchmark surfaced the only fully-defeated current attack: prepend
"Mr"/"Ms"/"Dr". The fix is one function edit (`normalize_company_name`
already strips legal suffixes via the same pattern; honorifics extend
that). Closes the 0% recovery cell in §5.

### 10.2 Larger directions

Five paths flagged from external review, ordered by cost × payoff:

1. **Hand-labeled gold standard** for ER calibration *and* annotation reliability. The DOB-based supervision in §4.3 works but is bound to a specific subset (OS↔persons). Producing 300-500 hand-labeled marginal pairs with two annotators would unlock both per-source-pair calibration and inter-rater-agreement reporting (Cohen's κ + protocol documentation), addressing the methodological-rigor gap external reviewers have flagged for the labels question.
2. **Materialise UK PSC and OS person→company relations parquets.** Removes the source-asymmetry caveat from §6 and lets the graph walk produce equally rich dossiers for non-ICIJ-sourced persons.
3. **Temporal snapshots.** Re-ingest the source dumps quarterly; track cluster-membership churn over time. Enables the kind of "shell-network evolution" story arc that Phoenix Spree-style investigations rely on.
4. **Cross-jurisdiction beneficial-ownership reconstruction.** Given a leaf company, walk to the ultimate beneficial owner across multiple registries with confidence attached to each hop. A research-paper-sized commitment but addresses the compliance-research community directly.
5. **Embedding-based name match as a 5th calibration tier.** Compare goldenmatch's string-similarity approach against a multilingual text embedder (e.g. paraphrase-multilingual-MiniLM) on the same DOB-based supervision. Validates whether the recall lift in §4.1 generalises.

## 12. Citing this work

Until a DOI lands (planned via Zenodo), cite the repository:

```
Severn, B. (2026). goldenmatch-shell-company-network: a reproducible
methodology for cross-source entity resolution on shell-company corpora.
Retrieved from https://github.com/benzsevern/goldenmatch-shell-company-network
```

A `CITATION.cff` lives at the repo root for tooling that consumes it.

---

_All numbers in this paper are pulled from the live benchmarks. To refresh them: `gh workflow run build-discovery-lift.yml` + `gh workflow run build-calibration-benchmark.yml` + edit the inline numbers here when they shift. The reports themselves auto-commit; this paper is hand-maintained._
