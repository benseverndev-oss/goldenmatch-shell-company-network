# Project status — `goldenmatch-shell-company-network`

_Snapshot as of 2026-05-12. Two PRs merged onto `main` from `claude/goldenmatch-shell-company-scaffold-tVsBL`._

## TL;DR

Investigative-data-engineering scaffold + the full Phase 0–5 plumbing
for a public GoldenMatch case study on shell-company / offshore-entity
networks. The pipeline runs end-to-end on synthetic fixtures (60 pytest
tests, lint clean). It is **not yet a finished investigation** — real
public-data ingestion, human labelling, and the actual writeup are the
next moves.

## What runs today

```
ingest ─┬─► icij_entities/addresses/officers/intermediaries/edges.parquet
        ├─► opencorporates_companies.parquet
        ├─► gleif_entities.parquet
        └─► opensanctions_entities.parquet
                          │
                          ▼
              build_candidate_tables ───► company_entities.parquet
              build_address_table   ───► address_entities.parquet
              build_person_table    ───► person_entities.parquet
                          │
                          ▼
              run_goldenmatch_full ───► <name>_clusters.csv + lineage.json
                          │
              ┌───────────┼────────────┐
              ▼           ▼            ▼
   eval_against_labels  build_graph_smoke  report_shared_addresses
   (P/R/F1 vs CSV)      (NetworkX + same_as overlay)  (top-N MD/parquet)
```

Smoke fixtures cover the interesting cases: same company across sources,
suffix variation, shared registered-agent address, officer relationship,
near-name false-positive trap.

## Module map

| Path | Role |
| --- | --- |
| `src/shellnet/schemas.py` | Pydantic models: `CompanyEntity`, `PersonOrOfficer`, `AddressRecord`, `RelationshipEdge`, `IdentifierRecord` |
| `src/shellnet/normalize.py` | `normalize_company_name` (suffix strip, ASCII fold, dotted-initials collapse), `normalize_jurisdiction` (ISO 2-letter + 3-letter + alias map), `normalize_address_text`, `normalize_identifier` |
| `src/shellnet/paths.py` | Single source of truth for the `data/` layout, with `SHELLNET_DATA_DIR` override |
| `src/shellnet/sources/{icij,opencorporates,gleif,opensanctions}.py` | Per-source adapters, all emitting the same canonical row shape |
| `src/shellnet/matching/company_features.py` | Unified company-table builder |
| `src/shellnet/matching/address_features.py` | Unified address-table builder + `shared_address_report` |
| `src/shellnet/matching/person_features.py` | Unified person-table builder (officers + intermediaries + OS Persons) |
| `src/shellnet/matching/labels.py` | Canonical labels store, `derive_seed_labels`, `evaluate` with source filters |
| `src/shellnet/matching/runs.py` | Read GoldenMatch cluster CSV + lineage JSON, recover `entity_uid` via row-id join |
| `src/shellnet/matching/goldenmatch_runner.py` | Lightweight config-validation wrapper |
| `src/shellnet/graph/build.py` | NetworkX `MultiDiGraph` builder, `add_same_as_edges`, `summarize` |
| `src/shellnet/reporting/coverage.py` | Per-column fill-rate / distinct-count stats + Markdown renderer |
| `configs/goldenmatch_company.yml` | 3 matchkeys (LEI exact, registry-id exact, weighted name+juris+address @ 0.85) |
| `configs/goldenmatch_address.yml` | Multi-pass blocking + exact + weighted address matchkeys @ 0.90 |
| `configs/goldenmatch_person.yml` | Token-sort + soundex + Jaro-Winkler @ 0.82 |

## Scripts (Typer CLIs in `scripts/`)

