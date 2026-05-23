# Hero Example Shortlist

Audit of the current ROE-non-compliance / OCOD / ICIJ / OpenSanctions material to identify the single strongest "hero example" for public-facing reporting. Source artefacts referenced are listed at the bottom.

## Executive verdict

**Lead hero example: `IGT Intergestions Trust Reg`** (a Liechtenstein Anstalt holding 5 prime Highgate land titles, on the US OFAC SDN list, with no filing under the UK Register of Overseas Entities).

It wins on every axis that matters for a defensible 30-second story:

- The sanctions evidence is **directly verifiable on a public US government list** — not inferred from name proximity, not requiring a corporate-registry walk, not contingent on a brand-vs-entity distinction. `ext_us_ofac_press_releases` in the OS record means there is a specific OFAC press release that names this entity and gives the reason for designation.
- The property side is **concrete and visual**: 5 UK land titles, one of which is land south of Highgate West Hill (prime north London), with one Liechtenstein correspondence address (`Aeulestrasse 6, 9490 Vaduz`).
- The disclosure rule is **clean**: ECTEA 2022 requires the overseas owner to register on the UK CH Register of Overseas Entities. Our anti-join shows no OE filing for any normalised-name variant of this entity.
- The story has **no name-collision problem** ("IGT Intergestions Trust Reg" is a unique business name in OS), **no brand-vs-corporate ambiguity** (the OFAC listing names the entity directly), and **no defamation exposure on a named individual** (the story is about the entity, not a private person).

The Ledra → Metalloinvest → Usmanov chain has higher headline drama (Usmanov is a household name) but **carries the highest legal risk in the shortlist**. The chain depends on a brand-identity link between LEDRA TRUSTEE SERVICES LIMITED (UK property owner) and Ledra Services Limited (Panama Papers nominee) — the data show shared "Ledra" branding at Cyprus service-provider level but no corporate parent/subsidiary edge. Saying "an Usmanov-linked nominee owns a Mayfair flat" is not the claim the data supports.

`FENLAND LIMITED` is the strongest backup hero: 313 prime-West-London residential titles in one Isle-of-Man entity, direct named officers in the Paradise Papers (Lilian + Lawrence Fenech). It has the biggest scale of any single thread by an order of magnitude. The reason it does not lead is that the Fenechs are not public figures and there is no sanctions or wrongdoing tag against them — naming them carries defamation risk that the IGT story does not.

## Ranking table

Scoring: 1-5 each. **Carescore = evidence + public-interest + visual − legal_risk − false_positive_risk**.

| Rank | Candidate | Hook (one sentence) | Ev | PI | VC | LR | FP | Carescore | Recommendation |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | **IGT Intergestions Trust Reg** | An OFAC-SDN-listed Liechtenstein Anstalt owns prime Highgate land but has never filed under the UK Register of Overseas Entities. | 5 | 4 | 4 | 2 | 1 | **10** | **Lead hero example** |
| 2 | **FENLAND LIMITED (Fenech, Malta/IOM)** | A single Isle of Man company owns 313 residential properties in prime West London and has not filed under the UK Register of Overseas Entities; Paradise Papers names the Maltese Fenech family as officers. | 4 | 4 | 5 | 3 | 1 | **9** | **Strong backup** |
| 3 | SE1 / Park Plaza Westminster Bridge | The biggest postcode cluster in the non-compliance headline turned out to be one Dutch hotel-condo operator, not 690 separate offshore shells — a downgrade lesson. | 5 | 1 | 3 | 1 | 1 | **7** | **Downgrade / control example** |
| 4 | Ledra → Metalloinvest → Usmanov | A Cyprus nominee firm that owns a Mayfair flat shares its brand with a Panama Papers nominee for a BVI Metalloinvest entity controlled by sanctioned Russian oligarch Alisher Usmanov. | 4 | 5 | 5 | 5 | 3 | **6** | Useful context only; rework needed before lead use |
| 5 | Embassy Development (Battersea / Nine Elms) | A Luxembourg/Jersey SPV cluster acquired £44M of Battersea regeneration land just before ECTEA commencement and has not filed. | 3 | 3 | 4 | 2 | 3 | **5** | Useful context only |
| 6 | Edokpolo / EKO IRE LIMITED | A BVI company connected to a Nigerian family via Pandora Papers holds 5 UK titles including a Park Plaza Westminster Bridge room. | 4 | 2 | 3 | 4 | 1 | **4** | Discard for lead use |
| 7 | Harmony Ridge Limited | A single Kensington flat is owned by a Jersey company that shares a name with a BVI entity in Panama Papers, OS-flagged sanction.linked. | 2 | 2 | 2 | 3 | 4 | **−1** | Discard |

