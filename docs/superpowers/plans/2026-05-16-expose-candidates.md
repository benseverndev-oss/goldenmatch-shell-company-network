# Exposé Candidates Pipeline Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the exposé-candidates pipeline specified in `docs/superpowers/specs/2026-05-16-expose-candidates-design.md` — a Railway-side 2-hop graph walk over section-4 rare cross-source officer names, a GH-Actions-side firecrawl freshness check, and a markdown renderer producing per-lead dossiers + a ranked index committed to `main`.

**Architecture:** Same compute split as the existing `render-novelty-report.yml` pipeline. New Railway script emits one denormalized parquet; new Actions workflow downloads it, fans out firecrawl searches, renders the dossier pages + index, and direct-pushes the result to `main`. One new shared module (`src/shellnet/novelty_ranking.py`) holds the scoring function so it's unit-testable.

**Tech Stack:** Python 3.12, polars, typer, FastAPI (existing job server), GitHub Actions, firecrawl HTTP API, the existing Railway shellnet-job service.

---

## File Structure

| Path | New / Modify | Responsibility |
|---|---|---|
| `src/shellnet/novelty_ranking.py` | NEW | Pure function `novelty_score(row, hits)` + auto-pin predicate; the only logic worth unit-testing |
| `tests/test_novelty_ranking.py` | NEW | Unit test locking the score formula + auto-pin predicate |
| `scripts/build_rare_officer_dossiers.py` | NEW | Railway-side: seed selection from `officer_overlap.parquet`, ICIJ 2-hop walk, denormalized parquet emit |
| `src/shellnet/job_server.py` | MODIFY | Add `build_rare_officer_dossiers` allowlist entry |
| `scripts/search_dossier_freshness.py` | NEW | Actions-side: 2-3 firecrawl queries per distinct rare-name in the parquet, write `search_results.json` sidecar |
| `scripts/render_dossiers.py` | NEW | Actions-side: render `docs/reports/dossiers/<slug>.md` + `docs/reports/exposes_candidates.md` from parquet + search-results JSON |
| `.github/workflows/build-exposes-candidates.yml` | NEW | Orchestrator workflow, `workflow_dispatch` only, direct-push to main |
| `docs/reports/dossiers/` | NEW dir | Per-lead `.md` outputs (workflow-managed) |
| `docs/reports/exposes_candidates.md` | NEW | Ranked index (workflow-managed) |
| `docs/reports/data/search_results.json` | NEW | Tracked sidecar so a PR reviewer can diff what firecrawl returned |

---

## Task 1: Novelty-ranking module + unit test

Pure function. TDD it first because everything downstream depends on the score formula.

**Files:**
- Create: `src/shellnet/novelty_ranking.py`
- Test: `tests/test_novelty_ranking.py`

- [ ] **Step 1.1: Write failing tests**

`tests/test_novelty_ranking.py`:

```python
"""Unit tests for novelty_score + auto_pin predicate.

The score is a triage signal; these tests lock the weights so a thoughtless
tweak doesn't silently reshuffle the exposé candidates index.
"""

from __future__ import annotations

import pytest

from shellnet.novelty_ranking import auto_pin, novelty_score


def test_zero_hits_localized_ran_yields_baseline_floor() -> None:
    # No web hits at all (localized RAN with 0 hits), no shell density:
    # max from web terms (0.40 + 0.25 + 0.15 = 0.80)
    score = novelty_score(
        hits_general=0, hits_offshore=0,
        hits_localized=0, localized_ran=True,
        n_linked_companies=0, n_jurisdictions=0,
    )
    assert score == pytest.approx(0.80, abs=1e-6)


def test_localized_skipped_does_not_grant_bonus() -> None:
    # No dominant jurisdiction → localized query SKIPPED.
    # The 0.15 term must NOT apply (was the bug spotted in review pass 2).
    score = novelty_score(
        hits_general=0, hits_offshore=0,
        hits_localized=0, localized_ran=False,
        n_linked_companies=0, n_jurisdictions=0,
    )
    assert score == pytest.approx(0.65, abs=1e-6)  # 0.40 + 0.25 + 0


def test_full_hits_full_density_yields_density_only() -> None:
    # Saturated web hits cancel the web bonus; only density terms contribute
    score = novelty_score(
        hits_general=10, hits_offshore=5,
        hits_localized=3, localized_ran=True,
        n_linked_companies=5, n_jurisdictions=3,
    )
    # 0 + 0 + 0 + 0.10 + 0.10
    assert score == pytest.approx(0.20, abs=1e-6)


def test_localized_zero_hits_when_run_breaks_to_full_bonus() -> None:
    base = dict(hits_general=0, hits_offshore=0, n_linked_companies=0, n_jurisdictions=0)
    score_ran_zero = novelty_score(**base, hits_localized=0, localized_ran=True)
    score_ran_one = novelty_score(**base, hits_localized=1, localized_ran=True)
    assert score_ran_zero - score_ran_one == pytest.approx(0.15, abs=1e-6)


def test_score_bounded_zero_to_one() -> None:
    assert 0.0 <= novelty_score(
        hits_general=0, hits_offshore=0,
        hits_localized=0, localized_ran=True,
        n_linked_companies=0, n_jurisdictions=0,
    ) <= 1.0
    assert 0.0 <= novelty_score(
        hits_general=100, hits_offshore=100,
        hits_localized=100, localized_ran=True,
        n_linked_companies=100, n_jurisdictions=100,
    ) <= 1.0


def test_density_bonus_caps() -> None:
    s5 = novelty_score(
        hits_general=10, hits_offshore=5,
        hits_localized=3, localized_ran=True,
        n_linked_companies=5, n_jurisdictions=0,
    )
    s20 = novelty_score(
        hits_general=10, hits_offshore=5,
        hits_localized=3, localized_ran=True,
        n_linked_companies=20, n_jurisdictions=0,
    )
    assert s5 == s20


def test_auto_pin_requires_zero_web_hits_and_multi_shell() -> None:
    assert auto_pin(hits_general=0, hits_offshore=0, n_linked_companies=3) is True
    assert auto_pin(hits_general=1, hits_offshore=0, n_linked_companies=3) is False
    assert auto_pin(hits_general=0, hits_offshore=1, n_linked_companies=3) is False
    assert auto_pin(hits_general=0, hits_offshore=0, n_linked_companies=2) is False
```

