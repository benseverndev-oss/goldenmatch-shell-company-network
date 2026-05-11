# goldenmatch-shell-company-network

A reproducible **case study** in using
[GoldenMatch](https://pypi.org/project/goldenmatch/) to reconcile shell-company
and offshore-entity records across public datasets, then reconstruct fragmented
corporate-identity graphs from them.

This repo is **scaffolding plus ingestion**. It does not (yet) contain a
finished investigation. The point of the first pass is to make it cheap and
honest to *run* the analysis: drop public bulk files into `data/raw/`, run a
handful of scripts, and you'll get an interim parquet per source, a unified
company table, a GoldenMatch run, and a NetworkX graph summary.

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
```

## Configuration

All secrets live in `.env` (see `.env.example`). Today the only relevant
secret is `OPENCORPORATES_API_KEY`, which is *optional* — adapters work
without it but at lower rate limits and with less data per record.

## Status

Phase 0 (scaffolding) and the analytical plumbing for Phases 2–5 are in place.
What works today:

- All four source adapters parse fixture-shaped inputs to parquet, including
  ICIJ officers and intermediaries.
- Three unified tables: `company_entities`, `address_entities`,
  `person_entities`. Each gracefully handles missing sources.
- Three GoldenMatch configs (`goldenmatch_company.yml`,
  `goldenmatch_address.yml`, `goldenmatch_person.yml`) — all validated against
  the real engine, the company config runs end-to-end on fixtures.
- `scripts/run_goldenmatch_full.py` shells out to the GoldenMatch CLI and
  joins its cluster output back to our entity ids.
- `scripts/generate_candidate_pairs.py` + `derive_seed_labels.py` +
  `eval_against_labels.py` form a labelling + evaluation pipeline.
- `scripts/build_address_table.py` + `report_shared_addresses.py` surface
  shared-agent clusters as Markdown + parquet.
- `scripts/build_person_table.py` fuses ICIJ officers/intermediaries with
  OpenSanctions Persons.
- The graph smoke layers GoldenMatch `same_as` edges on top of source
  relationships.
- `scripts/coverage_report.py` writes per-column fill-rate tables for every
  interim/processed parquet.
- 60 pytest tests run end-to-end with no network.

What's still ahead (`docs/roadmap.md`): real-data ingestion (sandbox blocks
remote downloads, so this is a follow-up), a labelled evaluation subset
contributed by humans, GLEIF XML parsing, an investigation writeup.

## Legal & ethical

- This project is research code released under the MIT licence.
- The **datasets** it ingests are governed by their own licences and terms of
  use. Read them before redistributing anything you derive.
- Do not publish identity-linked claims about specific people or companies
  without independent review.
- Do not scrape OpenCorporates aggressively. Use the API, set a key, respect
  the rate limits.
