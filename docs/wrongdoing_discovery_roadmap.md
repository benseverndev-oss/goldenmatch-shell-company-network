# Wrongdoing-discovery roadmap

_Created 2026-05-25. The companion to `docs/ingestion_roadmap.md`: that doc is
about which **corpora** to add; this one is about how to turn the corpus into a
repeatable stream of **named, currently-live, wrongdoing-signalled leads** that a
journalist would actually chase._

## Why this exists (the lesson that motivated it)

The first real-corpus run (see `reports/investigations/aeza_ofac_uk_psc_finding.md`)
matched UK PSC declarations against OpenSanctions and surfaced recognizable names
— Zyuzin, Volozh, Trotsenko, Mordashov, Marchenko, plus the Aeza cyber-host. But:

- Matching **"is this person sanctioned / a PEP?"** mostly *rediscovers known bad
  actors*. The famous connections are already published.
- Every resolved company turned out **dissolved or in liquidation** — interesting
  structure, dead story.

So the bar isn't "famous name in a graph." It's **a wrongdoing act, at a live
target, on a join nobody has done, resolvable to a name, with an evidence bundle.**

## End state (definition of done)

A scheduled Railway job that, each run, emits a **short ranked queue** to
`docs/reports/wrongdoing_leads.md` where every row is:

1. **Signalled** — carries a concrete wrongdoing signal, not just a list status.
2. **Live** — the target entity is currently active (or the harm is ongoing).
3. **Named** — resolves to a specific person/company at the end of the trail.
4. **Novel** — built from a cross-source join, not in already-published reporting.
5. **Bundled** — ships with a machine-built evidence dossier + a right-of-reply /
   defamation checklist, so a human can verify fast.

Success metric: **precision of the top-N queue** (fraction that survive human
review as genuine, novel, publishable leads), tracked run over run — not raw
match count.

## Guiding principles

- **Signal, not status.** Score the *act* (evasion, breach, concealment), not
  membership of a list.
- **Live + harm.** Gate on `dissolution_date is null` / recent filings; bias to
  public money, regulated services, or identifiable victims.
- **Joins, not density.** Novelty lives where two+ sources meet (PSC ∩ sanctions ∩
  property ∩ disqualification ∩ procurement), never in single-source clusters.
- **Lead, not verdict.** Everything is a hypothesis for human review; no
  auto-accusations. Verification + defamation gating is a first-class step.

## The wrongdoing-signal taxonomy

The scoring layer should recognise these, roughly in descending evidential weight:

| Signal | Definition | Primary sources |
|---|---|---|
| **Sanctions evasion (timing)** | control of a UK entity moves to a relative / thin-identity nominee within a window of the principal's designation date | `uk_psc_relationships` dates × OpenSanctions designation dates |
| **Regulatory breach** | disqualified director still acting (s.11 CDDA 1986); overseas owner not on the ROE (ECTEA 2022) | `uk_disqualified_directors`, HMLR OCOD × CH overseas-entities |
| **Concealment / nominee front** | sole, low-footprint PSC controlling an entity tied to a sanctioned parent or high-harm sector (the Aeza/Timurov pattern) | `uk_psc_relationships` + `sanctions_overlay` + officer-overlap |
| **Control by sanctioned parent** | active UK entity whose ownership chain terminates at an SDN/asset-frozen parent | GLEIF L2 + `uk_psc_relationships` + sanctions |
| **Bank-flagged / court-found** | SAR-flagged subject; adverse court/insolvency finding | FinCEN, OCCRP, court/insolvency feeds (roadmap C/E) |

## Phases (ordered by payoff per unit effort)

### Phase 0 — Deploy what's already built _(unblocks everything temporal)_
- Merge PR #153, redeploy Railway (`git pull --ff-only` → `railway up --detach
  --ci --service shellnet-job`), re-run `ingest_uk_bods` to materialise
  `interim/uk_psc_relationships.parquet` on the volume.
- _Done when:_ a survivor PSC match joins to its company + control dates with no
  zip re-parse.

### Phase 1 — Sanctions-evasion timing detector _(highest leverage; uses Phase 0)_
- `scripts/probe_sanctions_evasion_timing.py`: join `uk_psc_relationships`
  `start_date`/`end_date` against OS designation dates; flag control changes
  within ±N months of a designation, especially to a same-surname / same-address
  party; **filter to currently-active companies.**
- _Done when:_ a ranked evasion-lead report exists and the Mordashov-style
  "shares to the son after dad was sanctioned" pattern is caught generically.

### Phase 2 — Wrongdoing-signal scoring layer
- Turn the taxonomy above into a scored layer in
  `src/shellnet/investigations/` (extend `attention.py` / fold into
  `rank_public_interest_leads.py`): a `wrongdoing_score` dominated by signal
  strength, **gated** by an `active` flag and a `harm` flag — replacing the
  current structure-centric ranking for this queue.
- _Done when:_ top-of-queue is consistently signalled+live, not nameless-dense.

### Phase 3 — Live-status + harm enrichment
- Companies House status/recency check (active vs struck-off, last-filing date)
  as a reusable enrichment; sector/harm tagging (care, social housing, NHS/public
  suppliers, gambling, crypto, defence, education) via SIC codes + procurement.
- _Done when:_ each lead shows current status and a harm category.

### Phase 4 — Corpus expansion on unjoined, wrongdoing-grade seams
- From `docs/ingestion_roadmap.md`, prioritise sources that *are* wrongdoing by
  construction or carry a flag journalists haven't joined: **FinCEN SARs**,
  **OCCRP Laundromat transactions**, **UK/Scottish insolvency + disqualification
  feeds**, **public-procurement/contracts** (public money), **NYC ACRIS** deeper.
- _Done when:_ at least one new source adds a signal the current join can't make.

### Phase 5 — Evidence bundle + verification gate
- For each top lead, auto-build a dossier (reuse `evidence_bundle` /
  `build_validation_pack`) with primary-source deep links (CH filing, sanctions
  listing, property title), a right-of-reply draft, and a defamation/ethics
  checklist that must be ticked before anything leaves the repo.
- _Done when:_ a lead can go from queue → verifiable dossier in one job.

### Phase 6 — Feedback loop
- Record human-review outcomes (genuine / novel / published) per lead; feed back
  into the Phase-2 weights. Track top-N precision over time.
- _Done when:_ weights are tuned from outcomes, not intuition.

## Cross-cutting constraints

- **Compute on Railway** (the box OOMs on the corpus); each new probe needs a
  `_ALLOWED_SCRIPTS` entry + redeploy.
- **Ethics/legal gate is non-negotiable.** Sanctions/disqualification/dissolution
  are public facts; *intent* and *current control* are not — never publish an
  identity-linked wrongdoing claim without independent confirmation.
- **Active-status caveat.** Snapshots lag; always re-check live status (the Aeza
  finding flipped from "active" to "dissolved" on a live check).

## The first move

Phase 0 → Phase 1. The evasion-timing detector is the highest-value next probe:
it converts the relationship layer just shipped (PR #153) into a *signal* (control
timing vs sanction timing) rather than a status lookup, targets currently-active
companies, and resolves to a named principal + nominee — the shape of a story
people care about.
