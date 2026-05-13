---
title: "Sanctioned Russians on the UK PSC register — what an automated join surfaces"
subtitle: "Joining OpenSanctions against UK Companies House beneficial-ownership disclosures with a public entity-resolution pipeline"
canonical_url: ""
tags:
  - entity-resolution
  - investigative-data
  - sanctions
  - companies-house
  - opensanctions
  - python
cover: ""
publish_date: ""
---

> **Hypothesis, not proof.** Every match in this post is a name +
> country coincidence between two public datasets. Identity confirmation
> still requires DOB / passport / known-prior-filing checks. I cite
> Wikidata IDs and UK Companies House PSC numbers where I have them,
> and hedge anything I don't.

## The setup

I run [`goldenmatch-shell-company-network`](https://github.com/benzsevern/goldenmatch-shell-company-network)
as a case study in cross-source entity resolution. The premise is
simple: take a corpus of public data about offshore companies and
sanctioned individuals, normalise the rows, and surface the joins that
investigative journalism has either taken years to do manually or
hasn't done at all.

Earlier in the series I ran the matcher against the consolidated
OpenSanctions sanctions / crime / Interpol-Red-Notice lists vs ICIJ
Offshore Leaks officers. It produced 132 unique non-Chinese exact-name
matches. After verifying five of them against primary sources, the
finding was discouraging: *every single one mapped to already-published
journalism.* Schiavone, Kolbin, Vassiliades, Putin's cousin, the
Saifullah brothers, the Maltese fuel-smugglers — all worked-through
cases. The matcher was rediscovering, not discovering.

The diagnosis was structural: ICIJ + OpenSanctions are exactly the two
corpora investigative outlets have been mining for years. Anything the
match would catch, OCCRP / ICIJ / The Insider / Bellingcat / Times of
Malta / Dawn already caught with a human in the loop.

The fix was to add a corpus those outlets *haven't* exhaustively
mined: **UK Companies House beneficial-ownership data**, specifically
the People with Significant Control (PSC) Register plus the Register
of Overseas Entities, both republished by OpenOwnership in their BODS
format.

## What the UK PSC register is

Since 2016 every UK company has been legally required to declare its
ultimate beneficial owners — Persons of Significant Control. Since
2022 every overseas company that owns UK property has had to do the
same. Both registers are public.

OpenOwnership re-publishes both as one 3.67 GB BODS parquet bundle
covering 12.15 million person statements and 5.79 million entity
statements. The BODS format is normalised — name, nationality,
address, identifiers all live in separate parquets joined back to a
spine table by foreign key.

This is the *officially disclosed* beneficial-ownership data, not
leaked-provider records. The legal floor is much higher than ICIJ:
if a name appears here, the company's directors swore to it.

## What ran

I added an adapter for the BODS bundle to the pipeline, ingested the
two register slices on a Railway container, rebuilt the unified
person table (which grew from 1.95 M rows to 14.02 M rows), and re-ran
the list-match against the same OpenSanctions reference set (121 050
sanction / crime / Interpol-tagged persons).

Practical caveat: the matcher's blocking config OOMs on common
first-name blocks once you add the full UK PSC corpus to the target
("Anthony" alone has 168 000 records on the UK register). I scoped the
target's UK PSC contribution to five sanctions-relevant countries:
Russia, Ukraine, Belarus, Cyprus, Kazakhstan. That's the explicit
"sanctioned Russian via UK Ltd / Cypriot enabler" pattern, and exactly
what the join is most likely to surface clean signal on.

The list-match ran in about 11 minutes on the Railway box.

## Result

| | Previous run (ICIJ + OpenSanctions) | + UK PSC (ru/ua/by/cy/kz) |
| --- | ---: | ---: |
| Matched pairs (score ≥ 0.80) | 47,411 | 57,229 |
| Exact-normalized-name matches | 611 | 670 |
| UK PSC novel exact-name unique names | 0 | **43** |

Forty-three new individuals. Each one declared themselves to UK
Companies House as a beneficial owner of a UK company *and* shares an
exact name + country with a row on a public sanctions or
politically-exposed-persons list.

## The Wikidata-anchored slice

These are the easiest hits to verify because Wikidata carries a
biography you can cross-reference against the UK PSC declaration's
month-of-birth + nationality.

| Name | Country | Wikidata | What public sources say |
| --- | --- | --- | --- |
| Mr Igor Vladimirovich Zyuzin | RU | `Q4194951` | Controlling shareholder of Mechel (Russian coal + steel). UK, EU, Switzerland sanctions post-2022. |
| Mr Andrey Filatov | RU | `Q2336310` | Sibanthracite (Russian coal export); art collector. UK + EU sanctions. |
| Alexander Abramov | RU | `Q4054890` | Evraz co-founder and chairman; UK + EU sanctions. Also appeared in ICIJ in the earlier run. |
| Ms Oksana Marchenko | UA | `Q4283159` | Wife of Viktor Medvedchuk, the pro-Russian Ukrainian politician who was Putin's preferred negotiating partner. EU-sanctioned. |
| Kirill Seleznev | RU | `Q6415267` | Former CEO of Gazprom Mezhregiongaz. |
| Mr Yury Vasilyev | RU | `Q19861744` | Russian politician (verify which one — common name in Russian Duma rolls). |
| Olga Vladimirovna Korobova | RU | `Q108616243` | Russian PEP. |

Three more Aleksandr* Wikidata hits in the result table need disambiguation:
`Aleksandr Potapov Q28862235`, `Aleksandr Shcherbakov Q108685063`,
`Aleksandr Zhuk Q13028277`. Russian first-name conventions make
"Aleksandr [Surname]" extremely common; the matcher caught all three
without distinguishing.

## Companies House PSC IDs

Where the OS row is OS-internal (`NK-*`) or where the OS profile itself
captured the UK Companies House PSC ID directly, the match returns the
specific UK company number. That's the publication-grade part of the
result: anyone can take the company number and pull the underlying
filing from <https://find-and-update.company-information.service.gov.uk/>.

| Name | Country | UK PSC reference | Note |
| --- | --- | --- | --- |
| Mr Nikita Mordashov | RU | `NK-FDpsUY77HooCKp` | Son of Alexey Mordashov (sanctioned Severstal owner). |
| Mr. Evgeny Giner | RU | `gb-coh-psc-04128720-…` | CSKA Moscow owner. |
| Alexey Isaykin | CY | `gb-coh-psc-09605430-…` and `gb-coh-psc-09652290-…` | Founder of Volga-Dnepr Airlines. Two separate UK PSC declarations. |
| Mr Maxim Viktorov | RU | `gb-coh-psc-04092367-…` | Russian businessman; classical-music collector / Concertino Capital. |
| Marat Timurov | KZ | `gb-coh-psc-15109642-…` | Kazakhstani PSC. |
| Ms. Natalia Degtiar | RU | `gb-coh-psc-OC425116-…` | LLP (limited liability partnership) PSC. |
| Ms Maria Vovk | RU | `gb-coh-psc-OC428060-…` | LLP PSC. |
| Sergei Kondratenko | CY | `NK-DY9E2mYcUQYFk3` | Cyprus-based Russian PSC. |
| Andrei Horbach | BY | `NK-VLXNrsz6Dvb8tM` | Belarusian, sanctioned. |
| Andrey Ignatyev | RU | `cz-person-andrey-ignatyev-…` | On the Czech sanctions list. |

## Interpol Red Notice subjects on the UK register

Four Interpol Red Notice subjects appear with UK PSC declarations:

- Oleg Tarasov (RU)
- Mikhail Serov (RU)
- Andrey Ivanov (RU; common name — needs disambiguation)
- Alexander Orlov (RU)

A wanted-person notice plus a declared UK-company beneficial ownership
is exactly the pattern the Companies House Verification programme was
built to flag.

## What this proves and what it doesn't

**What it proves.** Joining public OpenSanctions data against public
UK PSC declarations programmatically surfaces forty-three concrete
sanctioned-individual-as-UK-beneficial-owner candidate links in
about ten minutes of compute time. Most appear on lists journalists
were already familiar with (UK + EU asset freezes, the Russian
oligarch-tracking projects). The specific UK company numbers attached
to each row are publication-grade pointers anyone can pull and verify.

**What it does not prove.** A name + country match is a *lead*. Two
"Andrey Ivanov" people in Russia is unsurprising. Each row needs
either:

1. DOB cross-check between the OS profile and the Companies House
   PSC filing (Companies House gives month + year of birth on PSC
   declarations).
2. A known-prior-filing cross-reference (does this individual already
   appear in published reporting tied to this specific UK company?).
3. Address cross-check (the PSC filing has an address; OS often does
   too).

I deliberately haven't done that verification for any specific row
here. The point of this post is to show the *method*, not to
single-name-publish any individual. The forty-three rows are
candidates for an investigative reporter or compliance team to
review, not findings to publish.

## Why this worked when the earlier run didn't

The previous round of the case study failed to find anything novel
because ICIJ + OpenSanctions are *exactly* the two corpora that
investigative outlets have been mining since 2016 (Panama Papers) and
2017 (OFAC + OpenSanctions). Anything the join would catch had
already been caught by a journalist.

UK PSC data is different. It's:

1. *Recent.* The register only became mandatory in 2016 for
   companies and in 2022 for overseas-entity property-owners. There's
   less institutional knowledge about who's on it.
2. *Officially disclosed.* The declarations are legally required —
   the floor is much higher than leaked-provider records.
3. *Less mined.* The Times' "Foreigners and the Roman Abramovich
   Football Club" investigations + OCCRP's Russian Asset Tracker have
   worked specific subsets, but the *systematic* join against
   OpenSanctions across all 12 M PSC declarations has not, to my
   knowledge, been published openly.

The match isn't doing anything magical — it's just running a SQL
INNER JOIN on (normalised_name, country) between two corpora and
filtering to the high-signal sub-table. But because one of those
corpora is less mined than the others, the output contains material
that the matcher has actually *surfaced* rather than just
*rediscovered*.

## Try it yourself

The full pipeline is at
<https://github.com/benzsevern/goldenmatch-shell-company-network>.
The findings doc with the full 43-row table lives at
[`reports/investigations/list_match_uk_psc_findings.md`](https://github.com/benzsevern/goldenmatch-shell-company-network/blob/main/reports/investigations/list_match_uk_psc_findings.md).
The CLI to reproduce:

```bash
# Fetch the OpenOwnership UK BODS bundle (3.67 GB)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$SHELLNET_JOB_URL/fetch-url?url=https%3A%2F%2Foo-bodsdata.s3.amazonaws.com%2Fdata%2Fuk_version_0_4%2Fparquet.zip&dest=raw%2Fopenownership%2Fuk_bods.zip"

# Ingest (joins normalised sub-tables; ~3 min)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$SHELLNET_JOB_URL/run-script?name=ingest_uk_bods"

# Rebuild unified tables
curl -X POST -H "Authorization: Bearer $TOKEN" "$SHELLNET_JOB_URL/build?what=person"
curl -X POST -H "Authorization: Bearer $TOKEN" "$SHELLNET_JOB_URL/build?what=company"

# Run the join
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$SHELLNET_JOB_URL/run-script?name=list_match_os_sanctions_vs_icij"

# Download the result
curl -fL -H "Authorization: Bearer $TOKEN" \
  "$SHELLNET_JOB_URL/download?path=reports/generated/list_match_os_sanctions_vs_icij_matched.csv" \
  -o matched.csv
```

## What's next

`docs/ingestion_roadmap.md` lists the remaining corpora I haven't yet
added: FinCEN Files structured data (BuzzFeed + ICIJ 2020 leak; bank
SARs); GLEIF Level 2 (corporate parent-child ownership graph derived
from LEIs); OCCRP Russian / Troika Laundromat transaction data. Each
of these adds a different *kind* of edge to the unified graph —
respectively bank-flagging, corporate-ownership, and wire-transfer —
and would surface different kinds of join.

The Pareto pattern from this run is clear: every additional corpus
beyond ICIJ + OpenSanctions that hasn't been comprehensively mined by
investigative outlets is where the entity-resolution method delivers
the highest novelty per hour. UK PSC was the largest single such
corpus. The remaining ones are smaller per-row but more specific in
the signals they carry.

---

**About this post.** Companion to the case study at
[`goldenmatch-shell-company-network`](https://github.com/benzsevern/goldenmatch-shell-company-network).
The full machine-readable findings live under
[`reports/investigations/list_match_uk_psc_findings.md`](https://github.com/benzsevern/goldenmatch-shell-company-network/blob/main/reports/investigations/list_match_uk_psc_findings.md).
