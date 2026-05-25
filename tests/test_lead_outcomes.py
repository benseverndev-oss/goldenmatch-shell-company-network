"""Tests for the lead-outcomes feedback loop (roadmap Phase 6)."""

from __future__ import annotations

import polars as pl

from shellnet.investigations import lead_outcomes as lo


def _leads():
    return pl.DataFrame(
        {
            "lead_id": ["a", "b", "c", "d"],
            "wrongdoing_score": [1.0, 0.9, 0.8, 0.7],
            "evasion_timing": [1.0, 1.0, 0.0, 0.0],
            "regulatory_breach": [0.0, 0.0, 1.0, 1.0],
        }
    )


def _outcomes():
    return pl.DataFrame(
        {
            "lead_id": ["a", "b", "c", "d"],
            "reviewed_at": ["2026-05-01"] * 4,
            "verdict": ["genuine", "rejected", "novel", "rejected"],
            "reviewer_note": ["", "namesake", "", "dissolved decoy"],
        }
    )


def test_top_n_precision():
    m = lo.top_n_precision(_leads(), _outcomes(), n=4)
    assert m["reviewed"] == 4
    assert m["positives"] == 2  # genuine + novel
    assert m["precision"] == 0.5
    assert m["novelty_rate"] == 0.25  # one "novel" of four reviewed


def test_top_n_precision_respects_n_and_ranking():
    # top-2 by score = a, b -> genuine, rejected -> precision 0.5, reviewed 2
    m = lo.top_n_precision(_leads(), _outcomes(), n=2)
    assert m["in_top_n"] == 2
    assert m["reviewed"] == 2
    assert m["precision"] == 0.5


def test_signal_lift_orders_by_predictiveness():
    lift = lo.signal_lift(_leads(), _outcomes())
    by = {r["signal"]: r for r in lift.iter_rows(named=True)}
    # evasion_timing present on a(genuine)+b(rejected) -> rate_with 0.5
    assert by["evasion_timing"]["rate_with"] == 0.5
    # regulatory_breach present on c(novel)+d(rejected) -> rate_with 0.5
    assert by["regulatory_breach"]["rate_with"] == 0.5


def test_empty_outcomes_safe():
    m = lo.top_n_precision(_leads(), pl.DataFrame(schema={"lead_id": pl.Utf8, "verdict": pl.Utf8}))
    assert m["reviewed"] == 0
    assert m["precision"] == 0.0
