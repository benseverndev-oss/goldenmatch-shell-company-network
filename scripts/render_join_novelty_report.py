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
    # Collapse to one row per LEI so the table reads as anchors, not duplicates.
    grouped = df.group_by("lei").agg(
        pl.col("icij_name").n_unique().alias("icij_name_variants"),
        pl.col("icij_name").first().alias("icij_name_sample"),
        pl.col("os_name").first().alias("os_name"),
        pl.col("gleif_name").first().alias("gleif_name"),
        pl.col("icij_jurisdiction").first().alias("icij_jurisdiction"),
        pl.col("sanction_list_count").first().alias("sanction_list_count"),
        pl.col("icij_uid").len().alias("icij_row_count"),
    )
    out = [
        "| LEI | GLEIF name | ICIJ name (sample) | ICIJ row count | OS name | Jurisdiction | OS list count |",
        "|---|---|---|---:|---|---|---:|",
    ]
    for r in grouped.to_dicts():
        out.append(
            "| `{lei}` | {gleif_name} | {icij_name_sample} ({icij_name_variants} variants) | {icij_row_count} | {os_name} | {icij_jurisdiction} | {sanction_list_count} |".format(
                **{k: ("" if v is None else str(v).replace("|", "\\|")) for k, v in r.items()}
            )
        )
    return "\n".join(out) + "\n"


def _render_person_table(df: pl.DataFrame, *, limit: int = 50) -> str:
    if df.height == 0:
        return "_No DOB-confirmed sanctioned-officer pairs found in the current run._\n"
    # One row per sanctioned anchor (os_uid). Show how many PSC seats they hold
    # (psc_uid count) so reviewers see the network footprint, not just names.
    grouped = (
        df.group_by("os_uid")
        .agg(
            pl.col("os_name").first().alias("os_name"),
            pl.col("psc_name").first().alias("psc_name_sample"),
            pl.col("psc_name").n_unique().alias("psc_name_variants"),
            pl.col("psc_uid").n_unique().alias("psc_seats"),
            pl.col("psc_dob").first().alias("psc_dob"),
            pl.col("psc_country").first().alias("psc_country"),
            pl.col("sanction_datasets").first().alias("sanction_datasets"),
            pl.col("name_score").max().alias("name_score"),
        )
        .sort(by=["psc_seats", "name_score"], descending=[True, True])
        .head(limit)
    )
    out = [
        "| Sanctioned name (OS) | UK PSC name | DOB | Country | PSC seats | Sanction lists | Name score |",
        "|---|---|---|---|---:|---|---:|",
    ]
    for r in grouped.to_dicts():
        out.append(
            "| {os_name} | {psc_name_sample} | {psc_dob} | {psc_country} | {psc_seats} | {sanction_datasets} | {name_score:.3f} |".format(
                **{
                    k: ("" if v is None else (v if isinstance(v, float) else str(v).replace("|", "\\|")))
                    for k, v in r.items()
                }
            )
        )
    return "\n".join(out) + "\n"


def _render_icij_psc_table(df: pl.DataFrame, *, limit: int = 50) -> str:
    if df.height == 0:
        return "_No filtered ICIJ↔UK_PSC pairs in the current run._\n"
    # One row per ICIJ uid (a person may sit on multiple UK PSC seats).
    grouped = (
        df.group_by("icij_uid")
        .agg(
            pl.col("icij_name").first(),
            pl.col("psc_name").first().alias("psc_name_sample"),
            pl.col("psc_uid").n_unique().alias("psc_seats"),
            pl.col("country").first(),
            pl.col("name_score").max(),
        )
        .sort(by=["psc_seats", "name_score"], descending=[True, True])
        .head(limit)
    )
    out = [
        "| ICIJ leak name | UK PSC name (sample) | Country | PSC seats | Score |",
        "|---|---|---|---:|---:|",
    ]
    for r in grouped.to_dicts():
        out.append(
            f"| {r['icij_name']} | {r['psc_name_sample']} | {r['country']} | {r['psc_seats']} | {r['name_score']:.3f} |"
        )
    return "\n".join(out) + "\n"


def _render_officer_overlap_table(df: pl.DataFrame, *, limit: int = 50) -> str:
    if df.height == 0:
        return "_No rare multi-source officer names in the current run._\n"
    cols = [c for c in df.columns if c not in ("kind", "n_tokens", "max_per_source")]
    # Want: normalized_name, n_sources, total_entities, per-source counts (the source-named columns)
    source_cols = [c for c in cols if c not in ("normalized_name", "n_sources", "total_entities")]
    show = df.head(limit)
    header_extras = " | ".join(source_cols)
    out = [
        f"| Officer name | n_sources | total | {header_extras} |",
        "|---|---:|---:|" + "---:|" * len(source_cols),
    ]
    for r in show.to_dicts():
        per_src = " | ".join(str(int(r.get(c, 0) or 0)) for c in source_cols)
        out.append(
            f"| {r['normalized_name']} | {int(r['n_sources'])} | {int(r['total_entities'])} | {per_src} |"
        )
    return "\n".join(out) + "\n"


