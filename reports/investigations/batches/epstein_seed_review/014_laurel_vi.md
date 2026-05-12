# Investigation seed: `Laurel, Inc.` / vi

Generated `2026-05-12T13:50:16+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets + published GoldenMatch context.

**Seed source:** USVI Second Amended Complaint ST-20-CV-14 ¶40: VI corporation; Epstein listed as President/Director; owns Palm Beach property according to complaint.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 13 possible outside-jurisdiction match(es) — see separate section.
- Cluster membership: [37254, 76255, 77126, 171142, 278532, 287561, 338539, 475204, 501335, 570693, 724420, 788901] (from dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`).
- ICIJ 1-hop neighbourhood: 4 address(es), 10 officer-edge(s), 9 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 100.0 | `icij:10037714` | icij | `LAUREL INCORPORATED` | ? |  |
| 2 | 100.0 | `icij:82008944` | icij | `Laurel Trust` | bm |  |
| 3 | 100.0 | `icij:30016924` | icij | `LAUREL LIMITED` | ? |  |
| 4 | 100.0 | `icij:55022720` | icij | `LAUREL LIMITED` | mt |  |
| 5 | 100.0 | `opensanctions:icijol-82008944` | opensanctions | `Laurel Trust` | bm |  |
| 6 | 92.3 | `icij:196490` | icij | `LAURIEL LIMITED` | ? |  |
| 7 | 90.9 | `icij:10075885` | icij | `AUREL LIMITED` | vg |  |
| 8 | 85.7 | `icij:10076717` | icij | `LAURIMEL LIMITED` | vg |  |
| 9 | 85.7 | `icij:10172637` | icij | `LAURIMEL LIMITED` | ? |  |
| 10 | 85.7 | `icij:224400` | icij | `Laureola Corporation` | ? |  |
| 11 | 85.7 | `icij:20023643` | icij | `LAURIMEL LIMITED` | ? |  |
| 12 | 85.7 | `icij:20131038` | icij | `ANLAUREL LTD.` | ? |  |
| 13 | 85.7 | `icij:240550149` | icij | `LAURIMEL Inc` | pa |  |

## Published GoldenMatch context

### Cluster membership

From dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`.

| entity_uid | cluster_id |
| --- | ---: |
| `icij:10037714` | 37254 |
| `icij:10075885` | 76255 |
| `icij:20023643` | 338539 |
| `icij:82008944` | 501335 |
| `icij:55022720` | 724420 |
| `icij:240550149` | 788901 |
| `icij:10076717` | 77126 |
| `icij:224400` | 287561 |
| `icij:30016924` | 570693 |
| `icij:10172637` | 171142 |
| `icij:196490` | 278532 |
| `icij:20131038` | 475204 |

## 1-hop ICIJ neighbourhood

### `icij:10037714` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11009289` | LARSSEN CORPORATE SERVICES S.A. | ? | Panama Papers |

### `icij:82008944` — 4 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:81027090` | Canon's Court | bm | Paradise Papers - Appleby |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:80000191` |  | trustee of | ? | Paradise Papers - Appleby |
| `icij:80002335` | Appleby Protectors (Bermuda) Limited | enforcer of | bm | Paradise Papers - Appleby |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:80108628` |  | connected_to | connected to | Paradise Papers - Appleby |

### `icij:30016924` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:32000238` | GTC CORPORATE SERVICES LIMITED | bs | Paradise Papers - Bahamas corporate registry |

### `icij:55022720` — 4 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:58074340` | JIREH, TRIQ IL-BIES, SAN GWANNSGN 07, MALTA | ? | Paradise Papers - Malta corporate registry |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:56020096` | CARL F WILLIAMS | judicial representative of | us | Paradise Papers - Malta corporate registry |
| `icij:56020096` | CARL F WILLIAMS | director of | us | Paradise Papers - Malta corporate registry |
| `icij:56079086` | CRV INTERNATIONAL LIMITED | shareholder of | mt | Paradise Papers - Malta corporate registry |

### `icij:196490` — 2 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:286081` | Stanley Davis Group Limited 41 Chalton Street London NW 1JD England | gb | Offshore Leaks |  |  |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:298296` | Stanley Davis Group Limited | gb | Offshore Leaks |

### `icij:10075885` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11012037` | PRIME CORPORATE SOLUTIONS SARL | lu | Panama Papers |

### `icij:10076717` — 3 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:12170902` | Mt. Wesley Trustees Limited | shareholder of | nz | Panama Papers |
| `icij:12116596` | Republic International Trust Company Ltd. as trustee of The  | shareholder of | mc | Panama Papers |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11004266` | GUARDIAN MANAGEMENT SARL | mc | Panama Papers |

### `icij:10172637` — 2 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11010643` | LEGAL CONSULTING SERVICES LIMITED | ru | Panama Papers |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:20023643` | LAURIMEL LIMITED | same_company_as | same company as | Bahamas Leaks |

### `icij:224400` — 3 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:271169` | Kuzniecky & Co. Banco General Building, 21st Floor Aquilino de la Guardia Street | pa | Offshore Leaks |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:20620` | Raul Garrido Garibaldo | director of | pa | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:298166` | Kuzniecky & Co. | pa | Offshore Leaks |

### `icij:20023643` — 2 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000136` | MOSSACK FONSECA & CO. (BAHAMAS) LIMITED | bs | Bahamas Leaks |

**Connected entities**

| node | name | kind_raw | role | leak |
| --- | --- | --- | --- | --- |
| `icij:10172637` | LAURIMEL LIMITED | same_company_as | same company as | Bahamas Leaks |

### `icij:20131038` — 2 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:22000200` | BSI MANAGEMENT LTD. | director | ? | Bahamas Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000365` | AMBER TRUST LTD. | bs | Bahamas Leaks |

### `icij:240550149` — 1 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:240552154` | Roberto Arturo Dunn Suarez | power of attorney | ? |  |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Laurel, Inc.` / `vi`
- Seed normalized: `laurel` / `vi`
- Sources present in candidate pool: icij, opensanctions
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
- GoldenMatch dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
- GoldenMatch list-match run: `a01cce05-896b-4d19-911c-b3efe7b5f56f`
