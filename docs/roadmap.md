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

- [x] Pull a single ICIJ leak. Actually pulled the full `full-oldb.LATEST.zip`
      bundle: 814,344 entities, 402,246 addresses, 771,315 officers, 25,629
      intermediaries, 3,339,267 edges. End-to-end through `scripts/ingest_icij.py`.
- [ ] Cache OpenCorporates results for a hand-picked seed of ~20 high-profile
      shell-company names. **Blocked**: no API key + curated seed list yet.
- [x] Pull GLEIF. Pulled the **full** Golden Copy file (13 GB JSON, 3,304,422
      LEI records) — far larger than the original "small sample" target.
      Required a new streaming adapter (`shellnet.sources.gleif_golden_copy`)
      since the v1-API adapter would OOM on a multi-GB JSON. Adapter uses
      `ijson` + 100k-row parquet chunking.
- [x] Pull one OpenSanctions dataset. US OFAC SDN, 70,301 entities ingested.
- [x] `scripts/coverage_report.py` writes per-column fill-rate stats so we
      can see where ingestion is thin.

## Phase 1.5 — Infrastructure (added mid-Phase 1)

The full ICIJ + GLEIF dataset is too big to dedupe on a laptop, so this
phase materialized to push compute into a managed environment. Land below
is reusable for later phases.

- [x] FastAPI control plane (`src/shellnet/job_server.py`) wrapping each
      pipeline stage as an endpoint: upload, fetch-url, unzip, ingest,
      build, match, match-against, publish, run-script, status, logs.
- [x] Dockerfile + `railway.json` + `.dockerignore` for one-command deploy.
- [x] Railway service `shellnet-job` + 50 GB persistent volume mounted at
      `/data` + bearer-token auth (`SHELLNET_JOB_TOKEN` env var).
- [x] Postgres writer (`src/shellnet/publish.py`) that writes a `shellnet`
      schema next to the showcase tables in the existing project Postgres.
      Tables: `runs`, `clusters`, `same_as_pairs`, `list_matches`.
- [x] `scripts/upload_icij.py` — laptop-side streamed zip uploader.
- [x] `scripts/filter_company_table.py` — drops placeholder names,
      mega-blocks (>4000 rows per `substring:0:8 || jurisdiction`), and
      supports `--drop-sources` / `--keep-only-sources` for slicing.

## Phase 2 — Matching

- [x] Run the GoldenMatch CLI against the unified table; capture cluster
      output under `reports/generated/` (`scripts/run_goldenmatch_full.py`).
- [x] Candidate-pair generator + seed-label deriver
      (`scripts/generate_candidate_pairs.py`, `scripts/derive_seed_labels.py`).
- [x] Evaluator that scores a run against the labels CSV with humans-only
      and derived-only splits (`scripts/eval_against_labels.py`).
- [ ] Hand-label 200–500 candidate pairs from the marginal band.
- [x] Tighten the name+address matchkey. Swapped `jaro_winkler` →
      `token_sort` and raised threshold 0.85 → 0.92 after the first run
      surfaced ~10K leading-token false positives (CRYSTAL FINANCE /
      CRYSTAL BAY / CRYSTAL INVESTMENTS-style collisions). Result: the
      borderline-low_overlap class collapsed from 10,666 → 5 on the
      ICIJ→GLEIF list-match while keeping the perfect-band count intact.
      Stopping short of full `probabilistic` until we have hand-labels.
- [~] Add `negative_evidence` for divergent identifiers (lei,
      company_number). Configured in `goldenmatch_company.yml` but
      commented out: goldenmatch 1.12.x crashes the `match` subcommand
      with a polars schema-build error when negative_evidence is enabled
      (`could not append value: 'HE322854' of type: str to the builder`).
      The feature works in `dedupe`. Re-enable once upstream fixes it.
- [x] List-match (`goldenmatch match`) is the right tool at this scale
      for cross-source resolution. Full ICIJ+GLEIF dedupe OOMs at 4.1M
      rows even on 24 GB / 24 vCPU; `match TARGET --against REFERENCE`
      streams target rows against reference blocks and stays under 7 GB.
      Pipeline: ICIJ+OpenSanctions dedupe → match deduped result against
      GLEIF reference → publish to `shellnet.list_matches`.

## Phase 3 — Address clusters

- [x] Build a deduplicated address parquet from all sources
      (`scripts/build_address_table.py`).
- [x] Wire `configs/goldenmatch_address.yml` to it.
- [x] Identify the top-N addresses by hosted-entity count and write a
      report (`scripts/report_shared_addresses.py` → Markdown + parquet).
      Ran on the full ICIJ ingest: top result is Portcullis TrustNet
      Chambers (Tortola) hosting **33,858 entities**, followed by a long
      tail of Mossack Fonseca offices and other registered-agent shops.
- [ ] Hand-review the top-N entries; tighten the address normalizer based
      on what looks like false positives.
- [ ] Address-table GoldenMatch dedupe is currently blocked: matching
      on the 701K-row address table OOMs because placeholder/legal-form
      prefixes (`stichtin||nl`, `the trus||au`) form 9K+-row mega-blocks.
      Apply the same mega-block filter we use for companies before
      retrying, or pre-strip legal-form prefixes during normalization.

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
      (`shellnet.graph.build.add_same_as_edges`). Ran on the full
      ingest: 2.03M nodes, 4,272 `same_as` edges layered on top of the
      ICIJ source relationships. Summary in `graph_smoke_summary.json`.
- [ ] Compute centrality + community detection; write per-cluster summaries.
- [ ] Pick 1–3 clusters as case-study writeups with full provenance.

## Phase 6 — Polish & publication

- [ ] Add a `notebooks/01_case_study.ipynb` with a worked example.
- [ ] Generate static HTML / PDF of the writeup under `reports/`.
- [ ] Final README pass with the actual case study, not just scaffolding
      instructions.
- [x] Heuristic precision review of a list-match run
      (`scripts/review_matches.py` → `*_review.md`). Classifies each pair
      as identical / normalized_eq / jur_close / jur_loose / low_overlap /
      jur_mismatch and crosstabs against score band. Used to validate the
      v2 config landed a real precision lift (high-trust share 33% → 99.5%).
