# Cluster 47 — Same-person verification for "Peter Kevin Perry"

**Generated 2026-05-20. Cross-references four public records via Tavily
extract. Not a finding of wrongdoing; a verification that the records
GoldenMatch surfaced under the name "Peter Kevin Perry" plausibly refer
to the same individual.**

The first-stage validation pack flagged two ICIJ Offshore Leaks uids
(`icij:56056705`, `icij:56056803`) under the same normalized name and
left the final verdict as `Human review required`. The corroboration
pass then surfaced two additional public-web records under the same
name (Companies House officer record, Bloomberg profile). This
document is that human-review pass.

## Records reviewed

| # | Source | URL |
| --- | --- | --- |
| A | ICIJ Offshore Leaks Database (Paradise Papers) | <https://offshoreleaks.icij.org/nodes/56056705> |
| B | ICIJ Offshore Leaks Database (Paradise Papers) | <https://offshoreleaks.icij.org/nodes/56056803> |
| C | UK Companies House — officer appointments | <https://find-and-update.company-information.service.gov.uk/officers/HgeHCR6Q4eZTWFZbXw6EqaRPPvs/appointments> |
| D | Bloomberg profile (paywalled body) | <https://www.bloomberg.com/profile/person/5130594> |

## Side-by-side

| Attribute | A (ICIJ 56056705) | B (ICIJ 56056803) | C (Companies House) | D (Bloomberg) |
| --- | --- | --- | --- | --- |
| Surface name | PETER KEVIN PERRY | PETER KEVIN PERRY | Peter Kevin PERRY | Peter Kevin Perry |
| Listed address | **52 BARRULE PARK, RAMSEY IM8 2BP** | **52 BARRULE PARK, RAMSEY IM8 2BP** | **52 Barrule Park, Ramsey, Isle Of Man, IM8 2BP** | (not exposed in extract) |
| DOB | — | — | April 1963 | — |
| Nationality | — | — | British | — |
| Country of residence | — | — | Isle Of Man | — |
| Earliest role visible | 22 Sep 2010 | 16 Dec 2011 | 12 Nov 2019 | "Former Board Member" |
| Sample roles | Legal/Judicial rep + Director of INTEGRATED-CAPABILITIES LTD (Malta) | Secretary of 30+ Malta companies (LARSTON, INSTAPARK, SIDECAR, JOBIZ, PAKINYA, …) | Active Director of FORWARD TRADERS LIMITED (09088104) | Corvus Capital LLC |

## A = B = C: high-confidence same individual

The Isle of Man postal code `IM8 2BP` is for a single street in Ramsey;
combined with the matching house number (52) and street name (Barrule
Park), this is a **single physical address**. Three independent records
list the same name + the same address:

- ICIJ `56056705` (Paradise Papers) → 52 Barrule Park, Ramsey IM8 2BP
- ICIJ `56056803` (Paradise Papers) → 52 Barrule Park, Ramsey IM8 2BP
- Companies House `HgeHCR6Q4eZTWFZbXw6EqaRPPvs` → 52 Barrule Park, Ramsey, Isle Of Man, IM8 2BP

Name match alone is weak (homonyms are common). Name + identical
physical address across three records, two of them primary regulatory
sources (Companies House) or primary leak sources (ICIJ Offshore
Leaks), is **high-confidence**. The Companies House DOB (April 1963) +
nationality (British) + country of residence (Isle of Man) are
consistent with the offshore-director archetype the ICIJ records
describe.

**Verdict for A = B = C: same individual.**

The two ICIJ uids are best explained as the ICIJ pipeline creating
distinct node IDs for two roles he held in the leaked documents (one
for the earliest INTEGRATED-CAPABILITIES appointment in 2010, one for
the later Malta-secretary appointments from 2011-2016). The Companies
House record covers his post-2019 UK directorships.

## A = B = C → D: not verified via UK Companies House

