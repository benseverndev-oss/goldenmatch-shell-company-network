# Failed investigations — what didn't work and why

_Last updated: 2026-05-17._

This file exists because **methodological credibility requires reporting failures, not just successes.** Investigative tools that only publish their wins encourage over-trust in their outputs; we'd rather be the kind of system a journalist-skeptic believes by default because we've been honest about the cases where the pipeline produces noise, empty results, or contradictory evidence.

Five real failure cases from this corpus, each documented with: what we expected, what happened, why, and what (if anything) would fix it.

---

## 1. The reconcile fan-outs returned empty matches

**What we tried.** Built per-source enrichment via Max Harlow's `reconcile` CLI: pointing Russian-sanctioned-entity names at the Russian Federal Tax Service registry (`reconcile_ru_companies`) and US-sanctioned-entity names at SEC EDGAR (`reconcile_sec_filings`). Expected output: enriched CSVs with company numbers, filings, registered addresses.

**What happened.** Both reconcilers ran end-to-end (after patching a separate `Process.stdin.unref()` crash in `reconcile@latest`) and returned **zero matches** across 50-name shortlists each.

**Why it failed.** The shortlists were the wrong inputs, not the tooling:

- **Russian FTS** is a registry of *operating Russian companies*. Our shortlist was 50 names drawn from the sanctions overlay's Ukrainian-language NSDC entries — Ukrainian sanctions write about Russian entities in Ukrainian. The Cyrillic name strings on the shortlist don't match the Russian-language strings the FTS indexes. Even where the underlying company exists in FTS, the cross-language transliteration defeats name-match.
- **SEC EDGAR** is a registry of *US public filers*. Our shortlist was 50 sanctioned individuals + orgs. Sanctioned entities are rarely SEC-filing public companies; the structural overlap is near-zero.

**Honest read.** The reconcile pipeline is operational, but its value is per-investigation enrichment on *correctly-curated* shortlists — for example, IMOs from a specific maritime sanctions case, or US filer names from a 13D ownership-disclosure investigation. Not a bulk-enrichment tool.

**What would fix it.** Two options:
1. **Better shortlist curation.** If the journalist starts from a specific Russian operating company name, FTS reconciliation works. The bottleneck is having a sourced shortlist, not the wiring.
2. **Different sources entirely.** The cross-language transliteration problem is real for the Russian case; an embedding-based name matcher (multilingual MiniLM) would handle it where exact-match fails. Captured in `methodology.md §11`.

The wiring stays on `main` for when a real investigative shortlist exists; we don't claim it produced useful output on the shortlists we tried.

---

## 2. UK MP financial-interests scraper produced zero bytes

**What we tried.** Wrapped `maxharlow/scrape-members-financial-interests` to surface the UK MP Register of Members' Financial Interests as a PEP (politically-exposed-person) overlay. Expected output: CSV of MP names + declared financial relationships.

**What happened.** The scraper ran for 7 seconds and produced a **0-byte CSV**. Log showed it iterated URLs `http://www.publications.parliament.uk/pa/cm/cmregmem/{YYMMDD}/contents.htm` from 2025-11-04 through today and got nothing back from every date.

**Why it failed.** UK Parliament changed the Register's URL scheme after the 2024 General Election cut a new Parliament. The upstream scraper hardcodes the old scheme; the post-2024 publications use a different path (and a different publication cadence).

**Honest read.** This is an upstream-scraper rot problem we can't fix from inside our repo without rewriting the scraper. Documented in `memory/` as a known issue and excluded from the §4 methodology claims; the MP-interests layer doesn't contribute to any benchmark on `main`.

**What would fix it.** Either rewrite the scraper against the new URL scheme, or switch to Parliament's open-data API (`developer.parliament.uk`) which exposes the Register as structured data. Not in scope for v1 — captured as a deferred follow-up.

---

## 3. Disqualified-directors cross-reference is dominated by name collisions

**What we tried.** Cross-referenced the 222-row UK Insolvency Service struck-off-director register against the full `person_entities` table. Expected output: a small ranked list of UK-disqualified directors who *also* appear in ICIJ leaks, OpenSanctions, or GLEIF — the "struck-off-and-still-active" pattern.

**What happened.** 665 person-side hits. Inspection showed the matches are dominated by name-collision noise: the 222 disqualified names include high-frequency UK names (Singh, Smith, Khan, Jones), each matching dozens of unrelated entries in `person_entities`. The "interesting" subset — disqualified directors who *also* appear as ICIJ leak officers — was only **2 rows** out of 665. The other 663 are noise.

**Why it failed.** Three compounding factors:

1. **Name-only matching has no precision floor.** Without a DOB-confirmation step, "John Smith" in the disqualified register matches every John Smith in UK PSC.
2. **The disqualified register only covers the *currently-in-force* orders** (222 rows), not the historical strikeoffs. So the population is small AND skewed toward recent, lower-profile cases.
3. **The high-value joins are with ICIJ, but ICIJ persons don't carry DOB** in this corpus, so DOB-filtering can't be applied to the cross-source side.

