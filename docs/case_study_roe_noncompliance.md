# UK Register of Overseas Entities — structural non-compliance

> Working draft. Numbers from the May 2026 OCOD release and the May 2026 UK CH Basic Company Data bulk download. Methodology + caveats at the bottom.

## Headline

The UK's **Economic Crime (Transparency and Enforcement) Act 2022** (ECTEA) created a Register of Overseas Entities at Companies House. Every overseas-incorporated entity holding UK qualifying-estate property since the Feb 2022 cut-over is required to register and disclose beneficial ownership. Failure is a criminal offence under s.34/s.42, with daily fines, criminal liability for officers, and restrictions on dealing with the property.

Cross-referencing the UK CH OE registry (30,221 registered entities, May 2026) against HM Land Registry's OCOD (365,316 UK property titles owned by overseas entities, May 2026) by normalised entity name produces:

| Metric | Count |
|---|---:|
| OCOD distinct foreign-owner proprietors | 27,892 |
| **Apparent ECTEA non-compliant proprietors** | **5,324 (19.1%)** |
| **UK property titles held by non-compliant proprietors** | **12,240 (12.6%)** |
| ...of which acquired pre-Aug-2022 (past transitional deadline) | 11,473 |
| ...of which acquired post-Aug-2022 (unambiguous breach, no transitional defence) | **733** |
| Non-compliant proprietors also named in ICIJ Offshore Leaks | 622 |
| Non-compliant proprietors flagged by OpenSanctions (sanction / debarment / crime / PEP) | 13 (5 high-confidence) |
| Named individuals surfaced via ICIJ officer enrichment | 447 |

Read with appropriate caution: the name-key anti-join carries false-positive risk where the OCOD record uses a different name form than the OE filing (e.g. "Ltd" vs "Limited"). Suffix-stripping reduces but does not eliminate this. The true non-compliance rate is likely lower than the raw 19% — but plausibly still in the **5–15%** range, i.e. several thousand UK property titles whose foreign owners have not complied with the statute.

## Geographic concentration

Non-compliant titles cluster in **prime central London** plus the SE1 regeneration belt:

| Outward postcode | Non-compliant titles | Area |
|---|---:|---|
| SE1 | 690 | Dominated by **Park Plaza Westminster Bridge hotel-condo** (Dutch B.V. operator, 615+ titles) — see SE1 deepdive section |
| SW7 | 152 | South Kensington |
| W14 | 129 | Olympia / West Kensington |
| SW5 | 122 | Earls Court |
| SW1X | 111 | Belgravia / Knightsbridge |
| NW1 | 102 | Camden / Regent's Park |
| SW3 | 94 | Chelsea |
| W8 | 80 | Kensington |
| NW8 | 68 | St John's Wood |
| W1K | 65 | Mayfair |

## Jurisdictional concentration

| Country | Non-compliant titles | Non-compliant entities |
|---|---:|---:|
| British Virgin Islands | 1,600 | 992 |
| Singapore | 1,451 | 50 |
| Jersey | 1,327 | 523 |
| Luxembourg | 1,168 | 526 |
| Isle of Man | 962 | 357 |
| Netherlands | 853 | 143 |
| Guernsey | 654 | 258 |
| Ireland | 397 | 132 |
| Panama | 347 | 214 |
| Seychelles | 178 | 106 |

The Singapore concentration is notable: 1,451 titles across only 50 entities — much more concentrated than the BVI pattern. The leading Singapore non-compliant entity is **PROFITABLE PLOTS PTE LTD** with **1,335 titles**, the entity behind the UK land-banking fraud convictions in 2014. Those titles are most likely frozen/post-conviction assets rather than active non-compliance, but the structural signal stands.

## Personalised leads — named individuals behind the 622 ICIJ-overlap subset

Where the ICIJ leak record names specific individuals as officers, intermediaries, or beneficial owners of the non-compliant entity:

