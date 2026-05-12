# Investigation seed: `Cypress, Inc.` / vi

Generated `2026-05-12T13:50:04+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets + published GoldenMatch context.

**Seed source:** USVI Second Amended Complaint ST-20-CV-14 ¶38: VI corporation; Epstein listed as President/Director; owns New Mexico ranch property according to complaint.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 3 possible outside-jurisdiction match(es) — see separate section.
- Cluster membership: [326855, 355359, 626947] (from dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`).
- ICIJ 1-hop neighbourhood: 0 address(es), 0 officer-edge(s), 3 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 100.0 | `icij:20007175` | icij | `CYPRESS CORPORATION` | ? |  |
| 2 | 85.7 | `icij:20040806` | icij | `CIPRESS LIMITED` | ? |  |
| 3 | 85.7 | `icij:200110594` | icij | `CRPRESS LIMITED` | ? |  |

## Published GoldenMatch context

### Cluster membership

From dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`.

| entity_uid | cluster_id |
| --- | ---: |
| `icij:20007175` | 326855 |
| `icij:20040806` | 355359 |
| `icij:200110594` | 626947 |

## 1-hop ICIJ neighbourhood

### `icij:20007175` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000198` | LENNOX CORPORATE SERVICES LIMITED | bs | Bahamas Leaks |

### `icij:20040806` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000132` | SANTANDER BANK & TRUST (BAHAMAS) Ltd. | bs | Bahamas Leaks |

### `icij:200110594` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000022` | Nisbetts, Law Chambers | ? |  |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Cypress, Inc.` / `vi`
- Seed normalized: `cypress` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
- GoldenMatch dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
- GoldenMatch list-match run: `a01cce05-896b-4d19-911c-b3efe7b5f56f`
