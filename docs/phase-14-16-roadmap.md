# Phases 14-16: performance, GoldenMatch leverage, bridge-endpoint seeding

Three follow-ups after the Phases 11-13 + bridge tuning runs. Most
recent end-to-end recluster (max_nodes=30000, hops=3,
min_frontier_degree_deep=1):

| Metric | Value |
|---|---:|
| Subgraph nodes | 29,888 (cap fully binding) |
| Subgraph edges | 67,513 |
| `cross_jurisdictional_twin` edges | 111 |
| `same_company_as` edges | 10 (**one bridge landed**) |
| `beneficial_owner_of` edges | **0** |

The single `same_company_as` increment confirms the bridge mechanism
finally works topologically. The zero `beneficial_owner_of` count
means SEC-to-SEC ownership edges still aren't reached because they
sit one hop past the bridge — outside the 3-hop BFS budget.

Order to ship: **16 → 14 → 15**. 16 is small and unlocks the actual
discovery payoff. 14 unblocks bigger subgraphs without OOM. 15 is
the long-term quality and calibration upgrade.

---

## Phase 16 — pre-seed SEC bridge endpoints

**Why first:** Smallest change with the highest immediate payoff.
With the bridge already proven to enter at hop 3, putting its SEC
endpoints into the seed set at hop 0 gives the BFS three full hops
to walk the SEC corpus from each bridge landing site.

### Files

**New:** `scripts/select_bridge_endpoints.py`

Reads `sec_icij_bridges.parquet`, projects the `src_uid` column
(SEC side, `sec:CIK`) to a single-column `uid` parquet matching the
`--extra-seeds` schema Phase 11 already accepts. ~20 lines.

```python
def select(bridges: pl.DataFrame) -> pl.DataFrame:
    """Return DataFrame with columns: uid, source ('sec_bridge')."""
    return (
        bridges.select(pl.col("src_uid").alias("uid"))
        .unique()
        .with_columns(pl.lit("sec_bridge").alias("source"))
    )
```

CLI defaults: `--bridges /data/processed/sec_icij_bridges.parquet
--out /data/processed/bridge_endpoint_seeds.parquet`.

**Modified:** `scripts/build_confidence_graph.py`

`--extra-seeds` already accepts one parquet. Two options:
* Quick: change the allowlist entry to point at a concatenated
  parquet built by a small helper that unions `anomaly_seed_uids`
  + `bridge_endpoint_seeds`.
* Clean: turn `--extra-seeds` into a `nargs="+"` so multiple parquets
  union. Backwards-compatible if we keep accepting a single value.

Go with the clean option — it scales for Phase 17+ seed sources
without proliferating concat scripts.

### Allowlist + workflow

```python
"select_bridge_endpoints": [
    "scripts/select_bridge_endpoints.py",
    "--bridges",
    "/data/processed/sec_icij_bridges.parquet",
    "--out",
    "/data/processed/bridge_endpoint_seeds.parquet",
],
```

Update `build_confidence_graph_expanded` allowlist entry to pass
both parquets via the new multi-value flag.

New workflow `.github/workflows/select-bridge-endpoints.yml` —
mirror of Phase 11's. Runs in ~30 seconds.

### Tests

`tests/test_select_bridge_endpoints.py`:
* `test_emits_one_row_per_unique_sec_cik` — duplicate bridges to
  same SEC entity surface once.
* `test_uid_column_matches_extra_seeds_schema` — single `uid` column,
  string type.
* `test_empty_bridges_parquet_returns_empty` — graceful when
  Phase 10 produced zero matches.

### Acceptance

| Metric | Threshold |
|---|---:|
| `bridge_endpoint_seeds.parquet` row count | ≥ 25 (we have 30 bridges; some may dedup) |
| Recluster subgraph: `beneficial_owner_of` edges | **≥ 1** (the load-bearing fix) |
| `same_company_as` edges in subgraph | ≥ 20 (was 10; bridges now reachable from both sides) |

### Risks

* **Bridge endpoints flood the subgraph with SEC nodes.** Many SEC
  filers are large public funds (Royal Bank of Canada, Apollo) with
  thousands of beneficial-ownership edges. The 30k max-nodes cap
  could saturate on SEC nodes and starve the dossier-anchored core.
  Mitigation: add an `--extra-seeds-budget` flag that caps how many
  extra-seed neighbours can enter at each hop.

### Effort
1-2 hours: 30 min script + 30 min multi-value flag refactor + tests
+ 30 min Railway dispatch + verify.

---

## Phase 14 — kill the polars perf cliff in `_build_subgraph`

**Why:** Three concrete perf bugs in the BFS make max-nodes ≥ 50k
unrunnable today. Fixing them unlocks 100k+ node subgraphs without
OOM and cuts runtime even at current sizes.

