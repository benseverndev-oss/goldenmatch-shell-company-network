# Handoff — `claude/railway-host-pnF9F`

_Last updated: 2026-05-25_

## What we're trying to accomplish

**Big picture.** This repo is a reproducible investigative pipeline for
offshore-leak corpora (ICIJ Offshore Leaks + OpenSanctions + GLEIF + UK PSC +
UK disqualified directors). It resolves entities across those noisy sources
with GoldenMatch, builds a confidence-weighted graph, mines structure
(shared addresses/officers, latent communities, jurisdiction bridges), and
produces named investigative *candidates* (hypotheses, not accusations) with
quantified discovery-advantage benchmarks vs. single-source search.

**Why Railway.** The full corpus (~1.24M companies, ~1.86M persons, 12M+ UK PSC
rows) OOMs a laptop. All heavy compute runs on the `shellnet-job` FastAPI
control plane deployed to Railway, which wraps each pipeline stage as an
authenticated HTTP endpoint over a persistent `/data` volume. See
`src/shellnet/job_server.py` and the README "Running on Railway" section.

**This branch's immediate goal.** Get the Railway job host usable from this
session — confirm it's live and wire up the credentials needed to drive its
authenticated endpoints (`/status`, `/run-script`, `/download`, etc.).

## State as of this session

- **Host is up.** `GET https://shellnet-job-production.up.railway.app/healthz`
  → `200 {"ok":true,"data_dir":"/data"}`. The `/data` volume is mounted and
  bearer auth is enforced (`/status` returns `401` without a valid token).
- **Credentials saved to `.env`** (git-ignored via `.gitignore:23` — confirmed
  not tracked). Keys present: `SHELLNET_JOB_TOKEN`, `SHELLNET_DATA_DIR=/data`,
  `FIRECRAWL_API_KEY`, `TAVILY_API_KEY`, `DATABASE_URL`.
  - ⚠️ `DATABASE_URL` is stored in Railway reference-variable syntax
    (`${{...}}`) which only resolves inside Railway's own runtime — it is **not**
    a usable connection string from this container.
  - `SHELLNET_JOB_URL` is **not** in `.env` yet; the host URL above is hardcoded
    in CLAUDE.md. Export it if scripts/helpers need it.

## How to drive the host

```bash
set -a; . ./.env; set +a
export SHELLNET_JOB_URL=https://shellnet-job-production.up.railway.app
# status:
curl -fsS -H "Authorization: Bearer $SHELLNET_JOB_TOKEN" "$SHELLNET_JOB_URL/status" | python3 -m json.tool
# run an allowlisted script + poll + fetch (operator helper):
scripts/_railway_job.sh run <script-name>
scripts/_railway_job.sh fetch <path-relative-to-/data> [local-out]
```

Allowlisted script names live in `_ALLOWED_SCRIPTS` in
`src/shellnet/job_server.py`. `/run-script?name=<n>` auto-prepends `python`, so
allowlist entries must **not** start with `python`.

## Gotchas (from CLAUDE.md — read it)

- After merging to main: `git pull --ff-only` then
  `railway up --detach --ci --service shellnet-job`. Railway does **not**
  auto-deploy from GitHub pushes.
- `gh auth switch -u benzsevern` before any `gh pr` op (default account can't
  see this private repo).
- Adding a new ingest/script = new `_ALLOWED_SCRIPTS` entry **plus** a redeploy.
- `/data` volume budget ~30 GB; was at ~26 GB post-UK-BODS. Watch `df -h`.

## Open items / next steps

- Decide what we actually want to *run* on the host now that the token is
  wired — e.g. `GET /status` to see current pipeline state, or kick a build.
- Parked work (see `docs/status.md` / `docs/ingestion_roadmap.md`): journalist
  panel-review study, OpenCorporates ingest (needs API key), GLEIF L2 XML/ZIP,
  FinCEN Files (blocked on data shape), OCCRP Laundromat (multi-session).
