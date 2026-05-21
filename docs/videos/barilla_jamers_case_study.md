# Case study: JAMERS INTERNATIONAL S.A — video script

A worked example of the GoldenMatch shell-company-network methodology,
using only public data sources. Demonstrates that a pipeline fusing
ICIJ Offshore Leaks, HM Land Registry OCOD, and the UK Companies
House Register of Overseas Entities can surface a structurally
complete corporate-ownership trail in single-digit minutes of
compute, including connective tissue that single-source search
cannot produce.

**Target length:** 6–8 minutes.
**Tone:** Methodology-forward. No allegations. Every claim cited
on-screen to a public source URL.
**Audience:** Investigative journalists, open-data researchers, and
the engineers who support them.

---

## Pre-roll legal note (on-screen, 3s, fade)

> This video discusses publicly disclosed beneficial-ownership
> information. Offshore ownership of UK property and the use of
> Mossack Fonseca services are lawful. No wrongdoing is alleged
> against any individual or entity named.

---

## Act 1 — The hook (0:00–0:45)

### Shot 1.1 — Cold open (0:00–0:08)

**Visual:** Macro shot of a Barilla pasta box on a kitchen counter.
Slow pull-back. Soft kitchen light.

**Narration (VO):**
> Italy's largest pasta producer is owned by four siblings: Guido,
> Luca, Paolo, and Emanuela Barilla. They are heirs of a family
> business founded in 1877.

### Shot 1.2 — Title card (0:08–0:14)

**Visual:** Black card. White serif text:
```
THE FIVE-MINUTE LINK
A worked example of public-data investigative methodology
```

**Narration:**
> What follows is a five-minute trace through public records — from
> a 2016 leak to a London flat the family's offshore vehicle still
> owns a decade later.

### Shot 1.3 — Pre-empt the obvious objection (0:14–0:45)

**Visual:** Three screenshots stacked, fade-in:
1. AGI April 2016 headline: *"Panama Papers, spunta nuova lista con
   Berlusconi, Galliani e Barilla"*
2. ANSA April 2016: *"Berlusconi-linked firms named in Panama
   Papers"*
3. L'Espresso June 2018: *"Barilla, Corallo e Margherita Agnelli: i
   tesori dei vip d'Italia sono all'estero"*

**Narration:**
> The Barilla family's appearance in the Panama Papers was reported
> in 2016 by Italian outlets AGI and ANSA, and again in 2018 by
> L'Espresso. So this isn't a scoop about the Panama Papers
> themselves. The piece this video adds is one specific connection:
> the flat in London the offshore vehicle bought one year before the
> leak and still owns today. That join is something single-source
> search can't make. A pipeline that fuses three public sources
> made it in five minutes.

---

## Act 2 — The data sources (0:45–2:30)

### Shot 2.1 — Source 1: ICIJ Offshore Leaks (0:45–1:15)

**Visual:** Screen-capture of https://offshoreleaks.icij.org with the
URL bar visible. Then drill down to the public Paolo Barilla node:
https://offshoreleaks.icij.org/nodes/13009747. Camera lingers on the
"Officer of" relationship to JAMERS INTERNATIONAL S.A.

**Narration:**
> Source one: the ICIJ Offshore Leaks Database. Public, free,
> Creative-Commons-licensed. It contains the entity records from
> Mossack Fonseca's leaked client files. Searching for "Barilla"
> surfaces four officer records — one for each of Pietro Barilla's
> children. Three brothers jointly control a 1999 BVI company
> called KIMORA INDUSTRIES LTD. The sister, Emanuela, has her own
> separate 2014 BVI vehicle called JAMERS INTERNATIONAL S.A.

### Shot 2.2 — Source 2: HM Land Registry OCOD (1:15–1:45)

**Visual:** Screen-capture of
https://use-land-property-data.service.gov.uk/datasets/ocod. Show
the dataset description. Then a terminal showing
`head OCOD_FULL_2026_05.csv` with column headers.

