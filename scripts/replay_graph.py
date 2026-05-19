"""Generate a frame-by-frame storyboard of a cluster's graph emergence.

    uv run python scripts/replay_graph.py --cluster-id 503264

Reads cluster membership from Postgres ``shellnet.clusters`` (or an
offline ``--clusters-parquet``), builds the timeline with
``temporal.build_timeline``, buckets events into ``--n-frames`` cumulative
snapshots, and writes:

* ``replay/cluster_<id>/storyboard.md`` — video-script-ready frame walk
* ``replay/cluster_<id>/replay.json`` — machine-readable sequence
* ``replay/cluster_<id>/frames/frame_NN.png`` — optional per-frame PNGs
  (only when matplotlib is importable; degrades silently otherwise)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import polars as pl
import typer
from dotenv import load_dotenv

from shellnet.investigations.cluster_explainer import (
    gather_member_attrs,
    gather_repeats,
)
from shellnet.investigations.graph_replay import (
    build_replay,
    render_replay_json,
    render_replay_markdown,
    write_replay_png_frames,
)
from shellnet.investigations.temporal import build_timeline
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT

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
    cluster_id: int = typer.Option(..., "--cluster-id"),
    n_frames: int = typer.Option(10, "--n-frames", help="Number of cumulative frames."),
    processed_dir: Path = typer.Option(PROCESSED_DIR, "--processed-dir"),
    interim_dir: Path = typer.Option(INTERIM_DIR, "--interim-dir"),
    clusters_parquet: Path | None = typer.Option(
        None, "--clusters-parquet", help="Offline (cluster_id, entity_uid) parquet."
    ),
    out_dir: Path = typer.Option(
        PROJECT_ROOT / "reports" / "generated",
        "--out-dir",
        help="Reports root; outputs land under `<out-dir>/replay/cluster_<id>/`.",
    ),
    png_frames: bool = typer.Option(
        True,
        "--png-frames/--no-png-frames",
        help="Try to render per-frame PNGs (silently skipped if matplotlib not installed).",
    ),
    no_postgres: bool = typer.Option(False, "--no-postgres"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # ----- Membership -----
    members_uids: list[str] = []
    if not no_postgres and os.environ.get("DATABASE_URL"):
        try:
            import psycopg

            with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
                members_uids, _ = _members_from_postgres(conn, cluster_id)
        except ImportError:
            log.warning("DATABASE_URL set but psycopg not installed")
        except Exception as exc:  # noqa: BLE001
            log.warning("Postgres path failed (%s); falling back to parquet", exc)
    if not members_uids:
        offline = _read_optional_parquet(clusters_parquet)
        if offline is None:
            raise typer.BadParameter(
                "no cluster membership available — set DATABASE_URL or pass --clusters-parquet."
            )
        members_uids = _members_from_parquet(offline, cluster_id)
    if not members_uids:
        raise typer.BadParameter(f"cluster {cluster_id} has 0 members.")
    log.info("loaded cluster %d with %d member(s)", cluster_id, len(members_uids))

    company_path = processed_dir / "company_entities.parquet"
    if not company_path.exists():
        raise typer.BadParameter(f"company_entities.parquet not found at {company_path}")
    company_df = pl.read_parquet(company_path)
    edges_df = _read_optional_parquet(interim_dir / "icij_edges.parquet")
    addresses_df = _read_optional_parquet(interim_dir / "icij_addresses.parquet")
    officers_df = _read_optional_parquet(interim_dir / "icij_officers.parquet")
    intermediaries_df = _read_optional_parquet(interim_dir / "icij_intermediaries.parquet")

    members = gather_member_attrs(company_df, members_uids)
    inters, addrs, offs = gather_repeats(
        members_uids,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )

    timeline = build_timeline(
        members,
        edges_df=edges_df,
        intermediaries=inters,
        addresses=addrs,
        officers=offs,
    )
    replay = build_replay(timeline, members, cluster_id=cluster_id, n_frames=n_frames)
    log.info("built replay with %d frame(s); %s", len(replay.frames), replay.summary)

    cluster_out = Path(out_dir) / "replay" / f"cluster_{cluster_id}"
    cluster_out.mkdir(parents=True, exist_ok=True)

    (cluster_out / "storyboard.md").write_text(render_replay_markdown(replay), encoding="utf-8")
    (cluster_out / "replay.json").write_text(render_replay_json(replay), encoding="utf-8")
    log.info("wrote storyboard.md and replay.json under %s", cluster_out)

    if png_frames and replay.frames:
        png_dir = cluster_out / "frames"
        paths = write_replay_png_frames(replay, png_dir)
        if paths:
            log.info("wrote %d PNG frame(s) under %s", len(paths), png_dir)
        else:
            log.info("PNG frames skipped (matplotlib not installed)")

    print(str(cluster_out / "storyboard.md"))


if __name__ == "__main__":
    app()
