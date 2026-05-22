# US appendix: why the methodology doesn't transplant (yet)

Fourth piece of the GoldenMatch case-study package
([overview](00_package_overview.md)). The three UK case studies
demonstrate that joining ICIJ Offshore Leaks + HM Land Registry
OCOD + UK Companies House Register of Overseas Entities produces
high-signal findings about overseas-company-owned UK property.
A reasonable follow-up question: *does the same pipeline work in
the US?*

We ingested the largest US municipal property-records dataset
available — NYC ACRIS — and ran the same name-matching join. The
finding is **negative**, and the *reason* it's negative is itself
publishable: the US lacks the regulatory infrastructure that makes
the UK join work.

**Target audience:** OECD beneficial-ownership review teams, EU
6AMLD Article 30 review, US Treasury OFAC, US Treasury FinCEN, US
Congressional Financial Services Committee, NY Attorney General.
**Format:** Not a video. A methodology appendix / discussion paper.
Pairs with the three UK video scripts.

---

## 1. The hypothesis

The three UK case studies (128 Ebury Street, petrol forecourts via
Jersey, Channel Islands hubs) all share a structural template:

```
   ICIJ Offshore Leaks                  HM Land Registry OCOD
   (Panama / Paradise / Pandora    +    (Overseas Companies
    Papers — leaked offshore-company    Ownership Data —
    name lists)                          May 2026 release)

                          +

   UK Companies House Register of Overseas Entities
   (mandatory beneficial-owner disclosure since the 2022
    Economic Crime Act — names, DOBs, nationalities, addresses)

                          ↓

   Joined output:
   - Specific UK property titles
   - Held by named offshore companies in leaked corpora
   - With declared natural-person beneficial owners
   - Disambiguated by DOB / nationality / declared address
```

The question for the US: *can we reproduce this with US data?*

## 2. The dataset we ingested

The closest US-side equivalent of HM Land Registry OCOD is the
**NYC Department of Finance ACRIS** (Automated City Register
Information System). Free and public via NYC Open Data. Three
datasets joined on `document_id`:

- **acris_master** — every recorded NYC document (1966–present)
- **acris_parties** — grantor + grantee names per document
- **acris_legals** — property addresses per document

Ingest results (Railway-side, ~30 minutes):

| Dataset | Rows | Size |
| --- | ---: | ---: |
| Master | 16,987,166 | 193 MB parquet |
| Parties | 46,311,925 | 1.37 GB parquet |
| Legals | 22,620,641 | 316 MB parquet |

Filtered to deed-document types only (transfers, not mortgages/
refinances): **5,770,120 grantee party rows** to scan.

## 3. The join — what it produced

We ran the same name-matching join the UK case studies use, against
two cross-reference sources:

| Cross-reference source | Total entities | NYC ACRIS deed-grantee name-matches |
| --- | ---: | ---: |
| ICIJ Offshore Leaks (all leaks) | ~810k entities | **5,371 rows** (1,510 distinct names) |
| OpenSanctions sanctioned persons (OFAC SDN + EU/UN/UK lists) | ~120k persons | **3,472 rows** (1,105 distinct names) |

Surface-level: that's 8,843 potential leads. The UK methodology
would treat each as a starting point for the next probe.

## 4. Why those numbers are noise

A sample of the top ICIJ name-matches:

```
WANG, JIANHUA          → ICIJ "WANG JIANHUA"
LI, HONG (×3 documents) → ICIJ "LI Hong"
LIU, SHUO              → ICIJ "LIU Shuo"
CHEN, LONG / RONG / MEI LING / CHEN  → 4 separate "Chen"
GU, YU                 → ICIJ "GU Yu"
HONG, YI               → ICIJ "HONG YI"
MA, XIAOHUA            → ICIJ "Ma Xiaohua"
```

A sample of the top OFAC-SDN matches:

```
SINGH, JATINDER        → SDN "SINGH JATINDER"
AHMAD, ALI             → SDN "Ahmad Ali"
RAHMAN, MIZANUR (×3)   → SDN "Rahman Mizanur"
RANA, MOHAMMAD         → SDN "RANA MOHAMMAD"
MOHAMED, KHALED        → SDN "MOHAMED KHALED"
KING, STEPHEN          → SDN "KING STEPHEN"
```

These are **extremely common names** in their cultural origins —
Chinese for the ICIJ matches, South Asian / Arabic / Anglo for the
SDN matches. NYC's immigration-heavy buyer pool means these names
appear in property-purchase records by the hundreds. The same
names appear in global ICIJ entries and OFAC SDN lists for
unrelated individuals on the other side of the world.

**The defamation guard the UK pipeline uses** (`Person` schema,
≥2 tokens, ≥8 characters) is not strict enough at NYC scale.
Without disambiguators — date of birth, nationality, full
correspondence address — every common name produces dozens of
false-positive cross-matches.

## 5. Address concentration — also disappointing

The UK case studies' breakthrough was the *address-concentration*
analysis: 128 Ebury Street administering 119 UK titles, 1 Royal
Plaza Guernsey 3,697 titles, etc. We ran the same address-
concentration analysis on the NYC ACRIS grantee correspondence
addresses. The top hubs:

