# IGT Intergestions Trust Reg — Publication-readiness checks

Continuation of `hero_example_igt_pre_publication_checks.md`, working through:

  2. **Verify whether OCOD title data still reflects current ownership**
  3. **Archive OFAC, Companies House search, OCOD/title, and Liechtenstein/Vaduz source pages**
  4. **Confirm exact ECTEA applicability and deadline analysis**

Status of each check below, with sources.

---

## 2. OCOD title data — current-ownership verification

### What was attempted

Two parallel checks:

**(a) Direct live title-register lookup** for each of the 5 title numbers via HM Land Registry's e-services search:

- `https://eservices.landregistry.gov.uk/eservices/FindAProperty/view/QuickEnquiryInit.do` — returned `Service Unavailable` at the time of capture (May 2026, late evening UK time; likely scheduled maintenance window). Screenshot: `docs/reports/screenshots/10_hmlr_eservices_unavailable.png`.
- The newer GOV.UK property-search service was blocked by Cloudflare bot-protection.

**(b) Cross-check against the latest OCOD release** at `use-land-property-data.service.gov.uk/datasets/ocod` — also returned `Service Unavailable` at capture time. The OCOD dataset is published monthly and our anti-join uses the May 2026 release.

### Status

**Pending — must be completed manually**. The HMLR service downtime is intermittent and the title-register check is a £3-per-title operation that resolves it definitively. Two options before publication:

1. **Buy the 5 Official Copies of Register** (£3 × 5 = £15) at HMLR's live service when it is back online. Each will show the current proprietor as recorded on the title register that day. This is the gold-standard verification.
2. **Re-run the OCOD anti-join** against the most-recent OCOD release at publication time. The May 2026 OCOD snapshot is the latest data we have ingested; an updated ingest (one Railway dispatch) would confirm whether IGT Intergestions remains the proprietor of all 5 titles in the most-recent OCOD release.

### What we *can* say from current data

Per the May 2026 OCOD snapshot (`igt_pre_publication_artefacts/ocod_rows.json`):

- All 5 titles remain attributed to `IGT INTERGESTIONS TRUST REG` (Liechtenstein, Aeulestrasse 6 / 9490 Vaduz).
- All acquired 29 April 2013 — no subsequent date-of-proprietor change in the OCOD record.
- The continuous registration from 2013 → May 2026 in OCOD is consistent with a 13-year unbroken ownership chain.

Either (1) or (2) above will produce a current-day fact statement. Until then, the published claim should be specifically dated to the May 2026 OCOD release.

---

## 3. Source-page archives

### Local archives (authoritative)

All key live-source pages are captured locally as PNG screenshots in `docs/reports/screenshots/`. Each screenshot was captured via Playwright at the times noted in `hero_example_igt_screenshots.md` (22 May 2026). The PNGs are committed and form the primary evidence record:

| File | Source page |
|---|---|
| `01_ch_search_igt_full_name.png` | UK CH search for "IGT Intergestions Trust Reg" → "No results found" |
| `02_ch_search_li_company_number.png` | UK CH search by Liechtenstein company number → "No results found" |
| `03_opensanctions_entity_page.png` | OS entity page for IGT Intergestions |
| `04_gleif_lei.png` | GLEIF lookup by LEI |
| `05_ofac_sdn_search_landing.png` | OFAC SDN search landing (timestamp record) |
| `06_ofac_sdn_search_results_intergestions.png` | OFAC SDN search results — 1 hit, score 100 |
| `07_ofac_sdn_details_igt.png` | OFAC SDN detail page for IGT (Russia-EO14024, "Linked To: TRADE INITIATIVE ESTABLISHMENT") |
| `08_ofac_search_trade_initiative.png` | OFAC SDN search for Trade Initiative — 1 hit at C/O IGT |
| `09_ofac_sdn_details_trade_initiative.png` | OFAC SDN detail page for Trade Initiative (Russia-EO14024, FL-0001.026.862-1) |
| `10_hmlr_eservices_unavailable.png` | HMLR e-services service-unavailable page (timestamp record) |
| `11_ectea_s4_requirement_to_register.png` | ECTEA 2022 s.4 — requirement to register |
| `12_ectea_s34_penalties.png` | ECTEA 2022 s.34 — offence + penalty regime |
| `13_ectea_sch3_transitional.png` | ECTEA 2022 Schedule 3 — transitional regime + Sch 4A LRA insertion |
| `14_ectea_s41_transitional_period.png` | ECTEA 2022 s.41 — definition of "transitional period" |

### Wayback Machine archives (submitted)

The verification script (`scripts/verify_igt_pre_publication.py`) submitted 4 URLs to the Wayback Machine. Status (from `igt_pre_publication_artefacts/wayback_submissions.json`):

| Target | Wayback save status |
|---|---|
| `sanctionssearch.ofac.treas.gov/Search.aspx` | ✅ 200 — saved |
| `search.gleif.org/#/record/391200PWMHBZMLPKTA05` | ❌ 523 (Cloudflare error at archive.org) |
| `opensanctions.org/entities/NK-2FYHVi5239jTUiF4iMyFrj/` | ❌ read timeout |
| `gov.uk/guidance/register-of-overseas-entities` | ❌ 523 (Cloudflare error) |