## Candidate sections

### 1. IGT Intergestions Trust Reg

#### 30-second hook
A Liechtenstein company called IGT Intergestions Trust Reg owns five plots of prime Highgate land in north London. It is on the US Treasury OFAC sanctions list. Under a 2022 UK law, overseas companies that own UK property must register on the Companies House Register of Overseas Entities and disclose who really controls them. There is no record of this company having filed.

#### What the repo currently supports
Sourced from `roe_noncompliance.json`, `roe_noncompliance_personalize.json`, `aar_igt_verify.json`, `case_study_roe_noncompliance.md`:

- **OCOD titles**: 5. Sample title: `LAND LYING TO THE SOUTH OF Highgate West Hill, London`, acquired 29 April 2013. (`aar_igt_verify.json` → targets[1].ocod_titles)
- **Proprietor name (OCOD-side)**: `IGT INTERGESTIONS TRUST REG`
- **Country of incorporation (OCOD-side)**: Liechtenstein
- **Proprietor correspondence address**: `Aeulestrasse 6, 9490 Vaduz, Liechtenstein` (a known Liechtenstein corporate-services address)
- **UK CH OE filing**: not present in the OE registry by exact-key or token-set match (anti-join from `probe_roe_noncompliance.py` + `probe_roe_noncompliance_strict.py`)
- **OpenSanctions record**:
  - Name: `Igt Intergestions Trust Reg`
  - Topics: `debarment | sanction`
  - Jurisdictions: `li`
  - Datasets: **`us_ofac_sdn`**, `us_sam_exclusions`, `ext_us_ofac_press_releases`, `opencorporates`
- **OFAC press-release link**: presence on `ext_us_ofac_press_releases` indicates a specific Treasury press release that names this entity with the designation reason. (Not yet pulled into the repo; that fetch is a publication prerequisite — see "What is missing" below.)
- **ICIJ leak presence**: not directly. ICIJ pattern matches for "intergestions" are noise from substring matches against unrelated CRAIGTECH / BIGTECH / BIGTRANS records and should not be used.

#### What appears to be the issue
**Sanctions-adjacent UK property ownership combined with a public-register failure under ECTEA 2022.** The entity is on the actual US Treasury Specially Designated Nationals list (debarment + sanction topics, `us_ofac_sdn` dataset) and is named as proprietor on five UK Highgate land titles via overseas-incorporated (Liechtenstein) form. ECTEA 2022 obliges that overseas owner to register and disclose beneficial ownership at UK Companies House; the anti-join finds no filing under any name-form variant.

#### Why anyone would care
- **Sanctions-adjacent public interest** — an entity the US Treasury has formally sanctioned is on the title to UK land.
- **Public-register failure** — the UK Register of Overseas Entities was created in 2022 specifically to make this visible. The visible gap is itself the story.

#### Evidence chain

1. **OCOD record** (HM Land Registry, May 2026 release): proprietor `IGT INTERGESTIONS TRUST REG`, country of incorporation `LIECHTENSTEIN`, proprietor address `Aeulestrasse 6, 9490 Vaduz, Liechtenstein`, sample title `LAND LYING TO THE SOUTH OF Highgate West Hill, London` (added 29 April 2013), 5 titles in total. Source: `aar_igt_verify.json` (target `igt_intergestions`).
2. **UK CH OE registry** (May 2026 bulk download, 30,221 OE-registered entities): no matching entry by suffix-stripped exact key or by token-set Jaccard fuzzy at threshold 0.7. Source: `probe_roe_noncompliance.py` + `probe_roe_noncompliance_strict.py`.
3. **OpenSanctions consolidated dataset**: entity `Igt Intergestions Trust Reg` (Liechtenstein) listed on `us_ofac_sdn`, `us_sam_exclusions`, `ext_us_ofac_press_releases`, `opencorporates`, with topics `debarment | sanction`.
4. **Conclusion**: an OFAC-listed Liechtenstein Anstalt holds 5 UK Highgate land titles; no UK ROE filing exists for that overseas owner.

