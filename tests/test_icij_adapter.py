from pathlib import Path

from shellnet.sources import icij


def _stage_icij(tmp_path: Path, fixtures_dir: Path) -> Path:
    """Copy the ICIJ-shaped fixtures into tmp_path with the names the adapter
    expects to discover."""
    raw = tmp_path / "raw" / "icij"
    raw.mkdir(parents=True)
    mapping = {
        "icij_entities_sample.csv": "panama_papers.nodes-entities.csv",
        "icij_addresses_sample.csv": "panama_papers.nodes-addresses.csv",
        "icij_relationships_sample.csv": "panama_papers.relationships.csv",
    }
    for src, dst in mapping.items():
        (raw / dst).write_text((fixtures_dir / src).read_text("utf-8"))
    return raw


def test_discover_files(tmp_path: Path, fixtures_dir: Path) -> None:
    raw = _stage_icij(tmp_path, fixtures_dir)
    files = icij.discover_files(raw)
    assert files.entities is not None
    assert files.addresses is not None
    assert files.relationships is not None


def test_discover_files_empty(tmp_path: Path) -> None:
    raw = tmp_path / "empty"
    raw.mkdir()
    files = icij.discover_files(raw)
    assert files.is_empty()


def test_load_entities(tmp_path: Path, fixtures_dir: Path) -> None:
    raw = _stage_icij(tmp_path, fixtures_dir)
    files = icij.discover_files(raw)
    df = icij.load_entities(files.entities)  # type: ignore[arg-type]
    assert df.height == 5
    expected_cols = {
        "source",
        "source_id",
        "name",
        "normalized_name",
        "jurisdiction",
        "address_raw",
        "normalized_address",
    }
    assert expected_cols.issubset(set(df.columns))
    # Jurisdiction is normalized to ISO alpha-2.
    juris = df["jurisdiction"].to_list()
    assert "vg" in juris  # British Virgin Islands → vg
    assert "ky" in juris  # Cayman Islands → ky
    # Suffix stripped from the normalized name.
    norm_names = df["normalized_name"].to_list()
    assert "acme holdings" in norm_names


def test_ingest_creates_parquet(tmp_path: Path, fixtures_dir: Path) -> None:
    raw = _stage_icij(tmp_path, fixtures_dir)
    out = tmp_path / "interim"
    written = icij.ingest(raw_dir=raw, out_dir=out)
    assert "entities" in written
    assert "addresses" in written
    assert "edges" in written
    assert all(p.exists() for p in written.values())


def test_ingest_no_files_returns_empty(tmp_path: Path) -> None:
    raw = tmp_path / "no_data"
    raw.mkdir()
    out = tmp_path / "interim"
    written = icij.ingest(raw_dir=raw, out_dir=out)
    assert written == {}
