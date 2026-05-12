"""Build notebooks/01_case_study.ipynb programmatically.

We construct the notebook with nbformat so the source-of-truth lives
in code (this file) and the notebook can be regenerated on demand.
Run this script once after changing the source; commit the resulting
.ipynb alongside.
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

nb = nbf.v4.new_notebook()
nb["metadata"] = {
    "kernelspec": {
        "display_name": "Python 3 (shellnet)",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "pygments_lexer": "ipython3"},
}

cells: list = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text.lstrip("\n")))


def code(text: str) -> None:
    cells.append(nbf.v4.new_code_cell(text.strip("\n")))


md(
    """
# Phoenix Spree Deutschland — executable case study

Companion to `reports/case_study.md`. This notebook re-derives every
table and chart in the writeup from the data on disk (parquet on the
Railway volume or local mirror, plus Postgres for the published runs).

Run order: top to bottom. The notebook is read-only against Postgres —
no run-state changes here.
"""
)

code(
    """
import os
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
import psycopg

# Default to the Railway-volume layout; override with environment if you
# mirrored the artifacts locally.
DATA_DIR = Path(os.environ.get("SHELLNET_DATA_DIR", "/data"))
PROCESSED_DIR = DATA_DIR / "processed"
INTERIM_DIR = DATA_DIR / "interim"
REPORTS_DIR = DATA_DIR / "reports" / "generated"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://golden:Qgl7Y6bNiRTI__Rr-OJy_a0dr1iVf8A9@metro.proxy.rlwy.net:38076/golden_showcase",
)


def pg():
    return psycopg.connect(DATABASE_URL)


SPOTLIGHT_CLUSTER_ID = 503264
"""
)

md(
    """
## 1. Data inventory

Counts the ingested rows in each interim parquet plus the published-run
sizes from Postgres.
"""
)

code(
    """
inventory = []
for name in (
    "icij_entities",
    "icij_addresses",
    "icij_officers",
    "icij_intermediaries",
    "icij_edges",
    "opensanctions_entities",
    "gleif_entities",
):
    p = INTERIM_DIR / f"{name}.parquet"
    if p.exists():
        inventory.append((name, pl.scan_parquet(p).select(pl.len()).collect().item()))
print(f"{'parquet':<28s}  rows")
for n, r in inventory:
    print(f"  {n:<26s}  {r:>10,}")

with pg() as conn, conn.cursor() as cur:
    cur.execute(
        "SELECT what, records, clusters, multi_member_clusters, same_as_pairs "
        "FROM shellnet.runs ORDER BY created_at DESC"
    )
    print()
    print(f"{'what':<40s}  records   clusters   multi   same_as_pairs")
    for w, rec, cl, mm, sa in cur.fetchall():
        print(f"  {w:<38s}  {rec:>7}  {cl or 0:>9}  {mm or 0:>6}  {sa or 0:>13}")
"""
)

md(
    """
## 2. The spotlight cluster

Pull the 9 members of cluster 503264 from Postgres, their attributes from
the unified company table, and their GLEIF anchors from the v2 list-match.
"""
)

code(
    """
with pg() as conn, conn.cursor() as cur:
    cur.execute(
        "SELECT run_id FROM shellnet.runs WHERE what='company' "
        "ORDER BY created_at DESC LIMIT 1"
    )
    dedupe_run = str(cur.fetchone()[0])
    cur.execute(
        "SELECT entity_uid FROM shellnet.clusters "
        "WHERE run_id=%s AND cluster_id=%s",
        (dedupe_run, SPOTLIGHT_CLUSTER_ID),
    )
    member_uids = [r[0] for r in cur.fetchall()]
    print(f"cluster {SPOTLIGHT_CLUSTER_ID}: {len(member_uids)} members")

attrs = (
    pl.read_parquet(PROCESSED_DIR / "company_entities.parquet")
    .filter(pl.col("entity_uid").is_in(member_uids))
    .select(["entity_uid", "name", "jurisdiction", "source_id"])
    .sort("entity_uid")
)
attrs
"""
)

code(
    """
with pg() as conn, conn.cursor() as cur:
    cur.execute(
        "SELECT run_id FROM shellnet.runs "
        "WHERE what LIKE 'list_match:%%v2%%' "
        "ORDER BY created_at DESC LIMIT 1"
    )
    lm_run = str(cur.fetchone()[0])
    cur.execute(
        "SELECT target_entity_uid, ref_lei, ref_name, score, score_band "
        "FROM shellnet.list_matches "
        "WHERE run_id=%s AND target_entity_uid = ANY(%s) "
        "ORDER BY target_entity_uid",
        (lm_run, member_uids),
    )
    anchors = pl.DataFrame(
        [
            {"target_uid": t, "ref_lei": l, "ref_name": n, "score": float(s), "band": b}
            for t, l, n, s, b in cur.fetchall()
        ]
    )
anchors
"""
)

md(
    """
### 2.1 The VI → VII edge case

`icij:82015313` (Phoenix Spree Deutschland VI Limited) and
`icij:82015339` (Phoenix Spree Deutschland VII Limited) both map to the
same GLEIF reference `529900ZH4XA9K4B3EP79` (Phoenix Spree Deutschland
VII Limited). That's not a claim VI = VII — it's a `--match-mode best`
artifact: GLEIF appears to have no record for VI, so the closest
available reference for VI is VII (score 0.987, "high" band rather than
"perfect").
"""
)

md(
    """