#### Red flags and caveats
- **OFAC press release not yet pulled into the repo.** The `ext_us_ofac_press_releases` dataset confirms one exists, but the designation reason — which is the substance of the story — is not yet in our artefacts. Reading the OFAC press release before publication is a hard prerequisite.
- **OCOD snapshot is May 2026.** If the entity has been delisted from OCOD since (sold the land, for instance) the OCOD reference must be checked against a current title-register pull.
- **No direct person-to-company edge.** The data show the corporate entity holds the title; we do not have ICIJ-leak-style officer-level data for IGT Intergestions Trust Reg. The story is corporate-level, not person-level.
- **Acquisition date 29-04-2013 is pre-ECTEA.** This entity falls under the transitional regime (registration deadline 31 Jan 2023). Past that deadline → in breach; before it → in transitional grace. Verify the OFAC designation is also pre-deadline (it almost certainly is, but verify).
- **No wrongdoing alleged on the part of any individual.** The structural finding is about an OFAC-listed entity and an unfiled UK registration, not a person's conduct.

#### What is missing before publication
- Pull the specific **OFAC press release** that names this entity (designation date + reason). The `ext_us_ofac_press_releases` linkage means OS knows it exists; we need the actual text.
- **Live Companies House check**: search OE register at `find-and-update.company-information.service.gov.uk` for "IGT Intergestions" and any variant; confirm no registration.
- **OCOD row verification**: pull the exact 5 OCOD rows and confirm proprietor name + dates + addresses unchanged in current OCOD.
- **Title register purchase**: for each of the 5 titles, buy the current official copy from HM Land Registry. Confirms current ownership.
- **Right of reply**: written enquiry to the Liechtenstein corporate-services address at Aeulestrasse 6, Vaduz.
- **Lawyer review**: pre-publication review focusing on the OFAC-designated-entity framing and confirming no individual is named without their own basis.

#### Verdict
**Lead hero example.**

---

### 2. FENLAND LIMITED (Fenech / Malta-IOM thread)

#### 30-second hook
A single Isle of Man company called FENLAND LIMITED owns 313 residential property titles in prime West London — Kensington, Earls Court, Bayswater, South Kensington, Pimlico. It has not filed under the UK Register of Overseas Entities. The Paradise Papers leak names Lilian Fenech and Lawrence Fenech as its officers; the same name "FENLAND INC." appears separately in the Panama Papers held by bearer shares.

#### What the repo currently supports
Sourced from `fenland_deepdive.json`, `named_threads_expand.json`, `roe_noncompliance_personalize.json`, `case_study_roe_noncompliance.md`:

- **OCOD titles**: 313, all attributed to one proprietor `FENLAND LIMITED`.
- **Country of incorporation (OCOD-side)**: Isle of Man (all 313).
- **Proprietor correspondence address**: `8 St Georges Street, Douglas, Isle Of Man, IM1 1AH`.
- **Postcode-outward concentration**: W14 (85), SW5 (62), W8 (55), W2 (53), SW7 (26), SW1V (14), SW10 (12).
- **Sample title**: `144 Portnall Road, London (W9 3BQ)`, price-paid `£910,000`, acquired 02-09-2011.
- **UK CH OE filing**: not present in the OE registry by exact-key or token-set Jaccard match.
- **ICIJ entity record**: `FENLAND LIMITED`, jurisdiction Malta, source `Paradise Papers – Malta corporate registry`. A separate `FENLAND INC.` appears in the Panama Papers, held by bearer.
- **Named officers in the Paradise Papers entry**: `LILIAN FENECH`, `LAWRENCE FENECH` (both Malta).
- **Address co-tenancy**: the IOM correspondence address `8 St Georges Street, Douglas IM1 1AH` is shared with two further non-compliant proprietors — `M.H.E. INVESTMENTS LIMITED` and `ROSSMOOR LIMITED`. Cluster of 3 non-compliant entities at one IOM corp-services address.

#### What appears to be the issue
**Large-scale public-register failure under ECTEA 2022, combined with offshore-leak overlap.** A single overseas-incorporated entity holds 313 UK residential titles concentrated in prime West London. ECTEA 2022 obliges it to register and disclose beneficial ownership; the anti-join finds no filing. Two named individuals (Fenech family) appear in the Paradise Papers Malta corporate-registry leak as officers.

This is *not* a sanctions case. The Fenech family are not on any sanctions or PEP list in our data.

#### Why anyone would care
- **Scale**: 313 prime-central-London residential properties held by one Isle of Man company without UK BO disclosure is itself the headline. Concentrated in some of the most expensive postcodes in the country.
- **Public-register failure**: precisely the situation ECTEA 2022 was meant to expose.
- **Offshore-leak overlap**: independent corroboration that the entity exists and was named in Maltese filings.

