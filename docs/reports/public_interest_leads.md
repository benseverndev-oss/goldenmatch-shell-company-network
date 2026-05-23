# Public-Interest Lead Ranking

## Status

Machine-generated triage. **Not an allegation of wrongdoing.** Every candidate is a public-interest *lead* requiring human review before any publication. Sector and harm labels are weak (substring matches against entity names and addresses) and may be wrong.

## Executive verdict

The top three leads as ranked by `public_interest_score` are:

1. **IGT Intergestions Trust Reg.** (score 39). A US-OFAC-sanctioned Liechtenstein trust enterprise is recorded as proprietor of five UK Land Registry titles on Highgate West Hill, including a building called Bromwich House at 1 Witanhurst Lane, with no matching filing found on the UK Register of Overseas Entities.
2. **TRADE INITIATIVE ESTABLISHMENT** (score 30). A 1968 Liechtenstein establishment on the US OFAC sanctions list is registered at the same Vaduz address as IGT Intergestions Trust Reg, the sanctioned entity that owns five Highgate land titles in London.
3. **FENLAND LIMITED** (score 27). A single Isle-of-Man-administered company is recorded as proprietor of 313 residential property titles concentrated in prime West London, with no matching filing found on the UK Register of Overseas Entities.

## Why this exists

Generic compliance gaps (a missing register filing here, an ICIJ overlap there) are hard for the public to care about. This report ranks leads where hidden ownership intersects with public harm, public money, sanctions, court findings, or regulated services, in a way a normal person can understand in one sentence.

## Scoring model

```
public_interest_score =
  3 * bad_actor_evidence
+ 3 * public_money_or_public_harm
+ 2 * concealment_structure
+ 2 * property_visual_clarity
+ 1 * offshore_complexity
- 3 * false_positive_risk
- 2 * legal_risk
```

Each component is scored 0-5. The formula is transparent on purpose: anyone can recompute any candidate's score from the per-component values.

Recommendation buckets (based on the score alone — manual override is expected):

| Score | Recommendation |
|---:|---|
| ≥ 35 | **lead** |
| 25-34 | strong_backup |
| 15-24 | needs_manual_review |
| 5-14 | use_as_context |
| −5 to 4 | downgrade |
| < −5 | discard |

## Top ranked leads