**Narration:**
> Source two: HM Land Registry's Overseas Companies Ownership Data.
> Updated quarterly, free under the UK government's Open Government
> Licence, published since 2017. It lists every UK property held by
> an overseas-incorporated company. About fifty thousand titles.

### Shot 2.3 — Source 3: UK Register of Overseas Entities (1:45–2:30)

**Visual:** Companies House search page typing "JAMERS INTERNATIONAL",
landing on https://find-and-update.company-information.service.gov.uk/company/OE014670.
Zoom into the "Beneficial owners" tab.

**Narration:**
> Source three: the UK Companies House Register of Overseas
> Entities. Introduced by the Economic Crime Act of 2022. Every
> foreign company that owns UK property has to declare its
> beneficial owners on this register, publicly. JAMERS INTERNATIONAL
> S.A is registered as OE014670. Its declared beneficial owner is
> Emanuela Barilla, Italian national, date of birth April 1968.
> She filed in August 2017 and last confirmed the declaration on
> the 17th of January 2026.

### Shot 2.4 — The methodology gap (2:30–3:00)

**Visual:** A diagram on a whiteboard or motion graphic:
- Three labelled circles: "Panama Papers (ICIJ)", "OCOD (HMLR)",
  "Register of Overseas Entities (CH)".
- Overlapping centre with a question mark.
- Arrow from the centre to a labelled flat icon.

**Narration:**
> Each source on its own answers a narrow question. ICIJ tells you
> who appeared in the leak. OCOD tells you which overseas companies
> own which UK properties. Companies House tells you who declared
> themselves as beneficial owners. Connecting all three — and
> following the same entity across them — is the work no single
> search bar does.

---

## Act 3 — The pipeline (3:00–4:30)

### Shot 3.1 — Terminal cast: the dispatch (3:00–3:30)

**Visual:** Terminal recording (`asciinema` or VHS-style):
```
$ git pull --ff-only
$ curl -X POST $RAILWAY_URL/run-script?name=probe_high_stakes_bridges
$ curl -X POST $RAILWAY_URL/run-script?name=probe_hmlr_ocod_crossref
$ curl -X POST $RAILWAY_URL/run-script?name=probe_bvi_confirmed_deepdive
$ curl -X POST $RAILWAY_URL/run-script?name=probe_barilla_network
```

Status polling rolls past. Real durations.

**Narration:**
> The pipeline runs server-side. Five HTTP POSTs trigger five probes
> against the parquet-stored corpus. Each probe takes about thirty
> seconds. Total runtime: under five minutes. The result is a
> series of small JSON files containing the joins.

### Shot 3.2 — Result drilldown (3:30–4:30)

**Visual:** JSON files on screen, sequenced:
1. `sanctions_overlap.json` — quickly scroll, "no matches"
2. `ocod_icij_overlap.json` — highlight three BVI-confirmed rows
3. `bvi_deepdive.json` — zoom on JAMERS block, point at Emanuela
   Barilla officer line + Flat 5, 134 St Albans Avenue
4. `barilla_network.json` — show all four siblings in
   wide_barilla_scan

**Narration:**
> The first probe — looking for SEC-13D filers on US sanctions
> lists — returned no substantive hits. That's a useful negative.
> The second probe — overseas-company UK property owners that
> appear in the Panama Papers — returned seventy-nine candidates,
> three of them with confirmed BVI jurisdiction on both sides. One
> of those three is JAMERS INTERNATIONAL S.A. The deep-dive shows
> Emanuela Barilla as named officer and one UK property. The wide
> scan recovers the entire Italian Barilla family — all four
> siblings — across Mossack Fonseca's records.

---

## Act 4 — The finding (4:30–6:30)

### Shot 4.1 — The two-vehicle family structure (4:30–5:15)

**Visual:** Animated network graph:
- Four nodes labelled Guido, Luca, Paolo, Emanuela Barilla
- Three brothers → KIMORA INDUSTRIES LTD (BVI, 1999, bearer shares)
- Emanuela → JAMERS INTERNATIONAL S.A (BVI, 2014)
- Both vehicles connected to MAYA INTERNATIONAL FOUNDATION (Panama)
- JAMERS → Flat 5, 134 St Albans Avenue, London W4 5JR
- Every edge annotated with source URL

