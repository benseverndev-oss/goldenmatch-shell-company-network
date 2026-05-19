"""Assemble investigative evidence packets for one or more clusters.

    uv run python scripts/bundle_evidence.py --cluster-id 503264
    uv run python scripts/bundle_evidence.py --cluster-ids 1,2,3

For each cluster, writes a self-contained directory under
``<out-dir>/evidence/cluster_<id>/`` containing:

* ``source_filings/`` — the raw source-adapter records for each member
* ``edges.csv`` — every cluster-incident edge with provenance
* ``leak_index.md`` — leak labels → edge counts → date range
* ``registry_links.md`` — clickable external URLs
* ``sanctions_records.json`` — list-match anchors against the cluster
* ``manifest.md`` + ``bundle.json`` — human-readable + machine-readable index

Membership comes from Postgres ``shellnet.clusters`` (when ``DATABASE_URL``
is set), or from ``--clusters-parquet`` for offline / fixture work.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from pathlib import Path

import polars as pl
import typer
from dotenv import load_dotenv

from shellnet.investigations.cluster_explainer import gather_member_attrs
from shellnet.investigations.evidence_bundle import build_evidence_bundle, write_bundle
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


def _load_clusters(
    conn,
    cluster_ids: list[int] | None,
) -> tuple[dict[int, list[str]], str]:
    """Pull cluster membership from Postgres for the requested cluster ids
    (or all multi-member clusters if ``cluster_ids`` is None)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT run_id FROM shellnet.runs WHERE what='company' ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("no company run in shellnet.runs")
        run_id = str(row[0])
        if cluster_ids:
            cur.execute(
                "SELECT cluster_id, entity_uid FROM shellnet.clusters "
                "WHERE run_id=%s AND cluster_id = ANY(%s)",
                (run_id, cluster_ids),
            )
        else:
            cur.execute(
                """
                WITH cnt AS (
                    SELECT cluster_id, COUNT(*) AS n
                    FROM shellnet.clusters WHERE run_id = %s
                    GROUP BY cluster_id HAVING COUNT(*) >= 2
                )
                SELECT c.cluster_id, c.entity_uid
                FROM shellnet.clusters c JOIN cnt USING (cluster_id)
                WHERE c.run_id = %s
                """,
                (run_id, run_id),
            )
        members: dict[int, list[str]] = defaultdict(list)
        for cid, uid in cur.fetchall():
            members[int(cid)].append(uid)
    return dict(members), run_id


def _load_clusters_from_parquet(
    df: pl.DataFrame, cluster_ids: list[int] | None
) -> dict[int, list[str]]:
    members: dict[int, list[str]] = defaultdict(list)
    if cluster_ids:
        df = df.filter(pl.col("cluster_id").is_in(cluster_ids))
    for r in df.select(["cluster_id", "entity_uid"]).iter_rows(named=True):
        members[int(r["cluster_id"])].append(r["entity_uid"])
    return dict(members)


def _resolve_ids(cluster_id: int | None, cluster_ids_csv: str | None) -> list[int] | None:
    out: list[int] = []
    if cluster_id is not None:
        out.append(int(cluster_id))
    if cluster_ids_csv:
        for tok in cluster_ids_csv.split(","):
            tok = tok.strip()
            if tok:
                out.append(int(tok))
    return sorted(set(out)) if out else None


@app.command()
def main(
    cluster_id: int | None = typer.Option(None, "--cluster-id"),
    cluster_ids: str | None = typer.Option(None, "--cluster-ids", help="Comma-separated."),
    processed_dir: Path = typer.Option(PROCESSED_DIR, "--processed-dir"),
    interim_dir: Path = typer.Option(INTERIM_DIR, "--interim-dir"),
    sanctions_parquet: Path | None = typer.Option(
        None, "--sanctions-parquet", help="Optional list-match anchor parquet."
    ),
    clusters_parquet: Path | None = typer.Option(
        None, "--clusters-parquet", help="Offline fallback: (cluster_id, entity_uid) parquet."
    ),
    out_dir: Path = typer.Option(
        PROJECT_ROOT / "reports" / "generated" / "evidence",
        "--out-dir",
        help="Bundles land under `<out-dir>/cluster_<id>/`.",
    ),
    no_postgres: bool = typer.Option(False, "--no-postgres"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    ids = _resolve_ids(cluster_id, cluster_ids)
    if ids is None:
        log.info("no cluster ids passed; bundling every multi-member cluster in the latest run")

    # ----- Inputs -----
    company_path = processed_dir / "company_entities.parquet"
    if not company_path.exists():
        raise typer.BadParameter(f"company_entities.parquet not found at {company_path}")
    company_df = pl.read_parquet(company_path)
    edges_df = _read_optional_parquet(interim_dir / "icij_edges.parquet")
    sanctions_df = _read_optional_parquet(sanctions_parquet)
    source_dfs = {
        "icij": _read_optional_parquet(interim_dir / "icij_entities.parquet"),
        "opencorporates": _read_optional_parquet(interim_dir / "opencorporates_companies.parquet"),
        "gleif": _read_optional_parquet(interim_dir / "gleif_entities.parquet"),
        "opensanctions": _read_optional_parquet(interim_dir / "opensanctions_entities.parquet"),
    }

    # ----- Membership -----
    members_by_cluster: dict[int, list[str]] = {}
    dedupe_run_id = None
    if not no_postgres and os.environ.get("DATABASE_URL"):
        try:
            import psycopg

            with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
                members_by_cluster, dedupe_run_id = _load_clusters(conn, ids)
        except ImportError:
            log.warning("DATABASE_URL set but psycopg not installed")
        except Exception as exc:  # noqa: BLE001
            log.warning("Postgres path failed (%s); falling back to parquet", exc)
    if not members_by_cluster:
        offline = _read_optional_parquet(clusters_parquet)
        if offline is None:
            raise typer.BadParameter(
                "no cluster membership available — set DATABASE_URL or pass --clusters-parquet."
            )
        members_by_cluster = _load_clusters_from_parquet(offline, ids)
    if not members_by_cluster:
        raise typer.BadParameter("no clusters resolved.")
    log.info("bundling %d cluster(s)", len(members_by_cluster))

    # ----- Bundle each cluster -----
    paths: list[Path] = []
    for cid, uids in members_by_cluster.items():
        members = gather_member_attrs(company_df, uids)
        bundle = build_evidence_bundle(
            cid,
            members,
            edges_df=edges_df,
            source_dfs=source_dfs,
            sanctions_df=sanctions_df,
        )
        path = write_bundle(bundle, out_dir)
        log.info(
            "wrote %s (filings=%d edges=%d leaks=%d links=%d sanctions=%d)",
            path,
            len(bundle.source_filings),
            len(bundle.edges),
            len(bundle.leak_references),
            len(bundle.registry_links),
            len(bundle.sanctions_records),
        )
        paths.append(path)

    if paths:
        _ = dedupe_run_id  # reserved for future per-run scoping in the index
        # A top-level index across the batch (one line per bundle).
        index_path = Path(out_dir) / "index.md"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Evidence packets",
            "",
            f"{len(paths)} bundle(s) generated.",
            "",
            "| cluster_id | path |",
            "| ---: | --- |",
        ]
        for p in paths:
            try:
                cid = int(p.name.split("_", 1)[1])
            except (IndexError, ValueError):
                cid = -1
            lines.append(f"| {cid} | [{p.name}/manifest.md]({p.name}/manifest.md) |")
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log.info("wrote index %s", index_path)
        print(str(index_path))


if __name__ == "__main__":
    app()
