# Non-obvious investigative structure benchmark

_Generated 2026-05-17 21:30 UTC from `processed/structure_benchmark_summary.json`._

## What this measures

Earlier benchmarks (`discovery_lift.md`, `non_obviousness_ranking.md`)
quantified how many **entities** or **per-anchor scores** the pipeline
surfaces vs simpler baselines. This benchmark steps up to the next
level: **structural patterns** that are visible *only* when you can
aggregate across entities, edges, and overlay datasets — the kind of
thing ICIJ's per-entity search or naive degree-rank cannot produce
even with unlimited time.

Six structure types, each defined operationally below. The count
column is the **lower-bound number of distinct instances the
pipeline detects** under the conservative threshold for that type.

## Headline counts

| ID | Structure | Detected by pipeline | Reachable via ICIJ search alone |
|---|---|---:|:---:|
| S1 | Latent intermediary reuse | **126** | ✗ |
| S2 | Unexpected jurisdiction bridges | **99** | ✗ |
| S3 | Hidden registry anchors (ICIJ ↔ GLEIF) | **19,934** | ✗ |
| S4 | Sanctions-adjacent community closure | **25** | ✗ |
| S5 | Fragmented ownership convergence | **2,010** | ✗ |
| S6 | Anomalous community structures (top-50) | **50** | ✗ |

| | **Total pipeline structures** | **22,244** | |

All six "ICIJ-search alone" cells are ✗ by construction. ICIJ Offshore
Leaks DB doesn't compute these aggregations — it's a per-record search
index. The structural signal is not "ICIJ search misses some entities";
it's "ICIJ search cannot answer these structural questions at all."

## Per-structure detail

### Latent intermediary reuse

**Detected: 126**

_Baseline reachability:_ ICIJ DB shows intermediary records but does not aggregate per-client distinctness in batch.

_Definition:_ ICIJ intermediaries (`intermediary_of` target) linked to ≥3 distinct officers.

Top intermediaries by client count:

| Intermediary UID | Distinct clients |
|---|---:|
| `icij:101300076` | 5 |
| `icij:82019585` | 4 |
| `icij:101300442` | 4 |
| `icij:101300337` | 4 |
| `icij:101300690` | 4 |

### Unexpected jurisdiction bridges

**Detected: 99**

_Baseline reachability:_ Cross-entity bridges require joining officer-of edges across companies; ICIJ DB cannot compute that.

_Definition:_ company pairs sharing an officer where one company is in a high-risk offshore jurisdiction ({vg, ky, bm, pa, bs, ai, tc, vc, ms, im, je, gg, cy}) and the other is in a mainstream OECD venue ({gb, us, fr, de, nl, ch, lu, ie, se, no, fi, dk, ca, au, jp}).

Sample bridges:

| Company A | Juris A | Company B | Juris B |
|---|---|---|---|
| `icij:82002777` | us | `icij:82022446` | ky |
| `icij:82000231` | bm | `icij:82001775` | us |
| `icij:82007452` | bm | `icij:82014151` | us |
| `icij:82002744` | us | `icij:82005296` | bm |
| `icij:82003067` | bm | `icij:82014150` | us |

### Hidden registry anchors (ICIJ ↔ GLEIF)

**Detected: 19,934**

_Baseline reachability:_ ICIJ DB has no GLEIF integration. 0% reachable from ICIJ search alone.

_Definition:_ ICIJ entities that match a GLEIF LEI but carry no sanctions-list flag. Formal-registry presence without disclosure trigger.

- Distinct ICIJ uids: **19,934**
- Distinct LEIs: **10,157**

Top hidden anchors:

| ICIJ name | Juris | GLEIF name | LEI |
|---|---|---|---|
| BOUMA CORPORATION LTD | ky | Bouma Corporporation Ltd | `254900Q808X0MEWHIG67` |
| Atrium XI | ky | Atrium XI | `549300TGINJQCXBCLS76` |
| Atrium X | ky | Atrium X | `254900BPA69DOSW60885` |
| Atrium X Trust | ky | Atrium X | `254900BPA69DOSW60885` |
| ROCK ENTERPRISES LIMITED | mt | Rock Enterprises Limited | `485100O56SYJ99TTKV40` |

