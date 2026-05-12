# Investigation seed: `Butterfly Trust` / vi

Generated `2026-05-12T02:19:28+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets.

**Seed source:** NYDFS Consent Order ¶¶28–31 describes Butterfly Trust accounts in the Epstein relationship; Senate Finance 2025 list also names Butterfly Trust. Trust seed, not a company.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 3 possible outside-jurisdiction match(es) — see separate section.
- ICIJ 1-hop neighbourhood: 0 address(es), 4 officer-edge(s), 3 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 100.0 | `icij:172773` | icij | `Butterfly Limited` | ? |  |
| 2 | 100.0 | `icij:20064002` | icij | `BUTTERFLY LIMITED` | ? |  |
| 3 | 100.0 | `icij:200111378` | icij | `BUTTERFLY LIMITED` | ? |  |

## Published GoldenMatch context

_Skipped — no `DATABASE_URL` set. Set the env var to enrich with published list-match anchors, cluster memberships, and same-as pairs._
## 1-hop ICIJ neighbourhood

### `icij:172773` — 5 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:49224` | Martin Mayer | beneficial owner of | ch | Offshore Leaks |
| `icij:113638` | Directcorp Limited | director of | ? | Offshore Leaks |
| `icij:49616` | Secorp Limited | secretary of | ? | Offshore Leaks |
| `icij:84369` | Stockcorp Limited | shareholder of | ? | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:99133` |  | ? | Offshore Leaks |

### `icij:20064002` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000047` | GRAHAM COOPER | bs | Bahamas Leaks |

### `icij:200111378` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Butterfly Trust` / `vi`
- Seed normalized: `butterfly` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
