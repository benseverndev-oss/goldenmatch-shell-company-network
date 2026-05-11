from pathlib import Path

import polars as pl

from shellnet.matching.person_features import build_person_table
from shellnet.sources import icij, opensanctions


def _stage(tmp_path: Path, fixtures_dir: Path) -> Path:
    raw = tmp_path / "raw" / "icij"
    raw.mkdir(parents=True)
    for src, dst in (
        ("icij_officers_sample.csv", "nodes-officers.csv"),
        ("icij_intermediaries_sample.csv", "nodes-intermediaries.csv"),
    ):
        (raw / dst).write_text((fixtures_dir / src).read_text("utf-8"))
    interim = tmp_path / "interim"
    icij.ingest(raw_dir=raw, out_dir=interim)
    opensanctions.ingest(
        input_path=fixtures_dir / "opensanctions_entities_sample.json",
        out_dir=interim,
    )
    return interim


def test_build_person_table(tmp_path: Path, fixtures_dir: Path) -> None:
    interim = _stage(tmp_path, fixtures_dir)
    out_dir = tmp_path / "processed"
    out = build_person_table(interim_dir=interim, out_dir=out_dir)
    df = pl.read_parquet(out)
    # 3 officers + 2 intermediaries + 1 OpenSanctions Person = 6
    assert df.height == 6
    kinds = set(df["kind"].to_list())
    assert {"officer", "intermediary", "person"} <= kinds
    # entity_uid is unique.
    assert df.height == df.unique(subset=["entity_uid"]).height


def test_build_person_table_empty(tmp_path: Path) -> None:
    interim = tmp_path / "empty_interim"
    interim.mkdir()
    out_dir = tmp_path / "processed"
    out = build_person_table(interim_dir=interim, out_dir=out_dir)
    df = pl.read_parquet(out)
    assert df.height == 0
