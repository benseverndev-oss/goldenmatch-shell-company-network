# goldenmatch-shell-company-network

A reproducible investigative pipeline for offshore-leak corpora, with
**quantified discovery-advantage benchmarks** against single-source
search baselines.

Built on [GoldenMatch](https://pypi.org/project/goldenmatch/) for
cross-source entity resolution, with ICIJ Offshore Leaks +
OpenSanctions + GLEIF + UK PSC + UK disqualified-directors as inputs.
The pipeline ingests, reconciles, builds a confidence-weighted graph,
runs unsupervised structure mining, and produces named investigative
candidates with per-entity novelty proofs.

**Start here:**
[`docs/reports/discovery_advantage.md`](docs/reports/discovery_advantage.md)
— the headline baseline-vs-pipeline benchmark. Every other report in
the repo is evidence for or against the claims made there.

## Headline result

The pipeline matches or beats every operational baseline we measured,
on every axis, on the full corpus:

| Axis | Baseline | Pipeline | Δ |
| --- | ---: | ---: | --- |
| Multi-source anchors surfaced | 22,695 (naive casefold) | 25,247 (GoldenMatch normalize) | ↑ 11.2% |
| Cross-source evidence on B3 sample | 465 (ICIJ search alone) | 500 (cross-source fuzzy) | ↑ 7.5% |
| Analyst-hours to triage B3 | 255.9 (manual) | 96.0 (pipeline) | ↓ 62.5% |
| Adversarial perturbation recovery | 0.42 (exact-after-normalize) | 0.99 (fuzzy token-set 85) | ↑ 133% |
| Expected calibration error | 0.38 (raw ER score) | ~0 (PAV-calibrated) | ↓ 100% |
| Brier score | 0.399 (raw) | 0.240 (calibrated) | ↓ 39.9% |

Full provenance and per-axis methodology in
[`discovery_advantage.md`](docs/reports/discovery_advantage.md).
Per-entity walkthrough of 11 named candidates in
[`top_candidates_walkthrough.md`](docs/reports/top_candidates_walkthrough.md).

## Reports & benchmarks

All reports are generated from Railway-side compute and committed to
the repo. Each markdown report has a sibling JSON / parquet under
[`docs/reports/data/`](docs/reports/data/) with the raw numbers.

| Report | What it shows | Build |
| --- | --- | --- |
| [`discovery_advantage.md`](docs/reports/discovery_advantage.md) | Synthesis benchmark: baseline-vs-pipeline delta across 6 axes | `build_discovery_advantage` |
| [`top_candidates_walkthrough.md`](docs/reports/top_candidates_walkthrough.md) | 11 named candidates with per-entity novelty proofs | `build_top_candidates_walkthrough` |
| [`discovery_lift.md`](docs/reports/discovery_lift.md) | B1→B4 tier funnel: how many anchors each pipeline stage surfaces | `build_discovery_lift` |
| [`baseline_comparison.md`](docs/reports/baseline_comparison.md) | ICIJ-search vs cross-source fuzzy + analyst-hour model | `build_baseline_comparison` |
| [`adversarial_benchmark.md`](docs/reports/adversarial_benchmark.md) | B2 vs B6 recovery against 4 perturbation classes | `build_adversarial_benchmark` |
| [`calibration_benchmark.md`](docs/reports/calibration_benchmark.md) | PAV calibration: raw vs calibrated Brier / ECE / log-loss | `build_calibration_benchmark` |
| [`structure_benchmark.md`](docs/reports/structure_benchmark.md) | 6 non-obvious structural patterns (intermediary reuse, jurisdiction bridges, registry anchors, sanctions-adjacent closure, ownership convergence, anomalous communities) | `build_structure_benchmark` |
| [`non_obviousness_ranking.md`](docs/reports/non_obviousness_ranking.md) | Per-anchor 5-factor non-obviousness score | `build_non_obviousness` |
| [`latent_clusters.md`](docs/reports/latent_clusters.md) | Unsupervised Louvain community mining + anomaly scoring | `build_latent_clusters` |
| [`temporal_patterns.md`](docs/reports/temporal_patterns.md) | Address-officer resurrections, incorporation bursts, long-lived anchors | `build_temporal_patterns` |
| [`confidence_graph.md`](docs/reports/confidence_graph.md) | Credibility-weighted communities, contradiction-aware closure, review-priority ranking | `build_confidence_graph` |
| [`join_novelty.md`](docs/reports/join_novelty.md) | Cross-source join novelty: rare-attribute joins absent from any single source | (built inline) |
| [`exposes_candidates.md`](docs/reports/exposes_candidates.md) | Auto-generated candidate exposés from top-anomaly clusters | `build_exposes_candidates` |
| [`failed_investigations.md`](docs/reports/failed_investigations.md) | Documented dead-ends (negative results) | (manual) |

## Worked investigations

Two case studies were the v1.0 deliverable and still hold up as the
"this is what the pipeline does to a real seed" demonstration:

- **Phoenix Spree Deutschland** — 9-member ICIJ cluster, 100% GLEIF
  anchored.
  [`notebooks/01_case_study.ipynb`](notebooks/01_case_study.ipynb) ·
  [writeup](reports/case_studies/503264_phoenix_spree_deutschland.md).
- **Epstein corporate-network seed review** — 28 sourced seeds. Headline
  *Liquid Funding, Ltd.* (Bermuda, ICIJ Paradise Papers — Appleby) is
  the single corroborated lead, with Jeffrey E Epstein listed as
  director + chairman alongside Bear Stearns SVP Jeffrey M Lipman.
  [`notebooks/02_epstein_case_study.ipynb`](notebooks/02_epstein_case_study.ipynb) ·
  [findings](reports/investigations/epstein_followup_2_findings.md).

Beyond these two, the **top-candidates walkthrough** auto-generates
11 named candidates (shared intermediaries, cross-jurisdiction bridge
officers, Louvain communities, non-obviousness-ranked rare officers)
without requiring a hand-curated seed list — the unsupervised channels
ask the pipeline to find investigation candidates the analyst didn't
know to look for.

## Corpus

After ICIJ + OpenSanctions + GLEIF + UK PSC ingest:

| Table | Rows |
| --- | ---: |
| `company_entities.parquet` | **1,240,555** (ICIJ 814k + OS 426k) |
| `person_entities.parquet` | **1,864,666** (ICIJ 711k + OS 1.15M) |
| `address_entities.parquet` | **1,180,555** (ICIJ 702k + OS 479k) |
| `uk_psc_dob.parquet` | **12,151,833** (UK Companies House PSC, DOB-only) |

## What this is — and isn't

**Is:** investigative data engineering with **quantified, reproducible
benchmarks** against operational baselines. We *connect* records that
plausibly refer to the same legal entity across noisy public sources;
we surface graph structure (shared addresses, shared officers, latent
communities, jurisdiction bridges) that a human investigator can then
review; and we measure how much of that surfacing is unreachable from
single-source search alone.

**Isn't:**

1. **An accusation engine.** Presence in ICIJ Offshore Leaks does not
   imply wrongdoing — many entities are legitimate. Matches produced
   by GoldenMatch are *hypotheses*, not facts. Always review by hand.
2. **A journalist-confirmed novelty study.** Discovery advantage is
   measured against operational baselines (ICIJ search, naive fuzzy
   match, manual cross-reference) — not against a panel of investigative
   journalists confirming which surfaced candidates are actually
   exposé-worthy. That panel-review study is the documented v2 gap in
   [`discovery_advantage.md`](docs/reports/discovery_advantage.md)
   §"Analyst review outcomes".
3. **A licence-bypass.** The datasets it ingests are governed by their
   own licences and terms of use. Read them before redistributing
   anything you derive.

## Data sources

| Source | Role | Access | Notes |
| --- | --- | --- | --- |
| [ICIJ Offshore Leaks](https://offshoreleaks.icij.org/pages/database) | Primary entities + relationships | Manual CSV download | Multiple leak bundles (Panama, Paradise, Pandora, etc.) |
| [OpenCorporates](https://api.opencorporates.com/) | Registry-anchored company records | API (key optional) | Polite pagination + on-disk cache |
| [GLEIF Golden Copy](https://www.gleif.org/en/lei-data/gleif-golden-copy) | Authoritative LEI records | Manual download | Streaming JSONL parser (`ijson`); XML is TODO |
| [OpenSanctions](https://www.opensanctions.org/datasets/) | Sanctions / PEPs / registers / enforcement | Manual export | Used as overlay, not ground truth |
| [UK Companies House PSC](https://download.companieshouse.gov.uk/en_pscdata.html) | Persons with Significant Control | Daily bulk download | 12M+ rows, DOB-only after filtering |
| [UK Disqualified Directors](https://download.companieshouse.gov.uk/en_output.html) | Banned company officers | Daily bulk download | Used as a regulatory-action signal |

Full per-source fields, licensing, and caveats live in
[`docs/data-sources.md`](docs/data-sources.md).

## Quickstart

```bash
# 0. Tooling: needs Python >=3.11 and uv (https://docs.astral.sh/uv/)
uv sync --extra dev

# 1. Run the test suite to confirm the scaffold is healthy
uv run pytest

# 2. Drop raw inputs in place (see docs/data-sources.md for each source)
#    e.g. unzip the ICIJ bundle into data/raw/icij/

# 3. Ingest whichever sources you have
uv run python scripts/ingest_icij.py
uv run python scripts/ingest_gleif.py --input data/raw/gleif/sample.json
uv run python scripts/ingest_opensanctions.py --input data/raw/opensanctions/entities.ftm.json

# 4. Build the unified tables
uv run python scripts/build_candidate_tables.py
uv run python scripts/build_address_table.py
uv run python scripts/build_person_table.py

# 5. Run GoldenMatch dedupe + list-match
uv run python scripts/run_goldenmatch_full.py --what company
uv run python scripts/run_goldenmatch_full.py --what address
uv run python scripts/run_goldenmatch_full.py --what person

# 6. Build the confidence-weighted graph + downstream benchmarks
uv run python scripts/build_confidence_graph.py
uv run python scripts/build_latent_clusters.py
uv run python scripts/build_structure_benchmark.py
uv run python scripts/build_non_obviousness.py
uv run python scripts/build_temporal_patterns.py

# 7. Synthesis report
uv run python scripts/build_discovery_advantage.py
uv run python scripts/render_discovery_advantage.py \
    --summary data/processed/discovery_advantage_summary.json \
    --out docs/reports/discovery_advantage.md
```

If you have `just` installed, all of the above are also available as
recipes: `just setup`, `just test`, `just ingest-icij`, etc.

For corpus-scale runs, **don't run any of the `build_*` scripts
locally** — they OOM on a laptop. See § Running on Railway below.

## Running on Railway

The full ICIJ + GLEIF + OpenSanctions corpus is too big to dedupe and
graph-walk on a laptop. The repo ships a FastAPI control plane
(`src/shellnet/job_server.py`) that wraps each pipeline stage as an
HTTP endpoint, deployable to Railway via the included `Dockerfile` +
`railway.json`.

Architecture:

```
laptop  --POST /upload-zip-->  shellnet-job (FastAPI)
                                |
                                +-- /data           (Railway volume, 50 GB)
                                +-- /unzip /ingest /build /match /publish /run-script
                                |
                                +-- DATABASE_URL --> Postgres (shellnet schema)
```

Setup (one-time):

```bash
railway link --project <project-id>
railway add --service shellnet-job
railway volume add --mount-path /data            # MSYS users: pass //data
railway variables -s shellnet-job \
  --set "SHELLNET_JOB_TOKEN=<your-token>" \
  --set "SHELLNET_DATA_DIR=/data" \
  --set 'DATABASE_URL=postgresql://${{postgres.POSTGRES_USER}}:${{postgres.POSTGRES_PASSWORD}}@${{postgres.RAILWAY_PRIVATE_DOMAIN}}:${{postgres.RAILWAY_TCP_APPLICATION_PORT}}/${{postgres.POSTGRES_DB}}'
railway up --service shellnet-job
railway domain --service shellnet-job
```

End-to-end ingest + dedupe + match against GLEIF (`$URL` = the
generated Railway domain, `$TOK` = your token):

```bash
SHELLNET_JOB_URL=$URL SHELLNET_JOB_TOKEN=$TOK \
  uv run python scripts/upload_icij.py full-oldb.LATEST.zip
curl -X POST -H "Authorization: Bearer $TOK" "$URL/unzip"
curl -X POST -H "Authorization: Bearer $TOK" "$URL/ingest?source=icij"
curl -X POST -H "Authorization: Bearer $TOK" \
  "$URL/fetch-url?url=https://data.opensanctions.org/datasets/latest/us_ofac_sdn/entities.ftm.json&dest=raw/opensanctions/us_ofac_sdn.ftm.json"
curl -X POST -H "Authorization: Bearer $TOK" "$URL/ingest?source=opensanctions"
curl -X POST -H "Authorization: Bearer $TOK" "$URL/build?what=company"
curl -X POST -H "Authorization: Bearer $TOK" "$URL/match?what=company"
curl -X POST -H "Authorization: Bearer $TOK" "$URL/publish?what=company"
```

### Reproducing the benchmarks

Every report in the § Reports & benchmarks table has a corresponding
GitHub Actions workflow that runs the build on Railway and commits the
refreshed report back to `main`. To regenerate any single report:

```bash
gh workflow run build-discovery-advantage.yml
gh workflow run build-top-candidates-walkthrough.yml
gh workflow run build-structure-benchmark.yml
gh workflow run build-confidence-graph.yml
gh workflow run build-calibration-benchmark.yml
gh workflow run build-adversarial-benchmark.yml
gh workflow run build-discovery-lift.yml
gh workflow run build-baseline-comparison.yml
gh workflow run build-non-obviousness.yml
gh workflow run build-latent-clusters.yml
gh workflow run build-temporal-patterns.yml
gh workflow run build-exposes-candidates.yml
```

Each workflow polls the Railway job to completion, downloads the
artefact, renders the markdown, and commits with `git pull --rebase`
before pushing to avoid the concurrent-workflow race.

Full ICIJ + OpenSanctions dedupe at this scale fits in ~3 GB and runs
in ~1 minute. The ICIJ+OS → GLEIF list-match runs in ~10 minutes on
the default Railway Pro service (24 vCPU / 24 GB). Full pairwise
dedupe over ICIJ + GLEIF + OpenSanctions (4.1M rows) does **not** fit
at 24 GB — list-match is the supported shape at this scale.

## Directory layout

```
.github/workflows/  CI + Railway-triggered benchmark builds (build-*.yml)
configs/            GoldenMatch YAMLs + source manifests
data/               Raw / interim / processed / sample data (mostly git-ignored)
docs/               Source descriptions, methodology, roadmap
  docs/paper/       Methodology paper
  docs/reports/     Generated benchmark reports (committed)
notebooks/          Exploratory notebooks (case studies)
reports/            Per-seed investigation writeups
scripts/            Thin Typer CLIs that wrap library code
  scripts/build_*.py    Benchmark builders (run on Railway)
  scripts/render_*.py   Markdown renderers (run on GH Actions)
src/shellnet/       Library code: schemas, normalization, source adapters, matching, graph
tests/              Pytest suite + tiny synthetic fixtures
Dockerfile          Container image for the Railway job service
railway.json        Railway deploy config (healthcheck path, restart policy)
```

## Status

**v1.0** (case-study deliverable) — Phases 0–6 shipped: ingest, unified
tables, matching + eval, address + person tables, graph analysis, two
case-study writeups with full provenance.

**Since v1.0** (benchmark-pipeline extensions, all generated on
Railway and reproducible via GH Actions):

- **Discovery Advantage Report** — single-artifact synthesis of every
  baseline-vs-pipeline measurement
  ([`build_discovery_advantage`](scripts/build_discovery_advantage.py))
- **Top-candidates walkthrough** — per-entity novelty proofs across 5
  surfacing channels
  ([`build_top_candidates_walkthrough`](scripts/build_top_candidates_walkthrough.py))
- **Discovery lift** — B1→B4 tier funnel
  ([`build_discovery_lift`](scripts/build_discovery_lift.py))
- **Baseline comparison** — ICIJ-search vs cross-source recall +
  analyst-hour model
  ([`build_baseline_comparison`](scripts/build_baseline_comparison.py))
- **Adversarial benchmark** — recovery against 4 perturbation classes
  ([`build_adversarial_benchmark`](scripts/build_adversarial_benchmark.py))
- **PAV calibration** — Brier / ECE / log-loss before vs after isotonic
  regression
  ([`build_calibration_benchmark`](scripts/build_calibration_benchmark.py))
- **Structure benchmark** — 6 non-obvious structural patterns
  ([`build_structure_benchmark`](scripts/build_structure_benchmark.py))
- **Non-obviousness scoring** — 5-factor per-anchor composite
  ([`build_non_obviousness`](scripts/build_non_obviousness.py))
- **Latent-cluster mining** — Louvain communities + anomaly scoring on
  ICIJ corpus
  ([`build_latent_clusters`](scripts/build_latent_clusters.py))
- **Temporal patterns** — address-officer resurrections, incorporation
  bursts, long-lived anchors
  ([`build_temporal_patterns`](scripts/build_temporal_patterns.py))
- **Confidence-aware graph** — credibility-weighted communities with
  multi-hop decay, contradiction-aware closure, review-priority
  ranking
  ([`build_confidence_graph`](scripts/build_confidence_graph.py))
- **Methodology paper** — formal writeup of the matcher, calibration,
  graph reasoning, and benchmark methodology
  ([`docs/paper/methodology.md`](docs/paper/methodology.md))

Items still parked (see [`docs/status.md`](docs/status.md) for the
canonical list):

- **Journalist panel-review study** — the v2 gap documented in
  `discovery_advantage.md` §"Analyst review outcomes". Surfaced
  candidates have no human-confirmed novelty label.
- **OpenCorporates ingest** — adapter ready, blocked on API key +
  curated seed list.
- **Probabilistic matchkey + `negative_evidence`** — labels exist;
  blocked on an upstream goldenmatch polars schema bug.
- **GLEIF Golden Copy XML / ZIP** — JSON / JSONL parsing is live; XML
  + ZIP raise `NotImplementedError`.
- **Provenance-weighted edge priors** — current credibility priors are
  per-`kind_raw`; a v2 would calibrate against the labelled marginal-
  pair review set.

## Configuration

Secrets live in `.env` (see `.env.example`):

- `OPENCORPORATES_API_KEY` (optional)
- `SHELLNET_JOB_TOKEN` (required for Railway control-plane endpoints)
- `SHELLNET_JOB_URL` (your Railway domain; also stored as a GH repo
  variable for the build-* workflows)
- `DATABASE_URL` (Postgres connection string for run / cluster / pair
  persistence)

## Legal & ethical

- This project is research code released under the MIT licence.
- The **datasets** it ingests are governed by their own licences and
  terms of use. Read them before redistributing anything you derive.
- Do not publish identity-linked claims about specific people or
  companies without independent review.
- Discovery-advantage numbers are measured against operational
  baselines, not against journalist-confirmed exposés. See
  [`discovery_advantage.md`](docs/reports/discovery_advantage.md)
  §"Analyst review outcomes" for the explicit v2 gap.
- Do not scrape OpenCorporates aggressively. Use the API, set a key,
  respect the rate limits.
