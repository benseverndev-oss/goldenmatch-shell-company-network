# Project status — `goldenmatch-shell-company-network`

_Snapshot as of 2026-05-12. Phases 0–6 landed on `main`._

## TL;DR

Investigative-data-engineering scaffold + full Phase 0–6 pipeline for a
public GoldenMatch case study on shell-company / offshore-entity networks.
End-to-end run on real ICIJ + GLEIF + OpenSanctions data (not just
fixtures), 300 hand-labelled marginal pairs grounding the eval, v1 → v2
config sweep with a band-weighted precision lift, centrality + Louvain
communities on the cluster sub-graph, and a Phoenix Spree case-study
writeup with full source provenance. The remaining holes are
OpenCorporates ingest (no API key) and the probabilistic-matchkey
upgrade now that real labels exist.

## What runs today

```
ingest ─┬─► icij_entities/addresses/officers/intermediaries/edges.parquet
        ├─► opencorporates_companies.parquet      (blocked: no API key)
        ├─► gleif_entities.parquet                 (3.3M LEI records, streaming)
        └─► opensanctions_entities.parquet         (OFAC SDN, 70k entities)
                          │
                          ▼
              build_candidate_tables ───► company_entities.parquet
              build_address_table   ───► address_entities.parquet
              build_person_table    ───► person_entities.parquet
                          │
                          ▼
              run_goldenmatch_full ───► <name>_clusters.csv + lineage.json
                          │
              ┌───────────┼────────────────┬──────────────────────┐
              ▼           ▼                ▼                      ▼
   eval_against_labels  build_graph_smoke  centrality_communities  case-study writeup
   (per-bucket P/R/F1   (NetworkX +        (Louvain on cluster     (Phoenix Spree,
   on 300 hand-labels)  same_as overlay)   sub-graph, top-N)       9-member cluster)
```

## Module map

| Path | Role |
| --- | --- |
| `src/shellnet/schemas.py` | Pydantic models: `CompanyEntity`, `PersonOrOfficer`, `AddressRecord`, `RelationshipEdge`, `IdentifierRecord` |
| `src/shellnet/normalize.py` | `normalize_company_name` (suffix strip, ASCII fold, dotted-initials collapse), `normalize_jurisdiction` (ISO 2-letter + 3-letter + alias map), `normalize_address_text`, `normalize_identifier` |
| `src/shellnet/paths.py` | Single source of truth for the `data/` layout, with `SHELLNET_DATA_DIR` override |
| `src/shellnet/sources/{icij,opencorporates,gleif,gleif_golden_copy,opensanctions}.py` | Per-source adapters, all emitting the same canonical row shape. `gleif_golden_copy` streams the 13 GB JSON via `ijson` |
| `src/shellnet/matching/company_features.py` | Unified company-table builder |
| `src/shellnet/matching/address_features.py` | Unified address-table builder + `shared_address_report` |
| `src/shellnet/matching/person_features.py` | Unified person-table builder (officers + intermediaries + OS Persons) |
| `src/shellnet/matching/labels.py` | Canonical labels store, `derive_seed_labels`, `evaluate` with source filters |
| `src/shellnet/matching/runs.py` | Read GoldenMatch cluster CSV + lineage JSON, recover `entity_uid` via row-id join |
| `src/shellnet/matching/goldenmatch_runner.py` | Lightweight config-validation wrapper |
| `src/shellnet/graph/build.py` | NetworkX `MultiDiGraph` builder, `add_same_as_edges`, `summarize` |
| `src/shellnet/reporting/coverage.py` | Per-column fill-rate / distinct-count stats + Markdown renderer |
| `src/shellnet/job_server.py` | FastAPI control plane for remote pipeline runs (Railway) |
| `configs/goldenmatch_company.yml` | v2 config: token_sort + threshold raised to 0.92 after eval |
| `configs/goldenmatch_address.yml` | Multi-pass blocking + exact + weighted address matchkeys @ 0.90 |
| `configs/goldenmatch_person.yml` | Token-sort + soundex + Jaro-Winkler @ 0.82 |

## Scripts (Typer CLIs in `scripts/`)

| Script | Purpose |
| --- | --- |
| `fetch_icij.py` | One-liner ICIJ bundle fetch with `--sha256` tripwire |
| `ingest_icij.py` | Discover + parse ICIJ CSVs into 5 interim parquets |
| `ingest_opencorporates.py` | API adapter, polite pagination, on-disk cache, `--dry-run` |
| `ingest_gleif.py` / `ingest_gleif_golden_copy.py` | JSON / JSONL parser; streaming variant for the full Golden Copy |
| `ingest_opensanctions.py` | Local FtM export adapter, optional pinned-URL download |
| `normalize_entities.py` | Re-apply normalization after `shellnet/normalize.py` tweaks |
| `build_candidate_tables.py` | Fuse all source company rows |
| `build_address_table.py` | Fuse all source addresses |
| `build_person_table.py` | Fuse officers + intermediaries + OS Persons |
| `generate_candidate_pairs.py` | Stratified marginal-band CSV for humans to label |
| `derive_seed_labels.py` | Auto-derived high-confidence seed labels |
| `run_goldenmatch_smoke.py` | Validate config against the real engine |
| `run_goldenmatch_full.py` | Shell out to `goldenmatch dedupe`, join cluster output to `entity_uid` |
| `eval_against_labels.py` | P/R/F1 per bucket + band-weighted overall precision estimate |
| `build_graph_smoke.py` | NetworkX graph + JSON summary, with `same_as` overlay |
| `centrality_communities.py` | Louvain + degree centrality on cluster sub-graph |
| `case_study_phoenix_spree.py` | Cluster provenance writeup with side-by-side member table |
| `report_shared_addresses.py` | Top-N shared addresses → Markdown + parquet |
| `coverage_report.py` | Per-column fill-rate report across all parquets |
| `investigate_entity.py` | Seed-query workflow: rank candidates for one `(name, jurisdiction)` pair, attach 1-hop ICIJ neighbourhood, optionally enrich from Postgres |
| `investigate_entities.py` | Batch version: read a `name,jurisdiction,source_note` CSV, write one report per seed + a top-level index. Loads parquets once, opens at most one Postgres connection |
| `investigate_person.py` | Person-side seed-query: name+country → matched person rows → all companies attached via officer / intermediary / shareholder edges |
| `investigate_address.py` | Address-side seed-query: free-text+country → matched address rows → all entities registered there |
| `expand_2hop.py` | One-shot 2-hop walk from a company `entity_uid` — surfaces every other company sharing an officer / intermediary with the seed. `--named-individuals-only` drops Appleby/PwC-style provider noise |

