"""Cluster Explanation Engine CLI.

Generate an investigator-ready briefing for one or more dedupe clusters.

    uv run python scripts/explain_cluster.py --cluster-id 503264
    uv run python scripts/explain_cluster.py --cluster-ids 1,2,3
    uv run python scripts/explain_cluster.py --top-from-rank 5

Pulls cluster membership from Postgres ``shellnet.clusters`` (latest
company-dedupe run) when ``DATABASE_URL`` is set, or from a local parquet
when ``--clusters-parquet`` is supplied — useful for testing on local
fixtures without standing up Postgres.

Reads the unified ``company_entities.parquet`` and the ICIJ interim
parquets for repeated-feature detection, and optionally
``cluster_centrality.parquet`` for centrality-based hidden-hub annotation.

Writes one Markdown briefing per cluster under
``<reports-dir>/cluster_explanations/cluster_<id>.md`` plus a tiny
``index.md`` listing the batch.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer
from dotenv import load_dotenv

from shellnet.investigations.cluster_explainer import (
    build_explanation,
    default_explanation_path,
    load_cluster_members_from_parquet,
    render_explanation_markdown,
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


def _resolve_cluster_ids(
    cluster_ids_csv: str | None,
    top_from_rank: int,
    rank_parquet: Path,
) -> list[int]:
    if cluster_ids_csv:
        out: list[int] = []
        for tok in cluster_ids_csv.split(","):
            tok = tok.strip()
            if tok:
                out.append(int(tok))
        return out
    if top_from_rank > 0:
        if not rank_parquet.exists():
            raise typer.BadParameter(
                f"--top-from-rank set but {rank_parquet} not found. "
                "Run scripts/rank_clusters.py first or pass --rank-parquet."
            )
        df = pl.read_parquet(rank_parquet)
        sort_col = "score" if "score" in df.columns else df.columns[0]
        return [int(r["cluster_id"]) for r in df.sort(sort_col, descending=True).head(top_from_rank).iter_rows(named=True)]
    return []


def _members_from_postgres(
    conn,
    cluster_id: int,
    run_id: str | None = None,
) -> tuple[list[str], str | None]:
    """Returns (member_uids, resolved_run_id). If run_id is None, uses the
    latest ``shellnet.runs`` row with ``what='company'``."""
    with conn.cursor() as cur:
        if run_id is None:
            cur.execute(
                "SELECT run_id FROM shellnet.runs WHERE what='company' "
                "ORDER BY created_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("no company run in shellnet.runs")
            run_id = str(row[0])
        cur.execute(
            "SELECT entity_uid FROM shellnet.clusters "
            "WHERE run_id=%s AND cluster_id=%s",
            (run_id, cluster_id),
        )
        uids = [uid for (uid,) in cur.fetchall()]
    return uids, run_id


@app.command()
def main(
    cluster_id: int | None = typer.Option(
        None, "--cluster-id", help="A single cluster id to explain."
    ),
    cluster_ids: str | None = typer.Option(
        None, "--cluster-ids", help="Comma-separated cluster ids (e.g. '1,2,3')."
    ),
    top_from_rank: int = typer.Option(
        0,
        "--top-from-rank",
        help="If >0, take the top-N cluster ids from cluster_ranking.parquet by score.",
    ),
    rank_parquet: Path = typer.Option(
        Path("/data/reports/generated/cluster_ranking.parquet"),
        "--rank-parquet",
        help="Cluster-ranking parquet produced by scripts/rank_clusters.py.",
    ),
    clusters_parquet: Path | None = typer.Option(
        None,
        "--clusters-parquet",
        help=(
            "Offline fallback: a parquet with at least (cluster_id, entity_uid). "
            "Used when DATABASE_URL is not set (or --no-postgres is passed)."
        ),
    ),
    processed_dir: Path = typer.Option(
        PROCESSED_DIR, "--processed-dir", help="Override the processed-parquet directory."
    ),
    interim_dir: Path = typer.Option(
        INTERIM_DIR, "--interim-dir", help="Override the interim-parquet directory."
    ),
    centrality_parquet: Path = typer.Option(
        PROCESSED_DIR / "cluster_centrality.parquet",
        "--centrality-parquet",
        help="Per-node centrality parquet from scripts/compute_centrality.py.",
    ),
    sanctions_parquet: Path | None = typer.Option(
        None,
        "--sanctions-parquet",
        help="Optional list-match anchor parquet (target_entity_uid, ref_*, score, ...).",
    ),
    out_dir: Path = typer.Option(
        PROJECT_ROOT / "reports" / "generated",
        "--out-dir",
        help="Reports root. Each briefing lands under `<out-dir>/cluster_explanations/`.",
    ),
    no_postgres: bool = typer.Option(
        False, "--no-postgres", help="Skip Postgres even if DATABASE_URL is set."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    ids = _resolve_cluster_ids(cluster_ids, top_from_rank, rank_parquet)
    if cluster_id is not None:
        ids.append(int(cluster_id))
    ids = sorted({i for i in ids})
    if not ids:
        raise typer.BadParameter(
            "Provide --cluster-id, --cluster-ids, or --top-from-rank > 0."
        )
    log.info("explaining %d cluster(s): %s", len(ids), ids)

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
    sanctions_df = _read_optional_parquet(sanctions_parquet) if sanctions_parquet else None

    pg_conn = None
    dedupe_run_id: str | None = None
    if not no_postgres and os.environ.get("DATABASE_URL"):
        try:
            import psycopg

            pg_conn = psycopg.connect(os.environ["DATABASE_URL"])
        except ImportError:
            log.warning("DATABASE_URL set but psycopg not installed; falling back to parquet")
            pg_conn = None
        except Exception as exc:  # noqa: BLE001
            log.warning("Postgres connect failed (%s); falling back to parquet", exc)
            pg_conn = None

    clusters_offline = (
        _read_optional_parquet(clusters_parquet) if clusters_parquet else None
    )

    written: list[tuple[int, Path, float, int]] = []  # (cluster_id, path, score, n_members)
    try:
        for cid in ids:
            try:
                if pg_conn is not None:
                    member_uids, dedupe_run_id = _members_from_postgres(pg_conn, cid, dedupe_run_id)
                elif clusters_offline is not None:
                    member_uids = load_cluster_members_from_parquet(clusters_offline, cid)
                else:
                    raise RuntimeError(
                        "no cluster-membership source available (no Postgres and "
                        "no --clusters-parquet)"
                    )
            except Exception as exc:  # noqa: BLE001
                log.warning("cluster %s: %s", cid, exc)
                continue

            if not member_uids:
                log.warning("cluster %s: 0 members in source", cid)
                continue

            expl = build_explanation(
                cid,
                member_uids,
                company_df=company_df,
                edges_df=edges_df,
                addresses_df=addresses_df,
                officers_df=officers_df,
                intermediaries_df=intermediaries_df,
                centrality_df=centrality_df,
                sanctions_df=sanctions_df,
            )
            inputs_meta = {
                "company_table": relpath_for_report(company_path),
                "icij_edges": relpath_for_report(interim_dir / "icij_edges.parquet"),
                "centrality_parquet": (
                    relpath_for_report(centrality_parquet)
                    if centrality_df is not None
                    else "(missing)"
                ),
                "sanctions_parquet": (
                    relpath_for_report(sanctions_parquet)
                    if (sanctions_parquet and sanctions_df is not None)
                    else "(none)"
                ),
            }
            md = render_explanation_markdown(
                expl,
                dedupe_run_id=dedupe_run_id,
                inputs_meta=inputs_meta,
                generated_at=datetime.now(UTC),
            )
            target = default_explanation_path(out_dir, cid)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(md, encoding="utf-8")
            log.info("wrote %s (score %.2f, %d members)", target, expl.features.total, len(expl.members))
            written.append((cid, target, expl.features.total, len(expl.members)))
    finally:
        if pg_conn is not None:
            pg_conn.close()

    if written:
        index_path = Path(out_dir) / "cluster_explanations" / "index.md"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Cluster explanations — {len(written)} cluster(s)",
            "",
            f"Generated `{datetime.now(UTC).isoformat(timespec='seconds')}`.",
            "",
            "| cluster_id | members | inv-score | report |",
            "| ---: | ---: | ---: | --- |",
        ]
        for cid, path, score, n in sorted(written, key=lambda r: -r[2]):
            rel = path.name
            lines.append(f"| {cid} | {n} | {score:.2f} | [{rel}]({rel}) |")
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log.info("wrote index %s", index_path)
        print(str(index_path))
    else:
        log.warning("no briefings written")


if __name__ == "__main__":
    app()
