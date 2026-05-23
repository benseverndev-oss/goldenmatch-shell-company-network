# IGT Intergestions Trust Reg — Evidence Chain

One-page evidence dossier for the hero example identified in `docs/reports/hero_example_shortlist.md`. Each section is structured as a self-contained slide. No sensationalism; every fact is sourced to a specific repo artefact and every uncertainty is surfaced.

---

## 1. Entity identity

| Field | Value |
|---|---|
| Exact name (OS canonical) | `Igt Intergestions Trust Reg` |
| Alias on OS | `IGT Intergestions Trust Reg.` |
| Name as recorded on OCOD | `IGT INTERGESTIONS TRUST REG` |
| Entity type | Liechtenstein **Trust Reg** (a registered trust enterprise under Liechtenstein corporate law — distinct from an Anstalt or AG) |
| Jurisdiction | Liechtenstein (`li`) |
| Liechtenstein company number | `FL00015130568` |
| Global LEI | `391200PWMHBZMLPKTA05` |
| Additional identifier | `JB8LS599999SL438` |
| OS internal ID | `NK-2FYHVi5239jTUiF4iMyFrj` |
| OS first-seen / last-seen | 2023-05-19 → 2026-05-13 |
| Registered office addresses (OS-recorded variants) | `Aeulestrasse 2, 9490 Vaduz` and `Aeulestrasse 30, 9490 Vaduz` |
| Registered office address (OCOD-recorded) | `Aeulestrasse 6, 9490 Vaduz, Liechtenstein` |

**Caveat:** OS records Aeulestrasse 2 and Aeulestrasse 30; OCOD records Aeulestrasse 6. All three are on the same Vaduz street known for corporate-services providers. Single-entity identity is confirmed by the matching Liechtenstein company number, global LEI, and OFAC SDN entry — the street-number variants are best read as different registered-office addresses used over time or for different filings, not as different entities.

Source: `aar_igt_verify.json` → `targets[1]` (target_key `igt_intergestions`).

---

## 2. OpenSanctions / OFAC source — why sanctions-relevant

| Field | Value |
|---|---|
| OS topics | `debarment | sanction` |
| OS datasets present | `us_ofac_sdn`, `us_sam_exclusions`, `ext_us_ofac_press_releases`, `ext_gleif`, `ua_war_sanctions`, `permid`, `us_trade_csl`, `opencorporates` |
| US Treasury OFAC SDN list | **Yes — present** (dataset `us_ofac_sdn`) |
| US System for Award Management Exclusions | **Yes — present** (`us_sam_exclusions`) |
| US Commerce Department Consolidated Screening List | **Yes — present** (`us_trade_csl`) |
| Ukrainian National Security and Defense Council sanctions | **Yes — present** (`ua_war_sanctions`) |
| OFAC press release referent | `ofac-pr-ee981f54400c00e64543bbc014c2...` (truncated in our snapshot — the exact OFAC press-release URL is the next verification step) |

The entity is on the **actual US Treasury Specially Designated Nationals list**, not a peripheral commercial database. The presence on `ua_war_sanctions` situates the designation in the Russia/Ukraine war context — i.e. the designation is among the Treasury sanctions packages issued in response to Russia's 2022 invasion of Ukraine. The specific OFAC designation reason is in the linked press release, which is the first manual check (see slide 8).

Source: same row in `aar_igt_verify.json`. The OFAC press-release ID is in the OS `referents` field of the raw JSON record.

---

## 3. OCOD title evidence — the 5 Highgate titles

All five titles are listed in OCOD May 2026 with proprietor `IGT INTERGESTIONS TRUST REG`, country of incorporation Liechtenstein, and **all registered on the same day, 29 April 2013** (suggesting a single estate or portfolio acquisition):

| Title number | Property | Postcode | Price-paid |
|---|---|---|---|
| `NGL780113` | LAND LYING TO THE SOUTH OF Highgate West Hill, London | (land — no postcode in OCOD) | — |
| `NGL809817` | LAND ON THE SOUTH EAST SIDE OF Highgate West Hill, London | (land — no postcode) | — |
| `LN44427` | **Bromwich House, 1 Witanhurst Lane, London** | **N6 6LT** | — |
| `NGL723612` | LAND LYING TO THE SOUTH EAST OF Highgate West Hill, London | (land — no postcode) | — |
| `NGL753781` | 79 Highgate West Hill, London | N6 6LU | **£450,000** |

