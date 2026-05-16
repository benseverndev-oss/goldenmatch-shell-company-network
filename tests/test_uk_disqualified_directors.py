from pathlib import Path

import polars as pl

from shellnet.sources import uk_disqualified_directors

_SAMPLE_CSV = (
    "caseNumber,companyName,personName,dateOfBirth,dateOrderStarts,"
    "disqualificationLength,lastKnownAddress,informationCorrectAsOf,conduct\n"
    '"123","ACME LIMITED","Smith, John","01/01/1970","01/06/2021","5 Years",'
    '"12 High Street, London, SW1A 1AA","01/01/2024",'
    '"Caused company to trade while insolvent."\n'
    '"124","Other Co Ltd","Doe, Jane","",,"3 Years",'
    '"45 Elm Avenue, Manchester, M1 2AB","01/01/2024","Withheld books and records."\n'
)


def test_ingest_projects_csv(tmp_path: Path) -> None:
    src = tmp_path / "disqualified-directors.csv"
    src.write_text(_SAMPLE_CSV, encoding="utf-8")
    out_dir = tmp_path / "interim"

    out = uk_disqualified_directors.ingest(src, out_dir=out_dir)
    assert out.exists()

    df = pl.read_parquet(out).sort("source_id")
    assert df.height == 2
    assert df["source"].unique().to_list() == ["uk_disqualified_directors"]

    row = df.filter(pl.col("source_id") == "123").to_dicts()[0]
    assert row["person_name"] == "Smith, John"
    assert row["normalized_person_name"]  # normalizer produces non-empty token
    assert row["company_name"] == "ACME LIMITED"
    assert row["normalized_company_name"]
    assert row["address_raw"].startswith("12 High Street")
    assert row["normalized_address"]
    assert row["date_of_birth"] == "01/01/1970"
    assert row["disqualification_length"] == "5 Years"

    row2 = df.filter(pl.col("source_id") == "124").to_dicts()[0]
    # Missing DoB tolerated — the normalizer should not throw.
    assert row2["normalized_person_name"]
