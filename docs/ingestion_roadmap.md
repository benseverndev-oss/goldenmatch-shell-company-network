# Ingestion roadmap — corpora that would extend novelty surface

State as of 2026-05-13. Five external data sources, ranked by novelty
payoff per hour of adapter work, that the existing pipeline doesn't yet
consume. Each section lists the source URLs, the data shape, the rows
we'd actually consume, the adapter work it implies, and a concrete
sequence of steps to land it.

This doc exists because the existing corpus (ICIJ + OpenSanctions +
GLEIF entity rows) has been demonstrably mined — every dense cluster
the matcher surfaces maps to already-published investigative journalism.
The corpora below target the gaps where journalism hasn't done the join.

## A — UK PSC + Overseas Entities (via OpenOwnership BODS)

**Why first.** UK is the world's second-most-popular shell-company
jurisdiction after the offshore set. ICIJ + OS carry zero UK official
beneficial-ownership disclosures. Adding it catches the
"sanctioned individual → UK Ltd → UK property" three-hop chains that
don't show up in ICIJ.

**Source.**
- URL: `https://oo-bodsdata.s3.amazonaws.com/data/uk_version_0_4/parquet.zip`
- Size: 3.67 GB
- Format: BODS v0.4 statements; pre-processed parquet
- Tables: person-statement, entity-statement, relationship-statement,
  interest rows (cross-linked via `statementId`)
- Last snapshot: 2025-03-11 (monthly refresh)
- Licence: CC0

**Rows.**
- ~13.9 M relationship statements
- ~29.6 M interest records
- ~9-10 M person statements (UK PSC declarations: name, country, DOB
  month/year, address district, nature-of-control type)
- ~3-4 M entity statements

**Adapter work (estimate).**

- `src/shellnet/sources/bods.py` — generic BODS statement parser; uses
  PyArrow to stream the parquet shards. ~3 hr.
- Hook into `_load_*` in `company_features.py` + `person_features.py`.
  ~30 min.
- New `goldenmatch_relationship.yml` if we want to consume the
  `relationship-statement` rows as edges into our NetworkX graph. ~1 hr.
- `/run-script` allowlist entry + Railway redeploy. ~10 min.

**Sequence to land.**

1. Fetch the 3.7 GB ZIP via `/fetch-url` to `/data/raw/openownership/uk_bods.zip`
2. Add `scripts/ingest_uk_bods.py` that:
   - Streams the parquet shards inside the ZIP
   - Filters `recordType in ('person', 'entity')` for the matcher's first pass
   - Emits two parquets: `uk_bods_persons.parquet`, `uk_bods_entities.parquet`
3. Extend `build_person_table.py` + `build_candidate_tables.py` to merge those.
4. Re-run `/run-script?name=list_match_os_sanctions_vs_icij` (or a new
   `list_match_os_sanctions_vs_uk` variant) to see what new matches surface.

**Expected novelty payoff.** *High.* Adds named PSCs with country + DOB
attribution — a much stronger identity signal than ICIJ's bare officer
names. Likely to surface UK Ltds where a sanctioned principal sits as
PSC, which the existing matcher cannot see.

## B — UK Overseas Entities Register (subset of A)

**Why.** Post-2022 UK requirement: any overseas entity owning UK
property must register beneficial owners with Companies House.
Designed exactly to catch the "Russian-oligarch-via-BVI-buys-London-
mansion" pattern. Tightly focused subset of A — useful as a standalone
quick win if A turns out too heavy.

**Source.** Same as A. The UK BODS feed includes both PSC and Overseas
Entities in the same parquet. Filter by `source_url` containing
`"register-of-overseas-entities"` or by entity type.

**Rows.** ~50 k overseas-entity registrations + their beneficial
owners (~150 k people).

**Adapter work.** None *separate* from A. Implementing A subsumes this.
Tagged separately because a "UK property-owner-tagged" subset is much
smaller and could be useful for a focused Russian-asset-tracker style
pass.

