from pathlib import Path

import polars as pl

from shellnet.matching.labels import (
    LABEL_COLUMNS,
    derive_seed_labels,
    evaluate,
    load_labels,
    save_labels,
)


def _make_company_table(tmp_path: Path) -> Path:
    """Tiny company table that exercises the derived-label rules."""
    df = pl.DataFrame(
        {
            "entity_uid": ["icij:a", "gleif:b", "icij:c", "opencorporates:d", "gleif:e"],
            "source": ["icij", "gleif", "icij", "opencorporates", "gleif"],
            "source_id": ["a", "b", "c", "d", "e"],
            "name": ["Acme Ltd", "Acme Limited", "Other Corp", "Acme Ltd (UK)", "Acme Ltd"],
            "normalized_name": ["acme", "acme", "other", "acme", "acme"],
            "jurisdiction": ["gb", "gb", "us", "gb", "gb"],
            "company_number": ["1234567", "", "", "1234567", ""],
            "lei": ["", "529900T8BM49AURSDO55", "", "", "DIFFERENTLEI00000000"],
            "status": ["Active", "ISSUED", "", "", "ISSUED"],
            "legal_form": ["ltd", "ltd", "corp", "ltd", "ltd"],
            "address_raw": ["", "", "", "", ""],
            "normalized_address": ["", "", "", "", ""],
        }
    )
    path = tmp_path / "company_entities.parquet"
    df.write_parquet(path)
    return path


def test_derive_seed_labels_finds_shared_company_number(tmp_path: Path) -> None:
    path = _make_company_table(tmp_path)
    labels = derive_seed_labels(path)
    # icij:a and opencorporates:d share company_number 1234567 in gb → match.
    match_rows = labels.filter(pl.col("label") == "match")
    pair = sorted(("icij:a", "opencorporates:d"))
    found = any(
        (r["left_uid"], r["right_uid"]) == tuple(pair) for r in match_rows.iter_rows(named=True)
    )
    assert found


def test_derive_seed_labels_finds_divergent_lei(tmp_path: Path) -> None:
    path = _make_company_table(tmp_path)
    labels = derive_seed_labels(path)
    # gleif:b and gleif:e share normalized_name "acme" but have different LEIs → no_match.
    no_match_rows = labels.filter(pl.col("label") == "no_match")
    pair = sorted(("gleif:b", "gleif:e"))
    found = any(
        (r["left_uid"], r["right_uid"]) == tuple(pair) for r in no_match_rows.iter_rows(named=True)
    )
    assert found


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    df = pl.DataFrame(
        {
            "left_uid": ["z:1", "a:2"],
            "right_uid": ["a:9", "b:5"],
            "label": ["match", "no_match"],
            "source": ["human:alice", "derived:test"],
            "reason": ["", ""],
        }
    )
    path = tmp_path / "labels.csv"
    save_labels(df, path)
    loaded = load_labels(path)
    # left_uid must be lexicographically <= right_uid after canonicalisation.
    for r in loaded.iter_rows(named=True):
        assert r["left_uid"] <= r["right_uid"]
    assert set(loaded.columns) == set(LABEL_COLUMNS)


def test_evaluate_basic() -> None:
    labels = pl.DataFrame(
        {
            "left_uid": ["a", "a", "c"],
            "right_uid": ["b", "c", "d"],
            "label": ["match", "match", "no_match"],
            "source": ["human:a", "derived:x", "human:b"],
            "reason": ["", "", ""],
        }
    )
    predicted = [("a", "b"), ("c", "d")]  # 1 TP + 1 FP, missing (a,c)
    metrics = evaluate(predicted, labels)
    assert metrics.true_positive == 1
    assert metrics.false_positive == 1
    assert metrics.false_negative == 1  # (a, c) is a labelled match we missed


def test_evaluate_human_only_source_filter() -> None:
    labels = pl.DataFrame(
        {
            "left_uid": ["a", "a"],
            "right_uid": ["b", "c"],
            "label": ["match", "match"],
            "source": ["human:alice", "derived:x"],
            "reason": ["", ""],
        }
    )
    predicted = [("a", "b")]
    human = evaluate(predicted, labels, sources=("human:",))
    # Only one labelled match in scope; we got it → recall 1.0, precision 1.0.
    assert human.precision == 1.0
    assert human.recall == 1.0
