# About this project

`goldenmatch-shell-company-network` is a reproducible investigative pipeline for offshore-leak corpora. It combines record-linkage benchmarking against operational baselines (the original v1 deliverable) with named, statute-anchored findings against real UK regulatory data (the v2 wrongdoing track).

## Two threads

### 1. Discovery-advantage pipeline (v1)

The original deliverable: an end-to-end ICIJ + OpenSanctions + GLEIF + UK PSC ingest, GoldenMatch-based cross-source entity resolution, confidence-weighted graph construction, unsupervised structure mining, and per-axis benchmarks against operational baselines.

Headline numbers (full provenance in [`docs/reports/discovery_advantage.md`](reports/discovery_advantage.md)):

| Axis | Δ vs baseline |
|---|---|
| Multi-source anchors surfaced | +11.2% |
| Cross-source evidence on B3 sample | +7.5% |
| Analyst-hours to triage B3 | −62.5% |
| Adversarial perturbation recovery | +133% |
| Expected calibration error | −100% |
| Brier score | −39.9% |

The two original case studies — **Phoenix Spree Deutschland** (100% GLEIF-anchored 9-member ICIJ cluster) and **Epstein corporate-network seed review** (28 sourced seeds; *Liquid Funding, Ltd.* the headline corroboration) — exercise the pipeline end-to-end on real targets.

### 2. ROE non-compliance wrongdoing track (v2)

The pivot: from describing structures to surfacing **chargeable statutory violations**.

The UK's Economic Crime (Transparency and Enforcement) Act 2022 created a Register of Overseas Entities at Companies House. Every overseas-incorporated entity holding UK qualifying property since the Feb 2022 cut-over must register and disclose beneficial ownership. Failure is a criminal offence (s.34/s.42), with daily fines, criminal liability for officers, and restrictions on dealing with the property until compliant.

Cross-referencing HM Land Registry's OCOD (365,316 UK titles owned by overseas companies, May 2026) against the UK CH OE registry (30,221 registered entities, extracted from the May 2026 Basic Company Data bulk download) by normalised entity name surfaces:

- **5,298 → 4,174 apparent non-compliant proprietors** (depending on matcher strictness)
- **12,181 → 9,198 UK property titles** held by them
- **733 of those titles unambiguously breached** — acquired post-Aug-2022, no transitional-period defence

The non-compliant set is then layered with four further lenses (ICIJ leak overlap, OpenSanctions sanctions/PEP overlap, geographic concentration in prime central London postcodes, acquisition-date split), and six named-thread case studies sit on top:

| Thread | Finding |
|---|---|
| FENLAND LIMITED (Isle of Man) | 313 UK residential titles concentrated in W14/SW5/W8/W2, Paradise Papers names Lilian + Lawrence Fenech as officers |
| Edokpolo / EKO IRE LIMITED (BVI) | 5 titles, Pandora Papers (Alcogal), three Edokpolo family officers named, Nigerian Edokonsult correspondence |
| Embassy Development (Lux/Jersey) | 3-SPV Battersea/Nine Elms structure incl. £44M Plot E, OS-flagged debarment+sanction, acquired pre-ECTEA |
| Harmony Ridge Limited (Jersey/BVI) | 1 Kensington flat, OS sanction.linked, name in Panama + Paradise Papers |
| **Ledra Trustee Services Limited (Cyprus)** | Mayfair flat (45 Green Street W1K 7FX), OS debarment+sanction. The same Cyprus "Ledra" service-provider brand appears in Panama Papers as nominee director for a multi-jurisdiction Metalloinvest BVI/Cyprus structure controlled by US-OFAC-sanctioned Russian oligarch Alisher Usmanov |
| **IGT Intergestions Trust Reg (Liechtenstein)** | 5 Highgate land titles. On the actual US OFAC SDN list. Liechtenstein-Anstalt counterpart to the Cyprus-Ledra finding |
| Park Plaza Westminster Bridge (SE1) | The 690-title SE1 cluster is 88% one hotel-condo operator (Dutch B.V.). Different pattern from the prime-luxury offshore-shell shape — reframing rather than headliner |

Full writeup with methodology, caveats, jurisdictional concentration, and the structural diagrams: [`docs/case_study_roe_noncompliance.md`](case_study_roe_noncompliance.md).

## Methodology, briefly

- **Compute on Railway, not laptop.** Heavy joins (OCOD × OE registry, 365k × 30k by normalised name; ICIJ × OS by tokens) run on the project's Railway service against parquets in a /data volume. The local repo holds only small extracts (the OE-prefixed bulk subset at `data/uk_ch_overseas_entities.parquet`, ~1 MB).
- **Defamation guards throughout.** Normalised-name matching requires ≥2 tokens and ≥8 chars; suffix-stripping (LTD/LIMITED/LLC/INC/BV/GMBH/SA…) before exact-key match; fuzzy second-pass with token-set Jaccard ≥ 0.7 to suppress suffix-form false positives. Each named-thread case study surfaces the specific corporate-registry caveats that apply.
- **No claim without an edge.** When a name appears in proximity (e.g. Yorgen Fenech in the same Paradise-Malta corporate-registry leak as FENLAND LIMITED, or USM Steel adjacent to IGT Intergestions in Panama Papers) but no graph edge ties them, this is flagged as "proximity in leak corpus, not connection" rather than claimed.
- **Live-source verification for high-stakes claims.** The Ledra-Metalloinvest chain went through `probe_metalloinvest_verify` (Railway-side ICIJ + OS records) + `verify_metalloinvest_uk_ch.py` (local live UK Companies House search) before any claim about Usmanov was made.

## What this is — and isn't

- **Is:** a record-linkage + cross-source investigative pipeline with quantified benchmarks against operational baselines, plus a working statute-anchored case study against UK ECTEA 2022 non-compliance.
- **Isn't:** an accusation engine. Every named-thread case study surfaces its caveats — corporate-identity vs brand-identity, proximity-in-leak vs edge-in-graph, OS topic-encoding quirks (e.g. AAR International's `crime.traffick` topic comes from US arms-export-controls enforcement, not human trafficking). The findings are leads that an investigative journalist or regulator would verify before publishing.

## Where to start reading

| If you want… | Read |
|---|---|
| The quantified pipeline benchmarks | [`docs/reports/discovery_advantage.md`](reports/discovery_advantage.md) |
| The named-targets walkthrough on the auto-surfaced candidates | [`docs/reports/top_candidates_walkthrough.md`](reports/top_candidates_walkthrough.md) |
| The ROE non-compliance case study (wrongdoing track) | [`docs/case_study_roe_noncompliance.md`](case_study_roe_noncompliance.md) |
| Methodology + uncertainty propagation in record-linkage | [`docs/methodology.md`](methodology.md) · [`docs/paper/methodology.md`](paper/methodology.md) |
| Data-source coverage and ingestion roadmap | [`docs/data-sources.md`](data-sources.md) · [`docs/ingestion_roadmap.md`](ingestion_roadmap.md) |
| Reproducing locally | See "Quickstart" in [`README.md`](../README.md) |