#### Evidence chain

1. **OCOD record**: proprietor `FENLAND LIMITED`, country `Isle of Man`, correspondence `8 St Georges Street, Douglas, Isle Of Man, IM1 1AH`. 313 titles. Concentrated W14 (85), SW5 (62), W8 (55), W2 (53). Source: `fenland_deepdive.json`.
2. **UK CH OE registry**: no matching entry. Source: `probe_roe_noncompliance.py` + `probe_roe_noncompliance_strict.py`.
3. **ICIJ Paradise Papers — Malta corporate registry**: entity `FENLAND LIMITED` (Malta), officers `LILIAN FENECH` + `LAWRENCE FENECH`. Source: `fenland_deepdive.json` (icij_fenland_entities + icij_fenech_officers, filtered to direct officer-of edges in `named_threads_expand.json`).
4. **Conclusion**: one IOM entity holds 313 UK residential properties without ECTEA-required disclosure. Paradise Papers separately records officers Lilian + Lawrence Fenech for an entity of the same name in Malta. The two are likely the same entity in different jurisdictional listings (IOM-administered, Malta corporate-registry record), but separate corporate-registry verification is recommended before claiming this.

#### Red flags and caveats
- **Fenech is one of the most common surnames in Malta.** The Paradise Papers Maltese corporate-registry leak contains 480+ "Fenech" officer entries. Direct edge to FENLAND LIMITED is recorded for **Lilian** and **Lawrence** specifically; other Fenech names are not connected to FENLAND in our graph.
- **Yorgen Fenech name-coincidence.** Yorgen Fenech (the Maltese businessman charged with masterminding the 2017 assassination of journalist Daphne Caruana Galizia) appears in the same Paradise Papers / Malta corporate-registry leak. **There is no edge in the leak graph linking him to FENLAND LIMITED.** Proximity in leak corpus is not a link.
- **Lilian and Lawrence Fenech are private individuals.** They are not on any sanctions, PEP or wrongdoing list in our data. The story is the company-level structure and the public-register gap, not their conduct.
- **IOM vs Malta jurisdictional question.** OCOD records the proprietor as Isle of Man-incorporated; the Paradise Papers ICIJ record is in the Malta corporate-registry leak. Same name; same UK property; very likely same entity but the corporate registries of IOM and Malta should be checked independently before claiming a single entity straddles both.
- **Acquisition dates pre-ECTEA.** Sample title acquired 2011. Falls in the transitional regime; deadline for registration was 31 Jan 2023.
- **No wrongdoing alleged.** ECTEA non-compliance is the regulatory violation; nothing more is asserted by the data.

#### What is missing before publication
- **Live Companies House search** for `FENLAND LIMITED` on the OE register — confirm no filing under any name form.
- **IOM Companies Registry pull** for `FENLAND LIMITED` — confirm IOM incorporation, current status, named directors, address history.
- **Malta Business Registry pull** for `FENLAND LIMITED` (Malta) — confirm whether the Paradise Papers Maltese entity is the same as the IOM-OCOD entity or two distinct entities sharing a name.
- **Spot-check 10 OCOD titles** by buying the current title registers from HM Land Registry.
- **Right of reply** to FENLAND LIMITED at the IOM address and to the named officers via their Maltese corporate-registry record.
- **Lawyer review** with particular attention to the careful drawing of the Yorgen Fenech non-link and the public-private distinction for the Fenechs.

#### Verdict
**Strong backup.** The scale advantage (313 vs 5 titles) is significant, but the absence of a sanctions/PEP/wrongdoing tag on the named officers means the public-interest framing depends entirely on the structural-disclosure-failure angle. That angle is defensible but less viscerally compelling than the OFAC-sanctioned-entity framing of IGT Intergestions.

---

### 3. SE1 / Park Plaza Westminster Bridge

#### 30-second hook
The biggest postcode cluster in our non-compliance headline — 690 UK titles in SE1, the South Bank — turned out, on inspection, to be 88% one Dutch company operating a hotel-condo investment scheme at the 1,019-room Park Plaza Westminster Bridge hotel. That is regulatory non-compliance but of a different shape from offshore secrecy. The lesson is what raw cluster counts can hide.

#### What the repo currently supports
Sourced from `se1_deepdive.json`, `case_study_roe_noncompliance.md`:

