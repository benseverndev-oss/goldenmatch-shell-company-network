# IGT Intergestions Trust Reg — Pre-publication checks

Status of each item in `hero_example_igt_intergestions.md` slide 8 ("Manual checks still required"). Marks each as **done**, **partial**, or **manual only**, with the artefact location and the gap (if any).

---

## Status summary

| # | Check | Status | Artefact |
|---:|---|---|---|
| 1 | OFAC press release pull | **PARTIAL** — referent ID captured, full text not yet fetched | `igt_pre_publication_artefacts/os_record.json` (raw_json field has referent) |
| 2 | Live UK Companies House OE-register search | **DONE** | `igt_pre_publication_artefacts/ch_search_*.html` × 11 variants + `ch_search_results.json` |
| 3 | OCOD rows archived | **DONE** | `igt_pre_publication_artefacts/ocod_rows.json` |
| 4 | Title-register purchases (HMLR, £15 total) | **MANUAL ONLY** | (must be purchased — see below) |
| 5 | Liechtenstein commercial register pull | **MANUAL ONLY** | (justizportal.li — paid, German UI) |
| 6 | Archive OS/OFAC/OCOD/ROE pages to Wayback Machine | **PARTIAL** — submission script ready, run separately | `scripts/verify_igt_pre_publication.py` (run without `--no-wayback`) |
| 7 | OS / GLEIF LEI verification | **PARTIAL** — search URL noted in artefacts, manual cross-check still needed | `igt_pre_publication_artefacts/wayback_submissions.json` (when run) |
| 8 | Witanhurst estate / Bromwich House clarification | **MANUAL ONLY** | (Camden planning portal) |
| 9 | Lawyer review | **MANUAL ONLY** | (out of scope for the repo) |

---

## 1. Live Companies House / ROE search — DONE

`scripts/verify_igt_pre_publication.py` ran live UK CH searches against 11 entity-name variants. **Every variant returned "No results found"** on the live UK Companies House search.

| # | Variant queried | CH "No results" banner | Useful hit returned? |
|---:|---|---|---|
| 1 | `IGT Intergestions Trust Reg` | Yes | None — fallback results only |
| 2 | `IGT Intergestions Trust Reg.` | Yes | None — fallback only |
| 3 | `IGT Intergestions Trust` | Yes | None — fallback only |
| 4 | `IGT Intergestions` | Yes | None — fallback only |
| 5 | `Intergestions Trust Reg` | Yes | None — fallback only |
| 6 | `Intergestions` | Yes | None — fallback only |
| 7 | `IGT Intergestions Trust Reg AG` | Yes | None — fallback only |
| 8 | `IGT-Intergestions` | Yes | None — fallback only |
| 9 | `I.G.T. Intergestions Trust Reg` | Yes | None — fallback only |
| 10 | `FL00015130568` (LI company number) | Yes | None |
| 11 | `391200PWMHBZMLPKTA05` (global LEI) | Yes | None |

CH's "fallback hits" (PROVENTUS TREUHAND UND VERWALTUNG AG, ANDERO TRUST REG, ASSESSOR TRUST REG, BRIGHTSTAR LOTTERY UK) are **different OE-registered Liechtenstein trust entities and the unrelated IGT-lottery company**, surfaced by CH's relevance fallback. They are not IGT Intergestions.

**Conclusion**: confirmed — no UK Companies House entry exists for IGT Intergestions Trust Reg under any of the 11 tested variants, including by Liechtenstein company number and global LEI. The May-2026 bulk-data anti-join finding is corroborated by the live July 2026 (or whenever this is run) CH search.

The 11 raw HTML responses are saved as `igt_pre_publication_artefacts/ch_search_<variant>.html` for the evidence record. The parsed summary is at `igt_pre_publication_artefacts/ch_search_results.json`.

---

## 2. OCOD rows archived — DONE

`igt_pre_publication_artefacts/ocod_rows.json` contains a tidy snapshot of the 5 OCOD May 2026 rows for IGT Intergestions Trust Reg. The snapshot is sourced from `aar_igt_verify.json` and reformatted for evidence purposes.

For each of the 5 titles, the archive contains: title number, property address, postcode (where present), price-paid (where present), date proprietor added, proprietor name, proprietor address, country of incorporation, the OCOD snapshot date.