**Bromwich House at 1 Witanhurst Lane is in the immediate physical curtilage of the Witanhurst estate** — one of the largest private residences in London. The OCOD record alone does not tell us whether Bromwich House is the main residence, a gatehouse, or a cottage on the estate; that requires a title-register pull. The four other titles are all on the Highgate West Hill stretch immediately south of the estate.

Source: `aar_igt_verify.json` → `targets[1].ocod_titles` (full title list with title numbers and acquisition dates).

---

## 4. ROE search evidence — no matching filing

The UK Companies House Register of Overseas Entities was extracted in full from the May 2026 Basic Company Data bulk download — 30,221 OE-prefixed entries — and committed to the repo at `data/uk_ch_overseas_entities.parquet`.

Two passes were run against the OE registry:

| Pass | Normalisation | Match? |
|---|---|---|
| Exact-key | lowercase, suffix-strip (LTD/LIMITED/LLC/INC/SA/SARL/AG/GMBH/BV/PLC/LLP/LP), alphanumeric-only | **No matches** for `igt intergestions trust reg` |
| Fuzzy second-pass | token-set Jaccard with prefix-blocking, threshold 0.7 | **No matches** above threshold |

Source: `probe_roe_noncompliance.py` (exact-key anti-join) + `probe_roe_noncompliance_strict.py` (fuzzy second-pass). Output: `roe_noncompliance.json` and `roe_noncompliance_strict.json`.

Search terms used (all returning no match): `igt intergestions trust reg`, `intergestions`, `igt intergestions`, `igt intergestions trust`. Live UK Companies House search by the same terms is the next manual check (see slide 8).

---

## 5. Timeline — ownership date vs ROE obligation

| Date | Event |
|---|---|
| **29 April 2013** | IGT Intergestions Trust Reg acquired all five UK titles (per OCOD `date_proprietor_added`) |
| 1 August 2022 | Economic Crime (Transparency and Enforcement) Act 2022 — Register of Overseas Entities provisions commence |
| **31 January 2023** | **Transitional deadline** for pre-existing overseas owners. After this date, an overseas owner that has not registered is in breach of s.4 ECTEA and subject to s.34 / s.42 criminal liability |
| (after 31 Jan 2023) | OFAC designation date — to be confirmed from the OFAC press release |
| May 2026 | OCOD snapshot, UK CH OE-registry bulk snapshot, anti-join run |

The breach in our anti-join is of the **transitional-period rule**: IGT owned UK property continuously from April 2013, and was required to register on the OE register by 31 January 2023. No filing is present in our May 2026 OE-registry snapshot.

Sources: OCOD `date_proprietor_added` field per title; ECTEA 2022 statute (s.4 commencement, s.34/s.42 penalty provisions).

---

## 6. Property map / location

No external screenshot is embedded here — a published version would include an OS-licensed map tile centred on **N6 6LT / N6 6LU** with the five titles marked, plus an inset of the Highgate West Hill stretch. Brief description for the cartographer:

- **Highgate West Hill** is a residential road on the western edge of Highgate Village in the London Borough of Camden, running between Hampstead Heath and Highgate Cemetery.
- **Witanhurst Lane** branches off the western side of Highgate West Hill, leading into the grounds of the Witanhurst estate.
- The five IGT titles cluster along a ~200m stretch of the southern end of Highgate West Hill and the eastern boundary of Witanhurst Lane.
- Postcodes N6 6LT and N6 6LU are immediately adjacent.

The map should be neutral cartographic illustration — no annotations, arrows, or visual overlays implying activity. Title numbers can be footnoted under the map.

---

## 7. Possible benign explanations

Each must be ruled out by the manual checks in slide 8 before publication.

