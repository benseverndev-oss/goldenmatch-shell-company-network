"""Tests for the person-side seed-query workflow."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from shellnet.investigations.person_query import (
    collect_company_edges,
    make_person_seed,
    rank_person_candidates,
    render_person_report,
)
from shellnet.matching.company_features import build_unified_table
from shellnet.matching.person_features import build_person_table
from shellnet.sources import icij


def _stage(tmp_path: Path, fixtures_dir: Path) -> tuple[Path, Path, Path]:
    raw = tmp_path / "raw" / "icij"
    raw.mkdir(parents=True)
    for src, dst in [
        ("icij_entities_sample.csv", "nodes-entities.csv"),
        ("icij_officers_sample.csv", "nodes-officers.csv"),
        ("icij_intermediaries_sample.csv", "nodes-intermediaries.csv"),
        ("icij_relationships_sample.csv", "relationships.csv"),
    ]:
        (raw / dst).write_text((fixtures_dir / src).read_text("utf-8"))
    interim = tmp_path / "interim"
    icij.ingest(raw_dir=raw, out_dir=interim)
    processed = tmp_path / "processed"
    build_unified_table(interim_dir=interim, out_dir=processed)
    build_person_table(interim_dir=interim, out_dir=processed)
    return interim, processed, interim / "icij_edges.parquet"


def test_make_person_seed_normalizes() -> None:
    seed = make_person_seed("Jeffrey E Epstein", "us")
    assert seed.normalized_country == "us"
    assert "jeffrey" in seed.normalized_name and "epstein" in seed.normalized_name


def test_rank_person_finds_fixture_officer(tmp_path: Path, fixtures_dir: Path) -> None:
    _, processed, _ = _stage(tmp_path, fixtures_dir)
    df = pl.read_parquet(processed / "person_entities.parquet")
    # Fixture has 'John Q. Public' as an officer.
    seed = make_person_seed("John Public", None)
    in_country, _ = rank_person_candidates(df, seed, min_score=80.0, top_n=10)
    assert in_country, "expected at least one match"
    assert any("john" in c.normalized_name and "public" in c.normalized_name for c in in_country)


def test_collect_company_edges_walks_officer_of(tmp_path: Path, fixtures_dir: Path) -> None:
    interim, processed, edges_path = _stage(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(edges_path)
    # icij:30000001 is John Q. Public per the fixture — director of icij:10000001 + 10000002.
    edges = collect_company_edges(["icij:30000001"], edges_df=edges_df, company_df=company_df)
    assert "icij:30000001" in edges
    company_uids = {e.company_uid for e in edges["icij:30000001"]}
    assert {"icij:10000001", "icij:10000002"} <= company_uids


def test_render_person_report_includes_sections(tmp_path: Path, fixtures_dir: Path) -> None:
    interim, processed, edges_path = _stage(tmp_path, fixtures_dir)
    df = pl.read_parquet(processed / "person_entities.parquet")
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(edges_path)
    seed = make_person_seed("John Public", None)
    in_country, outside = rank_person_candidates(df, seed, min_score=80.0)
    edges = collect_company_edges(
        [c.entity_uid for c in in_country if c.source == "icij"],
        edges_df=edges_df,
        company_df=company_df,
    )
    md = render_person_report(
        seed,
        in_country=in_country,
        outside_country=outside,
        edges_by_person=edges,
        inputs_meta={"top_n": 10},
        source_note="test",
    )
    assert "# Person investigation:" in md
    assert "Hypothesis, not proof" in md
    assert "## Candidate persons (same country)" in md
    assert "## Companies attached to matched persons" in md
    assert "icij:10000001" in md  # ACME HOLDINGS LIMITED is one of John Public's companies