### The three bugs

1. **`pl.col("src_node").is_in(list(frontier))` is linear-scan per
   row.** Polars treats a Python list as a literal array and scans
   it for every row of the 3.3M-edge frame. At 50k frontier UIDs,
   each hop becomes effectively O(edges × frontier_size).

2. **`set` ↔ `list` ↔ polars conversions per hop.** Each iteration
   materializes a Python list from a set, passes it across the
   pyo3 boundary, then `.to_list()`s the result back. ~3
   round-trips per hop.

3. **`.collect()` calls force eager materialization at scale.** The
   OO PSC entities frame (5.79M rows) goes through `.collect()`
   inside `build_name_index` before any filter, materializing 5
   string columns × 5.79M rows.

### Fixes

#### 14a — semi-join replaces `is_in(list)`

```python
# Before (slow):
adjacent = edges.filter(
    pl.col("src_node").is_in(list(frontier))
    | pl.col("dst_node").is_in(list(frontier))
)

# After (hash semi-join, scales linearly in min(edges, |frontier|)):
frontier_df = pl.DataFrame({"node": list(frontier)})
adj_src = edges.join(
    frontier_df.rename({"node": "src_node"}),
    on="src_node", how="semi",
)
adj_dst = edges.join(
    frontier_df.rename({"node": "dst_node"}),
    on="dst_node", how="semi",
)
adjacent = pl.concat([adj_src, adj_dst]).unique()
```

Expected speedup at 50k frontier: 20-100x.

#### 14b — frontier/visited as a single-column DataFrame

Keep `frontier_df: pl.DataFrame` (one column, `node`) instead of
Python sets. Set-difference becomes anti-join; union becomes vertical
concat + unique. No more PyO3 round-trips per hop.

#### 14c — lazy-collect the OO PSC entities

`build_name_index` should accept `pl.LazyFrame | pl.DataFrame` and
keep lazy until the final select. The caller passes
`pl.scan_parquet(p)` and collects only at the end of `detect_twins`
after both sides are filtered.

### Files

Touch:
* `scripts/build_confidence_graph.py` (14a, 14b)
* `scripts/detect_cross_jurisdiction_twins.py` (14c)
* `scripts/bridge_sec_icij_by_name.py` (14c)

### Tests

* `test_subgraph_no_python_is_in_list` — code-grep guard that the
  semi-join is used.
* `test_subgraph_correctness_unchanged` — old vs new
  implementation produce identical subgraphs on a 5k-row synthetic
  graph.
* `test_50k_frontier_completes_under_30s` — perf regression
  guard. Generates a 50k-node synthetic graph + 50k frontier,
  asserts the BFS finishes under 30s.

### Acceptance

| Metric | Threshold |
|---|---:|
| Recluster at max_nodes=50000, hops=3 completes | yes |
| Wall-clock runtime at max_nodes=30000 | ≤ 5 min (currently ~10) |
| Perf-regression test stays under 30s | yes |
| Existing report metrics unchanged at max_nodes=30000 | within ±5% on all counts |

### Risks

* **Behavioural drift.** The semi-join + anti-join refactor changes
  iteration order; communities may differ at the margin. Acceptance
  test #4 catches this — keep tolerances tight.
* **Lazy collect masks errors.** A schema mismatch in `oo_uk_psc_*`
  parquets only surfaces at `.collect()`. The Phase 0 BODS-v0.4
  schema fix is a recent example. Mitigation: log the schema right
  after `scan_parquet` so failures are diagnosable.

### Effort
3-4 hours. The 14a refactor + tests is the bulk. 14b is mechanical.
14c needs to flow through detect_twins + bridge build.

---

## Phase 15 — route ER workloads through the GoldenMatch SDK

**Why:** We're shipping with the `goldenmatch` Python package
installed at `.venv/Lib/site-packages/goldenmatch/` and using ~5%
of it. The SDK has:

* `ann_blocker` — approximate-nearest-neighbour candidate generation
* `cross_encoder` — calibrated pair scoring
* `cluster` — entity resolution
* `graph_er` — network-aware ER
* `boost`, `canopy`, `blocker`, `anomaly`
* DuckDB + Ray backends; `chunked`, `gpu`
* Domain configs (financial, people)

Three workloads in this repo were built from scratch and would land
on better calibrated, faster ground if routed through the SDK.

### 15a — Phase 3 twin detector → ANN blocker + cluster

**Today:** exact normalized-name + abbreviation regex + frequency-cap
heuristic.

