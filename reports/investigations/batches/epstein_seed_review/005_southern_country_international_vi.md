# Investigation seed: `Southern Country International Ltd.` / vi

Generated `2026-05-12T02:18:49+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets.

**Seed source:** USVI/estate litigation materials describe Epstein-owned Southern Country International, Ltd. and questioned estate transfers involving the entity.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 6 possible outside-jurisdiction match(es) — see separate section.
- ICIJ 1-hop neighbourhood: 1 address(es), 1 officer-edge(s), 6 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 91.2 | `icij:201178` | icij | `Super Country International Limited` | ? |  |
| 2 | 86.2 | `icij:20057704` | icij | `SOUTHERN CROSS INTERNATIONAL LIMITED` | ? |  |
| 3 | 86.2 | `icij:20104013` | icij | `COUNTRY SQUIRE INTERNATIONAL CORPORATION` | ? |  |
| 4 | 86.2 | `icij:20105039` | icij | `SOUTHERN CROSS INTERNATIONAL LTD.` | ? |  |
| 5 | 86.2 | `icij:200102547` | icij | `SOUTHERN CROSS INTERNATIONAL LTD.` | ? |  |
| 6 | 85.7 | `icij:20123926` | icij | `COUNTRY TIME INTERNATIONAL LTD.` | ? |  |

## Published GoldenMatch context

_Skipped — no `DATABASE_URL` set. Set the env var to enrich with published list-match anchors, cluster memberships, and same-as pairs._
## 1-hop ICIJ neighbourhood

### `icij:201178` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:264051` | Company Kit Limited Unit A, 6/F Shun On Comm Bldg. 112-114 Des Voeux Road C., Ho | hk | Offshore Leaks |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:20643` | Company Kit Nominees Inc. | director of | hk | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:297687` | Company Kit Limited | hk | Offshore Leaks |

### `icij:20057704` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000280` | PRIVATE TRUST CORPORATION LIMITED | bs | Bahamas Leaks |

### `icij:20104013` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000237` | LEX MANAGEMENT LIMITED | bs | Bahamas Leaks |

### `icij:20105039` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000100` | ARNOLD A. FORBES & CO. | bs | Bahamas Leaks |

### `icij:200102547` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

### `icij:20123926` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000362` | CITITRUST (BAHAMAS) LIMITED | bs | Bahamas Leaks |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Southern Country International Ltd.` / `vi`
- Seed normalized: `southern country international` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
