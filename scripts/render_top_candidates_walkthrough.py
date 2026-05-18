"""Render docs/reports/top_candidates_walkthrough.md from the synthesis JSON."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


_CHANNEL_LABELS = {
    "shared_agent_reuse": "Shared intermediary reuse",
    "jurisdiction_bridge": "Cross-jurisdiction officer bridge",
    "louvain_sanctions_adjacent": "Louvain community (sanctions-adjacent)",
    "louvain_anomaly_only": "Louvain community (anomaly-only)",
    "non_obviousness_rank": "Non-obviousness-ranked rare officer",
}


def _attest_row(att: dict | None) -> str:
    if not att:
        return "_(no name-resolvable attestation lookup for this channel)_"
    cells = []
    for src in ("opensanctions", "gleif", "uk_psc", "uk_disqualified"):
        if src in att:
            n = int(att[src])
            mark = "✓" if n > 0 else "✗"
            cells.append(f"`{src}` {mark} ({n})")
    return " · ".join(cells)


@app.command()
def main(
    summary: Path = typer.Option(..., "--summary"),
    out: Path = typer.Option(
        Path("docs/reports/top_candidates_walkthrough.md"), "--out"
    ),
) -> None:
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    cands = s.get("candidates", [])

    body = f"""# Top-candidate walkthrough — per-entity novelty proof

_Generated {now} from `processed/top_candidates_walkthrough.json`.
Companion to [`discovery_advantage.md`](discovery_advantage.md)._

## What this report does

The Discovery Advantage Report quantifies the delta between baseline
and pipeline workflows across the corpus. This report drills down: it
picks **{len(cands)} specific candidates** from {len(s.get("channels", []))} surfacing
channels and, for each one, shows exactly which sources confirm it,
what each single-source query would have returned, and why the
pipeline's view is the novel one.

This is the closing argument made entity-by-entity, not in aggregate.

## How to read each candidate

Each candidate below has:

- **Channel** — which surfacing channel ranked it
- **Source attestation** — `✓`/`✗` against OpenSanctions, GLEIF, UK
  PSC, UK disqualified, with hit counts
- **Baseline view** — what a journalist using single-source search
  would see today
- **Pipeline view** — what GoldenMatch surfaces
- **Novelty proof** — the structural reason the pipeline's view is
  not reachable from any single source

Source attestation is by **name-equality (casefold)** on the canonical
name column of each source. A `✓` means the name appears in that
source; a `✗` means it does not. Hits do not imply the entity is the
same individual — name collisions exist. They prove the lower bound
that single-source search returns *something*.

## Channels covered

| Channel | Candidates |
|---|---:|
"""
    by_channel: dict[str, int] = {}
    for c in cands:
        by_channel[c["channel"]] = by_channel.get(c["channel"], 0) + 1
    for ch, n in sorted(by_channel.items()):
        label = _CHANNEL_LABELS.get(ch, ch)
        body += f"| {label} | {n} |\n"

    body += "\n## Candidates\n\n"

    for i, c in enumerate(cands, 1):
        body += f"### {i}. {c['title']}\n\n"
        body += f"**Channel:** `{c['channel']}` — {_CHANNEL_LABELS.get(c['channel'], '')}\n\n"
        body += f"**UID:** `{c['uid']}`\n\n"
        meta = c.get("meta", {})
        if meta:
            kvs = [f"`{k}` = {v}" for k, v in meta.items() if v not in (None, "")]
            if kvs:
                body += "**Metadata:** " + " · ".join(kvs) + "\n\n"

        metric = c.get("metric", {})
        if metric:
            body += "**Metric:**\n\n"
            for k, v in metric.items():
                body += f"- `{k}`: {v}\n"
            body += "\n"

        samples = c.get("client_samples") or c.get("member_samples") or []
        if samples:
            label = "Client sample" if "client_samples" in c else "Member sample"
            body += f"**{label}:** " + ", ".join(f"`{x}`" for x in samples) + "\n\n"

        att = c.get("attestation")
        if att is not None:
            body += "**Source attestation:** " + _attest_row(att) + "\n\n"

        body += f"**Baseline view (single-source):** {c['baseline_view']}\n\n"
        body += f"**Pipeline view:** {c['pipeline_view']}\n\n"
        body += f"**Novelty proof:** {c['novelty_proof']}\n\n"
        body += "---\n\n"

    body += """## How to interpret across channels

- **Shared intermediaries** are aggregations: every input edge is in
  ICIJ, but no ICIJ UI surfaces the multiplicity. The pipeline's
  contribution is the count and the ranking.
- **Jurisdiction bridges** require officer deduplication + jurisdiction
  classification. They cannot be queried for in any source.
- **Louvain communities** are entirely synthesised. No source has any
  community structure; the cluster *is* the pipeline's output.
- **Non-obviousness-ranked rare officers** combine five orthogonal
  signals into one score; the composition crosses sources even when
  any single input is single-source.

## Caveats

1. **Source attestation is name-equality.** A `✓` confirms the name is
   present in that source; it does not confirm same-person identity.
   A v2 would resolve via deterministic IDs (LEI, PSC officer number)
   where available.
2. **Member samples are heuristic.** For Louvain communities, member
   samples are first-20-by-row-order, not centrality-ranked. Reading
   them as "the most important members" overstates the resolution.
3. **No journalist confirmation.** These are operational signals, not
   journalist-validated exposés. See
   [`discovery_advantage.md`](discovery_advantage.md) §"Analyst review
   outcomes" for the v2 panel-study gap.

## Reproduce

```bash
just job-run build_top_candidates_walkthrough
just job-fetch processed/top_candidates_walkthrough.json docs/reports/data/

uv run python scripts/render_top_candidates_walkthrough.py \\
    --summary docs/reports/data/top_candidates_walkthrough.json \\
    --out docs/reports/top_candidates_walkthrough.md
```

Or trigger `.github/workflows/build-top-candidates-walkthrough.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
