# Phases 8-10: making the expanded recluster actually expand

The Phase 7 recluster ran end-to-end against the new
`build_confidence_graph_expanded` job but the two new edge sources
contributed **zero edges**. The expanded report
(`docs/reports/confidence_graph_expanded.md`, run on 2026-05-20)
is structurally identical to the ICIJ-only baseline. This roadmap
fixes that.

Status of the two new inputs on Railway as of 2026-05-20 17:46 UTC:

| Source | Path on `/data` | Rows | Diagnosis |
|---|---|---:|---|
| Phase-3 twins | `processed/cross_jurisdiction_twins.parquet` | 0 | OO UK PSC parquets are absent (404) so the detector had nothing to join against. |
| Phase-6 SEC 13D/G | `processed/sec_13dg_edges.parquet` | 0 | SGML parser ran on 5000 filings but extracted `filer_cik=None` or `subject_cik=None` on every one — section headers in real 2025 Q4 filings don't match the parser's aliases. |
| OO UK PSC entities | `processed/oo_uk_psc_entities.parquet` | _missing_ | Phase 0 has not been re-run since the volume was last touched. |

Phases 8 and 9 unblock real edges. Phase 10 connects the SEC island
to the ICIJ corpus so SEC edges can influence the dossier-anchored
subgraph at all.

---

## Phase 8 — re-ingest OO UK PSC, then re-run twins + recluster

**Why:** Phase 3's twin detector defensive-path writes an empty
parquet when the OO entities table is missing. Until OO is
re-ingested, no Perry-style UK↔Malta bridges enter the graph and the
twin edge kind contributes nothing.

**Why now:** The OO bundle is the largest single edge enrichment in
the pipeline (13.9M relationships, CC0). Without it, ~half of the
new infrastructure is dead weight.

### Tasks
1. Dispatch `ingest-openownership-uk-psc.yml` on `main`. ~80 min on
   Railway (3.5 GB download, extract, project to 3 parquets).
2. Verify the three parquets land on the volume with non-zero size:
   `oo_uk_psc_entities.parquet`, `oo_uk_psc_persons.parquet`,
   `oo_uk_psc_relationships.parquet`.
3. Re-dispatch `detect-cross-jurisdiction-twins.yml`. ~10 min.
4. Confirm `cross_jurisdiction_twins.parquet` is non-empty and the
   PROBUTEC + I-CAP pairs surface as `strict_root` matches.
5. Re-dispatch `recluster-expanded-graph.yml`. ~30 min.

### Acceptance
- `cross_jurisdiction_twins.parquet` has ≥ 100 strict-root pairs.
- The PROBUTEC LTD ↔ PROBUTEC (MALTA) LTD pair appears in the parquet
  (search for `probutec` in `root`).
- The refreshed `confidence_graph_expanded.md` per-kind breakdown
  table shows non-zero `cross_jurisdictional_twin` and
  `psc_controller_of` rows.
- Cluster #47 (the Perry/Corvus seed-dense cluster) either grows or
  splits in a way that pulls in the Malta twin.

### Risk / fallback
- The OO download URL occasionally moves between annual snapshots.
  If 404, check `docs/ingestion_roadmap.md` for the current URL and
  bump it in `scripts/ingest_openownership_uk_psc.py`.
- Railway volume is single-region; if the build dies mid-extract the
  partial parquets stay on disk. Re-run is idempotent.

---

## Phase 9 — fix the SEC SGML header parser against real filings

**Why:** Phase 6's unit tests passed on a synthetic SGML envelope I
wrote, but every real 2025 Q4 filing produced
`extract_edge_from_sgml(...) → None`. The section-detector aliases
(`<SUBJECT-COMPANY>`, `SUBJECT COMPANY:`, etc.) don't match what
EDGAR actually emits.

**Why now:** SEC 13D/G is the highest-credibility edge type in the
priors table (0.92 × 0.97 = 0.89 effective) — signed under penalty
of perjury, court-admissible. Wasting that source is worse than the
twin-detector gap.

### Tasks
1. Download three representative live filings from the run's
   full-index:
   - `https://www.sec.gov/Archives/edgar/data/<cik>/<accession>.txt`
   - One SC 13D, one SC 13G, one /A amendment.
2. Diff their headers against the synthetic test fixture in
   `tests/test_ingest_sec_13dg_bulk.py`. Specifically check:
   - Section markers (`<SUBJECT-COMPANY>` vs `SUBJECT COMPANY:` vs
     something else)
   - `<CIK>` vs `<CENTRAL-INDEX-KEY>` (and which appears in which
     section)
   - Whether modern filings embed the data in XBRL/XML instead of
     the SGML preamble — in which case we need a fundamentally
     different parser.
3. Add at least two **real-corpus regression fixtures** to
   `tests/fixtures/sec_13dg/` — actual `.txt` files anonymised only
   if necessary. Sized to ~5 KB each.
