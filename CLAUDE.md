# Project: goldenmatch-shell-company-network

## Core conventions
- **All heavy compute runs on Railway**, never local — laptop OOMs on the corpus sizes. See `memory/compute_on_railway.md`.
- **`gh auth switch -u benzsevern`** before any `gh pr` operation — `benzsevern-mjh` is the default-active account and can't see this private repo.
- **After merging to main**, `git pull --ff-only` then `railway up --detach --ci --service shellnet-job` — Railway does *not* auto-deploy from GitHub pushes.

## Railway job server
- URL: `https://shellnet-job-production.up.railway.app` (also `vars.SHELLNET_JOB_URL`)
- Bearer token: `secrets.SHELLNET_JOB_TOKEN`
- `/run-script?name=<n>` auto-prepends `python` — allowlist entries in `src/shellnet/job_server.py:_ALLOWED_SCRIPTS` must NOT start with `python` (e.g. `["scripts/foo.py", "--input", "..."]`).
- All script outputs should land under `/data/...` (volume-mounted, persists across redeploys). `/app/reports/...` is ephemeral.
- `/download?path=<relative-to-/data>` to pull files back locally.

## Heavy-data patterns
- For lookups against 1M+ row parquets, use `pl.scan_parquet(p).filter(pl.col("x").is_in(needed_set)).collect()` — never `read_parquet().iter_rows()` on the full table.
- `df.to_dicts()` on >100k rows will OOM on Windows; iterate via `.iter_rows(named=True)` on a small slice.

## OS / matcher gotchas
- OS topic taxonomy: `sanction` = asset-freeze; `sanction.linked` = adjacent (NOT a freeze); `reg.action` = regulatory enforcement; `crime` = AML/criminal. Don't conflate.
- OS sanction-publishing datasets are named e.g. `us_ofac_sdn`, `us_sam_exclusions`, `gb_fcdo_sanctions` — the substring `us_ofac` misses `us_sam_exclusions` (the Sovcomflot Cyprus shells live there). See `scripts/walk_gleif_ownership.py` for the full ~20-name filter.
- GoldenMatch person dedupe OOMs at common-first-name blocks (`anthony` 168k records, `mr muh...` 31k, Russian patronymics 19k). Pre-filter target by jurisdiction before matching.

## Diagnostics
- `scripts/_inspect_zip.py` and `scripts/_inspect_bods_schemas.py` for inspecting raw zip/parquet contents on Railway.
- `docs/ingestion_roadmap.md` is the current source of truth for ingestion priorities + lessons-learned.
