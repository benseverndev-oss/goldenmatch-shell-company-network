# Handoff — wrongdoing-lead discovery pipeline

_Last updated: 2026-05-25. Read this to pick the work up cold._

## TL;DR

The project now has, on top of the entity-resolution + reporting stack, a full
**wrongdoing-lead discovery pipeline**: from the sanctioned-PSC survivor matches
through signal detection, gated ranking, live-status/harm enrichment, evidence
dossiers, and a precision feedback loop. It is **built, tested, and merging**.
The single operational thing left is the **Railway deploy (Phase 0)** that
materialises the relationship layer on the volume — see "Remaining work".

The guiding principle, learned the hard way this session: **score the wrongdoing
*act* at a *live* target on an *unjoined* corpus — not list-membership.** Matching
"is this person sanctioned?" rediscovers known actors whose companies are
dissolved. See `docs/wrongdoing_discovery_roadmap.md`.

## What shipped this session

### Investigative findings (merged)
- `reports/investigations/aeza_ofac_uk_psc_finding.md` — first real-corpus run.
  Cross-source convergence (UK PSC ∩ OpenSanctions) surfaced the OFAC/UK-
  sanctioned **Aeza** bulletproof-hosting UK company + a cohort of sanctioned
  Russian oligarchs (Zyuzin, Volozh, Trotsenko, Mordashov, Marchenko) with UK
  corporate vehicles. **All resolved companies are now dissolved/in liquidation**
  — recognizable names, wound-down vehicles. Lead, not verdict.

### Data layer (merged, PR #153)
- `uk_psc_relationships.parquet` is now emitted by the BODS ingest
  (`src/shellnet/sources/bods.py::_build_uk_psc_relationships`). 13.1M
  person→company PSC edges, keyed by `person_source_id` (= the `uk_psc:<id>`
  survivor key) with `company_id` / `company_number` / control nature / dates.

### The pipeline (PR #162, Phases 1–6)
Each phase is a pure, fixture-tested `src/shellnet/investigations/` module + a
thin `scripts/` CLI + a `_ALLOWED_SCRIPTS` entry in `job_server.py`.

| Phase | Module | Script | Job name |
| --- | --- | --- | --- |
| 1 Sanctions-evasion timing | `evasion_timing.py` | `probe_sanctions_evasion_timing.py` | `sanctions_evasion_timing` |
| 2 Wrongdoing scoring + rank | `wrongdoing_signals.py` | `rank_wrongdoing_leads.py` | `rank_wrongdoing_leads` |
| 3 Live status + harm | `company_status.py`, `harm.py` | `enrich_company_status.py` | `enrich_company_status` |
| 4 Disqualified-PSC (s.11 CDDA) | `regulatory_breach.py` | `probe_disqualified_psc_breach.py` | `disqualified_psc_breach` |
| 5 Evidence dossier + gate | `lead_dossier.py` | `build_lead_dossier.py` | `build_lead_dossier` |
| 6 Precision feedback | `lead_outcomes.py` | `score_lead_precision.py` | `score_lead_precision` |

Validated locally on the real corpus: evasion flags **Mordashov → Marina
Mordashova** and **Trotsenko → Gleb Trotsenko**; disqualified-PSC finds **28
candidate breach leads**; the dossier gate blocks publication until a human
ticks the checklist.

## End-to-end run (on Railway, after deploy)

```
ingest_uk_bods                 # -> interim/uk_psc_relationships.parquet  (Phase 0)
sanctions_evasion_timing       # -> processed/sanctions_evasion_timing.parquet
disqualified_psc_breach        # -> processed/regulatory_breach.parquet
rank_wrongdoing_leads          # -> processed/wrongdoing_leads.parquet + report md
enrich_company_status          # -> processed/company_status.parquet (live CH via Firecrawl)
rank_wrongdoing_leads          # re-run with --status to apply live/harm gates
build_lead_dossier             # -> /data/validation/leads/<id>.md  (verify + tick gate)
score_lead_precision           # -> lead_precision.md  (feeds Phase-2 weight retune)
```

All run via `POST /run-script?name=<job>` on the Railway job server. Signal
parquets are pluggable into the ranker via `--extra-signals`.

## PR status (as of writing)

- **Merged to main:** #151 (handoff note), #152 (Aeza finding), #153
  (`uk_psc_relationships`), #154 (roadmap).
- **Merging on green:** #162 (Phases 1–6, closes #156–#161), #163 (Railway MCP
  config). Auto-merge is disabled repo-wide, so they're merged manually when CI
  (`pytest + ruff` + CodeQL) is green.
- **Open:** #155 (Phase 0 deploy — needs Railway).

## Railway

- Job server: `https://shellnet-job-production.up.railway.app` (auth: bearer
  `SHELLNET_JOB_TOKEN`). Endpoints: `/healthz` (no auth), `/files`,
  `/download?path=`, `/run-script?name=`, `/status`, `/logs/{stage}`.
- **Railway MCP installed** (`.mcp.json`, PR #163): hosted server
  `https://mcp.railway.com` (HTTP/OAuth). Connects at **session start**, so it
  only appears in a **fresh session**, where it prompts for OAuth. Alternative:
  local `npx @railway/mcp-server` + `RAILWAY_API_TOKEN` secret.
- Per `CLAUDE.md`: after merging to main, deploy with
  `git pull --ff-only && railway up --detach --ci --service shellnet-job`.

## Remaining work / next steps

1. **Phase 0 deploy (#155).** In a fresh session with Railway MCP authorized:
   redeploy `shellnet-job`, then `run-script ingest_uk_bods` to materialise
   `uk_psc_relationships.parquet` on the volume. Everything else is already
   allowlisted and ready.
2. **First real ranked queue.** Run the end-to-end chain above, then
   `build_lead_dossier` and hand the top dossiers to human review.
3. **Phase 6 loop.** Record verdicts in `/data/validation/outcomes.csv`; rerun
   `score_lead_precision`; retune Phase-2 weights from `signal_lift`.
4. **Phase 4 expansion.** Add a genuinely new wrongdoing-grade corpus
   (procurement / insolvency / FinCEN) — see `docs/ingestion_roadmap.md`.

## Gotchas / caveats

- **Lead, not verdict.** Sanctions/disqualification/dissolution are public
  facts; intent and current control are not. The Phase-5 checklist gates
  publication; never assert wrongdoing without independent confirmation.
- **Designation dates** use OpenSanctions `first_seen` — exact for entities
  listed *via* a sanctions dataset (Aeza = 2025-07-01), a placeholder for
  pre-tracked PEPs (flagged `date_quality=placeholder`).
- **Snapshots lag.** Live company status must be re-checked (the Aeza finding
  flipped active→dissolved on a live Companies House check).
- **Fresh session required** for `.mcp.json` (and any network-policy) changes —
  they don't apply to a resumed session.
- **Compute on Railway.** New probes need a `_ALLOWED_SCRIPTS` entry + redeploy.
- Secrets live in git-ignored `.env`; `SHELLNET_JOB_TOKEN` etc. were shared in
  chat earlier in the project and should be rotated when convenient.
