# Investigation seed: `J Black Trust` / vi

Generated `2026-05-12T02:19:43+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets.

**Seed source:** Senate Finance 2025 list names J Black Trust. Trust seed, not a company.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 1 possible outside-jurisdiction match(es) — see separate section.
- ICIJ 1-hop neighbourhood: 0 address(es), 0 officer-edge(s), 1 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 87.5 | `icij:20128273` | icij | `JET BLACK LIMITED` | ? |  |

## Published GoldenMatch context

_Skipped — no `DATABASE_URL` set. Set the env var to enrich with published list-match anchors, cluster memberships, and same-as pairs._
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