- [ ] **Step 1.2: Run test, confirm it fails**

Run: `uv run pytest tests/test_novelty_ranking.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shellnet.novelty_ranking'`

- [ ] **Step 1.3: Write minimal implementation**

`src/shellnet/novelty_ranking.py`:

```python
"""Novelty scoring for the exposé-candidates pipeline.

Pure function — no I/O, no parquet reads. Imported by render_dossiers.py.
Spec: docs/superpowers/specs/2026-05-16-expose-candidates-design.md
"""

from __future__ import annotations


def novelty_score(
    *,
    hits_general: int,
    hits_offshore: int,
    hits_localized: int,
    localized_ran: bool,
    n_linked_companies: int,
    n_jurisdictions: int,
) -> float:
    """Weighted novelty score in [0, 1].

    Weights are constants locked by unit tests. The spec's earlier draft
    spoke of "operator-tunable via CLI flags"; we reject that as YAGNI —
    changing weights requires touching this function AND updating the
    tests, which is the review gate. Spec amended to match.

    ``localized_ran`` must be True only when the localized firecrawl query
    was actually emitted (the dominant-jurisdiction plurality test passed).
    Skipped-query runs MUST pass False, otherwise every name without a
    dominant jurisdiction gets a free 0.15 bonus — the bug spotted in
    review pass 2.
    """
    offshore_term = 0.40 * (1 - min(hits_offshore / 5, 1.0))
    general_term = 0.25 * (1 - min(hits_general / 10, 1.0))
    localized_term = 0.15 if (localized_ran and hits_localized == 0) else 0.0
    company_density = 0.10 * min(n_linked_companies / 5, 1.0)
    jurisdiction_density = 0.10 * min(n_jurisdictions / 3, 1.0)
    return offshore_term + general_term + localized_term + company_density + jurisdiction_density


def auto_pin(
    *,
    hits_general: int,
    hits_offshore: int,
    n_linked_companies: int,
) -> bool:
    """Whether a candidate gets pinned to the top of the index regardless of score.

    The cleanest 'found-X-first' shape: zero web mentions anywhere AND
    a non-trivial shell-network footprint.
    """
    return hits_general == 0 and hits_offshore == 0 and n_linked_companies >= 3
```

- [ ] **Step 1.4: Run tests, confirm pass**

Run: `uv run pytest tests/test_novelty_ranking.py -v`
Expected: PASS, all 6 tests

- [ ] **Step 1.5: Lint + commit**

```bash
uv run ruff check src/shellnet/novelty_ranking.py tests/test_novelty_ranking.py
git add src/shellnet/novelty_ranking.py tests/test_novelty_ranking.py
git commit -m "feat: novelty_score + auto_pin in shellnet.novelty_ranking

Pure function with unit-test coverage locking the weights. Spec:
docs/superpowers/specs/2026-05-16-expose-candidates-design.md"
```

---

## Task 2: Railway dossier script — seed selection + stub rows

Read `officer_overlap.parquet`, re-apply the rare-name filter (the on-disk parquet has the loose filter; spec requires the tight filter), pick top-N, emit one stub row per matched person from `person_entities`. No graph walk yet.

**Files:**
- Create: `scripts/build_rare_officer_dossiers.py`

- [ ] **Step 2.1: Write the script (seed + stub mode)**

`scripts/build_rare_officer_dossiers.py`:

```python
"""Build per-lead exposé-candidate dossiers from rare cross-source officer names.

Spec: docs/superpowers/specs/2026-05-16-expose-candidates-design.md

Reads officer_overlap.parquet (the section-4 source from join_novelty.md),
re-applies the rare-name filter (the on-disk filter is permissive per
build_officer_overlap.py), picks top-N seeds, and emits one denormalized
parquet row per (rare_name × person × company × attribute-snapshot).

For ICIJ-source persons, walks icij_edges to expand into linked
companies + co-officers + sanctions adjacency (only for OS-sourced
linked companies — see spec Limitations table). For UK PSC / OS
persons, emits only stub rows (no relations parquet exists today).
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


# Rare-name filter from spec. On-disk officer_overlap.parquet has the
# permissive build-time filter (max_per_source <= 50, n_tokens >= 2);
# the tight one we want lives downstream in build_join_novelty_report.
_MAX_PER_SOURCE = 2
_MIN_TOKENS = 3


def _seed_names(officer_overlap: Path, top_n: int) -> pl.DataFrame:
    """Read officer_overlap, apply rare filter, return top-N seeds."""
    raw = pl.read_parquet(officer_overlap)
    return (
        raw.filter(
            (pl.col("max_per_source") <= _MAX_PER_SOURCE)
            & (pl.col("n_tokens") >= _MIN_TOKENS)
            & (pl.col("n_sources") >= 2)
        )
        .sort(by=["n_sources", "total_entities"], descending=[True, True])
        .head(top_n)
    )


def _stub_rows(seeds: pl.DataFrame, person_table: Path) -> pl.DataFrame:
    """One stub row per matched person from person_entities."""
    seed_names = seeds.select("normalized_name").to_series().to_list()
    matched = (
        pl.scan_parquet(person_table)
        .filter(pl.col("normalized_name").is_in(seed_names))
        .select(
            pl.col("normalized_name").alias("rare_name"),
            pl.col("source").alias("person_source"),
            pl.col("entity_uid").alias("person_entity_uid"),
            pl.col("name").alias("person_name"),
            pl.col("country").alias("person_country"),
        )
        .collect()
    )
    return matched.with_columns(
        pl.lit(None).cast(pl.Utf8).alias("company_entity_uid"),
        pl.lit(None).cast(pl.Utf8).alias("company_name"),
        pl.lit(None).cast(pl.Utf8).alias("company_source"),
        pl.lit(None).cast(pl.Utf8).alias("company_jurisdiction"),
        pl.lit(None).cast(pl.Utf8).alias("company_normalized_address"),
        pl.lit(None).cast(pl.List(pl.Utf8)).alias("co_officers"),
        pl.lit(None).cast(pl.Utf8).alias("sanction_datasets"),
        pl.lit(None).cast(pl.Int32).alias("n_sanction_datasets"),
        pl.lit(False).alias("degree_capped"),
    )


@app.command()
def main(
    officer_overlap: Path = typer.Option(
        PROCESSED_DIR / "officer_overlap.parquet",
        "--officer-overlap",
    ),
    person_table: Path = typer.Option(
        PROCESSED_DIR / "person_entities.parquet",
        "--person-table",
    ),
    out: Path = typer.Option(
        PROCESSED_DIR / "rare_officer_dossiers.parquet",
        "--out",
    ),
    top_n: int = typer.Option(50, "--top-n"),
    max_degree: int = typer.Option(25, "--max-degree"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out.parent.mkdir(parents=True, exist_ok=True)
    _ = max_degree  # used in task 3

    seeds = _seed_names(officer_overlap, top_n)
    log.info("seeds selected: %d", seeds.height)

    stubs = _stub_rows(seeds, person_table)
    log.info("stub rows: %d (one per matched person)", stubs.height)

    stubs.write_parquet(out)
    typer.echo(f"Wrote: {out}")
    typer.echo(f"  {stubs.height} stub rows across {seeds.height} seed names")


if __name__ == "__main__":
    app()
```

