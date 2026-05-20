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
