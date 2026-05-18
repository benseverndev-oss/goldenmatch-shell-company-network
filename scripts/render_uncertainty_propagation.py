"""Render docs/reports/uncertainty_propagation.md from confidence_graph_summary.json
+ confidence_cluster_scored.parquet.

The operational counterpart to docs/paper/uncertainty_propagation.md —
that doc defines the formulas; this report shows the values they
produce on the current corpus.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    summary: Path = typer.Option(..., "--summary"),
    cluster_parquet: Path = typer.Option(..., "--cluster-parquet"),
    out: Path = typer.Option(Path("docs/reports/uncertainty_propagation.md"), "--out"),
) -> None:
    s = json.loads(summary.read_text(encoding="utf-8"))
    up = s.get("uncertainty_propagation", {})
    sub = s.get("subgraph", {})
    clusters = pl.read_parquet(cluster_parquet) if cluster_parquet.exists() else None
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""# Uncertainty propagation — operational values

_Generated {now} from `processed/confidence_graph_summary.json` and
`processed/confidence_cluster_scored.parquet`. Formal definitions in
[`docs/paper/uncertainty_propagation.md`](../paper/uncertainty_propagation.md)._

This report shows the values the four formal uncertainty-propagation
metrics produce on the current dossier-anchored subgraph. It is the
operational companion to the methodology document.

## Subgraph scope

| Metric | Value |
| --- | ---: |
| Seed UIDs (dossier anchors) | {sub.get("n_seed_uids", 0):,} |
| Subgraph nodes | {sub.get("n_nodes", 0):,} |
| Subgraph edges | {sub.get("n_edges", 0):,} |
| BFS depth | {sub.get("hops", 0)} hops |

## 1. Edge credibility (provenance-weighted)

```
cred(e) = cred_kind(kind_raw) × cred_source(source_label)
```

The kind priors live in `confidence_graph_summary.json` under
`edge_credibility_priors`. The source priors are tabulated below
(values from `source_credibility_priors`):

| Source | Prior | Rationale |
| --- | ---: | --- |
"""

    sp = s.get("source_credibility_priors", {}) or {}
    source_notes = {
        "Panama Papers": "Well-documented leak; high fidelity",
        "Paradise Papers - Appleby": "Well-documented; firm-level provenance",
        "Pandora Papers": "Recent leak; mid-to-high fidelity",
        "Bahamas Leaks": "Single-jurisdiction leak; mid fidelity",
        "Offshore Leaks": "Oldest leak; lowest fidelity",
        "OpenSanctions": "Curated overlay; high fidelity",
        "GLEIF": "Authoritative registry; highest fidelity",
        "UK PSC": "Statutory registry; high fidelity",
        "UK disqualified": "Statutory regulatory action; high fidelity",
    }
    for src, p in sorted(sp.items(), key=lambda kv: -kv[1]):
        note = source_notes.get(src, "")
        if not note and src.startswith("Paradise Papers"):
            note = "Well-documented leak; firm/registry-level provenance"
        body += f"| `{src}` | {p:.2f} | {note} |\n"
    body += (
        f"| _(unknown source)_ | {s.get('default_source_credibility', 0.85):.2f} | _Fallback_ |\n\n"
    )

    body += """## 2. Path-probability propagation

```
P(connection | π) = ∏_{i=1..k} cred(e_i)
```

Computed by Dijkstra on the negated-log graph, cutoff at
`-log 0.05 ≈ 3.0` (so paths weaker than 5% are dropped). Full
indirect-link list in
[`confidence_graph.md`](confidence_graph.md) §"Indirect links".

"""

    body += f"""**Independence assumption (explicit):**
{up.get("independence_assumption_note", "")}

## 3. Cluster confidence with contradiction penalty

```
conf(C) = mean_cred(C) × (1 - λ · contradiction_density(C))
```

with **λ = {s.get("contradiction_lambda", 0.5):.2f}** by default.

"""
    if clusters is not None and clusters.height > 0:
        n_clean = clusters.filter(pl.col("contradiction_density") == 0).height
        n_penalised = clusters.filter(pl.col("contradiction_density") > 0).height
        mean_conf = float(clusters.select(pl.col("cluster_confidence").mean()).item() or 0.0)
        body += f"- **Clusters scored:** {clusters.height:,}\n"
        body += f"- **Clean clusters** (`contradiction_density = 0`): **{n_clean:,}**\n"
        body += (
            f"- **Penalised clusters** (any contradiction-touching member): **{n_penalised:,}**\n"
        )
        body += f"- **Mean cluster confidence:** {mean_conf:.3f}\n\n"

        body += "**Top-10 clusters by confidence:**\n\n"
        body += "| Community | Size | Mean cred | Contradiction density | Cluster conf |\n"
        body += "|---:|---:|---:|---:|---:|\n"
        for r in clusters.head(10).iter_rows(named=True):
            body += (
                f"| {int(r['community_id'])} | {int(r['size'])} | "
                f"{float(r['mean_edge_credibility']):.3f} | "
                f"{float(r['contradiction_density']):.3f} | "
                f"**{float(r['cluster_confidence']):.3f}** |\n"
            )
        body += "\n"

        penalised = clusters.filter(pl.col("contradiction_density") > 0).sort(
            "contradiction_density", descending=True
        )
        if penalised.height > 0:
            body += "**Top-5 most-penalised clusters** (largest contradiction density):\n\n"
            body += "| Community | Size | Mean cred | Contradiction density | Cluster conf |\n"
            body += "|---:|---:|---:|---:|---:|\n"
            for r in penalised.head(5).iter_rows(named=True):
                body += (
                    f"| {int(r['community_id'])} | {int(r['size'])} | "
                    f"{float(r['mean_edge_credibility']):.3f} | "
                    f"**{float(r['contradiction_density']):.3f}** | "
                    f"{float(r['cluster_confidence']):.3f} |\n"
                )
            body += "\n"

    body += """## 4. Graph-level uncertainty

```
H(G) = (1/|E|) · Σ_e [-p log p - (1-p) log(1-p)]    (nats)
```

"""
    body += f"- **Total entropy:** {up.get('graph_total_entropy_nats', 0):.4f} nats\n"
    body += (
        f"- **Mean entropy per edge:** {up.get('graph_mean_entropy_per_edge_nats', 0):.4f} nats\n"
    )
    body += f"- **Normalised entropy** (divided by `log 2`): **{up.get('graph_normalised_entropy', 0):.4f}** ∈ [0, 1]\n"
    body += f"- **Mean edge credibility:** {up.get('graph_mean_edge_credibility', 0):.4f}\n\n"

    norm_h = up.get("graph_normalised_entropy", 0)
    mean_c = up.get("graph_mean_edge_credibility", 0)
    if mean_c >= 0.9 and norm_h <= 0.3:
        verdict = (
            "**Graph is dominated by credible structural edges. Conclusions are well-supported.**"
        )
    elif mean_c >= 0.9 and norm_h > 0.5:
        verdict = "**A few gray-zone edges are pulling the entropy up despite a credible majority. Investigate them via `confidence_review_priority.parquet`.**"
    elif mean_c < 0.6 and norm_h <= 0.3:
        verdict = "**Graph is dominated by low-credibility edges that the system is *confident* are weak. Conclusions are weakly supported but consistent.**"
    elif mean_c < 0.6 and norm_h > 0.5:
        verdict = (
            "**Graph is genuinely uncertain. Treat the partition output as exploratory only.**"
        )
    else:
        verdict = "**Intermediate epistemic state. Read the per-cluster and per-edge confidence numbers before treating any single finding as load-bearing.**"
    body += f"**Verdict:** {verdict}\n\n"

    body += """## 5. Combined decision rule

Read together with the formal definitions, the four metrics yield a
single threshold rule for whether a finding is publication-grade:

1. **Edge level.** Direct edges with `cred(e) ≥ 0.9` are publication-grade.
2. **Path level.** Indirect links with `P(connection | π) ≥ 0.5` are investigatively worth pursuing.
3. **Cluster level.** Communities with `conf(C) ≥ 0.7` AND `contradiction_density = 0` are publication-grade.
4. **Graph level.** The whole graph carries a `mean_cred(G)` / `H(G)` verdict (above).

## What this report does NOT prove

- **The priors are operator-set, not learned.** Calibrating `cred_kind`
  and `cred_source` against the labelled `marginal_pair_review`
  set is the documented v2 follow-up.
- **λ = 0.5 is a default.** The contradiction-penalty weight has not
  been swept against held-out analyst judgements.
- **Path-probability is a conservative lower bound.** The independence
  assumption is documented and explicit.

## Reproduce

```bash
just job-run build_confidence_graph
just job-fetch processed/confidence_graph_summary.json docs/reports/data/
just job-fetch processed/confidence_cluster_scored.parquet docs/reports/data/

uv run python scripts/render_uncertainty_propagation.py \\
    --summary docs/reports/data/confidence_graph_summary.json \\
    --cluster-parquet docs/reports/data/confidence_cluster_scored.parquet \\
    --out docs/reports/uncertainty_propagation.md
```

Or trigger `.github/workflows/build-confidence-graph.yml` (renders both
`confidence_graph.md` and this report).
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
