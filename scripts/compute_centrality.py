"""Compute centrality + community detection on the cluster sub-graph.

The full ICIJ + GLEIF graph is too large for full betweenness centrality
(2M+ nodes). This script restricts to the *cluster sub-graph*:

  * all entity_uids that are members of multi-member dedupe clusters
    (~18K from v2)
  * plus their direct ICIJ neighbours (officers, addresses,
    intermediaries) — this gives the structural context around each
    cluster

Then computes per-node:

  * degree_in / degree_out / degree_total
  * eigenvector_centrality (on the undirected projection)
  * betweenness_centrality (k-sample approximation)
  * louvain_community_id

Annotates each node with its dedupe cluster_id (if any) and source.
Writes parquet + a top-N markdown report.

Designed to run on the Railway container with the data on /data.
"""

from __future__ import annotations

import logging
import os
import time
from collections import Counter
from pathlib import Path

import networkx as nx
import polars as pl
import psycopg
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg.connect(url)


@app.command()
def main(
    processed_dir: Path = typer.Option(Path("/data/processed"), "--processed-dir"),
    interim_dir: Path = typer.Option(Path("/data/interim"), "--interim-dir"),
    out_parquet: Path = typer.Option(
        Path("/data/processed/cluster_centrality.parquet"), "--out-parquet"
    ),
    out_md: Path = typer.Option(Path("/data/reports/generated/centrality_top.md"), "--out-md"),
    betweenness_k: int = typer.Option(
        500, "--betweenness-k", help="k for k-sampled betweenness; 0 = full (slow on big graphs)."
    ),
    top_n: int = typer.Option(30, "--top-n"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    log.info("loading multi-member cluster members from Postgres")
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT run_id FROM shellnet.runs WHERE what='company' ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("no company run in shellnet.runs")
        dedupe_run_id = str(row[0])
        log.info("dedupe run_id = %s", dedupe_run_id)

        cur.execute(
            """
            WITH cnt AS (
                SELECT cluster_id, COUNT(*) AS n
                FROM shellnet.clusters
                WHERE run_id = %s
                GROUP BY cluster_id
                HAVING COUNT(*) >= 2
            )
            SELECT c.entity_uid, c.cluster_id
            FROM shellnet.clusters c
            JOIN cnt USING (cluster_id)
            WHERE c.run_id = %s
            """,
            (dedupe_run_id, dedupe_run_id),
        )
        cluster_by_uid: dict[str, int] = {uid: int(cid) for uid, cid in cur.fetchall()}
    log.info("%d cluster members", len(cluster_by_uid))

    log.info("loading icij_edges parquet")
    edges = pl.read_parquet(interim_dir / "icij_edges.parquet").select(
        ["src_node", "dst_node", "kind_raw"]
    )

    cluster_uid_set = set(cluster_by_uid.keys())
    log.info("filtering to ego sub-graph (edges incident to cluster members)")
    ego_edges = edges.filter(
        pl.col("src_node").is_in(cluster_uid_set) | pl.col("dst_node").is_in(cluster_uid_set)
    )
    log.info("ego sub-graph has %d edges", ego_edges.height)

    log.info("building NetworkX graph")
    g_directed = nx.DiGraph()
    for r in ego_edges.iter_rows(named=True):
        s, d = r["src_node"], r["dst_node"]
        g_directed.add_edge(s, d, kind=r.get("kind_raw") or "")
    log.info(
        "graph: %d nodes, %d edges", g_directed.number_of_nodes(), g_directed.number_of_edges()
    )

    log.info("loading company_entities for source/jurisdiction labels")
    company_df = pl.read_parquet(processed_dir / "company_entities.parquet").select(
        ["entity_uid", "source", "name", "jurisdiction"]
    )
    attr_lookup = {
        r["entity_uid"]: (r["source"], r["name"], r["jurisdiction"])
        for r in company_df.filter(pl.col("entity_uid").is_in(list(g_directed.nodes()))).iter_rows(
            named=True
        )
    }

    log.info("computing degree (cheap)")
    in_deg = dict(g_directed.in_degree())
    out_deg = dict(g_directed.out_degree())

    log.info("projecting to undirected for community + eigenvector")
    g_und = g_directed.to_undirected()

    log.info("computing eigenvector centrality (max_iter=300)")
    t0 = time.time()
    try:
        eig = nx.eigenvector_centrality(g_und, max_iter=300, tol=1e-4)
        log.info("eigenvector done in %.1fs", time.time() - t0)
    except nx.PowerIterationFailedConvergence:
        log.warning("eigenvector failed to converge; falling back to katz")
        eig = nx.katz_centrality_numpy(g_und, alpha=0.005)

    if betweenness_k > 0 and g_und.number_of_nodes() > betweenness_k:
        log.info("computing k-sampled betweenness (k=%d)", betweenness_k)
        t0 = time.time()
        bc = nx.betweenness_centrality(g_und, k=betweenness_k, normalized=True, seed=42)
        log.info("betweenness done in %.1fs", time.time() - t0)
    else:
        log.info("computing full betweenness")
        t0 = time.time()
        bc = nx.betweenness_centrality(g_und, normalized=True)
        log.info("betweenness done in %.1fs", time.time() - t0)

    log.info("running Louvain community detection")
    t0 = time.time()
    communities = nx.community.louvain_communities(g_und, seed=42)
    log.info("Louvain done in %.1fs (%d communities)", time.time() - t0, len(communities))
    community_by_node: dict[str, int] = {}
    for cid, members in enumerate(communities):
        for m in members:
            community_by_node[m] = cid
    community_sizes = Counter(community_by_node.values())

    log.info("assembling output rows")
    rows: list[dict] = []
    for node in g_directed.nodes():
        src, name, jur = attr_lookup.get(node, (None, None, None))
        rows.append(
            {
                "entity_uid": node,
                "source": src,
                "name": name,
                "jurisdiction": jur,
                "cluster_id": cluster_by_uid.get(node),
                "community_id": community_by_node.get(node),
                "community_size": community_sizes.get(community_by_node.get(node, -1), 0),
                "in_degree": in_deg.get(node, 0),
                "out_degree": out_deg.get(node, 0),
                "total_degree": in_deg.get(node, 0) + out_deg.get(node, 0),
                "eigenvector": float(eig.get(node, 0.0)),
                "betweenness": float(bc.get(node, 0.0)),
            }
        )
    df = pl.DataFrame(rows)
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out_parquet)
    log.info("wrote %s (%d rows)", out_parquet, df.height)

    # Markdown top-N report.
    lines: list[str] = []
    lines.append("# Cluster sub-graph centrality + communities")
    lines.append("")
    lines.append(f"Source dedupe run: `{dedupe_run_id}`")
    lines.append(
        f"Sub-graph: {g_directed.number_of_nodes()} nodes / "
        f"{g_directed.number_of_edges()} edges (cluster members + direct neighbours)"
    )
    lines.append(f"Communities: {len(communities)} (Louvain, undirected projection)")
    lines.append("")
    lines.append(
        "Centrality metrics computed on the *cluster sub-graph*, not the "
        "full 2M-node graph. Edges are directed ICIJ relationships "
        "(officer_of, registered_address, intermediary_of, etc.)."
    )
    lines.append("")

    lines.append(f"## Top {top_n} by total degree")
    lines.append("")
    lines.append("| entity_uid | source | name | jur | cluster | community | in | out | total |")
    lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |")
    top_deg = df.sort("total_degree", descending=True).head(top_n)
    for r in top_deg.iter_rows(named=True):
        lines.append(
            "| `{u}` | {s} | `{n}` | {j} | {cl} | {co} | {i} | {o} | {t} |".format(
                u=r["entity_uid"][:50],
                s=r["source"] or "?",
                n=(r["name"] or "")[:40].replace("|", "/"),
                j=r["jurisdiction"] or "",
                cl=r["cluster_id"] or "",
                co=r["community_id"] or "",
                i=r["in_degree"],
                o=r["out_degree"],
                t=r["total_degree"],
            )
        )
    lines.append("")

    lines.append(f"## Top {top_n} by eigenvector centrality")
    lines.append("")
    lines.append("| entity_uid | source | name | jur | cluster | community | eig |")
    lines.append("| --- | --- | --- | --- | ---: | ---: | ---: |")
    top_eig = df.sort("eigenvector", descending=True).head(top_n)
    for r in top_eig.iter_rows(named=True):
        lines.append(
            "| `{u}` | {s} | `{n}` | {j} | {cl} | {co} | {e:.4f} |".format(
                u=r["entity_uid"][:50],
                s=r["source"] or "?",
                n=(r["name"] or "")[:40].replace("|", "/"),
                j=r["jurisdiction"] or "",
                cl=r["cluster_id"] or "",
                co=r["community_id"] or "",
                e=r["eigenvector"],
            )
        )
    lines.append("")

    lines.append(f"## Top {top_n} by betweenness centrality")
    lines.append("")
    lines.append("| entity_uid | source | name | jur | cluster | community | bc |")
    lines.append("| --- | --- | --- | --- | ---: | ---: | ---: |")
    top_bc = df.sort("betweenness", descending=True).head(top_n)
    for r in top_bc.iter_rows(named=True):
        lines.append(
            "| `{u}` | {s} | `{n}` | {j} | {cl} | {co} | {b:.4f} |".format(
                u=r["entity_uid"][:50],
                s=r["source"] or "?",
                n=(r["name"] or "")[:40].replace("|", "/"),
                j=r["jurisdiction"] or "",
                cl=r["cluster_id"] or "",
                co=r["community_id"] or "",
                b=r["betweenness"],
            )
        )
    lines.append("")

    lines.append(f"## Top {top_n} communities by size")
    lines.append("")
    lines.append("| community_id | size |")
    lines.append("| ---: | ---: |")
    for cid, n in community_sizes.most_common(top_n):
        lines.append(f"| {cid} | {n} |")
    lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s", out_md)
    print(str(out_md))


if __name__ == "__main__":
    app()
