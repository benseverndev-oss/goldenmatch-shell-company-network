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
      and run `scripts/ingest_icij.py` end-to-end.
- [ ] Cache OpenCorporates results for a hand-picked seed of ~20 high-profile
      shell-company names; commit the cache layout to docs (not the data).
- [ ] Pull a small GLEIF JSON sample (~10k records) and run the adapter.
- [ ] Pull one OpenSanctions dataset (e.g. `us_ofac_sdn`) and run the adapter.
- [ ] Run `scripts/build_candidate_tables.py`; check column coverage.

## Phase 2 — Matching

- [ ] Run the GoldenMatch CLI against the unified table; capture cluster
      output under `reports/generated/`.
- [ ] Hand-label 200–500 candidate pairs from the marginal band.
- [ ] Convert the name+address matchkey to `probabilistic` and rerun.
- [ ] Add `negative_evidence` for divergent identifiers/jurisdictions.
- [ ] Compute precision/recall against the labelled set; iterate on
      blocking and weights.

## Phase 3 — Address clusters

- [ ] Build a deduplicated address parquet from all sources.
- [ ] Wire `configs/goldenmatch_address.yml` to it.
- [ ] Identify the top-N addresses by hosted-entity count and write a small
      report.

## Phase 4 — Officer / person resolution

- [ ] Parse ICIJ officers and intermediaries CSVs.
- [ ] Pull `Person` rows from OpenSanctions into a parallel persons table.
- [ ] Add a third GoldenMatch config tuned for personal names
      (lower thresholds, more transformations).

## Phase 5 — Graph analysis

- [ ] Layer GoldenMatch `same_as` edges into the NetworkX graph.
- [ ] Compute centrality + community detection; write per-cluster summaries.
- [ ] Pick 1–3 clusters as case-study writeups with full provenance.

## Phase 6 — Polish & publication

- [ ] Add a `notebooks/01_case_study.ipynb` with a worked example.
- [ ] Generate static HTML / PDF of the writeup under `reports/`.
- [ ] Final README pass with the actual case study, not just scaffolding
      instructions.