- [ ] **Step 2.2: Lint**

Run: `uv run ruff check scripts/build_rare_officer_dossiers.py`
Expected: All checks passed

- [ ] **Step 2.3: Smoke-test locally on the cached parquets**

Run:
```bash
uv run python scripts/build_rare_officer_dossiers.py \
  --officer-overlap data/processed/officer_overlap.parquet \
  --person-table data/processed/person_entities.parquet \
  --out /tmp/rare_dossiers_v1.parquet \
  --top-n 50 --verbose
```

Expected output: log lines reporting seeds selected (≥ 50 or close) and stub rows (likely 100-300 — multiple person rows per name). No errors.

If person_entities.parquet isn't local: skip the smoke test, note that the smoke runs server-side in task 8.

- [ ] **Step 2.4: Commit**

```bash
git add scripts/build_rare_officer_dossiers.py
git commit -m "feat: scripts/build_rare_officer_dossiers seed + stub mode

Seed selection from officer_overlap.parquet with the rare filter
re-applied. Emits one stub row per matched person. Graph walk lands
in the next commit."
```

---

## Task 3: Railway dossier script — ICIJ 2-hop walk

Extend the script to walk `icij_edges` for ICIJ-source persons, join companies + sanctions overlay + co-officers, with the `--max-degree` cap.

**Files:**
- Modify: `scripts/build_rare_officer_dossiers.py`

- [ ] **Step 3.1: Add `_expanded_icij_rows` function**

Add to `scripts/build_rare_officer_dossiers.py` (after `_stub_rows`):

