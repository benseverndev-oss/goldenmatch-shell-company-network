"""Rank every multi-member dedupe cluster by *investigative value*.

    uv run python scripts/rank_by_investigative_value.py

Produces the 'why this matters' leaderboard — complementary to
``scripts/rank_clusters.py``, which ranks by defensibility (dedupe
integrity). If ``cluster_ranking.parquet`` from the defensibility
ranker is on disk, this script joins it into the Markdown table so
the two scores appear side-by-side: clusters that rank high on
*both* are the strongest publication candidates.

Membership comes from Postgres ``shellnet.clusters`` (latest company
dedupe run) when ``DATABASE_URL`` is set; otherwise pass
``--clusters-parquet`` to read from a local parquet (offline / fixture
mode).
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer
from dotenv import load_dotenv

from shellnet.investigations.investigative_ranking import (
    rank_clusters_by_investigative_value,
    render_investigative_ranking_markdown,
)
from shellnet.paths import relpath_for_report

load_dotenv()

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _read_optional_parquet(path: Path | None) -> pl.DataFrame | None:
    if path is None or not path.exists():
        return None
    try:
        return pl.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not read %s: %s", path, exc)
        return None


def _load_clusters_from_postgres(conn) -> tuple[dict[int, list[str]], str]:
    """Pull every multi-member cluster from the latest company dedupe run."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT run_id FROM shellnet.runs WHERE what='company' ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("no company run in shellnet.runs")
        run_id = str(row[0])
        cur.execute(
            """
            WITH cnt AS (
                SELECT cluster_id, COUNT(*) AS n
                FROM shellnet.clusters
                WHERE run_id = %s
                GROUP BY cluster_id
                HAVING COUNT(*) >= 2
            )
            SELECT c.cluster_id, c.entity_uid
            FROM shellnet.clusters c
            JOIN cnt USING (cluster_id)
            WHERE c.run_id = %s
            """,
            (run_id, run_id),
        )
        members: dict[int, list[str]] = defaultdict(list)
        for cid, uid in cur.fetchall():
            members[int(cid)].append(uid)
    return dict(members), run_id


def _load_clusters_from_parquet(
    clusters_df: pl.DataFrame, min_members: int = 2
) -> dict[int, list[str]]:
    if clusters_df.height == 0:
        return {}
    members: dict[int, list[str]] = defaultdict(list)
    for r in clusters_df.select(["cluster_id", "entity_uid"]).iter_rows(named=True):
        members[int(r["cluster_id"])].append(r["entity_uid"])
    return {cid: uids for cid, uids in members.items() if len(uids) >= min_members}


@app.command()
def main(
    processed_dir: Path = typer.Option(
        Path("/data/processed"), "--processed-dir", help="Override the processed dir."
    ),
    interim_dir: Path = typer.Option(
        Path("/data/interim"), "--interim-dir", help="Override the interim dir."
    ),
    centrality_parquet: Path = typer.Option(
        Path("/data/processed/cluster_centrality.parquet"),
        "--centrality-parquet",
        help="Optional per-node centrality parquet from compute_centrality.py.",
    ),
    sanctions_parquet: Path | None = typer.Option(
        None,
        "--sanctions-parquet",
        help="Optional list-match anchor parquet (target_entity_uid, ref_*, score, ...).",
    ),
    rank_parquet: Path = typer.Option(
        Path("/data/reports/generated/cluster_ranking.parquet"),
        "--rank-parquet",
        help="Defensibility ranking parquet (joined into the Markdown if present).",
    ),
    clusters_parquet: Path | None = typer.Option(
        None,
        "--clusters-parquet",
        help=(
            "Offline fallback: a parquet with (cluster_id, entity_uid). Used when "
            "DATABASE_URL is not set (or --no-postgres is passed)."
        ),
    ),
    out_md: Path = typer.Option(
        Path("/data/reports/generated/cluster_investigative_ranking.md"),
        "--out-md",
        help="Where to write the Markdown leaderboard.",
    ),
    top_n: int = typer.Option(50, "--top-n", help="Rows in the Markdown table."),
    no_postgres: bool = typer.Option(
        False, "--no-postgres", help="Skip Postgres even if DATABASE_URL is set."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # ----- Membership -----
    dedupe_run_id: str | None = None
    members: dict[int, list[str]] = {}
    if not no_postgres and os.environ.get("DATABASE_URL"):
        try:
            import psycopg

            with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
                members, dedupe_run_id = _load_clusters_from_postgres(conn)
        except ImportError:
            log.warning("DATABASE_URL set but psycopg not installed; using parquet fallback")
        except Exception as exc:  # noqa: BLE001
            log.warning("Postgres path failed (%s); using parquet fallback", exc)

    if not members:
        offline = _read_optional_parquet(clusters_parquet)
        if offline is None:
            raise typer.BadParameter(
                "no cluster membership available — set DATABASE_URL or pass --clusters-parquet."
            )
        members = _load_clusters_from_parquet(offline)
    log.info("loaded %d multi-member cluster(s)", len(members))

    # ----- Inputs -----
    company_path = processed_dir / "company_entities.parquet"
    if not company_path.exists():
        raise typer.BadParameter(
            f"company_entities.parquet not found at {company_path}. "
            "Run scripts/build_candidate_tables.py first."
        )
    company_df = pl.read_parquet(company_path)
    log.info("loaded %d unified company rows", company_df.height)

    edges_df = _read_optional_parquet(interim_dir / "icij_edges.parquet")
    addresses_df = _read_optional_parquet(interim_dir / "icij_addresses.parquet")
    officers_df = _read_optional_parquet(interim_dir / "icij_officers.parquet")
    intermediaries_df = _read_optional_parquet(interim_dir / "icij_intermediaries.parquet")
    centrality_df = _read_optional_parquet(centrality_parquet)
    sanctions_df = _read_optional_parquet(sanctions_parquet)
    defensibility_df = _read_optional_parquet(rank_parquet)
    log.info(
        "inputs: edges=%s centrality=%s sanctions=%s defensibility=%s",
        "yes" if edges_df is not None else "missing",
        "yes" if centrality_df is not None else "missing",
        "yes" if sanctions_df is not None else "missing",
        "yes" if defensibility_df is not None else "missing",
    )

    # ----- Rank -----
    ranking = rank_clusters_by_investigative_value(
        members,
        company_df=company_df,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
        centrality_df=centrality_df,
        sanctions_df=sanctions_df,
    )
    log.info(
        "scored %d cluster(s); top score %.2f",
        ranking.height,
        ranking["investigative_score"].max() if ranking.height else 0.0,
    )

    # ----- Persist -----
    inputs_meta = {
        "company_table": relpath_for_report(company_path),
        "edges": relpath_for_report(interim_dir / "icij_edges.parquet")
        if edges_df is not None
        else "(missing)",
        "centrality": relpath_for_report(centrality_parquet)
        if centrality_df is not None
        else "(missing)",
        "defensibility": relpath_for_report(rank_parquet)
        if defensibility_df is not None
        else "(missing)",
    }
    md = render_investigative_ranking_markdown(
        ranking,
        defensibility_df=defensibility_df,
        top_n=top_n,
        dedupe_run_id=dedupe_run_id,
        generated_at=datetime.now(UTC),
        inputs_meta=inputs_meta,
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    log.info("wrote %s (top %d)", out_md, min(top_n, ranking.height))

    out_parquet = out_md.with_suffix(".parquet")
    ranking.write_parquet(out_parquet)
    log.info("wrote %s (%d rows)", out_parquet, ranking.height)
    print(str(out_md))


if __name__ == "__main__":
    app()