- 690 OCOD titles in SE1 outward postcode that fail the OE-registry anti-join.
- **563 of those 690 titles** held by `WESTMINSTER BRIDGE LONDON (REAL ESTATE) B.V.` (Netherlands).
- **46 more** held by `COUNTY HALL HOTEL HOLDINGS B.V.` (Netherlands).
- **571 titles at one building**: `200 Westminster Bridge Road, SE1 7UT` — Park Plaza Westminster Bridge hotel.
- **507 of the SE1 titles registered in 2016** alone — the hotel-condo scheme rollout.
- ICIJ overlap inside SE1: 7 distinct names, including the already-documented EKO IRE LIMITED (3 titles).

#### What appears to be the issue
A hotel-condo operator that has not filed under ECTEA 2022 for the 600+ individual room-titles its Dutch entities hold. Still ROE non-compliance; structurally different from the prime-residential offshore-shell pattern that dominates the rest of the case study.

#### Why anyone would care
- **False-positive / downgrade lesson** — the original geographic-concentration finding cited 690 titles in SE1 as a "South Bank regeneration cluster" peer of the Mayfair / Belgravia luxury-shell pattern. The deepdive showed that framing was wrong. Surfacing the correction is itself a contribution.

#### Evidence chain
1. OCOD: 690 non-compliant titles in outward postcode SE1.
2. Per-proprietor breakdown: WESTMINSTER BRIDGE LONDON (REAL ESTATE) B.V. holds 563, COUNTY HALL HOTEL HOLDINGS B.V. holds 46 — together 88% of the cluster.
3. Building-address breakdown: 571 at `200 Westminster Bridge Road`.
4. Acquisition-year distribution: 507 titles registered in 2016.
5. Conclusion: the cluster is the Park Plaza Westminster Bridge hotel-condo scheme; not 690 distinct offshore shells.

#### Red flags and caveats
- The Dutch entities are still ROE non-compliant in our anti-join; we are not absolving them, only reframing the cluster.
- The reframing is honest data-quality work; do not present it as the central wrongdoing finding.

#### What is missing before publication
- If used as a methodology section in a longer piece: a side-by-side of "raw geographic-concentration table" vs "post-deepdive table" with the SE1 row footnoted.
- If used standalone: a brief right-of-reply to the Dutch operator.

#### Verdict
**Downgrade / control example.** Strong for the "show your work" methodology section of a longer write-up; not a lead.

---

### 4. Ledra → Metalloinvest → Usmanov chain

#### 30-second hook
A Cyprus company that owns a Mayfair flat shares its name with a Cyprus nominee documented in the Panama Papers as the registered officer for a multi-jurisdiction Metalloinvest structure — the Russian metals empire of OFAC-sanctioned oligarch Alisher Usmanov.

#### What the repo currently supports
Sourced from `named_threads_expand.json`, `metalloinvest_verify.json`, `metalloinvest_uk_ch.json`, `case_study_roe_noncompliance.md`:

- **OCOD record**: `LEDRA TRUSTEE SERVICES LIMITED` (Cyprus) holds 2 Mayfair titles. Sample: `45 Green Street, Mayfair W1K 7FX`, £310,000, acquired 26 March 2015.
- **No UK ROE filing** for that name.
- **OS record**: `Ledra Trustee Services Limited` flagged `debarment | sanction`.
- **ICIJ Panama Papers**: two BVI entities named `METALLOINVEST (BVI) LIMITED` (incorporated 21 Sep 2006, status Defaulted) and `METALLOINVEST HOLDINGS B.V.I) LIMITED` (incorporated 18 May 2006, status Changed agent).
- **Connected officers of those BVI entities (per Panama Papers)**: `Ledra Services Limited` (Cyprus), `METALLOINVEST HOLDINGS (CYPRUS) LIMITED` (Cyprus), `BRIDGEWATER FIRST/SECOND NOMINEES LIMITED` (Isle of Man).
- **OS Metalloinvest records**: `Holdingovaya Kompaniya Metalloinvest AO` and `LLC Management Company "Metalloinvest"` both on `us_ofac_sdn` and `us_sam_exclusions`.
- **OS Usmanov record**: `Mr Alisher Burkhanovich Usmanov` — `sanction | debarment | role.oligarch | corp.disqual | role.rca | export.control` — on `us_ofac_sdn`, `us_sam_exclusions`.
- **ICIJ Usmanov officer records**: 27 entries naming Alisher Usmanov or Irina Viner Usmanova in Panama / Paradise Papers.
- **Live UK CH search** (via `verify_metalloinvest_uk_ch.py`): zero UK CH entities named "Metalloinvest".

