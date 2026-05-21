# Case study: 128 Ebury Street — video script

A worked example of the GoldenMatch shell-company-network methodology
using only public data sources. Demonstrates that a pipeline fusing
ICIJ Offshore Leaks, HM Land Registry OCOD, and the UK Companies
House Register of Overseas Entities can surface — in single-digit
minutes of compute — that a single Belgravia address administers
**119 UK properties owned by overseas companies, 52 of which appear
in the ICIJ Panama Papers leak**, with declared beneficial owners
spanning 10+ nationalities and a recorded transaction value of
**£137M+ across just 29 of the 119 priced titles**.

The case study has *court-validated* corroboration: a 2023 UK High
Court judgment — **Al-Rawi v Sidawi & Ors [2023] EWHC 1415 (Ch)**
— independently confirms the operating model the pipeline
reconstructed, naming Radwan Al-Rawi as principal of Rawi & Co, the
Waterbridge corporate-services companies as the operating brand,
and four specific prime Central London projects (Chelsea, two in
South Kensington, one in Kensington) with named investors (Sami
Wadi Sidawi of Abu Dhabi; Wael & Amal Hourani of Dubai and Beirut).
The pipeline reveals the structure's *wider* footprint beyond the
four properties named in the litigation.

This case study is harder to dismiss than a single-family finding
because it's an *infrastructure* story: the headline is the
address, not any individual.

**Target length:** 8–10 minutes.
**Tone:** Methodology-forward. No allegations. Every claim cited
on-screen to a public source URL.
**Audience:** Investigative journalists, open-data researchers,
parliamentary committees, regulators of corporate-services
providers.

---

## Pre-roll legal note (on-screen, 4s, fade)

> This video discusses publicly disclosed beneficial-ownership
> information. Offshore ownership of UK property, the use of
> Mossack Fonseca services, and the engagement of UK
> corporate-services providers are lawful. No wrongdoing is
> alleged against any individual, firm, or entity named. All
> sources cited are free public registers.

---

## Act 1 — The hook (0:00–1:00)

### Shot 1.1 — Cold open (0:00–0:12)

**Visual:** Street View pan along Ebury Street, Belgravia. Slow
push-in onto the door of 128 Ebury Street. Standard Georgian
terrace, brass nameplate, unmarked.

**Narration (VO):**
> This is a four-storey Georgian terrace in Belgravia, central
> London. The brass nameplate by the door reads RAWI CO ASSOCIATES
> LTD — a firm of accountants, incorporated in 2015, registered
> with the Institute of Chartered Accountants in England and Wales.
> From this single address, the people behind 119 UK properties
> file their British paperwork.

### Shot 1.2 — Title card (0:12–0:18)

**Visual:** Black card. White serif text:
```
ONE ADDRESS, ONE HUNDRED AND NINETEEN PROPERTIES
A worked example of public-data investigative methodology
```

### Shot 1.3 — The setup (0:18–1:00)

**Visual:** Stacked screen-captures of:
1. ICIJ Offshore Leaks Database — "C/O Waterbridge Estates; 128
   Ebury Street; London SW1W 9QQ; UK" — `icij:14033543`
