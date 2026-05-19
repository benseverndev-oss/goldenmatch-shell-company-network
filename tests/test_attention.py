"""Tests for the human-attention optimizer."""

from __future__ import annotations

import polars as pl

from shellnet.investigations.attention import (
    DEFAULT_WEIGHTS,
    UNCERTAINTY_ANOMALY_KINDS,
    AttentionScore,
    rank_by_attention,
    render_attention_ranking_markdown,
    render_next_actions_markdown,
    select_diverse_queue,
)


def _row(**overrides) -> dict:
    """Build one investigative-ranking-shaped row with sensible defaults."""
    base = {
        "cluster_id": 1,
        "size": 3,
        "sources": "icij",
        "jurisdictions": "vg=1|ky=1",
        "leaks_present": "Panama Papers",
        "intermediary_rarity": 0.0,
        "cross_jurisdiction_bridge": 0.5,
        "sanctions_proximity": 0.0,
        "registry_anchor_density": 0.0,
        "hidden_central_entity": 0.0,
        "dormant_but_connected": 0.0,
        "shell_reuse": 0.0,
        "investigative_score": 0.5,
        "n_anomalies": 0,
        "n_high_severity_anomalies": 0,
        "top_anomaly_kind": "",
        "n_edges_incident": 2,
        "n_leak_labels": 1,
        "n_sources": 1,
        "top_intermediary": "",
        "top_address": "",
        "top_officer": "",
        "sample_names": "A · B",
    }
    base.update(overrides)
    return base


def _df(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows)


def test_default_weights_sum_to_six_for_uniform_scoring() -> None:
    assert sum(DEFAULT_WEIGHTS.values()) == 6.0


def test_rank_by_attention_returns_one_row_per_cluster() -> None:
    df = _df([_row(cluster_id=1), _row(cluster_id=2, investigative_score=2.0)])
    out = rank_by_attention(df)
    assert out.height == 2
    assert set(out["cluster_id"].to_list()) == {1, 2}
    # Sorted by attention_score desc.
    scores = out["attention_score"].to_list()
    assert scores == sorted(scores, reverse=True)


def test_components_all_in_unit_interval() -> None:
    df = _df(
        [
            _row(cluster_id=1, investigative_score=3.0, n_anomalies=5, n_high_severity_anomalies=2),
            _row(cluster_id=2, investigative_score=1.0, n_anomalies=0),
        ]
    )
    out = rank_by_attention(df)
    for col in (
        "novelty",
        "structural_anomaly",
        "uncertainty_concentration",
        "graph_centrality",
        "evidence_density",
        "cross_source_convergence",
    ):
        for v in out[col].to_list():
            assert 0.0 <= v <= 1.0, f"{col}={v}"


def test_structural_anomaly_grows_with_severity_weighted_count() -> None:
    df = _df(
        [
            _row(cluster_id=1, n_anomalies=0),
            _row(cluster_id=2, n_anomalies=3, n_high_severity_anomalies=3),
        ]
    )
    out = rank_by_attention(df)
    r1 = out.filter(pl.col("cluster_id") == 1).row(0, named=True)
    r2 = out.filter(pl.col("cluster_id") == 2).row(0, named=True)
    assert r2["structural_anomaly"] > r1["structural_anomaly"]


def test_uncertainty_concentration_fires_for_known_kinds() -> None:
    df = _df(
        [
            _row(cluster_id=1, top_anomaly_kind="overlapping_lei", n_anomalies=1),
            _row(cluster_id=2, top_anomaly_kind=""),
        ]
    )
    out = rank_by_attention(df)
    r1 = out.filter(pl.col("cluster_id") == 1).row(0, named=True)
    r2 = out.filter(pl.col("cluster_id") == 2).row(0, named=True)
    assert r1["uncertainty_concentration"] > r2["uncertainty_concentration"]
    assert "overlapping_lei" in UNCERTAINTY_ANOMALY_KINDS


def test_uncertainty_floor_when_no_registry_but_multi_source() -> None:
    df = _df([_row(n_sources=2, registry_anchor_density=0.0)])
    out = rank_by_attention(df)
    assert out["uncertainty_concentration"][0] > 0


def test_cross_source_convergence_grows_with_source_count() -> None:
    df = _df(
        [
            _row(cluster_id=1, n_sources=1),
            _row(cluster_id=2, n_sources=4),
        ]
    )
    out = rank_by_attention(df)
    r1 = out.filter(pl.col("cluster_id") == 1).row(0, named=True)
    r2 = out.filter(pl.col("cluster_id") == 2).row(0, named=True)
    assert r2["cross_source_convergence"] > r1["cross_source_convergence"]


def test_cross_source_convergence_sanctions_bonus() -> None:
    df = _df(
        [
            _row(cluster_id=1, n_sources=2, sanctions_proximity=0.0),
            _row(cluster_id=2, n_sources=2, sanctions_proximity=0.6),
        ]
    )
    out = rank_by_attention(df)
    r1 = out.filter(pl.col("cluster_id") == 1).row(0, named=True)
    r2 = out.filter(pl.col("cluster_id") == 2).row(0, named=True)
    assert r2["cross_source_convergence"] > r1["cross_source_convergence"]


