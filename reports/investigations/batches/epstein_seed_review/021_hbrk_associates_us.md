# Investigation seed: `HBRK Associates, Inc.` / us

Generated `2026-05-12T13:50:42+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets + published GoldenMatch context.

**Seed source:** USVI/JPMorgan litigation cash-flow table lists HBRK Associates, Inc. as an account holder associated with Epstein-related accounts. Include as broader seed pending review.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- Best local candidate: `opensanctions:bic-ASOTUS61` (`KA ASSOCIATES, INC`, us, score 85.7)
- 25 possible outside-jurisdiction match(es) — see separate section.
- Cluster membership: [2338, 22040, 43920, 56063, 59457, 66030, 100356, 106166, 116347, 119661, 121653, 124106, 150656, 208358, 211587, 231437, 370797, 383366, 385353, 576629, 579218, 641657, 655366, 676681, 692945] (from dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`).
- ICIJ 1-hop neighbourhood: 6 address(es), 15 officer-edge(s), 22 intermediary-edge(s).

## Candidate records (same jurisdiction)

| # | score | exact | entity_uid | source | name | jurisdiction | lei | company_number |
| ---: | ---: | :-: | --- | --- | --- | --- | --- | --- |
| 1 | 85.7 |  | `opensanctions:bic-ASOTUS61` | opensanctions | `KA ASSOCIATES, INC` | us |  | ASOTUS61 |

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 93.3 | `icij:20068259` | icij | `BRKG ASSOCIATES LTD.` | ? |  |
| 2 | 92.9 | `icij:20053239` | icij | `HR ASSOCIATES INC.` | ? |  |
| 3 | 89.7 | `icij:10022362` | icij | `RJK ASSOCIATES CORP.` | ? |  |
| 4 | 89.7 | `icij:100300396` | icij | `B.M.R. ASSOCIATES LIMITED` | ? |  |
| 5 | 89.7 | `icij:100303662` | icij | `B & R ASSOCIATES LIMITED` | ? |  |
| 6 | 89.7 | `icij:200125653` | icij | `HUB ASSOCIATES INC.` | ? |  |
| 7 | 89.7 | `icij:200139535` | icij | `HRD ASSOCIATES LTD.` | ? |  |
| 8 | 89.7 | `icij:240022221` | icij | `BBK ASSOCIATES LTD` | vg |  |
| 9 | 87.5 | `icij:10099374` | icij | `BURKET ASSOCIATES LTD.` | vg |  |
| 10 | 87.5 | `icij:10123282` | icij | `BURKEM ASSOCIATES S.A.` | ? |  |
| 11 | 87.5 | `icij:20073411` | icij | `BROKER ASSOCIATES INC.` | ? |  |
| 12 | 86.7 | `icij:10058532` | icij | `BARI ASSOCIATES S.A.` | ? |  |
| 13 | 86.7 | `icij:10066084` | icij | `REKO ASSOCIATES LIMITED` | vg |  |
| 14 | 86.7 | `icij:10105151` | icij | `THOR ASSOCIATES S.A.` | vg |  |
| 15 | 86.7 | `icij:10150576` | icij | `LARK Associates Limited` | vg |  |
| 16 | 86.7 | `icij:10210254` | icij | `YORK ASSOCIATES INC.` | ? |  |
| 17 | 86.7 | `icij:200513491` | icij | `Trak Associates LLC` | ? |  |
| 18 | 85.7 | `icij:10002359` | icij | `NB ASSOCIATES S.A.` | ? |  |
| 19 | 85.7 | `icij:10044455` | icij | `KV ASSOCIATES S.A.` | ? |  |
| 20 | 85.7 | `icij:10059914` | icij | `CK & ASSOCIATES INC.` | vg |  |
| 21 | 85.7 | `icij:10115343` | icij | `BH Associates Ltd.` | vg |  |
| 22 | 85.7 | `icij:10118710` | icij | `BH Associates Ltd.` | vg |  |
| 23 | 85.7 | `icij:10120767` | icij | `KV ASSOCIATES S.A.` | vg |  |
| 24 | 85.7 | `icij:10213513` | icij | `G.R. ASSOCIATES LIMITED` | ? |  |
| 25 | 85.7 | `icij:145750` | icij | `RJ ASSOCIATES LTD.` | vg |  |

## Published GoldenMatch context

### Cluster membership

From dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`.

| entity_uid | cluster_id |
| --- | ---: |
| `icij:10002359` | 2338 |
| `icij:10022362` | 22040 |
| `icij:10044455` | 43920 |
| `icij:10059914` | 59457 |
| `icij:10099374` | 100356 |
| `icij:10213513` | 211587 |
| `icij:145750` | 231437 |
| `icij:20053239` | 370797 |
| `icij:100303662` | 579218 |
| `icij:200139535` | 655366 |
| `icij:10058532` | 56063 |
| `icij:10105151` | 106166 |
| `icij:10115343` | 116347 |
| `icij:20068259` | 383366 |
| `icij:200513491` | 676681 |
| `icij:10066084` | 66030 |
| `icij:10118710` | 119661 |
| `icij:10120767` | 121653 |
| `icij:10123282` | 124106 |
| `icij:10150576` | 150656 |
| `icij:10210254` | 208358 |
| `icij:20073411` | 385353 |
| `icij:100300396` | 576629 |
| `icij:200125653` | 641657 |
| `icij:240022221` | 692945 |

## 1-hop ICIJ neighbourhood

### `icij:20068259` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000436` | UNIVERSAL LEGAL SERVICES | bs | Bahamas Leaks |

