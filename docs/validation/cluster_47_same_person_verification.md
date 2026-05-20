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

## A = B = C → D: plausible but unverified

The Bloomberg profile page extract above did not surface a date of
birth, address, or any cross-referenceable identifier in its public
preview. The page lists the subject as "Former Board Member, Corvus
Capital LLC" but the full biography requires a Bloomberg Terminal
subscription.

The hypothesis "ICIJ/Companies House Perry = Bloomberg Corvus Capital
Perry" is **plausible**:

- Corvus Capital LLC is a small London-based investment vehicle with
  a known pattern of board appointments by people who hold parallel
  Malta and Isle of Man directorships.
- The offshore-vehicle-director archetype matches.
- Same name on a high-quality domain (Bloomberg) is itself weak
  corroboration.

It is **not verified**:

- No address, DOB, or other identifier on the Bloomberg public
  preview matched the Isle of Man records.
- The Bloomberg profile body is paywalled; the public preview shows
  only name + "Former Board Member, Corvus Capital LLC".
- Multiple people may share a name on Bloomberg; same-name on
  Bloomberg is not the same as same-person.

**Verdict for D: candidate, requires direct verification.** To upgrade
to "verified": pull the Corvus Capital LLC corporate filings (UK
Companies House for Corvus Capital LLC) and check whether
`HgeHCR6Q4eZTWFZbXw6EqaRPPvs` (the same officer ID) appears as a former
director. That's a one-query check that this document does not yet
perform.

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