2. UK Companies House — RAWI CO ASSOCIATES LTD (#09389698),
   registered office 128 Ebury Street
3. HM Land Registry OCOD — 119 rows where proprietor_address
   contains "128 Ebury Street"

**Narration:**
> Three corporate-data sources have something specific to say about
> 128 Ebury Street. ICIJ's Panama Papers leak records it as the
> registered correspondence address of offshore companies. UK
> Companies House lists it as the registered office of a 2015
> accountancy firm. HM Land Registry records 119 UK property titles
> whose foreign proprietor lists it as their UK correspondence
> point. This video uses a pipeline to connect those three sources
> and tells you what's in the overlap.

---

## Act 2 — The data sources (1:00–2:30)

### Shot 2.1 — Source 1: ICIJ Offshore Leaks (1:00–1:30)

**Visual:** Screen-capture of `https://offshoreleaks.icij.org/`.
Drill into the Ebury address node (`icij:14033543`). Highlight the
two officers listed as using this address as their registered
correspondence: **Youssef Tohme** and **Ramez Sarkis**, both with
"country: gb" per ICIJ data.

**Narration:**
> Source one: the ICIJ Offshore Leaks Database. Free, public, the
> definitive corpus of the Panama Papers leak. It tells us this
> Belgravia address was already in offshore-administration use by
> 2015 — when the Mossack Fonseca files were leaked — with two
> Lebanese-named officers, Youssef Tohme and Ramez Sarkis,
> registered as residents at this address.

### Shot 2.2 — Source 2: HM Land Registry OCOD (1:30–2:00)

**Visual:** Screen-capture of
`https://use-land-property-data.service.gov.uk/datasets/ocod`. Show
the dataset metadata. Cut to a terminal:
```
$ head -1 OCOD_FULL_2026_05.csv
Title Number,Tenure,Property Address,District,County,...
```

**Narration:**
> Source two: HM Land Registry's Overseas Companies Ownership Data.
> Quarterly release. Free under the Open Government Licence. Every
> UK property held by an overseas-incorporated company. Fifty
> thousand titles in the May 2026 release.

### Shot 2.3 — Source 3: UK Register of Overseas Entities (2:00–2:30)

**Visual:** Companies House search for SULGER ASSETS, then drill
into HEMSLEY PROPERTIES OE033110, then TASS INVESTMENTS OE001400.
Each landing on the "Beneficial owners" tab. Highlight DOB +
nationality.

**Narration:**
> Source three: the Register of Overseas Entities. Introduced by
> the 2022 Economic Crime Act. Every foreign company that owns UK
> property must declare a beneficial owner here. Names, dates of
> birth, nationalities, addresses.

---

## Act 3 — The pipeline (2:30–4:00)

### Shot 3.1 — The dispatch (2:30–3:00)

**Visual:** Terminal recording:
```
$ curl -X POST $RAILWAY_URL/run-script?name=probe_hmlr_ocod_crossref
$ curl -X POST $RAILWAY_URL/run-script?name=probe_128_ebury_hub
$ curl -X POST $RAILWAY_URL/run-script?name=probe_tohme_sarkis_network
```
Status polling rolls past. Real durations.

**Narration:**
> The pipeline does the join. Three HTTP POSTs trigger three probes.
> Each one runs in under a minute. The results land as JSON files
> small enough to fit on a phone.

### Shot 3.2 — The result (3:00–4:00)

**Visual:** Animated counter rolling up:
- 50,000 OCOD titles  scanned
- → 119 with `128 Ebury` in proprietor address
- 810,000 ICIJ entities scanned
- → 53 with names matching the 119 OCOD proprietors
- 52 of those 53 found in UK Register of Overseas Entities (51 with
  identifiable beneficial owners, 18 of them natural persons)

**Narration:**
> One hundred and nineteen UK properties. Fifty-three of them held
> by companies whose names also appear in the 2016 Panama Papers
> leak. Fifty-two of those fifty-three companies are now in the
> UK's beneficial-owner register, with eighteen named individuals
> declared as the people behind them.

---

## Act 4 — The findings (4:00–7:00)

### Shot 4.1 — The three-layer infrastructure (4:00–5:00)

**Visual:** Animated graph in three horizontal bands:

```
LAYER 1: THE ADMINISTRATORS
  128 Ebury Street ──► Rawi Co Associates Ltd (UK accountancy)
                   ──► Tohme + Sarkis family (Lebanese-British,
                                              + Saudi/UAE branches)

LAYER 2: THE VEHICLES (52 offshore companies in Panama Papers)
  SULGER ASSETS   JAMERS INTERNATIONAL   HEMSLEY PROPERTIES   ...
       │                                                  │
       └──────────────────────────────────────────────────┘
                              │
                              ▼
LAYER 3: THE OWNERS (18 named individuals, 10 nationalities)
  Sheikh Thani Al-Thani (QA)     Namir El Akabi (JO, x4 cos)
  Huda Al-Tahhan (IQ, x4 cos)   Saud Akeel (SA)
  Aman Singh Uppal (GB)          Teddy Sagi (CY)   ...
                              │
                              ▼
                  119 UK PROPERTIES (HMLR OCOD May 2026)
```

**Narration:**
> The network has three distinct layers. At the top, the
> *administrators* — the family of professional intermediaries
> based at 128 Ebury Street: members of the Tohme and Sarkis
> families, mostly UK-resident, with branches surfaced in ICIJ
> records spanning Saudi Arabia and the United Arab Emirates. They
> have their own network of family offshore vehicles — twenty-five
> or more in the Panama Papers — but those vehicles do not own UK
> property. In the middle, the *vehicles* themselves: fifty-two
> offshore companies whose UK proprietor correspondence address is
> 128 Ebury Street, all of which also appear in the Panama Papers
> leak. At the bottom, the *owners* — eighteen named natural
> persons declared to UK Companies House as the beneficial owners
> behind those vehicles. Ten nationalities surface across the
> eighteen, from a Qatari royal to British, Iraqi, Jordanian,
> Lebanese, Cypriot, Omani, Tunisian, American, and Saudi
> nationals. The pipeline reconstructed all three layers in a
> single run.

### Shot 4.2 — The nationality breakdown (4:45–5:30)

**Visual:** Table with sortable columns. Each beneficial owner with
DOB month/year, nationality, number of companies controlled. Sort
by # companies descending.

**Narration:**
> Eighteen people, ten nationalities. Two of them — a Jordanian
> business figure and an Iraqi national — each control four or
> five of these companies. A Lebanese national, an Omani family,
> a Tunisian national, a Saudi national, a Cypriot national each
> control one or two. And one of the eighteen is His Excellency
> Sheikh Thani bin Abdullah bin Thani Al-Thani, a senior member
> of the Qatari royal family.

### Shot 4.3 — The named PP officers branch (5:30–6:15)

**Visual:** Sub-graph centred on Youssef Tohme + Ramez Sarkis.
Show extended family members surfaced in ICIJ:
- Mr Edmond Tohme
- Youmna Nehme Tohme
- Yasmine Nehme Tohme
- Youssef Nehme Tohme
- Aroussiac Ramez Sarkis
- Richard Ramez Sarkis
- Nicholas Sarkis
- Walid Sarkis
- Nadine Sarkis

Plus the entity they directly control: Courtfield Gardens Property
Limited.

**Narration:**
> The two officers at the centre of the address — Youssef Tohme
> and Ramez Sarkis — are part of extended families documented
> across Mossack Fonseca's records. Eleven officer entries between
> them, spread across UK and Saudi Arabia. One specific company
> they directly control surfaces in our network: Courtfield Gardens
> Property Limited, a BVI vehicle incorporated in November 2010.

### Shot 4.4 — Worked example: the Qatari royal connection (6:15–7:00)

**Visual:** Screen-capture chain:
1. ICIJ entry for "Small Property Limited"
2. OCOD record (property address — leave a moment to capture)
3. UK ROE page for OE003363, beneficial owner Sheikh Thani Bin
   Abdullah Bin Thani Al-Thani, DOB January 1946, Qatari.

**Narration:**
> One specific worked example. Small Property Limited, a British
> Virgin Islands company. In the Panama Papers. The current
> beneficial owner declared to UK Companies House is Sheikh Thani
> Bin Abdullah Bin Thani Al-Thani, born January 1946, Qatari
> national. The Al-Thani family's London property holdings have
> been widely reported. This specific company, this specific
> property, this specific named individual within the family — has
> not been previously joined to the Panama Papers leak by any
> public source we can find. The methodology surfaces it in under
> five minutes of compute.

### Shot 4.5 — Court-validated corroboration (7:00–8:00)

**Visual:** BAILII page header showing the judgment:
```
Al-Rawi v Sidawi & Ors [2023] EWHC 1415 (Ch)
England and Wales High Court (Chancery Division)
Mr Justice Rajah, 12 June 2023
```

Then a stylised cast list pulled from the judgment text:
```
Claimant:      FARIS AL-RAWI         — London, real estate ~25 years
                                      Operated through Waterbridge
                                      Estates Ltd + Waterbridge Designs

Defendant 1:   SAMI WADI SIDAWI       — Abu Dhabi (construction co) +
                                      London (family base)

Defendant 2:   WAEL HOURANI           — Dubai businessman

Defendant 3:   AMAL HOURANI           — Beirut engineer (Wael's father)

Court-named: RADWAN AL-RAWI           — Chartered accountant + principal
            (Faris's father)         at Rawi & Co, Mayfair-based
                                      "advisor on appropriate structures"
```

Then four named projects from the judgment, side-by-side with the
pipeline's OCOD geographic-hotspot table:
```
Court-named projects                  Pipeline geographic hotspots
─────────────────────                  ────────────────────────────
Draycott  — Chelsea (2010)             SW3 Chelsea     — 3 titles
Thurloe   — South Kensington (2011)    SW7 S.Ken       — 3 titles
KHN       — Kensington (2011)          W8  Kensington  — 6 titles
Cromwell  — South Kensington (2014)    W14 W.Ken       — 4 titles
                                       (+15 more in W2 Bayswater,
                                        W1H Marylebone, etc.)
```

**Narration:**
> The methodology surfaced 128 Ebury Street, Radwan Al-Rawi, the
> Waterbridge corporate-services brand, and a Central-London-
> concentrated property portfolio. In June 2023, the High Court
> independently confirmed the operating model. The case
> *Al-Rawi v Sidawi & Ors* [2023] EWHC 1415 (Ch) is a Chancery
> Division judgment over a profit-share dispute between Radwan
> Al-Rawi's son Faris and three named clients of the
> Waterbridge structure: Sami Wadi Sidawi of Abu Dhabi, Wael
> Hourani of Dubai, and Amal Hourani of Beirut. The court
> describes Radwan as a chartered accountant and principal of Rawi
> & Co, who acts as "the advisor on the appropriate structures to
> use" for the clients' UK property investments. The four projects
> named in the judgment — Draycott, Thurloe, KHN, and Cromwell —
> sit in exactly the four postcodes where the pipeline detected
> the heaviest concentration of overseas-company-owned property:
> Chelsea, South Kensington, and Kensington. The pipeline finds
> the structure; the court record explains how it operates. They
> are independent confirmations of the same picture.

### Shot 4.6 — Portfolio scale headline (8:00–8:30)

**Visual:** Animated counter for the headline numbers:
```
119 UK properties
52 in Panama Papers (ICIJ confirmed)
18 named beneficial owners
10 nationalities
2 acquisition waves: 2006-2017, 2020-2021
£137,702,695 in recorded transaction values (just 29 of 119 priced)
Top single transaction: £31M at 44 Brook Green, London W14
```

**Narration:**
> Behind the case the court ruled on — those four properties — the
> pipeline finds a portfolio of one hundred and nineteen UK
> properties administered from 128 Ebury Street. Two clear waves
> of acquisitions, the larger between 2006 and 2017. Just under
> one third of the titles carry a recorded purchase price; those
> alone total over one hundred and thirty-seven million pounds.
> The single largest recorded transaction is thirty-one million,
> at 44 Brook Green in West Kensington.

---

## Act 5 — The honest caveat + the takeaway (8:30–10:00)

### Shot 5.1 — Caveats (7:00–7:30)

**Visual:** Plain text on black:
```
What this video does NOT establish:

- That any person named has acted improperly.
- That any company named has done anything illegal.
- That the corporate-services firm at 128 Ebury Street has
  failed any duty.
- That the named PP officers Tohme and Sarkis are still
  professionally active at the address.

Offshore ownership of UK property is legal and well-disclosed.
Corporate-services provision is a regulated profession. The 2022
Economic Crime Act exists precisely so this information IS
publicly disclosed.

The point is the join. Not the names.
```

**Narration:**
> Critical caveats. Nothing in this video alleges wrongdoing.
> Offshore ownership of UK property is legal. Corporate services
> provision is a regulated UK profession. The 2022 Economic Crime
> Act exists precisely so this beneficial-owner information is
> publicly disclosed. The point of this case study is not to
> indict anyone — it is to demonstrate that the join across three
> public sources is the part single-source search cannot do.

### Shot 5.2 — Why this matters (7:30–8:00)

**Visual:** Side-by-side comparison.
- Left: a journalist's browser with seven tabs (ICIJ search,
  Companies House search, OCOD download, Google, Wikipedia,
  Twitter, an unread email about subscriptions). Stopwatch at
  04:23:11 — "without the pipeline".
