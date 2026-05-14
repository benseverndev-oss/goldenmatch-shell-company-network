"""Tests for the seed-query investigation workflow."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from shellnet.investigations.seed_query import (
    collect_icij_neighbourhood,
    make_seed,
    rank_candidates,
    render_report,
)
from shellnet.matching.company_features import build_unified_table
from shellnet.sources import gleif, icij, opencorporates, opensanctions


def _stage_full_fixtures(tmp_path: Path, fixtures_dir: Path) -> tuple[Path, Path]:
    """Stage all four sources + ICIJ relationships into interim + processed."""
    raw_icij = tmp_path / "raw" / "icij"
    raw_icij.mkdir(parents=True)
    for src, dst in [
        ("icij_entities_sample.csv", "nodes-entities.csv"),
        ("icij_addresses_sample.csv", "nodes-addresses.csv"),
        ("icij_officers_sample.csv", "nodes-officers.csv"),
        ("icij_intermediaries_sample.csv", "nodes-intermediaries.csv"),
        ("icij_relationships_sample.csv", "relationships.csv"),
    ]:
        (raw_icij / dst).write_text((fixtures_dir / src).read_text("utf-8"))
    interim = tmp_path / "interim"
    icij.ingest(raw_dir=raw_icij, out_dir=interim)

    oc_df = opencorporates.parse_local_file(fixtures_dir / "opencorporates_company_sample.json")
    oc_df.write_parquet(interim / "opencorporates_companies.parquet")

    gleif.ingest(input_path=fixtures_dir / "gleif_lei_sample.json", out_dir=interim)
    opensanctions.ingest(
        input_path=fixtures_dir / "opensanctions_entities_sample.json",
        out_dir=interim,
    )

    processed = tmp_path / "processed"
    build_unified_table(interim_dir=interim, out_dir=processed)
    return interim, processed


def test_make_seed_normalizes_name_and_jurisdiction() -> None:
    seed = make_seed("ACME HOLDINGS LIMITED", "bvi")
    # normalize_company_name strips one trailing suffix run; "limited" is
    # popped but "holdings" is preserved (single-pass by design).
    assert seed.normalized_name == "acme holdings"
    assert seed.normalized_jurisdiction == "vg"


def test_make_seed_handles_unknown_jurisdiction() -> None:
    seed = make_seed("ACME", "atlantis")
    assert seed.normalized_jurisdiction is None


def test_rank_candidates_returns_in_and_outside_jurisdiction(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    _, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    df = pl.read_parquet(processed / "company_entities.parquet")

    seed = make_seed("ACME HOLDINGS LIMITED", "bvi")
    in_juris, outside = rank_candidates(df, seed, top_n=10, min_score=80.0)

    # BVI ACME row from ICIJ must be in-jurisdiction and on top, with an
    # exact normalized match.
    assert in_juris, "expected at least one in-jurisdiction candidate"
    top = in_juris[0]
    assert top.exact_normalized
    assert top.jurisdiction == "vg"
    assert top.source == "icij"
    assert top.score == 100.0

    # KY ACME row should land in the outside-jurisdiction bucket.
    outside_uids = {c.entity_uid for c in outside}
    assert any(c.jurisdiction == "ky" for c in outside)
    assert top.entity_uid not in outside_uids


def test_rank_candidates_global_when_no_jurisdiction(tmp_path: Path, fixtures_dir: Path) -> None:
    _, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    df = pl.read_parquet(processed / "company_entities.parquet")

    seed = make_seed("ACME HOLDINGS LIMITED", None)
    in_juris, outside = rank_candidates(df, seed, top_n=10, min_score=80.0)
    # No jurisdiction → everything is "in jurisdiction" and outside is empty.
    assert outside == []
    juris_seen = {c.jurisdiction for c in in_juris}
    assert {"vg", "ky"}.issubset(juris_seen)


def test_collect_icij_neighbourhood_pulls_addresses_and_officers(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")

    # ACME HOLDINGS LIMITED (BVI) has a registered_address + officer_of edge
    # in the fixture relationships.
    nbh = collect_icij_neighbourhood(
        ["icij:10000001"],
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
        company_df=company_df,
    )
    assert len(nbh) == 1
    n = nbh[0]
    assert n.entity_uid == "icij:10000001"
    assert n.addresses, "expected at least one registered address"
    assert n.officers, "expected at least one officer-of edge"
    # The BVI ACME's registered address should be in BVI.
    assert any((a.get("country") or "") == "vg" for a in n.addresses)


def test_render_report_includes_key_sections(tmp_path: Path, fixtures_dir: Path) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    df = pl.read_parquet(processed / "company_entities.parquet")

    seed = make_seed("ACME HOLDINGS LIMITED", "bvi")
    in_juris, outside = rank_candidates(df, seed, top_n=10, min_score=80.0)
    nbh = collect_icij_neighbourhood(
        [c.entity_uid for c in in_juris + outside if c.source == "icij"],
        edges_df=pl.read_parquet(interim / "icij_edges.parquet"),
        addresses_df=pl.read_parquet(interim / "icij_addresses.parquet"),
        officers_df=pl.read_parquet(interim / "icij_officers.parquet"),
        intermediaries_df=pl.read_parquet(interim / "icij_intermediaries.parquet"),
        company_df=df,
    )
    md = render_report(
        seed,
        in_juris=in_juris,
        outside_juris=outside,
        neighbourhoods=nbh,
        gm_context=None,
        sources_seen=sorted({c.source for c in in_juris + outside}),
        inputs_meta={"top_n": 10, "min_score": 80.0},
    )
    # Section anchors and seed echo.
    assert "# Investigation seed:" in md
    assert "ACME HOLDINGS LIMITED" in md
    assert "## Candidate records" in md
    assert "## Possible outside-jurisdiction matches" in md
    assert "## 1-hop ICIJ neighbourhood" in md
    assert "## Published GoldenMatch context" in md
    assert "no `DATABASE_URL` set" in md
    assert "## Provenance" in md
    # The same-jurisdiction top candidate (BVI ACME) must be in the report.
    assert "icij:10000001" in md
