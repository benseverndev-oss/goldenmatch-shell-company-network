# List-match v2 — OS sanctions/crime vs ICIJ officers (full 2.7 GB OS corpus)

Generated 2026-05-13. Follow-on to
`list_match_os_sanctions_vs_icij_findings.md`. Same workflow, materially
larger reference set.

> **Hypothesis, not proof.** Every match below is a name + country
> coincidence between two corpora. Confirming any one row as the *same
> individual* requires DOB / passport / address / known-filing
> verification.

## What changed from v1

After the first list-match pass (against the older OFAC SDN slice
already on the Railway volume, ~7,446 sanction/crime persons) returned
only 11 non-CN exact-name hits — all of which turned out to be
previously-reported journalism — we re-ran with the full consolidated
OpenSanctions `default` collection that we'd downloaded locally
(2.76 GB FtM JSON ingested into 1.58M rows via the schema-filtered
streaming ingest landed in PR #20).

| | v1 (small OFAC slice) | v2 (consolidated default) |
| --- | ---: | ---: |
| OS sanctioned/crime reference rows | 7,446 | **121,050** |
| ICIJ target rows | 711,079 | 711,079 |
| Total matched pairs (score ≥ 0.80) | 16,456 | **47,411** |
| Exact-normalized matches | 106 | **611** |
| Unique non-CN exact-name candidates | 11 | **132** |
| Novel (vs the 8 already-reported v1 cases) | 0 | **~128** |

## Posture on these results

The honest reading is somewhere between "validation" and "lead
generation." Most of the 132 names are still cases that already exist
on a public sanctions list AND already exist in ICIJ — what's "novel"
is that no journalist appears to have **explicitly connected** these
two facts about the same person before. That's a real category of
finding, but it's lighter-weight than uncovering a previously-unknown
identity.

A useful mental model: the matcher is doing the equivalent of a SQL
INNER JOIN on (name, country) between two public datasets. Most of
the join output is "person X was on sanctions list Y" + "person X
also incorporated company Z in BVI" — both facts public, the *join*
itself sometimes is too (journalists who covered the leak with that
country focus) and sometimes isn't. Treating any single row as
publication-grade still needs a human pass.

## Notable hits worth follow-up

The Wikidata-anchored rows are the easiest to verify because Wikidata
gives you DOB, biography, and structured cross-references. Each row
below is a unique target_normalized_name from the matched output;
score = 1.00 exact-normalized in all cases.

### Russian Federation — sanctioned high-profile

| ICIJ uid | Name | OS reference | Public context |
| --- | --- | --- | --- |
| `icij:25705` | **Alexander Abramov** | `Q4054890` | Co-founder / chairman Evraz; Russian steel billionaire; UK/EU sanctioned after 2022. ICIJ presence consistent with extensive offshore structuring. |
| `icij:240043456` | **Alexander Lebedev** | `Q370787` | Former KGB officer; banker; media mogul (Evening Standard, Independent former owner via his son); sanctioned. Well-known UK figure. |
| `icij:240100001` | **Igor Khanukovich Yusufov** | `Q4535427` | Former Russian Energy Minister (2001–2004); sanctioned. |
| `icij:240131190` | **Alexander Ionov** | `Q106913450` | US DOJ-indicted 2022 (FARA / Russian-influence operation against US activists). |
| `icij:13011888` | **Andrey Komarov** | `Q4229263` | Russian businessman, US DOJ FCPA prosecution + sanctions. |
| `icij:240132308` | **Olga Buzova** | `Q4098374` | Russian TV celebrity / pop singer; EU-sanctioned (post-2022). Surprising the matcher caught her — a celebrity sanction having an ICIJ-officer match is unusual signal. |
| `icij:12158644` | Oleg Belov | `Q4082210` | Russian businessman. |
| `icij:240053566` | Dmitry Novikov | `Q4322667` | Russian politician. |
| `icij:56056148` | Andrey Lebedev | `Q18786071` | (Different individual from Alexander Lebedev; common name.) |

### Interpol Red Notice subjects in ICIJ

Interpol's Red Notices are international wanted-person alerts. An
ICIJ officer record for someone with an active Red Notice is the
exact pattern an investigative outlet would want to surface:

| ICIJ uid | Name | Country | Red Notice |
| --- | --- | --- | --- |
| `icij:12163899` | Yusup Magomedov | ru | `interpol-red-2017-163624` |
| `icij:12146158` | Miguel Garcia | mx | `interpol-red-2012-312782` |
| `icij:80120696` | Sandeep | in | `interpol-red-2017-5499` |
| `icij:240381717` | Timur Magomadov | ru | `interpol-red-2016-38070` |
| `icij:56058008` | Maria Vorobyeva | ru | `interpol-red-2017-11188` |
| `icij:56062189` | Alexander Orlov | ru | `interpol-red-2005-32626` |
| `icij:66004338` | Harpreet Singh | in | `interpol-red-2025-6928` |
| `icij:240130978` | Aleksey Alekseev | ru | `interpol-red-2016-12655` |
| `icij:12215639` | Sergey Kovalevskiy | ru | `interpol-red-2013-58434` |
| `icij:12119345` | **Fabrice Félix Stéphane Touil** | fr | `interpol-red-2019-103493` |
| `icij:22997` | Andrey Ivanov | ru | `interpol-red-2015-37307` |

Common Slavic surnames are over-represented and not all individuals are
necessarily the same as the Red Notice subject — name collisions are
real. The French row (`Fabrice Félix Stéphane Touil`) is the kind of
name uniqueness that makes the match harder to dismiss.

### Other notable hits (national debarments, NCA, etc.)

| ICIJ uid | Name | Country | Source |
| --- | --- | --- | --- |
| `icij:240104239` | **Christodoulos Vassiliades** | cy | OS internal (NK-Xks…) — Cypriot lawyer, widely-reported Russian-money-laundering enabler |
| `icij:240130631` | Kevin Taylor | gb | UK NCA press list (`gb-nca-pr-…`) |
| `icij:13006383` | Andrey Ignatyev | ru | Czech sanctions list (`cz-person-…`) |
| `icij:240130776` | Gorbunova Olga | ru | Polish wanted list (`pl-wanted-…`) |
| `icij:28723` | Volkov Vladimir | ru | Polish wanted list |
| `icij:12208422` | Novikov Roman | ru | Polish wanted list |

### US debarment list (OCC) hits

The OS dataset includes the US OCC (Office of the Comptroller of the
Currency) banker-debarment list. These are individuals barred from
working in US banking — typically for fraud, embezzlement, or
unauthorized lending. Several ICIJ officers exact-match into this list:

- `icij:12118912 Carlos Gómez` (us)
- `icij:56076669 John Douglas` (us)
- `icij:91294 Kevin Johnson` (us)
- `icij:56010418 Robert L Jackson` (us)

These names are common enough that each row is more "interesting if
it pans out" than "almost certainly the same person."

## Caveats

- **Score 1.00 is name-match, not identity-match.** Two `Andrey Ivanov`s
  in Russia is unsurprising. Each row needs DOB / passport / known
  prior filing to confirm identity.
- **Wikidata-anchored hits are the easiest verifications** — Wikidata
  carries DOB and biography you can compare against ICIJ's
  incorporation-date / address fields.
- **OS-internal `NK-*` IDs need a separate lookup** to attribute (which
  specific list they're on). Doable but not surfaced inline by this
  pipeline.

## Reproducing

```bash
TOKEN=...; URL=https://shellnet-job-production.up.railway.app
# Make sure /data/raw/opensanctions/default.ftm.json exists (fetch via
#   POST /fetch-url?url=...&dest=raw/opensanctions/default.ftm.json )
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$URL/run-script?name=ingest_opensanctions_default_filtered"
# wait ~5 min
curl -X POST -H "Authorization: Bearer $TOKEN" "$URL/build?what=person"
# wait ~1 min
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$URL/run-script?name=list_match_os_sanctions_vs_icij"
# wait ~10 min
curl -fL -H "Authorization: Bearer $TOKEN" \
  "$URL/download?path=reports/generated/list_match_os_sanctions_vs_icij_matched.csv" \
  -o matched_v2.csv
```
