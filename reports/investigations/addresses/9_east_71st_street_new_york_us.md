# Address investigation: `9 East 71st Street New York` / us

Generated `2026-05-12T04:44:39+00:00`. Address-side seed-query workflow over the unified address table.

**Seed source:** 9 E 71st St — Epstein NYC townhouse per USVI SAC ¶39 (Maple, Inc.)

> **Hypothesis, not proof.** Addresses are noisy; matches reflect string similarity, not verified street identity. Shared-address overlap is a *signal* worth investigating, not a finding.

## Summary

- No same-country candidates above the score threshold.
- 2 matched address row(s) → 2 distinct entity registration(s) (across 2 address group(s), 2 edge(s) total).

## Address rows (same country)

_None._

## Address rows (different / unknown country)

| # | score | exact | address_uid | source | country | raw_text |
| ---: | ---: | :-: | --- | --- | --- | --- |
| 1 | 85.2 |  | `icij:58055073#addr` | icij | ? | 9 EAST 62ND STREET, NEW YORK |
| 2 | 82.8 |  | `icij:58013934#addr` | icij | ? | 27, EAST 95TH STREET, NEW YORK #4W |

## Entities registered at matched addresses

### `icij:58055073#addr` — 1 entity(ies)

| entity_uid | name | jurisdiction | source |
| --- | --- | --- | --- |
| `icij:56099908` | `` | ? | icij |

### `icij:58013934#addr` — 1 entity(ies)

| entity_uid | name | jurisdiction | source |
| --- | --- | --- | --- |
| `icij:56060345` | `` | ? | icij |

## Review notes

- 2 entity(ies) found. Review each registration to confirm the address is genuinely the same physical location.

## Provenance

- Seed text: `9 East 71st Street New York`
- Seed country: `us`
- Seed normalized: `9 east 71st street new york`
- address_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\address_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- top_n: `25`
- min_score: `80.0`
- global_fallback: `True`
