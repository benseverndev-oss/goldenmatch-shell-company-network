# Cluster 51 Validation Pack

## Status
Machine-generated. **Human review required.** Not an accusation or finding of wrongdoing.

## Investigation target
- Community ID: **51**
- Human anchor: **david james mason**
- Generated at: 2026-05-19 16:48:46 UTC
- Script: `scripts/build_validation_pack.py`
- Threshold: 0.9

### Data gaps / warnings
- ⚠️ dossier file not found at /app/docs/reports/dossiers/david-james-mason.md — using parquet only.

## Machine-generated triage summary
| Metric | Value |
| --- | --- |
| Priority score | 0.345343 |
| Cluster size | 12 |
| Cluster confidence | 0.9025 |
| Mean edge credibility | 0.9025 |
| Contradiction density | 0.0 |
| Anomaly score | 0.7 |
| Isolation | 1.0 |
| Seed nodes | 3 |
| Underreportedness | 1.0 |
| Attestation density | 0.0 |

## Why this cluster ranked highly
The composite priority formula produced **0.345343**, weighted on:

- structurally strange (anomaly): 0.7
- high-confidence: 0.9025
- highly connected: 0.4673
- underreported: 1.0

See `docs/reports/validation_queue.md` for the full ranking context.

## Community sample members (first 20)
| Name | uid | Jurisdiction | Seed? |
| --- | --- | --- | --- |
| BRAINTREE PROPERTIES LIMITED | icij:55062091 | mt | seed |
| ABBEYGLEN LIMITED | icij:55061260 | mt | seed |
| RIGHT IMAGE LIMITED | icij:55060150 | mt |  |
| HARBOUR CORPORATE MALTA LIMITED | icij:55058628 | mt |  |
| IPROPERTY LIMITED | icij:55060679 | mt |  |
| IPM (MALTA) LIMITED | icij:55061905 | mt |  |
| CONFIANCE MALTA SERVICES LIMITED | icij:55056785 | mt |  |
| MARLBOROUGH T ADVISORY LIMITED | icij:55051037 | mt |  |
| MKI MALTA LIMITED | icij:55060343 | mt |  |
| BIELEFELD PROPERTIES LIMITED | icij:55058948 | mt | seed |
| VERUM VICTUM HOLDINGS LIMITED | icij:55056831 | mt |  |
| icij:58003720 | icij:58003720 |  |  |

_Total cluster size: 12_

## david james mason dossier summary
_(no dossier file)_

## Company overlap table
| Company | Normalized | In cluster? | In dossier? | Match type | Conf |
| --- | --- | --- | --- | --- | --- |
| ABBEYGLEN LIMITED | abbeyglen | true | false | community_only | 1.00 |
| BIELEFELD PROPERTIES LIMITED | bielefeld properties | true | false | community_only | 1.00 |
| BRAINTREE PROPERTIES LIMITED | braintree properties | true | false | community_only | 1.00 |
| CONFIANCE MALTA SERVICES LIMITED | confiance malta services | true | false | community_only | 1.00 |
| HARBOUR CORPORATE MALTA LIMITED | harbour corporate malta | true | false | community_only | 1.00 |
| icij:58003720 | icij 58003720 | true | false | community_only | 1.00 |
| IPM (MALTA) LIMITED | ipm malta | true | false | community_only | 1.00 |
| IPROPERTY LIMITED | iproperty | true | false | community_only | 1.00 |
| MARLBOROUGH T ADVISORY LIMITED | marlborough t advisory | true | false | community_only | 1.00 |
| MKI MALTA LIMITED | mki malta | true | false | community_only | 1.00 |
| RIGHT IMAGE LIMITED | right image | true | false | community_only | 1.00 |
| VERUM VICTUM HOLDINGS LIMITED | verum victum holdings | true | false | community_only | 1.00 |

_Exact normalized-name overlap: **0** companies. Full CSV: `data/cluster_51_person_overlap.csv`._

