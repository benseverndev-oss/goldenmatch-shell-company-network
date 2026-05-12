# Investigation seed: `Nautilus, Inc.` / vi

Generated `2026-05-12T13:49:44+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets + published GoldenMatch context.

**Seed source:** USVI Second Amended Complaint ST-20-CV-14 ¶¶22–24: VI corporation owning Little St. James; Epstein listed as president/director.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 6 possible outside-jurisdiction match(es) — see separate section.
- Cluster membership: [6296, 243896, 258184, 418306, 616680, 763797] (from dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`).
- ICIJ 1-hop neighbourhood: 2 address(es), 26 officer-edge(s), 5 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 100.0 | `icij:169509` | icij | `Nautilus Trust` | ? |  |
| 2 | 100.0 | `icij:168254` | icij | `Nautilus Limited` | ? |  |
| 3 | 87.5 | `icij:20145122` | icij | `NAUTICUS, LTD.` | ? |  |
| 4 | 87.5 | `icij:200100029` | icij | `NANTILUS CORPORATION` | ? |  |
| 5 | 85.7 | `icij:10006363` | icij | `NATLUS CORPORATION` | ? |  |
| 6 | 85.7 | `icij:55064234` | icij | `ATILUS LTD` | mt |  |

## Published GoldenMatch context

### Cluster membership

From dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`.

| entity_uid | cluster_id |
| --- | ---: |
| `icij:10006363` | 6296 |
| `icij:169509` | 243896 |
| `icij:168254` | 258184 |
| `icij:20145122` | 418306 |
| `icij:200100029` | 616680 |
| `icij:55064234` | 763797 |

## 1-hop ICIJ neighbourhood

### `icij:169509` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:292091` | Jaime Rotondo | es | Offshore Leaks |

### `icij:168254` — 17 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:272053` | Monte Esquinza, 30 Bajo, Izd. 28010 Madrid SPAIN | es | Offshore Leaks |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:47535` | Jaime Rotondo Abogados | authorised person / signatory of | es | Offshore Leaks |
| `icij:2001534` | Bearer 1 | shareholder of | ? | Offshore Leaks |
| `icij:56917` | Trustcorp Limited | shareholder of | ? | Offshore Leaks |
| `icij:49616` | Secorp Limited | secretary of | ? | Offshore Leaks |
| `icij:41938` | Patrick K. Oesch | director of | ch | Offshore Leaks |
| `icij:117069` | Thomas Gui Mori | director of | es | Offshore Leaks |
| `icij:43216` | Erwin Muller | director of | ch | Offshore Leaks |
| `icij:116718` | Riccardo Giuscetti | director of | ch | Offshore Leaks |
| `icij:41632` | Peter Hafter | director of | ch | Offshore Leaks |
| `icij:117469` | Jaime Rotondo-Russo | director of | es | Offshore Leaks |
| `icij:44851` | Ann Weigel | director of | gb | Offshore Leaks |
| `icij:46768` | Alberto Goetsch Lara | director of | es | Offshore Leaks |
| `icij:96577` | Buque Anstalt | director of | li | Offshore Leaks |
| `icij:111447` | Carmen Thyssen-Bornemisza | shareholder of | ad | Offshore Leaks |
| `icij:114004` | Borja Thyssen-Bornemisza | shareholder of | ad | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:292091` | Jaime Rotondo | es | Offshore Leaks |

### `icij:20145122` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000018` | GSO CORPORATE SERVICES LTD. | bs | Bahamas Leaks |

### `icij:200100029` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

### `icij:10006363` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:11008489` | PARVEZ & CO. | gb | Panama Papers |

### `icij:55064234` — 12 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:58007938` | 171 OLD BAKERY STREET, VALLETTA, MALTA | ? | Paradise Papers - Malta corporate registry |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:56014203` | NOEL BUTTIGIEG SCICLUNA | judicial representative of | mt | Paradise Papers - Malta corporate registry |
| `icij:56014203` | NOEL BUTTIGIEG SCICLUNA | legal representative of | mt | Paradise Papers - Malta corporate registry |
| `icij:56014203` | NOEL BUTTIGIEG SCICLUNA | director of | mt | Paradise Papers - Malta corporate registry |
| `icij:56027237` | INGRIDA MIKENAITE | director of | ? | Paradise Papers - Malta corporate registry |
| `icij:56025907` | PATRICK BRISCOE WHITE | secretary of | mt | Paradise Papers - Malta corporate registry |
| `icij:56027237` | INGRIDA MIKENAITE | legal representative of | ? | Paradise Papers - Malta corporate registry |
| `icij:56027237` | INGRIDA MIKENAITE | judicial representative of | ? | Paradise Papers - Malta corporate registry |
| `icij:56026881` | NERIJUS NUMAVICIUS | shareholder of | ? | Paradise Papers - Malta corporate registry |
| `icij:56047806` | ONE FAMILY TRUST COMPANY LTD, in its capacity as trustee of  | shareholder of | bm | Paradise Papers - Malta corporate registry |
| `icij:56055980` | STICHTING NOVITUS | shareholder of | nl | Paradise Papers - Malta corporate registry |
| `icij:56047805` | ONE FAMILY TRUST COMPANY LTD, in its capacity as trustee of  | shareholder of | bm | Paradise Papers - Malta corporate registry |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Nautilus, Inc.` / `vi`
- Seed normalized: `nautilus` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
- GoldenMatch dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
- GoldenMatch list-match run: `a01cce05-896b-4d19-911c-b3efe7b5f56f`