def _render_disq_xref_table(df: pl.DataFrame) -> str:
    if df.height == 0:
        return "_No disqualified-director overlaps in the current run._\n"
    cols = ["source", "name", "country", "disq_person_name", "disq_dob", "disq_length"]
    out = [
        "| Source | Matched name | Country | Disqualified director | DoB | Length |",
        "|---|---|---|---|---|---|",
    ]
    for r in df.select(cols).to_dicts():
        out.append(
            "| {source} | {name} | {country} | {disq_person_name} | {disq_dob} | {disq_length} |".format(
                **{k: ("" if v is None else str(v).replace("|", "\\|")) for k, v in r.items()}
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
    ips = s.get("icij_psc_pairs", {"n_rows": 0, "distinct_psc_uids": 0, "distinct_icij_uids": 0, "country_distribution": []})
    rop = s.get("rare_officer_overlaps", {"n_rows": 0, "by_n_sources": []})
    dxr = s.get("disqualified_overlaps", {"n_rows": 0, "by_source": []})

    icij_psc = df.filter(pl.col("kind") == "icij_psc_pair")
    rare_off = df.filter(pl.col("kind") == "officer_overlap")
    disq_xref = df.filter(pl.col("kind") == "disqualified_overlap")
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    body = f"""# Newly surfaced cross-source joins

_Generated {now} by `scripts/render_join_novelty_report.py` from a Railway-side
build of `scripts/build_join_novelty_report.py`. See
[`docs/prior_art_comparison.md`](../prior_art_comparison.md) for what makes
these "newly surfaced" versus what ICIJ Offshore Leaks DB / OCCRP Aleph
already surface._

## Summary

The headline numbers are **distinct anchors** — the underlying entity
or sanctioned-person being surfaced, not the number of rows. Rows are
inflated by duplicate variants of the same entity (e.g. ICIJ filings
under multiple spellings of the same shell company name).

| Kind | Anchors | (Rows) | Notes |
|---|---:|---:|---|
| 1. ICIJ + OS + GLEIF company triples | **{cs["distinct_leis"]} LEIs** | {cs["n_rows"]} | 3-source company anchors |
| 2. DOB-confirmed OS↔UK_PSC pairs | **{ps["distinct_os_uids"]} sanctioned IDs** | {ps["n_rows"]} | {ps["with_evasion_signal"]} with evasion signal |
| 3. ICIJ↔UK_PSC direct pairs (filtered) | **{ips["distinct_icij_uids"]} ICIJ uids** | {ips["n_rows"]} | same-country, ≥3-token names, score ≥ 0.95 |
| 4. Rare multi-source officer names | {rop["n_rows"]} names | {rop["n_rows"]} | max ≤ 2 per source, ≥ 3 tokens |
| 5. UK disqualified-director cross-refs | {dxr["n_rows"]} matches | {dxr["n_rows"]} | ICIJ + GLEIF only (UK PSC dominated by name collisions) |

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

## 3. ICIJ ↔ UK PSC direct pairs (no sanctions pivot)

Same-country, multi-token-name, high-score matches between ICIJ leak
officers and UK PSC foreign-national directors. Independent of
sanctions status — the cleanest "person in 2 unrelated datasets"
primitive. Top {person_limit} shown.

{_render_icij_psc_table(icij_psc, limit=person_limit)}

### ICIJ↔UK_PSC country distribution

| Country | Pairs |
|---|---:|
"""
    for c in ips["country_distribution"]:
        body += f"| {c['country']} | {c['len']} |\n"

    body += f"""

## 4. Rare multi-source officer names

Normalized officer names appearing in 2+ source datasets, with all of:
**max ≤ 2 entities per source** (so not a common-name explosion),
**≥ 3 tokens** (so not just a first + last name collision), **at least
2 distinct sources**. Top {person_limit} shown.

{_render_officer_overlap_table(rare_off, limit=person_limit)}

## 5. UK disqualified-director cross-references

The 222-row UK Insolvency Service struck-off register cross-referenced
against the **full** unified person + company tables. Filtered to ICIJ
+ GLEIF matches (UK PSC matches are dominated by Singh / Smith / Jones
name collisions and provide no signal).

{_render_disq_xref_table(disq_xref)}

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
