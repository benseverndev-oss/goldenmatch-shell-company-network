"""Render docs/reports/temporal_patterns.md from the Railway artifacts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    resurrections: Path = typer.Option(..., "--resurrections"),
    bursts: Path = typer.Option(..., "--bursts"),
    anchors: Path = typer.Option(..., "--anchors"),
    summary: Path = typer.Option(..., "--summary"),
    out: Path = typer.Option(Path("docs/reports/temporal_patterns.md"), "--out"),
) -> None:
    res = pl.read_parquet(resurrections)
    bur = pl.read_parquet(bursts)
    anc = pl.read_parquet(anchors)
    s = json.loads(summary.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    rs = s["resurrections"]
    bs = s["bursts"]
    as_ = s["long_lived_anchors"]

    body = f"""# Temporal patterns — incorporation / dissolution dynamics

_Generated {now} from `processed/temporal_*.parquet`. The dossier
pipeline is structural and static; this report covers the time
dimension._

## Why this report exists

ICIJ leaks carry `incorporation_date` for {s["input_entities"]:,} entities
({s["input_entities"]:,} total). 96.8% have it; 42% also carry a
`dissolution_date`. That's enough to surface three temporal signatures
the static-graph reports can't see.

## 1. Resurrection pattern

> An entity dissolves, then a new entity is incorporated at the same
> normalized address within a {rs["window_days"]}-day window. The shell-network's
> "we got named in a leak, dissolve and reincorporate" move.

| Metric | Value |
|---|---:|
| Resurrection pairs found | **{rs["n_pairs"]:,}** |
| Median gap (dissolve → re-incorporate) | {rs["median_gap_days"] or "—"} days |
| Top-N written | {rs["n_kept"]:,} |

### Tightest resurrections (smallest gap)

| Old entity | Dissolved | New entity | Re-incorporated | Gap (days) | Jurisdiction |
|---|---|---|---|---:|---|
"""

    for r in res.head(10).iter_rows(named=True):
        body += (
            f"| {r['old_name']} | {r['d_date']} | {r['new_name']} | "
            f"{r['i_date']} | {int(r['gap_days'])} | "
            f"{r['old_juris'] or '—'} → {r['new_juris'] or '—'} |\n"
        )

    body += f"""

## 2. Burst incorporations

> ≥{bs["min_count"]} entities incorporated at the same normalized address
> within a {bs["window_days"]}-day window. Coordinated registration waves —
> formation-agent batches, scheme launches, or sanctions-driven flight.

| Metric | Value |
|---|---:|
| Address×window bursts found | **{bs["n_address_windows"]:,}** |
| Largest single burst | {bs["largest_burst"]:,} entities |
| Top-N written | {bs["n_kept"]:,} |

### Densest bursts (smallest span for {bs["min_count"]} entities)

| Address | Span (days) | Jurisdiction | Sample window |
|---|---:|---|---|
"""

    for r in bur.head(10).iter_rows(named=True):
        addr = (r.get("normalized_address") or "—")[:80]
        ws = r.get("window_start", "?")
        we = r.get("window_end", "?")
        body += (
            f"| `{addr}` | {int(r.get('span_days', 0))} | "
            f"{r.get('jurisdiction') or '—'} | {ws} → {we} |\n"
        )

    body += f"""

## 3. Long-lived anchors

> Entities incorporated > {as_["min_years"]} years ago, still active (no
> dissolution date), at addresses also hosting many recently-incorporated
> shells. Old anchor entities for shell-rotation patterns.

| Metric | Value |
|---|---:|
| Long-lived anchors found | **{as_["n_anchors"]:,}** |
| Top-N written | {as_["n_kept"]:,} |

### Top anchors by recent-activity at shared address

| Anchor entity | Address | Jurisdiction | Incorporated | Recent at addr |
|---|---|---|---|---:|
"""

    for r in anc.head(10).iter_rows(named=True):
        addr = (r.get("address") or "—")[:80]
        body += (
            f"| {r['name']} | `{addr}` | "
            f"{r['jurisdiction'] or '—'} | {r['incorporated']} | "
            f"{int(r['n_recent_at_addr'])} |\n"
        )

    body += """

## What this report does NOT prove

1. **Address normalization is imperfect.** Two slightly-different
   address strings can refer to the same physical location; burst /
   resurrection counts are lower bounds.
2. **No officer-level temporal join.** A more powerful "resurrection"
   would require the SAME officer or beneficial owner to appear in
   the new entity. Currently we only key on address.
3. **No cross-leak normalization.** Panama Papers and Pandora Papers
   may record the same physical office with different ICIJ-internal
   address IDs. Both patterns would be stronger if address dedup were
   global.
4. **Recent-activity threshold is hard-coded** (>=2020 incorporations
   for the long-lived-anchor count). Move the threshold and the
   ranking shifts.

## Reproduce

```bash
just job-run build_temporal_patterns
for p in processed/temporal_resurrections.parquet \\
         processed/temporal_bursts.parquet \\
         processed/temporal_long_lived.parquet \\
         processed/temporal_patterns_summary.json; do
    just job-fetch "$p" docs/reports/data/
done

uv run python scripts/render_temporal_patterns.py \\
    --resurrections docs/reports/data/temporal_resurrections.parquet \\
    --bursts docs/reports/data/temporal_bursts.parquet \\
    --anchors docs/reports/data/temporal_long_lived.parquet \\
    --summary docs/reports/data/temporal_patterns_summary.json \\
    --out docs/reports/temporal_patterns.md
```

Or trigger `.github/workflows/build-temporal-patterns.yml`.
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