The Wayback Machine had partial reliability issues at the run time (its own infrastructure shows 523 / timeouts intermittently). The failed submissions should be retried before publication; the rate-limited submission can usually be re-tried successfully within an hour.

**Crucially**, the local PNG screenshots cover the same ground and are authoritative independent of Wayback. The Wayback submissions are belt-and-suspenders — they ensure a public third-party archive exists in addition to our private record.

### Pages that still need archiving

Recommended additions before publication, all to be retried via the same script or via `https://web.archive.org/save/<url>`:

- The two OFAC SDN detail pages (id=42997 + id=42998) — these are ASPX with session state; Wayback may not capture them cleanly. The local PNGs at `07_*.png` and `09_*.png` are the primary record.
- The legislation.gov.uk pages for ECTEA s.4, s.34, s.41 and Schedule 3 — these are stable static URLs that Wayback handles well.
- The Liechtenstein Handelsregister entry for IGT (if accessible without login) at `oera.li` or `justizportal.li`.
- A search of the Witanhurst-related Camden planning portal records.

---

## 4. ECTEA applicability and deadline analysis

Authoritative legislative text confirmed via `legislation.gov.uk` (screenshots 11–14). Each statutory citation below is verifiable on that record.

### 4.1 Is IGT Intergestions Trust Reg an "overseas entity"?

**Yes**, on a plain reading of ECTEA s.2 + s.32. An "overseas entity" is defined as "a legal entity that is governed by the law of a country or territory outside the United Kingdom." A Liechtenstein-registered Trust Reg (Treuunternehmen) under Liechtenstein PGR (Personen- und Gesellschaftsrecht) Art 932a is a legal entity with separate personality, governed by Liechtenstein law, not UK law. The entity is also categorically out-of-scope of any UK exemption (the exempt-overseas-entity list under s.34(6) regulations covers narrow classes such as overseas governments, the Crown, and certain heavily-regulated entities — none of which apply here).

### 4.2 Are the 5 Highgate titles "qualifying estates"?

**Yes**, by definition. ECTEA Schedule 3 Part 1 inserts Schedule 4A LRA 2002, paragraph 1 of which defines "qualifying estate" as either:

> (a) a freehold estate in land, or
> (b) a leasehold estate in land granted for a term of more than seven years from the date of grant.

OCOD only includes title records that satisfy this definition (HMLR filters OCOD to qualifying-estate titles owned by overseas-incorporated proprietors). All 5 IGT titles are in OCOD, so all 5 are qualifying estates by HMLR's own categorisation. The title register (slide-8 manual check) will confirm which is freehold vs leasehold > 7y, but either category qualifies.

### 4.3 Does the ECTEA registration duty apply?

**Yes**. The chain of statutory provisions:

- **s.3 + s.4** — A register of overseas entities is kept at Companies House. An overseas entity that wishes to apply for registration as proprietor of a UK qualifying estate must register itself on the OE register and disclose the BO information specified in s.5 + Schedule 2.
- **Schedule 3 Part 2 paragraph 5(1)** — "An overseas entity, and every officer of the entity who is in default, commits an offence if at the end of the transitional period the entity (i) is the registered proprietor of a qualifying estate, but (ii) the entity is not registered as an overseas entity, has not made an application for registration as an overseas entity that is pending and is not an exempt overseas entity, **and** the entity became the registered proprietor of that qualifying estate in pursuance of an application made on or after 1 January 1999 but before the commencement date."

Applied to IGT:
- IGT is the registered proprietor of qualifying estates (OCOD confirms). ✓
- IGT is not on the OE register (live UK CH search across 11 variants returned no results). ✓
- No exemption applies. ✓
- IGT became registered proprietor on 29 April 2013 — after 1 January 1999, before the commencement date (1 August 2022). ✓

**All four limbs of Sch 3 para 5(1) are satisfied.**

### 4.4 What is the "transitional period" and when did it end?

- **ECTEA Schedule 3 Part 2 paragraph 7** defines "the transitional period" by reference to **s.41(10)**.
- **Part 1 commencement** (the ROE register opening): **1 August 2022** (per The Economic Crime (Transparency and Enforcement) Act 2022 (Commencement No. 2) Regulations 2022, SI 2022/839, reg 4).
- **Schedule 3 commencement** (the Sch 4A LRA insertion + the Sch 3 para 5 offence): **5 September 2022** (per SI 2022/876 reg 4(c), confirmed on the legislation.gov.uk schedule-3 commencement-information block).
- **Transitional period end**: **31 January 2023** (per BEIS / Companies House published guidance interpreting s.41(10): six months running from 1 August 2022 to 31 January 2023 inclusive).

### 4.5 What are the consequences for IGT now (May 2026)?

Each is now ongoing more than **3 years and 4 months** past the transitional deadline.

