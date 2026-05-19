# Cluster 70 Validation Pack

## Status
Machine-generated. **Human review required.** Not an accusation or finding of wrongdoing.

## Investigation target
- Community ID: **70**
- Human anchor: **adriano cefai**
- Generated at: 2026-05-19 16:44:40 UTC
- Script: `scripts/build_validation_pack.py`
- Threshold: 0.9

### Data gaps / warnings
- ⚠️ dossier file not found at /app/docs/reports/dossiers/adriano-cefai.md — using parquet only.

## Machine-generated triage summary
| Metric | Value |
| --- | --- |
| Priority score | 0.211773 |
| Cluster size | 5 |
| Cluster confidence | 0.9025 |
| Mean edge credibility | 0.9025 |
| Contradiction density | 0.0 |
| Anomaly score | 0.6 |
| Isolation | 1.0 |
| Seed nodes | 0 |
| Underreportedness | 1.0 |
| Attestation density | 0.0 |

## Why this cluster ranked highly
The composite priority formula produced **0.211773**, weighted on:

- structurally strange (anomaly): 0.6
- high-confidence: 0.9025
- highly connected: 0.3026
- underreported: 1.0

See `docs/reports/validation_queue.md` for the full ranking context.

## Community sample members (first 20)
| Name | uid | Jurisdiction | Seed? |
| --- | --- | --- | --- |
| ADRIANO CEFAI | icij:56033452 | mt |  |
| CHRISTIAN ELLUL | icij:56032560 | mt |  |
| FIDES FIDUCIARY LIMITED | icij:56083164 | mt |  |
| icij:58038552 | icij:58038552 |  |  |
| FIDES CORPORATE SERVICES LIMITED | icij:56082935 | mt |  |

_Total cluster size: 5_

## adriano cefai dossier summary
_(no dossier file)_

## Company overlap table
| Company | Normalized | In cluster? | In dossier? | Match type | Conf |
| --- | --- | --- | --- | --- | --- |
| ADRIANO CEFAI | adriano cefai | true | false | community_only | 1.00 |
| CHRISTIAN ELLUL | christian ellul | true | false | community_only | 1.00 |
| FIDES CORPORATE SERVICES LIMITED | fides corporate services | true | false | community_only | 1.00 |
| FIDES FIDUCIARY LIMITED | fides fiduciary | true | false | community_only | 1.00 |
| icij:58038552 | icij 58038552 | true | false | community_only | 1.00 |

_Exact normalized-name overlap: **0** companies. Full CSV: `data/cluster_70_person_overlap.csv`._

## Person-company role evidence
| Company | Relationship | Role | Leak |
| --- | --- | --- | --- |
| icij:58038552 | registered_address | registered address | Paradise Papers - Malta corporate registry |

_1 edges total. Full CSV: `data/cluster_70_person_company_roles.csv`._

## Recurring infrastructure
### Addresses
| Address | N linked | Source |
| --- | --- | --- |
| 5/1 MERCHANTS STREET VALLETTA VLT 1171 | 4 | Paradise Papers - Malta corporate registry |
| 5/1 MERCHANTS STREET VALLETTA VLT1171 | 2 | Paradise Papers - Malta corporate registry |

### Officers / directors
_(no rows)_

### Agents / intermediaries
_(no rows)_

### Secretaries / service providers
_(officer rows with role containing 'secretary' or 'service' surfaced in the officers table above; not separated in the source data.)_

## Company theme classification
| Theme | Count |
| --- | --- |
| services / administration | 2 |
| unknown | 2 |
| tech / digital | 1 |

_These are **weak labels** — keyword-based heuristics, every row is flagged needs_manual_review = true._

## Graph paths
See `data/cluster_70_graph_paths.md` for the full extracted-paths report.

## External search queue
`data/cluster_70_external_search_queries.csv` contains **50** queries.
No external search has been run automatically (no safe abstraction wired). The reviewer should execute these queries by hand against the appropriate registries / search engines, or pass `--run-external-search` if/when an in-repo abstraction is added.

## Same-person evidence matrix
> **Are the Peter Kevin Perry records the same person?**

**Final verdict: Human review required.** Below is candidate evidence only — do not treat as a determination.

**Supporting evidence:**
- All ICIJ rows report the same country: mt.

**Contradictory evidence:**
- _(none)_

**Missing evidence:**
- only one or zero ICIJ uids — cannot test same-person consistency.
- date-of-birth not available in icij_persons; cannot compare DOB.
- no canonical home-address field for persons; cannot compare residential address.

## Ordinary vs unusual analysis
| Indicator | Value | Interpretation |
| --- | --- | --- |
| Cluster size | 5 |  |
| Officer reuse rate | 0.0 | high reuse = corporate-services hub |
| Address reuse rate | 0.8 | high reuse = shared registered office |
| Intermediary reuse rate | 0.0 | high reuse = shared agent |
| Top theme | services / administration | share=0.4 |
| Anomaly score | 0.6 |  |
| Isolation | 1.0 | 1.0 = no cross-cluster bridges |
| Underreportedness | 1.0 | 1.0 = no name overlap with formal registries |
| Contradiction density | 0.0 |  |
| # repeated addresses | 2 |  |
| # repeated officers | 0 |  |
| # repeated intermediaries | 0 |  |

> **TODO:** percentile ranks against a cluster baseline have not been computed (no per-cluster baseline parquet present). Raw values only above.

## Contradictory or missing evidence
- ICIJ records do not include date-of-birth for persons; same-person claims cannot be tested on DOB.
- No web-corroboration is wired (dossier records 0 hits as of 2026-05-16).
- Address fields on most cluster member entity rows are null; address-bridge analysis depends on `registered_address` edges.

## Human review checklist
- [ ] Confirm whether the Peter Kevin Perry records refer to the same person
- [ ] Verify each overlapping company in source records
- [ ] Verify roles and dates
- [ ] Check external registry records (MFSA, Companies House, etc.)
- [ ] Check litigation / insolvency / sanctions / procurement / property / gaming / yacht records
- [ ] Determine whether this is ordinary corporate-services plumbing or unusual network structure
- [ ] Draft cautious narrative if evidence supports it

## Preliminary human verdict
Pending.

## Publication risk notes
- No allegations should be made without independent corroboration.
- Same-name does not imply same-person.
- Corporate-services hubs in Malta legitimately serve hundreds of unrelated clients; recurring infrastructure is a starting point, not an indictment.
- Preserve provenance (source_label, leak name, uid) for every claim carried into any published narrative.
