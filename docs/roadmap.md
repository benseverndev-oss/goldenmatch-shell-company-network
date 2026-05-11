# Roadmap

Phased plan for taking this from "scaffolding that runs on fixtures" to
"reproducible case study with real data and a writeup."

## Phase 0 — Scaffolding (this PR)

- [x] Project structure, `pyproject.toml`, `uv` workflow.
- [x] Canonical Pydantic schemas + normalization helpers + tests.
- [x] Adapters for ICIJ, OpenCorporates, GLEIF, OpenSanctions.
- [x] Unified company table builder.
- [x] Conservative `goldenmatch_company.yml`.
- [x] NetworkX graph builder + JSON summary.
- [x] Pytest suite over tiny synthetic fixtures.
- [x] README, data-sources doc, this roadmap.

## Phase 1 — Real ingestion (small slice)

- [ ] Pull a single ICIJ leak (e.g. Pandora Papers) into `data/raw/icij/`
      and run `scripts/ingest_icij.py` end-to-end. Use `scripts/fetch_icij.py
      --url … --sha256 …` if you want a reproducible one-liner.
- [ ] Cache OpenCorporates results for a hand-picked seed of ~20 high-profile
      shell-company names; commit the cache layout to docs (not the data).
- [ ] Pull a small GLEIF JSON sample (~10k records) and run the adapter.
- [ ] Pull one OpenSanctions dataset (e.g. `us_ofac_sdn`) and run the adapter.
- [x] `scripts/coverage_report.py` writes per-column fill-rate stats so we
      can see where ingestion is thin.

## Phase 2 — Matching

- [x] Run the GoldenMatch CLI against the unified table; capture cluster
      output under `reports/generated/` (`scripts/run_goldenmatch_full.py`).
- [x] Candidate-pair generator + seed-label deriver
      (`scripts/generate_candidate_pairs.py`, `scripts/derive_seed_labels.py`).
- [x] Evaluator that scores a run against the labels CSV with humans-only
      and derived-only splits (`scripts/eval_against_labels.py`).
- [ ] Hand-label 200–500 candidate pairs from the marginal band.
- [ ] Convert the name+address matchkey to `probabilistic` and rerun.
- [ ] Add `negative_evidence` for divergent identifiers/jurisdictions.

## Phase 3 — Address clusters

- [x] Build a deduplicated address parquet from all sources
      (`scripts/build_address_table.py`).
- [x] Wire `configs/goldenmatch_address.yml` to it.
- [x] Identify the top-N addresses by hosted-entity count and write a
      report (`scripts/report_shared_addresses.py` → Markdown + parquet).
- [ ] Hand-review the top-N entries; tighten the address normalizer based
      on what looks like false positives.

## Phase 4 — Officer / person resolution

- [x] Parse ICIJ officers and intermediaries CSVs.
- [x] Pull `Person` rows from OpenSanctions into a parallel persons table
      (`scripts/build_person_table.py`).
- [x] Add a third GoldenMatch config tuned for personal names
      (`configs/goldenmatch_person.yml`).
- [ ] Add a dedicated `normalize_person_name` (handles "Doe, John" /
      honorifics / married names) — the current normalizer is borrowed
      from companies and is conservative for people.

## Phase 5 — Graph analysis

- [x] Layer GoldenMatch `same_as` edges into the NetworkX graph
      (`shellnet.graph.build.add_same_as_edges`).
- [ ] Compute centrality + community detection; write per-cluster summaries.
- [ ] Pick 1–3 clusters as case-study writeups with full provenance.

## Phase 6 — Polish & publication

- [ ] Add a `notebooks/01_case_study.ipynb` with a worked example.
- [ ] Generate static HTML / PDF of the writeup under `reports/`.
- [ ] Final README pass with the actual case study, not just scaffolding
      instructions.