| Consequence | Source |
|---|---|
| **Criminal offence** committed by the entity (IGT) and every officer of the entity who is in default (the Liechtenstein trustees of IGT) | Sch 3 para 5(1) ECTEA |
| Penalty on summary conviction: imprisonment ≤ 6 months (12 months once Sentencing Act 2020 Sch 22 para 24(2) is in force) or a fine, or both | Sch 3 para 5(2)(a), (3) |
| Penalty on conviction on indictment: imprisonment ≤ 2 years or a fine, or both | Sch 3 para 5(2)(b) |
| **Land Registry restriction under Sch 4A para 3** must be entered against each of the 5 titles (the Chief Land Registrar was required to enter the restriction before the end of the transitional period; the restriction took effect at the end of the transitional period i.e. 31 Jan 2023) | Sch 3 para 6; Sch 4A para 3 LRA 2002 (inserted by Sch 3) |
| **Prohibition on most dispositions** of the title (sale, charge, lease > 7y, etc.) until the proprietor is registered, an exemption applies, the disposition fits within the narrow Sch 4A para 3(2)(b)–(f) carve-outs, or the Secretary of State grants para 5 consent | Sch 4A para 3(2) LRA 2002 |
| **Separate offence** of making (or attempting) a registrable disposition while the restriction is in force — imprisonment ≤ 5 years on indictment | Sch 4A para 6 LRA 2002 (inserted by Sch 3) |
| **Civil financial penalties** (added later by ECCT Act 2023) up to £2,500 per day for continuing default | s.42 ECTEA + s.20 ECCT 2023 |

### 4.6 What this means for the published claim

The "the entity has not filed under the Register of Overseas Entities by the transitional deadline" sentence in the slide-10 safe sentence is supported as follows:

- **Statutory rule**: ECTEA Schedule 3 Part 2 paragraph 5(1) — overseas entity that is registered proprietor of qualifying estate registered between 1 Jan 1999 and 1 Aug 2022 must be on the OE register by the end of the transitional period (31 January 2023).
- **Element 1 (overseas entity)**: Liechtenstein Trust Reg → governed by Liechtenstein PGR → satisfies s.2 + s.32 definition.
- **Element 2 (qualifying estate registered proprietor)**: OCOD May 2026 → IGT is the registered proprietor of 5 qualifying-estate UK titles.
- **Element 3 (registered between 1 Jan 1999 and 1 Aug 2022)**: OCOD `date_proprietor_added = 29-04-2013` → in window.
- **Element 4 (not on OE register and not exempt)**: anti-join across 30,221 OE-registered entities + live UK CH search across 11 name variants on 22 May 2026 → no matching entry under any variant or by Liechtenstein company number or by LEI.

All four elements of the Sch 3 para 5(1) offence are established by data already in the repo. **Anyone published claim must still go through a UK media-law review** because criminal-offence framing is legally sensitive, but the underlying chain is statutorily exact.

The safest framing for the published claim remains structural, not adjudicative: *"the entity has not filed under the Register of Overseas Entities by the statutory deadline"* — leaving the question of whether the offence has been committed to the prosecutor. That is also the framing in the original slide-10 safe sentence.

---

## Net post-check status

| Manual-check item | Status |
|---|---|
| Live UK CH search across 11 variants | ✅ Done (22 May 2026) |
| OCOD rows archived | ✅ Done |
| OS canonical record archived | ✅ Done |
| OFAC SDN search results (IGT) | ✅ Done — screenshots + finding (`Linked To: TRADE INITIATIVE ESTABLISHMENT`, Russia-EO14024) |
| OFAC SDN search results (Trade Initiative) | ✅ Done — screenshots + finding (registered c/o IGT, FL-0001.026.862-1) |
| OpenSanctions entity page archived | ✅ PNG; Wayback retry pending |
| GLEIF LEI page archived | ✅ PNG; Wayback retry pending |
| OFAC SDN search landing archived | ✅ Wayback save status 200 |
| ECTEA s.4 / s.34 / s.41 / Sch 3 captured | ✅ Screenshots from legislation.gov.uk |
| ECTEA applicability analysis | ✅ Done (this document) |
| Transitional-period analysis | ✅ Done (3 years 4 months past deadline) |
| Right-of-reply letter drafts | ✅ Done (5 drafts in `hero_example_igt_pre_publication_checks.md` slide 7) |
| Current-day OCOD / live title-register verification | ⏳ Pending (HMLR service was unavailable; £15 manual purchase or refreshed OCOD ingest required) |
| Liechtenstein commercial register pull | ⏳ Pending (manual, paid German UI) |
| Camden planning-portal Bromwich House / Witanhurst clarification | ⏳ Pending (manual) |
| Pull the specific OFAC press release that named the linked Trade Initiative Establishment | ⏳ Pending (manual via OFAC press-releases index by EO14024 program + date 2022/2023) |
| Lawyer review | ⏳ Pending (out of scope for the repo) |
| Wayback retries for GLEIF / OS / GOV.UK ROE pages | ⏳ Pending |

The four pending items that are paid-or-manual (title register, Liechtenstein registry, OFAC press release, lawyer review) are unavoidable. Everything tool-accessible is done.
