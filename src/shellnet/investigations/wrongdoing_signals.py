"""Wrongdoing-signal scoring layer (roadmap Phase 2, issue #157).

Combines the per-lead wrongdoing *signals* (the act) into one
``wrongdoing_score``, **gated** by whether the target is currently live and
whether there is a public-harm angle. This deliberately makes signal strength
dominate — unlike the structure-centric attention score — so the queue surfaces
"a wrongdoing act, at a live target" rather than "a dense graph".

A lead is a row keyed by ``lead_id`` (typically a ``company_id``) with any
subset of the signal columns in :data:`DEFAULT_WEIGHTS` (missing = 0), plus two
optional gate inputs produced by Phase 3:

  ``active``       tri-state: ``True`` live / ``False`` struck-off / ``None``
                   unknown. With ``active_gate`` on, only explicit ``False`` is
                   dropped (unknown is kept, flagged for review).
  ``harm_weight``  multiplier in [0, ~2]; absent/None treated as 1.0.

Weights are config (a plain dict) so Phase 6 can retune them from review
outcomes rather than intuition.
"""

from __future__ import annotations

import polars as pl

__all__ = ["DEFAULT_WEIGHTS", "score_wrongdoing"]

# Descending evidential weight (see the taxonomy in the roadmap / issue #157).
DEFAULT_WEIGHTS: dict[str, float] = {
    "evasion_timing": 1.0,
    "regulatory_breach": 0.9,
    "bank_or_court_flag": 0.8,
    "nominee_front": 0.7,
    "sanctioned_parent": 0.6,
}


def score_wrongdoing(
    leads: pl.DataFrame,
    weights: dict[str, float] | None = None,
    *,
    active_gate: bool = True,
    harm_gate: bool = False,
) -> pl.DataFrame:
    """Return ``leads`` with a ``wrongdoing_score``, gated and sorted desc.

    ``wrongdoing_score = (Σ wᵢ · signalᵢ) · harm_mult``, where ``harm_mult`` is
    ``harm_weight`` (default 1.0). Gates drop rows rather than zero them so the
    queue stays short:

    - ``active_gate``: drop rows with ``active == False`` (keep ``None``).
    - ``harm_gate``: drop rows with no positive ``harm_weight``.
    """
    weights = weights or DEFAULT_WEIGHTS
    if leads.height == 0:
        return leads.with_columns(pl.lit(0.0).alias("wrongdoing_score"))

    base = pl.lit(0.0)
    for signal, w in weights.items():
        if signal in leads.columns:
            base = base + pl.col(signal).cast(pl.Float64).fill_null(0.0) * w

    harm_mult = (
        pl.col("harm_weight").cast(pl.Float64).fill_null(1.0)
        if "harm_weight" in leads.columns
        else pl.lit(1.0)
    )
    out = leads.with_columns((base * harm_mult).alias("wrongdoing_score"))

    if active_gate and "active" in out.columns:
        out = out.filter(pl.col("active").fill_null(True) != False)  # noqa: E712
    if harm_gate and "harm_weight" in out.columns:
        out = out.filter(pl.col("harm_weight").cast(pl.Float64).fill_null(0.0) > 0)

    return out.sort("wrongdoing_score", descending=True)
