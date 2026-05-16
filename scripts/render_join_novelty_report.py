"""Render docs/reports/join_novelty.md from the Railway-produced summary.

Designed to run inside GitHub Actions (after the workflow has pulled
``processed/join_novelty.parquet`` and ``processed/join_novelty_summary.json``
from the Railway service). No heavy compute — just templating.

Inputs and output paths are CLI flags so the workflow can point at
artifacts on the runner without touching ``/data``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


def _render_company_table(df: pl.DataFrame) -> str:
    if df.height == 0:
        return "_No company-side triples found in the current run._\n"
    cols = ["icij_name", "os_name", "gleif_name", "lei", "icij_jurisdiction", "sanction_list_count"]
    rows = df.select(cols).to_dicts()
    out = [
        "| ICIJ name | OS name | GLEIF name | LEI | Jurisdiction | OS list count |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(
            "| {icij_name} | {os_name} | {gleif_name} | `{lei}` | {icij_jurisdiction} | {sanction_list_count} |".format(
                **{k: ("" if v is None else str(v).replace("|", "\\|")) for k, v in r.items()}
            )
        )
    return "\n".join(out) + "\n"


def _render_person_table(df: pl.DataFrame, *, limit: int = 50) -> str:
    if df.height == 0:
        return "_No DOB-confirmed sanctioned-officer pairs found in the current run._\n"
    cols = ["psc_name", "os_name", "psc_dob", "psc_country", "sanction_datasets", "name_score"]
    rows = df.head(limit).select(cols).to_dicts()
    out = [
        "| UK PSC officer | OS sanctioned name | DOB | Country | Sanction lists | Name score |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(
            "| {psc_name} | {os_name} | {psc_dob} | {psc_country} | {sanction_datasets} | {name_score:.3f} |".format(
                **{
                    k: ("" if v is None else (v if isinstance(v, float) else str(v).replace("|", "\\|")))
                    for k, v in r.items()
                }
            )
        )
    return "\n".join(out) + "\n"


@app.command()
def main(
    parquet: Path = typer.Option(..., "--parquet", help="join_novelty.parquet from Railway."),
    summary: Path = typer.Option(..., "--summary", help="join_novelty_summary.json from Railway."),
    out: Path = typer.Option(
        Path("docs/reports/join_novelty.md"), "--out", help="Markdown destination."
    ),
    person_limit: int = typer.Option(
        50, "--person-limit", help="Max person rows in the table (parquet keeps more)."
    ),
) -> None:
    df = pl.read_parquet(parquet)
    s = json.loads(summary.read_text(encoding="utf-8"))

    company = df.filter(pl.col("kind") == "company_triple")
    persons = df.filter(pl.col("kind") == "dob_confirmed_pair").filter(
        pl.col("evasion_signal_single_list_non_ofac")
    )

    cs = s["company_triples"]
    ps = s["dob_confirmed_pairs"]
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""# Newly surfaced cross-source joins

_Generated {now} by `scripts/render_join_novelty_report.py` from a Railway-side
build of `scripts/build_join_novelty_report.py`. See
[`docs/prior_art_comparison.md`](../prior_art_comparison.md) for what makes
these "newly surfaced" versus what ICIJ Offshore Leaks DB / OCCRP Aleph
already surface._

## Summary

| Kind | Rows | Distinct anchors | With evasion signal | With UK-disq overlap |
|---|---:|---:|---:|---:|
| ICIJ + OS + GLEIF company triples | {cs["n_rows"]} | {cs["distinct_leis"]} LEIs | {cs["with_evasion_signal"]} | {cs["with_disqualified_director_overlap"]} |
| DOB-confirmed OS↔UK_PSC pairs | {ps["n_rows"]} | {ps["distinct_os_uids"]} sanctioned IDs | {ps["with_evasion_signal"]} | {ps["with_disqualified_director_overlap"]} |

**Evasion signal** = `n_datasets == 1` on the sanctions overlay AND
`us_ofac_sdn` is absent — the regional-list-but-not-OFAC pattern the
overlay was designed to surface.

## 1. Company triples (ICIJ + OpenSanctions + GLEIF)

Same legal entity referenced by all three datasets. Invisible to any
single dataset's UI — ICIJ's Offshore Leaks DB doesn't show GLEIF LEIs;
OpenSanctions doesn't surface ICIJ leak provenance; GLEIF doesn't
flag sanctions status.

{_render_company_table(company)}

### Jurisdiction distribution

| Jurisdiction | Triples |
|---|---:|
"""
    for j in cs["jurisdiction_distribution"]:
        body += f"| {j['icij_jurisdiction'] or '(none)'} | {j['len']} |\n"

    body += f"""

## 2. DOB-confirmed sanctioned officer pairs (OS sanctions ↔ UK PSC)

Sanctioned persons whose name + date-of-birth-year match a UK PSC officer
record. Filtered to the **evasion signal** subset (sanctioned by at least
one government list but absent from OFAC SDN) — top {person_limit} shown,
parquet has the full {persons.height} rows.

{_render_person_table(persons, limit=person_limit)}

## Caveats

- Person matches use **year-only** DOB equality (most UK PSC DOB values
  are month+year). Full date-equal would be stronger but loses recall.
- Name matching uses string similarity; transliteration variants of
  Russian/Ukrainian names produce both real matches (Maslovsky ≡
  Маслоўскі) and false positives (different surnames sharing a
  first name + DOB year). Manual review of the top 50 is recommended
  before any investigative use.
- "Evasion signal" is a *prior* not a verdict — an entity on UA-NSDC
  but not OFAC may be a legitimate Ukrainian-specific listing rather
  than a US compliance gap.
- The 16-triple count for companies is small because GLEIF coverage is
  thinnest among the three sources; the joinable subset is what GLEIF
  carries.

## Reproduce

```bash
# Railway side (produces the two output files on the /data volume):
just job-run build_join_novelty_report
just job-fetch processed/join_novelty.parquet data/processed/
just job-fetch processed/join_novelty_summary.json data/processed/

# Local side (renders this markdown):
uv run python scripts/render_join_novelty_report.py \\
    --parquet data/processed/join_novelty.parquet \\
    --summary data/processed/join_novelty_summary.json \\
    --out docs/reports/join_novelty.md
```

Or trigger the GH Actions workflow `render-novelty-report.yml` which
does both steps and opens a PR with the regenerated report.
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
