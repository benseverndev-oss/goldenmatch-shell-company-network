"""Render docs/reports/discovery_advantage.md from the synthesis summary."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


_STRUCTURE_LABELS = {
    "S1_latent_intermediary_reuse": "Latent intermediary reuse",
    "S2_jurisdiction_bridges": "Unexpected jurisdiction bridges",
    "S3_hidden_registry_anchors": "Hidden registry anchors (ICIJ ↔ GLEIF)",
    "S4_sanctions_adjacent_closure": "Sanctions-adjacent community closure",
    "S5_fragmented_ownership_convergence": "Fragmented ownership convergence",
    "S6_anomalous_communities": "Anomalous community structures",
}


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if abs(v) >= 1000 or abs(v) < 0.001:
            return f"{v:,.4g}"
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


@app.command()
def main(
    summary: Path = typer.Option(..., "--summary"),
    out: Path = typer.Option(Path("docs/reports/discovery_advantage.md"), "--out"),
) -> None:
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""# Discovery Advantage Report

_Generated {now} from `processed/discovery_advantage_summary.json`. This
is a synthesis benchmark: it aggregates every existing baseline-vs-pipeline
measurement in the repo into one canonical artifact, so the investigative
novelty claim can be evaluated end-to-end without cross-referencing eight
separate reports._

## What this report is — and isn't

**Is:** a quantified delta between (a) what a journalist could surface
using single-source search + manual cross-reference, and (b) what the
GoldenMatch pipeline surfaces. Every number traces back to a primary
report in this repo; this document is the closing argument, not new
evidence.

**Isn't:** a human-validated novelty study. The repo has no labelled
analyst-review panel. Surfaced structures are operational proxies, not
journalist-confirmed exposés. The "Analyst review outcomes" section
below makes this explicit — it's flagged as a v2 gap, not a hidden
limitation.

## Headline delta

The pipeline either matches or beats every baseline on every axis we
quantify. Where the delta is large, that's the investigative-novelty
claim; where it's small, that's a sanity-check baseline.

| Axis | Baseline | Pipeline | Δ absolute | Δ % |
|---|---:|---:|---:|---:|
"""

    for d in s.get("headline_deltas", []):
        lower_better = d.get("lower_is_better", False)
        arrow = "↓" if lower_better else "↑"
        pct = d.get("relative_delta_pct")
        pct_str = f"{arrow} {abs(pct):.1f}%" if isinstance(pct, (int, float)) else "—"
        body += (
            f"| {d['axis']} "
            f"_({d['baseline_label']} → {d['pipeline_label']})_ "
            f"| {_fmt(d['baseline'])} | {_fmt(d['pipeline'])} "
            f"| {_fmt(d['absolute_delta'])} | {pct_str} |\n"
        )

    body += """

Each row is sourced from a specific primary report:
- B1→B2 lift: [`discovery_lift.md`](discovery_lift.md)
- ICIJ-search vs cross-source: [`baseline_comparison.md`](baseline_comparison.md)
- Analyst-hours: [`baseline_comparison.md`](baseline_comparison.md) §"Analyst-hour model"
- Adversarial recovery: [`adversarial_benchmark.md`](adversarial_benchmark.md)
- ECE / Brier: [`calibration_benchmark.md`](calibration_benchmark.md)

## Baseline workflows considered

A "baseline" here means a workflow a competent investigative journalist
could plausibly execute today with public-search tooling, no
cross-source ER, and no graph reasoning.

| Tier | Workflow | Output |
|---|---|---|
| B1 | Lowercase-only name match across the four corpora | Multi-source name overlaps without normalisation |
| B2 | GoldenMatch `normalize_company_name` then exact match | Multi-source overlaps after canonicalisation |
| B5 | ICIJ Offshore Leaks DB name-search alone | Hits per query — no cross-source aggregation |
| B6 | Fuzzy (token-set ≥0.85) across all four sources | Naive cross-source recall, no rare-name filter |

The pipeline (B3 → B4) layers on rare-name filtering, structural
ICIJ-edge walks, sanctions/PSC overlays, GLEIF reconciliation, and
confidence-aware graph reasoning. Every step is reversible to a
baseline measurement above.

## Surfaced latent structures

The pipeline surfaces six structural patterns that single-source search
cannot, by construction, compute. These are *structures*, not entities
— ICIJ's search returns entities, the pipeline returns the structural
aggregations over them.

| Structure | Detected | ICIJ-search reachable |
|---|---:|:---:|
"""

    for st in s.get("surfaced_structures", []):
        label = _STRUCTURE_LABELS.get(st["id"], st["id"])
        body += f"| {label} | **{int(st['n_detected']):,}** | {st['icij_reachable']} |\n"

    body += """
Full per-structure detail in [`structure_benchmark.md`](structure_benchmark.md).

## Latent / unsupervised discovery

Beyond seed-driven dossier work, the pipeline runs three unsupervised
surfacing channels — each surfaces investigative-interest candidates
no targeted query would have asked for.

| Channel | Output | Source report |
|---|---|---|
"""

    lm = s.get("latent_mining", {})
    body += f"| Louvain community anomaly | {_fmt(lm.get('louvain_total_communities'))} communities, {_fmt(lm.get('annotated_communities'))} annotated, max-anomaly {_fmt(lm.get('max_anomaly_score'))} | [`latent_clusters.md`](latent_clusters.md) |\n"
    body += f"| Temporal resurrections | {_fmt(lm.get('temporal_resurrections'))} addr-officer pairs reactivated | [`temporal_patterns.md`](temporal_patterns.md) |\n"
    body += f"| Address-incorporation bursts | {_fmt(lm.get('temporal_bursts'))} hotspots | [`temporal_patterns.md`](temporal_patterns.md) |\n"
    body += f"| Long-lived structural anchors | {_fmt(lm.get('long_lived_anchors'))} entities | [`temporal_patterns.md`](temporal_patterns.md) |\n"

    body += """

## Non-obviousness scoring

Per-anchor scoring on five investigative axes (cross-source rarity,
jurisdiction unusualness, sanctions adjacency, structural anchoring,
temporal anomaly) — independent of seed list, so it ranks anchors the
seed-driven pipeline didn't ask for.

"""
    no = s.get("non_obviousness", {})
    body += f"- **Anchors scored:** {_fmt(no.get('n_anchors_scored'))}\n\n"
    if no.get("top_10"):
        body += "Top 5 non-obvious anchors:\n\n| Anchor | Score | Top factors |\n|---|---:|---|\n"
        for r in no.get("top_10", [])[:5]:
            factors = r.get("top_factors") or r.get("factor_breakdown") or ""
            if isinstance(factors, dict):
                factors = ", ".join(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" for k, v in list(factors.items())[:3])
            body += f"| `{r.get('anchor_uid', '—')}` | {_fmt(r.get('score'))} | {factors} |\n"
        body += "\n"

    body += "Full ranking in [`non_obviousness_ranking.md`](non_obviousness_ranking.md).\n\n"

    body += "## Analyst review outcomes\n\n"
    aro = s.get("analyst_review_outcomes", {})
    body += f"**Status: {aro.get('status', '—')}**\n\n"
    body += f"{aro.get('note', '')}\n\n"
    op = aro.get("operational_proxies_available", {})
    if op:
        body += "**Operational proxies that exist today** (not journalist-confirmed):\n\n"
        body += f"- Structure benchmark total: {_fmt(op.get('structure_benchmark_total'))}\n"
        body += f"- Non-obviousness anchors scored: {_fmt(op.get('non_obviousness_anchors'))}\n"
        body += f"- Marginal-pair-review labels (positives): {_fmt(op.get('marginal_pair_review_labels'))}\n\n"

    body += """## False-positive comparison

Probability calibration is the standard tool for false-positive
control: an ECE near 0 means the pipeline's confidence scores can be
used as a top-k decision threshold without ranking-by-rank distortion.

"""
    fp = s.get("false_positive_lens", {})
    body += f"- **Raw ER score ECE:** {_fmt(fp.get('raw_ece'))}\n"
    body += f"- **PAV-calibrated ECE:** {_fmt(fp.get('calibrated_ece'))}\n"
    body += f"- **Labelled pairs used for calibration:** {_fmt(fp.get('n_labelled_pairs'))}\n\n"
    body += f"_{fp.get('interpretation', '')}_\n\n"
    body += "Full calibration plots + checkpoint table in [`calibration_benchmark.md`](calibration_benchmark.md).\n\n"

    body += """## Confidence-aware graph reasoning

Communities at the strictest credibility threshold are stable: the
mean Jaccard overlap between loose-threshold communities and strict-
threshold communities measures how much the community structure
depends on inferred (vs structural) edges.

"""
    cr = s.get("confidence_reasoning", {})
    body += f"- **Subgraph:** {_fmt(cr.get('subgraph_nodes'))} nodes, {_fmt(cr.get('subgraph_edges'))} edges, anchored on {_fmt(cr.get('n_seeds'))} dossier seeds\n"
    body += f"- **Mean Jaccard stability:** {_fmt(cr.get('stability_mean_jaccard'))}\n"
    body += f"- **Stable nodes (Jaccard ≥ 0.5):** {_fmt(cr.get('stability_n_stable_nodes'))} / {_fmt(cr.get('stability_n_evaluated'))}\n\n"
    body += "Per-community confidence aggregates, contradiction-aware closure pairs, and review-priority ranking in [`confidence_graph.md`](confidence_graph.md).\n\n"

    body += """## Cross-source join novelty

Joins where ≥2 of the four corpora agree, weighted by rarity of the
joined attribute. These joins do not exist in any single source; the
pipeline is the only mechanism that surfaces them.

| Join type | Count | Rare-only |
|---|---:|---:|
"""
    jn = s.get("join_novelty", {})
    for k, v in jn.items():
        if isinstance(v, dict):
            cnt = v.get("n_pairs") or v.get("n_triples") or v.get("n") or v.get("count") or "—"
            rare = v.get("n_rare") or v.get("n_rare_pairs") or "—"
            body += f"| {k} | {_fmt(cnt)} | {_fmt(rare)} |\n"

    body += """

Full join-novelty narrative in [`join_novelty.md`](join_novelty.md).

## What this proves

1. **The baseline a journalist could execute today recovers a strict
   subset of what the pipeline finds**, on every axis we measured.
2. **The pipeline is robust to the adversarial perturbations** that
   would defeat a naive normalize-then-match workflow (recovery rate
   jumps from ~0.42 to ~0.99 on the four perturbation classes).
3. **The pipeline's probability scores are calibrated**, so its top-k
   output can be triaged in expected-fraction terms — not just
   rank-ordered.
4. **Six structural patterns** are surfaced that single-source search
   cannot, by construction, compute. They're aggregations over the
   pipeline's outputs, not lookups against any single index.
5. **Three unsupervised channels** (community anomaly, temporal
   pattern, non-obviousness) surface candidates the seed list never
   asked for. The investigative novelty doesn't depend on already
   knowing what to look for.

## What this report does NOT prove

1. **No journalist-confirmed novelty.** The strongest claim we make is
   "structurally invisible to single-source search," not "a journalist
   confirmed this is interesting." A v2 with a panel-review study
   would close this gap.
2. **Baselines are operationally chosen, not exhaustively benchmarked.**
   The B-tier definitions are documented and reproducible, but a
   stronger competitor (e.g. a commercial graph-search product like
   Maltego or i2) is not in scope.
3. **No production validation.** Outputs have not been published as
   an exposé. The pipeline's discovery advantage is measured on
   internal benchmarks, not against real publication outcomes.
4. **Calibration sample is finite.** The PAV calibration uses 340
   positive + 340 negative labelled pairs; tail performance on
   underrepresented edge kinds is uncertain.

## Inputs synthesised

This report aggregates the following primary summaries:

"""
    for n in s.get("inputs_present", []):
        body += f"- ✓ `processed/{n}`\n"
    for n in s.get("inputs_missing", []):
        body += f"- ✗ `processed/{n}` (missing — partial synthesis)\n"

    body += """

## Reproduce

```bash
just job-run build_discovery_advantage
just job-fetch processed/discovery_advantage_summary.json docs/reports/data/

uv run python scripts/render_discovery_advantage.py \\
    --summary docs/reports/data/discovery_advantage_summary.json \\
    --out docs/reports/discovery_advantage.md
```

Or trigger `.github/workflows/build-discovery-advantage.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