**Tomorrow:** ANN-blocker generates the candidate set with embedding
similarity; `cluster` resolves the candidates with calibrated
probabilities; output keeps the same `cross_jurisdiction_twins.parquet`
schema but with a per-pair probability instead of the hand-set 0.85
credibility.

Effect on credibility graph: `cross_jurisdictional_twin` edges
become per-edge weighted, not flat 0.85. Better
threshold-stability analysis downstream.

### 15b — Phase 10 SEC↔ICIJ bridge → cross_encoder

**Today:** exact normalized-name match with multi-token gate.

**Tomorrow:** `cross_encoder` scores each (sec_filer, icij_entity)
pair with a calibrated probability. Output is the same
`sec_icij_bridges.parquet` shape plus a `prob` column. Bridge
credibility becomes a per-row product of (kind_cred 0.85) ×
(prob), so high-confidence bridges (Royal Bank of Canada, exact
multi-token match + jurisdiction agreement) land near 0.85, while
weaker matches stay below threshold.

### 15c — `build_confidence_graph` Louvain → `graph_er`

**Today:** networkx Louvain on a weighted graph.

**Tomorrow:** `goldenmatch.core.graph_er` purpose-built for
network-aware ER. Probably faster on the 30k-node subgraphs;
threshold-stability semantics may change.

### Files

* `src/shellnet/matching/goldenmatch_runner.py` — currently a
  one-function table-loader. Expand into the canonical entry point
  for `ann_blocker`, `cross_encoder`, `cluster`, `graph_er`.
* `scripts/detect_cross_jurisdiction_twins.py` — replace the
  bespoke join logic with a `goldenmatch_runner.match_companies`
  call.
* `scripts/bridge_sec_icij_by_name.py` — same.
* `scripts/build_confidence_graph.py` — swap Louvain for `graph_er`
  behind a flag so we can compare partitions side-by-side.

### Tests

* `tests/test_goldenmatch_runner.py` — smoke that each entry point
  loads and returns the expected dataclass shape on a 50-row fixture.
* Per-script integration tests stay; they assert against the new
  output parquet shapes.

### Acceptance

| Metric | Threshold |
|---|---:|
| `cross_jurisdiction_twins.parquet` gains a `prob` column with values in [0, 1] | yes |
| Twin probability distribution shows a discriminative split (not just 0.5/1.0) | yes — at least 3 bands |
| `sec_icij_bridges.parquet` gains a `prob` column | yes |
| Louvain vs graph_er partition agreement (NMI) | ≥ 0.7 (sanity bound; below = investigate) |
| Recluster runtime at hops=3 / max_nodes=30000 | ≤ current 10 min |

### Risks

* **Calibration shifts cluster membership.** The current credibility
  priors are operator-set; per-edge calibrated probabilities will
  produce different communities. Document both the pre- and post-
  switch reports as separate artefacts; don't overwrite the
  baseline.
* **GoldenMatch SDK has its own perf cliffs at corpus scale.** Phase
  3's OOM at 5.79M rows happened with our hand-rolled code; the SDK
  has `chunked` + `gpu` backends but they need configuring. Test on
  small subsets first.
* **Ray backend in the SDK changes the deployment shape.** If
  `graph_er` defaults to Ray, Railway-side container needs Ray
  installed and a head-node config. DuckDB backend is the safer
  default for shellnet-job.

### Effort
1-2 days. 15a alone is a half-day with tests; 15b another half;
15c is the larger of the three because of the side-by-side
comparison machinery.

---

## Out of scope (for now)

* **Switch from polars to DuckDB across the pipeline.** GoldenMatch's
  DuckDB backend is interoperable, but ripping out polars from
  every script is a much bigger rewrite. Defer until a perf reason
  forces the choice.
* **GPU acceleration via `goldenmatch.core.gpu`.** Railway shellnet-
  job is CPU-only today. Not worth provisioning a GPU container
  until 15a/b/c are calibrated and benchmarked on CPU.
* **Re-doing Phases 1, 2, 4, 5, 7, 11 through the SDK.** Those phases
  don't have ER-matcher workloads. 14 + 15 cover the ER pieces;
  the rest of the pipeline stays as-is.

## Recommended order

**16 → 14 → 15.** Phase 16 is a half-day change that finally lands
`beneficial_owner_of` edges in the subgraph (the metric we've been
chasing). Phase 14 unblocks bigger subgraphs without OOM and cuts
existing runtimes. Phase 15 is the quality + calibration upgrade
that should land once Phase 16's payoff is locked in and Phase 14's
perf ceiling is raised.

If only one ships: **Phase 16.** It's the only one with a directly
testable acceptance metric (`beneficial_owner_of` count > 0 in the
report) and we already know it'll work because hop 1-3 will reach
the SEC-SEC edges once SEC nodes are in the seed set at hop 0.