| n_rows | Address | What it actually is |
| ---: | --- | --- |
| **26,110** | The Manhattan Club / 200 West 56th St NY 10019 | The well-documented timeshare property (FTC v Manhattan Club, 2014-2017) — each timeshare unit is its own deed |
| 3,998 | C/O Hilton Resorts Corporation, Orlando | Hilton timeshare buyers' corporate return-address |
| 1,800+ | 147-20 / 147-24 Hillside Avenue, Jamaica, Queens | Immigration-heavy postcode — likely a legal-services concentration |
| 1,800+ | 26 Federal Plaza, New York | The federal building (immigration courts) — return address on many recordings |
| 963 | 425 Walnut Street, Cincinnati | Western & Southern Financial Group HQ — institutional RE purchases |
| 945 | 199 Lee Avenue, Brooklyn 11211 | Williamsburg Hasidic-community holding entity |
| 668 | 3 Court Square / 23-15 44th Drive, LIC | Major Long Island City commercial building |
| 644 | 15 Broad Street, New York 10005 | Wall Street (former NYSE neighbour) |

**None of these are offshore-administration hubs of the kind the
UK methodology surfaces.** The biggest concentration is a
documented domestic timeshare property. The others are corporate
return addresses, immigration filing addresses, or legitimate
commercial buildings.

## 6. The actual finding — regulatory infrastructure

This is **not a pipeline failure**. It's a **regulatory-data
failure**. The UK methodology relies on three layers of data, only
two of which exist in the US equivalent:

| Layer | UK | US (NYC ACRIS equivalent) |
| --- | --- | --- |
| **Property records** | HM Land Registry OCOD (foreign owners only, 365k rows, deduplicated by title, includes country of incorporation) | NYC ACRIS (all documents, 46M party rows, no country/disambiguation, includes mortgages + releases as separate rows) |
| **Offshore-leak corpora** | ICIJ (same as US) | ICIJ (same as UK) |
| **Beneficial-owner disclosure** | UK Companies House Register of Overseas Entities (2022 Economic Crime Act) — mandatory, public, includes names + DOBs + nationalities + addresses | **None at federal level.** Delaware refuses to publish LLC beneficial owners; NYC ACRIS has no BO disclosure layer; FinCEN's CTA-mandated BO database is non-public |

**The 2022 UK Economic Crime Act is the load-bearing piece.**
Without it, the UK join produces the same noise the US join does.

## 7. What would fix the US side

Three specific regulatory changes would make a US version of this
methodology possible:

### (a) Publish the FinCEN CTA beneficial-ownership database

The 2021 Corporate Transparency Act established a beneficial-owner
registry at FinCEN, but the database is closed to the public — only
law enforcement and certain financial institutions have access. If
the FinCEN BO data were made public on the UK ROE model, the US
join would work *immediately*.

### (b) Publish a federal property-ownership aggregator

US property records are county-by-county. A federal aggregator on
the model of HM Land Registry OCOD — even just for foreign owners —
would eliminate the need to ingest hundreds of county recorders
separately. The 2018 FinCEN Geographic Targeting Orders are a
partial start (covering all-cash high-value residential purchases
in ~12 metros) but the data is not public and the coverage is
narrow.

### (c) Delaware LLC registry transparency

Delaware is the most-used US state for LLC incorporation
(2.2M+ LLCs). Its registry does not publish beneficial owners or
even member lists. Other US states (Nevada, Wyoming) have similar
opacity. EU 6AMLD-style mandatory BO disclosure for US LLCs would
close the largest single data gap.

## 8. Comparison table — UK vs US data availability

| Question | UK | US |
| --- | --- | --- |
| Can we list every property owned by a foreign company? | **Yes** (OCOD, free, quarterly) | No (county-by-county; partial via NYC ACRIS) |
| Can we get the beneficial owner of any foreign-incorporated property holder? | **Yes** (ROE, free, mandatory since 2022) | No (FinCEN CTA data is non-public) |
| Can we cross-reference offshore-leak corpora to property holdings? | **Yes, in 5 minutes of compute** | Partial — names match but disambiguation fails |
| Can we identify "hub" administrative addresses? | **Yes** (128 Ebury, 1 Royal Plaza, 26 New Street...) | No useful signal — biggest hub is a timeshare scandal |

## 9. Recommended publication framing

This appendix should ship *alongside* the three UK case studies in
the package, framed as:

> "We applied the same pipeline to the largest available US municipal
> property-records dataset — NYC ACRIS, 46 million party rows. The
> result is noise-dominated. The reason is not the pipeline; it's
> the absence of a US equivalent of the UK 2022 Economic Crime Act's
> beneficial-owner disclosure layer. The pipeline finds what the
> regulator chooses to disclose. The OECD's beneficial-ownership
> review, the EU's 6AMLD Article 30 review, and any US Congressional
> committee considering Corporate Transparency Act amendments may
> find this useful evidence that *transparency requires both the
> data layer and the disclosure layer*."

This is a stronger argument for the UK regulatory model than a
forced US case study would be. The package's overall claim
becomes:

> "The same open-source pipeline produces high-signal investigative
> output in the UK (where post-2022 regulation discloses BO data)
> and noise in the US (where federal-level BO data remains
> non-public). The data join is cheap; the regulatory disclosure is
> the bottleneck."

---

## Reproducibility

The exact data, scripts, and probe outputs are bundled in
`cluster_us_methodology_appendix_bundle.zip`:

- `probes/nyc_acris_offshore.json` — the full probe output
- `probes/us_angles.json` — the SEC 13D/G + sanctioned-person cross-check
- `source_code/probe_nyc_acris_offshore.py` + `scripts/ingest_nyc_acris.py`
- `source_code/probe_us_angles.py`
- `source_code/src/shellnet/sources/nyc_acris.py`
- This appendix document

All claims sourced. Every number above is reproducible from the
included parquet outputs.
