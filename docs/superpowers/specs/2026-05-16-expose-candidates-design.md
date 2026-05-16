# Design — Exposé candidates pipeline

**Date:** 2026-05-16
**Status:** Approved by user (chunk-by-chunk during /brainstorm session); revised after spec-review-loop pass 1
**Origin:** Brainstorm "How can we move the needle on 'new exposé' novelty?"

## Goal

A defensible "we found X first" blog post on `goldenmatch-shell-company-network`. The blog post will hand-pick 3-5 leads from a ranked candidate index this pipeline produces. Each lead must be backed by:

- A 2-hop graph dossier showing what shell network the person sits inside
- A web-search freshness check showing the specific connection isn't already public

The pipeline does NOT write the blog post itself. It produces the candidate index + per-lead dossiers; the human picks the winners and drafts the narrative against them.

## Non-goals

- External journalist pickup (a tighter bar than this design targets)
- Network-pattern novelty (the "shell-cluster catalog" alternative — captured as a follow-up spec, not in this design)
- Auto-drafting the blog post text via LLM
- Full investigation-grade verification (primary-source pulls from Land Registry / court records) — out of scope; surfaced as `prior_coverage` + web-search only

## Pre-existing context

Five join-novelty signal kinds are already shipped (`docs/reports/join_novelty.md`). This design works against **section 4 — rare multi-source officer names** because:

- 200 rare-name candidates (max ≤ 2 entities per source, ≥ 3 tokens, ≥ 2 sources)
- Rare names are the underexposed slice — section 3's exact-name matches surface famous people (Lebedev, Sajwani, Sammut) who fail the "we found X first" test
- The data already exists at `processed/officer_overlap.parquet` after the existing `build_officer_overlap` job

Compute split per `CLAUDE.md`: Railway runs the heavy joins; GH Actions runs the web search + render. Direct-push-to-main since enterprise policy still blocks PR creation.

## Architecture

```
[Railway /data volume]
  Existing: person_entities.parquet, icij_edges.parquet, address_entities.parquet,
            sanctions_overlay.parquet, officer_overlap.parquet, ...
  NEW: processed/rare_officer_dossiers.parquet
       (one denormalized row per [rare_name × source × person_entity × linked_company × attribute])

[GH Actions workflow build-exposes-candidates.yml — workflow_dispatch only]
  1. POST /run-script?name=build_rare_officer_dossiers   → Railway emits the parquet
  2. GET /download                                       → pulls parquet to runner
  3. scripts/search_dossier_freshness.py                 → firecrawl per name → search_results.json
  4. scripts/render_dossiers.py                          → emits per-lead .md + index .md
  5. git commit + push to main (same pattern as render-novelty-report.yml)
```

## Components

| File | Runs on | Purpose |
|---|---|---|
| `scripts/build_rare_officer_dossiers.py` | Railway | 2-hop graph walk per top-N rare names → denormalized parquet |
| `scripts/search_dossier_freshness.py` | Actions runner | Firecrawl 2-3 queries per name, attach top hits to sidecar JSON |
| `scripts/render_dossiers.py` | Actions runner | Render `docs/reports/dossiers/<slug>.md` + `docs/reports/exposes_candidates.md` |
| `.github/workflows/build-exposes-candidates.yml` | GitHub Actions | Orchestrator; `workflow_dispatch` only |
| `tests/test_novelty_ranking.py` | CI / local | Unit test for the ranking function (only logic worth testing) |
| Allowlist entry in `src/shellnet/job_server.py` | Railway | Makes `build_rare_officer_dossiers` callable via `/run-script` |

## Data bridges and known limitations

The 2-hop walk runs against the data we actually have. What we have and what we don't:

| Bridge | Status | Implication |
|---|---|---|
| `person_entities.entity_uid` ↔ `icij_edges.src_node` / `.dst_node` | ✅ Both use the `icij:<numeric>` form | ICIJ person→company expansion is fully supported |
| `company_entities` → address | `normalized_address` is a string column; no `address_id` FK | Address overlap is a string join on `normalized_address`, deduped via `address_entities.address_uid` when needed for cross-referencing |
| `company_entities` → sanctions overlay | No `os_id` column; existing pattern strips `^opensanctions:` from `source_id` to get the overlay key | Adjacency join works **only for companies sourced from OpenSanctions**; ICIJ/PSC-sourced companies cannot be linked to overlay without going through an existing match table |
| `person_entities` → `linked_to_company` | No such column exists | Co-officer derivation must walk source-specific relations; only `icij_edges` is materialized |
| UK PSC person→company relations | ❌ Not materialized in any parquet today | **UK PSC persons surface as "appears in this source" only — no company expansion in v1** |
| OpenSanctions person→company relations | ❌ Not materialized | **OS persons surface as "appears in this source" only — no company expansion in v1** |

