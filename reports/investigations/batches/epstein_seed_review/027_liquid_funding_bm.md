# Investigation seed: `Liquid Funding Ltd.` / bm

Generated `2026-05-12T05:05:18+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets + published GoldenMatch context.

**Seed source:** Reported in public Epstein corporate-network summaries as a Bermuda investment/offshore entity linked through Paradise Papers/ICIJ context. Broader watchlist seed pending verification.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- Best local candidate: `icij:82004676` (`Liquid Funding, Ltd.`, bm, score 100.0)
- Cluster membership: [499145] (from dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`).
- ICIJ 1-hop neighbourhood: 3 address(es), 15 officer-edge(s), 0 intermediary-edge(s).

## Candidate records (same jurisdiction)

| # | score | exact | entity_uid | source | name | jurisdiction | lei | company_number |
| ---: | ---: | :-: | --- | --- | --- | --- | --- | --- |
| 1 | 100.0 | ✓ | `icij:82004676` | icij | `Liquid Funding, Ltd.` | bm |  |  |

## Published GoldenMatch context

### Cluster membership

From dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`.

| entity_uid | cluster_id |
| --- | ---: |
| `icij:82004676` | 499145 |

## 1-hop ICIJ neighbourhood

### `icij:82004676` — 26 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:81027090` | Canon's Court | bm | Paradise Papers - Appleby |  |  |
| `icij:81029389` | Argyle House | bm | Paradise Papers - Appleby |  |  |
| `icij:81030718` | Pascal Lambert | ie | Paradise Papers - Appleby |  |  |

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:80111786` | Perinchief - Diane | secretary of | ? | Paradise Papers - Appleby |
| `icij:80113450` | Poole - Deborah J | director of | ? | Paradise Papers - Appleby |
| `icij:80069756` | Gillespie - Hugh Edwin | director of | ? | Paradise Papers - Appleby |
| `icij:80067647` | Fulton - Mary | auditor | ie | Paradise Papers - Appleby |
| `icij:80039252` | Erskine - Alex J | director of | ? | Paradise Papers - Appleby |
| `icij:80000191` |  | secretary of | ? | Paradise Papers - Appleby |
| `icij:80114190` | PricewaterhouseCoopers LLP - New York, Madison Ave | auditor | ? | Paradise Papers - Appleby |
| `icij:80096976` | MacNamara - Liam | director of | ie | Paradise Papers - Appleby |
| `icij:80094304` | Lipman - Jeffrey M | director of | us | Paradise Papers - Appleby |
| `icij:80063035` | Epstein - Jeffrey E | director of | ? | Paradise Papers - Appleby |
| `icij:80107655` | Novelly - Paul Anthony | director of | us | Paradise Papers - Appleby |
| `icij:80087420` | Klug - Marcus | director of | ? | Paradise Papers - Appleby |
| `icij:80056030` | Deloitte & Touche LLP - NY - Broadway | auditor | us | Paradise Papers - Appleby |
| `icij:80042934` | Burritt - James R | director of | us | Paradise Papers - Appleby |
| `icij:80088364` | Krehan - Ernst | director of | ? | Paradise Papers - Appleby |

## Review notes

- Top candidate is an exact normalized-name match in the seed jurisdiction — strong signal.

## Provenance

- Seed: `Liquid Funding Ltd.` / `bm`
- Seed normalized: `liquid funding` / `bm`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
- GoldenMatch dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
- GoldenMatch list-match run: `a01cce05-896b-4d19-911c-b3efe7b5f56f`