### Sanctions-adjacent community closure

**Detected: 25**

_Baseline reachability:_ Per-entity records don't flag sanctions; community-level closure requires both layers.

_Definition:_ latent-cluster communities (from `latent_clusters.parquet`) containing ≥1 entity whose normalized name matches a sanctions-overlay alias.

Top sanctions-adjacent communities:

| Community | Size | Jurisdictions | Sanctioned | Anomaly |
|---:|---:|---|---:|---:|
| 2762 | 173 | hk;mt;vg | 1 | 0.420 |
| 2125 | 1771 | ae;ch;gb;hk;us;vg | 3 | 0.394 |
| 3401 | 4014 | cy;hk;mt;nz;uk;uy;vg | 5 | 0.393 |
| 954 | 29 | mt;vg | 2 | 0.344 |
| 3841 | 3356 | ae;ai;bm;bs;bz;cy;gg;hk;im;je;ky;mt;pa;sg;vg;xx | 4 | 0.340 |

### Fragmented ownership convergence

**Detected: 2,010**

_Baseline reachability:_ Per-address listings exist on ICIJ DB but officer-distinctness across hosted entities isn't surfaced.

_Definition:_ addresses hosting between 3 and 10 entities (not formation-agent hubs), where ≥3 distinct officers appear across the hosted companies.

Top addresses:

| Address | Companies | Distinct officers |
|---|---:|---:|
| `fortenberry corporate services ltd 519 st james court st denis street port louis` | 6 | 470 |
| `lic luis fernando herrera toledo legal center 6 avenida 20 25 zona 10 ciudad de ` | 9 | 159 |
| `cr pablo cataumbert colonia 981 piso 8 montevideo uruguay` | 3 | 124 |
| `mesoamerica plaza roble edificio el portico piso 2 escazu costa rica` | 9 | 121 |
| `evgeny l andreev 5 bakunina prospect saint petersburg 191024 saint petersburg ru` | 4 | 120 |

### Anomalous community structures (top-50)

**Detected: 50**

_Baseline reachability:_ Communities are not a concept in ICIJ DB.

_Definition:_ top-50 from `latent_clusters.parquet` by anomaly score (computed without seed bias on the full ICIJ corpus).

- Median size: **61**
- Max anomaly score: **0.454**

Top 5:

| Community | Size | Jurisdictions | Sanctioned | Anomaly |
|---:|---:|---|---:|---:|
| 1878 | 78 | pa;us;vg | 0 | 0.454 |
| 377 | 115 | cy;vg | 0 | 0.444 |
| 3557 | 107 | hk;vg | 0 | 0.440 |
| 308 | 64 | uk;vg | 0 | 0.426 |
| 2762 | 173 | hk;mt;vg | 1 | 0.420 |



## Honest reading

- **Counts are lower bounds.** Thresholds are conservative (`min_clients ≥ 3`,
  `min_distinct_officers ≥ 3`, etc.); loosening them would surface more
  instances but with lower investigative-relevance density. We err on the
  side of fewer-but-cleaner.
- **Baseline ✗ is structural, not throughput.** ICIJ search would return the
  individual entities; what it can't do is compute the structural
  aggregation. A human could in principle assemble the structures manually
  by typing 50 queries per anchor and tallying — that's the analyst-time
  baseline quantified in `baseline_comparison.md` (×2.7 speedup).
- **Some structures depend on prior pipeline outputs.** S4 and S6 require
  `latent_clusters.parquet`; S3 requires the GLEIF match file. The
  benchmark is a meta-result on top of the rest of the pipeline.
- **No human ground truth.** "Non-obvious" is operationalised as
  "produced by the pipeline AND structurally invisible to single-source
  search," not as "a journalist confirmed it's interesting." A v2 would
  send the top-N from each structure to a panel.

## Reproduce

```bash
just job-run build_structure_benchmark
just job-fetch processed/structure_benchmark_summary.json docs/reports/data/

uv run python scripts/render_structure_benchmark.py \
    --summary docs/reports/data/structure_benchmark_summary.json \
    --out docs/reports/structure_benchmark.md
```

Or trigger `.github/workflows/build-structure-benchmark.yml`.
