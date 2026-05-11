from pathlib import Path

from shellnet.sources import opencorporates


def test_parse_local_file(fixtures_dir: Path) -> None:
    df = opencorporates.parse_local_file(fixtures_dir / "opencorporates_company_sample.json")
    assert df.height == 3
    assert set(df.columns) >= {
        "source", "source_id", "name", "normalized_name", "jurisdiction",
        "company_number", "address_raw", "normalized_address",
    }
    juris = set(df["jurisdiction"].to_list())
    assert juris == {"gb", "lu"}
    # Suffix stripped from normalized_name where applicable.
    assert "acme holdings" in df["normalized_name"].to_list()


def test_cache_key_is_stable() -> None:
    a = opencorporates._cache_key({"q": "Foo", "page": 1})
    b = opencorporates._cache_key({"page": 1, "q": "Foo"})
    assert a == b


def test_dry_run_smoke(monkeypatch, tmp_path: Path) -> None:
    """Dry-run mode must complete without HTTP and write an empty parquet."""
    # Point cache + interim into tmp_path so we never touch the repo dirs.
    monkeypatch.setattr(opencorporates, "OPENCORPORATES_CACHE", tmp_path / "cache")
    out_dir = tmp_path / "interim"
    out = opencorporates.ingest_query(
        "Acme Holdings",
        jurisdiction="gb",
        limit=10,
        sleep_seconds=0,
        use_cache=False,
        dry_run=True,
        out_dir=out_dir,
    )
    assert out.exists()
