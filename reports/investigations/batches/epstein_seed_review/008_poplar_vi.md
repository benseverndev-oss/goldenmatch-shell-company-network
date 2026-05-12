# Investigation seed: `Poplar, Inc.` / vi

Generated `2026-05-12T13:49:53+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets + published GoldenMatch context.

**Seed source:** USVI Second Amended Complaint ST-20-CV-14 ¶¶30–32: VI corporation; Epstein listed as president/director; filings tied it to Great St. Jim, LLC/Great St. James.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 5 possible outside-jurisdiction match(es) — see separate section.
- Cluster membership: [33609, 180553, 624864, 628716, 758210] (from dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`).
- ICIJ 1-hop neighbourhood: 1 address(es), 0 officer-edge(s), 4 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 100.0 | `icij:10034018` | icij | `POPLAR CORPORATION` | ? |  |
| 2 | 100.0 | `icij:10182128` | icij | `POPLAR S.A.` | ? |  |
| 3 | 100.0 | `icij:55058380` | icij | `POPLAR LTD` | mt |  |
| 4 | 92.3 | `icij:200112405` | icij | `POPULAR S.A.` | ? |  |
| 5 | 90.9 | `icij:200108446` | icij | `POLAR CORP.` | ? |  |

## Published GoldenMatch context

### Cluster membership

From dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`.

| entity_uid | cluster_id |
| --- | ---: |
| `icij:10182128` | 180553 |
| `icij:55058380` | 758210 |
| `icij:200108446` | 624864 |
| `icij:200112405` | 628716 |
| `icij:10034018` | 33609 |

## 1-hop ICIJ neighbourhood

### `icij:10034018` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11011863` | MOSSACK FONSECA & CO. | pa | Panama Papers |

### `icij:10182128` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11003262` | CAPITA FIDUCIARY (LUXEMBOURG) | lu | Panama Papers |

### `icij:55058380` — 1 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:58025138` | 248 ST. PAUL'S STR, VALLETTA, MALTA | ? | Paradise Papers - Malta corporate registry |  |  |

### `icij:200112405` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

### `icij:200108446` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Poplar, Inc.` / `vi`
- Seed normalized: `poplar` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
- GoldenMatch dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
- GoldenMatch list-match run: `a01cce05-896b-4d19-911c-b3efe7b5f56f`
