# Investigative-grade survivors after DOB + coverage filters

Generated 2026-05-13. End-state of the DOB-triangulation + news-
coverage pipeline (PRs #40–#42).

> **Hypothesis, not proof.** Every survivor below is a name + country
> match between OS sanctions / Interpol / Wikidata records and a UK
> Companies House PSC declaration. DOB year-match adds identity
> confidence but is not full identity proof — DOB month + year alone
> isn't a unique discriminator at population scale. Each row is a
> publication-grade *lead* that still warrants source-document review
> (Companies House filing, sanctions order, Wikidata DOB exact day)
> before any single-name claim.

## What ran

The pipeline is now three composable post-processors over the v3
list-match output:

1. **`enrich_match_with_dob`** — pulls `recordDetails_birthDate` from
   the UK PSC BODS spine and `properties.birthDate` from the OS
   raw_json. Classifies each match row into
   `both_present_year_match` / `both_present_year_mismatch` /
   `ref_only` / `target_only` / `neither`.

2. **`score_prior_coverage`** — for each unique (target_name,
   target_country) tuple, runs a Firecrawl search and counts
   results from a known list of mainstream investigative outlets
   (ICIJ, OCCRP, Reuters, FT, NYT, WaPo, Guardian, WSJ, BBC,
   Bloomberg, OFAC press, plus Russian / Ukrainian outlets).

3. **`filter_match_survivors`** — keeps only:
   - exact-normalized-name matches
   - non-CN (`target_country != cn`)
   - DOB confirms or is non-contradictory
     (`both_present_year_match` / `ref_only` / `target_only`)
   - zero mainstream coverage

Final result: **29 unique survivors** from the 57,229-row input.

## DOB triangulation impact

| dob_match bucket | count |
| --- | ---: |
| `ref_only` (OS has DOB, UK PSC doesn't) | 29,178 |
| `neither` | 18,233 |
| **`both_present_year_mismatch`** | **8,941** |
| `target_only` (UK PSC has DOB, OS doesn't) | 537 |
| `both_present_year_match` | 340 |

Of the 9,281 rows where both sides carry a DOB, **only 340 (3.7%) have
year agreement**. The other 8,941 are same-name-country pairs of
*different people* — the matcher's name-only join had ~96% noise on
that slice. DOB triangulation collapses that to the ~4% that survive
year agreement.

## The 29 survivors

### Tier A: DOB year-match + low total coverage (genuinely under-reported)

These are the highest-confidence + lowest-prior-coverage survivors —
the closest thing to publication-grade output the pipeline produced.

| Name | Country | Reference | DOB | cov | Public context |
| --- | --- | --- | ---: | ---: | --- |
| **Mr Maxim Viktorov** | RU | UK CH PSC `04092367` | 1972-06 | **1** | Russian businessman / classical-music collector. UK PSC declaration. Almost no English-language press. |
| **Mr. Roman Viktorovich Trotsenko** | RU | Wikidata `Q61814491` | (match) | 3 | Aeon Corporation owner; Russian transport / infrastructure tycoon. Q-ID anchored. |
| **Ms. Natalia Degtiar** | RU | UK CH PSC `OC425116` (LLP) | (match) | 3 | UK Limited Liability Partnership PSC. |
| **Ms Maria Vovk** | RU | UK CH PSC `OC428060` (LLP) | (match) | 3 | UK Limited Liability Partnership PSC. |
| **Mr Nikita Mordashov** | RU | OS `NK-FDpsUY77HooCKp...` | (match) | 4 | Son of Alexey Mordashov (sanctioned Severstal). |
| **Ms Oksana Marchenko** | UA | Wikidata `Q4283159` | (match) | 4 | Wife of Viktor Medvedchuk (Putin-ally Ukrainian politician). EU-sanctioned. |
| **Mr Marat Timurov** | KZ | UK CH PSC `15109642` | (match) | 5 | Kazakhstani PSC of a UK company. |

### Tier B: DOB year-match + coverage-ceiling hits (well-known names, host filter under-counted)

These all reached the cov=8 ceiling but no result fell into the
mainstream-outlet host list. Most are sanctioned, well-known figures
whose coverage runs through outlets the host filter didn't include
(sanctions trackers, financial-data sites, OS itself). Filter
calibration issue rather than novelty:

- **Mr Igor Vladimirovich Zyuzin** (Mechel, Wikidata `Q4194951`)
- **Mr Arkady Volozh** (Yandex co-founder, `Q4123823`)
- **Mr. Evgeny Giner** (CSKA Moscow)
- **Mr Alexey Isaykin** + **Alexey Isaykin** (Volga-Dnepr Airlines —
  two separate UK PSC declarations)
- **Sergei Kondratenko** (Cyprus)
- **Alexey Andreev** (Interpol Red 2016-69269)

### Tier C: One-sided DOB (`ref_only` / `target_only`) — confirmed-on-one-side only

When only the OS side has a DOB, identity is non-contradicted but
not directly confirmed. The matcher's name + country match holds;
DOB just doesn't disqualify it. These are 15 rows including:

- **IGOR KHANUKOVICH YUSUFOV** (former Russian Energy Minister, `Q4535427`)
- **ANDREY LEBEDEV** (`Q18786071`)
- **YURY VASILYEV** (`Q19861744`)
- **ELENA PERMINOVA** (`Q55437706`)
- **Vladimir Filippov** (`Q2636066`)
- **PAUL SA** (`Q4341227`)
- **Maria Lebedeva** (`Q107097778`, target_only)
- Several Interpol Red Notice subjects: Andrey Ivanov, Aleksey
  Alekseev, Sergey Kovalevskiy, Sandeep
- Polish-wanted: Volkov Vladimir, NOVIKOV ROMAN, Taylor - Robert,
  NGUYEN CHI DUNG

## Reading the result honestly

**The pipeline now produces ~7 publication-grade leads** (Tier A
above) where the original v3 produced 43 candidates with no
disambiguation. That's a meaningful step toward investigative-grade
output — DOB year-match collapses the noise, coverage scoring sorts
by novelty.

**Notable specific lead:** **Maxim Viktorov** with cov=1 is the
single lowest-prior-coverage row in the entire survivor set. UK
Companies House PSC `04092367`, b. June 1972, declared in OS as a
sanctioned Russian (concrete ref:
`opensanctions:gb-coh-psc-04092367-vvqx31aqkmw6jpb4tie4umsu-as`). The
DOB month + year matches between the UK declaration and the OS
record. No mainstream English-language coverage. This is the kind
of row a compliance team or asset-tracker reporter would put at the
top of their review pile.

**Filter calibration caveats:**

- The `MAINSTREAM_HOSTS` set in `score_prior_coverage.py` is
  curated, not exhaustive. Sanctions-tracker sites, financial-data
  aggregators, and OFAC's own press releases aren't in it — so
  well-known sanctioned figures (Zyuzin, Volozh, Giner) score
  zero mainstream coverage even when their canonical references
  exist. Expanding the host list to ~50 outlets would tighten this.
- The Firecrawl `--limit 8` ceiling means we can't distinguish
  cov=8 from cov=80. Increasing to `--limit 20` would give better
  resolution on the "well-known" rows.
- DOB year-match is necessary but not sufficient — population-level
  many sanctioned Russians of the same name share a birth year by
  chance. Adding the OS record's `birthPlace` or address-city
  match would tighten further.

## Pipeline composability

The combined four-step Railway pipeline now is:

```
list_match_os_sanctions_vs_icij  →  47k matched pairs
       ↓
enrich_match_with_dob            →  +3 cols (target_dob, ref_dob, dob_match)
       ↓
score_prior_coverage             →  +2 cols (prior_coverage_n, _mainstream)
       ↓
filter_match_survivors           →  29 investigative-grade rows
```

Each is a separate `/run-script` allowlist entry, runs against
Railway-side parquets, and emits a small CSV that the next step
consumes. Reproducible end-to-end in ~20 minutes of compute,
0 minutes of laptop RAM.

## What this changes about the project posture

Before this round, the matcher's output was "candidate leads
filtered manually by human verification" — i.e., raw matched.csv
plus firecrawl follow-up per row. The DOB + coverage step turns
that into "small, ranked, pre-filtered survivor list with
confidence and novelty signals attached."

The remaining gap to true investigative-grade is essentially manual
review of the ~7 Tier A rows: confirm each company filing,
cross-reference OS source documents, write per-row dossiers. That's
the journalism, not the engineering. The matcher + post-processors
have done what they can do without a human in the loop.
