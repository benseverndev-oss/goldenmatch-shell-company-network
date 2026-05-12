# Address investigation: `Ugland House Grand Cayman` / ky

Generated `2026-05-12T04:47:50+00:00`. Address-side seed-query workflow over the unified address table.

**Seed source:** Maples & Calder mass-incorporation address — control for shared-address noise

> **Hypothesis, not proof.** Addresses are noisy; matches reflect string similarity, not verified street identity. Shared-address overlap is a *signal* worth investigating, not a finding.

## Summary

- No same-country candidates above the score threshold.
- 6 matched address row(s) → 11 distinct entity registration(s) (across 6 address group(s), 11 edge(s) total).

## Address rows (same country)

_None._

## Address rows (different / unknown country)

| # | score | exact | address_uid | source | country | raw_text |
| ---: | ---: | :-: | --- | --- | --- | --- |
| 1 | 84.7 |  | `icij:58112113#addr` | icij | ? | UGLAND HOUSE GRAND CAYMAN KY1-1104 |
| 2 | 84.7 |  | `icij:14081969#addr` | icij | ? | Ugland House; Grand Cayman; KY1-1104 |
| 3 | 79.4 |  | `icij:58119598#addr` | icij | ? | UGLAND HOUSE GRAND CAYMAN GRAND CAYMAN |
| 4 | 76.9 |  | `icij:14081968#addr` | icij | ? | Ugland House; Grand Cayman; Cayman Islands |
| 5 | 76.9 |  | `icij:58098339#addr` | icij | ? | UGLAND HOUSE, GRAND CAYMAN CAYMAN ISLANDS |
| 6 | 75.8 |  | `icij:14081967#addr` | icij | ? | Ugland House; Grand Cayman; Caymand Islands |

## Entities registered at matched addresses

### `icij:14081969#addr` — 1 entity(ies)

| entity_uid | name | jurisdiction | source |
| --- | --- | --- | --- |
| `icij:12220755` | `` | ? | icij |

### `icij:14081967#addr` — 1 entity(ies)

| entity_uid | name | jurisdiction | source |
| --- | --- | --- | --- |
| `icij:12220821` | `` | ? | icij |

### `icij:14081968#addr` — 1 entity(ies)

| entity_uid | name | jurisdiction | source |
| --- | --- | --- | --- |
| `icij:12224375` | `` | ? | icij |

### `icij:58112113#addr` — 6 entity(ies)

| entity_uid | name | jurisdiction | source |
| --- | --- | --- | --- |
| `icij:56098753` | `` | ? | icij |
| `icij:56098708` | `` | ? | icij |
| `icij:56098754` | `` | ? | icij |
| `icij:56098741` | `` | ? | icij |
| `icij:56098747` | `` | ? | icij |
| `icij:56098739` | `` | ? | icij |

### `icij:58119598#addr` — 1 entity(ies)

| entity_uid | name | jurisdiction | source |
| --- | --- | --- | --- |
| `icij:56098724` | `` | ? | icij |

### `icij:58098339#addr` — 1 entity(ies)

| entity_uid | name | jurisdiction | source |
| --- | --- | --- | --- |
| `icij:56098720` | `` | ? | icij |

## Review notes

- High shared-address concentration (11 distinct entities) — classic registered-agent / mass-incorporation pattern. Filter for jurisdictional overlap with the seed before drawing conclusions.

## Provenance

- Seed text: `Ugland House Grand Cayman`
- Seed country: `ky`
- Seed normalized: `ugland house grand cayman`
- address_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\address_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- top_n: `10`
- min_score: `75.0`
- global_fallback: `True`
