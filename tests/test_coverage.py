from pathlib import Path

import polars as pl

from shellnet.reporting.coverage import (
    coverage_for,
    coverage_table_markdown,
    render_report,
)


def test_coverage_for_basic(tmp_path: Path) -> None:
    df = pl.DataFrame(
        {
            "name": ["a", "", None, "b"],
            "n": [1, 2, 3, 4],
        }
    )
    stats = coverage_for(df)
    name = next(s for s in stats if s.column == "name")
    # 2 non-empty out of 4
    assert name.non_empty == 2
    assert abs(name.fill_rate - 0.5) < 1e-9
    n = next(s for s in stats if s.column == "n")
    assert n.non_empty == 4
    assert n.fill_rate == 1.0


def test_markdown_renders() -> None:
    df = pl.DataFrame({"a": ["x"], "b": [1]})
    stats = coverage_for(df)
    md = coverage_table_markdown(stats)
    assert "| Column |" in md
    assert "`a`" in md
    assert "`b`" in md


def test_render_report_handles_missing(tmp_path: Path) -> None:
    real = tmp_path / "exists.parquet"
    pl.DataFrame({"x": [1, 2]}).write_parquet(real)
    missing = tmp_path / "nope.parquet"
    out = render_report([real, missing])
    assert "exists.parquet" in out
    assert "missing" in out
