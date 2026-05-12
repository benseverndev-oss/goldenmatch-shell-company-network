# Investigation seed: `Southern Financial LLC` / vi

Generated `2026-05-12T02:18:40+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets.

**Seed source:** NYDFS Consent Order ¶24: Southern Financial LLC described as wholly owned subsidiary of Southern Trust Company Inc. and one of the Deutsche Bank brokerage-account entities; Senate Finance 2025 list also names it.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 8 possible outside-jurisdiction match(es) — see separate section.
- ICIJ 1-hop neighbourhood: 2 address(es), 12 officer-edge(s), 6 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 100.0 | `icij:10194636` | icij | `SOUTHERN FINANCIAL CORP.` | vg |  |
| 2 | 88.9 | `icij:200515085` | icij | `Northern Financial, LLC` | ? |  |
| 3 | 88.2 | `icij:10168547` | icij | `SOUTHERN FINANCE INC.` | ? |  |
| 4 | 88.2 | `icij:240020680` | icij | `SHERON FINANCIAL CORP.` | vg |  |
| 5 | 86.5 | `icij:200102748` | icij | `SOUTHWEST FINANCIAL CORPORATION` | ? |  |
| 6 | 85.7 | `icij:10020268` | icij | `WESTERN FINANCIAL LTD.` | ? |  |
| 7 | 85.7 | `icij:10022781` | icij | `SORTENY FINANCIAL LTD.` | ? |  |
| 8 | 85.7 | `icij:55041638` | icij | `WESTERN FINANCIAL LIMITED` | mt |  |

## Published GoldenMatch context

_Skipped — no `DATABASE_URL` set. Set the env var to enrich with published list-match anchors, cluster memberships, and same-as pairs._
## 1-hop ICIJ neighbourhood

### `icij:10194636` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11007372` | MOSSACK FONSECA & CO. (GENEVA) S.A. | ch | Panama Papers |

### `icij:200515085` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

### `icij:10168547` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11007372` | MOSSACK FONSECA & CO. (GENEVA) S.A. | ch | Panama Papers |

### `icij:240020680` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:240000001` | 3rd Floor, Yamraj Building, Market Square, P.O. Box 3175 Road Town, Tortola Brit | vg |  |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:240040933` | CARLO FEDERICO BURÀ | Ultimate Beneficial Owner | ch |  |
| `icij:240045059` | CARLOS BURA | Ultimate Beneficial Owner | ch |  |

### `icij:200102748` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

### `icij:10020268` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11011729` | CLAMORGAN S.A. | ? | Panama Papers |

### `icij:10022781` — 4 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:12087133` | Lucy Margaret CLARKE | shareholder of | ? | Panama Papers |
| `icij:12220615` | THE BEARER | shareholder of | pa | Panama Papers |
| `icij:12220616` | THE BEARER | shareholder of | pa | Panama Papers |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11000574` | IGMASA MANAGEMENT | ad | Panama Papers |

### `icij:55041638` — 8 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:58080629` | NO 116/8, 'SAN JUAN', ST. GEORGE'S ROAD, ST. JULIANSSTJ 3203, MALTA | ? | Paradise Papers - Malta corporate registry |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:56082891` | RES MALTA LIMITED | director of | mt | Paradise Papers - Malta corporate registry |
| `icij:56082891` | RES MALTA LIMITED | legal representative of | mt | Paradise Papers - Malta corporate registry |
| `icij:56023645` | KENNETH A. MiCALLEF | auditor of | mt | Paradise Papers - Malta corporate registry |
| `icij:56082891` | RES MALTA LIMITED | judicial representative of | mt | Paradise Papers - Malta corporate registry |
| `icij:56032560` | CHRISTIAN ELLUL | secretary of | mt | Paradise Papers - Malta corporate registry |
| `icij:56083931` | SOLV INTERNATIONAL LTD. | shareholder of | mt | Paradise Papers - Malta corporate registry |
| `icij:56083577` | E & S CONSULTANCY LIMITED | shareholder of | mt | Paradise Papers - Malta corporate registry |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Southern Financial LLC` / `vi`
- Seed normalized: `southern financial` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
