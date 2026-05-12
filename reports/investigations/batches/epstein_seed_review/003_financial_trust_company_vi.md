# Investigation seed: `Financial Trust Company, Inc.` / vi

Generated `2026-05-12T02:18:45+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets.

**Seed source:** USVI/JPMorgan litigation materials and Senate/DOJ-related lists identify Financial Trust Company, Inc. as an Epstein-related entity/account holder. Use as a seed, not as a conclusion.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 6 possible outside-jurisdiction match(es) — see separate section.
- ICIJ 1-hop neighbourhood: 5 address(es), 11 officer-edge(s), 6 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 89.8 | `icij:202777` | icij | `TREMASET FINANCIAL COMPANY LTD.` | ? |  |
| 2 | 87.5 | `icij:226181` | icij | `Financial Company RINKOST Ltd` | ? |  |
| 3 | 85.1 | `icij:10021311` | icij | `PROTON FINANCIAL COMPANY LTD.` | ? |  |
| 4 | 85.1 | `icij:10023453` | icij | `PROTON FINANCIAL COMPANY LTD.` | ? |  |
| 5 | 85.1 | `icij:194282` | icij | `KELART FINANCIAL COMPANY INC.` | ? |  |
| 6 | 85.1 | `icij:232902` | icij | `STENFO FINANCIAL COMPANY LTD.` | ? |  |

## Published GoldenMatch context

_Skipped — no `DATABASE_URL` set. Set the env var to enrich with published list-match anchors, cluster memberships, and same-as pairs._
## 1-hop ICIJ neighbourhood

### `icij:202777` — 8 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:288469` | Unitrust Corporate Services Ltd. John Humphries House, Room 304 4-10 Stockwell S | gb | Offshore Leaks |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:24108` | Diagoras Nominees Limited | shareholder of | cy | Offshore Leaks |
| `icij:20642` | Standard Directors Ltd. | director of | ? | Offshore Leaks |
| `icij:27078` | Natalie Gureghian | director of | cy | Offshore Leaks |
| `icij:27079` | Stella Chrysostomou | director of | cy | Offshore Leaks |
| `icij:27081` | Bohemia Business, Corp. | shareholder of | vg | Offshore Leaks |
| `icij:27080` | Alexander Provotorov | director of | ru | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:298333` | Unitrust Corporate Services Ltd. | gb | Offshore Leaks |

### `icij:226181` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:237583` | G.S.L. Law & Consulting SHIPPING ADDRESS: Russian Federation Billing/Invoice add | ru | Offshore Leaks |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:20828` | Mr. Damian Calderbank | director of | ae | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:298170` | G.S.L. Law & Consulting | cy | Offshore Leaks |

### `icij:10021311` — 4 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:12159875` | WINFRIED KÖLLMANN | shareholder of | de | Panama Papers |
| `icij:12159876` | THE BEARER | shareholder of | de | Panama Papers |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11012290` | MOSSFON MANAGERS LTD. | bs | Panama Papers |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:10023453` | PROTON FINANCIAL COMPANY LTD. | same_as | same name and registration date as |  |

### `icij:10023453` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:14104759` | PROTON FINANCIAL COMPANY LTD. SUITE 13; FIRST FLOOR OLIAJI TRADE CENTRE FRANCIS  | ? | Panama Papers |  |  |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11003356` | WINFRIED KOELLMANN | ? | Panama Papers |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:10021311` | PROTON FINANCIAL COMPANY LTD. | same_as | same name and registration date as |  |

### `icij:194282` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:288469` | Unitrust Corporate Services Ltd. John Humphries House, Room 304 4-10 Stockwell S | gb | Offshore Leaks |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:24619` | Standad Directors Ltd. | director of | ? | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:298333` | Unitrust Corporate Services Ltd. | gb | Offshore Leaks |

### `icij:232902` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:288469` | Unitrust Corporate Services Ltd. John Humphries House, Room 304 4-10 Stockwell S | gb | Offshore Leaks |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:20642` | Standard Directors Ltd. | director of | ? | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:298333` | Unitrust Corporate Services Ltd. | gb | Offshore Leaks |

## Cross-candidate overlap

**Addresses shared across candidates**

| address | shared by |
| --- | --- |
| Unitrust Corporate Services Ltd. John Humphries House, Room 304 4-10 Stockwell S | icij:194282, icij:202777, icij:232902 |

**Officers shared across candidates**

| name | shared by |
| --- | --- |
| Standard Directors Ltd. | icij:202777, icij:232902 |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Financial Trust Company, Inc.` / `vi`
- Seed normalized: `financial trust company` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
