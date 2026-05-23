# IGT Intergestions Trust Reg — Current-ownership question

> **The single remaining load-bearing gap.** *Does IGT still currently own the five Highgate titles, or did OCOD reflect an older ownership state?*

This document works through every accessible path to closing that gap and concludes with a defensible interim answer plus the one paid step that closes it definitively.

---

## What "current ownership" means

The 5 titles in question, all registered to `IGT INTERGESTIONS TRUST REG.` per OCOD `date_proprietor_added` of **29 April 2013**:

- `NGL780113` — LAND LYING TO THE SOUTH OF Highgate West Hill, London
- `NGL809817` — LAND ON THE SOUTH EAST SIDE OF Highgate West Hill, London
- `LN44427` — Bromwich House, 1 Witanhurst Lane, London N6 6LT
- `NGL723612` — LAND LYING TO THE SOUTH EAST OF Highgate West Hill, London
- `NGL753781` — 79 Highgate West Hill, London N6 6LU (price-paid £450,000)

"Current ownership" = the proprietor recorded against each of these title numbers in HM Land Registry's live title register today.

---

## What our data already shows

| Source | Snapshot date | Proprietor recorded |
|---|---|---|
| OCOD May 2026 release | early May 2026 | `IGT INTERGESTIONS TRUST REG.` for all 5 titles |
| OCOD `date_proprietor_added` | 29 April 2013 | (initial registration — same as current per snapshot) |

OCOD is HMLR's monthly Overseas Companies Ownership Data publication. The May 2026 release is the latest available; the June 2026 release will not appear until on or about 1 June 2026.

So at the snapshot date — early May 2026 — IGT is the proprietor. The unresolved question is whether the title changed hands between the OCOD snapshot date and **today**.

---

## What live HMLR services do we have access to?

### Path A — HMLR e-services Quick Enquiry (free, no account)

`eservices.landregistry.gov.uk/eservices/FindAProperty/view/QuickEnquiryInit.do` returned `Service Unavailable` on both 22 May 2026 attempts (late evening UK time). Screenshot: `docs/reports/screenshots/10_hmlr_eservices_unavailable.png`.

When operational, this page lets a non-authenticated user enter a title number and retrieve a property summary. Per HMLR's own statement (screenshot 15), the **free property summary does not include the owner's name** — owner is now in the paid title register only.

So even with the service back online, the free Quick Enquiry alone does not answer the current-ownership question.

### Path B — Search for Land and Property Information (GOV.UK)

`gov.uk/search-property-information-land-registry`. Open page captured at screenshot 15. Confirmed pricing as of May 2026:

| Document | Cost | Reveals owner? |
|---|---|---|
| Property summary | **FREE** | ❌ No |
| Title register | **£7 online** (£11 official by post) | ✅ Yes |
| Title plan | £7 online (£11 official by post) | — |

Requires sign-in and a debit/credit card. The **£7 × 5 = £35** title-register purchase is the gold-standard verification, but is unavoidable.

Newer pricing than what this repo's earlier documentation cited (£3 per title). Updated in the publication-readiness check.

### Path C — Bulk OCOD CSV download

`use-land-property-data.service.gov.uk/datasets/ocod` returned `Service Unavailable` at attempt. When operational, this service offers free monthly OCOD downloads to registered users. The latest release we have is May 2026; no later release exists yet (June 2026 ~ 1 June 2026).

### Path D — Cloudflare-blocked / GUI-only routes

`search-property-information.service.gov.uk` was blocked by a Cloudflare anti-bot check at attempt. Manual browser access required.

---

## The legal-structural argument that constrains plausible movement

This argument doesn't replace a live title check but **substantially narrows the space of plausible movements** between the May 2026 OCOD snapshot and today:

ECTEA 2022 Schedule 3 paragraph 6 required HMLR's Chief Land Registrar to enter a restriction under Sch 4A para 3 LRA 2002 against every overseas-entity-held title before the end of the transitional period (31 January 2023). That restriction is on the title from 31 January 2023 onwards.

The restriction (Sch 4A LRA 2002 para 3(2)) **prohibits the registration of most dispositions** unless:

