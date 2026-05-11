from pathlib import Path

import polars as pl

from shellnet.matching.company_features import build_unified_table
from shellnet.sources import gleif, icij, opencorporates, opensanctions


def _stage_all(tmp_path: Path, fixtures_dir: Path) -> Path:
    interim = tmp_path / "interim"
    interim.mkdir()

    # ICIJ
    raw_icij = tmp_path / "raw" / "icij"
    raw_icij.mkdir(parents=True)
    (raw_icij / "panama.nodes-entities.csv").write_text(
        (fixtures_dir / "icij_entities_sample.csv").read_text("utf-8")
    )
    icij.ingest(raw_dir=raw_icij, out_dir=interim)

    # OpenCorporates — write parquet from local fixture parsing
    oc_df = opencorporates.parse_local_file(fixtures_dir / "opencorporates_company_sample.json")
    oc_df.write_parquet(interim / "opencorporates_companies.parquet")

    # GLEIF
    gleif.ingest(input_path=fixtures_dir / "gleif_lei_sample.json", out_dir=interim)

    # OpenSanctions
    opensanctions.ingest(
        input_path=fixtures_dir / "opensanctions_entities_sample.json",
        out_dir=interim,
    )
    return interim


def test_build_unified_table(tmp_path: Path, fixtures_dir: Path) -> None:
    interim = _stage_all(tmp_path, fixtures_dir)
    out_dir = tmp_path / "processed"
    path = build_unified_table(interim_dir=interim, out_dir=out_dir)
    assert path.exists()

    df = pl.read_parquet(path)
    sources = set(df["source"].to_list())
    # All four sources contributed at least one row.
    assert {"icij", "opencorporates", "gleif", "opensanctions"} <= sources
    # entity_uid is unique.
    assert df.height == df.unique(subset=["entity_uid"]).height
    # Same-company across sources shows up under the same normalized name.
    norm = df["normalized_name"].to_list()
    assert sum(1 for n in norm if n == "acme holdings") >= 3


def test_build_unified_table_handles_missing_sources(tmp_path: Path) -> None:
    interim = tmp_path / "interim"
    interim.mkdir()
    out_dir = tmp_path / "processed"
    path = build_unified_table(interim_dir=interim, out_dir=out_dir)
    assert path.exists()
    df = pl.read_parquet(path)
    assert df.height == 0