All available as `just`/`make` recipes.

## Phase progress

| Phase | Status |
| --- | --- |
| **0** — Scaffolding (repo layout, schemas, normalization, adapters, configs, smoke tests, docs) | done |
| **1** — Real ingestion (small slice) | ICIJ + GLEIF + OpenSanctions pulled at full scale; OpenCorporates blocked on API key |
| **1.5** — Infrastructure (FastAPI job server, Railway deploy) | done |
| **2** — Matching (labels + eval) | 300 hand-labelled pairs across 4 buckets; v1 → v2 config sweep landed; threshold raised 0.85 → 0.92 |
| **3** — Address clusters | table builder + GoldenMatch config + top-N report all green |
| **4** — Persons / officers / intermediaries | done — ICIJ officers + intermediaries + OS Persons fused, person config landed |
| **5** — Graph analysis | `same_as` overlay landed; Louvain communities + degree centrality on 50,998-node cluster sub-graph |
| **6** — Case-study writeup | Phoenix Spree (cluster 503264, 9 members, Jersey, 100% GLEIF anchored) shipped with executable notebook |

## Numbers (real data)

ICIJ bundle (`full-oldb.LATEST.zip`):
- 814,344 entities, 402,246 addresses, 771,315 officers, 25,629 intermediaries, 3,339,267 edges

GLEIF Golden Copy:
- 3,304,422 LEI records (streamed via `ijson` + 100k-row parquet chunking)

OpenSanctions OFAC SDN:
- 70,301 entities

GoldenMatch v1 → v2 list-match (`icij_os_vs_gleif`):
- v1 (threshold 0.85): 20,297 matched pairs
- v2 (threshold 0.92, token_sort): 5,630 matched pairs (~73% reduction)
- Cluster sub-graph: 50,998 nodes / 75,011 edges, 3,018 Louvain communities

Labels:
- 300 pairs across 4 stratified buckets in `data/labels/marginal_v1.csv`
  - `v1_dropped` (n=100): 6 match / 81 no_match / 13 unsure — confirms v2's threshold raise dropped mostly noise
  - `v2_marginal` (n=100): 41 match / 43 no_match / 16 unsure
  - `perfect_sanity` (n=50): 50 match / 0 no_match — score ≥ 0.99 is reliable
  - `v2_borderline_class` (n=50): 11 match / 24 no_match / 15 unsure
- Headline (band-weighted, strict): **est. v1 precision 43.7%, v2 precision 94.4% (+50.7pp)**
- Headline (generous, unsure → match): v1 54.1% → v2 95.6% (+41.5pp)
- Recall cost of the threshold raise, on the dropped band: 6% strict / 19% generous

## Quality bars

- Pytest suite passing, no network.
- `ruff check` clean over `src/`, `tests/`, `scripts/`.
- Sandbox-clean: nothing in `data/raw`, `data/interim`, `data/processed`, `reports/generated` is committed (gitignored). Only `.gitkeep` placeholders.
- No hardcoded secrets. `OPENCORPORATES_API_KEY` and `OPENSANCTIONS_DATASET_URL` are env-driven and optional.

## What's open

1. **OpenCorporates ingest.** Adapter is ready, blocked on API key + curated seed list of ~20 high-profile shell-company names.
2. **Probabilistic matchkey + negative evidence.** Real labels now exist (300 pairs). Promote `name_juris_address_weighted` from weighted to `probabilistic` with Fellegi-Sunter EM, add `negative_evidence` for divergent identifiers / jurisdictions. The 50/43/16 split in the `v2_marginal` bucket is the most informative training signal.
3. **Centrality report enrichment.** Top-N table currently has empty `name` / `jur` / `cluster` columns for hubs in the ICIJ-only sub-graph — needs a join back to `company_entities` / `person_entities` on `entity_uid` before publication.
4. **`normalize_person_name`.** Person table currently borrows `normalize_company_name`. Needs honorifics, `"Doe, John"` ↔ `"John Doe"`, and transliteration handling.
5. **More case-study writeups.** Phoenix Spree is the first. Centrality + community output should surface 1–2 more clusters worth writing up (largest community by member count, highest-centrality intermediary, etc.).
6. **GLEIF XML.** Today we parse JSON / JSONL + the Golden Copy JSON. The Golden Copy XML and ZIP shapes are still `NotImplementedError` — decide whether to implement or drop.

## Ethical posture

Unchanged from the README: this is investigative data engineering, not an
accusation engine. Matches are hypotheses, public-source data is incomplete
and noisy, manual review is required, source licences must be respected.
The Phoenix Spree writeup carries an explicit disclaimer that ICIJ
membership does not imply wrongdoing.
