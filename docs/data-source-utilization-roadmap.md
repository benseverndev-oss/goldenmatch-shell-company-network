# Utilization roadmap for the new data sources

PRs #65, #66, and #67 landed three OpenCheck-style data sources:

- **OO UK PSC BODS bundle** (#65): bulk-ingest, 3.5 GB, 13.9M
  relationships. Outputs `oo_uk_psc_{entities,persons,relationships}.parquet`.
- **National-registry adapters** (#66): point-query Norway (full),
  France (full), Ireland + Netherlands (limited). Available via
  `scripts/lookup_registry.py`.
- **SEC EDGAR 13D/13G adapter** (#67): point-query, same CLI.

This doc is the plan for **getting value out of them**. The
ingestion priorities for *more* sources live in
[`ingestion_roadmap.md`](ingestion_roadmap.md); this is what to do
with the ones we already have.

Phases are ordered by leverage. Stop after Phase 1 if you only have
one PR's worth of time before recording.

---

## Phase 0 — Activate the OO bundle on Railway (one command)

PR #65 is dead weight until the bundle is actually ingested.

```bash
gh workflow run ingest-openownership-uk-psc.yml
```

That triggers the Railway job. 80-minute one-shot. Result: three new
parquets sitting in `/data/processed/oo_uk_psc_*.parquet` on the
Railway volume. No code changes needed.

After it lands, run `gh workflow run build-confidence-graph.yml` (or
the equivalent) to confirm the existing discovery pipeline still
passes with the volume present. Don't wire it in yet — that's Phase 1.

**Why first**: nothing else in this roadmap matters if the bundle
isn't on disk.

---

## Phase 1 — Wire UK PSC into the discovery graph

The current confidence graph is built from ICIJ + GLEIF +
`uk_psc_dob.parquet`. Replace the third with the OO bundle and
re-run discovery. Expect new clusters; expect existing clusters to
gain edges (in particular, the Perry / Strait Street network should
pick up UK PSC controllers behind the Malta entities the script
already surfaces).

Sub-tasks:

- Update `scripts/build_confidence_graph.py` to read
  `oo_uk_psc_relationships.parquet` as a new edge source with
  `source_label = "Open Ownership UK PSC"`, `kind_raw = "psc_controller_of"`.
- Update `cred_source` to give OO authority weight (it's CC0
  Companies House data, regulator-issued). Suggested weight: 0.97,
  between GLEIF (0.95) and OFAC primary (0.97).
- Re-run `scripts/build_validation_queue.py --top-n 20` and diff
  against the current top-20 (`docs/reports/validation_queue.md`).
- Eyeball: did Cluster 47 grow? Did new top-20 clusters appear that
  weren't reachable from the dossier-anchored 2-hop walk?

**Acceptance**: the validation queue diff makes sense, and at least
one new high-priority cluster surfaces that wasn't in the previous
top-20.

**Cost**: medium PR, all local Python changes. Re-running the
Railway pipeline is ~30 minutes.

---

## Phase 2 — Wire point-query adapters into the corroborate script

`scripts/corroborate_validation_pack.py` currently corroborates via
Tavily. The hit scorer has a known weakness for generic OFAC pages
(mitigated in PR #61 but not eliminated). Registry adapters are
**state-authoritative**: a Norwegian BRREG hit on a Norwegian
cluster member is definitive, not topical.

Sub-tasks:

- Add a `--with-registry-lookups` flag to the corroborate script.
- For each cluster member, look at jurisdiction:
  - `gb` → check Open Ownership UK PSC parquet (we already have it
    locally; no API call)
  - `no` → `BrregNorwayAdapter.search(name)` if no
    organisasjonsnummer, then `lookup()`
  - `fr` → `InpiFranceAdapter.search(name)`
  - `ie` / `nl` → log shallow lookup with documented limitation note
- For US-listed members (any cluster member that mentions a CIK or
  ticker in its identifiers) → `SecEdgar13DAdapter.search()`
- Write hits to a new artefact `cluster_<id>_registry_hits.csv` with
  columns: cluster_member, registry, identifier, name_match_score,
  officers_overlapping_with_cluster, sourceUrl.
- The evidence ledger gains a new `registry_corroborated` claim type
  with `publication_safe = true` whenever the registry hit confirms
  both the entity AND at least one officer named in the ICIJ data.

**Acceptance**: re-running corroborate on cluster 47 produces zero
new registry hits (cluster 47 is all-Malta; we don't have a Malta
adapter), but re-running on a hypothetical UK-anchored cluster
produces ≥1 BODS-confirmed officer per cluster member.

**Cost**: medium PR. ~200 LOC for the corroborate integration. No
new tests of the adapters themselves; reuse the mocks from PR #66.

---

## Phase 3 — Cross-jurisdictional name-lineage detector

The Perry verification (PRs #62, #63, #64) surfaced this by hand:
**PROBUTEC LTD** (UK, 2000) had a Maltese twin **PROBUTEC (MALTA)
LTD**; **I-CAP MARINE SERVICES LIMITED** (UK, 2008) had
**INTEGRATED-CAPABILITIES (MALTA) LTD** in Malta. Same Perry, same
root name, different jurisdiction. That's the offshore-onshore
holding-structure signature.

Until now we detected this manually. Phase 3 automates it.

Sub-tasks:

- New script `scripts/detect_cross_jurisdiction_twins.py`.
- For each Malta cluster member:
  - Strip the jurisdictional qualifier (`(MALTA)`, `MT`, `LIMITED`,
    `LTD`, `PLC`, …) and any common-noun core.
  - Search the OO UK PSC parquet for entities with the same
    normalized root.
  - Search each national-registry adapter for the same root.
  - Score matches by: edit distance, jurisdiction proximity (UK/IoM
    bridges → Malta is common; FR → Malta less so), officer-name
    overlap.
- Emit a new edge type: `cross_jurisdictional_twin` with
  `cred_source` 0.85 (heuristic).
- Re-run discovery; expect clusters to grow across borders.

**Acceptance**: the Perry case is rediscovered automatically —
PROBUTEC LTD and I-CAP MARINE SERVICES LIMITED should appear as
twin-edges into cluster 47.

**Cost**: substantive PR. ~400 LOC + tests. This is the highest-
leverage discovery-side upgrade.

---

## Phase 4 — Emit BODS as a sibling of FTM

Our exports are FTM ndjson today (PR #58). Open Ownership, ICIJ
Datashare, and AMLA workflows all consume BODS v0.4. We're one
mapping table away from interoperability.

Sub-tasks:

- New script `scripts/export_validation_pack_bods.py` (mirror of
  the FTM exporter).
- Map our FTM Person → BODS personStatement, Company →
  entityStatement, Directorship/Ownership → relationshipStatement
  with `interestType` codes.
- Each BODS statement carries `publicationDetails` with publisher =
  GoldenMatch and `bodsVersion = "0.4"`.
- Add the BODS file to the OpenAleph bundle (PR #59) alongside the
  FTM file. Aleph autodetects either.

**Acceptance**: a fresh cluster bundle contains both
`entities.ftm.json` and `statements.bods.jsonl`. `bods_validator`
(open source) accepts the BODS file without errors.

**Cost**: small PR. ~200 LOC + a test that re-emits the cluster 47
FTM as BODS and roundtrips.

---

## Phase 5 — AMLA "complex corporate structure" risk signals

The EU's Anti-Money Laundering Authority published draft Regulatory
Technical Standards for Customer Due Diligence that name specific
"complex corporate structure" red-flag indicators. OpenCheck
implements them as a `risk.py` module. Adding the equivalent to our
research brief gives every claim a citable regulatory framework.

Indicators to compute per cluster (most are already present, just
not labelled against AMLA categories):

| AMLA indicator | What it means | Where we already compute it |
| --- | --- | --- |
| ≥3 ownership layers | Multi-hop UBO chain | not yet — needs Phase 1 |
| Trust or arrangement in chain | Trust as legal owner | weak label only today |
| Non-EU jurisdiction in chain | Cross-EU/non-EU bridge | we have jurisdiction strings |
| Nominee shareholder | Officer holds shares for an undisclosed UBO | inferred from officer-equity pattern |
| Composite threshold | ≥2 of the above | trivial once individual signals exist |
| Advisory: subjective obfuscation | Free-form journalist judgement | leave as `needs_review` |

Sub-tasks:

- New `src/shellnet/risk_signals.py` module.
- One function per indicator; each returns a tagged
  `RiskSignal(indicator_code, score, evidence)`.
- Integrate into the corroborate research brief: a new "AMLA CDD
  RTS indicators" section that lists each fired signal + the cited
  evidence.

**Acceptance**: cluster 47's brief shows: ≥3 layers fired
(INTEGRATED-CAPABILITIES is shareholder of 36 cluster companies →
multi-layer), shared address fired, non-EU jurisdiction NOT fired
(Malta is EU). Cluster 37 shows: liquidation pattern not currently
in the AMLA list but worth flagging.

**Cost**: medium PR. ~300 LOC.

---

## Phase 6 — Bulk-ingest SEC 13D/13G filings

PR #67 is point-query only. To make 13D/G filings participate in
*discovery* (not just corroboration), ingest the daily filing index
into a parquet.

Sub-tasks:

- New `scripts/ingest_sec_13d_13g.py` that walks
  `https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=SC+13`
  daily (or backfills from a date range).
- For each filing, fetch the primary doc, parse out filer + subject
  + percent + CUSIP. (XML parsing is the work here; the SEC's
  XBRL/EDGAR filing structure is well-documented.)
- Output `sec_13d_13g_edges.parquet` with shape mirroring our
  existing `icij_edges.parquet`: src_node (filer), dst_node
  (subject), kind_raw = "schedule_13d_filer_of", percent,
  filing_date.
- Add to the confidence graph as a new edge source.

**Acceptance**: any cluster member that's a CIK shows incoming
"schedule_13d_filer_of" edges from the >5% beneficial owners. The
discovery pipeline can then walk those filers across clusters.

**Cost**: larger PR. ~500 LOC including XML parsing. Backfill is
~80k filings since 2001, fits comfortably in a Railway parquet.

---

## Phase 7 — Re-cluster with the expanded graph

After Phases 1, 3, and 6 add new edge types, the confidence graph
is meaningfully larger and denser. Re-run Louvain + the
anomaly/isolation/underreportedness scoring; expect the validation
queue's composition to shift.

Sub-tasks:

- `gh workflow run build-confidence-graph.yml`
- `gh workflow run build-validation-queue.yml`
- `gh workflow run build-validation-pack.yml` for any newly-surfaced
  top-10 cluster.
- Compare new vs old top-10. Document which clusters appeared
  because of OO UK PSC, which because of cross-jurisdictional
  twins, which because of SEC 13D/G.

**Acceptance**: at least one new top-10 cluster is anchored on a UK
or US entity that wasn't reachable from the ICIJ-only graph.

**Cost**: zero code; just compute. Document the result in
`docs/reports/discovery_advantage.md` (existing file).

---

## What's out of scope (and why)

- **Additional national-registry adapters** (Czechia, Poland,
  Austria, Slovakia, Lithuania, Latvia, Estonia, Switzerland,
  Sweden, Finland). OpenCheck has all of these; we don't, and we
  shouldn't add them until a cluster surfaces a hit. Premature.
- **Wikidata bridging.** Useful for LEI ↔ company ↔ person lookups
  at scale, but the manual cross-reference work we did for Perry
  takes ~10 minutes per target; not worth the ingestion overhead
  unless we're automating across hundreds of anchors.
- **OpenTender (DIGIWHIST) procurement data.** Narrative-stage
  tool, not discovery-stage. Plug in when a specific cluster
  surfaces procurement exposure.
- **EveryPolitician.** OpenSanctions already carries PEP data.

---

## Recommended order if you only have time for two PRs

1. **Phase 1** — wire UK PSC into the discovery graph. The OO
   bundle is the biggest single enrichment available and it doesn't
   participate until this lands.
2. **Phase 3** — cross-jurisdictional twin detector. Discovers the
   Perry-style holding structures automatically. Highest leverage
   per LOC.

Phase 2 (corroborate integration) is also good value but smaller
scope; Phase 5 (AMLA signals) is publication-defensibility insurance
worth doing before any video ships.