#### What appears to be the issue
A potential **sanctions-adjacent UK property ownership** finding, **subject to a key qualification**: the connection runs through brand-identity between Ledra Trustee Services Limited (UK property owner) and Ledra Services Limited (the Cyprus nominee named in Panama Papers as officer for the BVI Metalloinvest entities). We have not established corporate parent/subsidiary identity between those two entities from this data alone.

#### Why anyone would care
- **Sanctions-adjacent public interest** — if the corporate link survives separate registry verification, this is a Mayfair flat in the asset-holding chain of a US-sanctioned Russian oligarch.
- **Politically-exposed proximity** — Usmanov is a household name in UK sanctions reporting; an entity that holds UK property and shares a brand with a documented nominee for his offshore structure is a story regardless of whether the corporate link is verified, provided the framing is precise.

#### Evidence chain
1. **OCOD**: `LEDRA TRUSTEE SERVICES LIMITED` (Cyprus) owns 2 Mayfair titles, including 45 Green Street W1K 7FX, no UK ROE filing.
2. **OS**: `Ledra Trustee Services Limited` tagged `debarment | sanction`.
3. **ICIJ Panama Papers**: two BVI Metalloinvest-named entities (`METALLOINVEST (BVI) LIMITED`, `METALLOINVEST HOLDINGS B.V.I) LIMITED`) officered by `Ledra Services Limited` (Cyprus, distinct from but brand-shared with the UK property owner), alongside `METALLOINVEST HOLDINGS (CYPRUS) LIMITED` (Cyprus) and Bridgewater Nominees (IOM).
4. **OS**: Holdingovaya Kompaniya Metalloinvest AO on US OFAC SDN; Alisher Usmanov on US OFAC SDN.
5. **Conclusion**: the brand-identity chain is documented; the corporate-identity chain between the two Ledra entities is *not* documented from this data alone.

#### Red flags and caveats
- **Brand vs corporate identity.** `LEDRA TRUSTEE SERVICES LIMITED` (the UK property owner) and `Ledra Services Limited` (the Panama Papers nominee) are different corporate names. They share "Ledra" branding and a Cyprus jurisdiction; we do not have a parent/subsidiary edge in this data. Saying "the same firm" is wrong; saying "a member of the same Cyprus service-provider family" is supported.
- **No direct Usmanov edge.** Of the 27 Usmanov officer records in ICIJ, zero are direct officers of the two BVI Metalloinvest entities. The structure layers nominees (Cyprus + Isle of Man) between Usmanov and the BVI shells — by design.
- **The Metalloinvest BVI name is typo'd.** "METALLOINVEST HOLDINGS B.V.I) LIMITED" with the stray paren is the data quality of the original BVI registry record. Separate BVI registry pull recommended.
- **Live UK CH search confirms no UK Metalloinvest entity.** Two "Usmanov"-named UK companies exist (`USMANOV LTD`, `VK USMANOVA LIMITED`) but are not, without further evidence, linked to Alisher Usmanov.

