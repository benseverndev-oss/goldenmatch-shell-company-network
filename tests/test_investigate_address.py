"""Tests for the address-side seed-query workflow."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from shellnet.investigations.address_query import (
    collect_entities_at_addresses,
    make_address_seed,
    rank_addresses,
    render_address_report,
)
from shellnet.matching.address_features import build_address_table
from shellnet.matching.company_features import build_unified_table
from shellnet.sources import icij


def _stage(tmp_path: Path, fixtures_dir: Path) -> tuple[Path, Path, Path]:
    raw = tmp_path / "raw" / "icij"
    raw.mkdir(parents=True)
    for src, dst in [
        ("icij_entities_sample.csv", "nodes-entities.csv"),
        ("icij_addresses_sample.csv", "nodes-addresses.csv"),
        ("icij_relationships_sample.csv", "relationships.csv"),
    ]:
        (raw / dst).write_text((fixtures_dir / src).read_text("utf-8"))
    interim = tmp_path / "interim"
    icij.ingest(raw_dir=raw, out_dir=interim)
    processed = tmp_path / "processed"
    build_unified_table(interim_dir=interim, out_dir=processed)
    build_address_table(interim_dir=interim, out_dir=processed)
    return interim, processed, interim / "icij_edges.parquet"


def test_make_address_seed_normalizes() -> None:
    seed = make_address_seed("Ugland House, Grand Cayman", "ky")
    assert seed.normalized_country == "ky"
    assert "ugland" in seed.normalized_text


def test_rank_addresses_finds_ugland_house(tmp_path: Path, fixtures_dir: Path) -> None:
    _, processed, _ = _stage(tmp_path, fixtures_dir)
    addr_df = pl.read_parquet(processed / "address_entities.parquet")
    seed = make_address_seed("Ugland House, South Church Street, George Town, Grand Cayman", "ky")
    in_country, _ = rank_addresses(addr_df, seed, min_score=55.0, top_n=10)
    assert in_country, "expected at least one ugland-house match"
    assert any("ugland" in c.normalized_text for c in in_country)


def test_collect_entities_at_addresses_surfaces_registered_companies(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    interim, processed, edges_path = _stage(tmp_path, fixtures_dir)
    addr_df = pl.read_parquet(processed / "address_entities.parquet")
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(edges_path)
    seed = make_address_seed("Ugland House Grand Cayman", "ky")
    in_country, outside = rank_addresses(addr_df, seed, min_score=55.0, top_n=10)
    grouped = collect_entities_at_addresses(
        in_country + outside, company_df=company_df, edges_df=edges_df
    )
    flat_uids = {e.entity_uid for bucket in grouped.values() for e in bucket}
    # The Pandora-Papers ACME (icij:10000002) is registered at Ugland House
    # per the fixture relationships.
    assert "icij:10000002" in flat_uids


def test_render_address_report_includes_sections(tmp_path: Path, fixtures_dir: Path) -> None:
    interim, processed, edges_path = _stage(tmp_path, fixtures_dir)
    addr_df = pl.read_parquet(processed / "address_entities.parquet")
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(edges_path)
    seed = make_address_seed("Ugland House Grand Cayman", "ky")
    in_country, outside = rank_addresses(addr_df, seed, min_score=55.0, top_n=10)
    grouped = collect_entities_at_addresses(
        in_country + outside, company_df=company_df, edges_df=edges_df
    )
    md = render_address_report(
        seed,
        in_country=in_country,
        outside_country=outside,
        entities_by_address=grouped,
        inputs_meta={"top_n": 10},
        source_note="test",
    )
    assert "# Address investigation:" in md
    assert "Hypothesis, not proof" in md
    assert "## Entities registered at matched addresses" in md