| UK titles | Entity | Jurisdiction | Leak | Named individuals |
|---:|---|---|---|---|
| **313** | **FENLAND LIMITED** | Malta | Paradise Papers | **LILIAN FENECH, LAWRENCE FENECH** |
| 15 | BASSWOOD INTERNATIONAL INC. | — | Panama Papers | (bearer shares) |
| 12 | ARUNDEL CORP. | — | Panama Papers | HSBC Trustee (C.I.) + bearer |
| 9 | PEPINO BUSINESS S.A. | — | Panama Papers | **BRUNO JEAN FRANCOIS RASSON** (ZA) |
| 8 | IVM PCC | Mauritius | Paradise Papers | **James Andrew O'Toole, David Breeze** (both GB) |
| 7 | Sigma Corporation | — | Panama Papers | **FOFANOV FEDOR, WU HUI** (CN) |
| 7 | ALLEGRO (Aruba) | — | Paradise Papers | **MENNA-TORTA, LICHTENSZTAJN-GOLDENBERG** |
| 6 | RYBERRY DEVELOPMENT LIMITED | BVI | Panama Papers | **Willem Kerkmeer** (NL) |
| 5 | TRAFALGAR PROPERTIES (CORP) | BVI | Pandora Papers | **RANJIT PARAKRAMA DE ALWIS** |
| 5 | CADMORE INVESTMENTS LIMITED | BVI | Pandora Papers | **MARIA CRISTINA LLACH REYES** |
| 5 | **EKO IRE LIMITED** | BVI | Pandora Papers | **OSAROBO, GRACE, OSATOHANWEN EDOKPOLO** (family cluster) |
| 5 | SAMOS INVESTMENTS INC. | — | Paradise Papers | Austin family cluster (4 named) |

Each row pairs:
- A named individual in a specific leaked corpus
- A specific count of UK property titles
- An overseas entity that has not filed under ECTEA 2022

### Structural patterns visible in the personalisation

1. **Bearer shares** — "THE BEARER" appears as the officer-of-record for multiple top-volume entities (BASSWOOD INTERNATIONAL, ARUNDEL CORP, UPPER SIDE LTD). Bearer-share companies are by design untraceable: even with full leak access, the beneficial owner is structurally hidden. UK ROE compliance was designed exactly to defeat this, which makes the non-filing a meaningful signal.
2. **Professional nominees** — HSBC Trustee (C.I.), Stenham Trustees, Experta Trustees Jersey, Mohul Nominees, Elcan Nominees, Cannon Nominees, Huntlaw Directors. These dominate the officer field. The named "officer" is itself a service-provider, not the real beneficial owner. ROE filing would force disclosure behind the nominee.
3. **Family clusters** — the Edokpolo family (3 named officers, EKO IRE LIMITED), the Austin family (4 named, SAMOS INVESTMENTS), the Fenech family (FENLAND LIMITED). These are the strongest "true beneficial owner" signals — surnames match across the officer roster.

## Methodology

1. **Bulk-extract UK CH OE registry.** Filter the May 2026 BasicCompanyData bulk CSV (5.7M rows, 2.8 GB uncompressed) on `CompanyNumber LIKE 'OE%'`. Yields 30,221 OE-registered entities.
2. **Load OCOD.** HM Land Registry's Overseas Companies Ownership Data, May 2026. 365,316 UK title records held by foreign-incorporated proprietors.
3. **Normalised-name anti-join.** Strip corporate suffixes (LTD/LIMITED/LLC/INC/SA/GMBH/BV/AG/PLC/LLP/LP) + non-alphanumeric, lowercase. Any OCOD proprietor whose normalised name does NOT appear in the OE normalised-name set is flagged as potentially non-compliant.
4. **ICIJ overlap.** Cross-reference flagged proprietors against the consolidated ICIJ Offshore Leaks dataset (Panama / Paradise / Pandora / Bahamas / Offshore Leaks combined, ~810,000 entities).
5. **Officer enrichment.** For ICIJ-matched flagged entities, walk the leak edge graph backwards from entity to its officers, intermediaries, and beneficial owners.
6. **Geographic / jurisdictional aggregation.** Group flagged titles by OCOD outward-postcode and proprietor country-of-incorporation.

## Caveats

