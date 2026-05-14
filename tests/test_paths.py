"""Tests for path helpers."""

from __future__ import annotations

from shellnet.paths import PROJECT_ROOT, relpath_for_report


def test_relpath_for_report_inside_project() -> None:
    p = PROJECT_ROOT / "data" / "processed" / "company_entities.parquet"
    assert relpath_for_report(p) == "data/processed/company_entities.parquet"


def test_relpath_for_report_outside_project_falls_back_to_basename(
    tmp_path,
) -> None:
    p = tmp_path / "sub" / "file.parquet"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"")
    assert relpath_for_report(p) == "file.parquet"


def test_relpath_for_report_accepts_string() -> None:
    p = PROJECT_ROOT / "data" / "interim" / "icij_edges.parquet"
    assert relpath_for_report(str(p)) == "data/interim/icij_edges.parquet"
