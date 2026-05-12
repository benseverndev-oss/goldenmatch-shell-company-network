# Investigation seed: `Southern Trust Company, Inc.` / vi

Generated `2026-05-12T13:49:09+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets + published GoldenMatch context.

**Seed source:** USVI Second Amended Complaint ST-20-CV-14 ¶37: VI company originally incorporated as Financial Informatics, Inc.; Epstein described as President/Director and sole owner. Also NYDFS Consent Order ¶24 references brokerage account.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 5 possible outside-jurisdiction match(es) — see separate section.
- Cluster membership: [334464, 512543, 652390, 740558] (from dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`).
- ICIJ 1-hop neighbourhood: 3 address(es), 6 officer-edge(s), 2 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 88.4 | `icij:20014355` | icij | `SOUTHERN STAR COMPANY LIMITED` | ? |  |
| 2 | 87.2 | `opensanctions:bic-TRCUAU21` | opensanctions | `THE TRUST COMPANY LIMITED` | au |  |
| 3 | 86.4 | `icij:55039844` | icij | `SOUTHERN STYLE COMPANY LIMITED` | mt |  |
| 4 | 86.3 | `icij:82126802` | icij | `Southern Global Trust Company Ltd` | mu |  |
| 5 | 85.7 | `icij:200136528` | icij | `Fisher Trust Company Inc.` | ? |  |

## Published GoldenMatch context

### Cluster membership

From dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`.

| entity_uid | cluster_id |
| --- | ---: |
| `icij:200136528` | 652390 |
| `icij:20014355` | 334464 |
| `icij:82126802` | 512543 |
| `icij:55039844` | 740558 |

## 1-hop ICIJ neighbourhood

### `icij:20014355` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000388` | EURO CANADIAN TRUST COMPANY | bs | Bahamas Leaks |

### `icij:55039844` — 7 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:58135404` | IRIS, TRIQ IL-KANONKU BONNICI, HAMRUNHMR 2160, MALTA | ? | Paradise Papers - Malta corporate registry |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:56023816` | CHRISTOPHER BALDACCHINO | auditor of | mt | Paradise Papers - Malta corporate registry |
| `icij:56028451` | CLAYTON GALEA | director of | mt | Paradise Papers - Malta corporate registry |
| `icij:56028451` | CLAYTON GALEA | legal representative of | mt | Paradise Papers - Malta corporate registry |
| `icij:56028451` | CLAYTON GALEA | judicial representative of | mt | Paradise Papers - Malta corporate registry |
| `icij:56028451` | CLAYTON GALEA | secretary of | mt | Paradise Papers - Malta corporate registry |
| `icij:56028451` | CLAYTON GALEA | shareholder of | mt | Paradise Papers - Malta corporate registry |

### `icij:82126802` — 2 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:81000438` | 8th Floor Medine Mews | ? | Paradise Papers - Appleby |  |  |
| `icij:81000379` | C/o Corporate & Chancery Chambers, 2nd Floor, Barkly Wharf, Le Caudan Waterfront | ? | Paradise Papers - Appleby |  |  |

### `icij:200136528` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Southern Trust Company, Inc.` / `vi`
- Seed normalized: `southern trust company` / `vi`
- Sources present in candidate pool: icij, opensanctions
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
- GoldenMatch dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
- GoldenMatch list-match run: `a01cce05-896b-4d19-911c-b3efe7b5f56f`
