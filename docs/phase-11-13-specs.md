# Phases 11-13: implementation specs

Companion to `phase-11-13-bridge-reach-roadmap.md`. The roadmap
explains *why*; this doc is the *how* — exact files, signatures,
schemas, allowlist entries, tests, acceptance numbers.

Conventions:
- Paths starting with `/data/` are Railway-volume paths (run-time).
- Paths starting with `scripts/`, `src/`, `tests/` are repo-relative.
- "TDD step" prefixes a test to write *before* the implementation.

---

## Phase 11 — broaden seed set with top-N anomaly communities

### Files

**New:** `scripts/select_anomaly_seeds.py`

```python
"""Select cluster-member UIDs from the top-N anomaly-ranked communities.

Reads ``confidence_community_anomalies.parquet`` (produced by the
recluster job), picks the N highest-anomaly communities, and emits a
parquet of their member UIDs for use as extra seeds in the next
recluster pass.
"""

import argparse
from pathlib import Path
import polars as pl

def select(
    anomalies_path: Path,
    communities_path: Path,
    *,
    top_n: int = 10,
    min_anomaly_score: float = 0.5,
) -> pl.DataFrame:
    """Returns DataFrame with one column: uid (str)."""
    anomalies = pl.read_parquet(anomalies_path)
    top = (
        anomalies
        .filter(pl.col("anomaly_score") >= min_anomaly_score)
        .sort("anomaly_score", descending=True)
        .head(top_n)
    )
    top_community_ids = top["community_id"].to_list()

    communities = pl.read_parquet(communities_path)
    return (
        communities
        .filter(pl.col("community_id").is_in(top_community_ids))
        .select(pl.col("uid"))
        .unique()
    )
```

CLI:
```
uv run python scripts/select_anomaly_seeds.py \
    --anomalies /data/processed/confidence_community_anomalies.parquet \
    --communities /data/processed/confidence_communities.parquet \
    --top-n 10 \
    --out /data/processed/anomaly_seed_uids.parquet
```

Output schema: single column `uid: str`. Expected size: 200-800 UIDs
(top-10 communities × ~20-80 members each).

**Modified:** `scripts/build_confidence_graph.py`

Add a typer.Option:
```python
extra_seeds_parquet: Path | None = typer.Option(
    None,
    "--extra-seeds",
    help=(
        "Optional parquet with a single 'uid' column. Members added to "
        "the seed set BEFORE the BFS expansion, so their 2-hop "
        "neighbourhoods enter the subgraph alongside the dossier set."
    ),
),
```

Plumbing:
```python
seeds = set(seed_person_uids) | set(seed_company_uids)
if extra_seeds_parquet and extra_seeds_parquet.exists():
    extra = pl.read_parquet(extra_seeds_parquet)["uid"].to_list()
    log.info("loaded %d extra seed UIDs from %s", len(extra), extra_seeds_parquet)
    seeds |= set(extra)
```

Also raise the default `--max-nodes` from 8,000 → 16,000 since the
expanded seed set will push the BFS closer to the cap.

**New:** `tests/test_select_anomaly_seeds.py`
- `test_picks_top_n_by_anomaly_score` — fixture with 5 communities,
  N=2, verify selection by score.
- `test_min_anomaly_score_filter` — communities below threshold dropped.
- `test_returns_unique_uids` — same UID in two top communities
  appears once in output.
- `test_empty_when_no_communities_meet_threshold` — returns empty df
  with correct schema, doesn't crash.

**New:** `tests/test_build_confidence_graph_extra_seeds.py`
- `test_extra_seeds_expand_subgraph` — synthetic dossier set of 1
  node, extra-seeds of 5 nodes. Subgraph should include 2-hop
  neighbourhoods of all 6.

### Allowlist entries

`src/shellnet/job_server.py`:

```python
"select_anomaly_seeds": [
    "scripts/select_anomaly_seeds.py",
    "--anomalies",
    "/data/processed/confidence_community_anomalies.parquet",
    "--communities",
    "/data/processed/confidence_communities.parquet",
    "--top-n",
    "10",
    "--out",
    "/data/processed/anomaly_seed_uids.parquet",
],
```

Update `build_confidence_graph_expanded` entry to pass:
```
"--extra-seeds",
"/data/processed/anomaly_seed_uids.parquet",
"--max-nodes",
"16000",
```

### Workflow

`.github/workflows/select-anomaly-seeds.yml` — mirror of the
existing single-script dispatch workflows (`detect-cross-...`,
`bridge-sec-icij-...`). Runs in ~1 min on Railway.

### Acceptance numbers