Verifying the rows have not changed in current OCOD requires either (a) re-running the Railway ingest with the next OCOD monthly release, or (b) purchasing the title registers from HMLR (slide-8 item #4). Both belong on the pre-publication checklist.

---

## 3. Title register checks for the 5 Highgate titles — MANUAL ONLY (cost: £15)

| Title # | Property | Cost |
|---|---|---:|
| `NGL780113` | LAND LYING TO THE SOUTH OF Highgate West Hill, London | £3 |
| `NGL809817` | LAND ON THE SOUTH EAST SIDE OF Highgate West Hill, London | £3 |
| `LN44427` | Bromwich House, 1 Witanhurst Lane, London N6 6LT | £3 |
| `NGL723612` | LAND LYING TO THE SOUTH EAST OF Highgate West Hill, London | £3 |
| `NGL753781` | 79 Highgate West Hill, London N6 6LU | £3 |

Procedure:
1. Go to `https://eservices.landregistry.gov.uk/eservices/FindAProperty/view/QuickEnquiryInit.do`
2. For each title number, select "Search by title number" and enter the exact number above
3. Purchase the **Official Copy of Register** (£3 per title)
4. For each title, additionally request the **Title Plan** (£3 per title) if mapping fidelity matters — total then becomes £30

What to look for on each returned official copy:
- Current proprietor name (still IGT Intergestions Trust Reg?)
- Current proprietor address (still Aeulestrasse 6 Vaduz?)
- **Restrictions on the title under Schedule 4A LRA 2002** — these are the ECTEA-driven restrictions that block dealings until the overseas owner registers on the OE register. If a Schedule 4A restriction is on the title, that is itself evidence that the OE-register non-filing has practical consequence.
- Any charges (mortgages) registered against the title
- Any cautions or notices that suggest disputes
- The Bromwich House title plan specifically — does the parcel sit inside the Witanhurst estate curtilage or alongside it?

---

## 4. OFAC / OpenSanctions source archived — PARTIAL

### OpenSanctions snapshot

`igt_pre_publication_artefacts/os_record.json` contains the canonical OS record for the entity, including:
- OS internal ID `NK-2FYHVi5239jTUiF4iMyFrj`
- Datasets list: `us_ofac_sdn`, `us_sam_exclusions`, `ext_us_ofac_press_releases`, `ext_gleif`, `ua_war_sanctions`, `permid`, `us_trade_csl`, `opencorporates`
- Identifiers: Liechtenstein company number `FL00015130568`, LEI `391200PWMHBZMLPKTA05`, additional `JB8LS599999SL438`
- Addresses (variants): Aeulestrasse 2 / 6 / 30, 9490 Vaduz
- First-seen / last-seen on OS: 2023-05-19 → 2026-05-13
- The `raw_json` field on the record contains the full original FTM JSON including the OFAC-press-release referent

The OS entity page URL `https://www.opensanctions.org/entities/NK-2FYHVi5239jTUiF4iMyFrj/` should be submitted to the Wayback Machine before publication. The submission code is in `scripts/verify_igt_pre_publication.py` (run without `--no-wayback`).

### OFAC press release — GAP

Slide-8 item #1: the OS `referents` field contains an `ofac-pr-ee981f54400c00e64543bbc014c2...` identifier indicating a specific OFAC press release exists, but the full text is not yet pulled into the repo.

The two paths to resolve:
1. Search the OFAC sanctions search at `https://sanctionssearch.ofac.treas.gov/` for `IGT Intergestions`. The OFAC SDN entry usually links to the press release where the entity was first designated.
2. Search the OS source page `https://www.opensanctions.org/entities/NK-2FYHVi5239jTUiF4iMyFrj/` — OS typically lists the OFAC press release URL as a source.

Once the press release is in hand, extract: **designation date** (so we can compare against the ECTEA transitional deadline), **designation reason** (sanctions program — Russia / Belarus / counter-narcotics / other), and any **beneficial-owner identification** in the OFAC paperwork. This is the single biggest pre-publication evidence gap.

### OFAC SDN search page — PARTIAL

The script also attempted to fetch the OFAC SDN search page (`sanctionssearch.ofac.treas.gov/Search.aspx`). The endpoint redirected to an error page on a bare GET because the search form requires a POST with parameters. This is a manual GUI step.

---

## 5. Exact spelling / entity-variant audit — DONE

The 11-variant CH search above is the operational variant audit. In addition, the entity-name normalisation passes in the anti-join cover the same surface:

| Variant tested | Mechanism | Match? |
|---|---|---|
| Exact name with full stop / without / `Trust Reg` / `Trust Reg.` | Suffix-strip + alphanumeric-only key (`probe_roe_noncompliance.py`) | No |
| Token-set Jaccard ≥ 0.7 at any token-prefix block | Fuzzy second-pass (`probe_roe_noncompliance_strict.py`) | No |
| Truncations and partial-token variants | 11-variant live CH search (this document) | No |
| Liechtenstein company number `FL00015130568` | Live CH search by number | No |
| Global LEI `391200PWMHBZMLPKTA05` | Live CH search by LEI | No |

**Critical naming caveat surfaced by this audit**: "IGT" is also the name of **International Game Technology**, a major US-listed lottery operator. CH's fallback hits returned `BRIGHTSTAR LOTTERY UK BIDCO LIMITED` and related entities on every IGT-substring search, because IGT (the lottery company) recently sold its UK lottery business to Brightstar. The published claim must be explicit that "IGT" in our context refers to **IGT Intergestions Trust Reg** of Liechtenstein, and is unrelated to **International Game Technology** the lottery operator. Recommended formulation in published text: spell the entity in full as "IGT Intergestions Trust Reg" on every mention, with the Liechtenstein company number `FL00015130568` on first mention.

---

## 6. Timeline check against ROE legal deadlines — DONE

| Date | Event | Source |
|---|---|---|
| **29 April 2013** | All 5 IGT titles registered in OCOD with proprietor IGT Intergestions Trust Reg | OCOD title rows |
| **1 August 2022** | Economic Crime (Transparency and Enforcement) Act 2022 receives Royal Assent (15 March 2022); ROE provisions commenced by The Economic Crime (Transparency and Enforcement) Act 2022 (Commencement No. 2) Regulations 2022 (SI 2022/839) | UK statute |
| **5 September 2022** | Register of Overseas Entities opens for filings at UK Companies House | UK CH announcement |
| **31 January 2023** | **Transitional deadline** for pre-existing overseas owners that held UK qualifying-estate property at 28 February 2022. Past this date, the entity is in breach of s.7 ECTEA (failure to comply with the registration requirement) and any officer commits an offence under s.34 ECTEA. Additionally, the title becomes subject to a Land Registry restriction under s.4A LRA 2002 (inserted by ECTEA) prohibiting most dispositions | ECTEA 2022 ss.4, 7, 34, 42; Sch 3 |
| **(unknown date) 2022 or later** | OFAC SDN designation of IGT Intergestions Trust Reg — date to be confirmed from the OFAC press release | OS `ext_us_ofac_press_releases` referent |
| **May 2026** | UK CH OE-registry bulk snapshot pulled; OCOD May 2026 snapshot pulled; anti-join run; no OE-registry entry found for IGT Intergestions under any tested variant | This investigation |
| **(this week)** | Live CH search across 11 variants confirms no UK CH entry exists | `igt_pre_publication_artefacts/ch_search_results.json` |

**Net regulatory position from the timeline**:
- IGT owned UK property continuously from 29 April 2013 — well before the ECTEA cut-over of 28 February 2022.
- The transitional registration deadline of 31 January 2023 has passed by more than 3 years.
- An OE-register filing is therefore overdue. Under s.34 ECTEA each day of non-compliance is an additional day's offence (the s.34 offence framework is one of the elements that distinguish ECTEA from earlier disclosure-failure regimes).
- The OCOD record dates the ownership; the live CH search dates the non-filing; the OFAC SDN listing dates the additional sanctions overlay (subject to confirmation from the press release).

The legal question that the OFAC press-release date answers is whether the OFAC designation was before or after the 31 January 2023 transitional deadline. Either case is publishable — both establish a current-day non-compliance — but the framing differs slightly:

- **If OFAC designation pre-dates 31 January 2023**: IGT was already on the OFAC SDN list when it missed the ECTEA transitional registration deadline. The story is "OFAC-listed entity failed to register under UK law that was passed in direct response to the Russia/Ukraine war sanctions enforcement gap."
- **If OFAC designation post-dates 31 January 2023**: IGT missed the ECTEA deadline first, then was OFAC-designated. The story is "an entity already in breach of the UK transparency regime was subsequently sanctioned by the United States, and is still not on the UK register."

---

## 7. Right-of-reply plan

Five letters / enquiries to send by registered post and email **before publication**, with a minimum 7-day response window. Drafts below; each should be tailored to the publication's house style.

### A. To IGT Intergestions Trust Reg (registered office)

**By registered post:** IGT Intergestions Trust Reg, Aeulestrasse 6, 9490 Vaduz, Liechtenstein
**By post (variant 1):** Aeulestrasse 2, 9490 Vaduz, Liechtenstein
**By post (variant 2):** Aeulestrasse 30, 9490 Vaduz, Liechtenstein

> Dear Sir or Madam,
>
> I am preparing an article for publication that refers to IGT Intergestions Trust Reg (Liechtenstein company number FL00015130568, LEI 391200PWMHBZMLPKTA05). I write to seek your response to the following facts and to offer a right of reply before publication.
>
> 1. According to HM Land Registry's Overseas Companies Ownership Data, the entity has been recorded since 29 April 2013 as the proprietor of five UK Land Registry titles in Highgate, London: NGL780113, NGL809817, LN44427 (Bromwich House, 1 Witanhurst Lane), NGL723612, and NGL753781 (79 Highgate West Hill). Please confirm or correct this.
> 2. According to OpenSanctions, the entity is on the United States Treasury OFAC Specially Designated Nationals list, on the U.S. System for Award Management Exclusions, and on the Ukrainian National Security and Defense Council sanctions register. Please provide your position on these designations.
> 3. The UK Register of Overseas Entities at UK Companies House contains no record of a filing by the entity. A live search this week against eleven name variants and the Liechtenstein company number returned no matches. The statutory transitional deadline for pre-existing overseas owners of UK property was 31 January 2023. Please confirm whether the entity has filed under the UK Register of Overseas Entities and, if so, provide the OE-registration number; or, if not, your reason.
> 4. Please confirm the entity's current registered office, current trustees / responsible officers, and a contact for any further questions.
>
> I propose to publish on [date]. Any response received by [date − 1] will be reflected in the published article in full. If no response is received by that date, the article will note that fact.
>
> [signature]

### B. To UK Companies House — Register of Overseas Entities enquiries

**Email:** `enquiries@companieshouse.gov.uk`
**Cc:** the ROE enforcement team if a published address exists

> Dear Sir or Madam,
>
> I am preparing an article that refers to a Liechtenstein-registered trust enterprise ("IGT Intergestions Trust Reg", Liechtenstein company number FL00015130568, LEI 391200PWMHBZMLPKTA05) that, according to HM Land Registry's Overseas Companies Ownership Data, has been the proprietor of five UK Land Registry titles in Highgate, London since 2013, and that appears on the United States OFAC Specially Designated Nationals list.
>
> A search of the Register of Overseas Entities at Companies House under eleven name variants and the Liechtenstein company number returns no matches. The article will report this fact.
>
> Before publication I would be grateful for the following:
> 1. Confirmation, on a yes/no basis, of the lookup result for "IGT Intergestions Trust Reg" and the variants listed in the attached appendix.
> 2. A general comment on what enforcement steps Companies House takes against an overseas owner of UK property that is on the United States OFAC list and has not registered on the Register of Overseas Entities by the 31 January 2023 transitional deadline.
> 3. Whether Companies House is aware of the case, and any commentable position.
>
> I propose to publish on [date]. Any response by [date − 1] will be reflected in the article.
>
> [signature]

### C. To HM Land Registry

**Email:** the relevant regional office for the title numbers (Croydon Office handles London titles by default)

> Dear Sir or Madam,
>
> I am writing in connection with five UK Land Registry titles in Highgate, London: NGL780113, NGL809817, LN44427, NGL723612, and NGL753781. The HM Land Registry "Overseas Companies Ownership Data" dataset records the proprietor of all five as a Liechtenstein-registered entity ("IGT Intergestions Trust Reg", Liechtenstein company number FL00015130568) since 29 April 2013.
>
> Before publication of an article that refers to these titles, I would be grateful for the following confirmations on the public record:
> 1. The current proprietor of each title (so I can confirm or correct the OCOD data against the live register).
> 2. Whether a restriction has been entered on each title under section 4A of the Land Registration Act 2002 (as inserted by the Economic Crime (Transparency and Enforcement) Act 2022 Schedule 3), prohibiting dispositions until the proprietor is on the Register of Overseas Entities.
> 3. Whether any charges, cautions, or other notices are currently entered against any of the five titles.
>
> I will purchase official copies of the registers for each title via the Land Registry's standard online service. This letter is to ensure HM Land Registry has notice of the intended publication and the opportunity to comment.
>
> [signature]

### D. To OFSI (UK Office of Financial Sanctions Implementation)

**Email:** `OFSI@hmtreasury.gov.uk`

> Dear OFSI,
>
> I am preparing an article about a Liechtenstein-registered entity ("IGT Intergestions Trust Reg") that is on the United States Treasury OFAC Specially Designated Nationals list and that, according to HM Land Registry data, owns five Land Registry titles in Highgate, London.
>
> Before publication, I would be grateful for OFSI's general position on the following:
> 1. The treatment of UK assets held by an entity that is on the United States OFAC SDN list but not currently on the UK consolidated list of financial sanctions targets.
> 2. Whether IGT Intergestions Trust Reg is the subject of any UK financial sanctions designation or asset-freeze.
> 3. Whether the failure of such an entity to register on the Register of Overseas Entities at Companies House is itself a matter that OFSI engages with, or whether it sits within Companies House / Land Registry / HMRC enforcement competences.
>
> I will not publish OFSI's response as a quote without explicit consent.
>
> [signature]

### E. To the publicly-facing representative for Witanhurst (or, if none, the London Borough of Camden planning service)

**Email:** the Witanhurst public-facing PR contact if known; otherwise via Camden's planning portal contact form

> Dear Sir or Madam,
>
> The HM Land Registry public "Overseas Companies Ownership Data" dataset lists a property called "Bromwich House, 1 Witanhurst Lane, London N6 6LT" (title number LN44427) as being in the ownership of a Liechtenstein-registered entity.
>
> Before any reference to this title in an article in preparation, I am writing to ask:
> 1. Whether Bromwich House is part of the Witanhurst estate, an adjacent building, or a separate property entirely.
> 2. Whether your organisation has any commentable position on the matter.
>
> I do not propose to make claims about the wider Witanhurst estate without verification; this letter is solely to clarify the relationship between Bromwich House and the estate before any geographical reference is published.
>
> [signature]

---

## 8. Items still pending after this run

Hard prerequisites for publication that cannot be completed from this repo:

1. **Buy the 5 HMLR title registers** (£15 total, online).
2. **Pull the specific OFAC press release** naming IGT Intergestions Trust Reg, via either the OFAC SDN public search interface or the OpenSanctions entity page.
3. **Pull the Liechtenstein commercial register** record for company `FL00015130568` via `justizportal.li` (paid, German interface).
4. **Run the Wayback Machine submissions** by re-executing `scripts/verify_igt_pre_publication.py` without `--no-wayback`. (We deferred them in this run because Wayback save submissions can be slow and unreliable; they should be done at publication-readiness moment.)
5. **GLEIF LEI verification** at `https://search.gleif.org/#/record/391200PWMHBZMLPKTA05` to capture the canonical legal-name spelling and current registered office.
6. **Camden planning-portal search** for Bromwich House / 1 Witanhurst Lane to clarify the building's relationship to the Witanhurst estate.
7. **Send the five right-of-reply letters** above and observe the response window.
8. **Lawyer review** of the published draft.

---

## 9. Artefact index

| File | Contents |
|---|---|
| `igt_pre_publication_artefacts/ch_search_*.html` (11 files) | Raw HTML responses from live UK CH search for each name variant |
| `igt_pre_publication_artefacts/ch_search_results.json` | Parsed summary of all 11 CH searches |
| `igt_pre_publication_artefacts/ocod_rows.json` | Local archive of the 5 OCOD title rows (May 2026 snapshot) |
| `igt_pre_publication_artefacts/os_record.json` | Local archive of the canonical OS record (identifiers, datasets, addresses) |
| `igt_pre_publication_artefacts/ofac_search_page.html` | OFAC SDN search landing page (no-results redirect — search itself is GUI-only) |
| `igt_pre_publication_artefacts/wayback_submissions.json` | Wayback Machine submission results (populated when `--no-wayback` is not passed) |
| `docs/reports/hero_example_igt_intergestions.md` | 10-slide evidence chain |
| `docs/reports/hero_example_shortlist.md` | Original ranking that selected this candidate |