```python
def _expanded_icij_rows(
    stubs: pl.DataFrame,
    icij_edges: Path,
    company_table: Path,
    person_table: Path,
    sanctions_overlay: Path,
    max_edges_per_seed: int,
) -> pl.DataFrame:
    """For ICIJ-source person rows in stubs, walk icij_edges to companies.

    Returns rows with the same schema as stubs but with company columns
    populated. Stubs themselves are kept by the caller; this returns the
    extra expanded rows alongside them.
    """
    icij_seeds = stubs.filter(pl.col("person_source") == "icij")
    if icij_seeds.height == 0:
        return stubs.head(0)  # empty same-schema frame

    seed_uids = icij_seeds.select("person_entity_uid").to_series().to_list()

    edges = (
        pl.scan_parquet(icij_edges)
        .filter(
            pl.col("src_node").is_in(seed_uids) | pl.col("dst_node").is_in(seed_uids)
        )
        .collect()
    )

    # Build (seed_uid, other_uid) pairs.
    pairs = (
        pl.concat(
            [
                edges.filter(pl.col("src_node").is_in(seed_uids)).select(
                    pl.col("src_node").alias("seed_uid"),
                    pl.col("dst_node").alias("linked_uid"),
                ),
                edges.filter(pl.col("dst_node").is_in(seed_uids)).select(
                    pl.col("dst_node").alias("seed_uid"),
                    pl.col("src_node").alias("linked_uid"),
                ),
            ],
            how="vertical",
        )
        .unique()
        .filter(pl.col("seed_uid") != pl.col("linked_uid"))
    )

    # Edge-fan-out cap per seed. Note: this caps RAW edges, not linked
    # companies — some edges resolve to addresses or non-company entities
    # and will get filtered out by the company join below. Renaming to
    # max_edges_per_seed for honesty.
    degree_per_seed = pairs.group_by("seed_uid").agg(pl.len().alias("degree"))
    pairs = pairs.join(degree_per_seed, on="seed_uid", how="left")
    capped = pairs.with_columns(
        (pl.col("degree") > max_edges_per_seed).alias("degree_capped")
    )
    capped = capped.sort("linked_uid").group_by("seed_uid").head(max_edges_per_seed)

    # Lookup linked companies (linked_uid that exist in company_entities)
    companies = (
        pl.scan_parquet(company_table)
        .filter(pl.col("entity_uid").is_in(capped.select("linked_uid").to_series().to_list()))
        .select(
            pl.col("entity_uid").alias("company_entity_uid"),
            pl.col("name").alias("company_name"),
            pl.col("source").alias("company_source"),
            pl.col("source_id").alias("company_source_id"),
            pl.col("jurisdiction").alias("company_jurisdiction"),
            pl.col("normalized_address").alias("company_normalized_address"),
        )
        .collect()
    )

    # Sanctions adjacency: only for OS-sourced companies; strip the prefix.
    overlay = pl.read_parquet(sanctions_overlay).select(
        pl.col("os_id"),
        pl.col("datasets").alias("sanction_datasets"),
        pl.col("n_datasets").alias("n_sanction_datasets"),
    )
    companies = companies.with_columns(
        pl.when(pl.col("company_source") == "opensanctions")
        .then(pl.col("company_source_id").str.replace("^opensanctions:", ""))
        .otherwise(None)
        .alias("_os_key")
    )
    companies = companies.join(
        overlay, left_on="_os_key", right_on="os_id", how="left"
    ).drop("_os_key", "company_source_id")

    # Join companies onto the (seed, linked) pairs.
    expanded = (
        capped.rename({"linked_uid": "company_entity_uid"})
        .join(companies, on="company_entity_uid", how="inner")
    )

    # Co-officers: other persons sharing an edge with this company.
    company_uids = expanded.select("company_entity_uid").to_series().to_list()
    co_edges = (
        pl.scan_parquet(icij_edges)
        .filter(
            pl.col("src_node").is_in(company_uids) | pl.col("dst_node").is_in(company_uids)
        )
        .collect()
    )
    co_pairs = pl.concat(
        [
            co_edges.filter(pl.col("src_node").is_in(company_uids)).select(
                pl.col("src_node").alias("company_entity_uid"),
                pl.col("dst_node").alias("co_uid"),
            ),
            co_edges.filter(pl.col("dst_node").is_in(company_uids)).select(
                pl.col("dst_node").alias("company_entity_uid"),
                pl.col("src_node").alias("co_uid"),
            ),
        ],
        how="vertical",
    ).unique()

    # co_uid → normalized_name (only those that are persons in person_entities).
    # Use the explicitly-passed person_table path rather than guessing a
    # sibling filename — the spec doesn't pin layout that strictly.
    co_names = (
        pl.scan_parquet(person_table)
        .filter(pl.col("entity_uid").is_in(co_pairs.select("co_uid").to_series().to_list()))
        .select(
            pl.col("entity_uid").alias("co_uid"),
            pl.col("normalized_name").alias("co_name"),
        )
        .collect()
    )
    co_pairs = co_pairs.join(co_names, on="co_uid", how="inner")
    co_officers = (
        co_pairs.group_by("company_entity_uid")
        .agg(pl.col("co_name").unique().alias("co_officers"))
    )

    expanded = expanded.join(co_officers, on="company_entity_uid", how="left")

    # Join back to seed person info to fill the dossier schema.
    seed_info = icij_seeds.select(
        pl.col("person_entity_uid").alias("seed_uid"),
        "rare_name", "person_source", "person_name", "person_country",
    )
    out = expanded.join(seed_info, on="seed_uid", how="inner").select(
        "rare_name", "person_source",
        pl.col("seed_uid").alias("person_entity_uid"),
        "person_name", "person_country",
        "company_entity_uid", "company_name", "company_source",
        "company_jurisdiction", "company_normalized_address",
        "co_officers", "sanction_datasets",
        pl.col("n_sanction_datasets").cast(pl.Int32),
        "degree_capped",
    )
    return out
```

- [ ] **Step 3.2: Wire it into main()**

Modify `main()` in `scripts/build_rare_officer_dossiers.py`:

Replace:
```python
    stubs = _stub_rows(seeds, person_table)
    log.info("stub rows: %d (one per matched person)", stubs.height)

    stubs.write_parquet(out)
```

With:
```python
    stubs = _stub_rows(seeds, person_table)
    log.info("stub rows: %d", stubs.height)

    expanded = _expanded_icij_rows(
        stubs,
        icij_edges=icij_edges,
        company_table=company_table,
        person_table=person_table,
        sanctions_overlay=sanctions_overlay,
        max_edges_per_seed=max_degree,
    )
    log.info("icij-expanded rows: %d", expanded.height)

    all_rows = pl.concat([stubs, expanded], how="diagonal_relaxed")
    log.info("total dossier rows: %d", all_rows.height)
    all_rows.write_parquet(out)
```

And add the new CLI options before `top_n`:

```python
    icij_edges: Path = typer.Option(
        INTERIM_DIR / "icij_edges.parquet",
        "--icij-edges",
    ),
    company_table: Path = typer.Option(
        PROCESSED_DIR / "company_entities.parquet",
        "--company-table",
    ),
    sanctions_overlay: Path = typer.Option(
        PROCESSED_DIR / "sanctions_overlay.parquet",
        "--sanctions-overlay",
    ),
```

Remove the `_ = max_degree` line.

- [ ] **Step 3.3: Lint**

Run: `uv run ruff check scripts/build_rare_officer_dossiers.py`
Expected: All checks passed

- [ ] **Step 3.4: Smoke-test locally if data available**

```bash
uv run python scripts/build_rare_officer_dossiers.py \
  --officer-overlap data/processed/officer_overlap.parquet \
  --person-table data/processed/person_entities.parquet \
  --icij-edges data/interim/icij_edges.parquet \
  --company-table data/processed/company_entities.parquet \
  --sanctions-overlay data/processed/sanctions_overlay.parquet \
  --out /tmp/rare_dossiers_v2.parquet \
  --top-n 50 --max-degree 25 --verbose
```

Expected: stub rows + icij-expanded rows logged; no errors. Inspect the parquet briefly:

```bash
uv run python -c "
import polars as pl
df = pl.read_parquet('/tmp/rare_dossiers_v2.parquet')
print('rows:', df.height)
print(df.head(3))
print('person_source distribution:')
print(df.group_by('person_source').len())
"
```

If `person_entities.parquet` or `icij_edges.parquet` aren't local: skip smoke, validate server-side in Task 8.

- [ ] **Step 3.5: Commit**

