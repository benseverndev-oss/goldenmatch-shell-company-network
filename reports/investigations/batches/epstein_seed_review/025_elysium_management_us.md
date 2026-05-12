# Investigation seed: `Elysium Management, LLC` / us

Generated `2026-05-12T02:19:40+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets.

**Seed source:** Senate Finance 2025 list names Elysium Management, LLC. Broader seed pending review.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 8 possible outside-jurisdiction match(es) — see separate section.
- ICIJ 1-hop neighbourhood: 1 address(es), 13 officer-edge(s), 7 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 100.0 | `icij:20151599` | icij | `Elysium Management Limited` | ? |  |
| 2 | 88.9 | `icij:20174886` | icij | `ALYSSUM MANAGEMENT LIMITED` | ? |  |
| 3 | 87.5 | `icij:55071555` | icij | `EIM MANAGEMENT LIMITED` | mt |  |
| 4 | 86.5 | `icij:20129433` | icij | `DELIRIUM MANAGEMENT LIMITED` | ? |  |
| 5 | 85.7 | `icij:10025363` | icij | `KELLUM MANAGEMENT S.A.` | ? |  |
| 6 | 85.7 | `icij:10110753` | icij | `JETSUM MANAGEMENT LIMITED` | vg |  |
| 7 | 85.7 | `icij:10213301` | icij | `KELSIE MANAGEMENT LIMITED` | ? |  |
| 8 | 85.7 | `icij:20043405` | icij | `KELSIE MANAGEMENT LIMITED` | ? |  |

## Published GoldenMatch context

_Skipped — no `DATABASE_URL` set. Set the env var to enrich with published list-match anchors, cluster memberships, and same-as pairs._
## 1-hop ICIJ neighbourhood

### `icij:20151599` — 3 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:22014692` | DIRMAC LIMITED | director | ? | Bahamas Leaks |
| `icij:22017710` | NOMARK LIMITED | director | ? | Bahamas Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000523` | JULIUS BAER TRUST COMPANY (BAHAMAS) LTD | bs | Bahamas Leaks |

### `icij:20174886` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000458` | GENESIS FUND SERVICES LIMITED | bs | Bahamas Leaks |

### `icij:55071555` — 6 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:58078879` | MED ISLE BUSINESS CENTRE TRIQ CENSU FARRUGIA, MSIDA, MALTA | ? | Paradise Papers - Malta corporate registry |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:56074556` | MAURO SALCINI | legal representative of | it | Paradise Papers - Malta corporate registry |
| `icij:56074556` | MAURO SALCINI | judicial representative of | it | Paradise Papers - Malta corporate registry |
| `icij:56074556` | MAURO SALCINI | secretary of | it | Paradise Papers - Malta corporate registry |
| `icij:56074556` | MAURO SALCINI | shareholder of | it | Paradise Papers - Malta corporate registry |
| `icij:56074556` | MAURO SALCINI | director of | it | Paradise Papers - Malta corporate registry |

### `icij:20129433` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000330` | CREDIT SUISSE TRUST LIMITED | bs | Bahamas Leaks |

### `icij:10025363` — 4 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:12175289` | TELESTO S.A. | shareholder of | ? | Panama Papers |
| `icij:12118992` | THE BEARER | shareholder of | cy | Panama Papers |
| `icij:12118995` | THE BEARER | shareholder of | cy | Panama Papers |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11007867` | LINXX SERVICES (CYPRUS) LIMITED | cy | Panama Papers |

### `icij:10110753` — 4 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:12084895` | GALLIARD HOMES LIMITED | shareholder of | ? | Panama Papers |
| `icij:12084895` | GALLIARD HOMES LIMITED | shareholder of | ? | Panama Papers |
| `icij:12163057` | FIDECS TRUST COMPANY LIMITED | shareholder of | gi | Panama Papers |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11010693` | STM FIDECS MANAGEMENT LTD. | gi | Panama Papers |

### `icij:10213301` — 2 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11007078` | ILS FIDUCIARIES (IOM) LIMITED | im | Panama Papers |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:20043405` | KELSIE MANAGEMENT LIMITED | same_company_as | same company as | Bahamas Leaks |

### `icij:20043405` — 2 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000136` | MOSSACK FONSECA & CO. (BAHAMAS) LIMITED | bs | Bahamas Leaks |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:10213301` | KELSIE MANAGEMENT LIMITED | same_company_as | same company as | Bahamas Leaks |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Elysium Management, LLC` / `us`
- Seed normalized: `elysium management` / `us`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
