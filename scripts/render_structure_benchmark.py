"""Render docs/reports/structure_benchmark.md from the Railway summary JSON."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


_STRUCTURE_NAMES = {
    "S1_latent_intermediary_reuse": "Latent intermediary reuse",
    "S2_jurisdiction_bridges": "Unexpected jurisdiction bridges",
    "S3_hidden_registry_anchors": "Hidden registry anchors (ICIJ ↔ GLEIF)",
    "S4_sanctions_adjacent_closure": "Sanctions-adjacent community closure",
    "S5_fragmented_ownership_convergence": "Fragmented ownership convergence",
    "S6_anomalous_communities": "Anomalous community structures (top-50)",
}


@app.command()
def main(
    summary: Path = typer.Option(..., "--summary"),
    out: Path = typer.Option(Path("docs/reports/structure_benchmark.md"), "--out"),
) -> None:
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""# Non-obvious investigative structure benchmark

_Generated {now} from `processed/structure_benchmark_summary.json`._

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
"""

    for k, label in _STRUCTURE_NAMES.items():
        n = int(s["structures"][k]["n_detected"])
        body += f"| {k[:2]} | {label} | **{n:,}** | ✗ |\n"

    body += f"""
| | **Total pipeline structures** | **{s["totals"]["total_pipeline_structures"]:,}** | |

All six "ICIJ-search alone" cells are ✗ by construction. ICIJ Offshore
Leaks DB doesn't compute these aggregations — it's a per-record search
index. The structural signal is not "ICIJ search misses some entities";
it's "ICIJ search cannot answer these structural questions at all."

## Per-structure detail

"""

    for k, label in _STRUCTURE_NAMES.items():
        st = s["structures"][k]
        base = s["baseline_reachability"].get(k[:2], "—")
        body += f"### {label}\n\n"
        body += f"**Detected: {int(st['n_detected']):,}**\n\n"
        body += f"_Baseline reachability:_ {base}\n\n"

        if k == "S1_latent_intermediary_reuse":
            body += f"_Definition:_ ICIJ intermediaries (`intermediary_of` target) linked to ≥{int(st.get('min_clients_threshold', 3))} distinct officers.\n\n"
            if st["top_5"]:
                body += "Top intermediaries by client count:\n\n| Intermediary UID | Distinct clients |\n|---|---:|\n"
                for r in st["top_5"]:
                    body += f"| `{r['dst_node']}` | {int(r['n_clients']):,} |\n"
                body += "\n"
        elif k == "S2_jurisdiction_bridges":
            body += "_Definition:_ company pairs sharing an officer where one company is in a high-risk offshore jurisdiction ({vg, ky, bm, pa, bs, ai, tc, vc, ms, im, je, gg, cy}) and the other is in a mainstream OECD venue ({gb, us, fr, de, nl, ch, lu, ie, se, no, fi, dk, ca, au, jp}).\n\n"
            if st["top_5"]:
                body += "Sample bridges:\n\n| Company A | Juris A | Company B | Juris B |\n|---|---|---|---|\n"
                for r in st["top_5"]:
                    body += f"| `{r['company_a']}` | {r['juris_a'] or '—'} | `{r['company_b']}` | {r['juris_b'] or '—'} |\n"
                body += "\n"
        elif k == "S3_hidden_registry_anchors":
            body += "_Definition:_ ICIJ entities that match a GLEIF LEI but carry no sanctions-list flag. Formal-registry presence without disclosure trigger.\n\n"
            body += f"- Distinct ICIJ uids: **{int(st.get('distinct_icij_uids', 0)):,}**\n"
            body += f"- Distinct LEIs: **{int(st.get('distinct_leis', 0)):,}**\n\n"
            if st["top_5"]:
                body += "Top hidden anchors:\n\n| ICIJ name | Juris | GLEIF name | LEI |\n|---|---|---|---|\n"
                for r in st["top_5"]:
                    body += f"| {r.get('target_name', '—')} | {r.get('target_jurisdiction') or '—'} | {r.get('ref_name', '—')} | `{r.get('ref_lei', '—')}` |\n"
                body += "\n"
        elif k == "S4_sanctions_adjacent_closure":
            body += "_Definition:_ latent-cluster communities (from `latent_clusters.parquet`) containing ≥1 entity whose normalized name matches a sanctions-overlay alias.\n\n"
            if st["top_5"]:
                body += "Top sanctions-adjacent communities:\n\n| Community | Size | Jurisdictions | Sanctioned | Anomaly |\n|---:|---:|---|---:|---:|\n"
                for r in st["top_5"]:
                    body += f"| {int(r['community_id'])} | {int(r['size'])} | {r.get('jurisdictions', '—')} | {int(r['n_sanctioned'])} | {float(r['anomaly_score']):.3f} |\n"
                body += "\n"
        elif k == "S5_fragmented_ownership_convergence":
            body += f"_Definition:_ addresses hosting between {int(st['min_entities'])} and {int(st['max_entities'])} entities (not formation-agent hubs), where ≥{int(st['min_distinct_officers'])} distinct officers appear across the hosted companies.\n\n"
            if st["top_5"]:
                body += "Top addresses:\n\n| Address | Companies | Distinct officers |\n|---|---:|---:|\n"
                for r in st["top_5"]:
                    addr = (r.get('normalized_address') or '—')[:80]
                    body += f"| `{addr}` | {int(r['n_companies'])} | {int(r['n_distinct_officers'])} |\n"
                body += "\n"
        elif k == "S6_anomalous_communities":
            body += "_Definition:_ top-50 from `latent_clusters.parquet` by anomaly score (computed without seed bias on the full ICIJ corpus).\n\n"
            body += f"- Median size: **{int(st.get('median_size', 0))}**\n"
            body += f"- Max anomaly score: **{float(st.get('max_anomaly', 0)):.3f}**\n\n"
            if st["top_5"]:
                body += "Top 5:\n\n| Community | Size | Jurisdictions | Sanctioned | Anomaly |\n|---:|---:|---|---:|---:|\n"
                for r in st["top_5"]:
                    body += f"| {int(r['community_id'])} | {int(r['size'])} | {r.get('jurisdictions', '—')} | {int(r['n_sanctioned'])} | {float(r['anomaly_score']):.3f} |\n"
                body += "\n"

    body += """

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

uv run python scripts/render_structure_benchmark.py \\
    --summary docs/reports/data/structure_benchmark_summary.json \\
    --out docs/reports/structure_benchmark.md
```

Or trigger `.github/workflows/build-structure-benchmark.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
