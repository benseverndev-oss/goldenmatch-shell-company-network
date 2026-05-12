# Person investigation: `Jeffrey Epstein` / (unspecified)

Generated `2026-05-12T04:43:20+00:00`. Person-side seed-query workflow over the unified person table.

**Seed source:** USVI/JPMorgan/Senate Finance public reporting — see seeds/epstein_entities.csv for entity-level provenance

> **Hypothesis, not proof.** Personal names collide aggressively in the offshore-leaks corpus. A name match is a lead to verify, not a claim that the named officer is the same individual as the seed. Confirm with DOB, address, or independent filings before relying on any row below.

## Summary

- Best in-country candidate: `icij:80063035` (`Epstein - Jeffrey E`, ?, score 93.8, kind=officer)
- 8 person→company edge(s) across 4 matched person(s).

## Candidate persons (same country)

| # | score | exact | entity_uid | source | kind | name | country | topics |
| ---: | ---: | :-: | --- | --- | --- | --- | --- | --- |
| 1 | 93.8 |  | `icij:80063035` | icij | officer | `Epstein - Jeffrey E` | ? |  |
| 2 | 82.4 |  | `icij:110112161` | icij | officer | `BLEUSTEIN JEFFREY L.` | ? |  |
| 3 | 81.2 |  | `icij:110116466` | icij | officer | `GOLDSTEIN JEFFREY` | ? |  |
| 4 | 80.0 |  | `icij:80071982` | icij | officer | `Greenstein - Jeffrey H` | us |  |

## Companies attached to matched persons

### `icij:80063035` — 2 edge(s)

| company_uid | name | jur | source | kind_raw | role | start | end | leak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `icij:82004676` | `Liquid Funding, Ltd.` | bm | icij | officer_of | director of | 09-NOV-2001 | 30-MAR-2007 | Paradise Papers - Appleby |
| `icij:82004676` | `Liquid Funding, Ltd.` | bm | icij | officer_of | chairman of | 09-NOV-2001 | 19-MAR-2007 | Paradise Papers - Appleby |

### `icij:110112161` — 1 edge(s)

| company_uid | name | jur | source | kind_raw | role | start | end | leak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `icij:101504681` | `HARLEY-DAVIDSON FOREIGN SALES CORPORATION` | ? | icij | officer_of | director of | 01-OCT-1997 |  |  |

### `icij:110116466` — 1 edge(s)

| company_uid | name | jur | source | kind_raw | role | start | end | leak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `icij:101514922` | `RG/G FSC, INC.` | ? | icij | officer_of | director of | 30-JAN-1998 |  |  |

### `icij:80071982` — 4 edge(s)

| company_uid | name | jur | source | kind_raw | role | start | end | leak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `icij:82006001` | `IXI Bicycle Company Ltd.` | bm | icij | officer_of | vice-president of | 19-NOV-2003 | 16-FEB-2010 | Paradise Papers - Appleby |
| `icij:82006001` | `IXI Bicycle Company Ltd.` | bm | icij | officer_of | director of | 31-OCT-2003 | 16-FEB-2010 | Paradise Papers - Appleby |
| `icij:82006001` | `IXI Bicycle Company Ltd.` | bm | icij | officer_of | shareholder of |  |  | Paradise Papers - Appleby |
| `icij:82006001` | `IXI Bicycle Company Ltd.` | bm | icij | officer_of | is signatory for |  |  | Paradise Papers - Appleby |

## Review notes

- No exact normalized-name match in the seed country. Treat all rows as fuzzy hypotheses.

## Provenance

- Seed: `Jeffrey Epstein` / `?`
- Seed normalized: `jeffrey epstein` / `?`
- person_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\person_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- top_n: `50`
- min_score: `80.0`
- global_fallback: `True`
