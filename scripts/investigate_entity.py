"""Seed-query investigation: rank candidates for one (name, jurisdiction)
pair and emit a markdown report.

    uv run python scripts/investigate_entity.py \
        --name "ACME HOLDINGS" --jurisdiction bvi

Reads the unified ``data/processed/company_entities.parquet`` plus the
ICIJ interim parquets for 1-hop neighbourhood context. If ``DATABASE_URL``
is set, also enriches with published GoldenMatch list-match anchors,
cluster memberships, and same-as pairs.

The script never reaches for the network on its own; if the env var
isn't set the GoldenMatch section is simply marked as skipped.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer
from dotenv import load_dotenv

from shellnet.investigations.seed_query import (
    collect_icij_neighbourhood,
    default_report_path,
    fetch_goldenmatch_context,
    make_seed,
    rank_candidates,
    render_report,
)
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT, relpath_for_report

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


@app.command()
def main(
    name: str = typer.Option(..., "--name", help="Seed company name."),
    jurisdiction: str | None = typer.Option(
        None,
        "--jurisdiction",
        help="Seed jurisdiction (ISO-2, ISO-3, or a recognised alias like 'bvi').",
    ),
    top_n: int = typer.Option(25, "--top-n", help="Max candidates per section."),
    min_score: float = typer.Option(
        85.0, "--min-score", help="RapidFuzz token_sort_ratio floor (0-100)."
    ),
    global_fallback: bool = typer.Option(
        True,
        "--global-fallback/--no-global-fallback",
        help="If a jurisdiction is given, also search outside it and list separately.",
    ),
    processed_dir: Path = typer.Option(
        PROCESSED_DIR, "--processed-dir", help="Override the processed-parquet directory."
    ),
    interim_dir: Path = typer.Option(
        INTERIM_DIR, "--interim-dir", help="Override the interim-parquet directory."
    ),
    out_dir: Path = typer.Option(
        PROJECT_ROOT / "reports",
        "--out-dir",
        help="Reports root. The report lands under `<out-dir>/investigations/`.",
    ),
    out_path: Path | None = typer.Option(
        None,
        "--out-path",
        help="Override the auto-generated report path entirely.",
    ),
    no_postgres: bool = typer.Option(
        False,
        "--no-postgres",
        help="Skip the Postgres lookup even if DATABASE_URL is set.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    seed = make_seed(name, jurisdiction)
    log.info(
        "seed: name=%r juris=%r → normalized=%r/%r",
        seed.name,
        seed.jurisdiction,
        seed.normalized_name,
        seed.normalized_jurisdiction,
    )

    company_path = processed_dir / "company_entities.parquet"
    if not company_path.exists():
        raise typer.BadParameter(
            f"company_entities.parquet not found at {company_path}. "
            "Run scripts/build_candidate_tables.py first."
        )
    company_df = pl.read_parquet(company_path)
    log.info("loaded %d unified company rows", company_df.height)

    in_juris, outside_juris = rank_candidates(
        company_df,
        seed,
        top_n=top_n,
        min_score=min_score,
        include_outside_jurisdiction=global_fallback,
    )
    log.info(
        "ranked: %d in-jurisdiction, %d outside-jurisdiction",
        len(in_juris),
        len(outside_juris),
    )

    icij_uids = [c.entity_uid for c in (in_juris + outside_juris) if c.source == "icij"]
    edges_df = _read_optional_parquet(interim_dir / "icij_edges.parquet")
    addresses_df = _read_optional_parquet(interim_dir / "icij_addresses.parquet")
    officers_df = _read_optional_parquet(interim_dir / "icij_officers.parquet")
    intermediaries_df = _read_optional_parquet(interim_dir / "icij_intermediaries.parquet")
    neighbourhoods = collect_icij_neighbourhood(
        icij_uids,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
        company_df=company_df,
    )
    log.info("1-hop ICIJ neighbourhoods built for %d uids", len(neighbourhoods))

    gm_context = None
    if not no_postgres and os.environ.get("DATABASE_URL"):
        try:
            import psycopg
        except ImportError:
            log.warning("DATABASE_URL set but psycopg not installed; skipping GoldenMatch context")
        else:
            all_uids = [c.entity_uid for c in in_juris + outside_juris]
            try:
                with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
                    gm_context = fetch_goldenmatch_context(all_uids, conn=conn)
                log.info(
                    "GoldenMatch: %d anchor(s), %d cluster row(s), %d same-as pair(s)",
                    len(gm_context.list_match_anchors),
                    len(gm_context.cluster_memberships),
                    len(gm_context.same_as_pairs),
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("GoldenMatch context query failed: %s", exc)
                gm_context = None

    sources_seen = sorted({c.source for c in in_juris + outside_juris})
    inputs_meta = {
        "company_table": relpath_for_report(company_path),
        "icij_edges": relpath_for_report(interim_dir / "icij_edges.parquet"),
        "top_n": top_n,
        "min_score": min_score,
        "global_fallback": global_fallback,
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
    )

    target = out_path or default_report_path(out_dir, seed)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(md, encoding="utf-8")
    log.info("wrote %s", target)
    print(str(target))


if __name__ == "__main__":
    app()
