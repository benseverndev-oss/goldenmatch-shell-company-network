# Design — Exposé candidates pipeline

**Date:** 2026-05-16
**Status:** Approved by user (chunk-by-chunk during /brainstorm session)
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

## Data flow

### Seed selection (Railway, build_rare_officer_dossiers.py)

```
officer_overlap.parquet
  → filter is already in the parquet (n_sources >= 2, max_per_source <= 2, n_tokens >= 3)
  → sort: n_sources DESC, total_entities DESC
  → head: --top-n (default 50)
```

50 not 200 because of (a) firecrawl per-run budget on the Actions side and (b) human triage capacity downstream.

### 2-hop walk per seed name N

```
For each name N:
  matched_persons := person_entities.filter(normalized_name == N)
  For each person P in matched_persons:
    linked_companies := walk(P → icij_edges if P.source == "icij"
                              OR uk_psc owner_of relation if P.source == "uk_psc"
                              OR opensanctions directorOf relation if P.source == "opensanctions")
    For each company C in linked_companies:
      attrs := {
        jurisdiction:    C.jurisdiction,
        address_norm:    address_entities.lookup(C.address_id).normalized_address,
        co_officers:     person_entities.filter(linked_to == C).normalized_name (list),
        sanction_lists:  sanctions_overlay.lookup(C.os_id).datasets,
        n_datasets:      sanctions_overlay.lookup(C.os_id).n_datasets,
      }
      emit row(N, P.source, P.entity_uid, P.name, P.country,
               C.entity_uid, C.name, **attrs)
```

Output: `processed/rare_officer_dossiers.parquet`. Denormalized (one row per N × P × C × attribute-snapshot) so the renderer is pure SELECT.

### Web search (Actions, search_dossier_freshness.py)

```
For each distinct rare_name N from the parquet:
  hits_general   := firecrawl_search(f'"{N}"', limit=5)
  hits_offshore  := firecrawl_search(f'"{N}" (shell OR offshore OR director OR PSC)', limit=5)
  hits_localized := firecrawl_search(f'"{N}" {top_jurisdiction_of_N}', limit=3)
  store: { N: { general: [...], offshore: [...], localized: [...] } }
```

Budget: 50 names × 3 queries ≈ 150 firecrawl calls. Capped via `--max-searches`. Per-name failure (rate limit, 500, etc.) marks that name `search_skipped`; does not poison the batch.

### Novelty score (in render_dossiers.py)

```
novelty_score(row) =
    +0.40 * (1 if prior_coverage_n == 0 else 0)            # existing scorer says zero coverage
    +0.20 * (1 if not prior_coverage_mainstream else 0)    # no mainstream hit
    +0.20 * (1 - min(len(hits_offshore) / 5, 1.0))         # few offshore-query hits = newer
    +0.10 * (1 - min(len(hits_general) / 10, 1.0))         # less generally famous
    +0.05 * min(n_linked_companies / 5, 1.0)               # shell-density bonus
    +0.05 * min(n_jurisdictions / 3, 1.0)                  # multi-juris bonus
```

Score ∈ [0, 1]. ≥ 0.80 = "investigate this one." Weights operator-tunable via CLI flags. The renderer sorts the index by score DESC. Score is a triage signal, NOT a verdict — the explicit comment in the rendered file makes that clear.

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
| `max_searches` | int | `150` | Hard firecrawl cap; halts further searches on hit |

Reuses the direct-push-to-main pattern from `render-novelty-report.yml` (enterprise policy blocks PR creation). Per-run idempotency:

- Dossier `.md` files for names that fall out of the top-N on a later run **stay in git**. No auto-prune. Prevents surprise deletions when seed parameters change.
- The index is fully regenerated each run; stale dossier files become unlinked from the index but remain at their URL.

## Error handling

| Failure | Handling |
|---|---|
| `officer_overlap.parquet` missing on Railway | Hard fail with "run `build_officer_overlap` first" |
| firecrawl rate-limited mid-batch | Log, mark that name `search_skipped`, continue; index row shows "needs manual search" |
| firecrawl returns 5xx on a single name | Log, continue (don't poison the batch) |
| `max_searches` exhausted mid-run | Halt searches, render what we have, surface skip-count in the workflow summary |
| Renderer encounters a name with zero matched persons (data-skew edge case) | Drop with warning; row was likely a stale rare-name |
| Allowlist entry missing on Railway (new code not deployed) | Workflow's poll step times out; trivial to debug from the run log |

## Testing

- **Unit test, `tests/test_novelty_ranking.py`**: synthetic input rows → expected score band. Locks the weights so a thoughtless tweak doesn't silently reshuffle the index.
- **No CI for markdown templates** — they're too fragile to lock in, and the cost of breakage is one ugly run we manually regenerate.
- **Local smoke test** before first Railway/Actions run: invoke `build_rare_officer_dossiers.py` against the locally-cached `data/processed/officer_overlap.parquet` plus a stub stand-in for the other parquets if needed; eyeball one rendered dossier file.

## Quirks worth flagging in the rendered output

1. **Offshore-query hit count is coarse.** A famous person whose Wikipedia page mentions "offshore" once still gets 5 hits. The score is a triage tool; you still scroll the dossier and make the call.
2. **Same-name collisions remain possible.** A rare 3-token name in 2-3 sources can still be two different people sharing a name. The dossier surfaces enough context (jurisdiction, address overlap, co-officers) to spot this; the renderer doesn't try to auto-resolve.
3. **`prior_coverage` is based on a corpus snapshot.** New mainstream coverage that landed after the corpus was built won't show up as "covered." The web-search step partially compensates.

## Follow-up specs (out of scope for this design)

- **Shell-cluster catalog** (the "Approach C" from /brainstorm) — network-pattern novelty instead of person-novelty. Distinct enough that it deserves its own brainstorm + spec.
- **Auto-drafted lead summaries via Claude API** — feed dossier + search hits, get a 2-paragraph human-readable draft. Useful productivity layer; not part of this design because we want the human in the loop on the "is this new" call.
- **Automated prune of stale dossier files** — current design intentionally leaves them. Revisit if the directory becomes unwieldy.
