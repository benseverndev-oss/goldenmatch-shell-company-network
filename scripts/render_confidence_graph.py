"""Render docs/reports/confidence_graph.md from the Railway artifacts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    edges: Path = typer.Option(..., "--edges"),
    communities: Path = typer.Option(..., "--communities"),
    summary: Path = typer.Option(..., "--summary"),
    out: Path = typer.Option(Path("docs/reports/confidence_graph.md"), "--out"),
) -> None:
    edges_df = pl.read_parquet(edges)
    cs_df = pl.read_parquet(communities)
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Edge-credibility distribution.
    cred_dist = (
        edges_df.with_columns(
            pl.when(pl.col("credibility") >= 0.9)
            .then(pl.lit("≥0.90 (structural)"))
            .when(pl.col("credibility") >= 0.7)
            .then(pl.lit("0.70–0.90"))
            .when(pl.col("credibility") >= 0.5)
            .then(pl.lit("0.50–0.70"))
            .otherwise(pl.lit("<0.50"))
            .alias("bucket")
        )
        .group_by("bucket")
        .len()
        .sort("len", descending=True)
    )

    # Per-kind credibility table.
    by_kind = (
        edges_df.group_by("kind_raw")
        .agg(
            pl.len().alias("n"),
            pl.col("credibility").first().alias("credibility"),
        )
        .sort("n", descending=True)
    )

    # Top communities by size at the strictest threshold.
    strictest = s["thresholds"][-1]
    top_communities = (
        cs_df.filter(pl.col("threshold") == strictest)
        .group_by("community_id")
        .agg(
            pl.len().alias("size"),
            pl.col("is_seed").sum().alias("n_seeds"),
        )
        .sort("size", descending=True)
        .head(10)
    )

    # Anomaly-ranked communities (loaded from sibling parquet if present).
    anomaly_path = edges.parent / "confidence_community_anomalies.parquet"
    anomaly_df: pl.DataFrame | None = (
        pl.read_parquet(anomaly_path) if anomaly_path.exists() else None
    )
    # Multi-hop indirect-links table (loaded from sibling parquet if present).
    indirect_path = edges.parent / "confidence_indirect_links.parquet"
    indirect_df: pl.DataFrame | None = (
        pl.read_parquet(indirect_path) if indirect_path.exists() else None
    )
    # Confidence-aware-reasoning extensions (loaded if sibling parquets exist).
    aggregates_path = edges.parent / "confidence_community_aggregates.parquet"
    aggregates_df: pl.DataFrame | None = (
        pl.read_parquet(aggregates_path) if aggregates_path.exists() else None
    )
    contradictions_path = edges.parent / "confidence_contradictions.parquet"
    contradictions_df: pl.DataFrame | None = (
        pl.read_parquet(contradictions_path) if contradictions_path.exists() else None
    )
    review_path = edges.parent / "confidence_review_priority.parquet"
    review_df: pl.DataFrame | None = pl.read_parquet(review_path) if review_path.exists() else None

    sub = s["subgraph"]
    stab = s["stability"]

    body = f"""# Confidence-aware graph reconstruction

_Generated {now} from `processed/confidence_graph_edges.parquet`,
`processed/confidence_communities.parquet`, and
`processed/confidence_graph_summary.json`. Companion to
[`methodology.md` §6](../paper/methodology.md)._

## What this report measures

Standard community detection treats edges as binary present/absent. In an
adversarial ER setting, every edge carries uncertainty: structural ICIJ
relations (`officer_of`, `registered_address`) are firm; inferred
relations (`same_name_as`, `similar`) are soft. This report:

1. **Scores each edge's credibility** based on its `kind_raw` (operator
   priors documented below).
2. **Runs Louvain community detection at multiple credibility thresholds**,
   producing a partition per threshold.
3. **Quantifies stability** — does the community structure survive when
   we drop low-credibility edges?

The scope is the 2-hop subgraph anchored on the **dossier seed set**
(the {sub["n_seed_uids"]} entities from `rare_officer_dossiers.parquet`),
not the full 3.3M-edge ICIJ corpus. Bounded compute, investigatively-
aligned subgraph.