### `icij:20053239` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000260` | HARRY B. SANDS, LOBOSKY | bs | Bahamas Leaks |

### `icij:10022362` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11012037` | PRIME CORPORATE SOLUTIONS SARL | lu | Panama Papers |

### `icij:100300396` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:120010733` | ANMARA, OLD QUEEN'S FORT, ST. JAMES, BARBADOS. | ? |  |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:110059247` | PETERS DR. MONICA E. | director of | ? |  |
| `icij:110124216` | PETERS DR. BEVIS F. | director of | ? |  |

### `icij:100303662` — 4 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:120005494` | C/O ALLEYNE & ALLEYNE, ALLEYNE HOUSE, WHITE PARK ROAD, ST. MICHAEL. BARBADOS | ? |  |  |  |
| `icij:120016932` | C/O ALLIN ENTERPRISES "THE OLIVES", COLLYMORE ROCK ST. MICHAEL, BARBADOS | ? |  |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:110073910` | REIFER META ISAIDORE | director of | ? |  |
| `icij:110122699` | REIFER GEORGE | director of | ? |  |

### `icij:200125653` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

### `icij:200139535` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000005` | Associated Trustees Limited | ? |  |

### `icij:240022221` — 2 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:240000001` | 3rd Floor, Yamraj Building, Market Square, P.O. Box 3175 Road Town, Tortola Brit | vg |  |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:240042795` | REBECCA SAMANTHA VIANA JAOUI | Ultimate Beneficial Owner | ? |  |

### `icij:10099374` — 2 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:12002895` | THE BEARER | shareholder of | ? | Panama Papers |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11003818` | (GVA) FIGESTOR S.A. | ch | Panama Papers |

### `icij:10123282` — 2 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:12005638` | THE BEARER | shareholder of | ? | Panama Papers |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11012567` | BKF BEKER FINANCE SA | ch | Panama Papers |

### `icij:20073411` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000377` | OFFSHORE MANAGERS LIMITED | bs | Bahamas Leaks |

### `icij:10058532` — 5 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:12018913` | THE BEARER | shareholder of | ? | Panama Papers |
| `icij:12019804` | THE BEARER | shareholder of | ? | Panama Papers |
| `icij:12019805` | THE BEARER | shareholder of | ? | Panama Papers |
| `icij:12019806` | THE BEARER | shareholder of | ? | Panama Papers |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11002931` | SG TRUST (SWITZERLAND) SA | ch | Panama Papers |

### `icij:10066084` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11007765` | CONTINENTAL FINANCIAL SERVICES LIMITED | ? | Panama Papers |

### `icij:10105151` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11006076` | FIDUCIAIRE JEAN-MARC FABER | lu | Panama Papers |

### `icij:10150576` — 2 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:12128202` | TURNSTONE TRUST AND SECURITIES LIMITED OF THE HAKUNA MATATA  | shareholder of | ? | Panama Papers |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11013180` | TURNSTONE | im | Panama Papers |

### `icij:10210254` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11010869` | BUDIN & ASSOCIES | ch | Panama Papers |

### `icij:200513491` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

### `icij:10002359` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11010837` | LATINCONSULT INC. | pa | Panama Papers |

### `icij:10044455` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11013111` | KV ASSOCIATES S.A. | lu | Panama Papers |

### `icij:10059914` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11009258` | VICTOR LING & COMPANY | hk | Panama Papers |

### `icij:10115343` — 2 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11012290` | MOSSFON MANAGERS LTD. | bs | Panama Papers |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:10118710` | BH Associates Ltd. | same_as | same name and registration date as |  |

### `icij:10118710` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:14092567` | BH Associates Ltd. AKARA BLDG.; 24 DE CASTRO STR. WICKHAMS CAY I P.O. BOX 3136   | vg | Panama Papers |  |  |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11012720` | PRICEWATERHOUSE COOPERS (GIBRALTAR) | ? | Panama Papers |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:10115343` | BH Associates Ltd. | same_as | same name and registration date as |  |

### `icij:10120767` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11013111` | KV ASSOCIATES S.A. | lu | Panama Papers |

### `icij:10213513` — 2 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11010584` | LUBBOCK FINE (LONDON) | gb | Panama Papers |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:20050387` | G.R. ASOCIATES LIMITED | same_company_as | same company as | Bahamas Leaks |

### `icij:145750` — 5 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:236724` | Portcullis TrustNet Chambers P.O. Box 3444 Road Town, Tortola British Virgin Isl | vg | Offshore Leaks |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:54662` | Portcullis TrustNet (BVI) Limited | records & registers of | ? | Offshore Leaks |
| `icij:69734` | Ronald Johnson | director of | ? | Offshore Leaks |
| `icij:74134` | Nola Elaine Johnson | shareholder of | ca | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:290197` | NetIncorp.com Corporation | vg | Offshore Leaks |

## Cross-candidate overlap

**Officers shared across candidates**

| name | shared by |
| --- | --- |
| THE BEARER | icij:10058532, icij:10099374, icij:10123282 |

## Review notes

- No exact normalized-name match; treat all candidates as fuzzy hypotheses pending review.

## Provenance

- Seed: `HBRK Associates, Inc.` / `us`
- Seed normalized: `hbrk associates` / `us`
- Sources present in candidate pool: icij, opensanctions
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
- GoldenMatch dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
- GoldenMatch list-match run: `a01cce05-896b-4d19-911c-b3efe7b5f56f`