## Person-company role evidence
| Company | Relationship | Role | Leak |
| --- | --- | --- | --- |
| BIELEFELD PROPERTIES LIMITED | officer_of | director of | Paradise Papers - Malta corporate registry |
| BIELEFELD PROPERTIES LIMITED | officer_of | judicial representative of | Paradise Papers - Malta corporate registry |
| BIELEFELD PROPERTIES LIMITED | officer_of | legal representative of | Paradise Papers - Malta corporate registry |
| BIELEFELD PROPERTIES LIMITED | officer_of | secretary of | Paradise Papers - Malta corporate registry |
| ABBEYGLEN LIMITED | officer_of | director of | Paradise Papers - Malta corporate registry |
| ABBEYGLEN LIMITED | officer_of | judicial representative of | Paradise Papers - Malta corporate registry |
| ABBEYGLEN LIMITED | officer_of | legal representative of | Paradise Papers - Malta corporate registry |
| ABBEYGLEN LIMITED | officer_of | secretary of | Paradise Papers - Malta corporate registry |
| BRAINTREE PROPERTIES LIMITED | officer_of | secretary of | Paradise Papers - Malta corporate registry |

_9 edges total. Full CSV: `data/cluster_51_person_company_roles.csv`._

## Recurring infrastructure
### Addresses
| Address | N linked | Source |
| --- | --- | --- |
| 1, BLOCK C SKYWAY OFFICES 179, MARINA STREET, PIETA'PTA 9042, MALTA | 11 | Paradise Papers - Malta corporate registry |

### Officers / directors
| Officer | N linked | Roles |
| --- | --- | --- |
| CONFIANCE MALTA LIMITED | 8 | director of;judicial representative of;legal representative of;shareholder of |
| GEOFFREY ROBERT LE PAGE | 6 | secretary of |
| JAMES PAUL GALLIGAN | 4 | director of;judicial representative of;legal representative of;shareholder of |
| DAVID JAMES MASON | 3 | director of;judicial representative of;legal representative of;secretary of |
| GARETH IVAN O'CONNELL | 3 | director of;judicial representative of;legal representative of;secretary of;shareholder of |
| JUSTIN JAMES CAFFREY | 3 | director of;judicial representative of;legal representative of;shareholder of |

### Agents / intermediaries
_(no rows)_

### Secretaries / service providers
_(officer rows with role containing 'secretary' or 'service' surfaced in the officers table above; not separated in the source data.)_

## Company theme classification
| Theme | Count |
| --- | --- |
| unknown | 6 |
| property / real estate | 3 |
| services / administration | 2 |
| investment / holding / capital | 1 |

_These are **weak labels** — keyword-based heuristics, every row is flagged needs_manual_review = true._

## Graph paths
See `data/cluster_51_graph_paths.md` for the full extracted-paths report.

## External search queue
`data/cluster_51_external_search_queries.csv` contains **113** queries.
No external search has been run automatically (no safe abstraction wired). The reviewer should execute these queries by hand against the appropriate registries / search engines, or pass `--run-external-search` if/when an in-repo abstraction is added.

## Same-person evidence matrix
> **Are the Peter Kevin Perry records the same person?**

**Final verdict: Human review required.** Below is candidate evidence only — do not treat as a determination.

**Supporting evidence:**
- _(none)_

**Contradictory evidence:**
- _(none)_

**Missing evidence:**
- only one or zero ICIJ uids — cannot test same-person consistency.
- country field missing in ICIJ persons rows.
- date-of-birth not available in icij_persons; cannot compare DOB.
- no canonical home-address field for persons; cannot compare residential address.

## Ordinary vs unusual analysis
| Indicator | Value | Interpretation |
| --- | --- | --- |
| Cluster size | 12 |  |
| Officer reuse rate | 0.917 | high reuse = corporate-services hub |
| Address reuse rate | 0.917 | high reuse = shared registered office |
| Intermediary reuse rate | 0.0 | high reuse = shared agent |
| Top theme | unknown | share=0.5 |
| Anomaly score | 0.7 |  |
| Isolation | 1.0 | 1.0 = no cross-cluster bridges |
| Underreportedness | 1.0 | 1.0 = no name overlap with formal registries |
| Contradiction density | 0.0 |  |
| # repeated addresses | 1 |  |
| # repeated officers | 6 |  |
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