1. **Name variant on the OE register.** The entity could have filed under `IGT Intergestions Trust Reg.` (with full stop), `IGT Intergestions`, `IGT Intergestions Trust Reg AG`, or any combination including a translation of "Trust Reg". The exact-key + fuzzy passes used multiple variants but cannot rule out an exotic spelling. **Live UK CH OE-register lookup is required.**
2. **Title data lag.** OCOD reflects HM Land Registry data as published; if the five titles have since been sold or restructured (e.g. via the OFAC frozen-asset process), the OCOD record could be stale. **Title-register purchases are required.**
3. **ROE filing under a different proprietor.** If the original Liechtenstein Anstalt has been administratively merged into a different vehicle, the new vehicle might be ROE-registered. **Liechtenstein commercial register pull is required.**
4. **OFAC designation not yet recorded against the UK property.** UK financial sanctions (administered by OFSI, separate from US OFAC) take their own designation pathway; OFAC SDN listing is not automatically UK-actionable. The UK Sanctions and Anti-Money Laundering Act 2018 regime is what matters for UK property freezing; OFAC SDN listing is what makes the entity globally sanctions-relevant but is not in itself a UK-enforced freeze. The story should not conflate these.
5. **Bromwich House status uncertain.** Bromwich House at 1 Witanhurst Lane may be a cottage on the Witanhurst estate, a separate building with a confusingly similar address, or part of a different property altogether. Saying "owns part of Witanhurst" without buying the title register is unsafe.
6. **"Trust Reg" identity.** Liechtenstein "Trust Reg" (Treuunternehmen) is a registered trust enterprise. It is distinct in Liechtenstein law from an Anstalt or AG. The story should describe it as "a registered Liechtenstein trust enterprise" rather than "a Liechtenstein company" to avoid mischaracterising the entity type.

---

## 8. Manual checks still required before publication

Hard prerequisites — no claim about IGT Intergestions Trust Reg should be published until each of these is complete:

1. **Pull the OFAC press release.** Resolve the `ofac-pr-ee981f54400c00e64543bbc014c2...` referent ID via the OS source page or OFAC's own publication index. Extract: designation date, designation reason, sanctions program (Russia / Belarus / counter-narcotics / etc.), beneficial-ownership rationale if stated.
2. **Live UK Companies House OE-register search.** Visit `find-and-update.company-information.service.gov.uk` and query the OE register for: `IGT Intergestions Trust Reg`, `IGT Intergestions`, `Intergestions`, and any LEI- or LI-company-number-based search the service permits. Save the result page as a PDF for the record.
3. **Pull the 5 OCOD title registers from HM Land Registry.** £3 per title online (£15 total). Confirms current proprietor name, current proprietor address, full property description, and any restrictions or charges on the title.
4. **Pull the Liechtenstein commercial register record.** Liechtenstein's Justizportal at `justizportal.li` should hold the public corporate record for `FL00015130568` — confirms current registered office, current trustees, status (active / in liquidation), and any changes since 2013.
5. **Archive the OS, OFAC, OCOD, and ROE-register pages** to Wayback Machine and a local copy. Sanctions data and OCOD data are revised regularly; the published claim needs a stable evidence snapshot.
6. **Resolve the OS LEI** via GLEIF (`391200PWMHBZMLPKTA05` should appear at `gleif.org` with the canonical legal-name spelling and current registered office).
7. **Confirm Bromwich House identity** — separately from the title register, a planning-portal search at the London Borough of Camden should confirm whether Bromwich House is a freestanding dwelling, a building on the Witanhurst estate, or a building-name reuse.
8. **Lawyer review** — focused on (a) the OFAC-listed-entity framing, (b) the careful drawing of the OCOD / ROE / OFAC distinction, (c) whether any individual beneficial owner can be safely identified from the OFAC designation paperwork.

---

## 9. Right-of-reply targets

The right-of-reply requests should be issued in writing **before** publication, with a minimum 7-day response window, to each of the following:

| Target | Address | What to ask |
|---|---|---|
| **IGT Intergestions Trust Reg** (registered office) | Aeulestrasse 6 (also 2 and 30), 9490 Vaduz, Liechtenstein | (a) Confirm or correct your current registered office address; (b) confirm whether you have filed under the UK Register of Overseas Entities and provide the OE-registration number if you have; (c) provide your position on the US OFAC SDN designation; (d) provide a contact for any further questions |
| **UK Companies House** — Register of Overseas Entities desk | `enquiries@companieshouse.gov.uk` and the Cardiff office | (a) Confirm the lookup result for `IGT Intergestions Trust Reg` and any reasonable name variants on the OE register; (b) confirm what enforcement steps Companies House takes against an OE-register non-filer that is also OFAC-listed |
| **HM Land Registry** | The relevant local office for title numbers `NGL780113`, `NGL809817`, `LN44427`, `NGL723612`, `NGL753781` | (a) Confirm current proprietor; (b) confirm whether any restrictions or charges have been entered on these titles under Schedule 4A LRA 2002 (ECTEA-driven restrictions on dealings) |
| **OFSI** (UK Office of Financial Sanctions Implementation) | `OFSI@hmtreasury.gov.uk` | (a) Confirm whether `IGT Intergestions Trust Reg` is the subject of a UK financial sanctions designation; (b) confirm the position on UK assets held by a US-OFAC-listed Liechtenstein entity that is not on the UK consolidated list |
| **HMRC's Economic Crime Supervision Team** (only if the story specifically frames ECTEA enforcement) | via the GOV.UK ECTEA enforcement contact | (a) Whether ECTEA enforcement action has been opened against this entity |
| **The Witanhurst estate** | via the public-facing Witanhurst representative if one exists; otherwise via the London Borough of Camden planning record | (a) Confirm or correct the description of Bromwich House at 1 Witanhurst Lane in relation to the Witanhurst estate |

Do **not** approach: any named individual associated with the entity until the OFAC designation paperwork has been read and any underlying beneficial-owner identification has been lawyer-cleared.

---

## 10. Safe sentence

The single sentence below is exactly what can be said as-is, on the strength of the artefacts in the repo today, before any of the slide-8 manual checks have been completed:

> "A Liechtenstein-registered trust enterprise on the United States Treasury OFAC sanctions list — `Igt Intergestions Trust Reg`, Liechtenstein company number `FL00015130568` — has been recorded since April 2013 as the proprietor of five UK Land Registry titles clustered on Highgate West Hill in north London, including a building called Bromwich House at 1 Witanhurst Lane (N6 6LT). The UK's Register of Overseas Entities — which since 2022 has required every overseas-incorporated owner of UK property to disclose its beneficial owners by 31 January 2023 — contains no filing under the entity's name or any common variant of it."

What this sentence does:

- **Asserts only facts in OCOD, OS/OFAC, and the OE-registry anti-join** — every clause is a record citation.
- **Names the entity, not any individual** — no person is identified or implied.
- **Describes the location precisely** — Highgate West Hill, Bromwich House at 1 Witanhurst Lane — without claiming Bromwich House *is* Witanhurst or that the IGT entity owns the Witanhurst residence itself.
- **States the ROE rule plainly** — overseas-incorporated owners must file by 31 January 2023.
- **Reports the absence of a filing as a public-register fact** — "no filing under the entity's name or any common variant of it" is what our data shows.
- **Carries one implicit caveat: the OE-register lookup was via May 2026 bulk data** — a live OE-register search (slide 8 check #2) before publication is required to refresh that claim. Once that live check is done, the sentence stands.

What this sentence does **not** do:

- Does not name an individual beneficial owner.
- Does not claim the IGT entity owns Witanhurst, or that the Highgate land is part of the Witanhurst estate.
- Does not characterise the OFAC designation reason (which awaits the press-release pull).
- Does not claim UK criminal liability — only the public-register fact and the statutory rule it visibly fails to satisfy.

---

## Source artefacts referenced

- `aar_igt_verify.json` — IGT-specific OCOD + OS records (5 titles, full title numbers, OS dataset list, identifiers, LEI)
- `roe_noncompliance.json` — v1 anti-join confirming no OE-registry match
- `roe_noncompliance_strict.json` — fuzzy second-pass confirming no OE-registry match at Jaccard ≥ 0.7
- `docs/case_study_roe_noncompliance.md` — case-study writeup with IGT Intergestions section
- `docs/reports/hero_example_shortlist.md` — ranking that selected this candidate
- `docs/reports/data/hero_example_shortlist.json` — machine-readable companion
- `scripts/probe_aar_igt_verify.py` — probe that produced the data summarised here
