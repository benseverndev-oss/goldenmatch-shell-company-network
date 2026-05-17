"""Render docs/reports/latent_clusters.md from the Railway artifacts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    parquet: Path = typer.Option(..., "--parquet"),
    summary: Path = typer.Option(..., "--summary"),
    out: Path = typer.Option(Path("docs/reports/latent_clusters.md"), "--out"),
) -> None:
    df = pl.read_parquet(parquet)
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    g = s["graph"]
    w = s["anomaly_score_weights"]
    dist = s["anomaly_score_distribution"]

    body = f"""# Latent-cluster mining — anomalous communities on the full ICIJ graph

_Generated {now} from `processed/latent_clusters.parquet`. Companion to
[`confidence_graph.md`](confidence_graph.md): that report anchors on the
dossier seed set; this one mines the **entire ICIJ relationship graph**
with no seed bias._

## What this is

The first lead-generation output that doesn't require a journalist to know
where to look. Louvain community detection on the full 3.3M-edge ICIJ
corpus (filtered to high-credibility structural edges + nodes with
degree ≥ 5), then anomaly-scoring every community by the combination
of features below.

## Pipeline

| Step | Outcome |
|---|---:|
| High-credibility ICIJ edges | {g["edges"]:,} (after kind filter) |
| Nodes at degree ≥ {g["min_degree"]} | {g["nodes"]:,} |
| Communities found | {s["total_communities"]:,} |
| Communities with size ≥ 3 (eligible) | {s["annotated_communities"]:,} |
| Top-N written | {s["top_n_written"]} |

**Edge kinds kept** (high-credibility only): {", ".join(f"`{k}`" for k in g["high_credibility_kinds"])}. Inferred kinds (`same_name_as`, `similar`) excluded — they'd otherwise dominate communities with name-collision noise.

## Anomaly score components

| Component | Weight | Reading |
|---|---:|---|
| `jurisdiction_span` | {w["jurisdiction_span"]:.2f} | More distinct jurisdictions = harder to explain by a single registrar's local activity |
| `sanctions_density` | {w["sanctions_density"]:.2f} | Fraction of community members whose normalized name appears in the sanctions overlay alias set |
| `size_sweet_spot` | {w["size_sweet_spot"]:.2f} | Triangular: peaks at ~50 members; tiny clusters and giant hubs are both deprioritised |
| `intermediary_density` | {w["intermediary_density"]:.2f} | Fraction of internal edges that are `intermediary_of` — the "shared corporate secretary" signature |
| `address_density` | {w["address_density"]:.2f} | Fraction of internal edges that are `registered_address` — the "shell-cluster at a shared address" signature |

## Score distribution

| Statistic | Anomaly score |
|---|---:|
| Min | {dist["min"]:.3f} |
| Median | {dist["median"]:.3f} |
| Max | {dist["max"]:.3f} |

## Top 25 anomalous communities

| Rank | Community | Size | Jurisdictions | Sanctioned | Int. density | Addr. density | Anomaly |
|---:|---:|---:|---|---:|---:|---:|---:|
"""

    for i, r in enumerate(df.head(25).iter_rows(named=True), start=1):
        body += (
            f"| {i} | {int(r['community_id'])} | {int(r['size'])} | "
            f"{r['jurisdictions'] or '—'} | {int(r['n_sanctioned'])} | "
            f"{float(r['intermediary_density']):.2f} | {float(r['address_density']):.2f} | "
            f"**{float(r['anomaly_score']):.3f}** |\n"
        )

    body += """

## Reading

The top communities are the **graph's own recommendations** for what to
investigate, derived without any seed bias. A community ranked highly here
is *not* a community that contains a dossier-pipeline anchor; it's a
structurally unusual cluster the data surfaces on its own.

Three patterns the top-25 tend to fit:

- **Cross-jurisdiction intermediary hubs.** High `jurisdiction_span` and
  near-1.0 `intermediary_density` = formation-agent service clusters
  that bridge registries — these are the "shared corporate secretary"
  pattern across multiple offshore venues.
- **Sanctions-adjacent shell clusters.** Any community with
  `n_sanctioned ≥ 1` is worth opening — at the size-50 sweet spot it
  often means a sanctioned principal plus a fan of related shells the
  sanction list itself hasn't enumerated.
- **Pure-jurisdiction shell groupings.** Single-jurisdiction (often `vg`)
  communities at the size sweet spot with high intermediary density =
  classic BVI shell-pool registered through one formation agent.

## What this report does NOT prove

1. **Anomaly is a structural signal, not investigative confirmation.**
   Top-ranked communities still need human review; structural
   unusualness ≠ guilt.
2. **Single-jurisdiction clusters dominate the top.** Of the eligible
   communities, most span only one jurisdiction. This is a property of
   the corpus (Panama Papers / Paradise / Pandora ingest is heaviest
   on BVI/Bermuda/Panama), not the metric.
3. **Sanctions match is via normalized-name alias lookup.** The same
   false-positive risk as discussed in `baseline_comparison.md` applies:
   a community member matching a common sanctioned-name alias may not
   be the sanctioned person.
4. **No temporal info.** A community here is a static snapshot. The
   [`temporal_patterns.md`](temporal_patterns.md) report covers the
   evolution side.

## Reproduce

```bash
just job-run build_latent_clusters
just job-fetch processed/latent_clusters.parquet docs/reports/data/
just job-fetch processed/latent_clusters_summary.json docs/reports/data/

uv run python scripts/render_latent_clusters.py \\
    --parquet docs/reports/data/latent_clusters.parquet \\
    --summary docs/reports/data/latent_clusters_summary.json \\
    --out docs/reports/latent_clusters.md
```

Or trigger `.github/workflows/build-latent-clusters.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
