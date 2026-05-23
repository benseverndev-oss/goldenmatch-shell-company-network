# IGT Intergestions Trust Reg — Live-source screenshots

Captured by Playwright on 22 May 2026 against the live public sources. Each PNG in `docs/reports/screenshots/` is the full-page screenshot of the page described below at the time of capture; the corresponding evidence claim is what the screenshot supports.

## Index

| # | File | URL captured | What it shows |
|---:|---|---|---|
| 01 | `01_ch_search_igt_full_name.png` | `find-and-update.company-information.service.gov.uk/search/companies?q=IGT+Intergestions+Trust+Reg` | UK Companies House live company search for the full entity name returns **"No results found"**. The fallback suggestions returned (`PROVENTUS TREUHAND UND VERWALTUNG AG`, `BRIGHTSTAR LOTTERY UK BIDCO LIMITED`, etc.) are unrelated Liechtenstein OE-registered entities and the unrelated IGT-lottery company. |
| 02 | `02_ch_search_li_company_number.png` | `find-and-update.company-information.service.gov.uk/search/companies?q=FL00015130568` | Same CH search by Liechtenstein company number `FL00015130568` returns **"No results found"** with zero fallback. Confirms no UK Companies House entry corresponds to the Liechtenstein incorporation number. |
| 03 | `03_opensanctions_entity_page.png` | `opensanctions.org/entities/NK-2FYHVi5239jTUiF4iMyFrj/` | OpenSanctions canonical page for **"IGT Intergestions Trust Reg."**. Confirms the entity exists in OS with the identifiers, datasets, and topics referenced in our local artefacts. |
| 04 | `04_gleif_lei.png` | `search.gleif.org/#/record/391200PWMHBZMLPKTA05` | GLEIF (Global Legal Entity Identifier Foundation) lookup for the LEI `391200PWMHBZMLPKTA05` referenced in our OS record. |
| 05 | `05_ofac_sdn_search_landing.png` | `sanctionssearch.ofac.treas.gov/` | US Treasury OFAC SDN search landing page (SDN List last updated 21 May 2026). Captured for the timestamp record. |
| 06 | `06_ofac_sdn_search_results_intergestions.png` | OFAC SDN search results for `Intergestions` (minimum name score 100) | **Lookup Results: 1 Found** — `IGT INTERGESTIONS TRUST REG.`, Aeulestrasse 2, Entity, Program **RUSSIA-EO14024**, List **SDN**, Score 100. |
| 07 | `07_ofac_sdn_details_igt.png` | `sanctionssearch.ofac.treas.gov/Details.aspx?id=42998` | OFAC SDN entity-detail record for **IGT INTERGESTIONS TRUST REG.**. Confirms: Type Entity; List SDN; Program RUSSIA-EO14024; **Remarks: (Linked To: TRADE INITIATIVE ESTABLISHMENT)**; Registration Number `FL-0001.513.056-8` (Liechtenstein); LEI `391200PWMHBZMLPKTA05`; Identification Number `JB8LS5.99999.SL.438`; Organization Established Date **20 Aug 1993**; Addresses `Aeulestrasse 2, Vaduz 9490` and `Aeulestrasse 30, Vaduz 9490`. |
| 08 | `08_ofac_search_trade_initiative.png` | OFAC SDN search for `Trade Initiative Establishment` | **Lookup Results: 1 Found** — `TRADE INITIATIVE ESTABLISHMENT`, address **"C/O IGT Intergestions Trust Reg., Aeulestrasse 30"**, Entity, Program RUSSIA-EO14024, SDN, Score 100. |
| 09 | `09_ofac_sdn_details_trade_initiative.png` | `sanctionssearch.ofac.treas.gov/Details.aspx?id=42997` | OFAC SDN entity-detail record for **TRADE INITIATIVE ESTABLISHMENT**. Confirms: Type Entity; List SDN; Program RUSSIA-EO14024; Registration Number `FL-0001.026.862-1` (Liechtenstein); Organization Established Date **27 Nov 1968**; Address `C/O IGT Intergestions Trust Reg., Aeulestrasse 30, Vaduz 9490, Liechtenstein`. |

## Major addition to the evidence chain

The OFAC details pages establish a fact pattern stronger than the case study previously documented:

1. **IGT INTERGESTIONS TRUST REG.** is OFAC-listed as **"Linked To: TRADE INITIATIVE ESTABLISHMENT"** under the **RUSSIA-EO14024** sanctions program (Executive Order 14024 — the foundational Biden EO for Russia-related designations after the February 2022 invasion of Ukraine).
2. **TRADE INITIATIVE ESTABLISHMENT** is also OFAC SDN-listed, on the same RUSSIA-EO14024 program, registered at **"C/O IGT Intergestions Trust Reg., Aeulestrasse 30, Vaduz"**.
3. The two entities share Liechtenstein address-space (Aeulestrasse 2 / 30, Vaduz 9490). Trade Initiative was established 27 November 1968; IGT was established 20 August 1993 — Trade Initiative is the older entity, IGT is its corporate-services-of-record.
4. IGT is the registered proprietor of five UK Land Registry titles in Highgate, London (since 29 April 2013), including Bromwich House at 1 Witanhurst Lane and 79 Highgate West Hill.
5. The UK Companies House Register of Overseas Entities has **no filing** for IGT under any of 11 tested name variants, including the Liechtenstein company number.

## What this still does NOT establish

- **Who controls TRADE INITIATIVE ESTABLISHMENT**. The OFAC remarks field on the Trade Initiative detail page is empty. The OFAC press release that designated these entities is the next document to obtain — it will name the beneficial-owner rationale.
- **Whether Bromwich House at 1 Witanhurst Lane is part of the Witanhurst estate** versus an adjacent/independent building.
- **Whether either entity has been UK-sanctioned separately by OFSI**, as opposed to being on the US OFAC list only.

The OFAC press release pull (slide 8 item #1 of the original evidence chain) is now an even higher priority — it will name the underlying target individual or family whose assets these Liechtenstein vehicles hold.

## Updated safe sentence

The slide-10 safe sentence in `hero_example_igt_intergestions.md` can now be extended (still all data-supported, no overclaim):

> "A Liechtenstein-registered trust enterprise on the United States Treasury OFAC sanctions list — `IGT Intergestions Trust Reg.`, Liechtenstein company number `FL-0001.513.056-8`, designated under the Russia-related Executive Order 14024 programme as a linked entity of another OFAC-sanctioned Liechtenstein establishment, `Trade Initiative Establishment` (registered c/o the same Vaduz address as IGT) — has been recorded since April 2013 as the proprietor of five UK Land Registry titles clustered on Highgate West Hill in north London, including a building called Bromwich House at 1 Witanhurst Lane (N6 6LT). The UK's Register of Overseas Entities — which since 2022 has required every overseas-incorporated owner of UK property to disclose its beneficial owners by 31 January 2023 — contains no filing under the entity's name or any common variant of it. A live search of the UK Companies House register conducted on 22 May 2026 against eleven name variants, the Liechtenstein company number, and the global LEI returned no matches."