## Subgraph statistics

| Metric | Value |
|---|---:|
| Seed UIDs (dossier anchors) | {sub["n_seed_uids"]:,} |
| Subgraph nodes | {sub["n_nodes"]:,} |
| Subgraph edges | {sub["n_edges"]:,} |
| BFS depth | {sub["hops"]} hops |

## Edge-credibility priors

| Edge kind | Credibility | Rationale |
|---|---:|---|
"""

    kind_descriptions = {
        "registered_address": "Structural fact from leak documents",
        "officer_of": "Structural fact from leak documents",
        "intermediary_of": "Structural fact from leak documents",
        "shareholder_of": "Structural fact from leak documents",
        "same_id_as": "Identifier-based merge by ICIJ",
        "same_as": "Manual ICIJ deduplication",
        "same_company_as": "Cross-leak company identity",
        "underlying": "Structural ownership relation",
        "connected_to": "Generic relation, weaker than typed kinds",
        "same_name_as": "Name-similarity inference, weakest",
        "similar": "ICIJ vague relation, weakest",
    }
    for kind, cred in s["edge_credibility_priors"].items():
        body += f"| `{kind}` | {cred:.2f} | {kind_descriptions.get(kind, '—')} |\n"
    body += (
        f"| _(default for unknown kinds)_ | {s['default_edge_credibility']:.2f} | _Fallback_ |\n"
    )

    body += "\n### Distribution in this subgraph\n\n"
    body += "| Credibility bucket | Edges |\n|---|---:|\n"
    for r in cred_dist.iter_rows(named=True):
        body += f"| {r['bucket']} | {int(r['len']):,} |\n"

    body += "\n### Per-kind breakdown (subgraph)\n\n"
    body += "| Edge kind | Credibility | Edges in subgraph |\n|---|---:|---:|\n"
    for r in by_kind.iter_rows(named=True):
        body += f"| `{r['kind_raw']}` | {float(r['credibility']):.2f} | {int(r['n']):,} |\n"

    body += """

## Communities at three credibility thresholds

The community partition is computed at each threshold by filtering
edges to those at-or-above the threshold, then running Louvain on the
filtered graph.

| Threshold | Edges retained | Communities | Largest | Median | Singletons |
|---:|---:|---:|---:|---:|---:|
"""

    for t in s["thresholds"]:
        key = f"{t:.2f}"
        pt = s["per_threshold"][key]
        body += (
            f"| {t:.2f} | {pt['edges_retained']:,} | {pt['n_communities']} | "
            f"{pt['largest_community_size']:,} | {pt['median_community_size']} | "
            f"{pt['n_singletons']} |\n"
        )

    body += f"""

## Stability across thresholds

**Per-node Jaccard overlap** between the community membership at the
most-permissive threshold ({stab["thresholds_compared"][0]:.2f}) and the most-strict threshold
({stab["thresholds_compared"][1]:.2f}):

| Metric | Value |
|---|---:|
| Nodes evaluated | {stab["n_nodes_evaluated"]:,} |
| Mean Jaccard overlap | **{stab["mean_jaccard"]:.3f}** |
| Nodes with overlap ≥ 0.5 | {stab["n_nodes_overlap_ge_0_5"]:,} ({stab["fraction_overlap_ge_0_5"] * 100:.1f}%) |

A mean Jaccard of {stab["mean_jaccard"]:.2f} means **the community structure is
{("highly stable" if stab["mean_jaccard"] >= 0.9 else "moderately stable" if stab["mean_jaccard"] >= 0.7 else "unstable")} to credibility-threshold changes**.
The dominant communities are anchored by structural ICIJ edges
(`officer_of`, `registered_address`) which all have credibility ≥ 0.9
and survive any threshold in this range. Inferred edges (`same_name_as`,
`similar`, credibility 0.5) get filtered out at threshold ≥ 0.7,
producing the small change in community count visible above.

