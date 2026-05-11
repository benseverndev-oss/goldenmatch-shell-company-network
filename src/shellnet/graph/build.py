"""Build a NetworkX graph from the unified company table and per-source edges.

This is the smoke-test version: it gives every entity a node and every edge
file (today, ICIJ relationships) a directed edge. Cross-source ``same_as``
edges from GoldenMatch get layered on later.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import networkx as nx
import polars as pl

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


def summarize(g: nx.MultiDiGraph) -> dict[str, Any]:
    """Return a small JSON-able summary of the graph."""
    undirected = g.to_undirected(as_view=True)
    components = list(nx.connected_components(undirected))
    component_sizes = sorted((len(c) for c in components), reverse=True)
    by_kind: dict[str, int] = {}
    for _, attrs in g.nodes(data=True):
        by_kind[attrs.get("kind", "unknown")] = by_kind.get(attrs.get("kind", "unknown"), 0) + 1
    by_source: dict[str, int] = {}
    for _, attrs in g.nodes(data=True):
        by_source[attrs.get("source", "unknown")] = by_source.get(attrs.get("source", "unknown"), 0) + 1
    return {
        "node_count": g.number_of_nodes(),
        "edge_count": g.number_of_edges(),
        "component_count": len(components),
        "largest_component_size": component_sizes[0] if component_sizes else 0,
        "component_size_histogram": component_sizes[:20],
        "nodes_by_kind": by_kind,
        "nodes_by_source": by_source,
    }


def write_summary(g: nx.MultiDiGraph, out_path: Path | None = None) -> Path:
    out_path = out_path or (REPORTS_DIR / "graph_smoke_summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summarize(g), indent=2, default=str), encoding="utf-8")
    log.info("Wrote graph summary to %s", out_path)
    return out_path
