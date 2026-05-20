"""Smoke test for the OO UK PSC edge merge in build_confidence_graph.

Doesn't run the full Louvain pipeline (that needs the rare-officer
dossiers parquet which lives in /data/processed/). Just imports the
script as a module and verifies:

1. The OO source label is in the source-credibility map with the
   right weight.
2. The OO psc_controller_of kind is in the kind-credibility map.
3. The CLI accepts the new --oo-uk-psc-edges flag.
4. The combined-edges concatenation is shape-compatible.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_confidence_graph.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_confidence_graph", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["build_confidence_graph"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load()


def test_oo_source_credibility_present(mod):
    assert "Open Ownership UK PSC (BODS v0.4)" in mod._SOURCE_CREDIBILITY
    # Slightly above raw UK PSC (0.95) since OO has done the canonicalisation.
    assert mod._SOURCE_CREDIBILITY["Open Ownership UK PSC (BODS v0.4)"] >= 0.95
    assert mod._SOURCE_CREDIBILITY["Open Ownership UK PSC (BODS v0.4)"] < 1.0


def test_psc_controller_of_kind_present(mod):
    assert "psc_controller_of" in mod._EDGE_KIND_CREDIBILITY
    # Treated as structural (state-mandated), but not as definitive as
    # registered_address; sit it between 0.85 and 0.95.
    weight = mod._EDGE_KIND_CREDIBILITY["psc_controller_of"]
    assert 0.85 <= weight <= 0.95


def test_cli_accepts_oo_flag(mod, tmp_path):
    # Inspect the click command parameters directly. The previous version
    # of this test grepped `--help` output, but Rich/Typer wraps long flag
    # names mid-token in narrow terminals (CI defaults to 80 cols) which
    # broke the substring match. Going through the click command object
    # is both faster and width-independent.
    import typer.main

    cmd = typer.main.get_command(mod.app)
    # Find the underlying main command — Typer wraps single-command apps
    # so the params might be on `cmd` directly or on a single sub-command.
    if hasattr(cmd, "commands") and cmd.commands:
        first = next(iter(cmd.commands.values()))
        params = first.params
    else:
        params = cmd.params
    flag_names = {opt for p in params for opt in p.opts}
    assert "--oo-uk-psc-edges" in flag_names, flag_names


def test_diagonal_concat_compatibility(tmp_path):
    """The OO and ICIJ edge schemas must concat with polars `how='diagonal'`."""
    icij = pl.DataFrame(
        {
            "src_node": ["icij:1"],
            "dst_node": ["icij:2"],
            "kind_raw": ["officer_of"],
            "source_label": ["Paradise Papers - Malta corporate registry"],
        }
    )
    oo = pl.DataFrame(
        {
            "src_node": ["oo:gb-coh-per-1"],
            "dst_node": ["oo:gb-coh-2"],
            "kind_raw": ["psc_controller_of"],
            "source_label": ["Open Ownership UK PSC (BODS v0.4)"],
        }
    )
    combined = pl.concat([icij, oo], how="diagonal")
    assert combined.height == 2
    assert {"src_node", "dst_node", "kind_raw", "source_label"} <= set(combined.columns)
    # No node-id namespace collision.
    assert combined["src_node"].n_unique() == 2
