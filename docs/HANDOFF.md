# Hand-off: Cluster Explanation Engine → "find the wow" phase

_Last updated: 2026-05-25. Read this first if you're picking the work up cold._

## TL;DR

The full "machine-assisted investigative reasoning" layer is **built, tested,
and merged** (PR #53). What is **not** done: it has never run against the real
corpus, so we have **no demonstrably interesting ("wow") network yet**. The
single blocker is network access — this Claude-Code-on-the-web environment's
egress allowlist blocks the Railway job server. Everything below is about
getting past that and hunting for a recognizable named endpoint.

## What shipped (PR #53, merged to main)

Ten features, all pure-functional modules under `src/shellnet/investigations/`
with thin Typer CLIs under `scripts/` and entries in the Railway job-server
allowlist (`src/shellnet/job_server.py:_ALLOWED_SCRIPTS`). ~218 tests green,
ruff + format clean.

| # | Feature | Module | Script | Job-server name |
| --- | --- | --- | --- | --- |
| 1 | Cluster explanation engine | `cluster_explainer.py` | `explain_cluster.py` | `explain_cluster`, `explain_top_clusters` |
| 2 | Investigative-value ranking | `investigative_ranking.py` | `rank_by_investigative_value.py` | `rank_by_investigative_value`, `..._with_join` |
| 3 | Anomaly / contradiction detection | `anomalies.py` | (in explain) | — |
| 4 | Narrative-path generation | `narrative_paths.py` | (in explain) | — |
| 5 | Discovery delta | `discovery_delta.py` | (in explain) | — |
| 6 | Subcluster extraction | `subcluster.py` | `extract_subclusters.py` | `extract_subclusters` |
| 7 | Temporal reconstruction | `temporal.py` | (in explain) | — |
| 8 | Source-document bundling | `evidence_bundle.py` | `bundle_evidence.py` | `bundle_evidence` |
| 9 | Attention optimizer | `attention.py` | `rank_by_attention.py` | `rank_by_attention` |
| 10 | Interactive graph replay | `graph_replay.py` | `replay_graph.py` | `replay_graph` |

Every CLI supports an **offline `--clusters-parquet` fallback** so it runs
without Postgres — that's how all of it was validated against the
`tests/fixtures/` ICIJ sample (the toy ACME/Sunrise companies).

## The open problem: no wow factor

Honest assessment from this session:

1. **Wow comes from a *name*, not from structure.** A 40-company web only
   lands with an audience if the trail ends at a recognizable
   sanctioned/politically-exposed person, or at a contradiction implying a
   crime. The engine ranks *structural* interest (rare intermediaries,
   bridges, centrality), which is a different axis from "recognizable human."
2. **The score treats a famous endpoint as 1/6 of the weight.**
   `sanctions_proximity` is one equal component among six in
   `attention.py`. For wow, endpoint identity should dominate.
3. **It has never run on the real corpus.** Everything proven so far is the
   4-company fixture. The real parquets live on the Railway `/data` volume and
   the new rankers have not touched them. We genuinely don't know what's at
   the top of the real attention queue.
4. **These leaks are picked over.** ICIJ has mined Panama/Pandora for years;
   the famous connections are mostly already published. The realistic wow here
   is probably a *non-obvious link between two already-known bad actors* —
   exactly what cross-source convergence + narrative paths target, but only if
   we hunt for it deliberately.

## The blocker: network egress allowlist

This environment runs a **restrictive network allowlist**. Probed this session:

| Host | Result |
| --- | --- |
| `pypi.org` | ✅ 200 |
| `api.github.com` | ✅ reachable (GitHub's own rate-limit, not the proxy) |
| `shellnet-job-production.up.railway.app` | ❌ `Host not in allowlist` |
| `api.tavily.com` | ❌ `Host not in allowlist` |
| `api.firecrawl.dev` | ❌ `Host not in allowlist` |

So even with a valid `SHELLNET_JOB_TOKEN`, the Railway job server is
unreachable from here. `DATABASE_URL` in the env is a Railway `${{...}}`
template (interpolated only inside Railway's network), so direct Postgres
from this container is also impossible — which is fine, because the job
server runs *inside* Railway and can reach Postgres for us.

### Unblock (must be done in the web UI, then a NEW session)

1. Click the **cloud icon** (current environment name) → **Edit** the
   environment.
2. **Network access** selector → **Custom**.
3. **Allowed domains**, one per line:
   ```
   shellnet-job-production.up.railway.app
   api.tavily.com
   api.firecrawl.dev
   ```
   (`*.up.railway.app` is more robust to domain changes. Tavily/Firecrawl
   only needed for web name-verification.)
4. **Tick "Also include default list of common package managers"** — without
   it, PyPI is blocked and `uv sync` breaks.
5. Save, then **start a fresh session** from claude.ai/code. Network-policy
   changes do **not** apply to a resumed session — only new ones. (Confirmed
   this session: re-probing after an edit still returned `Host not in
   allowlist` because we were resumed, not fresh.)

Docs: https://code.claude.com/docs/en/claude-code-on-the-web (see "Network
access" → "Allow specific domains").

## Railway job server reference

- URL: `https://shellnet-job-production.up.railway.app` (also `vars.SHELLNET_JOB_URL`)
- Auth: header `Authorization: Bearer $SHELLNET_JOB_TOKEN`.
  **Store the token as an environment secret — never paste it in chat.** The
  token shared in the prior session transcript should be rotated.
- Endpoints (all auth except `/healthz`):
  - `GET /healthz` → `{"ok": true, ...}` when reachable
  - `GET /files` → JSON tree of `/data`
  - `GET /download?path=<relative-to-/data>` → file stream
  - `GET /status`, `GET /logs/{stage}`
  - `POST /run-script?name=<allowlist-key>` → runs a script (auto-prepends
    `python`; allowlist entries must NOT start with `python`)
- Outputs land under `/data/...` (volume, persists). `/app/reports/...` is ephemeral.

### Critical caveat: the running deployment is PRE-MERGE

The live Railway service is whatever was deployed *before* PR #53 merged, so
the new allowlist entries (`rank_by_attention`, `explain_top_clusters`, …) are
**not there yet**. Per CLAUDE.md, after merging to main you must:

```
git pull --ff-only
railway up --detach --ci --service shellnet-job
```

This requires the Railway CLI + auth, which Claude does **not** have from the
web environment — a human has to run it. Until then, only the *old* allowlist
scripts are runnable remotely (`rank_clusters`, `centrality`,
`list_match_os_sanctions_vs_icij`, `sanctions_overlay`, the
`filter_match_survivors` pipeline, etc.).

## Plan once unblocked (in order)

1. **Cheapest first — read the existing leads file.** `/download` the
   already-generated `investigative_grade_survivors.csv` (output of the
   pre-existing `list_match_os_sanctions_vs_icij` → `enrich_match_with_dob` →
   `score_prior_coverage` → `filter_match_survivors` pipeline). If a
   recognizable sanctioned/PEP name exists in this corpus, it is already in
   that file. This may settle the wow question without running anything new.
   ```bash
   curl -sS -H "Authorization: Bearer $SHELLNET_JOB_TOKEN" \
     "$SHELLNET_JOB_URL/download?path=reports/generated/investigative_grade_survivors.csv" \
     -o /tmp/survivors.csv
   ```
   Also worth grabbing: `cluster_ranking.parquet`,
   `list_match_os_sanctions_vs_icij_matched.csv`, `sanctions_overlay.parquet`.
2. **Redeploy, then run the new rankers** (needs the human `railway up` step).
   Then `POST /run-script?name=rank_by_investigative_value`, then
   `name=rank_by_attention`, `/download` the
   `cluster_attention_ranking.parquet` + `cluster_next_actions.md`, and read
   the top of the queue.
3. **If the top is still nameless**, the fix is the **sanctions/PEP-first
   re-weighting**: bias `attention.py` so endpoint identity dominates (heavily
   up-weight `sanctions_proximity` and add a PEP/sanctions-hit term), then run
   the narrative-path engine *outward from sanctioned names* hunting for an
   active, real-world company at the other end. Target headline: "sanctioned
   person X is one shared-nominee hop from still-operating company Y." This is
   a small, well-scoped change to `attention.py` + a new
   `--weights` flag on `rank_by_attention.py`; not yet built.

## Local dev quickstart

```bash
uv sync --extra dev                 # dev deps (pytest/ruff) are an extra
uv run --no-sync pytest             # 218 tests
uv run --no-sync ruff check src scripts tests
uv run --no-sync ruff format --check src scripts tests
```

To exercise the whole pipeline offline against the fixture (no Railway, no
Postgres), stage the `tests/fixtures/` ICIJ sample into a temp dir, build the
unified table, write a synthetic `(cluster_id, entity_uid)` parquet, and run
any CLI with `--no-postgres --clusters-parquet <path>`. See the staging helper
in `tests/test_cluster_explainer.py::_stage_full_fixtures` for the exact steps.

## Security to-do

- Rotate `SHELLNET_JOB_TOKEN`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`, and the
  Postgres password — they were shared in a chat transcript.
- Store the job token as an environment **secret** (env var), not inline.
