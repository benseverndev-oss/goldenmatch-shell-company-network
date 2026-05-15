# Person investigation: `Jeffrey Epstein` / us

Generated `2026-05-13T19:49:39+00:00`. Person-side seed-query workflow over the unified person table.

> **Hypothesis, not proof.** Personal names collide aggressively in the offshore-leaks corpus. A name match is a lead to verify, not a claim that the named officer is the same individual as the seed. Confirm with DOB, address, or independent filings before relying on any row below.

## Summary

- No same-country candidates above the score threshold.
- 1 candidate(s) in a different / unknown country.
- 2 person→company edge(s) across 1 matched person(s).

## Candidate persons (same country)

_None._

## Candidate persons (different / unknown country)

| # | score | exact | entity_uid | source | kind | name | country | topics |
| ---: | ---: | :-: | --- | --- | --- | --- | --- | --- |
| 1 | 93.8 |  | `icij:80063035` | icij | officer | `Epstein - Jeffrey E` | ? |  |

## Companies attached to matched persons

### `icij:80063035` — 2 edge(s)

| company_uid | name | jur | source | kind_raw | role | start | end | leak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `icij:82004676` | `Liquid Funding, Ltd.` | bm | icij | officer_of | director of | 09-NOV-2001 | 30-MAR-2007 | Paradise Papers - Appleby |
| `icij:82004676` | `Liquid Funding, Ltd.` | bm | icij | officer_of | chairman of | 09-NOV-2001 | 19-MAR-2007 | Paradise Papers - Appleby |

## Review notes

- No exact normalized-name match in the seed country. Treat all rows as fuzzy hypotheses.

## Provenance

- Seed: `Jeffrey Epstein` / `us`
- Seed normalized: `jeffrey epstein` / `us`
- person_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\person_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- top_n: `25`
- min_score: `90.0`
- global_fallback: `True`
