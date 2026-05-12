# Follow-up findings — Epstein investigation (person + address + 2-hop)

Generated 2026-05-12. Companion to `batches/epstein_seed_review/findings.md`,
which covered the entity-side batch run.

> **Hypothesis, not proof.** Everything below is a lead the matcher
> produced from public data. Personal-name matches collide aggressively;
> address-text matches reflect string similarity, not verified physical
> identity; shared-officer overlaps are circumstantial. Nothing here
> should be read as a claim that the named individuals or companies
> were owned or controlled by Jeffrey Epstein, unless the sourced
> documents themselves say so.

## What this run added

Three new local capabilities, all built on the same ICIJ corpus already
loaded for the entity-side batch:

1. **`scripts/investigate_person.py`** — query the unified person table
   by name + country, then walk officer/intermediary/shareholder edges
   back to every company the matched person(s) attach to.
2. **`scripts/investigate_address.py`** — query the unified address
   table by free-text + country, then surface every entity registered
   at fuzzily-matching addresses.
3. **`scripts/expand_2hop.py`** — one-shot 2-hop walk from any company
   `entity_uid`: company → its officers → all *other* companies those
   officers attach to. Ranks results by number of distinct shared officers.

## 1 — Jeffrey Epstein, person query

Ran `investigate_person.py --name "Jeffrey Epstein" --min-score 80`.

**Findings:**

- ICIJ contains exactly one record consistent with the seed:
  `icij:80063035` `Epstein - Jeffrey E` (kind=officer, country=?).
  Score 93.8 against the seed `jeffrey epstein`.
- That record attaches to exactly **one** company in the ICIJ corpus:
  `icij:82004676` `Liquid Funding, Ltd.` (Bermuda), via two distinct
  edges from the Paradise Papers — Appleby leak:
  - `director of`, 2001-11-09 → 2007-03-30
  - `chairman of`, 2001-11-09 → 2007-03-19
- The three other top-scoring matches are clearly different people:
  `Bleustein Jeffrey L` (Harley-Davidson Foreign Sales),
  `Goldstein Jeffrey` (RG/G FSC),
  `Greenstein Jeffrey H` (IXI Bicycle Company, Bermuda).
  Name-collision noise, not Epstein.

**Reading:** the person-side walk confirms — and adds dates to — the
single ICIJ-direct Epstein connection already surfaced by the
entity-side batch. It also tells us the *absence* of any other
ICIJ-direct Epstein record is real, not a coverage artefact. Any
Epstein-network entities outside ICIJ (the USVI / US-DE / foundation
seeds from the original batch) will need OpenCorporates / GLEIF /
OpenSanctions ingest to surface.

Report: `reports/investigations/persons/jeffrey_epstein_global.md`.

## 2 — 2-hop expansion from `Liquid Funding, Ltd.`

Ran `expand_2hop.py --entity-uid icij:82004676 --label liquid_funding`.

**Topology:**

- 18 officer-class neighbours on the seed (14 named individuals, 1
  intermediary = `Appleby Services (Bermuda) Ltd.`, 2 audit firms
  = `PricewaterhouseCoopers LLP` and `Deloitte & Touche LLP`, 1
  corporate parent-shape = `Liquid Funding Holdings, LLC` (US)).
- 3,756 other ICIJ companies share at least one of those officers.
- 10 of the seed's 18 officers appear elsewhere in ICIJ.

**Most of the volume is provider noise.** Appleby Services is the
registered-agent for thousands of Bermuda entities; the two audit
firms similarly. Filter mentally for *named individuals* who appear
alongside Epstein on Liquid Funding.

**Noteworthy hit:**

- **`icij:82006077` `Bear Stearns International Funding (Bermuda)
  Limited`** shares **`icij:80094304` `Lipman - Jeffrey M`** (and the
  Appleby intermediary) with Liquid Funding. Lipman is listed as a
  co-director of Liquid Funding alongside Epstein.

  Context worth flagging (but **not** something the matcher can
  verify): Epstein's career began at Bear Stearns; the Bear Stearns
  ↔ Liquid Funding ↔ Epstein triangle here is consistent with that
  biographical detail, but the matcher only knows that the same
  string `Lipman - Jeffrey M` appears on both Bermuda entities. A
  human reviewer would want DOB / address / known professional record
  confirmation before treating the Lipman ↔ Lipman as the same person.

