"""Tests for the investigative-value ranking driver."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from shellnet.investigations.investigative_ranking import (
    rank_clusters_by_investigative_value,
    render_investigative_ranking_markdown,
)
from shellnet.matching.company_features import build_unified_table
from shellnet.sources import gleif, icij, opencorporates, opensanctions


def _stage_full_fixtures(tmp_path: Path, fixtures_dir: Path) -> tuple[Path, Path]:
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
    opencorporates.parse_local_file(
        fixtures_dir / "opencorporates_company_sample.json"
    ).write_parquet(interim / "opencorporates_companies.parquet")
    gleif.ingest(input_path=fixtures_dir / "gleif_lei_sample.json", out_dir=interim)
    opensanctions.ingest(
        input_path=fixtures_dir / "opensanctions_entities_sample.json", out_dir=interim
    )
    processed = tmp_path / "processed"
    build_unified_table(interim_dir=interim, out_dir=processed)
    return interim, processed


def _two_clusters() -> dict[int, list[str]]:
    return {
        # ACME BVI + KY — fixture wires officer 30000001 to both ⇒ shared
        # officer signal AND cross-border secrecy mirror.
        1: ["icij:10000001", "icij:10000002"],
        # Sunrise PA + BVI — fixture only wires the PA entity to its
        # intermediary; the BVI sibling has no incident edges. Useful as a
        # 'real cluster with no edge corroboration' baseline.
        2: ["icij:10000003", "icij:10000004"],
    }


def test_rank_returns_one_row_per_cluster_sorted_by_score(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")

    df = rank_clusters_by_investigative_value(
        _two_clusters(),
        company_df=company_df,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    assert df.height == 2
    assert set(df["cluster_id"].to_list()) == {1, 2}
    # Sorted by score desc.
    scores = df["investigative_score"].to_list()
    assert scores == sorted(scores, reverse=True)
    # All score components ∈ [0, 1].
    for col in (
        "intermediary_rarity",
        "cross_jurisdiction_bridge",
        "sanctions_proximity",
        "registry_anchor_density",
        "hidden_central_entity",
        "dormant_but_connected",
        "shell_reuse",
    ):
        for v in df[col].to_list():
            assert 0.0 <= v <= 1.0


def test_rank_components_match_known_fixture_signals(tmp_path: Path, fixtures_dir: Path) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")

    df = rank_clusters_by_investigative_value(
        _two_clusters(),
        company_df=company_df,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    c1 = df.filter(pl.col("cluster_id") == 1).row(0, named=True)
    c2 = df.filter(pl.col("cluster_id") == 2).row(0, named=True)

    # Cluster 1 spans vg+ky (both secrecy) → cross_jurisdiction_bridge maxes out.
    assert c1["cross_jurisdiction_bridge"] == 1.0
    # Cluster 1 has 0 LEI/cn members.
    assert c1["registry_anchor_density"] == 0.0
    # Cluster 1's shared officer 30000001 → shell_reuse picks up the corpus
    # degree of that node (=2 in the fixture).
    assert c1["shell_reuse"] > 0
    # Cluster 1 must rank strictly above cluster 2 (more shared signal).
    assert c1["investigative_score"] > c2["investigative_score"]
    # Cluster 2 spans pa+vg (both secrecy) but has no shared-feature edges,
    # so repeat-derived components are 0 while the bridge component still fires.
    assert c2["cross_jurisdiction_bridge"] == 1.0
    assert c2["shell_reuse"] == 0.0
    assert c2["dormant_but_connected"] == 0.0
    # No sanctions inputs were provided → sanctions_proximity is 0 everywhere.
    assert c1["sanctions_proximity"] == 0.0
    assert c2["sanctions_proximity"] == 0.0


def test_rank_handles_empty_inputs_gracefully(tmp_path: Path, fixtures_dir: Path) -> None:
    _, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    # No edges / addresses / officers / intermediaries → repeats all empty but
    # scoring still runs, returning bounded scores per cluster.
    df = rank_clusters_by_investigative_value(
        _two_clusters(),
        company_df=company_df,
        edges_df=None,
    )
    assert df.height == 2
    for v in df["investigative_score"].to_list():
        assert 0.0 <= v <= 7.0


def test_rank_with_no_clusters_returns_empty_typed_frame() -> None:
    df = rank_clusters_by_investigative_value(
        {}, company_df=pl.DataFrame({"entity_uid": [], "source": []})
    )
    assert df.height == 0
    # Schema must still carry the expected columns so downstream join
    # logic doesn't break.
    for col in (
        "cluster_id",
        "investigative_score",
        "intermediary_rarity",
        "cross_jurisdiction_bridge",
    ):
        assert col in df.columns


def test_render_markdown_includes_score_columns_and_joins_defensibility(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")

    df = rank_clusters_by_investigative_value(
        _two_clusters(),
        company_df=company_df,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    # Synthetic defensibility frame — same shape as cluster_ranking.parquet.
    defensibility = pl.DataFrame({"cluster_id": [1, 2], "score": [4.20, 2.10]})
    md = render_investigative_ranking_markdown(
        df,
        defensibility_df=defensibility,
        top_n=10,
        dedupe_run_id="test-run",
    )
    assert "# Clusters ranked by investigative value" in md
    assert "investigative value" in md
    assert "defensibility" in md
    # Both cluster ids appear in the table.
    assert "| 1 |" in md
    assert "| 2 |" in md
    # The joined defensibility values appear.
    assert "4.20" in md
    assert "2.10" in md
    # Provenance includes the run id and the join note.
    assert "test-run" in md
    assert "Joined with defensibility" in md


def test_batch_repeats_match_per_cluster_results(tmp_path: Path, fixtures_dir: Path) -> None:
    """The batch driver must produce the same repeats per cluster as the
    per-cluster ``gather_repeats`` it shortcuts."""
    from shellnet.investigations.cluster_explainer import gather_repeats
    from shellnet.investigations.investigative_ranking import _batch_gather_repeats

    interim, _ = _stage_full_fixtures(tmp_path, fixtures_dir)
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")

    clusters = _two_clusters()
    batch = _batch_gather_repeats(
        clusters,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    for cid, uids in clusters.items():
        single = gather_repeats(
            uids,
            edges_df=edges_df,
            addresses_df=addresses_df,
            officers_df=officers_df,
            intermediaries_df=intermediaries_df,
        )
        b = batch[cid]
        assert {n.node for n in b[0]} == {n.node for n in single[0]}
        assert {n.node for n in b[1]} == {n.node for n in single[1]}
        assert {n.node for n in b[2]} == {n.node for n in single[2]}