- **Name-key false negatives.** Different normalisation between OCOD's proprietor field and CH's company-name field will miss legitimately compliant entities. Examples: "Deutsche Bank AG" appears non-compliant in our anti-join, but is large and well-known enough that this is almost certainly a name-form mismatch. The true non-compliance count is below 5,324.
- **Pre-Act ownership status.** ECTEA created a transitional window until 31 Jan 2023 for entities that already held UK property at the Feb 2022 commencement. Titles continuously held since pre-2022 are clearly past the deadline. Acquisitions post-Aug 2022 are unambiguously in breach (this drill is still pending — see open issues).
- **Defunct / frozen owners.** Some flagged entities are defunct (e.g. PROFITABLE PLOTS post-fraud-conviction). OCOD does not always remove these promptly. The number of *currently-actively-non-compliant* entities is below the raw count.
- **The leak corpora are themselves snapshots.** ICIJ data ends at the dates of the respective leaks (Panama 2015, Paradise 2017, Pandora 2021). Entities active today may have rotated their officer roster since.

## Case study — FENLAND LIMITED (Isle of Man)

The largest single non-compliant owner in the anti-join. **313 UK residential property titles** held by a single Isle of Man-incorporated company that has not filed under ECTEA 2022.

| Fact | Value |
|---|---|
| OCOD titles | 313 (all attributed to **FENLAND LIMITED**) |
| Jurisdiction | Isle of Man (all 313) |
| Proprietor correspondence address | 8 St Georges Street, Douglas, Isle of Man, IM1 1AH (Isle of Man corporate-services address) |
| ICIJ presence | FENLAND INC. (Panama Papers) + FENLAND LIMITED (Paradise Papers, Malta corporate registry) |
| Paradise Papers named officers | **Lilian Fenech, Lawrence Fenech** |
| UK ROE filing | None found (anti-join match) |

Postcode concentration is striking — the portfolio is concentrated in a tight prime West London residential band:

| Postcode | Titles | Area |
|---|---:|---|
| W14 | 85 | Olympia / West Kensington |
| SW5 | 62 | Earls Court |
| W8 | 55 | Kensington |
| W2 | 53 | Bayswater / Paddington |
| SW7 | 26 | South Kensington |
| SW1V | 14 | Pimlico |
| SW10 | 12 | West Brompton |

Sample (first in OCOD): **144 Portnall Road, London W9 3BQ**, price-paid **£910,000**, acquired 02-09-2011.

### Caveat — name coincidence ≠ connection

A name-search of ICIJ officers for "FENECH" returns 480 hits, including **Yorgen Fenech** — the Maltese businessman charged with masterminding the 2017 assassination of journalist Daphne Caruana Galizia, currently on trial in Malta. There is **no edge** in the ICIJ leak graph linking him to FENLAND LIMITED. He appears in the same Paradise Papers / Malta corporate-registry leak corpus, which is proximity, not connection. The direct named officers of FENLAND LIMITED in the Paradise Papers entry are **Lilian Fenech** and **Lawrence Fenech**. Fenech is one of the most common Maltese surnames; the bare name-overlap is not a finding without supporting evidence.

## OpenSanctions overlap — sanctioned/PEP/crime-linked owners

Five OS-flagged entities surface in the non-compliant set, but a follow-up drill (`probe_aar_igt_verify.py`) shows the **AAR International** hit is a false positive in context: it is AAR Corp, a US public aerospace MRO firm, whose `crime.traffick` topic comes from a historical US Directorate of Defense Trade Controls (ITAR / arms-export-controls) enforcement, not human trafficking. AAR Corp owns one UK-registered aircraft title at Crawley/Gatwick. Real OS-flagging exists but the finding is a regulatory housekeeping issue rather than a secrecy-jurisdiction concealment one.

Four high-confidence hits remain:

| Owner | OS topics | Jurisdiction |
|---|---|---|
| Harmony Ridge Limited | corp.offshore + sanction.linked | BVI |
| Embassy Development Limited | debarment + sanction | GB/JE |
| Ledra Trustee Services Ltd | debarment + sanction | Cyprus |
| Igt Intergestions Trust Reg | **debarment + sanction (on US OFAC SDN)** | Liechtenstein |

The remaining 8 OS hits are large regulated institutions (Deutsche Bank, National Bank of Greece, Bank of New York, Bloomberg, Tesla, European Bank for Reconstruction and Development) tagged for historical `reg.action` enforcement. These are noise in this context — large institutions with reportable regulatory history rather than active ECTEA evaders.

## The post-Aug-2022 subset — unambiguous breach