The Companies House search for "Corvus Capital" returns no UK entity
that matches the Bloomberg profile cleanly. The closest UK record is
**CORVUS CAPITAL L.P.** (`SL013246`, a Scottish Limited Partnership
registered 4 June 2013, address 69 Brunswick Street, Edinburgh). Two
other Corvus Capital entities (`CORVUS CAPITAL GROUP LTD`,
`CORVUS CAPITAL MANAGEMENT LIMITED`) were registered in Nov 2025 and
Jan 2026 respectively — almost certainly unrelated to a "Former
Board Member" Bloomberg profile that predates them.

More decisively, **the same Perry's master Companies House officer
record (`HF0jiKwO9x2R3Ypa0xss6sFPIuU`, 19 historical appointments)
contains no Corvus Capital affiliation at all.** That record includes
every past UK directorship and secretaryship recorded under his name
+ DOB + IoM address — and Corvus is not on it.

This means one of:

1. The Bloomberg "Peter Kevin Perry, Corvus Capital LLC" is a
   **different individual** with the same name.
2. The Bloomberg "Corvus Capital LLC" is a **US entity** (the "LLC"
   suffix is American) whose board appointments don't surface in UK
   Companies House at all. Verification would require US
   incorporation records (Delaware, BVI, or another offshore
   registry).
3. The Bloomberg profile predates the Companies House appointment
   history that's been digitised — Companies House only carries
   officer history back so far.

**Verdict for D: not verifiable from UK public sources.** Do not lift
"Corvus Capital LLC director" into any narrative without a separate US
registry confirmation. The plausibility argument falls below the bar
once the UK record doesn't carry the link.

## What the UK record *does* show — and why it strengthens A = B = C

Walking the 19-appointment Companies House officer record produced
two cross-jurisdictional corroborations that strengthen the
"ICIJ Perry = Companies House Perry" identification independently of
the address match:

### PROBUTEC lineage

| Jurisdiction | Entity | Status | Record |
| --- | --- | --- | --- |
| UK | **PROBUTEC LTD** (04102334) | Dissolved | Companies House — Peter Kevin Perry, Director, appointed 6 Nov 2000 |
| Malta | **PROBUTEC (MALTA) LTD** | (in cluster 47) | ICIJ Paradise Papers — Peter Kevin Perry, officer |

Same root name across two jurisdictions, same Perry, ~2000-era UK
incorporation followed by a Malta parallel. This is a corporate
lineage signal, not a coincidence.

### I-CAP / INTEGRATED-CAPABILITIES lineage

| Jurisdiction | Entity | Status | Record |
| --- | --- | --- | --- |
| UK | **I-CAP MARINE SERVICES LIMITED** (06494852) | Active | Companies House — Peter Kevin Perry, Director, appointed 6 Feb 2008 |
| Malta | **INTEGRATED-CAPABILITIES (MALTA) LTD** | (in cluster 47) | ICIJ — Peter Kevin Perry, Legal/Judicial rep + Director, appointed 22 Sep 2010 |
| Malta | **INTEGRATED-CAPABILITIES LTD** | (in cluster 47) | ICIJ — Peter Kevin Perry, same roles |

I-CAP is the obvious abbreviation of Integrated CAPabilities. The
2008 UK incorporation precedes the 2010 Malta incorporation by two
years — same person, same naming convention, parallel structures
spanning the IoM → UK → Malta corridor.

### Updated verdict for A = B = C

**Confirmed.** Three records share name + address; two records share
underlying business naming convention across jurisdictions; one record
(Companies House) supplies DOB and nationality. The same-person
identification is now publication-grade — well beyond
"same name + same postal code".

## What this means for any published narrative

A defensible sentence the verification now supports:

