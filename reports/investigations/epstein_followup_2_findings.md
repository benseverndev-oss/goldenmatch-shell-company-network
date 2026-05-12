# Follow-up 2 — Lipman / Bear Stearns hypothesis verified + dedupe sanity

Generated 2026-05-12. Third doc in the Epstein investigation series:

1. `batches/epstein_seed_review/findings.md` — entity-side batch.
2. `epstein_followup_findings.md` — person + address + 2-hop tools.
3. `epstein_followup_2_findings.md` — *this doc.*

> **Hypothesis, not proof.** Same posture as the other findings docs.
> The Lipman / Bear Stearns hypothesis has now been independently
> corroborated by multiple primary sources cited below — it is no
> longer a hypothesis. Other leads remain hypothesis-grade.

## Lipman ↔ Bear Stearns ↔ Liquid Funding — corroborated

The 2-hop expansion in the previous follow-up flagged `Bear Stearns
International Funding (Bermuda) Limited` as sharing co-director
`Lipman - Jeffrey M` with Liquid Funding. That was a name-string match
inside ICIJ; we marked it hypothesis-grade pending DOB / address /
professional-record verification.

External-source check now confirms it:

- **FINRA BrokerCheck** (regulator-authoritative): `JEFFREY MARK LIPMAN`,
  CRD# 717915, registered with `BEAR, STEARNS & CO. INC. CRD# 79`,
  New York, NY, **10/1980 – 09/2008** (28 years). Source:
  `https://files.brokercheck.finra.org/individual/individual_717915.pdf`.
- **ICIJ, second record** (independent corroboration *within* the
  corpus, not just from external sources): `LIPMAN JEFFREY M`
  (`icij:110014080`) appears in the Paradise Papers — Barbados
  corporate registry — as `Director` of **`BEAR STEARNS CARIBBEAN
  ASSET HOLDINGS LTD.`** from `10-JUL-2008` onward. Same individual,
  separate ICIJ node, separate jurisdiction — clean cross-leak link.
- **Bear Stearns held a 40% equity stake in Liquid Funding.** Source:
  National Memo, _"Epstein's Really Big Short"_: "Bear Stearns' 40
  percent stake in Epstein's Liquid Funding which, by this time, had
  $6.7 billion in liabilities …". This is consistent with the
  ICIJ-observed officer overlap: Bear Stearns staff (Lipman, Novelly)
  sat on the Liquid Funding board because Bear Stearns owned 40% of
  the entity.