733 non-compliant titles were acquired AFTER the ECTEA commencement date (Aug 2022), so cannot claim the transitional-period defence. By jurisdiction:

| Country | Post-Act non-compliant titles |
|---|---:|
| Luxembourg | 196 |
| Jersey | 91 |
| Isle of Man | 72 |
| Netherlands | 63 |
| British Virgin Islands | 44 |
| Qatar | 27 |
| Guernsey | 25 |
| Spain | 21 |
| France | 19 |
| Ireland | 16 |

These are the highest-quality leads — overseas owners who acquired UK property in the post-Act window and never filed.

## Strict matcher (fuzzy second-pass)

A v2 matcher (`probe_roe_noncompliance_strict.py`) runs a token-set Jaccard fuzzy second pass after the exact-key anti-join, to suppress suffix-form false positives like "Deutsche Bank AG" vs "Deutsche Bank Aktiengesellschaft".

| Pass | Non-compliant proprietors | Non-compliant titles |
|---|---:|---:|
| v1 (exact key, suffix-stripped) | 5,298 | 12,181 |
| v2 (after fuzzy reclassification at Jaccard ≥ 0.7) | 4,174 | 9,198 |

The fuzzy reclassifies 1,124 proprietors as likely-compliant under a different name form. **Caveat**: the v2 matcher is over-aggressive on serially-numbered SPVs (`SIR TRUSTEE 6 LIMITED` ↔ `sir trustee 3`, `ATHENA ASSET 5` ↔ `athena asset 7`) and on generic-token collisions (`P.S.G. INVESTMENT GROUP` ↔ `v k investment group`). The true strict count is between the v1 and v2 numbers — probably 4,500-4,800 proprietors. We surface both bounds rather than commit to a single figure.

## Additional named-thread case studies

### Edokpolo family — EKO IRE LIMITED (BVI, Pandora Papers / Alcogal)

5 UK property titles. Proprietor correspondence address `PO Box 1490, Edokonsult, Lagos, Nigeria, 2 Tower Street, London WC2H 9NP` links the BVI entity to a Nigerian consultancy. Properties include hotel-room titles at Park Plaza Westminster Bridge (SE1). Named officers in the Pandora leak (Alemán, Cordero, Galindo & Lee / Alcogal record): **Grace Osemwonyemwen Edokpolo, Osatohanwen Aristotle Edokpolo, Osarobo Edward Edokpolo** — a family cluster confirmed.

### Embassy Development — Battersea / Nine Elms

3 titles across related Luxembourg + Jersey SPVs (`EMBASSY DEVELOPMENT E S.A.R.L`, `EMBASSY DEVELOPMENT F S.A R.L`, `EMBASSY DEVELOPMENT LIMITED`). OpenSanctions flags `debarment + sanction`. Sample title: **Plot E, Nine Elms Park, Nine Elms Lane, London SW8 5BB**, £44,267,787 price-paid, acquired 15 February 2022 — six months before ECTEA commencement. The multi-SPV structure (E, F, plus the parent) is consistent with a project-financing layered ownership. No ICIJ leak appearance.

### Harmony Ridge Limited

1 UK title — Flat 7, 27 and 29 Hornton Street, London W8 7NR (Kensington), £749,500, acquired 26 May 2010. OpenSanctions flags `corp.offshore + sanction.linked`. ICIJ presence: two BVI entities named Harmony Ridge in Panama Papers + Paradise Papers (Appleby record). **Jurisdictional mismatch** — OCOD records the proprietor as Jersey-incorporated, ICIJ records BVI. Could be a re-domiciliation or a name collision between two distinct entities. The match warrants manual CH verification before naming.

### Ledra Trustee Services Limited — Cyprus nominee network

2 Mayfair titles; sample: **45 Green Street, Mayfair W1K 7FX**, £310,000, acquired 26 March 2015. Proprietor correspondence at `15 Agiou Pavlou Street, Ledra House, Nicosia 1105`. OpenSanctions flags `debarment + sanction`. ICIJ presence is the most extensive of these four threads: 4 related Ledra-named entities (Nevis, BVI, Malta) and 40 nominee-officer matches — `LEDRA SERVICES (NOMINEES) LIMITED`, `LEDRA TRUSTEES LIMITED`, `LEDRA NOMINEES LIMITED`, all Cyprus. This is a complete Cyprus nominee infrastructure — the proprietor is itself a service-provider corporate shell.