> "UK Companies House lists Peter Kevin Perry (born April 1963,
> British, resident in the Isle of Man) at 52 Barrule Park, Ramsey,
> with 19 past and present directorships. Two of those companies —
> PROBUTEC LTD (UK, 2000) and I-CAP MARINE SERVICES LIMITED (UK, 2008)
> — share root names with companies in the Malta-incorporated cluster
> the ICIJ Paradise Papers leak documents him as an officer of
> (PROBUTEC (MALTA) LTD and INTEGRATED-CAPABILITIES (MALTA) LTD).
> The Malta companies share registered office at 45/13 Strait Street,
> Valletta."

A sentence the verification does **not** support and should be left
out of any narrative:

> "Peter Kevin Perry of Corvus Capital LLC was the director of a
> 67-company Malta network."

The Bloomberg profile remains a same-name hit. The UK Companies
House record affirmatively does not list Corvus Capital among his
appointments.

## Addendum: US-registry follow-up on the Bloomberg "Corvus Capital LLC" claim

PR #62 closed the question via UK Companies House; this addendum
walks the US side to confirm that the Bloomberg attribution is dead
across every reachable primary source.

### SEC EDGAR full-text search

Query: `"Corvus Capital LLC"` (free-text, all filings)
→ **7 filings**, all from **2001-2003**, all for:

- BOSTON CELTICS LIMITED PARTNERSHIP /DE/ (CIK 0001059969)
- BOSTON CELTICS LIMITED PARTNERSHIP II /DE/ (CIK 0000805009)
- HENLEY LIMITED PARTNERSHIP (CIK 0001059969)

The most informative is **`SC 13E3`** (Henley LP, filed
2003-02-14, accession `0000910647-03-000068`). The director
biography section reads:

> "From 1998 to 2002, **Mr. Marsh** was the managing partner of
> Corvus Capital, LLC. From 1995 to 1998, he was Director of
> Trading and Sales with ABSA Securities, Inc., an investment
> banking firm. ..."

Combined queries:

| Query | Filings |
| --- | ---: |
| `"Corvus Capital LLC" "Peter Kevin Perry"` | **0** |
| `"Corvus Capital LLC" "Peter Perry"` | **0** |
| `"Corvus Capital" "Peter Kevin Perry"` | **0** |
| `"Corvus Capital" "Peter Perry"` | **0** |

**No SEC filing under any name variant ties any Peter Perry to any
Corvus Capital entity.**

Screenshots:
- `docs/validation/screenshots/sec_edgar_corvus_company_search.png`
- `docs/validation/screenshots/sec_edgar_henley_lp_filings.png`

### Delaware Division of Corporations

Free entity search at `icis.corp.delaware.gov` returns five
Corvus-Capital entities:

| File # | Entity name | Formation date | Notes |
| ---: | --- | --- | --- |
| 2942086 | CORVUS CAPITAL LLC | **1998-09-10** | Matches the SEC-filed (Marsh-managed) entity; registered agent: Corporation Service Company (CSC) |
| 4741239 | CORVUS CAPITAL LLC | **2009-10-13** | Newer LLC under the same name; no SEC filings under this entity; registered agent: Registered Agent Solutions, Inc. (Dover, DE) — generic shelf agent |
| 4979247 | CORVUS CAPITAL MANAGEMENT GP, LLC | — | Manager vehicle |
| 5087639 | CORVUS CAPITAL MANAGEMENT, LP | — | LP, presumably the fund vehicle |
| 5418707 | CORVUS CAPITAL ONSHORE FUND, LP | — | Onshore fund |

Delaware's free tier returns entity-level metadata only — no
officer / member / manager names without a paid certified copy
($20+). **The 1998 entity (file 2942086) is the one named in the
SEC filings as Marsh-managed.** The 2009 entity (file 4741239) is
a distinct entity formed seven years after Marsh's 1998-2002
tenure ended; it has no SEC filings under its own name and the
registered agent is a generic shelf provider used by thousands of
unrelated LLCs.

Either Delaware entity could in principle have been Bloomberg's
profile target, but neither can be tied to Perry without paying
Delaware's per-entity fee for filing history. Given (a) zero SEC
hits for Perry + Corvus, (b) zero appointments under Corvus in
Perry's UK Companies House master record, and (c) the 1998 entity
already accounted for by Marsh, the case for paying to dig
further is weak.

