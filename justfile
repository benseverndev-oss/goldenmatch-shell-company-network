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

# --- QA --------------------------------------------------------------------

test:
    uv run pytest

lint:
    uv run ruff check src tests scripts

format:
    uv run ruff format src tests scripts