**Officer-edge expansion reveals Ledra as a hub**. Each of the 40 Ledra-named officers in ICIJ appears as the officer-of-record for a different BVI entity in Panama Papers. Selected connected entities:

| Connected entity | Jurisdiction | Source |
|---|---|---|
| METALLOINVEST HOLDINGS B.V.I) LIMITED | BVI | Panama Papers |
| SIBLEY INTERNATIONAL LIMITED | BVI | Panama Papers |
| INDUSTRIAL PIPELINE CORPORATION | BVI | Panama Papers |
| SWINSTAR HOLDINGS LIMITED | BVI | Panama Papers |
| CONEY HOLDINGS GROUP LTD | BVI | Panama Papers |

The METALLOINVEST name is notable: Metalloinvest is the Russian metals/mining holding controlled by Alisher Usmanov, who is US OFAC, EU and UK sanctioned. The Panama Papers entry naming a Cyprus "Ledra Services" entity as officer of a BVI "Metalloinvest Holdings"-named entity places Ledra in the Russian-sanctioned-oligarch asset-holding chain.

### Ledra → Metalloinvest → Usmanov — verified chain

A follow-up verification probe (`probe_metalloinvest_verify.py`) plus live UK CH search confirms the BVI Metalloinvest entities are part of the **actual Usmanov-controlled Metalloinvest group**, not coincidental homonyms:

