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


def test_phase11_max_nodes_default_raised(graph_mod):
    """Phase 11 raised the --max-nodes default from 8000 to 16000 so the
    expanded seed set has BFS headroom."""
    import inspect

    sig = inspect.signature(graph_mod.main)
    default = sig.parameters["max_nodes"].default
    # Default is a typer.OptionInfo wrapping the value.
    value = getattr(default, "default", default)
    assert value == 16000, f"expected 16000, got {value!r}"


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
