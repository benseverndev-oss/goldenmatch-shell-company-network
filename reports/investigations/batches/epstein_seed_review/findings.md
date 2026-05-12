# Findings — `epstein_seed_review` batch

Generated 2026-05-12 from `seeds/epstein_entities.csv` (28 seeds) via
`scripts/investigate_entities.py`. Per-seed reports live in this directory
(`NNN_<slug>.md`); `index.md` is the auto-generated summary table.

> **Hypothesis, not proof.** Every candidate in this batch is a lead the
> matcher produced from public data. Names collide. Public data is
> incomplete. Treat each row as a lead requiring human review, not a
> finding. Nothing below should be read as a claim that any company is
> owned by, controlled by, or otherwise involved with Jeffrey Epstein
> unless the seed source itself says so and an independent record below
> corroborates it.

## Run scope

- **Candidate pool:** ICIJ-only — 814,344 rows from the Offshore Leaks
  bundle (Panama / Paradise / Pandora / Offshore Leaks).
- **Sources not staged for this run:** GLEIF Golden Copy, OpenCorporates,
  OpenSanctions. None of those interims were on disk at run time.
- **GoldenMatch published context:** skipped — `DATABASE_URL` not set.
- **Match config:** RapidFuzz `token_sort_ratio`, min score 85, top-N 25,
  jurisdiction as a strong preference (not a hard filter).
- **Total runtime:** 76.6 s.

The candidate pool matters: ICIJ has only **2 rows tagged `vi`** (US
Virgin Islands) and **482 tagged `us`**. Most rows are either offshore
registries (BVI, Malta, Aruba, Bermuda, Cayman) or have no jurisdiction
at all (482,214 / 814,344 ≈ 59% null). The Epstein seed list is dominated
by USVI and US-Delaware entities, so for most seeds the search space
here is structurally wrong. See "What would extend coverage" below.

## Numbers

- 28 seeds processed, 0 errors.
- **1** seed had a same-jurisdiction candidate (an exact normalized-name match).
- **20** seeds returned at least one outside-jurisdiction candidate.
- **11** seeds returned zero candidates anywhere:
  `J. Epstein & Co.`, `Great St. Jim, LLC`, `Plan D, LLC`,
  `Hyperion Air, LLC`, `Hyperion Air, Inc.`, `L.S.J., LLC`,
  `J Epstein Virgin Islands Foundation Inc.`, `Gratitude America Ltd.`,
  `JEGE Inc.`, `Jeepers Inc.`, `BV70, LLC`.

## Strong lead (1)

### #27 — `Liquid Funding Ltd.` / Bermuda

- Top candidate: `icij:82004676` `Liquid Funding, Ltd.`, jurisdiction `bm`, score **100.0** (exact normalized).
- 1-hop ICIJ neighbourhood (Paradise Papers — Appleby leak) names
  **`Epstein - Jeffrey E` as `director of`** the entity, alongside other
  named directors and PricewaterhouseCoopers as auditor.
- The matcher did **not** see the seed source note when it surfaced that
  officer — the officer link came directly from ICIJ edge data.
- Caveat: ICIJ membership does not in itself imply wrongdoing, and the
  director's name needs human verification (DOB / address / cross-reference
  to a known Epstein filing) before being relied on. The Appleby filing
  itself should be the next read.
- See `027_liquid_funding_bm.md` for full provenance.

This is the only report in the batch where the literal ICIJ name string
`Epstein - Jeffrey` appears outside the seed-source note that we ourselves
planted.

## Weaker leads worth a skim

These returned exact or near-exact name matches in ICIJ but with
`jurisdiction = ?` (null) — meaning ICIJ stripped or never had the
registry country. They are most likely unrelated entities with colliding
names, but the per-report 1-hop neighbourhoods are cheap to scan for any
officer / address that lines up with known Epstein-network facts.