def test_defensibility_join_when_provided() -> None:
    inv = _df([_row(cluster_id=1), _row(cluster_id=2)])
    defens = pl.DataFrame({"cluster_id": [1, 2], "score": [3.0, 1.5]})
    out = rank_by_attention(inv, defensibility_df=defens)
    assert "defensibility" in out.columns
    by_id = {r["cluster_id"]: r["defensibility"] for r in out.iter_rows(named=True)}
    assert by_id[1] == 3.0
    assert by_id[2] == 1.5


def test_kind_tag_uses_top_anomaly_kind() -> None:
    df = _df(
        [
            _row(cluster_id=1, top_anomaly_kind="hidden_hub"),
            _row(cluster_id=2, top_anomaly_kind=""),
        ]
    )
    out = rank_by_attention(df)
    by_id = {r["cluster_id"]: r["kind_tag"] for r in out.iter_rows(named=True)}
    assert by_id[1] == "hidden_hub"
    assert by_id[2] == "uncategorised"


def test_next_action_string_routes_on_top_anomaly() -> None:
    df = _df(
        [
            _row(cluster_id=1, top_anomaly_kind="shell_reuse_anomaly", top_address="Ugland House"),
            _row(cluster_id=2, top_anomaly_kind="hidden_hub"),
            _row(cluster_id=3, top_anomaly_kind="cross_border_mirror", jurisdictions="vg=1|ky=1"),
        ]
    )
    out = rank_by_attention(df)
    by_id = {r["cluster_id"]: r["next_action"] for r in out.iter_rows(named=True)}
    assert "Ugland House" in by_id[1]
    assert "hub" in by_id[2].lower()
    assert "mirror" in by_id[3].lower() or "jurisdiction" in by_id[3].lower()


def test_next_action_for_sanctions_when_no_top_anomaly() -> None:
    df = _df([_row(cluster_id=1, top_anomaly_kind="", sanctions_proximity=0.6)])
    out = rank_by_attention(df)
    assert "sanctions" in out["next_action"][0].lower()


def test_next_action_for_no_registry_anchor_multi_source() -> None:
    df = _df([_row(cluster_id=1, top_anomaly_kind="", n_sources=2, registry_anchor_density=0.0)])
    out = rank_by_attention(df)
    assert "registry" in out["next_action"][0].lower()


def test_rank_empty_input_returns_typed_empty_frame() -> None:
    out = rank_by_attention(pl.DataFrame())
    assert out.height == 0
    assert "attention_score" in out.columns
    assert "kind_tag" in out.columns


def test_select_diverse_queue_picks_one_per_kind() -> None:
    rows = []
    # 3 of the same kind followed by 1 of another.
    for cid, kind in zip(
        [1, 2, 3, 4],
        ["shell_reuse_anomaly", "shell_reuse_anomaly", "shell_reuse_anomaly", "hidden_hub"],
        strict=True,
    ):
        rows.append(_row(cluster_id=cid, top_anomaly_kind=kind, investigative_score=cid))
    df = _df(rows)
    ranked = rank_by_attention(df)
    queue = select_diverse_queue(ranked, top_n=3)
    # Top row is the highest-scoring shell_reuse_anomaly; the second row
    # must be the hidden_hub (different kind), not another shell_reuse.
    kinds = queue["kind_tag"].to_list()
    assert kinds[0] != kinds[1]
    # When the queue is asked for more than there are kinds, it fills with
    # remaining clusters from already-seen kinds.
    assert queue.height <= 3


def test_select_diverse_queue_empty_input() -> None:
    empty = rank_by_attention(pl.DataFrame())
    queue = select_diverse_queue(empty, top_n=5)
    assert queue.height == 0


def test_render_ranking_markdown_includes_headers_and_rows() -> None:
    df = _df(
        [
            _row(cluster_id=1, top_anomaly_kind="hidden_hub", n_anomalies=2),
            _row(cluster_id=2, top_anomaly_kind="cross_border_mirror"),
        ]
    )
    out = rank_by_attention(df)
    md = render_attention_ranking_markdown(out, top_n=10, dedupe_run_id="abc")
    assert "# Clusters ranked by investigator-attention" in md
    assert "from dedupe run `abc`" in md
    assert "| 1 |" in md
    assert "| 2 |" in md
    assert "kind | next action" in md


def test_render_next_actions_markdown_lists_one_per_section() -> None:
    df = _df(
        [
            _row(cluster_id=1, top_anomaly_kind="hidden_hub"),
            _row(cluster_id=2, top_anomaly_kind="shell_reuse_anomaly"),
        ]
    )
    ranked = rank_by_attention(df)
    queue = select_diverse_queue(ranked, top_n=2)
    md = render_next_actions_markdown(queue)
    assert "# Next-actions queue" in md
    assert "Cluster `1`" in md or "Cluster `2`" in md
    assert "Next action" in md


def test_attention_score_dataclass_has_evidence_field() -> None:
    a = AttentionScore(cluster_id=1, score=0.5)
    assert a.evidence == {}
    assert a.components == {}
