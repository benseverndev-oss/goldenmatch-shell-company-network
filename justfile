# Common commands. Install `just` (https://github.com/casey/just) or use the
# Makefile equivalents below by hand.

default:
    @just --list

# --- Setup -----------------------------------------------------------------

setup:
    uv sync --extra dev

# --- Ingestion -------------------------------------------------------------

ingest-icij:
    uv run python scripts/ingest_icij.py

ingest-opencorporates query jurisdiction="" limit="50":
    uv run python scripts/ingest_opencorporates.py --query "{{query}}" --jurisdiction "{{jurisdiction}}" --limit {{limit}}

ingest-gleif input sample="0":
    uv run python scripts/ingest_gleif.py --input {{input}} --sample {{sample}}

ingest-opensanctions input="":
    uv run python scripts/ingest_opensanctions.py --input "{{input}}"

# --- Build / smoke ---------------------------------------------------------

normalize:
    uv run python scripts/normalize_entities.py

candidates:
    uv run python scripts/build_candidate_tables.py

smoke-match:
    uv run python scripts/run_goldenmatch_smoke.py

smoke-graph:
    uv run python scripts/build_graph_smoke.py

# --- Full runs + reporting ------------------------------------------------

addresses:
    uv run python scripts/build_address_table.py

persons:
    uv run python scripts/build_person_table.py

run-company:
    uv run python scripts/run_goldenmatch_full.py --what company

run-address:
    uv run python scripts/run_goldenmatch_full.py --what address

run-person:
    uv run python scripts/run_goldenmatch_full.py --what person

candidates-csv:
    uv run python scripts/generate_candidate_pairs.py

seed-labels:
    uv run python scripts/derive_seed_labels.py

eval:
    uv run python scripts/eval_against_labels.py

shared-addresses:
    uv run python scripts/report_shared_addresses.py

coverage:
    uv run python scripts/coverage_report.py

# Seed-query investigation. Example: just investigate "ACME HOLDINGS" bvi
investigate name jurisdiction="":
    uv run python scripts/investigate_entity.py --name "{{name}}" --jurisdiction "{{jurisdiction}}"

# Batch seed-query. Example: just investigate-batch seeds/example_entities.csv
investigate-batch seeds:
    uv run python scripts/investigate_entities.py {{seeds}}

# Person seed-query. Example: just investigate-person "Jeffrey Epstein" us
investigate-person name country="":
    uv run python scripts/investigate_person.py --name "{{name}}" --country "{{country}}"

# Address seed-query. Example: just investigate-address "Ugland House Grand Cayman" ky
investigate-address text country="":
    uv run python scripts/investigate_address.py --text "{{text}}" --country "{{country}}"

# 2-hop officer-overlap walk from a company entity_uid.
expand-2hop entity_uid label:
    uv run python scripts/expand_2hop.py --entity-uid "{{entity_uid}}" --label "{{label}}"

# --- QA --------------------------------------------------------------------

test:
    uv run pytest

lint:
    uv run ruff check src tests scripts

format:
    uv run ruff format src tests scripts

# --- Railway deploy + remote scripts --------------------------------------
# Operator-side recipes that drive the shellnet-job service on Railway.
# Per CLAUDE.md, set `gh auth switch -u benzsevern` before any gh op, and
# remember Railway does NOT auto-deploy from GitHub — re-deploy after every
# merge.

# Re-deploy the Railway image (run after merging to main).
deploy:
    railway up --detach --ci --service shellnet-job

# Generic: trigger a /run-script entry by name and poll until done.
# Example: just job-run sanctions_overlay
job-run name:
    ./scripts/_railway_job.sh run {{name}}

# Generic: download a file from /data on the Railway volume.
# Example: just job-fetch processed/sanctions_overlay.parquet
job-fetch relpath out="":
    ./scripts/_railway_job.sh fetch {{relpath}} {{out}}

job-status stage="":
    ./scripts/_railway_job.sh status {{stage}}

# One-shot: build the sanctions multi-list overlay on Railway and pull it
# back. Uses interim/opensanctions_entities.parquet already on the volume.
run-sanctions-overlay:
    just job-run sanctions_overlay
    just job-fetch processed/sanctions_overlay.parquet

# One-shot: build the overlay merged with goldenmatch-sanctions-reconciliation
# records.parquet. Drop the external file under
# /data/raw/sanctions_reconciliation/records.parquet first (via /fetch-url
# or /upload-zip, depending on how it ships).
run-sanctions-overlay-external:
    just job-run sanctions_overlay_external
    just job-fetch processed/sanctions_overlay.parquet

# Equasis fan-out. Needs EQUASIS_CREDENTIALS set in the Railway service env
# AND a deduped shortlist already at /data/reports/generated/shortlist_imos.csv.
run-reconcile-equasis:
    just job-run reconcile_equasis
    just job-fetch reports/generated/shortlist_imos_enriched.csv

# Russian FTS + ITSoft fan-out (no auth). Needs a shortlist at
# /data/reports/generated/ru_shortlist.csv.
run-reconcile-ru:
    just job-run reconcile_ru_companies
    just job-fetch reports/generated/ru_shortlist_enriched.csv

# SEC EDGAR fan-out (no auth). Needs a shortlist at
# /data/reports/generated/us_shortlist.csv.
run-reconcile-sec:
    just job-run reconcile_sec_filings
    just job-fetch reports/generated/us_shortlist_sec.csv

# UK Insolvency Service disqualified-directors register: scrape → ingest →
# pull the join-ready parquet. The scrape is sequential (~hours) so this is
# a "kick off and walk away" recipe.
run-scrape-disqualified-directors:
    just job-run scrape_uk_disqualified_directors
    just job-run ingest_uk_disqualified_directors
    just job-fetch interim/uk_disqualified_directors.parquet

# UK MPs' Register of Members' Financial Interests. CSV only for now.
run-scrape-mp-interests:
    just job-run scrape_mp_interests
    just job-fetch raw/scrapers/members-financial-interests/members-financial-interests.csv

# Post-merge convenience: redeploy, then build the sanctions overlay end-to-end.
deploy-and-run-sanctions-overlay:
    just deploy
    just run-sanctions-overlay
