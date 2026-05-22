# GoldenMatch shell-company-network — three case studies + one methodology appendix

A coordinated production package: three UK video case studies plus
a US methodology appendix, all generated from the same open-source
pipeline that joins ICIJ Offshore Leaks, HM Land Registry OCOD,
the UK Companies House Register of Overseas Entities, NYC ACRIS,
and OpenSanctions.

All four pieces source every claim to free public registers. None
of them allege wrongdoing against any individual, firm, or entity
named. The three UK pieces have pre-publication checklists
requiring UK media-lawyer review and right of reply; the US
appendix has no individuals named and ships without lawyer
review.

| File | Scale | Audience | Status |
| --- | --- | --- | --- |
| [`128_ebury_street_case_study.md`](128_ebury_street_case_study.md) | One Belgravia firm + 119 titles + £137M | General-audience investigative | Drafted, pending lawyer review |
| [`petrol_forecourts_jersey_case_study.md`](petrol_forecourts_jersey_case_study.md) | UK petrol-forecourts + logistics ROIs via Jersey + £15B+ | Industry / regulatory | Drafted, pending lawyer review |
| [`channel_islands_hubs_case_study.md`](channel_islands_hubs_case_study.md) | The full top-10 hubs picture (£35.4B / 14,244 titles) | Methodology + national-policy | Drafted, pending lawyer review |
| [`us_appendix_methodology_paper.md`](us_appendix_methodology_paper.md) | US methodology appendix — why the same join doesn't transplant from UK to NYC ACRIS without federal BO disclosure | OECD / EU 6AMLD / FinCEN CTA review / US Congress | Drafted, ready to ship (no individuals named) |
| [`barilla_jamers_case_study.md`](barilla_jamers_case_study.md) | Single-family BVI structure | Filed for the future (already-reported finding) | Filed |

## Recommended publication order

1. **128 Ebury Street** first — the most concrete, most accessible.
   The court-validated corroboration via *Al-Rawi v Sidawi & Ors*
   [2023] EWHC 1415 (Ch) makes it the lowest-risk piece to record
   first. Run pre-publication procedure with this script as the
   reference template.

2. **Petrol forecourts via Jersey (Appleby)** second — the same
   methodology applied to a specific industry sector, with
   LSE-listed and PE-backed companies named. Higher commercial
   stakes; the methodology and right-of-reply pattern is already
   established by the first piece.

3. **Channel Islands hubs (institutional)** third — the
   methodology paper itself. The audience is regulators, the OECD,
   the EU Beneficial Ownership Directive review, and UK
   parliamentary committees. The piece is descriptive (£35B
   passes through six addresses) rather than accusatory.

Treating the three together as a *package* with a shared opening
banner ("From the GoldenMatch shell-company-network methodology
series") helps the audience recognise that the same pipeline
generated all three, and that each story is a different view of
the same underlying public data.

## Shared elements across all three scripts

### Pre-roll legal note (identical in all three)

```
This series discusses publicly disclosed beneficial-ownership
information. Offshore ownership of UK property, the use of the
2016/2017 leaked corporate-services providers, and the engagement
of UK-regulated accountancy and legal firms are lawful. No
wrongdoing is alleged against any individual, firm, or entity
named. All sources cited are free public registers; every
URL on-screen is one that the viewer can verify themselves.
```

### Shared sources block (in each script's outro)

```
Data sources cited

ICIJ Offshore Leaks Database
   offshoreleaks.icij.org   (CC BY-SA 4.0)

HM Land Registry OCOD
   use-land-property-data.service.gov.uk/datasets/ocod
   (OGL v3.0; Crown copyright)

UK Companies House
   find-and-update.company-information.service.gov.uk   (Public)

BAILII (UK court judgments)
   bailii.org   (Public)

Open-source pipeline:
   github.com/benseverndev-oss/goldenmatch-shell-company-network
   (MIT)
```

### Shared "honesty test" framing

Before recording each video, ask: **what's the strongest defence
the firms and individuals named could mount?** Each script's
final act must not contradict a plausible legitimate explanation.
The point of each piece is not to accuse — it is to show that one
public-data pipeline can reconstruct in five minutes what would
take a journalist several days of single-source searches.

## Pre-publication checklist (applies to all three)

- [ ] UK media-lawyer review of the specific script being recorded.
- [ ] Right-of-reply (minimum 7 working days) to every named
      natural person via their declared UK correspondence address.
- [ ] For corporate respondents: notification via Companies House
      registered office to (a) the firm itself, (b) the firm's
      regulator (ICAEW for accountants, SRA / Bar Standards Board
      / Law Society of Jersey / Guernsey Bar for lawyers, FCA for
      financial services).
- [ ] For LSE-listed respondents (Tritax Big Box REIT plc): notify
      the company secretary directly and observe market-abuse
      cooling-off conventions if the piece could move share price.
- [ ] For non-UK heads-of-state-family respondents (Sheikh Thani
      Al-Thani): notify the relevant embassy in London.
- [ ] Wayback-archive every cited URL the day before publication.
- [ ] Re-verify every ROE filing is current on the day of publish.
- [ ] If any named individual's response materially changes the
      narrative, recut before publish — equal time is the rule.

## Reproducibility bundle

Every claim in every script is backed by data in
`cluster_*_aleph_bundle.zip` artefacts produced by
`scripts/build_*_bundle.py`. Each bundle contains:
- the video script
- every Railway-side probe JSON that backs the script
- captured HTML of every cited Companies House + ICIJ + BAILII
  page (sha256-hashed in the manifest)
- the Python source of every probe that produced the data

Journalists can verify any sha256 against an independent fetch
to confirm the bundle hasn't been altered.

## What this package proves (the meta-claim)

The point of the package isn't *what* the pipeline finds. It's
*how cheaply* it finds it. Five minutes of compute against a
£0/month corpus of free public datasets produces:

- A specific Belgravia advisory operation with court-validated
  corroboration (case 1).
- A specific industry sector (petrol forecourts + logistics)
  routed through one Jersey law firm and documented in a 2017
  leak (case 2).
- An institutional picture of where £35 billion of UK property
  ownership sits in the offshore-administration landscape
  (case 3).

If the pipeline can reconstruct that much from public data in
five minutes, the bottleneck on investigative journalism in this
space is not "we don't have the data." It is "nobody has joined
the data yet."
