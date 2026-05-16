# Mirror of the most useful `just` recipes for environments without `just`.

.PHONY: setup test lint format ingest-icij candidates smoke-match smoke-graph \
	deploy run-sanctions-overlay run-reconcile-equasis run-reconcile-ru \
	run-reconcile-sec run-scrape-disqualified-directors run-scrape-mp-interests \
	deploy-and-run-sanctions-overlay

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

# --- Railway deploy + remote scripts --------------------------------------
# Reads SHELLNET_JOB_URL and SHELLNET_JOB_TOKEN from env. See justfile for
# the per-script recipes; these are the ones operators use most.

deploy:
	railway up --detach --ci --service shellnet-job

run-sanctions-overlay:
	./scripts/_railway_job.sh run sanctions_overlay
	./scripts/_railway_job.sh fetch processed/sanctions_overlay.parquet

run-reconcile-equasis:
	./scripts/_railway_job.sh run reconcile_equasis
	./scripts/_railway_job.sh fetch reports/generated/shortlist_imos_enriched.csv

run-reconcile-ru:
	./scripts/_railway_job.sh run reconcile_ru_companies
	./scripts/_railway_job.sh fetch reports/generated/ru_shortlist_enriched.csv

run-reconcile-sec:
	./scripts/_railway_job.sh run reconcile_sec_filings
	./scripts/_railway_job.sh fetch reports/generated/us_shortlist_sec.csv

run-scrape-disqualified-directors:
	./scripts/_railway_job.sh run scrape_uk_disqualified_directors
	./scripts/_railway_job.sh run ingest_uk_disqualified_directors
	./scripts/_railway_job.sh fetch interim/uk_disqualified_directors.parquet

run-scrape-mp-interests:
	./scripts/_railway_job.sh run scrape_mp_interests
	./scripts/_railway_job.sh fetch raw/scrapers/members-financial-interests/members-financial-interests.csv

deploy-and-run-sanctions-overlay: deploy run-sanctions-overlay
