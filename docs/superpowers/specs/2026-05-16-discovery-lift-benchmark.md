# Spec — Discovery-Lift Benchmark

**Date:** 2026-05-16
**Status:** Draft, will execute after one review pass
**Origin:** Response to external reviewer note ("you need a quantified discovery delta")

## Goal

Quantify what the goldenmatch + dossier pipeline surfaces that simpler baselines miss. The repo can demonstrate methodology, evaluation, and reproducibility (per prior_art_comparison.md). What it can't currently claim is "our system discovers things that the baselines don't." This benchmark closes that gap with concrete numbers.

## Non-goals

- Comparing against ICIJ DB's or Aleph's live UI (we can't programmatically replicate their search indexes).
- Real journalist user studies.
- Generative discovery (entity linking via LLM).

## What the comparison universe is

All distinct **person `normalized_name`** values appearing across `person_entities.parquet`. That's the entity space the rest of the project operates on; this benchmark just walks it more carefully.

## Baselines to compare

Four tiers, each strictly nested inside the next:

| Tier | Description | Production analogue |
|---|---|---|
| **B1 — Naive case-fold pairwise** | Names appearing in ≥2 distinct source tables after only `.lower().strip()`. No legal-suffix removal, no ASCII fold, no tokenization. | What you'd write in a weekend |
| **B2 — Goldenmatch-normalized** | Same as B1 but using `shellnet.normalize.normalize_company_name` (legal-suffix strip, ASCII fold, etc.). | `build_officer_overlap.py` output |
| **B3 — Rare-filter applied** | B2 narrowed to `max_per_source ≤ 2, n_tokens ≥ 3, n_sources ≥ 2`. Defends against common-first-name explosions. | Section-4 input to `build_join_novelty_report.py` |
| **B4 — Dossier pipeline** | B3 + ICIJ 2-hop graph walk + sanctions overlay (Phase 2). Adds *investigative signal* not just *match presence*. | `build_rare_officer_dossiers.py` |

The lift is the *delta between tiers* — how many additional anchors each layer surfaces, and what fraction of each layer's output is unique to it.

## Specific metrics

Per tier:
- **n_anchors**: count of distinct normalized names at that tier
- **n_anchors_with_signal**: count where the dossier pipeline (B4) gets ≥1 linked company OR ≥1 sanctions match (only meaningful for B4 itself)
- **incremental gain vs. previous tier**: `B_n.n_anchors - B_{n-1}.n_anchors` (in either direction — B3 is strictly smaller than B2, the "gain" is negative-by-design)

Per dossier seed (the B4 set, ~50 names):
- A boolean reachability flag per baseline: `reachable_b1`, `reachable_b2`, `reachable_b3`, `reachable_b4`. The ones with `reachable_b1=False` are the ones a naive baseline misses.

## Honest framing

The benchmark is mostly going to **vindicate normalization, not graph walk**, because:

- B1 → B2 lift is "how many names did legal-suffix-strip + ASCII-fold rescue from false negatives." Expect this to be the biggest single lift.
- B2 → B3 is a *reduction* by design (rare-filter throws away common-name noise). It's a precision move, not a recall move.
- B3 → B4 doesn't change the anchor count at all (B4 is the same anchors as B3, just enriched with graph context). The honest claim there is "B4 produces investigative-grade dossiers, not new anchors."

The report should say all of this plainly. Inflating the lift is worse than honestly reporting "the normalization layer is what does most of the work."

## Output

- `processed/discovery_lift.parquet` — small. One row per name in B1 ∪ B2 ∪ B3 ∪ B4 with four boolean columns + `dossier_has_signal`.
- `processed/discovery_lift_summary.json` — aggregate counts per tier.
- `docs/reports/discovery_lift.md` — rendered markdown report with the tier-by-tier table, the per-seed reachability breakdown, and honest framing.

## Compute split

Same Railway + GH-Actions pattern as the expose-candidates pipeline:

- Railway: `scripts/build_discovery_lift.py` — reads `person_entities.parquet` (818 MB), produces the small lift parquet + summary JSON.
- GH Actions runner: `scripts/render_discovery_lift.py` — reads the small artifacts, emits markdown.
- New `.github/workflows/build-discovery-lift.yml` — `workflow_dispatch`, direct-push to main.

## Limitations (in scope to document, not solve)

1. The benchmark measures `normalized_name` matching, not embedding-based or graph-traversal-based linking. Those would require building richer baselines.
2. "Reachability" here means "the name appears in 2+ sources at this tier." It does NOT mean "a journalist using a single-source UI would actually find this." That stronger claim needs separate work.
3. The B3 → B4 step has *no* numerical lift on anchor count; the lift is in dossier richness (linked companies, addresses, sanctions adjacency), which is qualitative. The renderer should make this explicit so a reader doesn't infer that the graph walk adds zero value.

## Out of scope (capture as follow-ups)

- DOB-confirmed pair lift (would require running matched_dob_scored against the same baselines — separate spec).
- Comparing against ICIJ Offshore Leaks DB's actual search index (would need their search API + rate limits).
- Embedding-based name matching as a 5th baseline (different research question).
