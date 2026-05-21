# Phase 17: disambiguate SEC ↔ ICIJ bridges beyond name similarity

The Phase 15a experiment proved the GoldenMatch SDK is correctly
wired (Phase 10's bridge ran end-to-end with the fuzzy matcher) but
also exposed a limitation that's worth a dedicated roadmap entry.

## What happened

Phase 15a enabled `--use-goldenmatch` on `bridge_sec_icij_by_name`
and re-ran the chain. The bridges parquet grew from **30** (exact
normalised-name match) to ~1,500+ (fuzzy, threshold 0.92). The
recluster's `beneficial_owner_of` count grew **17×** (453 → 7,757).

But the highest-probability matches included exactly the
false-positive cases the Phase 10 spec warned about:

| Bridge (both sides) | Probability | Verdict |
|---|---:|---|
| ROYAL BANK OF CANADA ↔ Royal Bank of Canada | 1.00 | ❌ public bank, name-coincidence with ICIJ |
| DELTA AIR LINES, INC. ↔ Delta Air Lines, Inc. | 1.00 | ❌ public airline |
| VICTORY CAPITAL MANAGEMENT INC ↔ VICTORY CAPITAL MANAGEMENT, INC. | 1.00 | ❌ public asset manager |
| Equitable Holdings, Inc. ↔ EQUITABLE HOLDINGS INC. | 1.00 | ❌ public insurance holding |
| EE Holdings Ltd ↔ EE HOLDINGS LTD | 1.00 | ✅ plausible offshore vehicle |
| Skycrest Holdings, LLC ↔ Skycrest Holdings, LLC | 1.00 | ✅ plausible |

GoldenMatch's job is to detect name similarity, and it does that
correctly. For exact-or-near-exact pairs it returns 1.0 regardless
of whether the names belong to the same entity. **The
disambiguation signal we actually need is not in the name.**

We rolled the allowlist back to the exact-match path (Phase 10
default) — 30 cleaner bridges, 17 mixed SEC+ICIJ communities at
threshold 0.5, no Delta/RBC noise. The fuzzy path stays available
behind `--use-goldenmatch` for future experiments.

## What Phase 17 needs to add

Three signals, in order of expected lift:

### 17a — drop large-cap US-listed issuers via SEC submissions index

The SEC EDGAR submissions API exposes per-CIK metadata including
`sicDescription`, `category` (e.g. "Large Accelerated Filer"),
`stateOfIncorporation`, and ticker symbols. Any SEC filer that's
classified as a Large Accelerated Filer OR has a US ticker OR has
SIC code in the "depository institutions" / "air transportation" /
"insurance carriers" range is almost certainly NOT the offshore-
shell ICIJ entity that happens to share its name.

**Action:** add `scripts/enrich_sec_filer_metadata.py` that pulls
`https://data.sec.gov/submissions/CIK{cik10}.json` for each filer in
the bridges parquet and joins back. New columns:
`sic`, `sic_description`, `category`, `state_of_incorporation`,
`ticker`. Then add a `--drop-large-cap-issuers` flag to the bridge
script.

**Cost:** one HTTP call per unique SEC CIK (~3k unique filers in the
4-quarter ingest at 9 req/s = ~6 min). Already rate-limit-paced.

### 17b — require officer-name overlap on the ICIJ side

Phase 10's roadmap called this out as the highest-precision option:
**only emit a bridge when the SEC filer's officers match at least
one ICIJ officer record on the ICIJ entity's side.**

The SEC 13D/G filing itself names the beneficial owner (a person or
corporate entity). If we extract that and check whether the same
person appears as an officer of the ICIJ entity, we have positive
evidence the two are linked beyond name coincidence.

**Action:** extend `scripts/ingest_sec_13dg_bulk.py` to also pull
the reporting-person name from the SGML header (it's there in the
`<REPORTING-OWNER>` section we already parse), then add an
officer-overlap join in the bridge script.

**Cost:** one extra projection in the SEC parquet (no new HTTP);
one extra join in the bridge script. Low effort.

### 17c — labelled ground-truth + cross-encoder fine-tuning

The honest long-term path: hand-label 100 bridge candidates as
real/false-positive (the 30 exact-match bridges + a sample of the
GoldenMatch-only candidates that 17a and 17b don't catch), then
fine-tune GoldenMatch's cross-encoder on them.

**Action:** create `data/labels/sec_icij_bridge_labels.csv` with
columns `sec_cik, icij_uid, label, rationale`. Document the
rationale per row (e.g. "Delta Air Lines is NYSE-listed, not in
ICIJ"). Use the labels to validate Phase 17a + 17b filters.

**Cost:** 2-3 hours of manual review. Worth doing.

## Recommended order

**17a → 17b → 17c.**

- **17a** is the cheapest filter and catches the loudest false
  positives (Delta, RBC, Equitable — all Large Accelerated Filers
  with US tickers).
- **17b** is the highest-precision filter but only fires when ICIJ
  has officer data on the matched entity (~10-20% of cases per Phase
  10's notes).
- **17c** lets us measure how much each filter is actually buying us
  and tunes the cross-encoder for the long tail.

## What stays as-is

- The Phase 15a `--use-goldenmatch` flag remains available, just
  defaulted off. Once Phase 17a + 17b filters land, we can re-enable
  the fuzzy matcher behind the filters and get the calibrated
  probabilities AND the disambiguation gate.
- The 30 exact-match bridges keep running in the current allowlist
  — they produced 453 `beneficial_owner_of` edges in the subgraph
  and 17 dossier-anchored mixed communities, which is real signal.

## Acceptance

After 17a + 17b ship:

| Metric | Threshold |
|---|---:|
| Bridges parquet row count (with --use-goldenmatch + 17a filter) | between 50 and 500 (vs current 1,500+ unfiltered or 30 exact-only) |
| Recluster `beneficial_owner_of` edges | ≥ 1,000 (vs 453 with exact-only, 7,757 with unfiltered GoldenMatch) |
| False positives in the top 20 by prob (Delta, RBC, Equitable etc.) | 0 |
| Mixed-namespace communities at threshold 0.5 | ≥ 25 (vs 17 exact-only) |

## Out of scope

- **Re-doing Phase 3 twins through GoldenMatch (Phase 15b).** The
  twin detector already has a working OOM-aware pipeline producing
  150k+ candidate twins. Routing through the SDK is the v2 quality
  story but doesn't change the discovery footprint today.
- **Replacing networkx Louvain with goldenmatch.core.graph_er
  (Phase 15c).** Even larger behaviour change; should follow Phase
  17 once the bridge edges are clean.