## 3. Evaluation: v1 vs v2

Reads `reports/eval_v1_vs_v2.json` (produced by `scripts/eval_v1_vs_v2.py`).
Re-rendering the headline table and per-band precision chart.
"""
)

code(
    """
import json
eval_json_paths = [
    Path("reports/eval_v1_vs_v2.json"),
    REPORTS_DIR / "eval_v1_vs_v2.json",
]
eval_path = next((p for p in eval_json_paths if p.exists()), None)
assert eval_path, f"could not find eval json at any of {eval_json_paths}"
eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
print(f"v1 run: {eval_data['v1_run']}  ({eval_data['v1_pair_count']:,} pairs)")
print(f"v2 run: {eval_data['v2_run']}  ({eval_data['v2_pair_count']:,} pairs)")
print()
print(f"Estimated v2 overall precision: "
      f"{eval_data['estimated_v2_overall_precision_strict']:.1%} strict / "
      f"{eval_data['estimated_v2_overall_precision_generous']:.1%} generous")
"""
)

code(
    """
fig, ax = plt.subplots(figsize=(7, 4))
bands = ("perfect", "high", "borderline")
v1_sizes = [eval_data["v1_band_counts"].get(b, 0) for b in bands]
v2_sizes = [eval_data["v2_band_counts"].get(b, 0) for b in bands]
x = range(len(bands))
ax.bar([i - 0.2 for i in x], v1_sizes, width=0.4, label="v1", color="#ddd")
ax.bar([i + 0.2 for i in x], v2_sizes, width=0.4, label="v2", color="#5c87bf")
ax.set_xticks(list(x))
ax.set_xticklabels(bands)
ax.set_ylabel("matched-pair count")
ax.set_title("v1 vs v2: matched pairs by score band")
ax.legend()
for i, (v, w) in enumerate(zip(v1_sizes, v2_sizes)):
    ax.text(i - 0.2, v, f"{v:,}", ha="center", va="bottom", fontsize=8)
    ax.text(i + 0.2, w, f"{w:,}", ha="center", va="bottom", fontsize=8)
plt.tight_layout()
plt.show()
"""
)

md(
    """
## 4. Hand-label distribution

Loads `data/labels/marginal_v1.csv` (300 pairs across four buckets) and
shows the label distribution per bucket.
"""
)

code(
    """
import csv
labels_paths = [
    Path("data/labels/marginal_v1.csv"),
    DATA_DIR / "labels" / "marginal_v1.csv",
]
labels_path = next((p for p in labels_paths if p.exists()), None)
assert labels_path, "labels CSV not found"
rows = list(csv.DictReader(labels_path.open(encoding="utf-8")))
by_bucket: dict[str, Counter[str]] = {}
for r in rows:
    by_bucket.setdefault(r["bucket"], Counter())[r["label"]] += 1
order = ("v1_dropped", "v2_marginal", "perfect_sanity", "v2_borderline_class")
print(f"{'bucket':<22s}  match  no_match  unsure  total")
for b in order:
    c = by_bucket.get(b, Counter())
    total = sum(c.values())
    print(
        f"  {b:<20s}  {c.get('match',0):>5}  {c.get('no_match',0):>8}  "
        f"{c.get('unsure',0):>6}  {total:>5}"
    )
"""
)

md(
    """
## 5. Centrality: top-degree nodes in the cluster sub-graph

Loads `cluster_centrality.parquet` and renders the top-30 by total degree.
"""
)

code(
    """
cent_paths = [
    Path("data/processed/cluster_centrality.parquet"),
    PROCESSED_DIR / "cluster_centrality.parquet",
]
cent_path = next((p for p in cent_paths if p.exists()), None)
if cent_path is None:
    print("cluster_centrality.parquet not present locally; skipping. "
          "Mirror it from the Railway volume to render this section.")
else:
    cent = pl.read_parquet(cent_path)
    top = cent.sort("total_degree", descending=True).head(30).select(
        ["entity_uid", "source", "name", "jurisdiction", "cluster_id",
         "community_id", "total_degree", "betweenness"]
    )
    top
"""
)

code(
    """
if cent_path is not None:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(
        cent.filter(pl.col("total_degree") > 0)["total_degree"].to_numpy(),
        bins=60, log=True, color="#5c87bf",
    )
    ax.set_xlabel("total degree")
    ax.set_ylabel("node count (log)")
    ax.set_title("Cluster sub-graph: degree distribution")
    plt.tight_layout()
    plt.show()
"""
)

md(
    """
## 6. Limitations + what's next

See `reports/case_study.md` § 7 and § 8 for the full treatment.
Headline limitations:

- Labels are AI-assisted, not human ground truth — small spot-check
  would harden the eval.
- Sampling bias: 300 pairs over-sampled marginal score bands.
- `negative_evidence` disabled due to a GoldenMatch 1.12.x crash in
  the `match` subcommand.
- Phoenix Spree VI maps to VII as a closest-available-reference
  artifact, not a same-entity claim.
"""
)

nb["cells"] = cells

out = Path("notebooks/01_case_study.ipynb")
out.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, out)
print(f"wrote {out} ({len(cells)} cells)")
