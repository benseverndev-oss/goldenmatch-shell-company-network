"""Render docs/reports/validation_queue.md from validation_queue.parquet + summary JSON.

The top-N candidates from build_validation_queue.py, each presented as a
self-contained card with the supporting evidence a human reviewer needs
to begin the deep-validation in docs/validation/template.md.

This is the input to Step 3 (manual validation), NOT a validation itself.
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
    queue: Path = typer.Option(..., "--queue"),
    summary: Path = typer.Option(..., "--summary"),
    out: Path = typer.Option(Path("docs/reports/validation_queue.md"), "--out"),
) -> None:
    df = pl.read_parquet(queue)
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    w = s.get("weighting", {})
    dist = s.get("priority_distribution", {})
    att = s.get("attestation_pools", {})

    body = f"""# Validation queue — top candidates for manual deep-review

_Generated {now} from `processed/validation_queue.parquet` and
`processed/validation_queue_summary.json`._

This is the **input to Step 3 (manual validation)** of the four-step
discovery workflow. Each candidate below is a cluster ranked by a
single composite score combining four axes; the per-candidate cards
provide the supporting evidence a reviewer needs to start the workbook
in [`docs/validation/template.md`](../validation/template.md).

**This report is not a validation.** No cluster below has been
journalist-confirmed. The ranking is a triage queue.

## The composite score

```
{s.get("formula", "")}
```

with weights:

| Axis | Variable | Default weight | What it captures |
| --- | --- | ---: | --- |
| Structurally strange | α | **{w.get("alpha", 1.2)}** | Anomaly score from `confidence_community_anomalies.parquet` — high seed-density + isolation + size-deviation |
| High-confidence | β | **{w.get("beta", 1.0)}** | `cluster_confidence` from formal uncertainty propagation (mean credibility × contradiction penalty) |
| Highly connected | γ | **{w.get("gamma", 0.7)}** | log(size) / log(max_size) — large clusters score higher |
| Underreported | δ | **{w.get("delta", 1.3)}** | 1 − fraction of member names appearing in OS / GLEIF / UK PSC / UK disqualified |

Defaults privilege **weird + unreported** over **big + safe**. The α/δ
weighting was chosen so a strange-but-small cluster outranks a
large-but-attested one, on the basis that step 3 validation has the
most leverage on findings that are unreachable from single-source
search.

## Scope

{s.get("scope_note", "")}

| Stat | Value |
| --- | ---: |
| Communities eligible (size ≥ 3) | {s.get("n_communities_eligible", 0):,} |
| Top-N surfaced here | {s.get("top_n", 0):,} |
| Max cluster size in scope | {s.get("max_cluster_size", 0):,} |
| Priority score — max | {dist.get("max", 0):.4f} |
| Priority score — p95 | {dist.get("p95", 0):.4f} |
| Priority score — median | {dist.get("median", 0):.4f} |
| Priority score — min | {dist.get("min", 0):.4f} |

Attestation pools (size of each name set used for the underreported axis):

| Source | Names |
| --- | ---: |
| OpenSanctions | {att.get("OpenSanctions", 0):,} |
| GLEIF | {att.get("GLEIF", 0):,} |
| UK PSC | {att.get("UK_PSC", 0):,} |
| UK disqualified | {att.get("UK_disqualified", 0):,} |
| Union | {att.get("union", 0):,} |

## How to use this queue

1. Open [`docs/validation/template.md`](../validation/template.md).
2. For each candidate below, copy the template to
   `docs/validation/cluster_{{community_id}}.md` and fill in the
   structured sections (discovery path, graph evolution, provenance
   chain, contradictory evidence, uncertainty preserved, verdict).
3. After validation, the confirmed candidates feed into the
   publication template at
   [`docs/reports/publication_template.md`](publication_template.md).

## Candidates

"""

    for i, r in enumerate(df.iter_rows(named=True), 1):
        cid = int(r["community_id"])
        body += f"### {i}. Community #{cid}\n\n"
        body += f"**Priority score:** **{float(r['priority_score']):.4f}**\n\n"
        body += "**Score breakdown:**\n\n"
        body += "| Axis | Value |\n| --- | ---: |\n"
        body += f"| Structurally strange (anomaly) | {float(r['anomaly_score']):.3f} |\n"
        body += f"| High-confidence (cluster_confidence) | {float(r['cluster_confidence']):.3f} |\n"
        body += f"| Highly connected (log-size norm) | {float(r['connectedness']):.3f} |\n"
        body += (
            f"| Underreported (1 − attestation density) | {float(r['underreportedness']):.3f} |\n\n"
        )

        body += "**Cluster diagnostics:**\n\n"
        body += f"- Size: **{int(r['size'])}** entities\n"
        body += f"- Mean edge credibility: {float(r['mean_edge_credibility']):.3f}\n"
        body += f"- Contradiction density: {float(r['contradiction_density']):.3f}\n"
        body += f"- Seed nodes (from dossier set): {int(r['n_seeds'])}\n"
        body += f"- Isolation: {float(r['isolation']):.3f}\n"
        body += f"- Attestation density: {float(r['attestation_density']):.3f} (low = underreported)\n\n"

        names = r.get("member_names_sample") or []
        if names:
            body += "**Member sample (first 10):**\n\n"
            for n in names[:10]:
                body += f"- `{n}`\n"
            body += "\n"

        body += (
            "**Validation workbook:** create "
            f"`docs/validation/cluster_{cid}.md` from "
            "[`docs/validation/template.md`](../validation/template.md) "
            "and complete the structured review.\n\n"
        )
        body += "---\n\n"

    body += """## Caveats

1. **Scope is dossier-anchored.** The confidence subgraph anchors on
   363 dossier seeds. A truly corpus-wide variant (running confidence-
   graph scoring on all 3.3M edges) would change the queue
   composition; that's parked because it requires non-trivial Railway
   re-architecture.
2. **Attestation is name-equality.** A name matching in OS / GLEIF /
   UK PSC does not confirm same-entity; it only proves the lower bound
   that something with the same name is in that registry. Used here as
   a *very* conservative "is this entity even reachable from formal
   sources" proxy.
3. **Priority ≠ truth.** A high priority score means the cluster is
   the highest-leverage candidate for manual review; it does not mean
   the cluster represents real coordinated activity. Step 3 is where
   that determination happens.
4. **Weights are operator-set.** Defaults (α=1.2, β=1.0, γ=0.7,
   δ=1.3) are documented choices, not learned. Re-rank with different
   exponents by passing `--alpha / --beta / --gamma / --delta` to
   `build_validation_queue.py`.

## Reproduce

```bash
just job-run build_validation_queue
just job-fetch processed/validation_queue.parquet docs/reports/data/
just job-fetch processed/validation_queue_summary.json docs/reports/data/

uv run python scripts/render_validation_queue.py \\
    --queue docs/reports/data/validation_queue.parquet \\
    --summary docs/reports/data/validation_queue_summary.json \\
    --out docs/reports/validation_queue.md
```

Or trigger `.github/workflows/build-validation-queue.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
