# Phases 11-13: making SEC bridges actually reach the dossier subgraph

Phase 10 produced 23 high-quality SEC ↔ ICIJ bridges (Royal Bank of
Canada, Transocean International, CVI Investments, etc.) but **none
entered the dossier-anchored 2-hop subgraph**: the bridged ICIJ
entities don't sit within 2 hops of the 363 rare-officer dossier
seeds. The recluster's `beneficial_owner_of` edge count is still 0.

Three options to fix the reach problem, ordered by expected lift per
unit effort.

| Status today (2026-05-20 19:something UTC) | Value |
|---|---:|
| SEC 13D/G edges on disk | 5,000 |
| SEC ↔ ICIJ bridges on disk | 23 |
| Bridged entities reachable from a dossier seed in ≤2 hops | 0 |
| `beneficial_owner_of` edges in subgraph | 0 |

---

## Phase 11 — broaden seed set to high-anomaly Phase-7 communities

**Why:** The current seed set is the 363 entities from
`rare_officer_dossiers.parquet`. That set is investigatively-aligned
but narrow — it skews toward people-side rare-officer anchors, not
company-side anomaly clusters. The 23 bridge candidates are large
public-fund SEC filers (RBC, Apollo, Victory Capital) that DO appear
in ICIJ but aren't 2-hop-adjacent to a rare-officer anchor.

**Hypothesis:** The recluster from the last run produced 79 non-
singleton communities at threshold ≥ 0.7. Many of them are anchored
by addresses or intermediaries (not rare officers). Adding the top
10 anomaly-ranked community-member UIDs to the seed set will pull
their 2-hop neighbourhoods in, and several of those likely intersect
the bridge candidates.

### Tasks
1. Add `--extra-seeds` flag to `build_confidence_graph` accepting a
   parquet of `uid` rows.
2. Add `scripts/select_anomaly_seeds.py` that reads
   `confidence_community_anomalies.parquet` and emits the union of
   member UIDs from the top-N communities by anomaly score (default
   N=10).
3. Wire into the expanded-recluster allowlist; pass the new seed
   parquet alongside the dossier set.
4. Re-run.

### Acceptance
- The subgraph node count grows (currently 7,888 capped at 8,000).
  Likely need to also raise `--max-nodes` to 16,000.
- ≥ 1 `beneficial_owner_of` edge enters the subgraph.
- At least one of the bridged ICIJ entities (Royal Bank of Canada,
  Transocean, CVI Investments) appears in the subgraph.

### Risk
- Anomaly-ranked seeds may flood the subgraph with low-credibility
  edges and dilute the existing dossier-anchored signal. Mitigate by
  tagging the new seeds in the output communities table so the
  reviewer can filter back to "communities anchored on at least one
  rare-officer seed".

---

## Phase 12 — bump BFS depth from 2 to 3 hops

**Why:** A 2-hop walk catches "seed → officer/address → entity → ?".
The bridge edges sit one hop further out: "dossier seed → ICIJ
entity X → bridged ICIJ entity Y (= SEC filer) → SEC issuer Z". The
extra hop is exactly where SEC filers materially enrich discovery.

**Why not first:** Each extra hop roughly squares the subgraph size.
Going from 7,888 → ~50k+ nodes will balloon Louvain runtime and the
threshold-stability analysis. Has to be paired with `--max-nodes`
tightening and probably a higher per-hop pruning threshold (drop low-
degree neighbours past hop 2).

### Tasks
1. Plumb `--hops 3` through the allowlist's
   `build_confidence_graph_expanded` entry.
2. Add per-hop pruning: when adding hop-3 neighbours, drop any node
   whose degree-in-the-frontier is < 2 (i.e. only keep nodes that
   bridge ≥ 2 hop-2 entities). Documented in the script.
3. Measure runtime + memory. If Louvain takes > 5 min, drop back to
   hops=2 + Phase 11 instead.

### Acceptance
- Subgraph node count grows 3-5x.
- ≥ 1 `beneficial_owner_of` edge enters the subgraph.
- Recluster total runtime ≤ 15 min (the existing 30-min workflow
  timeout has headroom).

### Risk
- The threshold-stability analysis assumes a small bounded subgraph.
  3-hop expansion produces a much larger subgraph where the loose
  threshold (0.5) communities become enormous and the strict
  threshold (0.9) communities largely fragment. The Jaccard stability
  metric may degrade in a way that's hard to interpret. Document
  this in the report's methodology section.

---

## Phase 13 — ingest multiple SEC quarters

**Why:** 5,000 edges from 2025 Q4 alone is the head of the
distribution: large recurring filers (Apollo, Vanguard, RBC). The
long tail of one-off filers (the obscure offshore vehicles we care
about for shell-company discovery) is spread across many quarters.
Ingesting 4 quarters = ~20k edges = ~4x more bridge candidates.

**Why last:** Even with 5,000 edges and 23 bridges, the recluster
showed zero subgraph hits. More edges won't help if Phases 11 and
12 don't first fix the reach problem. Conversely, once the reach is
fixed (Phase 11 or 12), more quarters is a cheap way to amplify.

### Tasks
1. Convert the `ingest_sec_13dg_bulk` allowlist entry from one
   (year, quarter) pair to a list. The script already accepts
   year/quarter as args; wrap the call site to iterate.
2. Switch the output from `sec_13dg_edges.parquet` (overwrite) to
   `sec_13dg_edges_<year>_q<quarter>.parquet` + a concat step that
   produces the union parquet.
3. Re-run for 2025 Q1-Q4. Total ingestion time: 4 × ~25 min ≈ 100
   min (within Railway timeout if chunked).

### Acceptance
- `sec_13dg_edges.parquet` has ≥ 15,000 edges.
- `sec_icij_bridges.parquet` grows to ≥ 60 bridges (proportional).
- Combined with Phase 11/12, at least 3 distinct `sec:CIK` nodes
  enter the subgraph and contribute `beneficial_owner_of` edges.

### Risk
- SEC's full-index format may differ across quarters (the 2025
  rename from "SC 13D" → "SCHEDULE 13D" is a fresh example). The
  parser's safety-net prefix list already accepts both, but new
  drift could need additional patches.
- Filing-side rate limiter still caps throughput at ~9 req/s. 4x
  more filings = 4x more elapsed time on the SEC fetch loop.

---

## Recommended order

**Phase 11 → 13 → 12.** Phase 11 is the cheapest experiment with the
highest expected lift (broaden the seed set, see if any of the 23
existing bridges land within reach). Phase 13 (more SEC quarters)
amplifies once Phase 11 confirms the mechanism. Phase 12 (3-hop
BFS) is the heaviest; only worth doing if Phases 11 + 13 still leave
the SEC corpus underused.

If only one phase ships: **Phase 11.** The bridge mechanism is proven
sound — the gap is purely "which ICIJ entities seed the BFS." That's
a 1-2 hour change.

## Out of scope here

- Fuzzy name matching for the bridge. The "Apex Management Ltd"
  cohort already includes several distinct entities sharing that
  name across BVI / Cayman / Malta; loosening the match invites the
  Corvus / Marsh defamation hazard documented in PR #61. Phase 14+
  could explore name + jurisdiction + officer-overlap triangulation,
  but it's not in scope here.
- Cross-source same-as edges (OpenSanctions ↔ ICIJ, GLEIF ↔ ICIJ).
  Those are separate bridges; the SEC bridge is the priority because
  it's the only registry source today contributing zero subgraph
  edges. PSC bridges (Phase 3 twins) already worked.