**Expected novelty payoff.** *High.* This corpus is *designed* for the
sanctions-enforcement use case. Every row is an explicit
"overseas-entity ↔ UK property" link with named beneficial owners.

## C — FinCEN Files structured data

**Why.** 2020 BuzzFeed + ICIJ leak of Suspicious Activity Reports.
Bank-SAR signal is much higher confidence than provider-record signal
— every row is a bank's own money-laundering flag. Narrow but
extremely high-quality.

**Source.**
- Primary release: BuzzFeed + ICIJ ("The FinCEN Files")
- Structured CSV / JSON: ICIJ's GitHub release alongside the project
- URL (as of 2020): `https://github.com/ICIJ/fincen-files-data`
- May need to scrape the project page for the latest endpoint
- Licence: research / fair use; cite explicitly

**Rows.**
- ~2,121 SARs; ~2,500 named entities; ~18,000 transactions
- Each row: filing bank, subject entity, transaction amount + currency,
  beneficiary bank, narrative

**Adapter work.**

- `src/shellnet/sources/fincen.py` — small, CSV-shaped, well-documented.
  ~1.5 hr.
- Edge type: introduce `flagged_by_bank` and `transaction_with` relation
  kinds.
- `scripts/ingest_fincen.py`. ~30 min.

**Sequence.**

1. Pull the structured release from ICIJ's GitHub.
2. Ingest entity rows into the unified company table (where `entity_schema = Company`)
   and person rows into the person table.
3. Emit `fincen_transactions.parquet` for graph use.
4. Re-run list-match; expected hits: small but very high-confidence.

**Expected novelty payoff.** *Medium-high.* Coverage is narrow but every
hit is a bank's flagged suspicion — that's a different *quality* of
signal than the existing corpus. Likely catches a handful of
ICIJ-named entities that banks flagged but journalists didn't connect.

## D — GLEIF Level 2 corporate-ownership (parent-child)

**Why.** We already ingest GLEIF entity rows but throw away the
`parent_lei` / `child_lei` fields. Walking those produces a
corporate-ownership graph **without needing any leak data** —
authoritative, registry-derived.

**Source.**
- We already have the GLEIF Golden Copy JSON at `/data/raw/gleif/`.
- Each entity has optional `RelationshipRecord` blocks pointing to direct
  parent / ultimate parent LEIs.
- Alternative: OpenOwnership re-publishes Level 2 as BODS parquet at
  `https://oo-bodsdata.s3.amazonaws.com/data/gleif_version_0_4/parquet.zip`
  (1.1 GB)

**Rows.** ~2.5 M ownership relationships across ~3.3 M LEI entities.

**Adapter work.**

- Modify `src/shellnet/sources/gleif_golden_copy.py` (or a new
  `gleif_ownership.py`) to emit a `gleif_ownership_edges.parquet` with
  `(child_lei, parent_lei, kind, percent, start_date, end_date)`. ~1 hr.
- Wire into the graph builder so `parent_of` edges include LEI-derived ones.

**Expected novelty payoff.** *Medium.* The corporate-ownership graph
itself isn't secret — anyone can pull it from GLEIF — but layering it
on top of our ICIJ + OS officer graph would surface "this GLEIF
subsidiary chain ends at a sanctioned ultimate parent" patterns the
existing matcher can't see.

## E — OCCRP Russian / Troika Laundromat structured data

**Why.** OCCRP's 2014/2019 investigations published transaction-level
data on Russian-source money flows. **This is exactly the missing
bridge for Igor Putin's 25+ proxy companies** — the transaction-level
data that links the named principals to the nominee operators ICIJ
captures but doesn't link.

**Source.**
- Russian Laundromat: <https://www.occrp.org/en/investigations/the-russian-laundromat>
- Troika Laundromat: <https://www.occrp.org/en/troikalaundromat/>
- Data shape: NOT FtM / BODS — OCCRP's own format, varies per project.
  Some published as Datasette databases, some as Aleph entities, some as
  CSV alongside articles.
