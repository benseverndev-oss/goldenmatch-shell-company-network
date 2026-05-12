# Investigation seed: `Elysium Trust` / vi

Generated `2026-05-12T13:51:02+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets + published GoldenMatch context.

**Seed source:** Senate Finance 2025 list names Elysium Trust. Trust seed, not a company.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 4 possible outside-jurisdiction match(es) — see separate section.
- Cluster membership: [233636, 414486, 587446, 758552] (from dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`).
- ICIJ 1-hop neighbourhood: 3 address(es), 10 officer-edge(s), 2 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 100.0 | `icij:144305` | icij | `Elysium Ltd` | vg |  |
| 2 | 100.0 | `icij:20115960` | icij | `ELYSIUM LIMITED` | ? |  |
| 3 | 100.0 | `icij:55058733` | icij | `ELYSIUM LTD` | mt |  |
| 4 | 85.7 | `icij:100322143` | icij | `ELYSEUM INC.` | ? |  |

## Published GoldenMatch context

### Cluster membership

From dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`.

| entity_uid | cluster_id |
| --- | ---: |
| `icij:100322143` | 587446 |
| `icij:144305` | 233636 |
| `icij:55058733` | 758552 |
| `icij:20115960` | 414486 |

## 1-hop ICIJ neighbourhood

### `icij:144305` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:236724` | Portcullis TrustNet Chambers P.O. Box 3444 Road Town, Tortola British Virgin Isl | vg | Offshore Leaks |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:54662` | Portcullis TrustNet (BVI) Limited | records & registers of | ? | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:296840` | Valerie Roma Cary | sg | Offshore Leaks |

### `icij:20115960` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000438` | BUTTERFIELD TRUST (BAHAMAS) LIMITED | bs | Bahamas Leaks |

### `icij:55058733` — 8 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:58104017` | VILLA GAUCI MDINA ROAD, BALZANBZN9031, MALTA | ? | Paradise Papers - Malta corporate registry |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:56106047` | GIANCARLO TRAVAGIN | director of | it | Paradise Papers - Malta corporate registry |
| `icij:56106047` | GIANCARLO TRAVAGIN | legal representative of | it | Paradise Papers - Malta corporate registry |
| `icij:56106047` | GIANCARLO TRAVAGIN | secretary of | it | Paradise Papers - Malta corporate registry |
| `icij:56106047` | GIANCARLO TRAVAGIN | judicial representative of | it | Paradise Papers - Malta corporate registry |
| `icij:56106047` | GIANCARLO TRAVAGIN | shareholder of | it | Paradise Papers - Malta corporate registry |
| `icij:56070765` | STEFANO TACCONI | shareholder of | it | Paradise Papers - Malta corporate registry |
| `icij:56070765` | STEFANO TACCONI | director of | it | Paradise Papers - Malta corporate registry |

### `icij:100322143` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:120016084` | #22 4TH AVENUE, VALLEY VIEW, ST. GEORGE, BARBADOS. | ? |  |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:110002563` | HANSSON ANITA M | director of | ? |  |
| `icij:110057108` | MARVILLE RASHID O | director of | ? |  |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Elysium Trust` / `vi`
- Seed normalized: `elysium` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
- GoldenMatch dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
- GoldenMatch list-match run: `a01cce05-896b-4d19-911c-b3efe7b5f56f`
