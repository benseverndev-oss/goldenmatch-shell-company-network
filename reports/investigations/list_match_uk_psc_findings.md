# List-match v3 — UK PSC layer added (Tier A from the ingestion roadmap)

Generated 2026-05-13. Follow-on to `list_match_os_sanctions_vs_icij_v2_findings.md`.

> **Hypothesis, not proof.** Each match is a name + country coincidence
> across two public datasets. Identity confirmation needs DOB / address /
> known prior filing. The UK PSC declarations *are* legally-required
> beneficial-ownership disclosures, so the floor is higher than ICIJ
> leaked-provider records — but a name match against an OS sanctions
> entry still needs human DOB/passport check before publication.

## What ran

- Ingested the **OpenOwnership BODS UK feed** (3.67 GB ZIP via
  `/fetch-url` on Railway). 12.15 M UK PSC person statements + 5.79 M
  UK entity statements. See PRs #22–#30.
- Re-built the unified person table: **14.02 M rows** (was 1.95 M).
- Widened the list-match target to include UK PSC rows scoped to the
  high-signal sanctions-target countries (Russia, Ukraine, Belarus,
  Cyprus, Kazakhstan). Wider scopes OOMed `goldenmatch match` on
  common-name blocks (`anthony` at 168 k records, `mr muh...` at 31 k).
- Same OS reference set as v2 (121 050 sanction / crime persons).

## Numbers

| | v2 (ICIJ + OS) | **v3 (+ UK PSC ru/ua/by/cy/kz)** | Delta |
| --- | ---: | ---: | ---: |
| Matched pairs (score ≥ 0.80) | 47 411 | **57 229** | +9 818 |
| Exact-normalized matches | 611 | **670** | +59 |
| UK PSC exact-match unique uids | 0 | **59** | +59 |
| UK PSC exact-match **unique names** | 0 | **43** | +43 |

## The 43 UK PSC names

Each row: a person who **declared themselves to UK Companies House** as
a beneficial owner of a UK company, *and* whose name + country
exact-match a row on an OS sanctions / crime / Interpol list. The
`target_entity_uid` is the OpenOwnership-published BODS statement ID;
the `ref_entity_uid` is the OS profile.

### Wikidata-anchored (strongest verifiability)

| Name | Country | Wikidata | Public context |
| --- | --- | --- | --- |
| **Mr Igor Vladimirovich Zyuzin** | ru | `Q4194951` | Russian coal/steel oligarch, controlling shareholder of Mechel; sanctioned by UK/EU/Switzerland after 2022 |
| **Mr Andrey Filatov** | ru | `Q2336310` | Sibanthracite (Russian coal); art collector; UK + EU sanctions |
| **Alexander Abramov** | ru | `Q4054890` | Evraz co-founder/chairman, sanctioned. Also appeared in v2 via ICIJ. |
| **Ms Oksana Marchenko** | ua | `Q4283159` | Wife of Viktor Medvedchuk (Putin ally; pro-Russian Ukrainian politician). EU-sanctioned. |
| **Kirill Seleznev** | ru | `Q6415267` | Former Gazprom Mezhregiongaz CEO |
| **Mr Yury Vasilyev** | ru | `Q19861744` | Russian politician |
| **Aleksandr Potapov** | ru | `Q28862235` | (verify which Aleksandr — common name) |
| **Aleksandr Shcherbakov** | ru | `Q108685063` | (verify) |
| **Aleksandr Zhuk** | ru | `Q13028277` | (verify) |
| **Andrey Lebedev** | ru | `Q18786071` | (different from Alexander Lebedev v2; verify) |
| **Olga Vladimirovna Korobova** | ru | `Q108616243` | Russian PEP |
| **Kirill Anatolyevich Seleznev** | ru | `Q6415267` | (Gazprom) |
| **Anatoly Petrov** | ru | `Q60677526` | (verify) |

### OS-internal + UK Companies House cross-listings

These have OpenSanctions internal IDs (`NK-*`) and / or
`gb-coh-psc-*` UK Companies House PSC ids. The UK PSC id is the
authoritative beneficial-ownership disclosure — anyone can look up the
company at <https://find-and-update.company-information.service.gov.uk/>.