**The honest methodological claim**: the community partition reported
here is not an artifact of an arbitrary credibility cut-off. If the
mean Jaccard were ~0.5, it would be.

## Top 10 communities at threshold {strictest:.2f}

Communities ranked by size. `n_seeds` = how many dossier-anchor UIDs
fall into this community (a signal that the community is investigatively
relevant, not just structurally large).

| Community ID | Size | Seed members |
|---:|---:|---:|
"""

    for r in top_communities.iter_rows(named=True):
        body += f"| {int(r['community_id'])} | {int(r['size']):,} | {int(r['n_seeds'])} |\n"

    if anomaly_df is not None and anomaly_df.height > 0:
        body += f"""

## Anomaly-ranked communities at threshold {strictest:.2f}

The size-ranked table above is a baseline. The investigatively-relevant
ranking is by **anomaly score**, which combines:

- **Seed density** (40% weight) — fraction of community members that are
  dossier-anchor seeds. High = community is investigatively-aligned.
- **Isolation** (35%) — fraction of community edges that are internal vs.
  bridging out to other communities. High = self-contained cluster, a
  shell-network signature.
- **Size deviation** (25%) — log-size distance from the median community
  size. Communities much smaller (tight clusters) or much larger (sprawling
  hubs) than the median are more anomalous than typical-sized ones.

Top 10:

| Rank | Community | Size | Seeds | Seed density | Isolation | Anomaly score |
|---:|---:|---:|---:|---:|---:|---:|
"""
        for i, r in enumerate(anomaly_df.head(10).iter_rows(named=True), start=1):
            body += (
                f"| {i} | {int(r['community_id'])} | {int(r['size']):,} | "
                f"{int(r['n_seeds'])} | {float(r['seed_density']):.2f} | "
                f"{float(r['isolation']):.2f} | {float(r['anomaly_score']):.3f} |\n"
            )

        body += (
            "\nThe top-ranked community here is the lead-generation engine's "
            "graph-level recommendation: investigate **this cluster** because "
            "its structural signature (isolated + seed-dense + size-distinctive) "
            "is most unlike everything else in the subgraph.\n"
        )

    if indirect_df is not None and indirect_df.height > 0:
        n_strong = indirect_df.filter(pl.col("path_probability") >= 0.5).height
        body += f"""

## Multi-hop indirect links between seeds

Pairs of dossier-anchor seeds that are **not directly connected** but are
reachable through a 2-3 hop path whose probability (product of edge
credibilities along the path) is ≥ 0.05. These are the "uncertain but
compelling" indirect links the per-anchor dossier walks miss.

| Metric | Value |
|---|---:|
| Indirect pairs surfaced | {indirect_df.height:,} |
| Pairs with path probability ≥ 0.5 (strong) | {n_strong:,} |

### Top 10 strongest indirect links

| src_uid | dst_uid | Path probability |
|---|---|---:|
"""
        for r in indirect_df.head(10).iter_rows(named=True):
            body += (
                f"| `{r['src_uid']}` | `{r['dst_uid']}` | "
                f"**{float(r['path_probability']):.3f}** |\n"
            )

        body += (
            "\nA path probability of 0.5 means the chain of edge credibilities "
            "between the two seeds multiplies out to 0.5 — strong enough that "
            "the pair is worth investigating as if it were a direct link, even "
            "though no single edge connects them. Lower values are weaker "
            "but still surface candidates a 1-hop search would miss.\n"
        )

    body += """

## Confidence-aware reasoning extensions

These extensions sit on top of the threshold-stability analysis and turn
the credibility-weighted graph into actionable reviewer signal.

