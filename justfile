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

# --- QA --------------------------------------------------------------------

test:
    uv run pytest

lint:
    uv run ruff check src tests scripts

format:
    uv run ruff format src tests scripts