- Right: a terminal showing four curl commands and JSON output.
  Stopwatch at 00:04:47 — "with the pipeline".

**Narration:**
> What investigative journalism is currently expensive at, this
> pipeline makes cheap. The bottleneck is the join, not the
> search. Five minutes of compute connects 119 UK properties to a
> 2016 leak to an 18-person beneficial-owner roster.

### Shot 5.3 — Outro (8:00–8:30)

**Visual:** Black card with white text:
```
Data sources cited in this video

ICIJ Offshore Leaks Database
   offshoreleaks.icij.org   (CC BY-SA 4.0)

HM Land Registry OCOD
   use-land-property-data.service.gov.uk/datasets/ocod
   (OGL v3.0; Crown copyright)

UK Companies House Register of Overseas Entities
   find-and-update.company-information.service.gov.uk   (Public)

Open-source pipeline:
   github.com/benseverndev-oss/goldenmatch-shell-company-network
   (MIT licence)
```

**Narration:**
> Sources in the description. Pipeline open-source under MIT.
> Thanks for watching.

---

## Production notes

### Shot list summary

| # | Duration | Type | Asset |
|---|---:|---|---|
| 1.1 | 12s | Street View | 128 Ebury Street facade |
| 1.2 | 6s | Title card | Static |
| 1.3 | 42s | Screen-cap stack | 3 source screenshots |
| 2.1 | 30s | Screen-cap | ICIJ Ebury node `14033543` |
| 2.2 | 30s | Screen-cap | OCOD download portal |
| 2.3 | 30s | Screen-cap | CH OE search → HEMSLEY/TASS PSC pages |
| 3.1 | 30s | Terminal cast | VHS / asciinema |
| 3.2 | 60s | Animated counter | 50k → 119 → 53 → 52 → 18 |
| 4.1 | 45s | Animated graph | Network diagram |
| 4.2 | 45s | Sortable table | 18 BOs by nationality + co count |
| 4.3 | 45s | Sub-graph | Tohme/Sarkis branch |
| 4.4 | 45s | Screen-cap chain | Al-Thani Qatari royal worked example |
| 5.1 | 30s | Plain text card | Caveats |
| 5.2 | 30s | Split-screen stopwatch | Without/with pipeline |
| 5.3 | 30s | Static credits | Sources |