Screenshots:
- `docs/validation/screenshots/delaware_corvus_capital_results.png`
- `docs/validation/screenshots/delaware_corvus_2942086_detail.png`
- `docs/validation/screenshots/delaware_corvus_4741239_detail.png`

### Nevada and OpenCorporates

- **Nevada SOS** (`esos.nv.gov`) returned an **Incapsula access-denied**
  page to the automated session. Could not retrieve any Nevada
  records via this channel.
  Screenshot: `docs/validation/screenshots/nevada_search_blocked.png`
- **OpenCorporates** (`opencorporates.com`) presented an **HAProxy
  bot challenge** on the search results page. Could not retrieve.
  Screenshot: `docs/validation/screenshots/opencorporates_corvus_capital_us.png`

Both blocks are anti-automation defenses, not evidence one way or the
other about Perry / Corvus. A reviewer with a real browser session and
either site's standard search UI could reach them; this document
records that the automated half of the verification stopped there.

### Final verdict on Bloomberg "Corvus Capital LLC"

**The Bloomberg attribution is unsupported across every primary
source reachable from automated public-registry walks.**

- UK Companies House master officer record (19 appointments): no
  Corvus appointment.
- SEC EDGAR (full corpus): no filing ties any Perry to any Corvus
  Capital entity.
- Delaware (free metadata): two LLCs under the name exist, one
  Marsh-managed per SEC, one a 2009 entity with no SEC trail.
  Neither shows a Perry link in the free tier.
- Nevada / OpenCorporates: blocked.

The most parsimonious explanation is that the Bloomberg profile
under the name "Peter Kevin Perry, Former Board Member, Corvus
Capital LLC" refers to **a different individual sharing the name**,
not the Isle-of-Man Peter Kevin Perry of cluster 47. The Bloomberg
profile body is paywalled and not reachable from this verification.

**Hard recommendation for any published narrative: do not lift the
Corvus claim under any framing.** The structural Malta-cluster
story stands on its own without it.

## Addendum: identifying the SEC "Mr. Marsh"

The Henley LP 13E3 director-biography section names the Corvus
Capital LLC managing partner in full:

> "**John B. Marsh, III, Director.** Mr. Marsh is the managing
> partner of MHF Advisors, LLC, a strategic investment partnership
> where he is an investment banker. The address of MHF Advisors,
> LLC is 411 West Putnam Avenue, Suite 420, Greenwich, CT 06830.
> Mr. Marsh has been a director of Henley II, Inc. since September
> 1992. From April 2002 to August 2002, he was a senior portfolio
> manager at Rayner and Stonington... From 1998 to 2002, Mr. Marsh
> was the managing partner of Corvus Capital, LLC. From 1995 to
> 1998, he was Director of Trading and Sales with ABSA Securities,
> Inc... From 1991 to 1995, he was Chief Executive Officer and
> President of Saicor Ltd... From 1988 to 1991 he was a Vice
> President at Deutsche Bank Capital Corporation... From 1985 to
> 1988 Mr. Marsh was a Vice President in the international
> arbitrage department of Merrill Lynch Pierce Fenner and Smith."

### Cross-cluster check

Does John B. Marsh, III appear in any GoldenMatch cluster?

- **ICIJ officers parquet** (`data/interim/icij_officers.parquet`):
  zero exact matches for "John B Marsh", "John B Marsh III", or
  "John Marsh". Every "John + Marsh" substring hit resolves to
  "John Marshall" (different surname).
- **Cluster 47** (Perry / Strait Street): zero "marsh" mentions in
  officers, roles, FTM, or any artefact.
- **Cluster 38** (size 204): a **STUART MARSH** appears as auditor
  on 94 cluster companies. Different first name — different
  individual.
- **Cluster 40** (size 161): **MARSH DEVELOPMENT LIMITED** is a
  cluster *company* (a Malta company name, not a person).