**Corporate parent-shape:**

- `icij:80094344` `Liquid Funding Holdings, LLC` (US) is recorded as
  an officer of Liquid Funding Ltd. — the apparent US parent /
  holding-company. Worth investigating directly if OpenCorporates is
  staged later (the LLC isn't currently in our pool as a *company*
  row, only as a person-shaped officer link).

- Beyond Bear Stearns, the next dense overlaps are clearly unrelated
  Bermuda commercial entities (Mundipharma's multiple subsidiaries,
  EPI Ecopetrol Pipelines, etc.). They share the Appleby intermediary
  + a handful of common Bermuda directors (Erskine, Gillespie, Gores,
  Poole), not Epstein himself.

Report: `reports/investigations/expansions/liquid_funding_2hop.md`
(28 KB; full ranked table of all 3,756 entities).

## 3 — Known Epstein addresses

Sanity-checked 3 addresses against the unified address table (701,569
rows; 100% ICIJ).

| Seed | Country | Min score | Address rows | Distinct entities | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| `Little St James` | (global) | 80 | 0 | 0 | Not in ICIJ — USVI not covered. |
| `Ugland House Grand Cayman` | ky | 75 | 6 | 11 | Maples & Calder mass-incorporation address — typical KY noise; none of the 11 entities are named in our Epstein seed list. |
| `El Brillo Way Palm Beach` | us | 75 | 0 | 0 | Not in ICIJ — US residential not covered. |
| `Canon's Court Hamilton Bermuda` | bm | 70 | 19 | 41 | Appleby's Bermuda office — mass-incorporation noise; Liquid Funding is among the 41 (expected). |

**Reading:** the address-side workflow works (Ugland House and Canon's
Court correctly surface as mass-incorporation hubs), but the two
direct-Epstein addresses (Little St James, El Brillo Way) are simply
not in ICIJ. Same structural gap as the entity-side batch: the corpus
covers offshore-provider registries, not USVI / US residential
records. Re-running these after OpenCorporates or a USVI-registry
ingest is the obvious next step.

## Summary

This follow-up materially **strengthens the one corroborated lead**
(Liquid Funding ↔ Epstein) by:

- Adding the date range (2001-11-09 → 2007-03-30 as director, ending
  ~11 days earlier as chairman).
- Adding the role hierarchy (director **and** chairman, not just
  director).
- Identifying a candidate corporate parent (`Liquid Funding Holdings,
  LLC`).
- Surfacing one potentially related entity (`Bear Stearns
  International Funding (Bermuda) Limited`) via a co-director name
  (`Lipman - Jeffrey M`) — still a *hypothesis* about a shared
  individual, not a verified link.

It **confirms** that ICIJ's coverage of Epstein-direct material is
limited to that one record. Every other seed in the original Epstein
list either doesn't appear in ICIJ at all or appears only as a
name-collision against unrelated offshore entities. Extending real
coverage requires OpenCorporates (USVI + US-DE), GLEIF (for any
LEI-anchored financial entities), and OpenSanctions (for any sanctions
overlap).

## Reproducing

```
# Prereqs (build the unified tables from staged ICIJ interim parquets):
uv run python scripts/build_candidate_tables.py
uv run python scripts/build_person_table.py
uv run python scripts/build_address_table.py

# Person query:
uv run python scripts/investigate_person.py \
    --name "Jeffrey Epstein" --min-score 80 --top-n 50

# 2-hop expansion from the one confirmed connection:
uv run python scripts/expand_2hop.py \
    --entity-uid icij:82004676 --label liquid_funding

# Address probes:
uv run python scripts/investigate_address.py \
    --text "Ugland House Grand Cayman" --country ky --min-score 75
```