The honest consequence: the 2-hop walk produces a **rich** dossier for the ICIJ-source person rows tied to a rare name, and a **thin** one for UK PSC and OS rows. A rare name in 3 sources where one of those is ICIJ gets the full graph; a rare name in {UK PSC, OS} only gets two source-row stubs. The renderer surfaces this asymmetry in the dossier so a reader isn't misled.

Materializing PSC and OS person→company relations is captured as a follow-up spec, not part of this design.

## Data flow

### Seed selection (Railway, build_rare_officer_dossiers.py)

```
officer_overlap.parquet
  ← on-disk filter is max_per_source <= 50, n_tokens >= 2 (per build_officer_overlap.py)
  → re-apply RARE filter: max_per_source <= 2, n_tokens >= 3
  → sort: n_sources DESC, total_entities DESC
  → head: --top-n (default 50)
```

The rare-name filter is **not** baked into the parquet; `build_officer_overlap.py` is permissive on disk and `build_join_novelty_report._rare_officer_overlaps()` does the tightening at report time. This new script must re-apply the same tighter filter independently.

50 not 200 because of (a) firecrawl per-run budget on the Actions side and (b) human triage capacity downstream.

### 2-hop walk per seed name N

```
For each name N:
  matched_persons := person_entities.filter(normalized_name == N)

  # Stub rows: every source row gets at least one dossier row, even without expansion.
  For each person P in matched_persons:
    emit stub row(N, P.source, P.entity_uid, P.name, P.country)

  # ICIJ expansion: walk only ICIJ-source persons (the only relation table we have).
  icij_persons := [P for P in matched_persons if P.source == "icij"]
  seed_uids := icij_persons.entity_uid

  edges := pl.scan_parquet("icij_edges.parquet")
            .filter(src_node.is_in(seed_uids) | dst_node.is_in(seed_uids))
            .collect()
  # Cap per-seed degree to bound 2-hop fan-out (Russian-patronymic outliers etc.).
  edges_per_seed := edges.group_by(seed-side).head(--max-degree, default 25)

  linked_company_uids := union(edges.src_node, edges.dst_node) - seed_uids

  companies := pl.scan_parquet("company_entities.parquet")
                .filter(entity_uid.is_in(linked_company_uids))
                .collect()

  For each company C in companies:
    address_norm := C.normalized_address      # already a string, no lookup needed

    # Sanctions adjacency only resolves for OS-sourced companies (limitation above).
    if C.source == "opensanctions":
      os_id := C.source_id.removeprefix("opensanctions:")  # NOT str.lstrip (charset-based)
      sanc := sanctions_overlay.lookup(os_id)
      sanction_lists := sanc.datasets
      n_datasets := sanc.n_datasets
    else:
      sanction_lists := None
      n_datasets := None

    # Co-officers via the SAME icij_edges scan (only works for ICIJ companies).
    if C.source == "icij":
      co_officer_uids := edges
                          .filter(src_node == C.entity_uid | dst_node == C.entity_uid)
                          .union(src_node, dst_node) - {C.entity_uid}
      co_officers := person_entities.filter(entity_uid.is_in(co_officer_uids)).normalized_name
    else:
      co_officers := []

    emit row(N, "icij", P.entity_uid, P.name, P.country,
             C.entity_uid, C.name, C.jurisdiction, address_norm,
             co_officers, sanction_lists, n_datasets)
```

Output: `processed/rare_officer_dossiers.parquet`. Denormalized (one row per N × P × C plus stub rows for non-expandable sources) so the renderer is pure SELECT.

**Memory profile.** Per `CLAUDE.md`'s heavy-data pattern: the `icij_edges` scan filters on `is_in(seed_uids)` lazily, never materializing the whole 22M-row edge table. The `--max-degree` cap bounds per-seed fan-out so a high-degree seed doesn't blow up the join.

### Web search (Actions, search_dossier_freshness.py)

```
For each distinct rare_name N from the parquet:
  hits_general   := firecrawl_search(f'"{N}"', limit=5)
  hits_offshore  := firecrawl_search(f'"{N}" (shell OR offshore OR director OR PSC)', limit=5)

  # Localized query is only emitted when N has a single dominant jurisdiction
  # across its linked companies. With 3-way ties, the query gets skipped — the
  # localized boost isn't worth the false signal.
  top_juris := dominant_jurisdiction(N)  # plurality with margin >= 2 over runner-up; else None
  if top_juris is not None:
    hits_localized := firecrawl_search(f'"{N}" {top_juris}', limit=3)
  else:
    hits_localized := []

  store: { N: { general: [...], offshore: [...], localized: [...] } }
```

