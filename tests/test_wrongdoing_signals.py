"""Tests for the wrongdoing-signal scoring layer (roadmap Phase 2)."""

from __future__ import annotations

import polars as pl

from shellnet.investigations import wrongdoing_signals as ws


def test_score_is_weighted_sum_times_harm():
    leads = pl.DataFrame(
        {
            "lead_id": ["a", "b"],
            "evasion_timing": [1.0, 0.0],
            "nominee_front": [0.0, 1.0],
            "harm_weight": [1.0, 2.0],
        }
    )
    out = ws.score_wrongdoing(leads, active_gate=False)
    m = {r["lead_id"]: r["wrongdoing_score"] for r in out.iter_rows(named=True)}
    assert m["a"] == 1.0 * ws.DEFAULT_WEIGHTS["evasion_timing"]  # 1.0
    assert m["b"] == 1.0 * ws.DEFAULT_WEIGHTS["nominee_front"] * 2.0  # 0.7 * 2
    # sorted descending
    assert out["lead_id"].to_list() == ["b", "a"]


def test_active_gate_drops_struck_off_keeps_unknown():
    leads = pl.DataFrame(
        {
            "lead_id": ["live", "dead", "unknown"],
            "evasion_timing": [1.0, 1.0, 1.0],
            "active": [True, False, None],
        }
    )
    out = ws.score_wrongdoing(leads, active_gate=True)
    assert set(out["lead_id"].to_list()) == {"live", "unknown"}


def test_harm_gate_requires_positive_harm():
    leads = pl.DataFrame(
        {
            "lead_id": ["x", "y"],
            "evasion_timing": [1.0, 1.0],
            "harm_weight": [0.0, 1.5],
        }
    )
    out = ws.score_wrongdoing(leads, active_gate=False, harm_gate=True)
    assert out["lead_id"].to_list() == ["y"]


def test_missing_signal_columns_treated_as_zero():
    leads = pl.DataFrame({"lead_id": ["a"], "evasion_timing": [1.0]})
    out = ws.score_wrongdoing(leads, active_gate=False)
    assert out.row(0, named=True)["wrongdoing_score"] == ws.DEFAULT_WEIGHTS["evasion_timing"]


def test_empty_leads_safe():
    leads = pl.DataFrame({"lead_id": [], "evasion_timing": []})
    out = ws.score_wrongdoing(leads)
    assert "wrongdoing_score" in out.columns
    assert out.height == 0