#### What is missing before publication
- **Cyprus corporate registry pull** for `LEDRA TRUSTEE SERVICES LIMITED` and `Ledra Services Limited` to establish or refute a corporate parent/subsidiary or common-ownership link.
- **BVI corporate registry pull** for the two BVI Metalloinvest entities to confirm beneficial-owner declarations (likely unavailable to public, but worth attempting via the BVI's gazette filings).
- **Pull the OFAC press release for Usmanov** that establishes the Metalloinvest control relationship (US Treasury has been explicit about this in 2022).
- **Right of reply** to LEDRA TRUSTEE SERVICES LIMITED at the Mayfair address and to the Cyprus correspondence (`15 Agiou Pavlou Street, Ledra House, Nicosia 1105`).
- **Lawyer review** with particular focus on whether the brand-identity framing is supportable as published or whether the entire Ledra-Metalloinvest-Usmanov chain should be held back pending corporate registry confirmation.

#### Verdict
**Useful context only; rework needed before lead use.** This is the highest-impact potential story in the shortlist but the most fragile without the Cyprus corporate-registry verification step. If that step succeeds, it becomes the lead. If it fails, it becomes a "brand-family" story which is harder to pitch and easier to attack.

---

### 5. Embassy Development (Battersea / Nine Elms)

#### 30-second hook
A Luxembourg-and-Jersey corporate cluster acquired £44 million of land at Nine Elms in Battersea just before the 2022 UK law forcing overseas property owners to disclose who controls them — and has not filed.

#### What the repo currently supports
- **OCOD titles**: 3 across three related SPVs (`EMBASSY DEVELOPMENT E S.A.R.L`, `EMBASSY DEVELOPMENT F S.A R.L`, `EMBASSY DEVELOPMENT LIMITED`).
- **Countries**: Luxembourg (2), Jersey (1).
- **Sample title**: `Plot E, Nine Elms Park, Nine Elms Lane, London SW8 5BB`, **price-paid £44,267,787**, acquired 15 February 2022.
- **Address co-tenancy**: 2 of the 3 SPVs share the Luxembourg correspondence `14-16 Avenue Pasteur, L-2130, Luxembourg`.
- **OS record**: `EMBASSY DEVELOPMENT LIMITED` flagged `debarment | sanction`.
- **No ICIJ leak presence** for any of the three Embassy Development entities.
- **No UK ROE filing** found in our anti-join.

#### What appears to be the issue
A high-value pre-ECTEA acquisition by a layered Luxembourg/Jersey SPV cluster with no UK Register of Overseas Entities filing. OS-flagged but anonymous as to ultimate ownership.

#### Why anyone would care
- **High-value UK property** (£44M+ single title).
- **Recognisable location**: Battersea regeneration zone, US Embassy site neighbourhood.
- **ECTEA-timing optics**: acquired Feb 2022 — six months before commencement — and still has not registered as the Act required.

#### Red flags and caveats
- **Pre-ECTEA acquisition.** Title acquired Feb 2022, which is before the Act came into force in Aug 2022. Falls under the transitional regime that ran to 31 Jan 2023. We do not know whether they then filed late (we assume not from the anti-join, but verify).
- **OS topic `debarment + sanction` without a named person.** Anonymous. The debarment record needs to be looked up to establish who the OS-flagged listing actually concerns.
- **No ICIJ leak overlap.** This is unusual for high-value offshore-secrecy concealment; suggests the SPVs are conventional project-financing vehicles for the Nine Elms development rather than secrecy vehicles. Worth treating as conventional non-compliance, not necessarily concealment.

#### What is missing before publication
- Lookup of the specific OS debarment-list source for `EMBASSY DEVELOPMENT LIMITED` (which debarment list, when, why).
- Cross-reference against the Nine Elms development consortium public filings (the project has UK-incorporated developer arms; expect names to be findable).
- Live UK CH ROE register search for all three Embassy Development name variants.

#### Verdict
**Useful context only.** Strong on visible facts (£44M, recognisable site, exact date) but weak on a chargeable wrongdoing thread.

---

### 6. Edokpolo / EKO IRE LIMITED

#### 30-second hook
A British Virgin Islands company named EKO IRE LIMITED, set up via the Alcogal law firm leaked in the Pandora Papers, owns 5 UK property titles — one of them a room in the Park Plaza Westminster Bridge hotel — and has not filed under the UK Register of Overseas Entities.

#### What the repo currently supports
- **OCOD titles**: 5. Sample: `Room 1285, Park Plaza Westminster Bridge, 200 Westminster Bridge Road, London (SE1 7UT)`, acquired 25 August 2010.
- **Country of incorporation**: British Virgin Islands.
- **Proprietor correspondence**: `PO Box 1490, Edokonsult, Lagos, Nigeria, 2 Tower Street, London WC2H 9NP`.
- **ICIJ Pandora Papers (Alcogal)**: entity `EKO IRE LIMITED` (BVI), officers `GRACE OSEMWONYEMWEN EDOKPOLO`, `OSATOHANWEN ARISTOTLE EDOKPOLO`, `OSAROBO EDWARD EDOKPOLO`.
- **No UK ROE filing**.

#### What appears to be the issue
ECTEA non-compliance by a BVI vehicle that is, per the Pandora Papers, a family asset-holding company. No sanctions overlap, no PEP overlap, no wrongdoing tag.

#### Why anyone would care
- **Offshore / leak overlap** — entity directly named in Pandora Papers via Alcogal.
- **Disclosure rule** — ROE filing required, not done.

But the public-interest framing is weak: the Edokpolos are private individuals, not public figures or sanctioned persons, and the property scale (5 titles, including hotel rooms) is small.

#### Red flags and caveats
- **Naming private individuals carries defamation risk** without a sanctions/PEP/wrongdoing tag.
- Park Plaza Westminster Bridge is the hotel-condo scheme — one of the 5 titles is a single hotel room, not a luxury home (see SE1 deepdive).
- The Edokonsult Lagos address suggests a Nigerian family business; legitimate offshore holding by a non-UK family is not in itself remarkable, even where ECTEA registration is required.

#### What is missing before publication
- A clear public-interest hook beyond bare ROE non-compliance. Without sanctions or PEP overlap, the Edokpolo story does not justify naming a private family.

#### Verdict
**Discard for lead use.** Useful in aggregate tables as one of the 622 ICIJ-overlap entries, not as a named hero.

---

### 7. Harmony Ridge Limited

#### 30-second hook
A single Kensington flat is owned by a Jersey company whose name also appears in the Panama and Paradise Papers as a BVI entity flagged by OpenSanctions as sanction-linked.

#### What the repo currently supports
- **OCOD title**: 1. `Flat 7, 27 and 29 Hornton Street, London W8 7NR`, £749,500, acquired 26 May 2010.
- **Country of incorporation (OCOD-side)**: Jersey.
- **ICIJ entity hits**: `Harmony Ridge Holdings Ltd` (BVI, Panama Papers) and `Harmony Ridge Limited` (BVI, Paradise Papers – Appleby).
- **OS record**: `Harmony Ridge Limited` flagged `corp.offshore | sanction.linked`.
- **No UK ROE filing**.

#### Red flags and caveats
- **Jurisdictional mismatch**: OCOD records Jersey; ICIJ records BVI. Possibly a re-domiciliation; possibly two distinct entities sharing a name. We cannot assume same-entity without separate registry verification.
- **Single title; small in scale.**
- **`sanction.linked` is the weakest OS sanctions topic** (linked, not direct).

#### Verdict
**Discard.** Too thin a thread for a lead; the jurisdictional mismatch is the right reason to leave it out.

---

## Source artefacts referenced

| File | Provenance |
|---|---|
| `docs/case_study_roe_noncompliance.md` | Master case-study writeup |
| `docs/about.md` | Single-page overview |
| `roe_noncompliance.json` | v1 OCOD × OE-registry anti-join (5,298 props / 12,181 titles) |
| `roe_noncompliance_personalize.json` | ICIJ officer + OS sanctions + date split (post-Aug-2022 = 733) |
| `roe_noncompliance_strict.json` | v2 matcher with fuzzy second-pass (4,174 / 9,198) |
| `roe_noncompliance_drill.json` | Earlier ICIJ-overlap + geo + date drill (v2 had OS=0 bug; rerun in personalize) |
| `named_threads_deepdive.json` | Per-target deepdive for the 4 OS-flagged hits + Edokpolo |
| `named_threads_expand.json` | Address co-tenancy + officer-edge expansion across the 5 threads |
| `fenland_deepdive.json` | Full Fenland title list, 480 Fenech officers in ICIJ |
| `metalloinvest_verify.json` | Full ICIJ + OS records for Metalloinvest and Usmanov |
| `metalloinvest_uk_ch.json` | Live UK CH search confirming no UK Metalloinvest entity |
| `aar_igt_verify.json` | The 2 remaining OS hits drill (AAR downgrade, IGT verified) |
| `se1_deepdive.json` | SE1 cluster reframing (88% Park Plaza hotel-condo) |
| `scripts/probe_roe_noncompliance.py` | Anti-join generator |
| `scripts/probe_roe_noncompliance_strict.py` | Fuzzy second-pass matcher |
| `scripts/probe_roe_noncompliance_personalize.py` | ICIJ + OS + dates personaliser |
| `scripts/probe_named_threads_deepdive.py` | Per-target deepdive (FENLAND etc.) |
| `scripts/probe_named_threads_expand.py` | Co-tenancy + officer expansion |
| `scripts/probe_fenland_deepdive.py` | FENLAND-specific drill |
| `scripts/probe_metalloinvest_verify.py` | Metalloinvest / Usmanov verification |
| `scripts/verify_metalloinvest_uk_ch.py` | Local live UK CH search |
| `scripts/probe_aar_igt_verify.py` | AAR + IGT drill |
| `scripts/probe_se1_deepdive.py` | SE1 geographic deepdive |
| `scripts/ingest_uk_ch_overseas_entities.py` | Bulk UK CH OE-prefix extract |
| `data/uk_ch_overseas_entities.parquet` | 30,221 OE-registered entities (May 2026 snapshot) |
