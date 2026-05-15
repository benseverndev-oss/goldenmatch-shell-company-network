# goldenmatch-shell-company-network

A reproducible **case study** in using
[GoldenMatch](https://pypi.org/project/goldenmatch/) to reconcile shell-company
and offshore-entity records across public datasets, then reconstruct fragmented
corporate-identity graphs from them.

The repo is **scaffolding, ingestion, and two worked investigations**.
Drop public bulk files into `data/raw/`, run a handful of scripts, and
you'll get unified tables across sources, a GoldenMatch dedupe +
list-match run, a NetworkX graph summary, and per-seed markdown
investigation reports. Two case studies live alongside the code.

## Corpus & case studies

Current corpus (after ICIJ + OpenSanctions ingest):

| Table | Rows |
| --- | ---: |
| `company_entities.parquet` | **1,240,555** (ICIJ 814k + OS 426k) |
| `person_entities.parquet` | **1,864,666** (ICIJ 711k + OS 1.15M) |
| `address_entities.parquet` | **1,180,555** (ICIJ 702k + OS 479k) |
| `uk_psc_dob.parquet` | **12,151,833** (UK Companies House PSC, DOB-only) |

Two investigations have been run end-to-end:

- **Phoenix Spree Deutschland** — 9-member ICIJ cluster, 100% GLEIF
  anchored. Walkthrough:
  [`notebooks/01_case_study.ipynb`](notebooks/01_case_study.ipynb)
  · writeup:
  [`reports/case_studies/503264_phoenix_spree_deutschland.md`](reports/case_studies/503264_phoenix_spree_deutschland.md).
- **Epstein corporate-network seed review** — 28 sourced seeds (USVI
  SAC, NYDFS, Senate Finance, JPMorgan litigation). Headline: *Liquid
  Funding, Ltd.* (Bermuda, ICIJ Paradise Papers — Appleby) is the
  single corroborated lead — Jeffrey E Epstein listed as director +
  chairman, 2001-11-09 to 2007-03-30, alongside Bear Stearns SVP
  Jeffrey M Lipman (FINRA CRD# 717915, Bear Stearns 1980–2008).
  Notebook:
  [`notebooks/02_epstein_case_study.ipynb`](notebooks/02_epstein_case_study.ipynb)
  · findings:
  [`reports/investigations/epstein_followup_2_findings.md`](reports/investigations/epstein_followup_2_findings.md).

## What this is — and isn't

**Is:** investigative data engineering. We try to *connect* records that
plausibly refer to the same legal entity across noisy public sources, and to
surface graph structure (shared addresses, shared officers, parent/child
chains) that a human investigator can then review.

**Isn't:** an accusation engine. Presence in the ICIJ Offshore Leaks does not
imply wrongdoing — many entities in that dataset are legitimate. Matches
produced by GoldenMatch are *hypotheses*, not facts. Always review by hand.
Always respect each source's licence and terms of service.

## Data sources

| Source | Role | Access | Notes |
| --- | --- | --- | --- |
| [ICIJ Offshore Leaks](https://offshoreleaks.icij.org/pages/database) | Primary entities + relationships | Manual CSV download | One bundle per leak; filename patterns vary across releases |
| [OpenCorporates](https://api.opencorporates.com/) | Registry-anchored company records | API (key optional) | Polite pagination + on-disk response cache |
| [GLEIF Golden Copy](https://www.gleif.org/en/lei-data/gleif-golden-copy) | Authoritative LEI records | Manual download | We parse JSON / JSONL today; XML is a TODO |
| [OpenSanctions](https://www.opensanctions.org/datasets/) | Enrichment (sanctions, PEPs, registers) | Manual export | Not used as ground truth |

Full per-source fields, licensing, and caveats live in
[`docs/data-sources.md`](docs/data-sources.md).

## Quickstart

```bash
# 0. Tooling: needs Python >=3.11 and uv (https://docs.astral.sh/uv/)
uv sync --extra dev

# 1. Run the test suite to confirm the scaffold is healthy
uv run pytest

# 2. Drop raw inputs in place (see docs/data-sources.md for each source)
#    e.g. unzip the ICIJ bundle into data/raw/icij/

# 3. Ingest whichever sources you have
uv run python scripts/ingest_icij.py
uv run python scripts/ingest_opencorporates.py --query "Acme Holdings" --jurisdiction gb --limit 50
uv run python scripts/ingest_gleif.py --input data/raw/gleif/sample.json
uv run python scripts/ingest_opensanctions.py --input data/raw/opensanctions/entities.ftm.json

# 4. Build the unified company table
uv run python scripts/build_candidate_tables.py

# 5. Sanity-check the GoldenMatch config
uv run python scripts/run_goldenmatch_smoke.py

# 6. Run the real GoldenMatch dedupe pass (writes reports/generated/company_*)
uv run python scripts/run_goldenmatch_full.py --what company

# 7. Derive cheap seed labels, score the run, and build the graph
uv run python scripts/derive_seed_labels.py
uv run python scripts/eval_against_labels.py
uv run python scripts/build_graph_smoke.py

# 8. Address-cluster pass + persons table (optional, but cheap)
uv run python scripts/build_address_table.py
uv run python scripts/report_shared_addresses.py
uv run python scripts/build_person_table.py
uv run python scripts/run_goldenmatch_full.py --what address
uv run python scripts/run_goldenmatch_full.py --what person

# 9. Coverage report across everything in interim/ and processed/
uv run python scripts/coverage_report.py
```

If you have `just` installed, all of the above are also available as recipes:
`just setup`, `just test`, `just ingest-icij`, `just smoke-graph`, etc.

## Running on Railway

The full ICIJ + GLEIF dataset is too big to dedupe on a laptop (4.1M rows
of unified company entities). The repo ships a small FastAPI control
plane (`src/shellnet/job_server.py`) that wraps each pipeline stage as
an HTTP endpoint and is deployable to Railway via the included
`Dockerfile` + `railway.json`.

Architecture:

```
laptop  --POST /upload-zip-->  shellnet-job (FastAPI)
                                |
                                +-- /data           (Railway volume, 50 GB)
                                +-- /unzip /ingest /build /match /publish ...
                                |
                                +-- DATABASE_URL --> Postgres (shellnet schema)
```

Setup (one-time):

```bash
railway link --project <project-id>
railway add --service shellnet-job
railway volume add --mount-path /data            # MSYS users: pass //data
railway variables -s shellnet-job \
  --set "SHELLNET_JOB_TOKEN=<your-token>" \
  --set "SHELLNET_DATA_DIR=/data" \
  --set 'DATABASE_URL=postgresql://${{postgres.POSTGRES_USER}}:${{postgres.POSTGRES_PASSWORD}}@${{postgres.RAILWAY_PRIVATE_DOMAIN}}:${{postgres.RAILWAY_TCP_APPLICATION_PORT}}/${{postgres.POSTGRES_DB}}'
railway up --service shellnet-job
railway domain --service shellnet-job
```

A typical run end-to-end (`$URL` = the generated Railway domain,
`$TOK` = your token):

```bash
# 1. Upload the ICIJ Offshore Leaks zip from your laptop
SHELLNET_JOB_URL=$URL SHELLNET_JOB_TOKEN=$TOK \
  uv run python scripts/upload_icij.py full-oldb.LATEST.zip
curl -X POST -H "Authorization: Bearer $TOK" "$URL/unzip"
curl -X POST -H "Authorization: Bearer $TOK" "$URL/ingest?source=icij"

# 2. Pull GLEIF + OpenSanctions inside the container
curl -X POST -H "Authorization: Bearer $TOK" \
  "$URL/fetch-url?url=https://data.opensanctions.org/datasets/latest/us_ofac_sdn/entities.ftm.json&dest=raw/opensanctions/us_ofac_sdn.ftm.json"
curl -X POST -H "Authorization: Bearer $TOK" "$URL/ingest?source=opensanctions"

# (GLEIF: see docs/data-sources.md for the GLEIF API URL, then
#  /fetch-url + /unzip-file + /ingest?source=gleif)

# 3. Build the unified table, filter, dedupe, list-match, publish
curl -X POST -H "Authorization: Bearer $TOK" "$URL/build?what=company"
curl -X POST -H "Authorization: Bearer $TOK" \
  "$URL/run-script?name=filter_company_no_gleif"
curl -X POST -H "Authorization: Bearer $TOK" "$URL/match?what=company"
curl -X POST -H "Authorization: Bearer $TOK" "$URL/publish?what=company"

# 4. Cross-source: match ICIJ+OS deduped entities against GLEIF as a reference
curl -X POST -H "Authorization: Bearer $TOK" \
  "$URL/run-script?name=extract_gleif_unified"
curl -X POST -H "Authorization: Bearer $TOK" \
  "$URL/match-against?target=processed/company_entities.parquet&against=processed/gleif_unified.parquet&run_name=icij_os_vs_gleif"
curl -X POST -H "Authorization: Bearer $TOK" \
  "$URL/publish-list-match?run_name=icij_os_vs_gleif"
curl -X POST -H "Authorization: Bearer $TOK" \
  "$URL/run-script?name=review_matches"

# Poll state any time
curl -H "Authorization: Bearer $TOK" "$URL/status"
curl -H "Authorization: Bearer $TOK" "$URL/logs/<stage>?tail=200"
```

Results land in two places:

- `/data/processed/` and `/data/reports/generated/` on the Railway volume
  (parquet + CSV + markdown reports).
- `shellnet.runs`, `shellnet.clusters`, `shellnet.same_as_pairs`, and
  `shellnet.list_matches` in the project Postgres — query directly or
  surface from the showcase frontend.

The full ICIJ + OpenSanctions dedupe at this scale fits in ~3 GB and runs
in ~1 minute. The ICIJ+OS → GLEIF list-match runs in ~10 minutes on the
default Railway Pro service (24 vCPU / 24 GB). Full pairwise dedupe over
ICIJ + GLEIF + OpenSanctions (4.1M rows) does **not** fit at 24 GB —
list-match is the supported shape at this scale.

## Directory layout

```
configs/        GoldenMatch YAMLs and source manifests
data/           Raw / interim / processed / sample data (git-ignored except .gitkeep)
docs/           Source descriptions, methodology, roadmap
notebooks/      Exploratory notebooks (kept lightweight; large outputs not committed)
reports/        Generated reports (git-ignored except .gitkeep)
scripts/        Thin Typer CLIs that wrap library code
src/shellnet/   Library code: schemas, normalization, source adapters, matching, graph
tests/          Pytest suite + tiny synthetic fixtures
Dockerfile      Container image for the Railway job service
railway.json    Railway deploy config (healthcheck path, restart policy)
```

## Configuration

All secrets live in `.env` (see `.env.example`). Today the only relevant
secret is `OPENCORPORATES_API_KEY`, which is *optional* — adapters work
without it but at lower rate limits and with less data per record.

## Status

**v1.0.0** — Phases 0–6 shipped on `main`. Full real-data ingest
(ICIJ + GLEIF + OpenSanctions + UK PSC), 300 hand-labelled marginal
pairs, v1 → v2 config sweep with band-weighted precision lift,
centrality + Louvain on the cluster sub-graph, and two end-to-end
case-study writeups. What works today:

- All four source adapters parse fixture-shaped inputs to parquet, including
  ICIJ officers and intermediaries.
- A streaming GLEIF Golden Copy adapter
  (`shellnet.sources.gleif_golden_copy`) for the multi-GB CDF JSON file —
  the v1-API adapter OOMs on the real file, this one chunks via `ijson`
  + per-batch parquet writes.
- Three unified tables: `company_entities`, `address_entities`,
  `person_entities`. Each gracefully handles missing sources.
- Three GoldenMatch configs (`goldenmatch_company.yml`,
  `goldenmatch_address.yml`, `goldenmatch_person.yml`). The company config
  has been **tuned post-spot-check**: `token_sort` instead of
  `jaro_winkler` on names + threshold raised to 0.92 to suppress
  leading-token false positives. See `docs/roadmap.md` § Phase 2.
- A FastAPI control plane (`src/shellnet/job_server.py`) deployable to
  Railway via the included `Dockerfile` / `railway.json`. Each pipeline
  stage is an endpoint (upload, fetch-url, unzip, ingest, build, match,
  match-against, publish, run-script). See § Running on Railway below.
- A Postgres writer (`src/shellnet/publish.py`) that persists dedupe runs
  and list-match results into a `shellnet` schema.
- `scripts/run_goldenmatch_full.py` shells out to the GoldenMatch CLI and
  joins its cluster output back to our entity ids.
- `scripts/generate_candidate_pairs.py` + `derive_seed_labels.py` +
  `eval_against_labels.py` form a labelling + evaluation pipeline.
- `scripts/build_address_table.py` + `report_shared_addresses.py` surface
  shared-agent clusters as Markdown + parquet (top hit on the full ICIJ
  ingest: Portcullis TrustNet Chambers hosts 33,858 entities).
- `scripts/build_person_table.py` fuses ICIJ officers/intermediaries with
  OpenSanctions Persons.
- `scripts/filter_company_table.py` drops placeholder names, mega-blocks,
  and optionally individual sources before matching.
- `scripts/review_matches.py` produces a heuristic precision review of a
  list-match run (identical / normalized_eq / jur_close / jur_loose /
  low_overlap classes crosstabbed against score bands).
- The graph smoke layers GoldenMatch `same_as` edges on top of source
  relationships.
- `scripts/coverage_report.py` writes per-column fill-rate tables for every
  interim/processed parquet.
- 60 pytest tests run end-to-end with no network.

**v1.0 is the case-study deliverable.** Phases 0–6 are shipped: ingest,
unified tables, matching + eval, address + person tables, graph
analysis, and two case-study writeups with full provenance. Items
parked for v1.0 (full list in `docs/status.md` § Parked / future work):

- OpenCorporates ingest — adapter ready, blocked on API key + curated
  seed list.
- Probabilistic matchkey + `negative_evidence` — labels exist (300
  pairs); `negative_evidence` is blocked on an upstream goldenmatch
  1.12.x polars schema bug in `match`.
- Address dedupe at full scale — needs the mega-block filter applied
  the same way as companies, or pre-stripped legal-form prefixes.
- `normalize_person_name` — currently borrows the company normalizer.
- More case studies — Phoenix Spree + Epstein are shipped; centrality
  + community output should surface 1–2 more candidates.
- GLEIF Golden Copy XML / ZIP — JSON / JSONL parsing is live; XML +
  ZIP raise `NotImplementedError`.

## Legal & ethical

- This project is research code released under the MIT licence.
- The **datasets** it ingests are governed by their own licences and terms of
  use. Read them before redistributing anything you derive.
- Do not publish identity-linked claims about specific people or companies
  without independent review.
- Do not scrape OpenCorporates aggressively. Use the API, set a key, respect
  the rate limits.
