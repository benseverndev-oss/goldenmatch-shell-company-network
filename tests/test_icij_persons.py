from pathlib import Path

import polars as pl

from shellnet.sources import icij


def _stage(tmp_path: Path, fixtures_dir: Path) -> Path:
    raw = tmp_path / "raw" / "icij"
    raw.mkdir(parents=True)
    for src, dst in (
        ("icij_officers_sample.csv", "nodes-officers.csv"),
        ("icij_intermediaries_sample.csv", "nodes-intermediaries.csv"),
        ("icij_entities_sample.csv", "nodes-entities.csv"),
    ):
        (raw / dst).write_text((fixtures_dir / src).read_text("utf-8"))
    return raw


def test_discover_includes_officers_and_intermediaries(tmp_path: Path, fixtures_dir: Path) -> None:
    raw = _stage(tmp_path, fixtures_dir)
    files = icij.discover_files(raw)
    assert files.officers is not None
    assert files.intermediaries is not None


def test_load_officers(tmp_path: Path, fixtures_dir: Path) -> None:
    raw = _stage(tmp_path, fixtures_dir)
    files = icij.discover_files(raw)
    df = icij.load_officers(files.officers)  # type: ignore[arg-type]
    assert df.height == 3
    cols = set(df.columns)
    assert {"source", "source_id", "name", "normalized_name", "country"} <= cols
    countries = set(df["country"].to_list())
    assert "gb" in countries
    assert "vg" in countries
    # Normalized names collapse "John Q. Public" and "John Q Public" identically.
    names = df["normalized_name"].to_list()
    assert names.count("john q public") == 2


def test_load_intermediaries(tmp_path: Path, fixtures_dir: Path) -> None:
    raw = _stage(tmp_path, fixtures_dir)
    files = icij.discover_files(raw)
    df = icij.load_intermediaries(files.intermediaries)  # type: ignore[arg-type]
    assert df.height == 2
    assert "status" in df.columns


def test_ingest_emits_person_parquets(tmp_path: Path, fixtures_dir: Path) -> None:
    raw = _stage(tmp_path, fixtures_dir)
    interim = tmp_path / "interim"
    written = icij.ingest(raw_dir=raw, out_dir=interim)
    assert "officers" in written
    assert "intermediaries" in written
    assert pl.read_parquet(written["officers"]).height == 3
    assert pl.read_parquet(written["intermediaries"]).height == 2
