"""Phase 7 — verify expanded-graph credibility priors + allowlist entry."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_SCRIPT = REPO_ROOT / "scripts" / "build_confidence_graph.py"


def _load_graph_mod():
    spec = importlib.util.spec_from_file_location("build_confidence_graph", GRAPH_SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["build_confidence_graph"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def graph_mod():
    return _load_graph_mod()


def test_phase7_edge_kinds_registered(graph_mod):
    assert "cross_jurisdictional_twin" in graph_mod._EDGE_KIND_CREDIBILITY
    assert "beneficial_owner_of" in graph_mod._EDGE_KIND_CREDIBILITY
    assert graph_mod._EDGE_KIND_CREDIBILITY["beneficial_owner_of"] > 0.9, (
        "SEC 13D/G edges should have high credibility (signed under penalty of perjury)"
    )
    assert graph_mod._EDGE_KIND_CREDIBILITY["cross_jurisdictional_twin"] < 0.9, (
        "Name-lineage twins are heuristic; should be < 0.9"
    )


def test_phase7_source_credibilities_registered(graph_mod):
    assert "SEC EDGAR 13D/13G" in graph_mod._SOURCE_CREDIBILITY
    assert "GoldenMatch twin detector" in graph_mod._SOURCE_CREDIBILITY


def test_phase7_cli_flags_exposed(graph_mod):
    """Smoke-check the new flags are recognised by the typer command."""
    import inspect

    sig = inspect.signature(graph_mod.main)
    params = sig.parameters
    assert "twin_edges_parquet" in params
    assert "sec_13dg_edges_parquet" in params


def test_phase7_allowlist_entry_exists():
    """job_server.py allowlist must carry the expanded variant."""
    spec = importlib.util.spec_from_file_location(
        "_job_server_check", REPO_ROOT / "src" / "shellnet" / "job_server.py"
    )
    assert spec is not None and spec.loader is not None
    # Just text-read for the assertion to avoid loading FastAPI at import time.
    text = (REPO_ROOT / "src" / "shellnet" / "job_server.py").read_text(encoding="utf-8")
    assert "build_confidence_graph_expanded" in text
    assert "--twin-edges" in text
    assert "--sec-13dg-edges" in text
    # And the allowlist entry must NOT start with "python" (per CLAUDE.md).
    assert (
        '"python",\n        "scripts/build_confidence_graph.py",\n        "--edges",\n        "/data/interim/icij_edges.parquet",\n        "--twin-edges"'
        not in text
    )


def test_phase7_workflow_present():
    wf = REPO_ROOT / ".github" / "workflows" / "recluster-expanded-graph.yml"
    assert wf.exists()
    txt = wf.read_text(encoding="utf-8")
    assert "build_confidence_graph_expanded" in txt
    assert "workflow_dispatch" in txt


def test_phase11_extra_seeds_flag_exposed(graph_mod):
    """Phase 11 plumbs --extra-seeds into build_confidence_graph.main."""
    import inspect

    sig = inspect.signature(graph_mod.main)
    assert "extra_seeds_parquet" in sig.parameters


def test_phase12_hops_3_with_pruning_bounds_size(graph_mod):
    """At hops=3 with min_frontier_degree_deep=2, the BFS only admits
    candidates that bridge >= 2 visited nodes. A star topology (1 hub
    + many one-degree leaves) should reach the hub but stop there.

    Builds a synthetic graph where:
      seed -> hubA (1 edge)
      hubA -> leaf1, leaf2, leaf3, leaf4 (4 edges)
      leaf1 -> tip1 (1 edge each — only reachable at hop 3)
      leaf2 -> tip2
      ...

    With hops=3 + min_degree=2, the tips should be pruned out since
    each connects to exactly one leaf (degree=1 into visited set).
    """

    import polars as pl

    edges = pl.DataFrame(
        {
            "src_node": [
                "seed",
                "hubA",
                "hubA",
                "hubA",
                "hubA",
                "leaf1",
                "leaf2",
                "leaf3",
                "leaf4",
            ],
            "dst_node": [
                "hubA",
                "leaf1",
                "leaf2",
                "leaf3",
                "leaf4",
                "tip1",
                "tip2",
                "tip3",
                "tip4",
            ],
            "kind_raw": ["officer_of"] * 9,
        }
    )
    sub = graph_mod._build_subgraph(
        edges, seed_uids={"seed"}, hops=3, max_nodes=100, min_frontier_degree_deep=2
    )
    visited = set(sub["src_node"].to_list()) | set(sub["dst_node"].to_list())
    # seed, hubA, leaf1-4 should all be in. tips should be filtered.
    assert "seed" in visited
    assert "hubA" in visited
    assert "leaf1" in visited
    assert "tip1" not in visited, (
        "tip1 has only 1 edge into visited set; deep-pruning should drop it"
    )


def test_phase12_hops_3_min_degree_1_admits_leaves(graph_mod):
    """Sanity: min_frontier_degree_deep=1 reproduces the pre-Phase-12
    behaviour and admits one-degree leaves at hop 3."""
    import polars as pl

    edges = pl.DataFrame(
        {
            "src_node": ["seed", "mid", "tail"],
            "dst_node": ["mid", "tail", "leaf"],
            "kind_raw": ["officer_of"] * 3,
        }
    )
    sub = graph_mod._build_subgraph(
        edges, seed_uids={"seed"}, hops=3, max_nodes=100, min_frontier_degree_deep=1
    )
    visited = set(sub["src_node"].to_list()) | set(sub["dst_node"].to_list())
    # leaf is the hop-3 node; with min_degree=1 it gets in.
    assert "leaf" in visited


def test_phase12_min_frontier_degree_deep_flag_exposed(graph_mod):
    import inspect

    sig = inspect.signature(graph_mod.main)
    assert "min_frontier_degree_deep" in sig.parameters


def test_phase11_max_nodes_default_raised(graph_mod):
    """Phase 11 raised the --max-nodes default from 8000 to 16000 so the
    expanded seed set has BFS headroom."""
    import inspect

    sig = inspect.signature(graph_mod.main)
    default = sig.parameters["max_nodes"].default
    # Default is a typer.OptionInfo wrapping the value.
    value = getattr(default, "default", default)
    assert value == 16000, f"expected 16000, got {value!r}"


def test_phase14_no_is_in_list_in_subgraph(graph_mod):
    """Phase 14 guard: _build_subgraph must use semi-joins, not
    is_in(list(...)). The list-scan version OOMs Railway at 50k
    frontiers."""
    # Inspect the compiled function's code object — that strips the
    # docstring and comments automatically, leaving only executable
    # bytecode constants. If the function ever calls is_in on a Python
    # list literal, "is_in" appears in co_names and "list" would be
    # a global reference. Simpler check: the AST.
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(graph_mod._build_subgraph))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "is_in":
                # Reject if the first arg is a call to list(...).
                if (
                    node.args
                    and isinstance(node.args[0], ast.Call)
                    and isinstance(node.args[0].func, ast.Name)
                    and node.args[0].func.id == "list"
                ):
                    raise AssertionError(
                        "_build_subgraph regressed to is_in(list(...)); "
                        "replace with .join(..., how='semi')"
                    )


def test_phase14_50k_frontier_completes_quickly(graph_mod):
    """Perf regression: BFS on a 50k-node synthetic graph with a 50k
    frontier must finish in < 20s. The pre-Phase-14 is_in(list)
    implementation took >40 min."""
    import time

    import polars as pl

    n = 50_000
    # Ring topology: every node connects to the next; degree=2 each.
    src_nodes = [f"n{i}" for i in range(n)]
    dst_nodes = [f"n{(i + 1) % n}" for i in range(n)]
    edges = pl.DataFrame(
        {
            "src_node": src_nodes,
            "dst_node": dst_nodes,
            "kind_raw": ["officer_of"] * n,
        }
    )
    # Seed with every other node — forces a large frontier.
    seeds = {f"n{i}" for i in range(0, n, 2)}

    t0 = time.monotonic()
    sub = graph_mod._build_subgraph(
        edges, seed_uids=seeds, hops=2, max_nodes=n, min_frontier_degree_deep=1
    )
    elapsed = time.monotonic() - t0
    assert elapsed < 20.0, f"BFS took {elapsed:.1f}s, perf regression"
    assert sub.height > 0


def test_phase14_correctness_unchanged_on_small_graph(graph_mod):
    """Sanity: the rewritten BFS produces the same visited node set as
    a hand-computed reachable-within-2-hops on a small graph."""
    import polars as pl

    edges = pl.DataFrame(
        {
            "src_node": ["a", "b", "c", "d"],
            "dst_node": ["b", "c", "d", "e"],
            "kind_raw": ["officer_of"] * 4,
        }
    )
    sub = graph_mod._build_subgraph(
        edges, seed_uids={"a"}, hops=2, max_nodes=100, min_frontier_degree_deep=1
    )
    visited = set(sub["src_node"].to_list()) | set(sub["dst_node"].to_list())
    # From "a" with 2 hops: a -> b -> c. So visited = {a, b, c}.
    # Edges in subgraph: a-b, b-c. NOT c-d (d isn't visited).
    assert visited == {"a", "b", "c"}, visited
    assert sub.height == 2


def test_phase3_and_phase6_allowlist_and_workflows():
    """Phase 3 / Phase 6 heavy scripts must be triggerable via the same
    Railway dispatch pattern as Phases 0 / 7 (otherwise compute can't be
    offloaded from the laptop)."""
    js = (REPO_ROOT / "src" / "shellnet" / "job_server.py").read_text(encoding="utf-8")
    assert "detect_cross_jurisdiction_twins" in js
    assert "ingest_sec_13dg_bulk" in js
    # Per CLAUDE.md: allowlist entries must NOT lead with "python".
    for name in ("detect_cross_jurisdiction_twins", "ingest_sec_13dg_bulk"):
        # The entry should look like "name": [\n        "scripts/..." — no "python" in between.
        idx = js.find(f'"{name}":')
        assert idx >= 0, f"{name} missing from allowlist"
        snippet = js[idx : idx + 200]
        assert '"python"' not in snippet, f"{name} entry must not lead with python"

    wf3 = REPO_ROOT / ".github" / "workflows" / "detect-cross-jurisdiction-twins.yml"
    wf6 = REPO_ROOT / ".github" / "workflows" / "ingest-sec-13dg-bulk.yml"
    assert wf3.exists() and wf6.exists()
    for wf in (wf3, wf6):
        txt = wf.read_text(encoding="utf-8")
        assert "SHELLNET_JOB_URL" in txt
        assert "/run-script?name=" in txt