**Narration:**
> Here is the structure the pipeline surfaces. The three brothers
> share one BVI vehicle from 1999, KIMORA INDUSTRIES, which used
> bearer shares in its original Mossack Fonseca filings — that
> means the holder of the physical share certificate was the legal
> owner, anonymous on paper. The sister, Emanuela, opened her own
> BVI vehicle, JAMERS INTERNATIONAL, in August 2014. Both vehicles
> share a Panamanian foundation, Maya International Foundation, as
> a co-officer — the link between the brothers' and the sister's
> structures.

### Shot 4.2 — The London property (5:15–6:00)

**Visual:** Street View pull-up of 134 St Albans Avenue, London W4
5JR. Linger on the building facade for two seconds. Cut to the OCOD
parquet row:
```
property_address:        Flat 5, 134 St Albans Avenue, London (W4 5JR)
postcode:                W4 5JR
title_number:            ...
proprietor_name:         JAMERS INTERNATIONAL S.A
country_incorporated:    BRITISH VIRGIN ISLANDS
date_proprietor_added:   30-03-2015
price_paid:              380000
```

**Narration:**
> On the thirtieth of March 2015 — one year before the Panama
> Papers leak became public — JAMERS INTERNATIONAL S.A purchased
> Flat 5, 134 St Albans Avenue in West London, postcode W4 5JR, for
> three hundred and eighty thousand pounds. Per HM Land Registry's
> May 2026 OCOD release, the company still holds the title. Per
> the UK Register of Overseas Entities, Emanuela Barilla is the
> sole declared beneficial owner of the company, with that
> declaration last confirmed on the seventeenth of January 2026.

### Shot 4.3 — The honest caveat (6:00–6:30)

**Visual:** Plain text on black:
```
Offshore ownership of UK property is legal.
Tens of thousands of titles are held this way.
This video does not allege wrongdoing.
The 2022 Economic Crime Act required this disclosure;
it is being followed correctly.
```

**Narration:**
> To be absolutely clear: there is no allegation of wrongdoing
> here. Offshore ownership of UK property is legal. The Barilla
> family's holdings have been disclosed in compliance with every
> applicable law. The 2022 Economic Crime Act explicitly required
> this kind of beneficial-owner declaration; the family has filed
> correctly and on time. The point of this case study is not the
> ethics of the structure but the difficulty of finding it.

---

## Act 5 — The methodology takeaway (6:30–8:00)

### Shot 5.1 — Why this matters (6:30–7:15)

**Visual:** Split-screen comparison.
- Left: a journalist's browser with five tabs open — ICIJ search,
  Companies House, HMLR portal, Google, Wikipedia. Stopwatch
  ticking at 04:23:11 marked "without the pipeline".
- Right: a single terminal with five curl commands and a JSON
  output. Stopwatch at 00:04:47 marked "with the pipeline".

**Narration:**
> An investigative journalist using single-source search would have
> to query each public source separately, hold the results in their
> head or a notebook, and connect them by hand. Possible, but
> expensive — the bottleneck is the join, not the search. The
> pipeline does the join for you. Five minutes of compute against
> public data. The Barilla example here is one of seventy-nine
> candidates the pipeline surfaced in a single run. Each of the
> other seventy-eight is a similar lead a journalist could now
> investigate.

### Shot 5.2 — The repository (7:15–7:45)

**Visual:** GitHub repo page:
`https://github.com/benseverndev-oss/goldenmatch-shell-company-network`.
README scroll. Highlight the LICENSE file (MIT).

**Narration:**
> The pipeline is open source. MIT licence on the code, share-alike
> licences honoured for each upstream dataset, full attribution to
> ICIJ, HM Land Registry, and Companies House preserved in every
> derived artefact. Anyone who wants to run their own join can.

### Shot 5.3 — Outro (7:45–8:00)