| # | Seed | Top candidate | Score | Report |
| ---: | --- | --- | ---: | --- |
| 14 | `Laurel, Inc.` | `LAUREL INCORPORATED` | 100.0 | `014_laurel_vi.md` |
| 22 | `Butterfly Trust` | `Butterfly Limited` | 100.0 | `022_butterfly_vi.md` |
| 21 | `HBRK Associates, Inc.` | `BRKG ASSOCIATES LTD.` | 93.3 | `021_hbrk_associates_us.md` |
| 18 | `FT Real Estate, Inc.` | `JTL Real Estate Ltd` (vg) | 89.7 | `018_ft_real_estate_us.md` |

Rows 1–3, 5, 6, 8, 12, 13, 23, 24, 25 also produced outside-jurisdiction
candidates worth a quick scan in case any 1-hop neighborhood surfaces a
named officer or registered address that corroborates the seed. Without
GLEIF / OpenCorporates / OpenSanctions in the pool, the expected default
on these is "name collision, no further signal."

## Likely dead-ends in *this* run

These are the seeds where the ICIJ-only pool is structurally the wrong
place to look. Absence of an ICIJ match here is uninformative — it
should not be read as evidence that the entity doesn't exist or isn't
linked to Epstein.

- **USVI registry entities** (rows 1–14 minus #4):
  `Southern Trust Company, Inc.`, `Southern Financial LLC`,
  `Financial Trust Company, Inc.`, `Southern Country International Ltd.`,
  `Nautilus, Inc.`, `Great St. Jim, LLC`, `Poplar, Inc.`, `Plan D, LLC`,
  `Hyperion Air, LLC`, `Hyperion Air, Inc.`, `Cypress, Inc.`,
  `Maple, Inc.`, `Laurel, Inc.`.
  USVI corporate registrations don't live in ICIJ. Need OpenCorporates
  (USVI registry) or the USVI Lieutenant Governor / Corporations and
  Trademarks division filings directly.
- **US Delaware / LLC entities** (rows 4, 15, 18–21, 25, 28):
  `J. Epstein & Co.`, `L.S.J., LLC`, `FT Real Estate, Inc.`,
  `JEGE Inc.`, `Jeepers Inc.`, `HBRK Associates, Inc.`,
  `Elysium Management, LLC`, `BV70, LLC`.
  Same problem — need OpenCorporates (US-DE) or LEI matches via GLEIF.
- **Foundations** (rows 16, 17):
  `J Epstein Virgin Islands Foundation Inc.`, `Gratitude America Ltd.`.
  US-tax-exempt orgs; needs IRS Form 990 / ProPublica Nonprofit Explorer
  data, not ICIJ.

## What would extend coverage

1. **OpenCorporates ingest** is the biggest missing piece. Specifically:
   the USVI registry and a US-Delaware seed query around the named LLCs.
   Adapter is already in the repo (`scripts/ingest_opencorporates.py`);
   blocked on an API key + a curated seed-name list. Re-run this batch
   after that and the USVI seeds should start to anchor.
2. **GLEIF Golden Copy ingest** for LEI-anchored cross-checks against
   any of the financial entities (`Financial Trust Company`,
   `Southern Trust Company`, `Liquid Funding`) that might have requested
   LEIs at some point.
3. **OpenSanctions ingest** for sanctions / PEP / register overlap on
   the offshore-network seeds — particularly the trusts and the
   Bermuda / BVI entities.
4. **Person-side cross-check.** With person tables built
   (`scripts/build_person_table.py` + a person-dedupe run), we could
   query `Jeffrey Epstein` as a person-seed and surface every entity
   the ICIJ person-graph attaches to him — not just the entities a
   sourced public list already names. That's potentially the strongest
   single follow-up.

## Reproducing

```
uv run python scripts/build_candidate_tables.py
uv run python scripts/investigate_entities.py seeds/epstein_entities.csv \
    --batch-id epstein_seed_review --top-n 25 --min-score 85 --verbose
```

Outputs are written to this directory.
