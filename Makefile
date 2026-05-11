# Mirror of the most useful `just` recipes for environments without `just`.

.PHONY: setup test lint format ingest-icij candidates smoke-match smoke-graph

setup:
	uv sync --extra dev

test:
	uv run pytest

lint:
	uv run ruff check src tests scripts

format:
	uv run ruff format src tests scripts

ingest-icij:
	uv run python scripts/ingest_icij.py

candidates:
	uv run python scripts/build_candidate_tables.py

smoke-match:
	uv run python scripts/run_goldenmatch_smoke.py

smoke-graph:
	uv run python scripts/build_graph_smoke.py
