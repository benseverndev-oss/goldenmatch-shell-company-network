# List-match — OpenSanctions sanctioned/crime persons vs ICIJ officers

Generated 2026-05-13. Companion to the Epstein investigation series;
this is a separate cross-source pass that turned out to surface real
identity hypotheses.

> **Hypothesis, not proof.** Every row below is the matcher saying
> "the same string appears in two corpora with the same country tag."
> Treat as a lead requiring DOB / passport / known-filing verification
> before publication. Personal-name collisions are real and common
> (a `Zhao Wei` in ICIJ is very probably not the same `Zhao Wei` in
> a sanctions list without further evidence).

## What ran

After two attempts at full-corpus person dedupe both got stuck
(local OOM at the bearer-share block; Railway 90+ min with zero
progress output), we scope-shrank to the narrower, more
investigatively useful question: *do any sanctioned or
crime-tagged OpenSanctions Persons fuzzily match an ICIJ
officer or intermediary?*

`scripts/list_match_os_sanctions_vs_icij.py` (called via the Railway
`/run-script` endpoint, with paths persisted to the `/data` volume):

- **Reference set:** OpenSanctions Persons whose `topics` list
  contains `sanction` or `crime`. On the Railway-side OS data
  (the OFAC SDN sample currently mounted, not the 2.7 GB
  consolidated default we ingested locally) that's **7,446 persons**.
- **Target set:** every ICIJ officer + intermediary —
  **711,079 persons**.
- **Config:** `configs/goldenmatch_person.yml`
  (token-sort + jaro-winkler on name @ 0.82, country adds 0.20 weight).
- **Output:** `reports/generated/list_match_os_sanctions_vs_icij_matched.csv`
  on the Railway volume, fetched locally via the new `/download` endpoint.

Ran in ~3 minutes on the Railway shellnet-job container.

## Numbers

- **16,456** matched ICIJ↔OS person-pairs at score ≥ 0.80.
- Score distribution: 108 at 1.00, 188 at 0.95–0.99, 5,194 at 0.90–0.94,
  9,185 at 0.85–0.89, 1,781 at 0.80–0.84.
- **106** pairs are exact-normalized-name matches (`target_normalized_name
  == ref_normalized_name`) — the strongest cross-source identity signal
  in this dataset.
- Of those 106, **95 are common Chinese names** (`Zhao Wei`, `Liu Yang`,
  `Lei Zhang`, `Jian Zhang`) repeated across many ICIJ records. These
  are very probably name collisions, not the same individuals.
- **11 distinct non-CN exact matches** remain — these are the leads
  worth a human read.

## Leads worth review (non-CN exact matches)

Each row below is one ICIJ officer/intermediary record whose name and
country exactly match a sanctioned or crime-tagged OS Person. The
right-most column is the matching OpenSanctions / Wikidata identifier.

| ICIJ uid | Name | Country | OS reference | Public context |
| --- | --- | --- | --- | --- |
| `icij:56075785` | **Francesco Schiavone** | it | `opensanctions:Q1420501` | Wikidata Q1420501 → Camorra (Casalesi clan) boss known as "Sandokan", convicted of murder + organized crime. A high-confidence identity match if the ICIJ entity is the same individual. |
| `icij:240041472` | **Petr Kolbin** | ru | `opensanctions:Q112042081` | Wikidata Q112042081 → Russian businessman + sanctions target widely reported as a Putin childhood friend / front-man. |
| `icij:56047296` | **Darren Debono** | mt | `opensanctions:Q16214810` | Wikidata Q16214810 → former Maltese footballer, convicted in the Maltese fuel-smuggling case. |
| `icij:240381462` | **Gordon Debono** | mt | `opensanctions:NK-kmNC4gcozwdd4aYfhFM4BH` | Co-defendant in the same Maltese fuel-smuggling investigation as Darren Debono. |
| `icij:12150876` | **John Francis Morrissey** | es | `opensanctions:NK-3bUsZmPRPcobjc3XDHQ99h` | Spain-jurisdiction person with a sanction/crime tag in OS. Worth a follow-up on which specific OFAC / Spanish-PEP list. |
| `icij:56106432` | **Rosario Guarino** | it | `opensanctions:NK-4zfMDMrysoWxLnReM3VZat` | Italian, sanction/crime-tagged in OS. |
| `icij:240043241` | **Oleg Usachev** | ru | `opensanctions:NK-gE8KBKBpo4khTViLKFv733` | Russia-jurisdiction sanctions target. |
| `icij:13008288` | **Artemis Artemiou** | cy | `opensanctions:NK-NwJRu4P2pVozk4ajoo4AS4` | Cyprus-jurisdiction sanctions/crime tag. |

Three other non-CN exact-name matches (not shown — same shape) round
out the 11 distinct individuals.

Each of these is a *candidate* identity. ICIJ membership does not
imply wrongdoing; the matcher does not verify identity beyond name +
country. Before relying on any row, a human reviewer should pull the
ICIJ entity's full record (incorporation date, registered address,
officer/director role + dates) and cross-reference against the
sanctions filing or court record. Wikidata-anchored matches (the
two `Q*` rows) are easiest to verify; the `NK-*` rows are
OpenSanctions-internal IDs that need an OS lookup to attribute.

## Why this matters for the case study

This is the kind of cross-source signal the whole pipeline was built
to surface: take a noisy, public, identifier-free corpus (ICIJ leaks)
and intersect it with a structured, identifier-bearing corpus
(OpenSanctions sanctions/PEPs). The intersection points to entities
already in the public record where the offshore-company structure
and the sanctions/criminal posture haven't been connected by name
alone.

For the Epstein-side investigation specifically: the corpus does
**not** carry a Jeffrey Epstein OS record (verified earlier — 18
"Epstein" persons in OS, none of them him), so this pass doesn't
extend that lead. But it does demonstrate that the workflow
*works* — the Camorra / Maltese-fuel / Russian-sanctions hits are
genuine cross-source matches the matcher caught without any human
in the loop.

## Caveats

- The Railway-side OpenSanctions data is the older OFAC SDN sample
  (51 MB, ~7k sanctioned/crime persons), not the 2.7 GB
  consolidated `default` collection (121k sanctioned/crime
  persons) ingested locally. Re-running on the bigger reference
  set is expected to roughly 16× the candidate count and would
  surface many more non-trivial hits.
- The `goldenmatch_person.yml` config has known blocking issues on
  Russian patronymics (the dedupe pass that exposed this); for
  list-match the blocking pressure is much lower because the
  reference set is small (7k) — that's why this ran in 3 min when
  full dedupe ran 90+ min with no output.
- The 95 Chinese-name exact matches are not all noise — some
  fraction probably *are* the same individual — but treating them
  as identified without DOB / address corroboration is wrong.
  Filter for high-confidence name uniqueness before relying on
  this slice.

## Reproducing

```bash
# On Railway (heavy work):
curl -X POST -H "Authorization: Bearer $SHELLNET_JOB_TOKEN" \
  "$SHELLNET_JOB_URL/run-script?name=list_match_os_sanctions_vs_icij"

# Download the resulting CSV:
curl -fL -H "Authorization: Bearer $SHELLNET_JOB_TOKEN" \
  "$SHELLNET_JOB_URL/download?path=reports/generated/list_match_os_sanctions_vs_icij_matched.csv" \
  -o matched.csv
```

Locally (smaller corpus required to avoid OOM on 1.86M-row inputs):

```bash
uv run python scripts/list_match_os_sanctions_vs_icij.py
```