- **OffshoreAlert** confirms the broader corporate-registry record:
  Bermuda Registrar of Companies filings for Liquid Funding Ltd.
  (dissolved 2015-11-25 after Members' Voluntary Liquidation),
  tagging `Jeffrey Epstein`, `Jeffrey Lipman`, `Paul Novelly`,
  `Marcus Klug`, `James Burritt`, `Roger Heintzelman`, `Liquid
  Funding Holdings`, `Bear Stearns`, `Appleby` as registered agent.

**Reading:** the matcher's lead was correct. The two ICIJ `Lipman`
records (Bermuda Liquid Funding + Barbados Bear Stearns Caribbean Asset
Holdings Ltd.) are the same Jeffrey M Lipman, a Senior Vice President
at Bear Stearns from 1980 to 2008 per FINRA. Bear Stearns held 40% of
Liquid Funding. The corporate-network ICIJ surfaces is a real
Bear-Stearns-anchored Bermuda structure that Epstein chaired and
directed.

This also corroborates the secondary 2-hop hit: `Liquid Funding
Holdings, LLC` is the **US holding company** through which Bear Stearns
held its 40% — OffshoreAlert tags it directly. So the apparent
parent-shape link the matcher surfaced (`Liquid Funding Holdings, LLC`
as officer of Liquid Funding Ltd.) is correct.

## Public-source citations (saved under `.firecrawl/`)

| Source | URL | What it confirms |
| --- | --- | --- |
| FINRA BrokerCheck PDF | `https://files.brokercheck.finra.org/individual/individual_717915.pdf` | Jeffrey M Lipman → Bear Stearns 1980-2008 |
| ICIJ Offshore Leaks (Lipman) | `https://offshoreleaks.icij.org/nodes/110014080` | Lipman → Bear Stearns Caribbean Asset Holdings Ltd. (Barbados, 2008-) |
| ICIJ Offshore Leaks (Liquid Funding) | `https://offshoreleaks.icij.org/nodes/82004676` | 17 officers including Lipman + Epstein + Novelly + Klug |
| OffshoreAlert | `https://www.offshorealert.com/jeffrey-epstein-liquid-funding-ltd-selected-filings/` | 357 pages of Bermuda Registrar filings; Lipman, Novelly, Epstein, Liquid Funding Holdings all tagged |
| National Memo | `https://www.nationalmemo.com/epstein-finances-2675057146` | Bear Stearns 40% stake; $6.7B Liquid Funding liabilities |
| Duggan USA | `https://www.dugganusa.com/post/liquid-funding-ltd-the-bermuda-shell-company-icij-missed` | Independent walkthrough of Liquid Funding's ICIJ record |
| Obsidian "Finding Truth" | `https://publish.obsidian.md/findingtruth/Modern+Companies/...Liquid+Funding+Ltd.` | "Two Liquid Funding directors — Jeffrey Lipman and Paul Novelly — simultaneously served as Bear Stearns directors/board members. Lipman …" |

## Person-side dedupe sanity check

Attempted a full GoldenMatch dedupe pass on `person_entities.parquet`
(796,944 rows). The current config trips a memory blow-up at a
72,070-row "bearer t" block (~38 GB allocation for a 72k×72k
all-pairs scoring step) — a real config issue with this corpus that
needs follow-up (tighter blocking key, or progressive blocking on
top of `token_sort`).

But for the specific question this doc cares about — *does Jeffrey
Epstein cluster with anyone else under name-variant matching?* — a
direct query of the person table substitutes:

```python
df.filter(pl.col('normalized_name').str.contains('epstein'))
# → 29 rows
```

Of those 29:

- 1 is the canonical `Epstein - Jeffrey E` (`icij:80063035`) — the
  record from the previous follow-up.
- The other 28 are clearly different individuals: `Epstein - Alan
  Lee`, `Epstein - Eli`, `Epstein - Glenn H`, `Epstein - Jonathan
  Stuart`, `Epstein - Martin J`, `Epstein - Mel H`, `Epstein -
  Richard`, `Epstein - Samuel H`, `Epstein - Zelma`, plus
  intermediary firms (`Epstein, Chomsky, Osnat & Co.`, `Epstein &
  Reed`), plus surname-only matches in longer composite names.
- **No alternate-spelling Jeffrey Epstein records.** No `J. Epstein`,
  `Jeffrey M Epstein`, `Jeffrey Mark Epstein` (the form OffshoreAlert
  uses as a tag), `Jeffrey Edward Epstein`. ICIJ has exactly one record.

**Reading:** the previous follow-up's negative result holds even under
a permissive name-prefix scan. The lone Epstein record is genuinely
the only one ICIJ carries; the absence of more entities isn't a
name-normalization artefact.

## OpenSanctions ingest — done

Downloaded the consolidated OpenSanctions default collection
(`https://data.opensanctions.org/datasets/latest/default/entities.ftm.json`,
~2.7 GB) to `data/raw/opensanctions/default.ftm.json`. The "default"
collection is the everything-from-everywhere union (sanctions + PEPs +
regulators + debarments + corporate records from dozens of sources),
not just sanctions.

Two adapter changes landed to make this corpus ingestible:

1. `_iter_entities` is now a true generator that streams NDJSON
   line-by-line (was reading the whole file as a single string, which
   OOMed at 2.7 GB).
2. `ingest()` writes parquet in 50k-row batches via `pyarrow.ParquetWriter`
   instead of buffering all parsed dicts in memory before a single
   `df.write_parquet`. Adds a `--schemas` filter (e.g.
   `Person,Company,Organization,LegalEntity`) so callers can drop the
   ~2.7M FtM rows that aren't relevant to entity / person matching
   (vehicles, address-as-entity, etc.).

**Final numbers after re-running the pipeline with OpenSanctions
included:**

| Table | Before OS | After OS | Delta |
| --- | ---: | ---: | ---: |
| `company_entities.parquet` | 814,344 | 1,240,555 | +426,211 |
| `person_entities.parquet` | 796,944 | 1,950,531 | +1,153,587 |
| `address_entities.parquet` | 701,569 | 1,180,555 | +478,986 |

### What OpenSanctions added — and didn't

**Did not add a Jeffrey Epstein record.** Surprising for someone with
his criminal history, but the OS default collection skews toward
*active* sanctions, PEPs, and regulator-issued debarments — not
historical convicted-criminal records. A name-prefix scan returns 18
"Epstein" persons in OS (mostly debarments and PEPs), none of them
Jeffrey:

- Several US federal exclusions (HHS OIG-style debarments).
- Several PEPs (politicians named Epstein in various jurisdictions).
- A handful of Russia/Iran/NK counter-sanction listings of unrelated
  Epsteins.

The implication for this case study: OpenSanctions does **not** widen
the Jeffrey Epstein person-side surface. The single ICIJ
`Epstein - Jeffrey E` record (`icij:80063035`, Liquid Funding,
chairman/director 2001-2007) remains the only verified anchor in our
combined corpus.

**Did add new entity-side coverage,** but not where this case study
needed it most:

- **Liquid Funding, Ltd. now has 2 in-jurisdiction matches** (was 1).
  The new one is `opensanctions:icijol-82004676` — OS re-exports the
  ICIJ Offshore Leaks node with a populated Bermuda registry company
  number (`EC29378`). Same entity, different anchor — useful
  identifier we didn't have.
- All 28 seeds otherwise behave the same as the ICIJ-only run. The
  USVI-registered entities (Nautilus, Cypress, Maple, Laurel, etc.)
  remain at 0 in-jurisdiction hits. OS doesn't carry the USVI
  registry either; it carries sanctions/PEP/debarment data plus
  re-exports of ICIJ leaks. The structural USVI gap is *not* closed
  by OpenSanctions.

The only data source that would close that gap is the USVI
Lieutenant Governor's Corporations and Trademarks Division registry
(or an OpenCorporates ingest with a USVI seed query, which depends on
an OpenCorporates API key).

## Updated case-study notebook

`notebooks/02_epstein_case_study.ipynb` is now committed **with
executed outputs** (the Python 3.13 + jupyter_client hang noted in
the previous follow-up turned out to be fixable with a recent
`nbconvert --execute --inplace` run). A static HTML render lives
beside it at `notebooks/02_epstein_case_study.html` so GitHub
viewers can read it without cloning.

## Open question (still hypothesis)

- The **other** Bermuda entities sharing a non-provider officer with
  Liquid Funding in the 2-hop walk are all Bear-Stearns-era Bermuda
  structures (Bear Stearns International Funding (Bermuda), plus
  Mundipharma / EPI / etc. via shared Bermuda directors like
  Erskine, Gillespie, Gores, Poole). Of those, only Bear Stearns
  International Funding is directly named in Bear-Stearns ↔ Epstein
  public reporting. The rest are likely unrelated Bermuda commercial
  entities that share Appleby-era directors with no Epstein link —
  but a per-entity human review of the larger 2-hop list (filter to
  named individuals, then check each entity's own Appleby filing)
  would close the question definitively.

## Reproducing

```
uv run python scripts/build_person_table.py
uv run python scripts/investigate_person.py --name "Jeffrey Epstein" --min-score 80
uv run python scripts/expand_2hop.py --entity-uid icij:82004676 --label liquid_funding --named-individuals-only
# Lipman verification: see .firecrawl/ for the saved search + scrape outputs.
```