```bash
git add scripts/build_rare_officer_dossiers.py
git commit -m "feat: icij 2-hop walk in build_rare_officer_dossiers

For ICIJ-source persons: walk icij_edges to linked companies (capped
at --max-degree), join sanctions_overlay via source_id prefix strip
(OS-sourced companies only), derive co-officers via a second edge
scan. UK PSC / OS persons remain as stubs per spec."
```

---

## Task 4: Allowlist entry on the Railway job server

**Files:**
- Modify: `src/shellnet/job_server.py`

- [ ] **Step 4.1: Add allowlist entry**

In `src/shellnet/job_server.py`, in the `_ALLOWED_SCRIPTS` dict, add immediately before `"build_join_novelty_report"`:

```python
    "build_rare_officer_dossiers": [
        "scripts/build_rare_officer_dossiers.py",
        "--officer-overlap",
        "/data/processed/officer_overlap.parquet",
        "--person-table",
        "/data/processed/person_entities.parquet",
        "--icij-edges",
        "/data/interim/icij_edges.parquet",
        "--company-table",
        "/data/processed/company_entities.parquet",
        "--sanctions-overlay",
        "/data/processed/sanctions_overlay.parquet",
        "--out",
        "/data/processed/rare_officer_dossiers.parquet",
    ],
```

- [ ] **Step 4.2: Lint**

Run: `uv run ruff check src/shellnet/job_server.py`
Expected: All checks passed

- [ ] **Step 4.3: Commit**

```bash
git add src/shellnet/job_server.py
git commit -m "chore: allowlist entry for build_rare_officer_dossiers"
```

---

## Task 5: Actions-side firecrawl search

**Files:**
- Create: `scripts/search_dossier_freshness.py`

- [ ] **Step 5.1: Write the script**

`scripts/search_dossier_freshness.py`:

```python
"""Run firecrawl queries per rare-name in a dossier parquet.

Spec: docs/superpowers/specs/2026-05-16-expose-candidates-design.md (Web search section)

Reads rare_officer_dossiers.parquet, runs 2-3 firecrawl queries per
distinct rare_name (general, offshore, optionally localized), writes
the hits as a sidecar JSON. Per-name failures are isolated; the batch
keeps going.

Auth: FIRECRAWL_API_KEY env var (provisioned as a GH Actions secret).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


_FIRECRAWL_URL = "https://api.firecrawl.dev/v1/search"


def _dominant_jurisdiction(df: pl.DataFrame, rare_name: str) -> str | None:
    """Plurality jurisdiction across the rare-name's linked companies.

    Returns None on ties (margin < 2 over runner-up).
    """
    js = (
        df.filter(pl.col("rare_name") == rare_name)
        .filter(pl.col("company_jurisdiction").is_not_null())
        .group_by("company_jurisdiction")
        .len()
        .sort("len", descending=True)
    )
    if js.height == 0:
        return None
    if js.height == 1:
        return js[0, "company_jurisdiction"]
    top, runner = js[0, "len"], js[1, "len"]
    if (top - runner) < 2:
        return None
    return js[0, "company_jurisdiction"]


def _firecrawl_search(
    client: httpx.Client, api_key: str, query: str, limit: int
) -> list[dict[str, Any]]:
    """Single firecrawl query. Returns hit dicts or [] on failure."""
    try:
        resp = client.post(
            _FIRECRAWL_URL,
            json={"query": query, "limit": limit},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        if resp.status_code == 429:
            log.warning("firecrawl rate-limited for %r", query)
            return []
        if resp.status_code >= 500:
            log.warning("firecrawl 5xx for %r: %s", query, resp.status_code)
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", []) or data.get("results", []) or []
    except (httpx.HTTPError, httpx.ReadTimeout, ValueError) as exc:
        log.warning("firecrawl exception for %r: %s", query, exc)
        return []


@app.command()
def main(
    parquet: Path = typer.Option(..., "--parquet", help="rare_officer_dossiers.parquet"),
    out: Path = typer.Option(..., "--out", help="search_results.json output path"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        log.error("FIRECRAWL_API_KEY env var not set")
        sys.exit(2)

    df = pl.read_parquet(parquet)
    rare_names = df.select("rare_name").unique().to_series().to_list()
    log.info("running firecrawl for %d rare names", len(rare_names))

    results: dict[str, dict[str, list[dict[str, Any]] | str]] = {}
    with httpx.Client() as client:
        for i, name in enumerate(rare_names, start=1):
            log.info("[%d/%d] %s", i, len(rare_names), name)
            top_juris = _dominant_jurisdiction(df, name)
            row: dict[str, list[dict[str, Any]] | str] = {
                "general": _firecrawl_search(client, api_key, f'"{name}"', 5),
                "offshore": _firecrawl_search(
                    client,
                    api_key,
                    f'"{name}" (shell OR offshore OR director OR PSC)',
                    5,
                ),
                "localized": (
                    _firecrawl_search(client, api_key, f'"{name}" {top_juris}', 3)
                    if top_juris
                    else []
                ),
                "dominant_jurisdiction": top_juris or "",
            }
            results[name] = row

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 5.2: Lint**

Run: `uv run ruff check scripts/search_dossier_freshness.py`
Expected: All checks passed

- [ ] **Step 5.3: Commit**

```bash
git add scripts/search_dossier_freshness.py
git commit -m "feat: search_dossier_freshness — firecrawl queries per rare name