- Aleph API: `https://aleph.occrp.org` (free researcher access, rate-limited).

**Rows.** Variable; Russian Laundromat estimated ~70k transactions,
Troika Laundromat ~1.3M; structures differ.

**Adapter work.** **Heavy.**

- Need to negotiate per-project data shape (CSV / Aleph API / Datasette).
- Aleph API client + pagination + rate-limit handling. ~3 hr.
- Per-project schema normaliser. ~2 hr each (likely 2-3 projects).
- Total: ~8-12 hr, multi-session.

**Sequence.**

1. Apply for Aleph researcher access (free, ~1-day turnaround).
2. Scope to one project first (Russian Laundromat is the smaller).
3. Build the Aleph client + normaliser.
4. Add `transaction` as a new edge kind in the schema.
5. Re-run investigations with the transaction layer enabled.

**Expected novelty payoff.** *Highest of the five if it works,
lowest probability of working in a single session.* The transaction
layer is where journalists have done their actual cross-source linking
work, but it requires bespoke adapter effort that we'd revisit in a
dedicated push.

## Order of execution (for the autonomous run)

1. **A — UK BODS** (PSC + Overseas Entities; covers B as well). Highest
   immediate payoff. ~4-6 hr including Railway ingest.
2. **D — GLEIF L2** (we already have the GLEIF JSON; extract the
   relationship blocks). ~1-2 hr.
3. **C — FinCEN Files** (small, well-shaped). ~2 hr.
4. **E — OCCRP Laundromat** (heaviest; flagged for follow-up session).

This sequence trades coverage for compounding pipeline yield: after A
+ D land, the *next* list-match pass against OpenSanctions has a
materially larger candidate surface. C + E are additive but smaller.

## Status update — what actually landed

