"""Batch seed-query investigation.

    uv run python scripts/investigate_entities.py seeds/epstein_entities.csv

Reads a CSV with at least these columns:

    name,jurisdiction,source_note

For each row, runs the same logic as ``scripts/investigate_entity.py`` and
emits a markdown report per seed. Also writes an index file summarizing
the whole batch alongside the per-seed reports.

The parquet inputs (`company_entities`, `icij_edges`, …) are read once and
shared across all seeds. If ``DATABASE_URL`` is set, *one* connection is
opened and reused for the whole batch.
"""

from __future__ import annotations

import csv
import logging
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer
from dotenv import load_dotenv

from shellnet.investigations.seed_query import (
    BatchRow,
    collect_icij_neighbourhood,
    default_report_path,
    fetch_goldenmatch_context,
    make_seed,
    rank_candidates,
    render_batch_index,
    render_report,
)
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT

load_dotenv()

app = typer.Typer(add_completion=False, no_args_is_help=True)
log = logging.getLogger(__name__)


def _read_optional_parquet(path: Path) -> pl.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pl.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not read %s: %s", path, exc)
        return None


def _read_seeds(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "name" not in reader.fieldnames:
            raise typer.BadParameter(
                f"{path} must have a 'name' column. Got: {reader.fieldnames!r}"
            )
        for raw in reader:
            row = {k: (v or "").strip() for k, v in raw.items()}
            if not row.get("name"):
                continue
            rows.append(row)
    return rows


@app.command()
def main(
    seeds: Path = typer.Argument(..., help="CSV file with name,jurisdiction,source_note columns."),
    top_n: int = typer.Option(25, "--top-n"),
    min_score: float = typer.Option(85.0, "--min-score"),
    global_fallback: bool = typer.Option(True, "--global-fallback/--no-global-fallback"),
    processed_dir: Path = typer.Option(PROCESSED_DIR, "--processed-dir"),
    interim_dir: Path = typer.Option(INTERIM_DIR, "--interim-dir"),
    out_dir: Path = typer.Option(
        PROJECT_ROOT / "reports",
        "--out-dir",
        help="Reports root. Per-seed reports + the index land under `<out-dir>/investigations/batches/<batch-id>/`.",
    ),
    batch_id: str | None = typer.Option(
        None,
        "--batch-id",
        help="Override the auto-derived batch id. Defaults to the seeds-file stem.",
    ),
    no_postgres: bool = typer.Option(False, "--no-postgres"),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast",
        help="Abort the batch on the first error instead of recording it in the index.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    seed_rows = _read_seeds(seeds)
    if not seed_rows:
        raise typer.BadParameter(f"{seeds} has no usable rows (missing 'name'?).")
    log.info("loaded %d seed(s) from %s", len(seed_rows), seeds)

    company_path = processed_dir / "company_entities.parquet"
    if not company_path.exists():
        raise typer.BadParameter(
            f"company_entities.parquet not found at {company_path}. "
            "Run scripts/build_candidate_tables.py first."
        )
    company_df = pl.read_parquet(company_path)
    edges_df = _read_optional_parquet(interim_dir / "icij_edges.parquet")
    addresses_df = _read_optional_parquet(interim_dir / "icij_addresses.parquet")
    officers_df = _read_optional_parquet(interim_dir / "icij_officers.parquet")
    intermediaries_df = _read_optional_parquet(interim_dir / "icij_intermediaries.parquet")
    log.info("loaded %d unified company rows", company_df.height)

    bid = batch_id or re.sub(r"[^A-Za-z0-9._-]+", "_", seeds.stem)
    batch_dir = out_dir / "investigations" / "batches" / bid
    batch_dir.mkdir(parents=True, exist_ok=True)

    conn = None
    if not no_postgres and os.environ.get("DATABASE_URL"):
        try:
            import psycopg

            conn = psycopg.connect(os.environ["DATABASE_URL"])
            log.info("opened postgres connection for batch enrichment")
        except ImportError:
            log.warning("DATABASE_URL set but psycopg not installed; skipping GoldenMatch context")
        except Exception as exc:  # noqa: BLE001
            log.warning("postgres connection failed: %s — continuing without it", exc)

    results: list[BatchRow] = []
    started = time.time()
    try:
        for i, raw in enumerate(seed_rows, start=1):
            name = raw["name"]
            jurisdiction = raw.get("jurisdiction") or None
            source_note = raw.get("source_note") or None
            seed = make_seed(name, jurisdiction)
            log.info(
                "[%d/%d] seed=%r juris=%r → %r/%r",
                i,
                len(seed_rows),
                name,
                jurisdiction,
                seed.normalized_name,
                seed.normalized_jurisdiction,
            )
            try:
                in_juris, outside_juris = rank_candidates(
                    company_df,
                    seed,
                    top_n=top_n,
                    min_score=min_score,
                    include_outside_jurisdiction=global_fallback,
                )
                icij_uids = [c.entity_uid for c in (in_juris + outside_juris) if c.source == "icij"]
                neighbourhoods = collect_icij_neighbourhood(
                    icij_uids,
                    edges_df=edges_df,
                    addresses_df=addresses_df,
                    officers_df=officers_df,
                    intermediaries_df=intermediaries_df,
                    company_df=company_df,
                )
                gm_context = None
                if conn is not None:
                    try:
                        gm_context = fetch_goldenmatch_context(
                            [c.entity_uid for c in in_juris + outside_juris],
                            conn=conn,
                        )
                    except Exception as exc:  # noqa: BLE001
                        log.warning("GoldenMatch lookup failed for %r: %s", name, exc)

                sources_seen = sorted({c.source for c in in_juris + outside_juris})
                inputs_meta = {
                    "company_table": str(company_path),
                    "icij_edges": str(interim_dir / "icij_edges.parquet"),
                    "top_n": top_n,
                    "min_score": min_score,
                    "global_fallback": global_fallback,
                    "seeds_csv": str(seeds),
                }
                md = render_report(
                    seed,
                    in_juris=in_juris,
                    outside_juris=outside_juris,
                    neighbourhoods=neighbourhoods,
                    gm_context=gm_context,
                    sources_seen=sources_seen,
                    inputs_meta=inputs_meta,
                    generated_at=datetime.now(UTC),
                    source_note=source_note,
                    batch_id=bid,
                )
                # Put per-seed reports inside the batch dir so the index can
                # link to them by filename. Prefix with the (1-based) CSV row
                # number so two seeds with the same normalized name + juris
                # cannot collide silently.
                idx_width = max(3, len(str(len(seed_rows))))
                prefix = f"{i:0{idx_width}d}"
                target = batch_dir / f"{prefix}_{default_report_path(out_dir, seed).name}"
                target.write_text(md, encoding="utf-8")
                results.append(
                    BatchRow(
                        seed=seed,
                        source_note=source_note,
                        report_path=target,
                        top_in_juris=in_juris[0] if in_juris else None,
                        n_in_juris=len(in_juris),
                        n_outside_juris=len(outside_juris),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("seed %r failed", name)
                if fail_fast:
                    raise
                results.append(
                    BatchRow(
                        seed=seed,
                        source_note=source_note,
                        report_path=batch_dir / "(none).md",
                        top_in_juris=None,
                        n_in_juris=0,
                        n_outside_juris=0,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
    finally:
        if conn is not None:
            conn.close()

    index_md = render_batch_index(
        results,
        batch_id=bid,
        seeds_path=seeds,
        generated_at=datetime.now(UTC),
    )
    index_path = batch_dir / "index.md"
    index_path.write_text(index_md, encoding="utf-8")
    log.info(
        "batch %s: %d seeds in %.1fs → %s",
        bid,
        len(results),
        time.time() - started,
        index_path,
    )
    print(str(index_path))


if __name__ == "__main__":
    app()
