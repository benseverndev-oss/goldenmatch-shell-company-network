# Investigation seed: `Maple, Inc.` / vi

Generated `2026-05-12T02:19:08+00:00` as part of batch `epstein_seed_review`. Seed-query workflow over local processed parquets.

**Seed source:** USVI Second Amended Complaint ST-20-CV-14 ¶39: VI corporation; Epstein listed as President/Director; owns 9 East 71st Street according to complaint.

> **Hypothesis, not proof.** Every candidate below is a guess the matcher produced from public data. Names collide. Public data is incomplete. Treat each row as a lead to review, not a finding to publish. Do not derive identity-linked claims without human review.

## Summary

- No same-jurisdiction candidates above the score threshold.
- 6 possible outside-jurisdiction match(es) — see separate section.
- ICIJ 1-hop neighbourhood: 1 address(es), 12 officer-edge(s), 5 intermediary-edge(s).

## Candidate records (same jurisdiction)

_No candidates passed the score threshold._

## Possible outside-jurisdiction matches

_These score well but their jurisdiction does not match the seed. Treat as lower-confidence hypotheses — jurisdiction may be missing, abbreviated differently, or genuinely distinct._

| # | score | entity_uid | source | name | jurisdiction | lei |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 100.0 | `icij:169840` | icij | `Maple Trust` | ? |  |
| 2 | 100.0 | `icij:20083745` | icij | `MAPLE LTD` | ? |  |
| 3 | 100.0 | `icij:82017408` | icij | `MAPLE TRUST` | ky |  |
| 4 | 100.0 | `icij:200101425` | icij | `MAPLE CORP.` | ? |  |
| 5 | 90.9 | `icij:200133884` | icij | `MARPLE LIMITED` | ? |  |
| 6 | 88.9 | `icij:20036379` | icij | `MALE, LTD` | ? |  |

## Published GoldenMatch context

_Skipped — no `DATABASE_URL` set. Set the env var to enrich with published list-match anchors, cluster memberships, and same-as pairs._
## 1-hop ICIJ neighbourhood

### `icij:169840` — 13 edges

**Officers**

| node | name | role | country | leak |
| --- | --- | --- | --- | --- |
| `icij:116916` | Steven E. Wheeler | trust settlor of | us | Offshore Leaks |
| `icij:111699` | Fidelitycorp Limited | trustee of trust of | ? | Offshore Leaks |
| `icij:116916` | Steven E. Wheeler | beneficiary of | us | Offshore Leaks |
| `icij:47961` | Cameron H. Wheeler | beneficiary of | us | Offshore Leaks |
| `icij:46691` | Carter B. Wheeler | beneficiary of | us | Offshore Leaks |
| `icij:116539` | M. Gates Wheeler | beneficiary of | us | Offshore Leaks |
| `icij:47929` | Justin P. Wheeler | beneficiary of | us | Offshore Leaks |
| `icij:43942` | Martha C. Wheeler | beneficiary of | us | Offshore Leaks |
| `icij:115898` | Brooke D. Wheeler | beneficiary of | us | Offshore Leaks |
| `icij:56689` | Garrett B. Wheeler | beneficiary of | us | Offshore Leaks |
| `icij:86655` | Dayton Ogden | protector of | us | Offshore Leaks |
| `icij:114247` | Mark A. Cohen, CPA | general accountant of | us | Offshore Leaks |

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:293360` | Lourie & Cutler, P.C. | us | Offshore Leaks |

### `icij:20083745` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000228` | H & J CORPORATE SERVICES LTD. | bs | Bahamas Leaks |

### `icij:82017408` — 1 edges

**Registered addresses**

| node | address | country | leak | start | end |
| --- | --- | --- | --- | --- | --- |
| `icij:81027146` | Clifton House | ? | Paradise Papers - Appleby |  |  |

### `icij:200101425` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000018` | Morning Star Holdings Limited | ? |  |

### `icij:200133884` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:230000066` | IFG Trust Services Inc. | ? |  |

### `icij:20036379` — 1 edges

**Intermediaries**

| node | name | country | leak |
| --- | --- | --- | --- |
| `icij:23000156` | TRIDENT CORPORATE SERVICES (BAH) LTD | bs | Bahamas Leaks |

## Review notes

- All hits are outside the seed jurisdiction. Consider whether the seed jurisdiction code itself is right.

## Provenance

- Seed: `Maple, Inc.` / `vi`
- Seed normalized: `maple` / `vi`
- Sources present in candidate pool: icij
- company_table: `D:\show_case\goldenmatch-shell-company-network\data\processed\company_entities.parquet`
- icij_edges: `D:\show_case\goldenmatch-shell-company-network\data\interim\icij_edges.parquet`
- top_n: `25`
- min_score: `85.0`
- global_fallback: `True`
- seeds_csv: `seeds\epstein_entities.csv`
