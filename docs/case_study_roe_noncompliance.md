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
| Non-compliant proprietors also named in ICIJ Offshore Leaks | 622 |
| Named individuals surfaced via ICIJ officer enrichment | 447 |

Read with appropriate caution: the name-key anti-join carries false-positive risk where the OCOD record uses a different name form than the OE filing (e.g. "Ltd" vs "Limited"). Suffix-stripping reduces but does not eliminate this. The true non-compliance rate is likely lower than the raw 19% — but plausibly still in the **5–15%** range, i.e. several thousand UK property titles whose foreign owners have not complied with the statute.

## Geographic concentration

Non-compliant titles cluster in **prime central London** plus the SE1 regeneration belt:

| Outward postcode | Non-compliant titles | Area |
|---|---:|---|
| SE1 | 690 | South Bank / Bermondsey / Southwark |
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

## Open issues

- OS sanctions/PEP/crime overlap (`probe_roe_noncompliance_personalize.py`) returned 0 hits on first run. Topic-encoding mismatch — fix in progress.
- Date-aware split (pre/post Aug 2022) returned 0/0 — date parsing issue, fix in progress.
- FENLAND LIMITED full deepdive — separate probe (`probe_fenland_deepdive.py`) walks all 313 titles + Fenech family ICIJ records.

## Sources

- HM Land Registry, Overseas Companies Ownership Data (OCOD), May 2026 release.
- UK Companies House, Basic Company Data bulk download, May 2026 snapshot.
- ICIJ Offshore Leaks Database, consolidated Panama / Paradise / Pandora / Bahamas / Offshore Leaks (https://offshoreleaks.icij.org).
- UK Economic Crime (Transparency and Enforcement) Act 2022, s.3, s.4, s.34, s.42.
