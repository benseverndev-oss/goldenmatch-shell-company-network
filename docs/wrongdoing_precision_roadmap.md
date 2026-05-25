# Wrongdoing-lead precision roadmap

_Created 2026-05-25. Follow-up to `docs/wrongdoing_discovery_roadmap.md`, written
after the first full end-to-end run on Railway. That doc **built** the pipeline
(Phases 0–6, now deployed and run); this one closes the gap that first real queue
exposed: **the pipeline emits candidates, not stories.**_

## What the first live run showed

The chain ran clean: 2 sanctions-evasion + 28 disqualified-PSC leads → live
Companies House status check → **18 leads** after the active-gate → 18 dossiers,
0 cleared. But reading the output as journalism rather than as a green build:

- **The famous leads are the weak ones.** Both evasion leads (Nikita Mordashov →
  Marina Mordashova, Roman → Gleb Trotsenko) are *already-known* sanctioned actors
  whose UK vehicles are **dissolved** — the discovery roadmap's own anti-pattern.
  The live-status gate correctly removed them, leaving a queue that is **100%
  regulatory-breach leads**.
- **"Regulatory breach" overstates what is measured.** s.11 CDDA 1986 bans
  *directing / managing* a company; the signal actually matches **PSC (>25%
  ownership)**. A disqualified person *holding shares* is not necessarily in
  breach. An unknown fraction of the 18 are passive shareholdings, not breaches.
  **This is the single biggest precision gap.**
- **Identity is name + birth year-month only** — namesake-collision risk is real
  and currently unquantified.
- **Harm classification barely fires** — 1 of 18 (SIC-driven). Name-keywords are
  too narrow (`CARING HANDS EMPLOYMENT AGENCY` → `none`) and at least one bucket
  is wrong (`TAX RECLAIM PPI` → `crypto_finance` off a generic financial SIC).
- **Precision is unmeasured** — 0 leads verified; the Phase-6 loop has no labels.

Net: exactly **one** lead (a BBL-fraud-disqualified director linked to an *active
care-sector* company) is worth a reporter's afternoon. The rest are candidates
until the gaps below are closed.

## Reframe

The discovery roadmap's bar was *signalled + live + named + novel + bundled*. The
first run met those **formally** but not **defensibly**. Add a sixth bar:

> **Substantiated** — the signal is the *act it claims* (an acting directorship,
> not a shareholding), the identity is disambiguated beyond a common-name match,
> and the claim survives the legal distinction it rests on.

Precision over recall: a 5-lead queue that is 80% real beats a 30-lead queue that
is 10% real. Every phase below trades recall for defensibility.

## Phases (ordered by payoff per unit effort)

### P1 — Resolve PSC vs. acting director _(highest leverage; the precision-defining join)_
- **Problem:** the breach signal is `disqualified ∩ PSC`, but s.11 is about
  directing/managing. PSC ≠ director.
- **Approach:** cross each disqualified-PSC lead against Companies House **officer
  appointments** and grade it:
  - disqualified + an **active director appointment** dated within/after the
    disqualification → **strong candidate breach**;
  - disqualified + **PSC only** (no active appointment) → passive shareholder,
    separate and down-weight;
  - appointment terminated before the disqualification → drop.
- **Data dependency:** CH officer-appointments are **not ingested today**. Two
  routes: (a) per-lead Firecrawl scrape of the officer's CH appointments page
  (cheap, reuses the Phase-3 pattern — start here); (b) a bulk CH officers ingest
  (for scale). Emit a `breach_grade` field the ranker gates/weights on.
- **Done when:** every breach lead is labelled acting-director vs passive-PSC, and
  the queue leads with acting-director breaches only.

### P2 — Identity disambiguation + false-positive measurement
- **Problem:** matching on name + DOB year-month admits namesakes.
- **Approach:** add DOB-day where either side carries it, address overlap (both
  the disqualified register and PSC records hold addresses), and a per-lead
  `identity_confidence`. Hand-verify a sample to estimate the namesake
  false-positive rate.
- **Done when:** each lead has `identity_confidence`; low-confidence is
  dropped/flagged; the FP rate is a known number, not a worry.

### P3 — Live currency confirmation
- **Problem:** "still acting" rests on a null `end_date` in lagging BODS.
- **Approach:** extend the existing Firecrawl enrichment from the CH overview tab
  to the **PSC tab + officers tab**; confirm the named person is *currently*
  listed as of the fetch date.
- **Done when:** each lead carries "live-confirmed PSC/officer as of `<date>`",
  not a snapshot inference.

### P4 — Harm taxonomy tuning
- **Problem:** 1/18 classified; narrow name-keywords; an over-broad
  `crypto_finance` financial-SIC bucket.
- **Approach:** broaden SIC→harm coverage (care-adjacent agencies, SIC 7810/8810,
  etc.), tighten `crypto_finance` so PPI/consumer-finance firms don't fall in it,
  and mine the **disqualification conduct text** (already in each dossier — e.g.
  "Bounce Back Loan", "Covid support", "care home") as a harm/severity signal in
  its own right, independent of SIC.
- **Done when:** harm reflects the conduct, not just a coarse SIC prefix, and the
  top queue has no obvious mislabels.

### P5 — Retire / repoint the low-value evasion signal
- **Problem:** evasion-on-dissolved is known-actor rediscovery (the discovery
  roadmap's explicit anti-pattern), yet it carries the highest signal weight.
- **Approach:** filter the evasion probe to **currently-active** targets *before*
  scoring (the discovery roadmap intended this; the live run showed it isn't
  enforced pre-rank), and down-weight already-published actors. Treat an evasion
  hit as a tip into live structure, not a standalone top lead.
- **Done when:** evasion no longer floats dissolved-company known-actor pairs to
  the top of the queue.

### P6 — Precision measurement + the systemic story
- **Problem:** 0 leads verified, and the strongest *public-interest* framing is
  aggregate, not per-lead.
- **Approach:** build a small labelled validation set (hand-adjudicate a sample of
  acting-director breaches), populate the Phase-6 outcomes loop, measure top-N
  precision per signal, retune Phase-2 weights from it. Then produce the
  **defensible aggregate** — "N disqualified directors are *currently acting as
  directors* of UK companies" — a systemic enforcement-gap finding that only holds
  once P1 separates directors from shareholders.
- **Done when:** top-N precision is a tracked number and the aggregate count is
  director-grade, not PSC-grade.

## Cross-cutting

- **Compute on Railway.** Each new probe needs a `_ALLOWED_SCRIPTS` entry +
  redeploy.
- **The PSC≠director distinction is an ethics requirement, not just precision.**
  Implying a passive shareholder is in breach of a directorship ban is a
  defamation risk; P1 gates that, so it ships first.
- **Precision over recall.** Prefer dropping a lead to shipping a namesake or a
  shareholder-as-director. The metric is top-N precision, tracked run over run.
