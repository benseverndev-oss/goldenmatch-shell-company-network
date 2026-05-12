"""Write a GoldenMatch run's output to Postgres.

Schema lives under ``shellnet`` so it never collides with showcase tables.
We drop and recreate per ``what`` (dedupe runs) or per ``run_name``
(list-match runs) on each publish so re-runs are idempotent.

Tables:
  shellnet.runs           — one row per (what, run_id), with summary stats
  shellnet.clusters       — (what, run_id, cluster_id, entity_uid)
  shellnet.same_as_pairs  — (what, run_id, left_uid, right_uid, cluster_id)
  shellnet.list_matches   — (run_id, run_name, target_*, ref_*, score)
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql

from shellnet.matching.runs import cluster_pairs, load_clusters, run_paths

log = logging.getLogger(__name__)

SCHEMA = "shellnet"


def _conn_str() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    # psycopg accepts the postgresql:// scheme directly.
    return url


def _ensure_schema(cur: psycopg.Cursor) -> None:
    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(SCHEMA)))
    cur.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {schema}.runs (
                run_id      uuid PRIMARY KEY,
                what        text NOT NULL,
                created_at  timestamptz NOT NULL DEFAULT now(),
                records     integer,
                clusters    integer,
                multi_member_clusters integer,
                same_as_pairs integer,
                config_path text,
                source_table text
            )
            """
        ).format(schema=sql.Identifier(SCHEMA))
    )
    cur.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {schema}.clusters (
                run_id      uuid NOT NULL REFERENCES {schema}.runs(run_id) ON DELETE CASCADE,
                what        text NOT NULL,
                cluster_id  bigint NOT NULL,
                entity_uid  text NOT NULL
            )
            """
        ).format(schema=sql.Identifier(SCHEMA))
    )
    cur.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {schema}.same_as_pairs (
                run_id      uuid NOT NULL REFERENCES {schema}.runs(run_id) ON DELETE CASCADE,
                what        text NOT NULL,
                left_uid    text NOT NULL,
                right_uid   text NOT NULL,
                cluster_id  bigint NOT NULL
            )
            """
        ).format(schema=sql.Identifier(SCHEMA))
    )
    cur.execute(
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS clusters_run_cluster_idx "
            "ON {schema}.clusters (run_id, cluster_id)"
        ).format(schema=sql.Identifier(SCHEMA))
    )
    cur.execute(
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS same_as_run_idx "
            "ON {schema}.same_as_pairs (run_id)"
        ).format(schema=sql.Identifier(SCHEMA))
    )
    cur.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {schema}.list_matches (
                run_id              uuid NOT NULL REFERENCES {schema}.runs(run_id) ON DELETE CASCADE,
                run_name            text NOT NULL,
                target_entity_uid   text NOT NULL,
                target_source       text,
                target_name         text,
                target_jurisdiction text,
                ref_entity_uid      text NOT NULL,
                ref_source          text,
                ref_name            text,
                ref_jurisdiction    text,
                ref_lei             text,
                score               double precision NOT NULL,
                score_band          text
            )
            """
        ).format(schema=sql.Identifier(SCHEMA))
    )
    cur.execute(
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS list_matches_run_idx "
            "ON {schema}.list_matches (run_id)"
        ).format(schema=sql.Identifier(SCHEMA))
    )
    cur.execute(
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS list_matches_target_idx "
            "ON {schema}.list_matches (target_entity_uid)"
        ).format(schema=sql.Identifier(SCHEMA))
    )


def _delete_prior_runs(cur: psycopg.Cursor, what: str) -> int:
    cur.execute(
        sql.SQL("DELETE FROM {schema}.runs WHERE what = %s").format(
            schema=sql.Identifier(SCHEMA)
        ),
        (what,),
    )
    return cur.rowcount or 0


def publish_run(
    *,
    what: str,
    reports_dir: Path,
    processed_dir: Path,
) -> dict[str, Any]:
    paths = run_paths(reports_dir, what)
    if not paths.clusters_csv.exists():
        raise FileNotFoundError(f"clusters csv missing: {paths.clusters_csv}")

    source_table = processed_dir / f"{what}_entities.parquet"
    clusters_df = load_clusters(paths, source_table=source_table)
    pairs = cluster_pairs(paths, source_table=source_table)
    run_id = uuid.uuid4()
    log.info("publishing run %s (%s): %d records, %d pairs", run_id, what, clusters_df.height, len(pairs))

    records = clusters_df.height
    n_clusters = int(clusters_df["cluster_id"].n_unique())
    multi = sum(1 for _, g in clusters_df.group_by("cluster_id") if g.height > 1)

    with psycopg.connect(_conn_str(), autocommit=False) as conn:
        with conn.cursor() as cur:
            _ensure_schema(cur)
            deleted = _delete_prior_runs(cur, what)
            cur.execute(
                sql.SQL(
                    "INSERT INTO {schema}.runs "
                    "(run_id, what, records, clusters, multi_member_clusters, same_as_pairs, source_table) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                ).format(schema=sql.Identifier(SCHEMA)),
                (str(run_id), what, records, n_clusters, multi, len(pairs), str(source_table)),
            )

            # Bulk insert clusters.
            cluster_rows = [
                (str(run_id), what, int(r["cluster_id"]), str(r["entity_uid"]))
                for r in clusters_df.iter_rows(named=True)
                if r.get("entity_uid") is not None
            ]
            if cluster_rows:
                with cur.copy(
                    sql.SQL(
                        "COPY {schema}.clusters (run_id, what, cluster_id, entity_uid) FROM STDIN"
                    ).format(schema=sql.Identifier(SCHEMA))
                ) as cp:
                    for row in cluster_rows:
                        cp.write_row(row)

            # Bulk insert same_as pairs.
            if pairs:
                with cur.copy(
                    sql.SQL(
                        "COPY {schema}.same_as_pairs (run_id, what, left_uid, right_uid, cluster_id) FROM STDIN"
                    ).format(schema=sql.Identifier(SCHEMA))
                ) as cp:
                    for left, right, cid in pairs:
                        cp.write_row((str(run_id), what, left, right, int(cid)))

        conn.commit()

    return {
        "run_id": str(run_id),
        "what": what,
        "records": records,
        "clusters": n_clusters,
        "multi_member_clusters": multi,
        "same_as_pairs": len(pairs),
        "deleted_prior_runs": deleted,
        "published_at": datetime.now(UTC).isoformat(),
    }


def _score_band(score: float) -> str:
    if score >= 0.99:
        return "perfect"
    if score >= 0.95:
        return "high"
    if score >= 0.85:
        return "borderline"
    return "low"


def publish_list_match(
    *,
    run_name: str,
    reports_dir: Path,
    what_tag: str | None = None,
) -> dict[str, Any]:
    """Read ``<run_name>_matched.csv`` and write rows to ``shellnet.list_matches``.

    Replaces any previous run with the same ``run_name``.
    """
    import csv

    matched_csv = reports_dir / f"{run_name}_matched.csv"
    if not matched_csv.exists():
        raise FileNotFoundError(f"matched csv missing: {matched_csv}")

    rows: list[dict[str, Any]] = []
    band_counts = {"perfect": 0, "high": 0, "borderline": 0, "low": 0}
    target_uids: set[str] = set()
    ref_uids: set[str] = set()
    with matched_csv.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                score = float(r["__match_score__"])
            except (KeyError, ValueError):
                continue
            band = _score_band(score)
            band_counts[band] += 1
            target_uids.add(r["target_entity_uid"])
            ref_uids.add(r["ref_entity_uid"])
            rows.append(
                {
                    "target_entity_uid": r["target_entity_uid"],
                    "target_source": r.get("target_source"),
                    "target_name": r.get("target_name"),
                    "target_jurisdiction": r.get("target_jurisdiction"),
                    "ref_entity_uid": r["ref_entity_uid"],
                    "ref_source": r.get("ref_source"),
                    "ref_name": r.get("ref_name"),
                    "ref_jurisdiction": r.get("ref_jurisdiction"),
                    "ref_lei": r.get("ref_lei"),
                    "score": score,
                    "score_band": band,
                }
            )

    run_id = uuid.uuid4()
    what = what_tag or f"list_match:{run_name}"
    log.info(
        "publishing list-match %s (%s): %d rows, %d unique targets, %d unique refs",
        run_id, run_name, len(rows), len(target_uids), len(ref_uids),
    )

    with psycopg.connect(_conn_str(), autocommit=False) as conn:
        with conn.cursor() as cur:
            _ensure_schema(cur)
            cur.execute(
                sql.SQL("DELETE FROM {schema}.runs WHERE what = %s").format(
                    schema=sql.Identifier(SCHEMA)
                ),
                (what,),
            )
            cur.execute(
                sql.SQL(
                    "INSERT INTO {schema}.runs "
                    "(run_id, what, records, clusters, multi_member_clusters, same_as_pairs, source_table) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                ).format(schema=sql.Identifier(SCHEMA)),
                (
                    str(run_id),
                    what,
                    len(rows),
                    len(ref_uids),
                    None,
                    len(rows),
                    str(matched_csv),
                ),
            )
            if rows:
                with cur.copy(
                    sql.SQL(
                        "COPY {schema}.list_matches "
                        "(run_id, run_name, target_entity_uid, target_source, target_name, "
                        "target_jurisdiction, ref_entity_uid, ref_source, ref_name, "
                        "ref_jurisdiction, ref_lei, score, score_band) FROM STDIN"
                    ).format(schema=sql.Identifier(SCHEMA))
                ) as cp:
                    for r in rows:
                        cp.write_row(
                            (
                                str(run_id),
                                run_name,
                                r["target_entity_uid"],
                                r["target_source"],
                                r["target_name"],
                                r["target_jurisdiction"],
                                r["ref_entity_uid"],
                                r["ref_source"],
                                r["ref_name"],
                                r["ref_jurisdiction"],
                                r["ref_lei"],
                                r["score"],
                                r["score_band"],
                            )
                        )
        conn.commit()

    return {
        "run_id": str(run_id),
        "what": what,
        "run_name": run_name,
        "matched_rows": len(rows),
        "unique_targets": len(target_uids),
        "unique_refs": len(ref_uids),
        "score_bands": band_counts,
        "published_at": datetime.now(UTC).isoformat(),
    }