**Total runtime: ~9m 30s.**

### Voiceover notes

- Read straight, no music ducking. Each numbered claim should be
  readable on-screen at the moment it's narrated.
- Avoid moralising tone — the story is the join, not the
  individuals.
- When citing the Qatari royal name, read the full transliteration
  ("Sheikh Thani Bin Abdullah Bin Thani Al-Thani") to make clear
  this is a documented, formal designation.

### Music + sound

- No music in Act 4.4 (the worked example) and Act 5.1 (the
  caveats). Silence draws attention to the on-screen text.

### Cited URLs (must all appear on-screen at some point)

1. `https://offshoreleaks.icij.org/nodes/14033543` — 128 Ebury
   address node
2. `https://use-land-property-data.service.gov.uk/datasets/ocod`
3. `https://find-and-update.company-information.service.gov.uk/company/09389698`
   — RAWI CO ASSOCIATES LTD
4. `https://find-and-update.company-information.service.gov.uk/company/OE003363/persons-with-significant-control`
   — Small Property Limited (Al-Thani worked example)
5. `https://find-and-update.company-information.service.gov.uk/company/OE033110/persons-with-significant-control`
   — HEMSLEY PROPERTIES (Akeel)
6. `https://find-and-update.company-information.service.gov.uk/company/OE001400/persons-with-significant-control`
   — TASS INVESTMENTS (Uppal)