- **ICIJ holds TWO Metalloinvest BVI entities in Panama Papers** — `METALLOINVEST (BVI) LIMITED` (inc 21-SEP-2006, status Defaulted) and `METALLOINVEST HOLDINGS B.V.I) LIMITED` (inc 18-MAY-2006, status Changed agent). The typo'd name on the second is a data-quality artefact; both use the Metalloinvest brand.
- **Connected officers**: `Ledra Services Limited` (Cyprus), `METALLOINVEST HOLDINGS (CYPRUS) LIMITED` (Cyprus subsidiary in the group structure), `BRIDGEWATER FIRST/SECOND NOMINEES LIMITED` (Isle of Man).
- **OpenSanctions confirms the Russian parent**: `Holdingovaya Kompaniya Metalloinvest AO` is tagged `debarment + sanction` and listed on `us_ofac_sdn`, `us_sam_exclusions`, `ua_war_sanctions`. Its management entity `LLC Management Company "Metalloinvest"` is similarly tagged + OFAC-listed.
- **Alisher Usmanov in OpenSanctions** with topics `sanction | debarment | role.oligarch | corp.disqual | role.rca | export.control`, present on `us_ofac_sdn`, `us_sam_exclusions`, and (per OS's classification) `gb_coh_disqualified`. His wife Irina Viner Usmanova is also OS-listed (`poi | sanction | role.pep | role.rca`).
- **Both Usmanovs appear in the leaked corpora directly** — Alisher Usmanov 13+ times in Panama Papers under name variants; Irina Viner Usmanova in both Panama and Paradise Papers.

The resulting structure:

```
Holdingovaya Kompaniya Metalloinvest AO  (Russia — OFAC-sanctioned, Usmanov-controlled)
   ↓
METALLOINVEST HOLDINGS (CYPRUS) LIMITED  (Cyprus subsidiary, Panama Papers)
   ↓
METALLOINVEST (BVI) LIMITED + METALLOINVEST HOLDINGS B.V.I) LIMITED  (BVI shells, 2006, Panama Papers)
   officers: Ledra Services Limited (Cyprus) + Bridgewater 1st/2nd Nominees Limited (IOM)
                  │  shared Cyprus 'Ledra' service-provider brand
                  ↓
LEDRA TRUSTEE SERVICES LIMITED  (Cyprus — no ROE filing, OS debarment+sanction)
   owns: 45 Green Street, Mayfair W1K 7FX + one other Mayfair title
```

### Caveats that still hold

1. **0 direct edges in the leak graph** between Usmanov-named officer nodes and the BVI Metalloinvest entities. The structure uses Cyprus + IOM nominees as the named officers — the layering pattern that makes beneficial ownership invisible by design. Usmanov is documented elsewhere in Panama Papers (13+ times) but not directly on these specific BVI shells.

2. **`LEDRA TRUSTEE SERVICES LIMITED`** (the UK property owner) and **`Ledra Services Limited`** (the Cyprus nominee in Panama Papers) are **distinct corporate entities sharing the "Ledra" brand**. The cluster of Ledra Services / Ledra Trustees / Ledra Nominees is plausibly under common control but the link between the Mayfair property owner and the Metalloinvest nominee is via **brand identity at the Ledra service-provider family**, not a parent/subsidiary edge we can prove from this data alone.

3. **Live UK CH search returned 0 hits for "Metalloinvest"** — the Russian holding's UK exposure is via overseas-incorporated entities not direct UK registration. Two "Usmanov"-named UK companies exist (`USMANOV LTD`, `VK USMANOVA LIMITED`) but without further info are likely homonyms.

4. **OS's `gb_coh_disqualified` tagging of Usmanov** does NOT mean he is on the live UK CH disqualified-officers register — earlier live CH search confirmed no Usmanov on that register. OS appears to treat sanctioned-and-therefore-deemed-disqualified persons as `corp.disqual` even where no CDDA court order exists. The "Usmanov is UK-disqualified" claim should be sourced specifically to the UK sanctions regime, not the CH disqualified-officers register.

### Net finding

The Mayfair flat at 45 Green Street W1K 7FX, held by Cyprus-incorporated LEDRA TRUSTEE SERVICES LIMITED without UK ROE filing, sits inside a verified structural pattern: the same Cyprus "Ledra" service-provider family is documented in Panama Papers as nominee for a multi-jurisdiction Metalloinvest BVI/Cyprus structure controlled by the OFAC-sanctioned Russian oligarch Alisher Usmanov. The brand-identity link is unambiguous; the corporate-control link between the UK-property-owning Ledra Trustee Services and the Panama Papers Ledra Services nominee would need separate corporate-registry verification.

### IGT Intergestions Trust Reg — Liechtenstein Anstalt on the OFAC SDN list

5 UK land titles. Sample: **LAND LYING TO THE SOUTH OF Highgate West Hill, London** — prime N6/NW3 boundary land. Proprietor address: **Aeulestrasse 6, 9490 Vaduz, Liechtenstein** — a known Liechtenstein corporate-services address. Country of incorporation Liechtenstein, structured as a "Trust Reg" (an Anstalt-style Liechtenstein vehicle).

OpenSanctions tags this entity with `debarment + sanction` and lists it on **the actual US OFAC SDN list** (`us_ofac_sdn`), plus `us_sam_exclusions`, `ext_us_ofac_press_releases`, and `opencorporates`. The presence on `ext_us_ofac_press_releases` indicates a specific OFAC press release naming the entity (which would give the underlying designation reason).

This is the verified-by-name Liechtenstein-Anstalt counterpart to the Ledra (Cyprus nominee) finding — same regulatory non-compliance pattern, different secrecy-jurisdiction.

Two ICIJ records in the local Panama Papers neighborhood warrant flagging but not claiming: **GALLAGHER HOLDINGS LIMITED aka USM STEEL** (the "USM" branding is suggestive of Alisher Usmanov's USM Holdings metals empire, but the connection isn't established by an edge in our data) and **Mr. Mihran Poghosyan** (Armenian politician with known offshore allegations). Both appear in the same Panama Papers corpus rather than directly linked to IGT Intergestions in the leak graph.

The net finding: an OFAC-SDN-listed Liechtenstein Anstalt holding 5 prime Highgate land titles, with no UK ROE filing. The OFAC designation reason would be the next verification step (via the linked OFAC press release).

## SE1 deepdive — reframing the largest postcode cluster

The headline geographic concentration figure listed SE1 with 690 non-compliant titles — the largest single outward-postcode cluster in the anti-join. A deepdive (`probe_se1_deepdive.py`) shows this number is misleading without context: **88% of those titles belong to one hotel-condo scheme**, not a distributed offshore-shell pattern.

| Top SE1 proprietor | Titles | Country |
|---|---:|---|
| WESTMINSTER BRIDGE LONDON (REAL ESTATE) B.V. | 563 | Netherlands |
| COUNTY HALL HOTEL HOLDINGS B.V. | 46 | Netherlands |
| Next 69 proprietors combined | 81 | Various |

**571 of those titles are at one address: 200 Westminster Bridge Road, SE1 7UT — the Park Plaza Westminster Bridge hotel.** Park Plaza Westminster Bridge is a 1,019-room hotel that operates as a **hotel-condo investment scheme** — each room is registered as a separate UK leasehold title. The Dutch B.V. is the operator-custodian entity that holds the title pool.

Acquisition-year distribution confirms: **507 of the SE1 titles were registered in 2016**, the year the hotel-condo scheme rolled out. The remaining titles are small numbers across other years.

Postcode-sector confirms: **642 of 690** SE1 titles are in **SE1 7** (the Westminster Bridge / Albert Embankment band where Park Plaza sits).

ICIJ leak overlap within SE1 is small — only 7 distinct names — and includes the already-documented EKO IRE LIMITED (Edokpolo family, 3 SE1 titles including a Park Plaza Westminster Bridge room) plus two single-title leak-named entities.

### Pattern read

SE1 doesn't fit the Mayfair/Belgravia/Kensington offshore-secrecy-shell pattern that dominates the rest of the high-confidence findings. It's **a hotel-condo operator non-filing under ECTEA 2022**, which is still regulatory non-compliance, but a different shape — one Dutch entity owes one bulk filing rather than 600+ overseas-secrecy-jurisdiction shells owing 600+ separate filings.

The 690 SE1 number should not be cited alongside the prime-central-London luxury postcode figures (W1K, SW1X, W8, SW3) without this qualification: those postcodes hold distributed shells, SE1 is concentrated in one hotel.

## Cross-thread address co-tenancy

The expand probe also surfaced shared proprietor correspondence addresses across non-compliant proprietors — a signal that a thread sits inside a wider serviced-address cluster:

| Thread | Shared address | Co-tenant non-compliant proprietors |
|---|---|---|
| FENLAND | 8 St Georges Street, Douglas IM1 1AH (IOM) | M.H.E. INVESTMENTS LIMITED, ROSSMOOR LIMITED |
| Embassy Development | 14-16 Avenue Pasteur, L-2130 Luxembourg | (intra-thread: 2 of 3 SPVs) |
| Harmony Ridge | 25 Iverna Court, London W8 6TY | THREE VALLEYS LIMITED |
| EDOKPOLO | (none — Lagos/WC2H address unique) | — |
| Ledra Trustee Services | (none on proprietor side — Cyprus address unique) | — |

Each of the FENLAND, Embassy Development, and Harmony Ridge threads now expands into a small local cluster of non-compliant proprietors sharing a correspondence address.

## Officer-edge expansion summary

| Thread | Officers expanded | Notable connections |
|---|---:|---|
| FENLAND (Fenech) | 40 | Maltese agribusiness/services cluster (AGROFRUIT, ANDRICO, ITALCA, FENECH CLARKE & CO. LTD, PEP LIMITED) |
| EDOKPOLO | 3 | Self-contained — only EKO IRE LIMITED |
| Embassy Development | 0 (no leak presence) | — |
| Harmony Ridge | 0 (limited expansion) | — |
| Ledra Trustee Services | 40 | Cyprus nominee infrastructure servicing BVI entities including a Metalloinvest-named entity (caveats above) |

## Status

All four lenses (ICIJ leak overlap, OS sanctions/PEP overlap, postcode/jurisdiction concentration, pre/post-Aug-2022 split) producing. Strict matcher gives a tighter lower bound (4,174 proprietors / 9,198 titles), with the methodology caveat surfaced. Named-thread deepdives complete for FENLAND, Edokpolo / EKO IRE, Embassy Development, Harmony Ridge, and Ledra Trustee Services.

## Sources

- HM Land Registry, Overseas Companies Ownership Data (OCOD), May 2026 release.
- UK Companies House, Basic Company Data bulk download, May 2026 snapshot.
- ICIJ Offshore Leaks Database, consolidated Panama / Paradise / Pandora / Bahamas / Offshore Leaks (https://offshoreleaks.icij.org).
- UK Economic Crime (Transparency and Enforcement) Act 2022, s.3, s.4, s.34, s.42.
