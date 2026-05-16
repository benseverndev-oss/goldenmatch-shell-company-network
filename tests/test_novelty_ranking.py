"""Unit tests for novelty_score + auto_pin predicate.

The score is a triage signal; these tests lock the weights so a thoughtless
tweak doesn't silently reshuffle the exposé candidates index.
"""

from __future__ import annotations

import pytest

from shellnet.novelty_ranking import auto_pin, novelty_score


def test_zero_hits_localized_ran_yields_baseline_floor() -> None:
    # No web hits at all (localized RAN with 0 hits), no shell density:
    # max from web terms (0.40 + 0.25 + 0.15 = 0.80)
    score = novelty_score(
        hits_general=0, hits_offshore=0,
        hits_localized=0, localized_ran=True,
        n_linked_companies=0, n_jurisdictions=0,
    )
    assert score == pytest.approx(0.80, abs=1e-6)


def test_localized_skipped_does_not_grant_bonus() -> None:
    # No dominant jurisdiction → localized query SKIPPED.
    # The 0.15 term must NOT apply (was the bug spotted in review pass 2).
    score = novelty_score(
        hits_general=0, hits_offshore=0,
        hits_localized=0, localized_ran=False,
        n_linked_companies=0, n_jurisdictions=0,
    )
    assert score == pytest.approx(0.65, abs=1e-6)  # 0.40 + 0.25 + 0


def test_full_hits_full_density_yields_density_only() -> None:
    # Saturated web hits cancel the web bonus; only density terms contribute
    score = novelty_score(
        hits_general=10, hits_offshore=5,
        hits_localized=3, localized_ran=True,
        n_linked_companies=5, n_jurisdictions=3,
    )
    # 0 + 0 + 0 + 0.10 + 0.10
    assert score == pytest.approx(0.20, abs=1e-6)


def test_localized_zero_hits_when_run_breaks_to_full_bonus() -> None:
    base = dict(hits_general=0, hits_offshore=0, n_linked_companies=0, n_jurisdictions=0)
    score_ran_zero = novelty_score(**base, hits_localized=0, localized_ran=True)
    score_ran_one = novelty_score(**base, hits_localized=1, localized_ran=True)
    assert score_ran_zero - score_ran_one == pytest.approx(0.15, abs=1e-6)


def test_score_bounded_zero_to_one() -> None:
    assert 0.0 <= novelty_score(
        hits_general=0, hits_offshore=0,
        hits_localized=0, localized_ran=True,
        n_linked_companies=0, n_jurisdictions=0,
    ) <= 1.0
    assert 0.0 <= novelty_score(
        hits_general=100, hits_offshore=100,
        hits_localized=100, localized_ran=True,
        n_linked_companies=100, n_jurisdictions=100,
    ) <= 1.0


def test_density_bonus_caps() -> None:
    s5 = novelty_score(
        hits_general=10, hits_offshore=5,
        hits_localized=3, localized_ran=True,
        n_linked_companies=5, n_jurisdictions=0,
    )
    s20 = novelty_score(
        hits_general=10, hits_offshore=5,
        hits_localized=3, localized_ran=True,
        n_linked_companies=20, n_jurisdictions=0,
    )
    assert s5 == s20


def test_auto_pin_requires_zero_web_hits_and_multi_shell() -> None:
    assert auto_pin(hits_general=0, hits_offshore=0, n_linked_companies=3) is True
    assert auto_pin(hits_general=1, hits_offshore=0, n_linked_companies=3) is False
    assert auto_pin(hits_general=0, hits_offshore=1, n_linked_companies=3) is False
    assert auto_pin(hits_general=0, hits_offshore=0, n_linked_companies=2) is False