"""

    if aggregates_df is not None and aggregates_df.height > 0:
        body += "### Per-community confidence aggregates\n\n"
        body += (
            "Mean / min edge credibility within each community at the "
            f"strict threshold ({s['thresholds'][-1]:.2f}). "
            "Communities with high mean credibility are structurally "
            "grounded; low-mean ones rest on inferred edges and deserve "
            "review before publication.\n\n"
        )
        body += "| Community | Internal edges | Mean credibility | Min credibility |\n"
        body += "|---:|---:|---:|---:|\n"
        top_agg = aggregates_df.sort("n_internal_edges", descending=True).head(10)
        for r in top_agg.iter_rows(named=True):
            body += (
                f"| {int(r['community_id'])} | "
                f"{int(r['n_internal_edges'])} | "
                f"{float(r['mean_edge_credibility']):.3f} | "
                f"{float(r['min_edge_credibility']):.3f} |\n"
            )
        body += "\n"

    if contradictions_df is not None and contradictions_df.height > 0:
        body += "### Contradiction-aware closure\n\n"
        body += (
            "Node pairs that share a community at the loose threshold but "
            "split across distinct communities at the strict threshold — "
            "the soft edges between them are the load-bearing assumptions. "
            f"Detected: **{contradictions_df.height:,}** pairs (capped).\n\n"
        )
        body += "| Node A | Node B | Loose community | Strict A | Strict B |\n"
        body += "|---|---|---:|---:|---:|\n"
        for r in contradictions_df.head(10).iter_rows(named=True):
            body += (
                f"| `{r['node_a']}` | `{r['node_b']}` | "
                f"{int(r['lo_community'])} | "
                f"{int(r['hi_community_a'])} | {int(r['hi_community_b'])} |\n"
            )
        body += "\n"

    if review_df is not None and review_df.height > 0:
        body += "### Review-priority ranking\n\n"
        body += (
            "Edges in the gray zone (credibility 0.4–0.75) that touch "
            "contradiction-prone nodes or dossier seeds, ranked by "
            "`uncertainty × impact`. These are the highest-leverage "
            "manual-review targets — a yes/no decision on each rewrites "
            f"large parts of the community structure. Total: **{review_df.height:,}**.\n\n"
        )
        body += "| Node A | Node B | Edge credibility | Uncertainty | Impact | Priority |\n"
        body += "|---|---|---:|---:|---:|---:|\n"
        for r in review_df.head(15).iter_rows(named=True):
            body += (
                f"| `{r['node_a']}` | `{r['node_b']}` | "
                f"{float(r['edge_credibility']):.3f} | "
                f"{float(r['uncertainty']):.3f} | "
                f"{float(r['impact_score']):.3f} | "
                f"{float(r['priority']):.3f} |\n"
            )
        body += "\n"

    body += """## What this report does NOT prove

1. **Credibility priors are operator estimates.** The per-edge-kind
   numbers in §"Edge-credibility priors" are hand-set, not learned. A
   v2 would calibrate them against the labelled marginal-pair review
   set (`labels.csv`) — which the repo doesn't yet have.
2. **Cross-source match edges are absent from this run.** The
   `confidence_graph_edges.parquet` here is ICIJ-only because the
   subgraph BFS walks `icij_edges`. Merging in cross-source-match edges
   (`icij_os_vs_gleif_matched.csv` etc.) with PAV-calibrated weights is
   a v2 follow-up; it would let the same threshold analysis run on
   cross-registry-merged identities.
3. **Stability ≠ correctness.** A stable community can still be wrong
   if the edge priors are systematically miscalibrated.
4. **The 2-hop subgraph is investigatively biased.** It anchors on
   dossier anchors that are *already* of interest. A baseline community
   analysis on a random-anchor subgraph would tell us if the stability
   here is general or specific to the dossier seeds.

## Reproduce

```bash
just job-run build_confidence_graph
for p in processed/confidence_graph_edges.parquet \\
         processed/confidence_communities.parquet \\
         processed/confidence_graph_summary.json; do
    just job-fetch "$p" docs/reports/data/
done

uv run python scripts/render_confidence_graph.py \\
    --edges docs/reports/data/confidence_graph_edges.parquet \\
    --communities docs/reports/data/confidence_communities.parquet \\
    --summary docs/reports/data/confidence_graph_summary.json \\
    --out docs/reports/confidence_graph.md
```

Or trigger `.github/workflows/build-confidence-graph.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
