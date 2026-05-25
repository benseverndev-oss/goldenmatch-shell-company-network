"""Lead-review feedback loop (roadmap Phase 6, issue #161).

Closes the loop: record human-review verdicts per lead, then measure the
metric that actually matters — **top-N precision** (fraction of reviewed leads
that survive as genuine/novel/published, not rejected) — and surface which
*signals* correlate with a genuine verdict so Phase-2 weights can be retuned
from evidence rather than intuition.

Pure functions over polars frames; the script wires the outcomes CSV in.
"""

from __future__ import annotations

import polars as pl

__all__ = [
    "POSITIVE_VERDICTS",
    "OUTCOME_COLUMNS",
    "top_n_precision",
    "signal_lift",
]

# Verdicts that count a lead as a "win".
POSITIVE_VERDICTS: frozenset[str] = frozenset({"genuine", "novel", "published"})

OUTCOME_COLUMNS: tuple[str, ...] = ("lead_id", "reviewed_at", "verdict", "reviewer_note")


def _reviewed(leads: pl.DataFrame, outcomes: pl.DataFrame) -> pl.DataFrame:
    o = outcomes.select(
        "lead_id", pl.col("verdict").cast(pl.Utf8).str.to_lowercase().alias("verdict")
    )
    return leads.join(o, on="lead_id", how="inner").with_columns(
        pl.col("verdict").is_in(list(POSITIVE_VERDICTS)).alias("is_positive")
    )


def top_n_precision(
    leads: pl.DataFrame, outcomes: pl.DataFrame, n: int = 20
) -> dict[str, float | int]:
    """Precision + novelty rate among the reviewed leads in the top-``n`` queue."""
    ranked = leads
    if "wrongdoing_score" in ranked.columns:
        ranked = ranked.sort("wrongdoing_score", descending=True)
    top = ranked.head(n)
    rev = _reviewed(top, outcomes)
    reviewed = rev.height
    positives = int(rev["is_positive"].sum()) if reviewed else 0
    novel = int((rev["verdict"] == "novel").sum()) if reviewed else 0
    return {
        "n": n,
        "in_top_n": top.height,
        "reviewed": reviewed,
        "positives": positives,
        "precision": round(positives / reviewed, 3) if reviewed else 0.0,
        "novelty_rate": round(novel / reviewed, 3) if reviewed else 0.0,
    }


def signal_lift(
    leads: pl.DataFrame, outcomes: pl.DataFrame, signals: list[str] | None = None
) -> pl.DataFrame:
    """Per-signal lift in the positive rate when the signal is present.

    For each signal column, ``lift = P(positive | signal>0) - P(positive |
    signal==0)`` over reviewed leads. Drives Phase-2 weight retuning.
    """
    rev = _reviewed(leads, outcomes)
    default = [
        "evasion_timing",
        "regulatory_breach",
        "nominee_front",
        "sanctioned_parent",
        "bank_or_court_flag",
    ]
    cols = [c for c in (signals or default) if c in rev.columns]
    rows = []
    for c in cols:
        with_sig = rev.filter(pl.col(c).cast(pl.Float64).fill_null(0.0) > 0)
        without = rev.filter(pl.col(c).cast(pl.Float64).fill_null(0.0) <= 0)
        rw = with_sig["is_positive"].mean() if with_sig.height else None
        ro = without["is_positive"].mean() if without.height else None
        rows.append(
            {
                "signal": c,
                "n_with": with_sig.height,
                "rate_with": round(rw, 3) if rw is not None else None,
                "rate_without": round(ro, 3) if ro is not None else None,
                "lift": round((rw or 0.0) - (ro or 0.0), 3) if rw is not None else None,
            }
        )
    return (
        pl.DataFrame(rows)
        if rows
        else pl.DataFrame(
            schema={
                "signal": pl.Utf8,
                "n_with": pl.Int64,
                "rate_with": pl.Float64,
                "rate_without": pl.Float64,
                "lift": pl.Float64,
            }
        )
    )