4. Patch `parse_sgml_header` + `extract_edge_from_sgml` until both
   fixtures produce valid edges.
5. Re-run `ingest-sec-13dg-bulk.yml`. Expect ~3k-5k edges from
   2025 Q4.

### Acceptance
- New fixture-based tests pass and at least one is in the original
  failure mode pre-fix.
- `sec_13dg_edges.parquet` on Railway has ≥ 1000 rows.
- Spot-check 5 rows against EDGAR's web UI to confirm
  `(filer_name, subject_name)` are correctly assigned.

### Risk / fallback
- If modern 13D/G filings have abandoned SGML headers in favour of
  XML/JSON, this becomes a rewrite, not a patch. Budget 1 day before
  escalating. Worst-case fallback: parse the filings' `index.json`
  (always present, exposes `cik` and `companyName` per role) instead
  of the .txt envelope.
- SEC's UA rule was tightened mid-2025 — short `Name Email` works,
  anything URL-bearing or buzzword-heavy gets 403. Already fixed in
  the allowlist; don't re-bloat it.

---

## Phase 10 — bridge SEC ↔ ICIJ via name matching

**Why:** Even with Phase 9 producing thousands of `beneficial_owner_of`
edges, every node is in the `sec:` UID namespace. The dossier seeds
are `icij:...`. The 2-hop BFS that builds the subgraph never reaches
SEC nodes because there is no bridge between the two namespaces. The
new edges form a topologically disconnected island.

**Why not now:** This is the most labour-intensive of the three
phases and has the highest false-positive risk (Bloomberg / Corvus
attribution lesson from earlier in the project). Land Phases 8 + 9
first so we know we have something to bridge to.

### Approach options (pick one in brainstorming before implementing)

**Option A — Hand-curated cross-walk table.** Maintain
`configs/sec_icij_bridge.csv` mapping `sec_cik → icij_uid` for
the ~50 SEC issuers that intersect existing dossier clusters. Cheap,
auditable, zero false positives, but doesn't scale.

**Option B — Name-only matcher.** Run `normalize_company_name` on
SEC `filer_name` + `subject_name` and join against ICIJ
`name_normalized`. Cheap, scales to all SEC nodes, but generates
false positives (the "Corvus Capital LLC" problem from PR #61). Edge
credibility would need to be capped at ~0.6 to reflect this.

**Option C — Name + jurisdiction + officer-name matcher.** Same as B
but requires officer-name overlap before emitting the bridge. Much
lower false-positive rate, but only applies to SEC issuers that ICIJ
also has officer data for (~5-10% of the SEC corpus).

**Recommendation:** Start with **A** for the 5 known-overlap clusters
(Perry, Ayre, etc.), publish the methodology, then layer in **C** as
a v2 once we have labels to calibrate against.

### Tasks
1. Brainstorm A vs C with a couple of concrete worked examples on
   the Perry/Corvus cluster.
2. If A: write the CSV, add a loader to
   `build_confidence_graph.py` that emits one
   `same_company_as` edge per bridge row with `cred_kind=0.95`.
3. If C: new module `src/shellnet/sec_icij_bridge.py` plus tests.
4. Re-dispatch recluster. Verify SEC nodes now appear in dossier-
   anchored subgraphs.

### Acceptance
- For Approach A: the bridge CSV is reviewed against EDGAR + ICIJ by
  hand before merging. No automated additions.
- For Approach C: at least 80% precision on a 20-row labelled sample
  (manually constructed). PRs that hit a known false-positive get a
  defamation-hazard test added.
- The recluster's `confidence_graph_expanded.md` per-kind table
  shows non-zero `beneficial_owner_of` AND those edges appear in at
  least one dossier-anchored community.

### Risk / fallback
- **Highest defamation-hazard phase of the project.** Every bridge
  edge is an assertion "this SEC entity is the same as this ICIJ
  entity" — re-read the Marsh-on-SEC-vs-Marsh-on-ICIJ lesson before
  starting. Names are not identities.
- If Approach C's precision is below 80% on the sample, fall back to
  A and document why.

---

## Recommended order

Phase 8 → Phase 9 → Phase 10. Each unlocks meaningful capability that
the previous one set up:

- **8** turns the existing detector into something that emits real
  rows.
- **9** fixes the highest-credibility data source we're currently
  wasting.
- **10** is what makes the SEC corpus actually visible to the
  dossier-anchored discovery engine.

If only one phase ships: do **9**. Twin detection is recoverable from
Phase 8 alone if needed later; the SEC parser bug is the single
biggest unrealised value in the current code.

## Out of scope here

- Adding more national registries (already documented as out-of-
  scope in `data-source-utilization-roadmap.md`).
- Re-calibrating the operator-set credibility priors — needs a
  labelled review set the repo doesn't have yet.
- Replacing Louvain with a different community detector. The
  threshold-stability analysis in Phase 7 already shows the partition
  is anchored by structural ICIJ edges; swapping detectors is unlikely
  to change which clusters surface.
