"""Slice a huge cluster into narratable subclusters.

    uv run python scripts/extract_subclusters.py --cluster-id 503264

Reads cluster membership from Postgres ``shellnet.clusters`` (or an
offline ``--clusters-parquet``), runs the five subcluster extractors
in ``shellnet.investigations.subcluster``, and writes:

  * ``subclusters/cluster_<id>/index.md`` — the leaderboard of
    extracted subclusters with their interest scores and narratives
  * ``subclusters/cluster_<id>/<subcluster_id>.md`` — a full
    ``cluster_explainer`` briefing scoped to each subcluster's member
    set
  * ``subclusters/cluster_<id>/subclusters.parquet`` — the same
    subcluster table as a parquet, for downstream tooling

For 33k+-member clusters this is the entry point that turns the
cluster into something investigators can actually read.
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
    annotate_centrality as _annotate_centrality,
)
from shellnet.investigations.cluster_explainer import (
    build_explanation,
    gather_repeats,
    render_explanation_markdown,
)
from shellnet.investigations.subcluster import (
    extract_subclusters,
    render_subcluster_index_markdown,
)
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT, relpath_for_report

load_dotenv()

app = typer.Typer(add_completion=False, no_args_is_help=True)
log = logging.getLogger(__name__)


def _read_optional_parquet(path: Path | None) -> pl.DataFrame | None:
    if path is None or not path.exists():
        return None
    try:
        return pl.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not read %s: %s", path, exc)
        return None


def _members_from_postgres(conn, cluster_id: int) -> tuple[list[str], str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT run_id FROM shellnet.runs WHERE what='company' ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("no company run in shellnet.runs")
        run_id = str(row[0])
        cur.execute(
            "SELECT entity_uid FROM shellnet.clusters WHERE run_id=%s AND cluster_id=%s",
            (run_id, cluster_id),
        )
        uids = [uid for (uid,) in cur.fetchall()]
    return uids, run_id


def _members_from_parquet(df: pl.DataFrame, cluster_id: int) -> list[str]:
    return df.filter(pl.col("cluster_id") == cluster_id).get_column("entity_uid").to_list()


@app.command()
def main(
    cluster_id: int = typer.Option(..., "--cluster-id", help="Cluster id to slice."),
    processed_dir: Path = typer.Option(
        PROCESSED_DIR, "--processed-dir", help="Override processed dir."
    ),
    interim_dir: Path = typer.Option(INTERIM_DIR, "--interim-dir", help="Override interim dir."),
    centrality_parquet: Path = typer.Option(
        PROCESSED_DIR / "cluster_centrality.parquet",
        "--centrality-parquet",
        help="Per-node centrality parquet from compute_centrality.py.",
    ),
    sanctions_parquet: Path | None = typer.Option(
        None, "--sanctions-parquet", help="Optional list-match anchors parquet."
    ),
    clusters_parquet: Path | None = typer.Option(
        None, "--clusters-parquet", help="Offline (cluster_id, entity_uid) parquet."
    ),
    out_dir: Path = typer.Option(
        PROJECT_ROOT / "reports" / "generated",
        "--out-dir",
        help="Reports root; outputs land under `<out-dir>/subclusters/cluster_<id>/`.",
    ),
    max_subclusters: int = typer.Option(
        20, "--max-subclusters", help="Cap on the number of subcluster briefings written."
    ),
    no_postgres: bool = typer.Option(False, "--no-postgres"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # ----- Membership -----
    dedupe_run_id: str | None = None
    members: list[str] = []
    if not no_postgres and os.environ.get("DATABASE_URL"):
        try:
            import psycopg

            with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
                members, dedupe_run_id = _members_from_postgres(conn, cluster_id)
        except ImportError:
            log.warning("DATABASE_URL set but psycopg not installed")
        except Exception as exc:  # noqa: BLE001
            log.warning("Postgres path failed (%s); falling back to parquet", exc)
    if not members:
        offline = _read_optional_parquet(clusters_parquet)
        if offline is None:
            raise typer.BadParameter(
                "no cluster membership available — set DATABASE_URL or pass --clusters-parquet."
            )
        members = _members_from_parquet(offline, cluster_id)
    if not members:
        raise typer.BadParameter(f"cluster {cluster_id} has 0 members.")
    log.info("loaded cluster %d with %d member(s)", cluster_id, len(members))

    # ----- Inputs -----
    company_path = processed_dir / "company_entities.parquet"
    if not company_path.exists():
        raise typer.BadParameter(f"company_entities.parquet not found at {company_path}")
    company_df = pl.read_parquet(company_path)
    edges_df = _read_optional_parquet(interim_dir / "icij_edges.parquet")
    addresses_df = _read_optional_parquet(interim_dir / "icij_addresses.parquet")
    officers_df = _read_optional_parquet(interim_dir / "icij_officers.parquet")
    intermediaries_df = _read_optional_parquet(interim_dir / "icij_intermediaries.parquet")
    centrality_df = _read_optional_parquet(centrality_parquet)
    sanctions_df = _read_optional_parquet(sanctions_parquet)

    # Cluster-level repeats + centrality, fed into subcluster extractors.
    inters, addrs, offs = gather_repeats(
        members,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    centrality = _annotate_centrality(centrality_df, members)

    subclusters = extract_subclusters(
        cluster_id,
        members,
        edges_df=edges_df,
        intermediaries=inters,
        addresses=addrs,
        officers=offs,
        centrality=centrality,
        max_subclusters=max_subclusters,
    )
    log.info("extracted %d subcluster(s)", len(subclusters))

    # ----- Write outputs -----
    cluster_out = Path(out_dir) / "subclusters" / f"cluster_{cluster_id}"
    cluster_out.mkdir(parents=True, exist_ok=True)

    index_md = render_subcluster_index_markdown(
        cluster_id, subclusters, dedupe_run_id=dedupe_run_id
    )
    (cluster_out / "index.md").write_text(index_md, encoding="utf-8")
    log.info("wrote %s", cluster_out / "index.md")

    # Parquet for downstream tooling.
    if subclusters:
        pl.DataFrame(
            [
                {
                    "cluster_id": cluster_id,
                    "subcluster_id": s.subcluster_id,
                    "kind": s.kind,
                    "size": s.size,
                    "interest_score": s.interest_score,
                    "seed_node": s.seed_node,
                    "seed_label": s.seed_label,
                    "narrative": s.narrative,
                    "member_uids": "|".join(s.member_uids),
                }
                for s in subclusters
            ]
        ).write_parquet(cluster_out / "subclusters.parquet")

    # Per-subcluster briefings.
    for s in subclusters:
        try:
            sub_expl = build_explanation(
                cluster_id,
                s.member_uids,
                company_df=company_df,
                edges_df=edges_df,
                addresses_df=addresses_df,
                officers_df=officers_df,
                intermediaries_df=intermediaries_df,
                centrality_df=centrality_df,
                sanctions_df=sanctions_df,
            )
            md = render_explanation_markdown(
                sub_expl,
                dedupe_run_id=dedupe_run_id,
                inputs_meta={
                    "company_table": relpath_for_report(company_path),
                    "subcluster_kind": s.kind,
                    "subcluster_seed": s.seed_label or s.seed_node or "",
                },
                generated_at=datetime.now(UTC),
            )
            target = cluster_out / f"{s.subcluster_id}.md"
            target.write_text(md, encoding="utf-8")
            log.info("wrote %s (kind=%s, size=%d)", target, s.kind, s.size)
        except Exception as exc:  # noqa: BLE001
            log.warning("failed to render subcluster %s: %s", s.subcluster_id, exc)

    print(str(cluster_out / "index.md"))


if __name__ == "__main__":
    app()