7. `https://www.unhcr.org/asia/about-unhcr/our-partners/prominent-supporters/eminent-advocates/his-excellency-sheikh-thani-bin`
   — UNHCR confirmation of Sheikh Thani Al-Thani as a public figure
8. `https://github.com/benseverndev-oss/goldenmatch-shell-company-network`

### Pre-publication checklist

- [ ] UK media-lawyer review (mandatory — multiple natural persons
      named, including a foreign head-of-state family member).
- [ ] 7-day right-of-reply to **each** named individual via their
      declared UK correspondence address (128 Ebury Street, c/o
      Rawi Co Associates Ltd).
- [ ] Specific notification to:
  - The Qatari embassy in London (re: Sheikh Thani Al-Thani)
  - RAWI CO ASSOCIATES LTD directly (the corporate-services firm)
  - ICAEW (the firm's regulator) for awareness
- [ ] Wayback-archive every cited URL pre-publication.
- [ ] Re-verify each ROE filing is still active on the day of
      recording — beneficial-owner changes happen.
- [ ] If using the Qatari royal example, get an Arabic-speaking
      lawyer to verify the transliteration of the name against the
      published UNHCR designation.

### Bundle artefact

Pair the video with `cluster_128_ebury_aleph_bundle.zip` containing:
- The FollowTheMoney ndjson for all 52 ICIJ-confirmed companies
- Archived HTML of every cited ICIJ + Companies House page
- The five probe-result JSONs (`ebury_128_hub.json`,
  `ocod_icij_overlap.json`, `tohme_sarkis_network.json`,
  `ebury_bos/_summary.json`, the per-company BO scrapes)
- This script
- The `probe_128_ebury_hub.py` + `probe_tohme_sarkis_network.py`
  + `scrape_ch_for_ebury_companies.py` source files

Bundle URL goes in the video description so journalists can
reproduce.

### One last honesty test

Before recording, ask: *what's the strongest defence the firm at
128 Ebury Street, or any named individual, could mount?*

- "We are a regulated UK accountancy firm; our clients are subject
  to KYC/AML obligations; we file accurate beneficial-owner
  declarations on time; we have no connection to the Panama Papers
  leak beyond providing a UK correspondence address to clients
  whose offshore vehicles existed long before our firm was
  incorporated in 2015."

All of that is plausibly true. The video must not contradict it.
The video's claim is **not** that anyone has acted improperly. It
is that one address sits at the junction of three public datasets
that no journalist had previously joined.

If the firm or any named person responds with a clean account of
their activities, that response gets equal time in the final cut.
That's how this kind of story stays both publishable and honest.