| Rank | Entity | One-sentence story | Why anyone would care | Sector / asset type | Evidence strength | Public-interest score | FP risk | Legal risk | Recommendation |
|---:|---|---|---|---|---|---:|---:|---:|---|
| 1 | IGT Intergestions Trust Reg. | A US-OFAC-sanctioned Liechtenstein trust enterprise is recorded as proprietor of five UK Land Registry titles on Highgate West Hill, including a building called Bromwich House at 1 | The US Treasury sanctioned this entity under its Russia-related Executive Order 14024 programme. The UK created a public Register of Overseas Entities in 2022 specifically so that  |  / prime central London land + building | BA=5/PM=2/CS=4/PVC=5/OC=4 | 39 | 0 | 2 | lead |
| 2 | TRADE INITIATIVE ESTABLISHMENT | A 1968 Liechtenstein establishment on the US OFAC sanctions list is registered at the same Vaduz address as IGT Intergestions Trust Reg, the sanctioned entity that owns five Highga | It is the primary OFAC target. IGT, the entity actually holding the UK property, is OFAC-listed as a 'Linked To' entity of Trade Initiative. | financial_secrecy / (no direct UK property in OCOD under this name; structurally linked to IGT's 5 Highgate titles) | BA=5/PM=1/CS=4/PVC=2/OC=4 | 30 | 0 | 2 | strong_backup |
| 3 | FENLAND LIMITED | A single Isle-of-Man-administered company is recorded as proprietor of 313 residential property titles concentrated in prime West London, with no matching filing found on the UK Re | 313 prime West London residential properties held by one overseas-incorporated company with no UK Register of Overseas Entities filing is exactly the situation ECTEA 2022 was desig | housing_leasehold / prime West London residential portfolio | BA=2/PM=3/CS=4/PVC=5/OC=3 | 27 | 1 | 3 | strong_backup |
| 4 | PROFITABLE PLOTS PTE LTD | A Singapore company called Profitable Plots Pte Ltd, whose principals were convicted in a 2014 UK land-banking fraud case, is recorded in HMLR's Overseas Companies Ownership Data a | 1,335 UK property titles attributed to a single Singapore company associated with a major UK fraud prosecution sit unchanged in HMLR data for more than a decade after the convictio | public_procurement;housing_leasehold / UK land-banking plots (mass small parcels) | BA=5/PM=4/CS=2/PVC=2/OC=1 | 27 | 1 | 3 | strong_backup |
| 5 | EMBASSY DEVELOPMENT (Lux + Jersey SPV cluster) | A Luxembourg-and-Jersey corporate cluster acquired £44 million of Battersea regeneration land just before the 2022 UK overseas-ownership-disclosure law commenced, and has not been  | Nine Elms Park is part of the wider Battersea / Vauxhall public-realm regeneration scheme. A £44M single-title acquisition by an offshore SPV cluster, with no UK BO disclosure, sit | public_procurement;housing_leasehold / prime regeneration-zone development land | BA=3/PM=3/CS=4/PVC=4/OC=3 | 25 | 2 | 3 | strong_backup |
| 6 | LEDRA TRUSTEE SERVICES LIMITED | A Cyprus trustee firm is recorded as proprietor of two Mayfair flats, with no matching UK Register of Overseas Entities filing, and shares a Cyprus brand with a nominee firm that t | If the Cyprus brand-family link reflects a corporate link, this is a Mayfair property in the asset-holding chain of a sanctioned Russian oligarch. | financial_secrecy / Mayfair flats | BA=3/PM=3/CS=5/PVC=4/OC=5 | 22 | 3 | 5 | needs_manual_review |
| 7 | HEALTHCARE PROPERTY HOLDINGS LIMITED | A Jersey-incorporated company called Healthcare Property Holdings Limited is recorded as proprietor of 37 UK property titles, with no matching UK Register of Overseas Entities fili | The company name itself indicates a healthcare-sector portfolio. Beneficial ownership of healthcare-property landlords is a recognised UK public-interest concern, particularly wher | care_health;housing_leasehold / healthcare-sector property portfolio (per entity name) | BA=1/PM=4/CS=3/PVC=3/OC=2 | 19 | 2 | 2 | needs_manual_review |
| 8 | MEDICX PROPERTIES V LIMITED | MedicX Properties V Limited, a Guernsey-incorporated holder of 41 UK property titles whose name and corporate group historically operated medical-centre properties leased to NHS-fu | MedicX as a brand historically owned and leased primary-care medical centres to NHS-funded GP practices. Beneficial ownership of medical-centre landlords is a recognised UK public- | care_health;public_procurement / medical-centre / primary-care property | BA=1/PM=4/CS=3/PVC=3/OC=2 | 17 | 2 | 3 | needs_manual_review |
| 9 | WESTMINSTER BRIDGE LONDON (REAL ESTATE) B.V. + COUNTY HALL HOTEL HOLDINGS B.V. | Two related Dutch companies are recorded as proprietors of 609 UK property titles — almost all at the Park Plaza Westminster Bridge hotel — with no matching filings found on the UK | Hotel-condo schemes have been a UK consumer-protection concern. 609 titles for a single building owned by a Dutch SPV with no UK BO disclosure is at minimum a regulatory-housekeepi | asylum_hotels;public_procurement / hotel-condo room titles (1,019-room hotel) | BA=0/PM=3/CS=2/PVC=3/OC=2 | 16 | 1 | 1 | needs_manual_review |
| 10 | EKO IRE LIMITED | A British Virgin Islands company set up via the Pandora-Papers-leaked Alcogal law firm is recorded as proprietor of five UK property titles — including a room in the Park Plaza Wes | Small scale and no sanctions overlay; use as case-study context rather than a lead. The Pandora-Papers documentary trail is independently corroborative of the offshore-secrecy patt | financial_secrecy / mixed UK property incl. one hotel-condo room | BA=1/PM=1/CS=4/PVC=3/OC=3 | 12 | 1 | 4 | use_as_context |
| 11 | THE GAS TRANSPORTATION COMPANY LIMITED | A Guernsey company called The Gas Transportation Company Limited is recorded as proprietor of 41 UK property titles, in a sector — gas pipeline / utility infrastructure — with mate | If the company is a UK gas distribution-network or pipeline infrastructure owner, beneficial ownership disclosure is directly material to UK energy policy and consumer billing. | regulated_infra / gas / utility infrastructure (per entity name) | BA=1/PM=3/CS=3/PVC=2/OC=2 | 11 | 3 | 2 | use_as_context |
| 12 | HARMONY RIDGE LIMITED | A single Kensington flat is recorded as owned by a Jersey company that shares a name with a separately-incorporated BVI entity in the Panama and Paradise Papers tagged by OpenSanct | Single-title; useful only as a name-pattern example. | housing_leasehold / single Kensington flat | BA=2/PM=1/CS=3/PVC=2/OC=2 | 3 | 4 | 3 | downgrade |
| 13 | AAR INTERNATIONAL INC | A US aerospace maintenance company subject to historical US arms-export-controls enforcement is recorded as proprietor of one UK aircraft title parked near Gatwick airport, with no | False-positive downgrade example. OS tagged AAR International with crime.traffick, but the topic refers to historical US Directorate of Defense Trade Controls (ITAR) arms-export en | regulated_infra / one aircraft / aviation parking title | BA=2/PM=0/CS=0/PVC=2/OC=0 | -10 | 4 | 4 | discard |
| 14 | UK CH disqualified-directors x ICIJ matches (multiple) | An earlier attempt to match UK Companies House disqualified directors against the ICIJ leak corpus surfaced ~219 distinct unique-on-both-sides names including well-known sanctioned | Downgrade / methodology example. Demonstrates why dataset-name (OpenSanctions 'gb_coh_disqualified') vs underlying-source-truth checks matter. | financial_secrecy / (none — leads track) | BA=1/PM=1/CS=1/PVC=0/OC=1 | -14 | 5 | 4 | discard |

## Lead profiles

### 1. IGT Intergestions Trust Reg.

#### One-sentence story

A US-OFAC-sanctioned Liechtenstein trust enterprise is recorded as proprietor of five UK Land Registry titles on Highgate West Hill, including a building called Bromwich House at 1 Witanhurst Lane, with no matching filing found on the UK Register of Overseas Entities.

#### Why anyone would care

The US Treasury sanctioned this entity under its Russia-related Executive Order 14024 programme. The UK created a public Register of Overseas Entities in 2022 specifically so that overseas owners of UK property would have to disclose who controls them. This entity has not been found on that register.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 5 title(s); N6 6LT, N6 6LU; sector tags `(unclassified)`
- **Overseas entity**: IGT Intergestions Trust Reg. (Liechtenstein)
- **UK ROE filing**: no matching filing found
- **ICIJ leak overlap**: not in ICIJ data
- **OpenSanctions overlap**: US OFAC SDN (RUSSIA-EO14024), us_sam_exclusions, ext_us_ofac_press_releases, ua_war_sanctions, opencorporates, ext_gleif, permid, us_trade_csl; OFAC remarks: '(Linked To: TRADE INITIATIVE ESTABLISHMENT)'
- **Companies House live check**: no UK Companies House entry under any of 11 tested variants or Liechtenstein company number or LEI (live search 22 May 2026)
- **Court / regulatory evidence**: (none in current artefacts)
- **Sanctions / enforcement evidence**: OFAC SDN entry id=42998, Program RUSSIA-EO14024, Linked To TRADE INITIATIVE ESTABLISHMENT. Liechtenstein company number FL-0001.513.056-8, LEI 391200PWMHBZMLPKTA05. Established 20 Aug 1993.

#### What the repo supports

Source files referenced:

- aar_igt_verify.json
- docs/reports/hero_example_igt_intergestions.md
- docs/reports/hero_example_igt_pre_publication_checks.md
- docs/reports/hero_example_igt_publication_readiness.md
- docs/reports/hero_example_igt_current_ownership.md
- docs/reports/hero_example_igt_screenshots.md
- docs/reports/screenshots/06_ofac_sdn_search_results_intergestions.png
- docs/reports/screenshots/07_ofac_sdn_details_igt.png

#### What is still missing

- Buy 5 HMLR title registers (£7 × 5 = £35) for definitive current ownership
- Pull the OFAC press release that names TRADE INITIATIVE ESTABLISHMENT for the underlying-control rationale
- Pull the Liechtenstein commercial register entry FL-0001.513.056-8 via justizportal.li
- Camden planning portal check on Bromwich House to clarify the Witanhurst-estate relationship
- Lawyer review with explicit attention to the entity-not-person framing

#### Safe sentence

> A Liechtenstein-registered trust enterprise on the US Treasury OFAC Specially Designated Nationals list (IGT Intergestions Trust Reg., Liechtenstein company number FL-0001.513.056-8, designated under the Russia-related Executive Order 14024 programme as a linked entity of another OFAC-sanctioned entity, TRADE INITIATIVE ESTABLISHMENT) has been recorded since April 2013 as the proprietor of five UK Land Registry titles on Highgate West Hill, north London, with no matching filing found on the UK Register of Overseas Entities.

#### Caveats

- Slide-10 safe sentence uses 'recorded since 2013 as the proprietor' until live title-register purchases confirm current state
- OFAC SDN designation is a US listing; UK financial sanctions (OFSI) is a separate regime that should be confirmed
- No individual beneficial owner is named in the data — entity-level claim only
- Bromwich House at 1 Witanhurst Lane is in the curtilage of the Witanhurst estate but the title-register purchase is required before claiming any relationship to the wider estate

#### Score breakdown

bad_actor_evidence: 5, public_money_or_public_harm: 2, concealment_structure: 4, property_visual_clarity: 5, offshore_complexity: 4, false_positive_risk: 0, legal_risk: 2 → **public_interest_score = 39** → recommendation: **lead**


### 2. TRADE INITIATIVE ESTABLISHMENT

#### One-sentence story

A 1968 Liechtenstein establishment on the US OFAC sanctions list is registered at the same Vaduz address as IGT Intergestions Trust Reg, the sanctioned entity that owns five Highgate land titles in London.

#### Why anyone would care

It is the primary OFAC target. IGT, the entity actually holding the UK property, is OFAC-listed as a 'Linked To' entity of Trade Initiative.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 0 title(s); (c/o IGT Intergestions Trust Reg., Aeulestrasse 30, Vaduz); sector tags `financial_secrecy`
- **Overseas entity**: TRADE INITIATIVE ESTABLISHMENT (Liechtenstein)
- **UK ROE filing**: not directly an OCOD proprietor; linked via IGT
- **ICIJ leak overlap**: not in ICIJ data
- **OpenSanctions overlap**: US OFAC SDN (RUSSIA-EO14024); SDN id 42997; LI company number FL-0001.026.862-1; established 27 Nov 1968
- **Companies House live check**: not on UK CH
- **Court / regulatory evidence**: (none in current artefacts)
- **Sanctions / enforcement evidence**: OFAC SDN id=42997, Program RUSSIA-EO14024

#### What the repo supports

Source files referenced:

- aar_igt_verify.json
- docs/reports/hero_example_igt_screenshots.md
- docs/reports/screenshots/09_ofac_sdn_details_trade_initiative.png

#### What is still missing

- Pull the underlying OFAC press release naming Trade Initiative
- Liechtenstein register entry FL-0001.026.862-1
- Trace any other Liechtenstein vehicles operating from the same Aeulestrasse address

#### Safe sentence

> Trade Initiative Establishment, a Liechtenstein company on the US OFAC Specially Designated Nationals list under the Russia-related Executive Order 14024 programme, is registered at the same Vaduz correspondence address as IGT Intergestions Trust Reg, the OFAC-sanctioned entity that is the recorded proprietor of five UK Land Registry titles in Highgate, London.

#### Caveats

- Not a direct UK property owner in OCOD; story angle is the IGT linkage
- Use as context for the IGT lead rather than as a separate hero candidate

#### Score breakdown

bad_actor_evidence: 5, public_money_or_public_harm: 1, concealment_structure: 4, property_visual_clarity: 2, offshore_complexity: 4, false_positive_risk: 0, legal_risk: 2 → **public_interest_score = 30** → recommendation: **strong_backup**


### 3. FENLAND LIMITED

#### One-sentence story

A single Isle-of-Man-administered company is recorded as proprietor of 313 residential property titles concentrated in prime West London, with no matching filing found on the UK Register of Overseas Entities.

#### Why anyone would care

313 prime West London residential properties held by one overseas-incorporated company with no UK Register of Overseas Entities filing is exactly the situation ECTEA 2022 was designed to make visible.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 313 title(s); W14, SW5, W8, W2, SW7, SW1V, SW10; sector tags `housing_leasehold`
- **Overseas entity**: FENLAND LIMITED (Isle of Man (OCOD); Malta (ICIJ Paradise Papers record))
- **UK ROE filing**: no matching filing found
- **ICIJ leak overlap**: FENLAND LIMITED (Malta, Paradise Papers); FENLAND INC. (Panama Papers, bearer)
- **OpenSanctions overlap**: (none in current artefacts)
- **Companies House live check**: no UK CH entry
- **Court / regulatory evidence**: (none in current artefacts)
- **Sanctions / enforcement evidence**: (none in current artefacts)

#### What the repo supports

Source files referenced:

- fenland_deepdive.json
- named_threads_expand.json
- docs/case_study_roe_noncompliance.md

#### What is still missing

- IOM Companies Registry entry for FENLAND LIMITED — confirm directors and status
- Malta Business Registry entry for FENLAND LIMITED — confirm whether IOM and Malta entities are the same
- Spot-check 10 HMLR title registers
- Right of reply to FENLAND LIMITED via IOM corp-services address

#### Safe sentence

> FENLAND LIMITED, an Isle-of-Man-administered company, is recorded in HM Land Registry's Overseas Companies Ownership Data as the proprietor of 313 UK property titles concentrated in prime West London postcodes. The UK Register of Overseas Entities at Companies House contains no matching filing under that name. The Paradise Papers contains a Malta corporate registry record for an entity of the same name with named officers Lilian Fenech and Lawrence Fenech.

#### Caveats

- No sanctions or adverse-evidence tag on FENLAND LIMITED or the named Fenech officers
- Fenech is a common Maltese surname — Yorgen Fenech name appears in the same Paradise Papers Malta corporate-registry leak but there is NO graph edge linking him to FENLAND LIMITED; do not imply otherwise
- Lilian and Lawrence Fenech are private individuals; the story is entity-level
- IOM-OCOD vs Malta-Paradise-Papers entity-identity needs separate registry verification

#### Score breakdown

bad_actor_evidence: 2, public_money_or_public_harm: 3, concealment_structure: 4, property_visual_clarity: 5, offshore_complexity: 3, false_positive_risk: 1, legal_risk: 3 → **public_interest_score = 27** → recommendation: **strong_backup**


### 4. PROFITABLE PLOTS PTE LTD

#### One-sentence story

A Singapore company called Profitable Plots Pte Ltd, whose principals were convicted in a 2014 UK land-banking fraud case, is recorded in HMLR's Overseas Companies Ownership Data as proprietor of 1,335 UK property titles with no matching filing on the UK Register of Overseas Entities.

#### Why anyone would care

1,335 UK property titles attributed to a single Singapore company associated with a major UK fraud prosecution sit unchanged in HMLR data for more than a decade after the convictions. The status of those titles — frozen, compensation-pool, or actively held — is a recognised public-interest question.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 1335 title(s); (mass plots across UK — title-level audit required); sector tags `public_procurement;housing_leasehold`
- **Overseas entity**: PROFITABLE PLOTS PTE LTD (Singapore)
- **UK ROE filing**: no matching filing found in OCOD-vs-OE-registry anti-join
- **ICIJ leak overlap**: not surfaced
- **OpenSanctions overlap**: not directly tagged in current artefacts
- **Companies House live check**: not on UK CH OE register (per anti-join)
- **Court / regulatory evidence**: 2014 UK Serious Fraud Office prosecution and convictions; reportable
- **Sanctions / enforcement evidence**: The principals were convicted of fraud; the company entity itself is the public-record holder of the residual property titles

#### What the repo supports

Source files referenced:

- roe_noncompliance.json
- docs/case_study_roe_noncompliance.md

#### What is still missing

- Confirm the SFO case (R v Profitable Plots / Land Options International) names this exact entity
- Confirm the SFO civil-recovery / confiscation status of the 1,335 titles — frozen, compensation-pool, or actively held?
- Cross-reference with UK CH disqualified-officers register for the named principals
- Title-level audit of a sample of the 1,335 titles to understand the asset class
- Right of reply via the Singapore registered office

#### Safe sentence

> PROFITABLE PLOTS PTE LTD, a Singapore company whose principals were convicted in a 2014 UK Serious Fraud Office land-banking prosecution, is recorded in HM Land Registry's Overseas Companies Ownership Data as proprietor of 1,335 UK property titles, with no matching filing on the UK Register of Overseas Entities. The current operational status of the company and the title pool — including whether the titles are subject to receivership, confiscation, or compensation proceedings — has not been independently verified in this work.

#### Caveats

- The principals' convictions are court-record fact; the company entity is separate from the convicted individuals
- 1,335 titles in OCOD does NOT mean active concealment — these may be SFO-frozen / receiver-held assets in a long-running compensation process
- The 'no ROE filing' point is genuinely interesting either way: if the company is dormant / under receivership, the question shifts to who is responsible for the filing
- The status of the underlying investors / claimants in the 2014 case is reportable; the company-level ROE finding is the news angle

#### Score breakdown

bad_actor_evidence: 5, public_money_or_public_harm: 4, concealment_structure: 2, property_visual_clarity: 2, offshore_complexity: 1, false_positive_risk: 1, legal_risk: 3 → **public_interest_score = 27** → recommendation: **strong_backup**


### 5. EMBASSY DEVELOPMENT (Lux + Jersey SPV cluster)

#### One-sentence story

A Luxembourg-and-Jersey corporate cluster acquired £44 million of Battersea regeneration land just before the 2022 UK overseas-ownership-disclosure law commenced, and has not been found on the UK Register of Overseas Entities.

#### Why anyone would care

Nine Elms Park is part of the wider Battersea / Vauxhall public-realm regeneration scheme. A £44M single-title acquisition by an offshore SPV cluster, with no UK BO disclosure, sits in a sector — UK regeneration land — with material public-money exposure.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 3 title(s); Plot E, Nine Elms Park, Nine Elms Lane, London SW8 5BB; sector tags `public_procurement;housing_leasehold`
- **Overseas entity**: EMBASSY DEVELOPMENT (Lux + Jersey SPV cluster) (Luxembourg + Jersey)
- **UK ROE filing**: no matching filing found
- **ICIJ leak overlap**: no ICIJ leak presence
- **OpenSanctions overlap**: EMBASSY DEVELOPMENT LIMITED tagged debarment + sanction by OS (source needs lookup)
- **Companies House live check**: no UK CH OE register entry
- **Court / regulatory evidence**: (none in current artefacts)
- **Sanctions / enforcement evidence**: OS topic debarment + sanction — primary source lookup pending

#### What the repo supports

Source files referenced:

- named_threads_deepdive.json
- named_threads_expand.json
- roe_noncompliance_personalize.json

#### What is still missing

- Look up the specific OS source for the debarment+sanction tag on EMBASSY DEVELOPMENT LIMITED
- Cross-reference Nine Elms development consortium public filings for the project sponsor
- Live UK CH OE-register search for all three name variants
- Confirm pre-ECTEA acquisition status (acquired Feb 2022, ECTEA commenced Aug 2022; transitional deadline 31 Jan 2023)

#### Safe sentence

> Three related SPVs — EMBASSY DEVELOPMENT E S.A.R.L (Luxembourg), EMBASSY DEVELOPMENT F S.A R.L (Luxembourg), and EMBASSY DEVELOPMENT LIMITED (Jersey) — are recorded in HM Land Registry's Overseas Companies Ownership Data as proprietors of three UK titles in Battersea / Nine Elms, including a £44 million title at Plot E, Nine Elms Park, acquired 15 February 2022. The UK Register of Overseas Entities contains no matching filing for any of the three names.

#### Caveats

- OS debarment+sanction topic without a named individual is anonymous and needs primary-source lookup
- Acquired pre-ECTEA commencement; the breach is the failure to file by 31 Jan 2023 transitional deadline
- Zero ICIJ leak presence is unusual for high-stakes concealment; this may be conventional project-financing rather than secrecy

#### Score breakdown

bad_actor_evidence: 3, public_money_or_public_harm: 3, concealment_structure: 4, property_visual_clarity: 4, offshore_complexity: 3, false_positive_risk: 2, legal_risk: 3 → **public_interest_score = 25** → recommendation: **strong_backup**


### 6. LEDRA TRUSTEE SERVICES LIMITED

#### One-sentence story

A Cyprus trustee firm is recorded as proprietor of two Mayfair flats, with no matching UK Register of Overseas Entities filing, and shares a Cyprus brand with a nominee firm that the Panama Papers documents as registered officer of a Russian Metalloinvest BVI structure connected to US-sanctioned oligarch Alisher Usmanov.

#### Why anyone would care

If the Cyprus brand-family link reflects a corporate link, this is a Mayfair property in the asset-holding chain of a sanctioned Russian oligarch.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 2 title(s); 45 Green Street, Mayfair, London W1K 7FX (+ one further Mayfair title); sector tags `financial_secrecy`
- **Overseas entity**: LEDRA TRUSTEE SERVICES LIMITED (Cyprus)
- **UK ROE filing**: no matching filing found
- **ICIJ leak overlap**: Panama Papers nominee chain for 2 Metalloinvest-named BVI entities (via the related Cyprus brand 'Ledra Services Limited')
- **OpenSanctions overlap**: OS topics debarment + sanction for LEDRA TRUSTEE SERVICES LIMITED
- **Companies House live check**: not on UK CH OE register
- **Court / regulatory evidence**: (none in current artefacts)
- **Sanctions / enforcement evidence**: Holdingovaya Kompaniya Metalloinvest AO on us_ofac_sdn + us_sam_exclusions + ua_war_sanctions; Alisher Usmanov on us_ofac_sdn + us_sam_exclusions; OS topics for Ledra Trustee Services Limited include debarment + sanction

#### What the repo supports

Source files referenced:

- metalloinvest_verify.json
- metalloinvest_uk_ch.json
- named_threads_expand.json
- docs/case_study_roe_noncompliance.md

#### What is still missing

- Cyprus corporate registry: confirm or refute that Ledra Trustee Services Limited and Ledra Services Limited share corporate parent / common control
- BVI registry/gazette for the two BVI Metalloinvest entities
- OFAC designation paperwork for Usmanov / Metalloinvest control chain
- Right of reply to LEDRA TRUSTEE SERVICES LIMITED at Mayfair correspondence and Nicosia Ledra House
- Lawyer review of brand-vs-corporate identity framing

#### Safe sentence

> LEDRA TRUSTEE SERVICES LIMITED, a Cyprus-registered trustee firm, is recorded as proprietor of two Mayfair property titles in HMLR's Overseas Companies Ownership Data, with no matching filing on the UK Register of Overseas Entities. OpenSanctions applies debarment and sanction topic tags to the entity. The same Cyprus 'Ledra' service-provider brand appears in the Panama Papers as registered officer of two BVI entities named for Metalloinvest, the Russian metals holding controlled by US-OFAC-sanctioned Alisher Usmanov. The brand-identity link is documented; the corporate-identity link between LEDRA TRUSTEE SERVICES LIMITED and Ledra Services Limited needs separate Cyprus-registry verification.

#### Caveats

- BRAND identity not CORPORATE identity between LEDRA TRUSTEE SERVICES LIMITED (UK property owner) and Ledra Services Limited (Panama Papers nominee). The Cyprus registry verification is the critical gate.
- Zero direct edges in the leak graph from any Usmanov officer node to the BVI Metalloinvest entities; the structure layers nominees between Usmanov and the BVI shells by design
- The Metalloinvest BVI entity name 'METALLOINVEST HOLDINGS B.V.I) LIMITED' contains a typo in the leak record
- Do NOT publish framing as 'Usmanov-owned Mayfair flat'; the supported framing is brand-family-shared with a documented Metalloinvest nominee

#### Score breakdown

bad_actor_evidence: 3, public_money_or_public_harm: 3, concealment_structure: 5, property_visual_clarity: 4, offshore_complexity: 5, false_positive_risk: 3, legal_risk: 5 → **public_interest_score = 22** → recommendation: **needs_manual_review**


### 7. HEALTHCARE PROPERTY HOLDINGS LIMITED

#### One-sentence story

A Jersey-incorporated company called Healthcare Property Holdings Limited is recorded as proprietor of 37 UK property titles, with no matching UK Register of Overseas Entities filing.

#### Why anyone would care

The company name itself indicates a healthcare-sector portfolio. Beneficial ownership of healthcare-property landlords is a recognised UK public-interest concern, particularly where care homes and clinical sites depend on a stable landlord.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 37 title(s); (not extracted in current artefacts — manual lookup required); sector tags `care_health;housing_leasehold`
- **Overseas entity**: HEALTHCARE PROPERTY HOLDINGS LIMITED (Jersey)
- **UK ROE filing**: no matching filing found in OCOD-vs-OE-registry anti-join
- **ICIJ leak overlap**: not surfaced in current artefacts
- **OpenSanctions overlap**: not surfaced
- **Companies House live check**: not on UK CH OE register (per anti-join)
- **Court / regulatory evidence**: (none in current artefacts)
- **Sanctions / enforcement evidence**: (none in current artefacts)

#### What the repo supports

Source files referenced:

- roe_noncompliance.json
- docs/case_study_roe_noncompliance.md

#### What is still missing

- Resolve OCOD title-level addresses to confirm the portfolio actually contains healthcare assets (the company name is a weak label only)
- Live UK CH OE-register search for name variants
- Cross-reference CQC (Care Quality Commission) regulated-locations registry
- Identify operating tenants and any NHS / local-authority payments to those tenants
- Right of reply

#### Safe sentence

> HEALTHCARE PROPERTY HOLDINGS LIMITED, a Jersey-incorporated company whose name indicates healthcare-sector activity, is recorded in HMLR's Overseas Companies Ownership Data as proprietor of 37 UK property titles, with no matching filing found on the UK Register of Overseas Entities. The composition of the property portfolio and any healthcare-tenant relationships have not been independently verified.

#### Caveats

- Name-based sector classification is a weak label; some 'Healthcare Property Holdings' entities are not in fact healthcare landlords
- No adverse evidence on the entity in current artefacts
- Title-level addresses must be confirmed before claiming the portfolio is in the care sector

#### Score breakdown

bad_actor_evidence: 1, public_money_or_public_harm: 4, concealment_structure: 3, property_visual_clarity: 3, offshore_complexity: 2, false_positive_risk: 2, legal_risk: 2 → **public_interest_score = 19** → recommendation: **needs_manual_review**


### 8. MEDICX PROPERTIES V LIMITED

#### One-sentence story

MedicX Properties V Limited, a Guernsey-incorporated holder of 41 UK property titles whose name and corporate group historically operated medical-centre properties leased to NHS-funded primary care providers, has no matching UK Register of Overseas Entities filing in our anti-join.

#### Why anyone would care

MedicX as a brand historically owned and leased primary-care medical centres to NHS-funded GP practices. Beneficial ownership of medical-centre landlords is a recognised UK public-interest concern given the NHS funding flowing through them via primary-care rent reimbursements.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 41 title(s); (not extracted in current artefacts — title-level address audit required); sector tags `care_health;public_procurement`
- **Overseas entity**: MEDICX PROPERTIES V LIMITED (Guernsey)
- **UK ROE filing**: no matching filing found in OCOD-vs-OE-registry anti-join
- **ICIJ leak overlap**: not surfaced
- **OpenSanctions overlap**: not surfaced
- **Companies House live check**: not on UK CH OE register (per anti-join)
- **Court / regulatory evidence**: (none in current artefacts)
- **Sanctions / enforcement evidence**: (none in current artefacts)

#### What the repo supports

Source files referenced:

- roe_noncompliance.json
- docs/case_study_roe_noncompliance.md

#### What is still missing

- Confirm whether MEDICX PROPERTIES V LIMITED is part of the historic Octopus Healthcare / MedicX Fund group (now Octopus AHI / Primary Health Properties or successor)
- Resolve OCOD title-level addresses to confirm portfolio composition
- Live UK CH OE-register search for all MedicX Properties name variants
- NHS primary-care contract / rent-reimbursement disclosure check
- Right of reply to the Guernsey address

#### Safe sentence

> MEDICX PROPERTIES V LIMITED, a Guernsey-incorporated company, is recorded as proprietor of 41 UK property titles in HM Land Registry's Overseas Companies Ownership Data, with no matching filing found on the UK Register of Overseas Entities. The MedicX corporate group has historically held medical-centre properties leased to NHS-funded primary care providers. The current beneficial ownership of MEDICX PROPERTIES V LIMITED and the composition of its 41-title portfolio have not been independently verified in this work.

#### Caveats

- MedicX as a brand has changed hands; the current group successor needs verification before any claim about beneficial ownership
- Numbered SPVs (MedicX Properties V) often appear within a wider series; the broader fund structure should be mapped
- No adverse evidence in current artefacts

#### Score breakdown

bad_actor_evidence: 1, public_money_or_public_harm: 4, concealment_structure: 3, property_visual_clarity: 3, offshore_complexity: 2, false_positive_risk: 2, legal_risk: 3 → **public_interest_score = 17** → recommendation: **needs_manual_review**


### 9. WESTMINSTER BRIDGE LONDON (REAL ESTATE) B.V. + COUNTY HALL HOTEL HOLDINGS B.V.

#### One-sentence story

Two related Dutch companies are recorded as proprietors of 609 UK property titles — almost all at the Park Plaza Westminster Bridge hotel — with no matching filings found on the UK Register of Overseas Entities.

#### Why anyone would care

Hotel-condo schemes have been a UK consumer-protection concern. 609 titles for a single building owned by a Dutch SPV with no UK BO disclosure is at minimum a regulatory-housekeeping question.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 609 title(s); 200 Westminster Bridge Road, London SE1 7UT + 1 Addington Street SE1 7RY; sector tags `asylum_hotels;public_procurement`
- **Overseas entity**: WESTMINSTER BRIDGE LONDON (REAL ESTATE) B.V. + COUNTY HALL HOTEL HOLDINGS B.V. (Netherlands)
- **UK ROE filing**: no matching filings found
- **ICIJ leak overlap**: small (≤7 distinct names within SE1)
- **OpenSanctions overlap**: not surfaced
- **Companies House live check**: not on UK CH OE register (per anti-join)
- **Court / regulatory evidence**: (none in current artefacts)
- **Sanctions / enforcement evidence**: (none in current artefacts)

#### What the repo supports

Source files referenced:

- se1_deepdive.json
- docs/case_study_roe_noncompliance.md

#### What is still missing

- Live UK CH OE-register search for both Dutch entity names
- Confirm whether Park Plaza Westminster Bridge has a Home Office / local authority accommodation contract
- Right of reply to the Dutch operator
- Decide whether to use as a hero candidate or as a methodology / downgrade example

#### Safe sentence

> WESTMINSTER BRIDGE LONDON (REAL ESTATE) B.V. and COUNTY HALL HOTEL HOLDINGS B.V., two Dutch-incorporated companies, are recorded between them as proprietors of 609 UK property titles — the majority at the Park Plaza Westminster Bridge hotel-condo development at 200 Westminster Bridge Road, London — with no matching filings on the UK Register of Overseas Entities.

#### Caveats

- Conventional hotel-condo operator pattern, not offshore-secrecy pattern
- No adverse evidence on the Dutch operator
- Better used as a 'show your work' downgrade / methodology example than as a hero lead

#### Score breakdown

bad_actor_evidence: 0, public_money_or_public_harm: 3, concealment_structure: 2, property_visual_clarity: 3, offshore_complexity: 2, false_positive_risk: 1, legal_risk: 1 → **public_interest_score = 16** → recommendation: **needs_manual_review**


### 10. EKO IRE LIMITED

#### One-sentence story

A British Virgin Islands company set up via the Pandora-Papers-leaked Alcogal law firm is recorded as proprietor of five UK property titles — including a room in the Park Plaza Westminster Bridge hotel — with no matching UK Register of Overseas Entities filing.

#### Why anyone would care

Small scale and no sanctions overlay; use as case-study context rather than a lead. The Pandora-Papers documentary trail is independently corroborative of the offshore-secrecy pattern.

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: 5 title(s); Park Plaza Westminster Bridge SE1 7UT + others; sector tags `financial_secrecy`
- **Overseas entity**: EKO IRE LIMITED (British Virgin Islands)
- **UK ROE filing**: no matching filing found
- **ICIJ leak overlap**: EKO IRE LIMITED (BVI) named in Pandora Papers via Alemán, Cordero, Galindo & Lee (Alcogal); 3 Edokpolo-named officers
- **OpenSanctions overlap**: (none in current artefacts)
- **Companies House live check**: not on UK CH OE register
- **Court / regulatory evidence**: (none in current artefacts)
- **Sanctions / enforcement evidence**: (none in current artefacts)

#### What the repo supports

Source files referenced:

- named_threads_deepdive.json
- named_threads_expand.json

#### What is still missing

- Sanctions / PEP screening of the three named Edokpolo officers
- Live UK CH OE-register search
- Title-level audit of the 5 titles

#### Safe sentence

> EKO IRE LIMITED, a British Virgin Islands company, is recorded as proprietor of five UK property titles in HMLR's Overseas Companies Ownership Data, with no matching filing on the UK Register of Overseas Entities. The Pandora Papers contains a corresponding Alemán, Cordero, Galindo & Lee record with three Edokpolo-surname officers.

#### Caveats

- The Edokpolos are private individuals with no sanctions, PEP or wrongdoing tag in current data
- Naming the family without an independent public-interest hook beyond ROE non-compliance is high defamation risk
- Park Plaza Westminster Bridge title is the hotel-condo scheme (see SE1 deepdive)
- Use as context only

#### Score breakdown

bad_actor_evidence: 1, public_money_or_public_harm: 1, concealment_structure: 4, property_visual_clarity: 3, offshore_complexity: 3, false_positive_risk: 1, legal_risk: 4 → **public_interest_score = 12** → recommendation: **use_as_context**


## Downgrades and false positives

This section makes the ranker's downgrades explicit. Each is an example of something that *looks* like a story but, on inspection, is weaker or misleading than the headline implies.

### Downgrade — HARMONY RIDGE LIMITED

A single Kensington flat is recorded as owned by a Jersey company that shares a name with a separately-incorporated BVI entity in the Panama and Paradise Papers tagged by OpenSanctions as sanction-linked.

**Why it ranked low**: false_positive_risk=4, legal_risk=3, score=3. OCOD Jersey vs ICIJ BVI jurisdictional mismatch unresolved — likely different entities sharing a name

### Downgrade — AAR INTERNATIONAL INC

A US aerospace maintenance company subject to historical US arms-export-controls enforcement is recorded as proprietor of one UK aircraft title parked near Gatwick airport, with no matching UK Register of Overseas Entities filing.

**Why it ranked low**: false_positive_risk=4, legal_risk=4, score=-10. OS crime.traffick topic here means arms-export-controls (ITAR) enforcement, not human trafficking — easy to misread

### Downgrade — UK CH disqualified-directors x ICIJ matches (multiple)

An earlier attempt to match UK Companies House disqualified directors against the ICIJ leak corpus surfaced ~219 distinct unique-on-both-sides names including well-known sanctioned figures, but a live UK CH search confirmed none of these names is on the current UK CH disqualified-officers register.

**Why it ranked low**: false_positive_risk=5, legal_risk=4, score=-14. Discard the original disqualified-director track for naming purposes


## Next actions

### Next actions for #1 — IGT Intergestions Trust Reg.

- Buy 5 HMLR title registers (£7 × 5 = £35) for definitive current ownership
- Pull the OFAC press release that names TRADE INITIATIVE ESTABLISHMENT for the underlying-control rationale
- Pull the Liechtenstein commercial register entry FL-0001.513.056-8 via justizportal.li
- Camden planning portal check on Bromwich House to clarify the Witanhurst-estate relationship
- Lawyer review with explicit attention to the entity-not-person framing

### Next actions for #2 — TRADE INITIATIVE ESTABLISHMENT

- Pull the underlying OFAC press release naming Trade Initiative
- Liechtenstein register entry FL-0001.026.862-1
- Trace any other Liechtenstein vehicles operating from the same Aeulestrasse address

### Next actions for #3 — FENLAND LIMITED

- IOM Companies Registry entry for FENLAND LIMITED — confirm directors and status
- Malta Business Registry entry for FENLAND LIMITED — confirm whether IOM and Malta entities are the same
- Spot-check 10 HMLR title registers
- Right of reply to FENLAND LIMITED via IOM corp-services address

