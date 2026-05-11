"""Build a NetworkX graph from the unified company table and per-source edges.

Every entity gets a node and every edge file (today: ICIJ relationships)
contributes a directed edge. Cross-source ``same_as`` edges from a
GoldenMatch run can be layered in via :func:`add_same_as_edges`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import networkx as nx
import polars as pl

from shellnet.matching.runs import cluster_pairs, run_paths
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, REPORTS_DIR

log = logging.getLogger(__name__)


def build_graph(
    processed_dir: Path = PROCESSED_DIR,
    interim_dir: Path = INTERIM_DIR,
) -> nx.MultiDiGraph:
    """Construct a MultiDiGraph from the unified company table + edge files.

    Multi-edges are intentional: the same officer↔company link can be
    asserted by multiple sources and we want each assertion preserved.
    """
    g: nx.MultiDiGraph = nx.MultiDiGraph()

    company_path = processed_dir / "company_entities.parquet"
    if company_path.exists():
        companies = pl.read_parquet(company_path)
        for row in companies.iter_rows(named=True):
            uid = row.get("entity_uid") or f"{row['source']}:{row['source_id']}"
            g.add_node(
                uid,
                kind="company",
                source=row["source"],
                name=row.get("name"),
                normalized_name=row.get("normalized_name"),
                jurisdiction=row.get("jurisdiction"),
            )
        log.info("Added %d company nodes", companies.height)

    edges_path = interim_dir / "icij_edges.parquet"
    if edges_path.exists():
        edges = pl.read_parquet(edges_path)
        for row in edges.iter_rows(named=True):
            src = row["src_node"]
            dst = row["dst_node"]
            # Make sure endpoints exist as nodes even if we haven't seen them
            # in the company table (officers, addresses, intermediaries).
            for n in (src, dst):
                if n not in g:
                    g.add_node(n, kind="unknown", source="icij")
            g.add_edge(
                src,
                dst,
                source="icij",
                kind=row.get("kind_raw") or "associated_with",
                role=row.get("role"),
            )
        log.info("Added %d ICIJ edges", edges.height)

    return g


def add_same_as_edges(
    g: nx.MultiDiGraph,
    *,
    output_dir: Path = REPORTS_DIR,
    run_name: str = "company",
    id_column: str = "entity_uid",
    source_table: Path | None = None,
) -> int:
    """Layer GoldenMatch ``same_as`` edges into an existing graph.

    Returns the number of edges added. Endpoints not already in the graph
    are added as ``kind='unknown'`` nodes — we never silently drop a
    matched pair just because the company table didn't have it.

    ``source_table`` is required when the cluster CSV uses GoldenMatch's
    opaque row-id format; for hand-written test fixtures with a native
    ``entity_uid`` column it's optional.
    """
    paths = run_paths(output_dir, run_name)
    if not paths.clusters_csv.exists():
        log.warning("No GoldenMatch cluster file at %s — skipping same_as overlay.", paths.clusters_csv)
        return 0
    if source_table is None:
        # Convention: company runs join against the processed company table.
        default = PROCESSED_DIR / f"{run_name}_entities.parquet"
        if default.exists():
            source_table = default
    added = 0
    for left, right, cluster_id in cluster_pairs(
        paths, id_column=id_column, source_table=source_table
    ):
        for n in (left, right):
            if n not in g:
                g.add_node(n, kind="unknown", source=n.split(":", 1)[0] if ":" in n else "unknown")
        # Directed graph + undirected semantics: add both directions so
        # downstream traversal doesn't depend on orientation.
        g.add_edge(left, right, source="goldenmatch", kind="same_as", cluster_id=cluster_id)
        g.add_edge(right, left, source="goldenmatch", kind="same_as", cluster_id=cluster_id)
        added += 2
    log.info("Added %d same_as edges from GoldenMatch run %r", added, run_name)
    return added


def summarize(g: nx.MultiDiGraph) -> dict[str, Any]:
    """Return a small JSON-able summary of the graph."""
    undirected = g.to_undirected(as_view=True)
    components = list(nx.connected_components(undirected))
    component_sizes = sorted((len(c) for c in components), reverse=True)
    by_kind: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for _, attrs in g.nodes(data=True):
        k = attrs.get("kind", "unknown")
        s = attrs.get("source", "unknown")
        by_kind[k] = by_kind.get(k, 0) + 1
        by_source[s] = by_source.get(s, 0) + 1
    edges_by_kind: dict[str, int] = {}
    for _, _, attrs in g.edges(data=True):
        k = attrs.get("kind", "unknown")
        edges_by_kind[k] = edges_by_kind.get(k, 0) + 1
    return {
        "node_count": g.number_of_nodes(),
        "edge_count": g.number_of_edges(),
        "component_count": len(components),
        "largest_component_size": component_sizes[0] if component_sizes else 0,
        "component_size_histogram": component_sizes[:20],
        "nodes_by_kind": by_kind,
        "nodes_by_source": by_source,
        "edges_by_kind": edges_by_kind,
    }


def write_summary(g: nx.MultiDiGraph, out_path: Path | None = None) -> Path:
    out_path = out_path or (REPORTS_DIR / "graph_smoke_summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summarize(g), indent=2, default=str), encoding="utf-8")
    log.info("Wrote graph summary to %s", out_path)
    return out_path