- (a) the entity is a registered overseas entity at the time of the disposition (IGT is not — anti-join + live CH search confirmed),
- (b) the disposition is in pursuance of a statutory obligation, court order, or operation of law (rare; would be publicly visible),
- (c) the disposition is in pursuance of a contract made before the restriction was entered (i.e. pre-31-Jan-2023 — getting harder to plausibly invoke 3+ years later),
- (d) the disposition is by a registered chargee or receiver,
- (e) the Secretary of State has given consent under Sch 4A para 5 (each case publicly recorded),
- (f) the disposition is by a specified insolvency practitioner.

A registrable disposition outside these exceptions cannot lawfully be registered, and making one is **a separate offence under Sch 4A para 6 with imprisonment up to 5 years on indictment**.

The effect: for IGT to have lawfully transferred ownership since 31 January 2023, one of the (a)-(f) carve-outs must apply. None of them is consistent with a normal arms-length sale to a UK-incorporated purchaser without the buyer running into the restriction.

There is also a structural OCOD constraint: OCOD only includes titles whose registered proprietor is an **overseas-incorporated entity**. If IGT had sold to any UK-incorporated buyer, the title would have **dropped out of OCOD** — it would not appear in May 2026 OCOD as IGT-owned.

So the May 2026 OCOD entry actively confirms two things: (i) IGT was the proprietor on the snapshot date, AND (ii) any sale (if one occurred earlier) must have been to *another* overseas-incorporated entity, which is itself unusual and would create a new OCOD record under that entity's name.

We can scan the May 2026 OCOD for any title number `NGL780113`, `NGL809817`, `LN44427`, `NGL723612`, `NGL753781` attributed to a proprietor OTHER than IGT — if such an entry existed, it would represent a transfer to another overseas entity. Let me check.

---

## Cross-check inside our own May 2026 OCOD snapshot

The `aar_igt_verify.json` artefact already contains the 5 title-number-level records for IGT. None of the 5 title numbers appears in OCOD attributed to any other proprietor (each title number is unique in OCOD by construction). All 5 are still attributed to IGT in the May 2026 snapshot.

In other words: **as of the most recent monthly publication of HMLR's overseas-entity-ownership data**, IGT remains the recorded proprietor of all 5 titles.

---

## What the OFAC sanctions overlay adds

IGT INTERGESTIONS TRUST REG. and TRADE INITIATIVE ESTABLISHMENT are both on the US OFAC SDN list under RUSSIA-EO14024. The OFAC SDN listing creates secondary-sanctions risk for any non-US counterparty considering a transaction with these entities (see Section 11 of Executive Order 14024 noted on both OFAC detail pages).

While the UK has its own Sanctions and Anti-Money Laundering Act 2018 regime separately, the OFAC overlay makes a sale of these titles to most plausible international buyers further constrained — banks and conveyancers are exceptionally cautious about facilitating a registration where the seller is OFAC-listed under the Russia program.

---

## Net answer

**The most defensible answer the repo can support today**: As of the May 2026 OCOD release, all 5 titles remain attributed to IGT Intergestions Trust Reg., who became registered proprietor in April 2013. The Sch 4A LRA restriction in force since 31 January 2023 has prevented all but a narrow class of dispositions in the intervening 3+ years, none of which is currently visible in the public record for these titles. The OFAC RUSSIA-EO14024 designation overlays a further secondary-sanctions deterrent on any plausible buyer.

**The 22-day window between the OCOD snapshot (early May 2026) and today is the only remaining gap.** The single path to closing it is the **£7 title-register purchase for each title via `gov.uk/search-property-information-land-registry`** (signed-in account + card payment, total £35). Each title register lists the current registered proprietor and the current Sch 4A restriction status. That is the definitive current-day check.

Until that purchase is done, the safest framing is the one already in the slide-10 safe sentence: **"recorded since April 2013 as the proprietor"** rather than **"currently owns"** — verb tense that aligns with the OCOD record without overclaiming current state.

---

## Recommended path for the published claim

1. Buy the 5 title registers (£35 total).
2. Confirm the current proprietor is IGT INTERGESTIONS TRUST REG. on each (or, if changed, report whatever the new state is — and that becomes a separate finding about how the title moved while the restriction was in place).
3. Confirm the Sch 4A restriction is recorded against each (per Sch 3 para 6 ECTEA the Chief Land Registrar was obliged to enter it).
4. Switch the published verb tense from "recorded since April 2013 as the proprietor" to "is the current registered proprietor" only after step 2 has cleared.

Until step 2, the May-2026-OCOD-anchored framing remains correct, with the verb tense above carrying that uncertainty honestly.
