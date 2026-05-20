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
