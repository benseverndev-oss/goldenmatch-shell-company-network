from pathlib import Path

import polars as pl

from shellnet.sources import opensanctions


def test_ingest_sample(tmp_path: Path, fixtures_dir: Path) -> None:
    out = opensanctions.ingest(
        input_path=fixtures_dir / "opensanctions_entities_sample.json",
        out_dir=tmp_path,
    )
    assert out is not None
    df = pl.read_parquet(out)
    assert df.height == 3
    schemas = set(df["entity_schema"].to_list())
    assert {"Company", "Person"} <= schemas
    # Identifiers and topics survive parsing.
    company_row = df.filter(pl.col("source_id") == "ofac-12345").row(0, named=True)
    assert "529900T8BM49AURSDO55" in company_row["identifiers"]
    assert "1234567" in company_row["identifiers"]
    assert "sanction" in company_row["topics"]
