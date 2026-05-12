# Investigation seed: `J Black Trust` / vi

Generated `2026-05-12T13:51:16+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets + published GoldenMatch context.

**Seed source:** Senate Finance 2025 list names J Black Trust. Trust seed, not a company.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 1 possible outside-jurisdiction match(es) — see separate section.
- Cluster membership: [436853] (from dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`).
- ICIJ 1-hop neighbourhood: 0 address(es), 0 officer-edge(s), 1 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 87.5 | `icij:20128273` | icij | `JET BLACK LIMITED` | ? |  |

## Published GoldenMatch context

### Cluster membership

From dedupe run `ba237a6c-8a29-43a5-8d07-f0eb81473bce`.

| entity_uid | cluster_id |
| --- | ---: |
| `icij:20128273` | 436853 |

## 1-hop ICIJ neighbourhood

### `icij:20128273` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000219` | GTC CORPORATE SERVICES LIMITED | bs | Bahamas Leaks |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `J Black Trust` / `vi`
- Seed normalized: `j black` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
- GoldenMatch dedupe run: `ba237a6c-8a29-43a5-8d07-f0eb81473bce`
- GoldenMatch list-match run: `a01cce05-896b-4d19-911c-b3efe7b5f56f`
