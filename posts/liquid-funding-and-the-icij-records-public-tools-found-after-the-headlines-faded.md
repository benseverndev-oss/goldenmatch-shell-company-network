---
title: "Liquid Funding and the ICIJ record public tools found after the headlines faded"
subtitle: "An entity-resolution case study against ~1.2M offshore-company records"
canonical_url: ""
tags:
  - entity-resolution
  - investigative-data
  - icij
  - opensanctions
  - python
cover: ""
publish_date: ""
---

> **Hypothesis, not proof.** This post is investigative data engineering, not
> an accusation engine. A name match in a public-leak corpus is a *lead* to
> verify, not a conclusion. I cite primary sources (FINRA, ICIJ, court
> filings) for each factual claim; everything else is hedged.

## What this is

I built [`goldenmatch-shell-company-network`](https://github.com/benzsevern/goldenmatch-shell-company-network)
as a case study in using
[GoldenMatch](https://pypi.org/project/goldenmatch/) to reconcile
shell-company records across noisy public sources — and to demonstrate the
matcher with a *real* investigative question rather than a synthetic
benchmark.

The corpus combines four public sources into one unified table:

| Source | What it brings | Rows |
| --- | --- | ---: |
| ICIJ Offshore Leaks (Panama / Paradise / Pandora) | Entities + officers + addresses + relationships from the major offshore-provider leaks | 814,344 companies, 796,944 person-shaped rows, 701,569 addresses |
| OpenSanctions `default` collection | Sanctions + PEPs + regulator debarments + re-exports of ICIJ nodes | +426k companies, +1.15M persons, +479k addresses |
| GLEIF Golden Copy | LEI-anchored authoritative company records | (separate run; 3.3M rows, used for cross-source list-match) |
| OpenCorporates | Registry-anchored records (needs API key) | not staged for this run |

Combined post-ingest: **1.24M companies / 1.95M persons / 1.18M addresses.**

The investigative question I picked: *how much of the Jeffrey Epstein
corporate network is visible in public-source data, and which leads
actually hold up under independent verification?*

## The seed list

I started from a 28-entity list assembled from public records — the USVI
Second Amended Complaint (ST-20-CV-14), the NYDFS Consent Order, the
Senate Finance 2025 list, and JPMorgan litigation cash-flow tables. Each
seed carries its source citation in a `seed_group` column. Crucially:
**the seed list is provenance, not conclusion.** Inclusion meant a
public document named the entity in an Epstein-adjacent context worth
verifying — nothing more.

The list spans:

- USVI-registered corporations from the SAC (Nautilus, Cypress, Maple,
  Laurel, Poplar, Plan D, Hyperion Air, Southern Trust, Southern
  Financial, Financial Trust, etc.)
- US-Delaware LLCs from the JPMorgan litigation (FT Real Estate, JEGE,
  Jeepers, HBRK Associates, BV70, L.S.J., Elysium Management).
- VI-domiciled trusts and foundations (Butterfly Trust, Haze Trust,
  Elysium Trust, J Black Trust, J Epstein Virgin Islands Foundation,
  Gratitude America).
- One Bermuda investment vehicle public reporting names: Liquid Funding
  Ltd.

I ran each seed through the same workflow: normalize the name +
jurisdiction, RapidFuzz `token_sort_ratio` against the unified company
table (default threshold 85), partition results into same-jurisdiction
matches (main section) vs outside-jurisdiction matches (separate
section, never silently mixed), then attach a 1-hop ICIJ neighborhood
walk (registered addresses, officers, intermediaries, connected
entities). One markdown report per seed, plus an index summarizing the
batch.

## What the corpus could and couldn't see

Of 28 sourced seeds, **exactly one** returned an exact in-jurisdiction
match: `Liquid Funding, Ltd.` (Bermuda), score 100.0, exact
normalized-name match. That's *not* because the other 27 entities don't
exist — it's because the corpus is structurally narrow for this seed
list. ICIJ has 2 rows tagged `vi` (US Virgin Islands) and 482 tagged
`us` out of 814k total. The Epstein seed list is dominated by USVI and
US-Delaware records, and neither registry feeds into ICIJ. Adding
OpenSanctions widened the candidate pool but not where this list
needed it: OS doesn't carry the USVI corporate registry either.

This is the kind of negative result that a public showcase rarely
spells out, but it matters. *Absence of a match here is not evidence
the entity isn't Epstein-linked* — it's evidence that ICIJ +
OpenSanctions are the wrong corpus to look in for USVI-registry
material. The same workflow run against an OpenCorporates ingest with
a USVI seed query would almost certainly anchor most of those 27
seeds. That's left as the obvious extension.

## The one lead, and what it actually says

`Liquid Funding, Ltd.` (`icij:82004676`) appears in the Paradise Papers
— Appleby leak, with 17 named officers across the entity's lifetime.
Two of those rows are the same individual:

- `Epstein - Jeffrey E` — listed as **director** of Liquid Funding
  from `2001-11-09` to `2007-03-30`.
- `Epstein - Jeffrey E` — listed as **chairman** of Liquid Funding
  from `2001-11-09` to `2007-03-19` (ending 11 days earlier than the
  director role).

The seed source (public reporting) and the ICIJ record corroborate
each other on this point. This is the one part of the case study
where the matcher's output and the sourced reporting agree closely
enough that I'm comfortable calling it a *fact*, not a hypothesis.

But there's no other ICIJ-direct attachment to Jeffrey Epstein in the
entire 1.95M-row person table. A name-prefix scan returns 29 records
with `epstein` in the normalized name — Alan Lee Epstein, Glenn H
Epstein, Jonathan Stuart Epstein, Martin J Epstein, Mel H Epstein,
Richard Epstein, Samuel H Epstein, Zelma Epstein, plus intermediary
firms (Epstein, Chomsky, Osnat & Co.; Epstein & Reed) and surname-only
matches in longer composite names. *Jeffrey E is the only Jeffrey
Epstein.* OpenSanctions has 18 more "Epstein" records (mostly US
healthcare-fraud debarments and PEPs from various countries) — none of
them are him either. The single Liquid Funding chairmanship is the
only ICIJ-direct Epstein attachment that exists.

## The 2-hop walk, and why most of it is provider noise

Once you have one confirmed lead, the obvious next move is to walk
the graph: company → its officers → other companies those officers
attach to. The raw 2-hop from Liquid Funding surfaces **3,756 other
ICIJ companies** sharing at least one officer with the seed.

Almost all of that volume is *provider noise*. `Appleby Services
(Bermuda) Ltd.` is the registered-agent for thousands of Bermuda
entities; PricewaterhouseCoopers LLP and Deloitte & Touche LLP appear
as auditor across the same population. None of these "shared officers"
are meaningful identity links.

After filtering to *named individuals* (dropping officers whose names
carry corporate legal suffixes like Ltd / LLC, or match a known
provider firm) the 3,756 rows collapse to **566**. One row stands out:

> `Bear Stearns International Funding (Bermuda) Limited` shares
> `Lipman - Jeffrey M` with Liquid Funding. (Lipman is one of Liquid
> Funding's directors alongside Epstein.)

That was the matcher's most interesting non-provider signal. The
question: is this `Lipman - Jeffrey M` (in two different ICIJ nodes,
one Bermuda and one Barbados) the same individual?

## Verifying the secondary lead

This is where the case study gets into investigative territory. The
matcher can only tell you the string `Lipman - Jeffrey M` appears in
both places. A human investigator has to confirm identity.

Five independent public sources confirm it:

- **FINRA BrokerCheck** is authoritative for registered US financial
  professionals. CRD# 717915 is `JEFFREY MARK LIPMAN`, registered
  with `BEAR, STEARNS & CO. INC. (CRD# 79)`, New York, NY,
  **10/1980 – 09/2008**. 28 years. (Source:
  [files.brokercheck.finra.org/individual/individual_717915.pdf](https://files.brokercheck.finra.org/individual/individual_717915.pdf))
- **ICIJ has a second Lipman record** at `icij:110014080` — Paradise
  Papers, Barbados corporate registry: `LIPMAN JEFFREY M` as
  Director of `BEAR STEARNS CARIBBEAN ASSET HOLDINGS LTD.` from
  `10-JUL-2008` onward. Same individual, different leak, different
  jurisdiction. A clean cross-leak corroboration *inside the corpus*.
- **National Memo**: "Bear Stearns' 40 percent stake in Epstein's
  Liquid Funding which, by this time, had $6.7 billion in liabilities…"
  — Bear Stearns held a 40% equity stake in Liquid Funding. The
  ICIJ-observed officer overlap (Lipman + Novelly sat on both boards)
  is consistent with that ownership stake.
- **OffshoreAlert** has 357 pages of Bermuda Registrar filings for
  Liquid Funding (dissolved 2015-11-25), tagging Lipman, Novelly,
  Epstein, Liquid Funding Holdings, and Appleby (registered agent).
- A public "Finding Truth" Obsidian-published note also independently
  documents the Lipman + Novelly co-directorships across Liquid
  Funding and Bear Stearns.

The matcher's hypothesis was correct. Jeffrey M Lipman, a Bear Stearns
Senior Vice President from 1980 to 2008, sat on the Liquid Funding
board alongside Epstein. Bear Stearns owned 40% of Liquid Funding via
the US holding company `Liquid Funding Holdings, LLC` (which OffshoreAlert
also confirms).

## What worked, what didn't, what's next

**What worked.** The pipeline produced one corroborated lead, walked
2 hops to one verified secondary connection, and produced a clean
"hypothesis, not proof" framing throughout. The matcher's structural
choices — strong jurisdiction preference (not a hard filter), 1-hop
ICIJ neighborhood attached to every candidate, no silent mixing of
in-jurisdiction vs outside-jurisdiction results — meant that even the
weak leads were inspectable on their own terms.

**What didn't.** The corpus has a real coverage gap for USVI / US-DE
seeds. Out of 28 sourced entities, 11 returned zero hits anywhere and
16 returned only weak outside-jurisdiction name collisions. The gap
isn't a matcher problem; it's a data problem. OpenSanctions didn't
close it (no USVI registry). GLEIF didn't close it (very few LEIs for
small offshore LLCs). The only realistic way to anchor most of that
list would be OpenCorporates against the USVI registry directly.

**What's next.** Three obvious follow-ups:

1. OpenCorporates ingest scoped to USVI + US-Delaware seed names —
   would potentially anchor 7-10 currently-zero-hit entities.
2. A focused review of the remaining 565 named-individual 2-hop rows.
   Most are Bear Stearns-era Bermuda directors with no apparent
   Epstein link, but a per-entity Appleby-filing review would close
   the question definitively.
3. Person-side dedupe across the full 1.86M-row corpus (now ingestible
   after filtering out the 85,865 "Bearer share" placeholders that
   were OOMing the matcher). Could surface other cross-source
   identity hypotheses beyond the Liquid Funding pair.

## Try it yourself

Repo: <https://github.com/benzsevern/goldenmatch-shell-company-network>.

The two executable notebooks are
[`01_case_study.ipynb`](https://github.com/benzsevern/goldenmatch-shell-company-network/blob/main/notebooks/01_case_study.ipynb)
(Phoenix Spree Deutschland) and
[`02_epstein_case_study.ipynb`](https://github.com/benzsevern/goldenmatch-shell-company-network/blob/main/notebooks/02_epstein_case_study.ipynb)
(this post's investigation). Each re-derives every number and table
from the data on disk. The CLIs are designed to be runnable on any
sourced seed list:

```bash
uv run python scripts/investigate_entities.py seeds/your_list.csv \
    --batch-id your_run --top-n 25 --min-score 85
```

If you reuse the workflow on a different topic, keep the framing
honest: matches are hypotheses, public data is incomplete, manual
review is required, every assertion should cite back to a source the
matcher could not have made up.

---

**About this post.** This is a writeup of work merged across PRs
#3–#10 in [goldenmatch-shell-company-network](https://github.com/benzsevern/goldenmatch-shell-company-network).
The full machine-readable findings live under
[`reports/investigations/`](https://github.com/benzsevern/goldenmatch-shell-company-network/tree/main/reports/investigations).