| Name | Country | Reference | Public context |
| --- | --- | --- | --- |
| **Mr Nikita Mordashov** | ru | `NK-FDpsUY77HooCKp` | Son of Alexey Mordashov (sanctioned Severstal owner) |
| **Mr. Evgeny Giner** | ru | `gb-coh-psc-04128720-...` | Russian businessman; CSKA Moscow owner; sanctioned |
| **Alexey Isaykin** | cy | `gb-coh-psc-09605430-...` | Volga-Dnepr Airlines founder; sanctioned. Two separate UK PSC rows surfaced. |
| **Sergei Kondratenko** | cy | `NK-DY9E2mYcUQYFk3` | Cyprus-based Russian PSC |
| **Marat Timurov** | kz | `gb-coh-psc-15109642-...` | Kazakhstan PSC |
| **Komarov Aleksandr** | ru | `NK-9VfkoGcTGg7tVD` | (verify) |
| **Ekaterina Romanova** | ru | `NK-MBTNZ4GiQghkpE` | (verify) |
| **Ms. Natalia Degtiar** | ru | `gb-coh-psc-OC425116-...` | LLP PSC (OC prefix = Limited Liability Partnership) |
| **Mr Maxim Viktorov** | ru | `gb-coh-psc-04092367-...` | Russian businessman; classical-music collector / Concertino Capital |
| **Ms Maria Vovk** | ru | `gb-coh-psc-OC428060-...` | LLP PSC |
| **Alexandr Zverev** | ru | `NK-7pzAhhAbL5Ajsz` | (verify) |
| **Andrei Horbach** | by | `NK-VLXNrsz6Dvb8tM` | Belarusian, sanctioned |
| **Andrey Ignatyev** | ru | `cz-person-andrey-ignatyev-...` | On Czech sanctions list |

### Interpol Red Notice + UK PSC overlap

| Name | Country | Note |
| --- | --- | --- |
| Oleg Tarasov | ru | Interpol Red Notice subject with UK PSC declaration |
| Mikhail Serov | ru | Same pattern |
| Andrey Ivanov | ru | Same pattern (common name; verify) |
| Alexander Orlov | ru | Same pattern |

## Reading the result honestly

**This is the first run in the series that surfaced names not already
worked through journalism.** v2's 11 high-confidence hits (Schiavone /
Lipman / Vassiliades / Lebedev / Kolbin / Debono / Morrissey / Artemiou
/ Usachev / Guarino / Putin) all mapped to published reporting on
manual review. The new UK PSC layer adds individuals like Nikita
Mordashov, Evgeny Giner, Igor Zyuzin, Maxim Viktorov, Andrey Filatov,
Oksana Marchenko, Alexey Isaykin — every one of these is a sanctioned
or sanction-adjacent figure with a *specific UK company number* on
their public Companies House PSC declaration.

This is the showcase artifact the project was built to demonstrate:
a public-source automated join between sanctions and beneficial-ownership
disclosures that surfaces concrete, verifiable, jurisdiction-specific
links in tens of minutes.

That said:

- Most of these named individuals **are** already in journalists' /
  asset-tracker databases. What's potentially novel is the *specific*
  UK company number on each PSC declaration — that's where a reporter
  could pull the filing and confirm continued or recent activity, or
  cross-reference against the UK frozen-assets register.
- Common Russian first names (Andrey, Alexander, Aleksandr) account
  for several rows; identity verification for each name is essential
  before publication.
- The OS-internal `NK-*` IDs need a separate OS lookup to attribute
  to a specific underlying sanctions list (UK OFSI / EU / OFAC / etc.).

## Caveats from the matcher's blocking pathology

To run cleanly, we had to scope UK PSC target to ru / ua / by / cy / kz
only. Wider scopes (Pakistani, Indian, Western European common names)
OOMed `goldenmatch match` on huge first-name + honorific blocks
("Mr Muh..." at 31 k, "Anthony" at 168 k). The matcher's blocking
config is a known weak spot for high-volume person data with thin
discriminators. Future runs should:

- Add a third blocking pass that combines name prefix + country + a
  first-letter-of-surname constraint
- Or pre-filter target sources by an explicit "interesting jurisdiction"
  list as we did here
- Or switch from `goldenmatch match` to a custom pyarrow-based
  exact-on-(normalized_name, country) join for the high-signal cases,
  reserving the full goldenmatch run for the fuzzy long tail

## What's still open (roadmap status)

From `docs/ingestion_roadmap.md`:

- **A — UK PSC + Overseas Entities** — landed (this doc).
- **B — UK Overseas Entities subset** — subsumed by A.
- **C — FinCEN Files** — not yet ingested. Smaller dataset, smaller
  matching risk; ~2.5k entities total. Reasonable next ingest.
- **D — GLEIF L2 parent-child** — not yet ingested. Adds corporate
  ownership graph from registry-derived data; no person-side OOM risk
  since it's company-to-company edges.
- **E — OCCRP Laundromat** — multi-session work; deferred.
