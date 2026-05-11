from pathlib import Path

from shellnet.sources import gleif


def test_ingest_sample(tmp_path: Path, fixtures_dir: Path) -> None:
    out = gleif.ingest(
        input_path=fixtures_dir / "gleif_lei_sample.json",
        sample=0,
        out_dir=tmp_path,
    )
    assert out is not None
    assert out.exists()
    import polars as pl

    df = pl.read_parquet(out)
    assert df.height == 2
    leis = set(df["lei"].to_list())
    assert "529900T8BM49AURSDO55" in leis
    # Jurisdiction is lowercased to ISO alpha-2.
    assert set(df["jurisdiction"].to_list()) == {"gb", "lu"}
    # Parent LEI flowed through.
    parents = [p for p in df["parent_lei"].to_list() if p]
    assert "ABCDEFGHIJKLMNOPQRST" in parents


def test_ingest_missing_returns_none(tmp_path: Path) -> None:
    out = gleif.ingest(input_path=tmp_path / "does_not_exist.json", out_dir=tmp_path)
    assert out is None