| Script | Purpose |
| --- | --- |
| `fetch_icij.py` | Optional one-liner ICIJ bundle fetch with `--sha256` tripwire |
| `ingest_icij.py` | Discover + parse ICIJ CSVs into 5 interim parquets |
| `ingest_opencorporates.py` | API adapter, polite pagination, on-disk cache, `--dry-run` |
| `ingest_gleif.py` | JSON / JSONL parser with `--sample` cap |
| `ingest_opensanctions.py` | Local FtM export adapter, optional pinned-URL download |
| `normalize_entities.py` | Re-apply normalization after `shellnet/normalize.py` tweaks |
| `build_candidate_tables.py` | Fuse all source company rows |
| `build_address_table.py` | Fuse all source addresses |
| `build_person_table.py` | Fuse officers + intermediaries + OS Persons |
| `generate_candidate_pairs.py` | Marginal-band CSV for humans to label |
| `derive_seed_labels.py` | Auto-derived high-confidence seed labels |
| `run_goldenmatch_smoke.py` | Validate config against the real engine |
| `run_goldenmatch_full.py` | Shell out to `goldenmatch dedupe`, join cluster output to `entity_uid` |
| `eval_against_labels.py` | P/R/F1 split by human-only / derived-only labels |
| `build_graph_smoke.py` | NetworkX graph + JSON summary, with `same_as` overlay |
| `report_shared_addresses.py` | Top-N shared addresses → Markdown + parquet |
| `coverage_report.py` | Per-column fill-rate report across all parquets |

All available as `just`/`make` recipes.

## Phase progress

| Phase | Status |
| --- | --- |
| **0** — Scaffolding (repo layout, schemas, normalization, adapters, configs, smoke tests, docs) | done |
| **1** — Real ingestion (small slice) | infra ready; needs unrestricted network to actually pull ICIJ / GLEIF / OpenSanctions |
| **2** — Matching | engine + labelling + evaluator all wired; missing only human labels for the marginal band |
| **3** — Address clusters | table builder + GoldenMatch config + top-N report all green |
| **4** — Persons / officers / intermediaries | ICIJ side parsed; OpenSanctions Persons fused; person config landed |
| **5** — Graph analysis | `same_as` overlay landed; centrality + community detection + writeup still ahead |

## Numbers (fixture-only)

Running the full pipeline against the synthetic fixture set:

- 12 unified company rows (5 ICIJ + 3 OpenCorporates + 2 GLEIF + 2 OpenSanctions Companies)
- 17 unified address rows
- 6 unified person rows
- **8 clusters → 6 `same_as` pairs** from `goldenmatch dedupe`
- Evaluation against derived seed labels: **precision = recall = 1.0** (sanity check only — no human labels yet)
- Graph: 16 nodes, 17 edges (`registered_address`, `officer_of`, `intermediary_of`, `same_as`), 7 components, largest = 5

## Quality bars

- **60 pytest tests** passing, no network.
- `ruff check` clean over `src/`, `tests/`, `scripts/`.
- Sandbox-clean: nothing in `data/raw`, `data/interim`, `data/processed`, `reports/generated` is committed (gitignored). Only `.gitkeep` placeholders.
- No hardcoded secrets. `OPENCORPORATES_API_KEY` and `OPENSANCTIONS_DATASET_URL` are env-driven and optional.

## What's open

1. **Real-data ingest.** This sandbox firewalls outbound HTTP; one ICIJ leak in a normal environment should be a `scripts/fetch_icij.py --url … --sha256 …` away.
2. **Human labels.** 200–500 marginal-band pairs reviewed by hand. The infra is ready (`candidate_pairs.csv` → fill `label` column → `eval_against_labels.py`).
3. **Probabilistic matchkey + negative evidence.** Once human labels exist, promote `name_juris_address_weighted` to `probabilistic` with Fellegi-Sunter EM, add `negative_evidence` for divergent identifiers / jurisdictions.
4. **`normalize_person_name`.** The person table currently borrows `normalize_company_name` (suffix-stripping is mostly a no-op on people, but person names have their own quirks — `"Doe, John"` vs `"John Doe"`, honorifics, transliteration).
5. **Graph analysis & writeup.** Centrality / community detection on the `same_as`-overlaid graph, then pick 1–3 clusters for a writeup with full source provenance.
6. **GLEIF XML.** Today we parse JSON / JSONL; the Golden Copy XML and ZIP shapes are still `NotImplementedError`.

## Ethical posture

Unchanged from the README: this is investigative data engineering, not an
accusation engine. Matches are hypotheses, public-source data is incomplete
and noisy, manual review is required, source licences must be respected.