| Metric | Threshold |
|---|---:|
| `anomaly_seed_uids.parquet` row count | ≥ 100, ≤ 2,000 |
| Recluster subgraph node count | grows from 7,888 → ≥ 12,000 |
| `beneficial_owner_of` edges in subgraph | ≥ 1 (proves reach) |
| At least one of {Royal Bank of Canada, Transocean Intl, CVI Investments} appears in subgraph | yes |
| Communities @ threshold 0.7 | within 50-200 range (sanity bound) |

### Risks + fallbacks

- **Anomaly-ranked seeds dilute the existing signal.** Mitigation: add
  a `seed_source` column to the output communities parquet
  (`dossier`, `anomaly`, or `both`) so the reviewer can filter to
  "communities anchored by ≥ 1 dossier seed" downstream.
- **Top-10 anomaly communities are themselves the new "noise".** If
  the report shows the new communities are all 3-node oddities, drop
  to top-5 or raise `--min-anomaly-score` to 0.7.

### Estimated effort
1-2 hours: 1 hour write + tests, 30 min Railway dispatch + verify.

---

## Phase 12 — BFS depth 2 → 3 hops with per-hop pruning

### Files

**Modified:** `scripts/build_confidence_graph.py`

`_build_subgraph` already accepts `hops` as a parameter — just expose
it via the existing `--hops` flag (already exposed) but add a
**per-hop frontier pruning step** to bound growth:

```python
def _build_subgraph(
    edges: pl.DataFrame,
    seed_uids: set[str],
    hops: int = 2,
    max_nodes: int = 16000,
    min_frontier_degree: int = 1,  # NEW
) -> pl.DataFrame:
    """...

    Per-hop pruning: when adding the hop-N frontier, drop candidate
    nodes whose degree-in-the-current-visited-set is below
    ``min_frontier_degree``. For hops <= 2 we keep min=1 (current
    behaviour); for hops >= 3 we tighten to min=2 so the extra hop
    only adds nodes that actually bridge multiple existing entities,
    not random one-degree leaves.
    """
```

Implementation sketch inside the BFS loop:
```python
for hop_i in range(hops):
    ...
    # Existing frontier expansion produces `next_frontier`.
    if hop_i >= 2:  # only tighten past hop 2
        # Count how many existing visited nodes each candidate connects to.
        adj_counts = (
            adjacent
            .filter(pl.col("src_node").is_in(list(next_frontier)) | pl.col("dst_node").is_in(list(next_frontier)))
            .with_columns(
                pl.when(pl.col("src_node").is_in(list(next_frontier)))
                  .then(pl.col("src_node"))
                  .otherwise(pl.col("dst_node"))
                  .alias("candidate")
            )
            .group_by("candidate").len()
            .filter(pl.col("len") >= min_frontier_degree)
        )
        next_frontier &= set(adj_counts["candidate"].to_list())
    ...
```

Expose two new flags:
```python
hops: int = typer.Option(2, "--hops"),  # already exists
min_frontier_degree_deep: int = typer.Option(
    2, "--min-frontier-degree-deep",
    help="Past hop 2, only add candidates with this many edges into the visited set.",
),
```

**Modified tests:** `tests/test_build_confidence_graph_oo_merge.py`
- `test_hops_3_with_pruning_bounds_size` — synthetic 200-node graph
  with one well-connected hub. Verify that hops=3 + pruning produces
  fewer than 2x the hops=2 node count.

### Allowlist update

Update `build_confidence_graph_expanded` to pass `--hops 3`.

### Acceptance numbers

| Metric | Threshold |
|---|---:|
| Recluster runtime | ≤ 15 min (workflow timeout is 60 min) |
| Subgraph node count | ≤ max_nodes (16,000 cap) |
| Mean Jaccard stability (0.5 vs 0.9) | ≥ 0.04 (currently 0.072; degradation expected, but bounded) |
| ≥ 1 `beneficial_owner_of` edge in subgraph | yes |
| `cross_jurisdictional_twin` edges in subgraph | ≥ 61 (current — must not regress) |

### Risks + fallbacks

- **Louvain runtime balloons** on the larger graph. The current
  recluster is ~3-4 min Railway-side; expect 8-12 min with hops=3.
  If > 15 min, raise the workflow timeout OR fall back to hops=2 +
  Phase 11.
