"""Phase 15 — GoldenMatch SDK wrapper smoke tests."""

from __future__ import annotations

import polars as pl
import pytest

from shellnet.matching.goldenmatch_runner import match_names


def test_match_names_returns_dataframe_with_prob_column():
    """A trivial fuzzy match between two frames with aligned schemas
    produces a DataFrame carrying a 'prob' column.

    GoldenMatch's match_df requires identical column sets on both
    sides (it concats them internally). The caller is responsible for
    projecting to a common schema before invoking — the wrapper just
    routes the call and surfaces the score column.
    """

    common_cols = ["id", "name", "normalized"]
    target = pl.DataFrame(
        {
            "id": ["t1"],
            "name": ["Acme Capital Partners LP"],
            "normalized": ["acme capital partners lp"],
        }
    )
    reference = pl.DataFrame(
        {
            "id": ["r1"],
            "name": ["Acme Capital Partners LP"],
            "normalized": ["acme capital partners lp"],
        }
    )
    assert sorted(target.columns) == sorted(common_cols)
    assert sorted(reference.columns) == sorted(common_cols)

    out = match_names(target, reference, name_col="normalized", fuzzy_threshold=0.9)
    assert isinstance(out, pl.DataFrame)
    assert "prob" in out.columns, out.columns


def test_match_names_rejects_missing_column():
    """name_col must exist on both sides."""
    target = pl.DataFrame({"a": ["x"]})
    reference = pl.DataFrame({"normalized": ["x"]})

    with pytest.raises(ValueError, match="name_col"):
        match_names(target, reference, name_col="normalized")


def test_match_names_empty_inputs_return_empty_with_prob():
    """Empty target with the right shape returns a typed-empty result."""
    schema = {"id": pl.String, "name": pl.String, "normalized": pl.String}
    target = pl.DataFrame(schema=schema)
    reference = pl.DataFrame(schema=schema)

    out = match_names(target, reference, name_col="normalized", fuzzy_threshold=0.9)
    assert out.is_empty()
    assert "prob" in out.columns