**A — UK BODS: completed.** Adapter at
`src/shellnet/sources/bods.py`; ingest script at
`scripts/ingest_uk_bods.py`. On Railway: 12.15 M UK PSC persons +
5.79 M UK entities. Unified person table grew to 14.02 M rows.
Re-running the OS-sanctions list-match with UK PSC scoped to
ru/ua/by/cy/kz surfaced **43 novel exact-name matches**, including
Wikidata-anchored hits like Zyuzin (Mechel), Filatov (Sibanthracite),
Marchenko (Medvedchuk's wife), and direct UK Companies House PSC
declarations from Mordashov-son, Giner (CSKA), Isaykin (Volga-Dnepr),
Viktorov, and others. See
`reports/investigations/list_match_uk_psc_findings.md` and
`posts/sanctioned-russians-on-the-uk-psc-register-...`.

**B — UK Overseas Entities: completed.** Subsumed by A. The BODS
feed includes both registers.

**C — FinCEN Files: queued, blocked on data shape.** ICIJ publishes
the data only through an interactive web explorer
(`projects.icij.org/investigations/fincen-files/explore-the-data/`).
There's no clean bulk CSV / JSON download — the data is loaded
client-side by the interactive frontend. Two paths to land it:

1. Build a scraper for the explore frontend's JSON endpoints
   (~2-3 hr; brittle but tractable).
2. Email ICIJ data team and request the raw transaction dataset
   (response time unknown; they're generally responsive to
   research requests).

Neither fits an autonomous run.

**D — GLEIF L2: queued, low payoff for current pipeline shape.**
Two practical sources:

1. The GLEIF Golden Copy RR (Relationship Record) JSON file —
   parallel to the LEI2 file we already ingest. The current
   `src/shellnet/sources/gleif_golden_copy.py` only consumes LEI2.
   Adding RR ingest is a ~1-2 hr extension.
2. OpenOwnership BODS GLEIF Level 2 parquet (~1.1 GB) — same
   adapter pattern as A.

The actual blocker for novelty payoff isn't the data — it's that the
*current list-match workflow is person-anchored*. Corporate
parent-child edges only pay off if we also add a company-anchored
matching pass: cluster a sanctioned individual's known business
interests against GLEIF's ownership tree to surface subsidiary
chains. That's separate, ~3-4 hr of pipeline work on top of the
data ingest.

**E — OCCRP Laundromat: deferred.** Multi-session work per the
original estimate. Aleph API client + per-project schema work is
the gating cost.

## Lessons learned (carry to future ingests)

- **The goldenmatch person config has a known blocking pathology on
  common-name + honorific clusters** ("Anthony" at 168k records,
  "Mr Muh..." at 31k, "alexandr" patronymic at 19k). Wider
  scopes OOM the matcher even on the Railway box. Fix is either a
  tighter blocking config (substring:0:10 + country + first-letter
  of surname) or per-source pre-filtering to high-signal
  jurisdictions, as we did for UK PSC (ru/ua/by/cy/kz only).
- **List-match scales much better than dedupe** for cross-source
  identity questions — the asymmetric shape lets blocking pressure
  be carried by the smaller reference set.
- **Adding a corpus that journalists haven't exhaustively mined
  is the single biggest novelty lever.** UK PSC was that lever for
  this case study.

## Disk budget

Railway `/data` volume is at **26.1 GB** post-A (raw inputs +
interim + processed + reports). The 30 GB budget I flagged in the
original roadmap is largely correct — adding GLEIF L2 BODS (~1.1 GB
raw) is fine, FinCEN raw is negligible, but the OCCRP Laundromat
raw + transaction-level processed parquets could push us over.
Future sessions should consider cleaning up the OpenSanctions
default raw (~2.7 GB) post-ingest since the interim parquet is the
operational artifact.

## Honest call on continuing

The substantive novelty win from this initiative — *which corpus
adds the most discovery surface per hour of work* — landed on
**Tier A (UK BODS)**. Going from "the matcher rediscovers what
journalism already published" to "the matcher surfaces 43
sanctioned individuals with specific UK Companies House PSC
declarations" was a step-change.

Tiers C/D/E remain valuable but their payoff per hour is materially
lower than A was. They're best run as targeted follow-ups when a
specific investigative question warrants the matching-pipeline work
(e.g. "is there a sanctioned-individual ↔ GLEIF-LEI-ownership-chain
pattern?" → spin up D as a focused session).

This roadmap is now the source of truth for future ingest work,
including the lessons above.

## Constraints + caveats

- Railway disk volume is shared (`/data` mount). Total free-disk
  budget around 30 GB. UK BODS at 3.7 GB + GLEIF L2 at 1.1 GB +
  existing OS default at 2.7 GB + ICIJ + GLEIF Golden Copy is getting
  tight. Watch `df -h` after each ingest.
- All adapters need the schema-filtered / chunked-write pattern we
  built for OpenSanctions (PR #20). Don't whole-file-load multi-GB inputs.
- Each ingest needs an allowlist entry in
  `src/shellnet/job_server.py` `_ALLOWED_SCRIPTS` plus a redeploy.
- Person-side dedupe still doesn't run cleanly on the full corpus
  (config blocking pathology — PR #11 placeholder filter solved part
  of it). Add new ingests without re-attempting full dedupe; use
  list-match for cross-source surfacing instead.

## What this doesn't include (and why)

- **OpenCorporates bulk.** Blocked on an API key from the user;
  ~200 M company records across 140 jurisdictions; would be the single
  biggest absolute win. Reapply for a researcher key separately.
- **WikiLeaks / random PEP feeds.** Too narrow or non-standard format
  to justify per-source adapter work given current marginal yield.
- **Property registries** (UK Land Registry overseas-entity register
  beyond what BODS covers, NYC ACRIS, etc.). Useful but
  per-jurisdiction format work; consider after A-D.