### Where the DOB stops being reachable from public records

Followup searches:

| Source | Query | Result |
| --- | --- | --- |
| UK Companies House officer search | `John B Marsh` | No matches — US-based career, no UK appointments |
| FINRA BrokerCheck (individual API) | `John B Marsh` (21 results) | All resolve to "John Marshall" or unrelated; Marsh III is not FINRA-registered |
| FINRA BrokerCheck (firm) | `MHF Advisors` | 0 hits |
| FINRA BrokerCheck (firm) | `Corvus Capital` | 1 hit — `CORVUS CAPITAL MANAGEMENT LLC` (Nashville TN, principal: Stephen James Vogel) — a **different** entity from Marsh's |
| SEC IAPD (firm) | `MHF Advisors` | 0 hits |
| SEC IAPD (individual) | `John B Marsh` | Same 21 false positives as BrokerCheck |

That's consistent with the Henley LP filing's description — Marsh has
been a private-fund managing partner / investment-banking executive,
not a retail-facing broker. Private-fund managers can be exempt from
IA registration under SEC rules, so the absence from FINRA/IAPD is
expected for someone with this career shape, not evidence of obscurity.

### Implied DOB window

Career data points let us estimate (not pin) a DOB:

- 1985-1988: VP, Merrill Lynch international arbitrage desk
  → typical age for that role is mid-20s to early 30s
- September 1992: appointed Director of Henley II, Inc.
- Estimated DOB: **roughly 1950-1957**

That decade window is enough to definitively separate John B. Marsh,
III from any other "Marsh" in the cluster dataset:

| Person | DOB / decade | First name | Verdict |
| --- | --- | --- | --- |
| **John B. Marsh, III** (SEC Corvus, Greenwich CT) | ~1950-1957 | John | The SEC-Corvus subject |
| **Peter Kevin Perry** (cluster 47 anchor, Isle of Man) | April **1963** | — | Different decade, different surname, different country |
| **STUART MARSH** (cluster 38 auditor, Malta) | unknown | Stuart | Different first name |

### Final cross-cluster verdict

**There is no person-level bridge between the SEC's "Corvus Capital
LLC" story (John B. Marsh, III, Greenwich CT) and any GoldenMatch
Malta cluster.** The Bloomberg "Corvus Capital LLC" attribution that
the corroboration pass surfaced for the cluster 47 anchor is, with
all available evidence, a same-name coincidence.

The Malta cluster story stands entirely on its own structural and
cross-jurisdictional findings (PROBUTEC, I-CAP / INTEGRATED-
CAPABILITIES). Do not introduce Marsh or Corvus into the narrative.

## What this means for any published narrative

A defensible sentence the verification supports:

> "Two ICIJ Offshore Leaks records and one UK Companies House officer
> record under the name Peter Kevin Perry share the same registered
> address at 52 Barrule Park, Ramsey, Isle of Man. The Companies House
> record gives a date of birth of April 1963 and lists British
> nationality with Isle of Man residence. The ICIJ records show
> appointments across more than thirty Malta-incorporated companies in
> the 2010-2016 period."

A sentence the verification does **not** yet support:

> "Peter Kevin Perry of Corvus Capital LLC was the director of a
> 67-company Malta network."

That sentence requires the additional step of confirming the Bloomberg
Corvus Capital affiliation is for the same individual via a primary
source like Companies House for Corvus Capital LLC, not via the
Bloomberg profile alone.

## Methodology note

This document is the manual half of the workflow the corroboration
script (`scripts/corroborate_validation_pack.py`) was designed to set
up. The script surfaced the four URLs as high-quality external hits;
this document does the cross-reference a journalist would do before
publishing.

The hit-scorer fix shipped in the same session removed several
false-positive OFAC pages from the high-relevance bucket. The
surviving high-relevance hits all name the cluster entity in the page
body, which is why the address-match cross-reference was possible
above without false-positive noise.