- **Threshold-stability metric degrades** because larger subgraphs
  fragment more at strict thresholds. Document this in the report's
  methodology section ("hops=3 expansion deliberately trades
  stability for reach; the headline result is the ≥1
  `beneficial_owner_of` edge").

### Estimated effort
2-3 hours: 1.5h script change + tests, 1h Railway runtime measurement
+ tune `--min-frontier-degree-deep`.

---

## Phase 13 — ingest 4 SEC quarters instead of 1

### Files

**Modified:** `scripts/ingest_sec_13dg_bulk.py`

Add a `main_loop` that iterates over a (year, quarter) list and
concatenates results:

```python
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--year-quarter",
        type=str,
        nargs="+",
        required=True,
        help=(
            "One or more year/quarter pairs to ingest, e.g. "
            "'--year-quarter 2025/1 2025/2 2025/3 2025/4'. The script "
            "iterates them and concatenates the results into --out."
        ),
    )
    # ... remove old --year / --quarter args
    # ... keep --out, --limit, --user-agent
```

Loop body:
```python
all_edges: list[Filing13DGEdge] = []
for yq in args.year_quarter:
    year_s, quarter_s = yq.split("/")
    year, quarter = int(year_s), int(quarter_s)
    log.info("fetching form.idx for %d Q%d", year, quarter)
    idx_text = fetch_idx(year, quarter)
    entries = parse_form_idx(idx_text)
    if args.limit:
        entries = entries[: args.limit]
    edges = build_edges(entries, fetch_filing)
    log.info("  -> %d edges from %d Q%d", len(edges), year, quarter)
    all_edges.extend(edges)
edges_to_parquet(all_edges, args.out)
```

**Backwards compatibility:** keep the old `--year` / `--quarter` flags
as a deprecated shim that maps to `--year-quarter <year>/<quarter>`.
Marks the old flags with `help=argparse.SUPPRESS` so they don't show
up in `--help` but existing callers still work.

### Tests

`tests/test_ingest_sec_13dg_bulk.py` additions:
- `test_year_quarter_multi_arg_parses` — `--year-quarter 2025/1 2025/2`
  produces 2 calls to a mock `fetch_idx`.
- `test_year_quarter_results_concatenate` — both quarters' edges
  appear in the final parquet, deduped by accession.
- `test_old_year_quarter_flags_still_work` — backwards compat.

### Allowlist update

```python
"ingest_sec_13dg_bulk": [
    "scripts/ingest_sec_13dg_bulk.py",
    "--year-quarter",
    "2025/1", "2025/2", "2025/3", "2025/4",
    "--out",
    "/data/processed/sec_13dg_edges.parquet",
    "--limit",
    "5000",
    "--user-agent",
    "Ben Severn bsevern@mjhlifesciences.com",
],
```

Note: `--limit` applies per-quarter, not total. With 4 quarters × 5000
= 20,000 max filings. At 9 req/s rate-limited, that's ~37 min upload-
side + per-filing parse time. Workflow timeout (45 min) needs a bump
to 75 min.

### Workflow

`.github/workflows/ingest-sec-13dg-bulk.yml` timeout: `45` → `75`.

### Acceptance numbers

| Metric | Threshold |
|---|---:|
| `sec_13dg_edges.parquet` row count | ≥ 15,000 |
| `sec_icij_bridges.parquet` row count | ≥ 60 (proportional to 4x SEC volume) |
| Distinct SEC filers in bridges parquet | ≥ 40 |
| Combined with Phase 11/12: ≥ 3 distinct `sec:CIK` nodes enter subgraph | yes |

### Risks + fallbacks

- **Quarter-by-quarter SEC format drift.** The 2025 rename ("SC 13D"
  → "SCHEDULE 13D") happened mid-year somewhere. Earlier quarters
  may still use the old name. The safety-net prefix list already
  covers both; if a quarter fails entirely, log and continue rather
  than aborting the whole job.
- **Rate-limit throughput is the bottleneck.** If 75 min isn't
  enough, drop `--limit` from 5000 → 2500. Loses some long-tail
  filers but stays under timeout.

### Estimated effort
2-3 hours: 1.5h script + tests, 1h Railway dispatch + verify (the
ingest itself runs ~37 min Railway-side).

---

## Cross-phase: post-merge verification checklist

After all three phases ship and the recluster runs:

1. **Phase 11 verification**:
   `confidence_communities.parquet` rows where `uid` is in
   `anomaly_seed_uids.parquet` — confirm they're in non-singleton
   communities (i.e. the BFS actually reached their neighbourhoods).

2. **Phase 12 verification**:
   `confidence_graph_summary.json` → `subgraph.n_nodes`. Expect
   ≥ 12,000 (vs current 7,888). If still 7,888 or 8,000, the
   max-nodes cap is binding — bump it.

3. **Phase 13 verification**:
   ```
   pl.read_parquet("sec_13dg_edges.parquet").group_by(
       pl.col("filed_date").str.slice(0, 4)
   ).len()
   ```
   should show all 4 quarters with non-zero counts.

4. **End-to-end verification**:
   Grep the rendered `confidence_graph_expanded.md` for a non-zero
   `beneficial_owner_of` row in the per-kind breakdown table. If
   present, the SEC corpus is finally contributing discovery signal.