**Honest read.** The 2 ICIJ hits (Santokh Singh, Sajid Bashir) made it into the join-novelty report's section 5; the other 663 names were filtered out at render time with an explicit "UK PSC matches dominated by name collisions" note in the report header. We accepted the precision cost and surfaced the cleaner signal.

**What would fix it.** Block on UK Companies House date-of-birth for the disqualified register (it's available on the source pages, just not in the scraper output). That single field would cut the noise from 663 to a single-digit count.

---

## 4. Sanctions-adjacency column was zero across all 50 dossiers

**What we tried.** In Phase 2 of the dossier pipeline, surface a "sanctions adjacency" indicator per lead: how many of the linked companies in the 2-hop graph walk also appear on the sanctions overlay? Expected: a small but non-zero count for some dossiers.

**What happened.** **Zero hits across all 50 top-N dossiers.** Both the OS-source-id-prefix-strip join (Phase 1) and the name-fallback join (Phase 2, using normalized-name match against the overlay's caption + aliases) returned nothing.

**Why it failed.** Structural, not implementation: the dossier pipeline's 2-hop graph walk runs against `icij_edges` — ICIJ shell companies linked to ICIJ officers. The sanctions overlay covers OpenSanctions persons + companies. ICIJ shells and OS sanctioned entities are largely disjoint sets — the shells were registered as ownership vehicles, not as sanctioned-list entries. Even the Phase-2 name fallback couldn't bridge the gap because the ICIJ shell names don't match OS captions.

**Honest read.** The column was hidden from the rendered index with an explicit "Phase 2 wired but didn't fire" note. The wiring stays in place because future runs (broader top-N, different seeds, additional source ingest) may produce hits, but on the current corpus + top-50 the signal is genuinely zero.

**What would fix it.** Materialise an explicit ICIJ↔OS company-side match — we have OS sanctions data + ICIJ companies but they were never reconciled at the company level (only at the person level via `list_match_os_sanctions_vs_icij`). A `list_match_os_vs_icij_companies` run would bridge them.

---

## 5. The adversarial benchmark surfaced a 100% failure mode

**What we tried.** Adversarial-robustness benchmark (`build_adversarial_benchmark`). For each B3 anchor, generate four synthetic perturbations modelling adversary moves and measure whether the pipeline still recovers the original. Expected: graceful degradation, maybe 70-90% recovery per perturbation.

**What happened.** **B2 normalize fails 100% against honorific insertion.** "Mr Francisco Lopes Filho" and "Francisco Lopes Filho" map to different keys in `officer_overlap.parquet` because `normalize_company_name` strips legal suffixes but **does not strip honorifics**. An adversary prepending "Mr" / "Dr" / "Sheikh" completely defeats the cross-source name match at the source-table level.

**Why it failed.** The normalize function was designed against company-name suffixes ("Ltd" / "Limited" / "LLC") and never extended to person-name honorifics. Honorific-stripping was added to the *render* step in the dossier pipeline (so the displayed name reads cleanly), but the underlying keys in the dedup'd person table still carry the prefix. The bug is that the de-duplication source-of-truth doesn't see "Mr Foo" and "Foo" as the same key.

**Honest read.** This is the most actionable failure on the list and it's captured in the methodology paper as §11.1 ("quick fix surfaced by §5"). The fix is one function edit: extend `normalize_company_name` to strip an opening honorific run the same way it strips a trailing legal-suffix run.

**What would fix it.** As noted — one edit to `shellnet.normalize.normalize_company_name`. Captured as a v2 follow-up because changing the canonical normaliser invalidates a lot of cached parquets and would require a re-ingest. Doing it cleanly means also adding unit tests + regenerating downstream artifacts.

---

## What these failures have in common

Three patterns recur:

1. **Source-language mismatch.** Russian FTS ↔ Ukrainian-NSDC shortlist; UK PSC ↔ post-General-Election URL scheme; OS captions ↔ ICIJ shell names. The pipeline assumes ASCII-folded normalised strings will match across sources; in practice transliteration, regime change, and registry-specific naming conventions break that assumption.
2. **Population mismatch.** Sanctioned entities ↔ SEC filers; UK-disqualified directors ↔ ICIJ offshore officers. The intersection of these populations is small *by construction*, not by data quality. The pipeline can't manufacture signal where the underlying populations are disjoint.
3. **Honorific / suffix asymmetry.** Source-table normalisation handles legal suffixes but not honorifics; render-time stripping handles honorifics but doesn't fix the underlying key. The split is a real bug, captured.

## What this file does NOT cover

Successful runs that produced clean output are in `discovery_lift.md`, `baseline_comparison.md`, `calibration_benchmark.md`, `confidence_graph.md`, and `adversarial_benchmark.md`. The exposé-candidates index is at `exposes_candidates.md` with 50 per-lead dossiers. This file is the inverse — what *didn't* work and why.

If a reader finds investigative claims in any of the **other** reports that aren't backed by structurally-defensible signal, that's worth flagging as a fix. We'd rather catch a false positive here than be quoted for one downstream.