**Visual:** Black card with white text:
```
Data sources cited in this video

ICIJ Offshore Leaks Database
   offshoreleaks.icij.org   (CC BY-SA 4.0)

HM Land Registry OCOD
   use-land-property-data.service.gov.uk/datasets/ocod
   (OGL v3.0; Crown copyright)

UK Companies House Register of Overseas Entities
   find-and-update.company-information.service.gov.uk
   (Public)

Prior reporting on Barilla family Panama Papers presence

AGI, 14 April 2016
ANSA, 14 April 2016
L'Espresso, 28 June 2018
```

Then fade to:
```
github.com/benseverndev-oss/goldenmatch-shell-company-network
```

**Narration:**
> All sources are linked in the description. Thanks for watching.

---

## Production notes

### Shot list summary

| # | Duration | Type | Asset needed |
|---|---:|---|---|
| 1.1 | 8s | Live action | Pasta-box close-up |
| 1.2 | 6s | Title card | Static |
| 1.3 | 31s | Screenshot stack | 3 Italian press headlines |
| 2.1 | 30s | Screen-cap | ICIJ Offshore Leaks DB |
| 2.2 | 30s | Screen-cap | HMLR data service + CSV terminal |
| 2.3 | 45s | Screen-cap | Companies House OE014670 |
| 2.4 | 30s | Motion graphic | Three-circle Venn |
| 3.1 | 30s | Terminal-cast | VHS / asciinema |
| 3.2 | 60s | JSON walk-through | 4 result files |
| 4.1 | 45s | Animated graph | Network diagram |
| 4.2 | 45s | Street View + table | Google Street View at W4 5JR |
| 4.3 | 30s | Plain text card | Static |
| 5.1 | 45s | Split-screen | Browser vs. terminal |
| 5.2 | 30s | Screen-cap | GitHub repo |
| 5.3 | 15s | Static credits | Source citations |

**Total runtime: ~7m 30s.**

### Voiceover notes

- Read narration straight, no music ducking below VO.
- Avoid emphasis on names. The story is the methodology, not the
  family.
- When citing dates and prices, slow down. Each number is a
  load-bearing fact the viewer should be able to verify.

### Music + sound

- No music in Act 4 (the finding) — silence draws attention to the
  cited facts.
- Soft synth in Acts 1, 2, 5. Public-domain or
  CC-BY-licensed only.

### Cited URLs (must all appear on-screen at some point)

1. `https://offshoreleaks.icij.org/`
2. `https://offshoreleaks.icij.org/nodes/13009747` (Paolo Barilla)
3. `https://use-land-property-data.service.gov.uk/datasets/ocod`
4. `https://find-and-update.company-information.service.gov.uk/company/OE014670`
5. `https://www.agi.it/estero/news/2016-04-14/panama_papers_spunta_nuova_lista_con_galliani_barilla_e_berlusconi-694821/`
6. `https://www.ansa.it/english/news/general_news/2016/04/14/more-italians-names-in-panama-papers_805e3af7-d071-447d-ab4d-d0fe1d758039.html`
7. `https://lespresso.it/c/attualita/2018/6/28/barilla-corallo-e-margherita-agnelli-i-tesori-dei-vip-ditalia-sono-allestero/10715`
8. `https://github.com/benseverndev-oss/goldenmatch-shell-company-network`

### Pre-publication checklist

- [ ] Have a UK media lawyer or experienced libel editor review the
      script.
- [ ] Re-verify the Emanuela Barilla DOB and address against UK
      Companies House live record on the day of recording.
- [ ] Re-verify HMLR OCOD May 2026 — if a newer release exists,
      confirm the title is still held.
- [ ] Notify the Barilla family communications team before
      publication and offer a 48-hour right of reply. Document the
      attempt.
- [ ] Archive every cited URL on the Wayback Machine pre-publication
      so links remain accessible after the video drops.

### Bundle artefact

Pair the video with the standard `cluster_barilla_aleph_bundle.zip`
(FollowTheMoney ndjson + archived HTML of every cited source + the
five probe-result JSONs + this script + the
`probe_*` scripts that produced the findings). Publish the bundle
URL in the video description so any viewer with `alephclient` can
reproduce the case study end-to-end.