Reads rare_officer_dossiers.parquet, runs 2-3 queries per distinct
rare_name (general / offshore / optional localized via dominant
jurisdiction), writes search_results.json. Per-name failures
isolated; FIRECRAWL_API_KEY from env."
```

---

## Task 6: Render dossiers + ranked index

**Files:**
- Create: `scripts/render_dossiers.py`

- [ ] **Step 6.1: Write the script**

`scripts/render_dossiers.py`:

```python
"""Render per-lead exposé dossiers + the ranked candidate index.

Spec: docs/superpowers/specs/2026-05-16-expose-candidates-design.md
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import typer

from shellnet.novelty_ranking import auto_pin, novelty_score

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(name: str) -> str:
    s = _SLUG_RE.sub("-", name.lower()).strip("-")
    return s or "unnamed"


def _hits_section(label: str, query: str, hits: list[dict[str, Any]]) -> str:
    if not hits:
        return f"### `{query}` — 0 hits\n_No hits._\n"
    lines = [f"### `{query}` — {len(hits)} hits"]
    for h in hits:
        title = (h.get("title") or "(no title)").replace("|", "\\|")
        url = h.get("url") or h.get("link") or ""
        snippet = (h.get("description") or h.get("snippet") or "").replace("\n", " ")
        lines.append(f"- [{title}]({url}) — _{snippet[:200]}_")
    return "\n".join(lines) + "\n"


def _render_one(
    rare_name: str,
    rows: pl.DataFrame,
    hits: dict[str, list[dict[str, Any]] | str],
    score: float,
    pinned: bool,
    now: str,
) -> str:
    expanded = rows.filter(pl.col("company_entity_uid").is_not_null())
    n_companies = expanded.select("company_entity_uid").unique().height
    jurisdictions = (
        expanded.filter(pl.col("company_jurisdiction").is_not_null())
        .select("company_jurisdiction")
        .unique()
        .to_series()
        .to_list()
    )
    sources = rows.select("person_source").unique().to_series().to_list()
    degree_capped = bool(rows.select(pl.col("degree_capped").any()).item())

    h_general = hits.get("general") or []
    h_offshore = hits.get("offshore") or []
    h_localized = hits.get("localized") or []
    top_juris = hits.get("dominant_jurisdiction") or ""

    body = [
        f"# {rare_name}",
        "",
        (
            f"**Sources:** {len(sources)} ({', '.join(sources)})  •  "
            f"**Linked companies:** {n_companies}  •  "
            f"**Jurisdictions:** {', '.join(jurisdictions) or '—'}  •  "
            f"**Novelty score:** {score:.2f}"
            f"{'  •  📌 **auto-pinned (no web mentions + multi-shell)**' if pinned else ''}"
            f"{'  •  ⚠️ degree-capped (partial picture)' if degree_capped else ''}"
        ),
        "",
        "## Linked entities by source",
    ]
    for src in sorted(sources):
        sub = rows.filter(pl.col("person_source") == src)
        n_ents = sub.select("person_entity_uid").unique().height
        body.append(f"### {src} ({n_ents} {'entity' if n_ents == 1 else 'entities'})")
        for r in sub.select(["person_name", "person_entity_uid", "person_country"]).unique().to_dicts():
            body.append(
                f"- {r['person_name']} — `{r['person_entity_uid']}` — country: {r['person_country'] or '—'}"
            )
        if src == "icij" and expanded.height > 0:
            body.append("")
            body.append("**Linked companies (ICIJ 2-hop walk):**")
            for c in expanded.select(
                ["company_name", "company_jurisdiction", "sanction_datasets", "company_normalized_address"]
            ).unique().to_dicts():
                sanc = c["sanction_datasets"] or "—"
                body.append(
                    f"- {c['company_name']} ({c['company_jurisdiction'] or '—'}) — "
                    f"address: `{(c['company_normalized_address'] or '—')[:80]}` — "
                    f"sanctions: {sanc}"
                )
        elif src in ("uk_psc", "opensanctions"):
            body.append(
                f"  _(stub only — no person→company relations parquet for {src} in v1)_"
            )
        body.append("")

    body.extend(
        [
            "## Web search (firecrawl, " + now.split(" ")[0] + ")",
            "",
            _hits_section("offshore", f'"{rare_name}" (shell OR offshore OR director OR PSC)', list(h_offshore)),
            _hits_section("general", f'"{rare_name}"', list(h_general)),
        ]
    )
    if top_juris:
        body.append(_hits_section("localized", f'"{rare_name}" {top_juris}', list(h_localized)))

    body.extend(
        [
            "## Reproduce",
            "",
            f"- `processed/rare_officer_dossiers.parquet`, filter `rare_name == \"{rare_name}\"`",
            "- Search ran via `scripts/search_dossier_freshness.py` on " + now.split(" ")[0],
        ]
    )
    return "\n".join(body) + "\n"


@app.command()
def main(
    parquet: Path = typer.Option(..., "--parquet", help="rare_officer_dossiers.parquet"),
    search_results: Path = typer.Option(..., "--search-results", help="search_results.json"),
    out_dir: Path = typer.Option(Path("docs/reports"), "--out-dir"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    df = pl.read_parquet(parquet)
    searches: dict[str, dict[str, Any]] = json.loads(search_results.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    dossiers_dir = out_dir / "dossiers"
    dossiers_dir.mkdir(parents=True, exist_ok=True)

    # Score each rare name + render its dossier.
    index_rows: list[dict[str, Any]] = []
    rare_names = df.select("rare_name").unique().to_series().to_list()
    written_slugs: set[str] = set()
    for rare_name in rare_names:
        rows = df.filter(pl.col("rare_name") == rare_name)
        expanded = rows.filter(pl.col("company_entity_uid").is_not_null())
        n_companies = expanded.select("company_entity_uid").unique().height
        n_juris = (
            expanded.filter(pl.col("company_jurisdiction").is_not_null())
            .select("company_jurisdiction")
            .unique()
            .height
        )
        hits = searches.get(rare_name, {"general": [], "offshore": [], "localized": [], "dominant_jurisdiction": ""})
        n_general = len(hits.get("general") or [])
        n_offshore = len(hits.get("offshore") or [])
        n_localized = len(hits.get("localized") or [])
        # localized_ran == True only when the localized query was emitted:
        # the search step writes a non-empty dominant_jurisdiction iff it
        # passed the plurality-with-margin test in search_dossier_freshness.
        localized_ran = bool(hits.get("dominant_jurisdiction"))
        n_sanc_adj = expanded.filter(pl.col("sanction_datasets").is_not_null()).height

        score = novelty_score(
            hits_general=n_general,
            hits_offshore=n_offshore,
            hits_localized=n_localized,
            localized_ran=localized_ran,
            n_linked_companies=n_companies,
            n_jurisdictions=n_juris,
        )
        pinned = auto_pin(
            hits_general=n_general,
            hits_offshore=n_offshore,
            n_linked_companies=n_companies,
        )

        slug = _slug(rare_name)
        written_slugs.add(slug)
        (dossiers_dir / f"{slug}.md").write_text(
            _render_one(rare_name, rows, hits, score, pinned, now),
            encoding="utf-8",
        )
        index_rows.append(
            {
                "name": rare_name,
                "slug": slug,
                "sources": rows.select("person_source").unique().height,
                "companies": n_companies,
                "jurisdictions": n_juris,
                "sanc_adj": n_sanc_adj,
                "hits_offshore": n_offshore,
                "score": score,
                "pinned": pinned,
            }
        )

    # Sort: pinned first, then score DESC.
    index_rows.sort(key=lambda r: (-int(r["pinned"]), -r["score"]))

    # Render the index.
    idx = [
        "# Exposé candidates — rare cross-source officer overlaps",
        "",
        f"_Generated {now} from `processed/rare_officer_dossiers.parquet` + `search_results.json`._",
        "",
        "Score is a triage signal, not a verdict — open each dossier and judge.",
        "📌 = auto-pinned (zero web mentions + ≥3 linked companies).",
        "",
        "| Rank | Name | Sources | Companies | Juris | Sanctions adj | Web hits (offshore) | Score | Dossier |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(index_rows, start=1):
        pin = "📌 " if r["pinned"] else ""
        idx.append(
            f"| {i} | {pin}{r['name']} | {r['sources']} | {r['companies']} | "
            f"{r['jurisdictions']} | {r['sanc_adj']} | {r['hits_offshore']} | "
            f"{r['score']:.2f} | [→](dossiers/{r['slug']}.md) |"
        )

    # Orphaned dossiers footer.
    existing = {p.stem for p in dossiers_dir.glob("*.md")}
    orphans = sorted(existing - written_slugs)
    if orphans:
        idx.append("")
        idx.append("## Orphaned dossiers")
        idx.append("")
        idx.append("_These dossiers were rendered by a previous run but fell out of the current top-N._")
        idx.append("")
        for slug in orphans:
            idx.append(f"- [`{slug}`](dossiers/{slug}.md)")

    (out_dir / "exposes_candidates.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    typer.echo(f"Wrote: {out_dir}/exposes_candidates.md")
    typer.echo(f"  + {len(written_slugs)} dossier .md files in {dossiers_dir}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 6.2: Lint**

Run: `uv run ruff check scripts/render_dossiers.py`
Expected: All checks passed

- [ ] **Step 6.3: Commit**

```bash
git add scripts/render_dossiers.py
git commit -m "feat: render_dossiers — per-lead .md + ranked index

Reads rare_officer_dossiers.parquet + search_results.json. Renders
docs/reports/dossiers/<slug>.md per lead (with full graph context,
firecrawl hits, score). Emits docs/reports/exposes_candidates.md
ranked by (pinned, score). Stale dossier files surfaced in an
orphaned footer rather than deleted."
```

---

## Task 7: GH Actions workflow

**Files:**
- Create: `.github/workflows/build-exposes-candidates.yml`

- [ ] **Step 7.1: Write the workflow**

`.github/workflows/build-exposes-candidates.yml`:

```yaml
name: build exposé candidates (Railway-side compute)

# Refreshes docs/reports/exposes_candidates.md + docs/reports/dossiers/*.md.
#
# 1. Triggers build_rare_officer_dossiers on Railway (heavy 2-hop walk
#    on the multi-GB person + edge tables on /data).
# 2. Downloads the small dossier parquet to the runner.
# 3. Fires firecrawl queries per distinct rare-name.
# 4. Renders the per-lead dossier .md files + the ranked index.
# 5. Direct-pushes to main (enterprise policy blocks PR creation).
#
# Spec: docs/superpowers/specs/2026-05-16-expose-candidates-design.md

on:
  workflow_dispatch:
    inputs:
      top_n:
        description: "Seed-name cap fed to Railway script"
        required: true
        default: "50"
        type: string
      max_degree:
        description: "Per-seed edge fan-out cap for the 2-hop walk"
        required: true
        default: "25"
        type: string

concurrency:
  group: build-exposes-candidates
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  build:
    name: Railway compute, runner render, direct-push
    runs-on: ubuntu-latest
    timeout-minutes: 30
    env:
      SHELLNET_JOB_URL: ${{ vars.SHELLNET_JOB_URL }}
      SHELLNET_JOB_TOKEN: ${{ secrets.SHELLNET_JOB_TOKEN }}
      FIRECRAWL_API_KEY: ${{ secrets.FIRECRAWL_API_KEY }}
      TOP_N: ${{ inputs.top_n }}
      MAX_DEGREE: ${{ inputs.max_degree }}
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Sync deps
        run: uv sync --frozen --no-dev

      - name: Confirm Railway reachable
        run: |
          set -euo pipefail
          curl -fsS "$SHELLNET_JOB_URL/healthz"

      - name: Trigger build_rare_officer_dossiers on Railway
        run: |
          set -euo pipefail
          curl -fsS -X POST \
            -H "Authorization: Bearer $SHELLNET_JOB_TOKEN" \
            "$SHELLNET_JOB_URL/run-script?name=build_rare_officer_dossiers"
          echo

      - name: Poll until build completes
        run: |
          set -euo pipefail
          stage="script_build_rare_officer_dossiers"
          for _ in $(seq 1 360); do
            sleep 5
            s=$(curl -fsS -H "Authorization: Bearer $SHELLNET_JOB_TOKEN" \
                "$SHELLNET_JOB_URL/status" \
                | python -c "import sys,json; d=json.load(sys.stdin); print(d['stages'].get('$stage',{}).get('status','?'))")
            echo "  $stage: $s"
            case "$s" in
              completed) break ;;
              failed)
                echo "::error::$stage failed"
                curl -fsS -H "Authorization: Bearer $SHELLNET_JOB_TOKEN" \
                  "$SHELLNET_JOB_URL/logs/$stage?tail=120" || true
                exit 1
                ;;
            esac
          done

      - name: Download dossier parquet
        run: |
          set -euo pipefail
          mkdir -p data/processed
          curl -fsS -H "Authorization: Bearer $SHELLNET_JOB_TOKEN" \
            "$SHELLNET_JOB_URL/download?path=processed/rare_officer_dossiers.parquet" \
            -o data/processed/rare_officer_dossiers.parquet
          ls -lh data/processed/rare_officer_dossiers.parquet

      - name: Run firecrawl search per rare name
        run: |
          set -euo pipefail
          mkdir -p docs/reports/data
          uv run python scripts/search_dossier_freshness.py \
            --parquet data/processed/rare_officer_dossiers.parquet \
            --out docs/reports/data/search_results.json \
            --verbose

      - name: Render dossiers + index
        run: |
          set -euo pipefail
          uv run python scripts/render_dossiers.py \
            --parquet data/processed/rare_officer_dossiers.parquet \
            --search-results docs/reports/data/search_results.json \
            --out-dir docs/reports \
            --verbose

      - name: Stage tracked copy of the dossier parquet
        run: |
          set -euo pipefail
          cp data/processed/rare_officer_dossiers.parquet \
             docs/reports/data/rare_officer_dossiers.parquet

      - name: Commit + push to main
        run: |
          set -euo pipefail
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add docs/reports/exposes_candidates.md \
                  docs/reports/dossiers/ \
                  docs/reports/data/search_results.json \
                  docs/reports/data/rare_officer_dossiers.parquet
          if git diff --cached --quiet; then
            echo "No changes to commit; report unchanged."
            exit 0
          fi
          git commit -m "report: refresh exposé candidates (top_n=$TOP_N, auto from build-exposes-candidates.yml)"
          git push origin HEAD:main
```

- [ ] **Step 7.2: Lint YAML**

No project ruff/yamllint config. Spot-check with `python -c "import yaml; yaml.safe_load(open('.github/workflows/build-exposes-candidates.yml'))"`:

```bash
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/build-exposes-candidates.yml'))" && echo OK
```

Expected: `OK`

- [ ] **Step 7.3: Commit**

```bash
git add .github/workflows/build-exposes-candidates.yml
git commit -m "feat: build-exposes-candidates GitHub Actions workflow

workflow_dispatch only; runs Railway-side dossier build, downloads the
small parquet, runs firecrawl per rare-name, renders index + per-lead
.md files, direct-pushes to main. Mirrors the render-novelty-report.yml
pattern."
```

---

## Task 8: End-to-end validation

- [ ] **Step 8.1: Push to main**

```bash
gh auth switch -u benzsevern
git push origin main
```

Expected: `main -> main`

- [ ] **Step 8.2: Redeploy Railway**

```bash
railway up --detach --ci --service shellnet-job
```

- [ ] **Step 8.3: Wait for the new allowlist entry to roll**

```bash
for i in $(seq 1 40); do
  out=$(curl -s -X POST \
    -H "Authorization: Bearer $SHELLNET_JOB_TOKEN" \
    "$SHELLNET_JOB_URL/run-script?name=__probe__")
  if echo "$out" | grep -q "build_rare_officer_dossiers"; then
    echo "Railway READY after ${i} polls"
    break
  fi
  printf '.'
  sleep 15
done
```

Expected: `Railway READY after N polls`

- [ ] **Step 8.4: Add FIRECRAWL_API_KEY secret if not already set**

```bash
gh secret list | grep FIRECRAWL_API_KEY || gh secret set FIRECRAWL_API_KEY
```

If not present, `gh secret set` will prompt for the value. Get it from the firecrawl dashboard.

- [ ] **Step 8.5: Trigger the workflow**

```bash
gh workflow run build-exposes-candidates.yml -f top_n=50 -f max_degree=25
sleep 5
gh run list --workflow=build-exposes-candidates.yml --limit 1
```

Get the run ID from the output.

- [ ] **Step 8.6: Wait for completion and inspect**

```bash
RUN_ID=<from previous step>
gh run watch $RUN_ID
gh run view $RUN_ID
```

Expected: green check, "Build on Railway, render on Actions, direct-push" job succeeded.

- [ ] **Step 8.7: Pull the auto-commit + sanity-check the rendered output**

```bash
git pull --ff-only
ls -la docs/reports/dossiers/ | head
head -40 docs/reports/exposes_candidates.md
```

Open 2-3 dossier .md files at random. Confirm:
- Header summary line populated correctly
- ICIJ-source persons have linked companies; UK PSC / OS persons show the stub disclaimer
- Web search section has hits (or "0 hits" if firecrawl returned empty for a rare name)
- Auto-pinned candidates show 📌 in the index

- [ ] **Step 8.8: Commit any local follow-up cleanups (if needed)**

If anything's broken: file an issue, fix in a follow-up commit. The pipeline is now self-refreshing — subsequent runs just rerun `gh workflow run build-exposes-candidates.yml`.

---

## Out of scope (follow-ups, NOT in this plan)

- Materializing UK PSC and OpenSanctions person→company relations parquets (would expand the 2-hop walk to all sources, currently ICIJ-only)
- Prior-coverage scoring for rare-officer rows (existing scorer only covers DOB-confirmed pair rows)
- LLM-drafted lead summaries (we want the human in the loop on "is this new")
- Automated prune of stale dossier files (currently leaves them; surfaces in orphaned footer)
- Shell-cluster catalog (the "Approach C" alternative from /brainstorm)