Budget: ~50 names × 2-3 queries ≈ 100-150 firecrawl calls. No artificial cap — firecrawl rate-limits naturally and per-name failures are isolated. Auth via the `FIRECRAWL_API_KEY` GitHub Actions secret (must be provisioned before first run; documented in the workflow's env block).

Per-name failure (rate limit, 5xx) marks that name `search_skipped`; does not poison the batch.

### Novelty score (in render_dossiers.py)

`prior_coverage_n` / `prior_coverage_mainstream` are NOT present on `officer_overlap.parquet` (they live on `dob_confirmed_pair` rows in the join-novelty parquet). For rare-officer rows we have no prior-coverage signal today; the score relies entirely on the web-search outputs and the structural shell-density signals.

Materializing prior-coverage for rare-officer rows is captured as a follow-up; for now the formula is:

```
novelty_score(row) =
    +0.40 * (1 - min(len(hits_offshore) / 5, 1.0))         # few offshore-query hits = newer
    +0.25 * (1 - min(len(hits_general) / 10, 1.0))         # less generally famous
    +0.15 * (1 if len(hits_localized) == 0 else 0)         # zero localized hits = stronger newness
    +0.10 * min(n_linked_companies / 5, 1.0)               # shell-density bonus
    +0.10 * min(n_jurisdictions / 3, 1.0)                  # multi-juris bonus
```

Score ∈ [0, 1]. ≥ 0.80 = "investigate this one." Weights are **constants in `shellnet.novelty_ranking.novelty_score`**, locked by unit tests in `tests/test_novelty_ranking.py`. Operator-tunable flags were considered and rejected as YAGNI: changing weights should require touching code AND updating the test (which is the review gate). The renderer sorts the index by score DESC. Score is a triage signal, NOT a verdict — the explicit comment in the rendered file makes that clear.

**Important: the localized-query term only applies when the localized firecrawl query actually ran** (i.e., the seed had a dominant jurisdiction passing the plurality-with-margin test). Skipped queries must pass `localized_ran=False` into the scorer so a missing dominant-jurisdiction doesn't grant a free 0.15 bonus. This was caught in plan review pass 1.

Names where `len(hits_offshore) == 0` AND `len(hits_general) == 0` AND `n_linked_companies >= 3` are auto-pinned to the top of the index irrespective of score, with a `(uncovered + multi-shell)` annotation — they're the cleanest "found-X-first" candidates.

## Output format

### Per-lead dossier (`docs/reports/dossiers/<slug>.md`)

One file per name. ~150-300 lines. Layout:

```markdown
# Pavel Maslovsky

**Sources:** 3 (icij, uk_psc, opensanctions)  •  **Linked companies:** 5  •  **Jurisdictions:** cy, ru, gb  •  **Novelty score:** 0.82

## Linked entities by source
### ICIJ (2 entities) ...
### UK PSC (3 entities) ...
### OpenSanctions (1 entity) ...

## Shell-network footprint
- 5 distinct linked companies across 3 jurisdictions
- 2 companies share address `12 Some St, Limassol` (co-officers: Sergey X, Elena Y)
- Sanctions adjacency: 1 of 5 linked companies on `ua_nsdc_sanctions`

## Web search (firecrawl, YYYY-MM-DD)
### `"Pavel Maslovsky" (shell OR offshore OR director OR PSC)` — 1 hit
- [The Bell – "Maslovsky's gold mining empire"](https://...) — _snippet_
### `"Pavel Maslovsky"` — 4 hits
- ...

## Reproduce
- `processed/rare_officer_dossiers.parquet`, filter `normalized_name == "pavel maslovsky"`
- Search ran via `scripts/search_dossier_freshness.py` against firecrawl on YYYY-MM-DD
```

### Ranked index (`docs/reports/exposes_candidates.md`)

Single file. Top-50 names by score, sorted DESC.

```markdown
# Exposé candidates — rare cross-source officer overlaps

Top 50 names by novelty score. Score is a triage signal, not a verdict —
open each dossier and judge.

| Rank | Name | Sources | Companies | Juris | Sanctions adj | Web hits (offshore) | Score | Dossier |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Pavel Maslovsky | 3 | 5 | 3 | 1 | 1 | 0.92 | [→](dossiers/pavel-maslovsky.md) |
| ... |
```

## Workflow contract

`workflow_dispatch` only. Inputs:

| Input | Type | Default | Notes |
|---|---|---|---|
| `top_n` | int | `50` | Seed count fed to Railway script |
| `max_degree` | int | `25` | Per-seed edge fan-out cap for the 2-hop walk |

Required env / secrets on the workflow:

| Name | Type | Source |
|---|---|---|
| `SHELLNET_JOB_URL` | repo variable | existing |
| `SHELLNET_JOB_TOKEN` | secret | existing |
| `FIRECRAWL_API_KEY` | secret | **new** — must be provisioned before first run |

Reuses the direct-push-to-main pattern from `render-novelty-report.yml` (enterprise policy blocks PR creation). Per-run idempotency:

- Dossier `.md` files for names that fall out of the top-N on a later run **stay in git**. No auto-prune. Prevents surprise deletions when seed parameters change.
- The index is fully regenerated each run. Stale dossier files become unlinked from the main table but appear in an **Orphaned dossiers** footer section at the bottom of the index (a one-line entry per file with its last-rendered date), so a reader following an external link to an orphaned dossier sees it's no longer top-ranked rather than guessing.

## Error handling

| Failure | Handling |
|---|---|
| `officer_overlap.parquet` missing on Railway | Hard fail with "run `build_officer_overlap` first" |
| firecrawl rate-limited mid-batch | Log, mark that name `search_skipped`, continue; index row shows "needs manual search" |
| firecrawl returns 5xx on a single name | Log, continue (don't poison the batch) |
| firecrawl per-name rate-limit | Log, mark name `search_skipped`, continue; rendered index shows "needs manual search" |
| Renderer encounters a name with zero matched persons (data-skew edge case) | Drop with warning; row was likely a stale rare-name |
| Allowlist entry missing on Railway (new code not deployed) | Workflow's poll step times out; trivial to debug from the run log |
| `FIRECRAWL_API_KEY` secret missing | Workflow fails fast at the search step with a clear "secret not set" error |
| High-degree seed in ICIJ (e.g. a Mossack Fonseca employee) | `--max-degree` cap truncates the edge fan-out per seed; truncated dossier surfaces a `degree_capped` flag so reviewer knows the picture is partial |

## Testing

- **Unit test, `tests/test_novelty_ranking.py`**: synthetic input rows → expected score band. Locks the weights so a thoughtless tweak doesn't silently reshuffle the index.
- **No CI for markdown templates** — they're too fragile to lock in, and the cost of breakage is one ugly run we manually regenerate.
- **Local smoke test** before first Railway/Actions run: invoke `build_rare_officer_dossiers.py` against the locally-cached `data/processed/officer_overlap.parquet` plus a stub stand-in for the other parquets if needed; eyeball one rendered dossier file.

## Quirks worth flagging in the rendered output

1. **Offshore-query hit count is coarse.** A famous person whose Wikipedia page mentions "offshore" once still gets 5 hits. The score is a triage tool; you still scroll the dossier and make the call.
2. **Same-name collisions remain possible.** A rare 3-token name in 2-3 sources can still be two different people sharing a name. The dossier surfaces enough context (jurisdiction, address overlap, co-officers) to spot this; the renderer doesn't try to auto-resolve.
3. **Dossier asymmetry between sources.** ICIJ-source person rows get full 2-hop expansion (linked companies, addresses, co-officers, sanctions adjacency for OS-side companies). UK PSC and OS person rows surface as stubs — "appears as a UK PSC officer with country=X, no further graph expansion in v1." The rendered dossier makes this asymmetry explicit; a reader shouldn't assume the absence of expansion means the absence of a network.
4. **Sanctions adjacency only resolves for OS-sourced companies.** Linked companies from ICIJ or UK PSC don't carry an OS link today, so they show `sanctions: unknown` rather than `sanctions: none`. Same caveat as above — absence-of-evidence ≠ evidence-of-absence.
5. **Degree cap truncates high-fan-out seeds.** Rare names tied to a known Mossack-Fonseca-style hub get the edge list truncated at `--max-degree`. The dossier displays a `degree_capped: true` flag so the reader knows the picture is partial.

## Follow-up specs (out of scope for this design)

- **Shell-cluster catalog** (the "Approach C" from /brainstorm) — network-pattern novelty instead of person-novelty. Distinct enough that it deserves its own brainstorm + spec.
- **Auto-drafted lead summaries via Claude API** — feed dossier + search hits, get a 2-paragraph human-readable draft. Useful productivity layer; not part of this design because we want the human in the loop on the "is this new" call.
- **Automated prune of stale dossier files** — current design intentionally leaves them. Revisit if the directory becomes unwieldy.
