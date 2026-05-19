"""Tests for subcluster extraction."""

from __future__ import annotations

import polars as pl

from shellnet.investigations.cluster_explainer import (
    AddressRepeat,
    CentralityAnnotation,
    IntermediaryRepeat,
    OfficerRepeat,
)
from shellnet.investigations.subcluster import (
    Subcluster,
    _extract_bridge_neighborhoods,
    _extract_communities,
    _extract_high_centrality_core,
    _extract_rare_intermediary_groups,
    _extract_shell_reuse_groups,
    extract_subclusters,
    render_subcluster_index_markdown,
)


def _edges_df(rows: list[tuple[str, str, str]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "src_node": [r[0] for r in rows],
            "dst_node": [r[1] for r in rows],
            "kind_raw": [r[2] for r in rows],
        }
    )


def test_subcluster_dataclass_size_property() -> None:
    s = Subcluster(
        subcluster_id="x",
        kind="community",
        member_uids=["icij:1", "icij:2", "icij:3"],
    )
    assert s.size == 3


def test_extract_communities_returns_empty_without_edges() -> None:
    assert _extract_communities(["icij:1", "icij:2"], None) == []
    assert _extract_communities(["icij:1", "icij:2"], _edges_df([])) == []


def test_extract_communities_groups_dense_neighborhood() -> None:
    """Six members, two officer-anchored cliques. Louvain should split
    them into two communities."""
    members = [f"icij:{i}" for i in range(1, 7)]
    edges = _edges_df(
        [
            # Officer A wires members 1, 2, 3.
            ("icij:30000A", "icij:1", "officer_of"),
            ("icij:30000A", "icij:2", "officer_of"),
            ("icij:30000A", "icij:3", "officer_of"),
            # Officer B wires members 4, 5, 6.
            ("icij:30000B", "icij:4", "officer_of"),
            ("icij:30000B", "icij:5", "officer_of"),
            ("icij:30000B", "icij:6", "officer_of"),
        ]
    )
    subs = _extract_communities(members, edges)
    # Two communities of 3 each. min_community_size=3 keeps both.
    assert len(subs) == 2
    for s in subs:
        assert s.size == 3
        assert s.kind == "community"
        assert all(uid in members for uid in s.member_uids)


def test_extract_communities_drops_singletons_below_min_size() -> None:
    members = [f"icij:{i}" for i in range(1, 5)]
    # No shared structure → Louvain returns mostly singletons.
    edges = _edges_df([("icij:1", "icij:30001", "officer_of")])
    subs = _extract_communities(members, edges)
    # Below MIN_COMMUNITY_SIZE, nothing emitted.
    assert all(s.size >= 3 for s in subs)


def test_extract_bridges_finds_critical_edge() -> None:
    members = ["icij:1", "icij:2", "icij:3", "icij:4"]
    # Two triangles joined by a single bridge member-pair (icij:2 — icij:3).
    edges = _edges_df(
        [
            ("icij:1", "icij:2", "officer_of"),
            ("icij:1", "icij:3000A", "officer_of"),
            ("icij:2", "icij:3000A", "officer_of"),
            ("icij:2", "icij:3", "officer_of"),  # bridge
            ("icij:3", "icij:4", "officer_of"),
            ("icij:3", "icij:3000B", "officer_of"),
            ("icij:4", "icij:3000B", "officer_of"),
        ]
    )
    subs = _extract_bridge_neighborhoods(members, edges)
    assert subs
    assert all(s.kind == "bridge_neighborhood" for s in subs)
    # The (2, 3) bridge is the one we expect.
    found = any(
        ("icij:2" in s.evidence["bridge_edge"]) and ("icij:3" in s.evidence["bridge_edge"])
        for s in subs
    )
    assert found


def test_extract_rare_intermediary_groups_picks_low_global_degree() -> None:
    rare = IntermediaryRepeat(
        node="icij:400A",
        name="BoutiqueAgent",
        country="bm",
        n_members_served=3,
        member_uids=["icij:1", "icij:2", "icij:3"],
        n_global_edges=3,  # below default threshold (10)
        leak_labels=["Pandora Papers"],
    )
    common = IntermediaryRepeat(
        node="icij:400B",
        name="MossackFonseca",
        country="pa",
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=5000,  # well above threshold
        leak_labels=["Panama Papers"],
    )
    subs = _extract_rare_intermediary_groups([rare, common])
    # Only the rare one yields a subcluster.
    assert len(subs) == 1
    assert subs[0].member_uids == ["icij:1", "icij:2", "icij:3"]
    assert subs[0].kind == "rare_intermediary_group"
    assert "BoutiqueAgent" in subs[0].narrative


def test_extract_high_centrality_core_returns_top_k_members() -> None:
    cent = [
        CentralityAnnotation("icij:1", 0.0, 0.50, 1, 7, True),
        CentralityAnnotation("icij:2", 0.0, 0.30, 1, 7, True),
        CentralityAnnotation("icij:3", 0.0, 0.20, 1, 7, True),
        CentralityAnnotation("icij:4", 0.0, 0.10, 1, 7, True),
        CentralityAnnotation("icij:hub", 0.0, 0.60, 5, 7, False),  # non-member
    ]
    subs = _extract_high_centrality_core(cent, top_k=3)
    assert len(subs) == 1
    s = subs[0]
    assert s.kind == "high_centrality_core"
    assert s.member_uids == ["icij:1", "icij:2", "icij:3"]
    assert s.evidence["anchor"] == "icij:1"


def test_extract_high_centrality_core_silent_when_all_zero() -> None:
    cent = [
        CentralityAnnotation("icij:1", 0.0, 0.0, 1, 7, True),
        CentralityAnnotation("icij:2", 0.0, 0.0, 1, 7, True),
    ]
    assert _extract_high_centrality_core(cent) == []


def test_extract_shell_reuse_groups_picks_high_global_degree() -> None:
    addr = AddressRepeat(
        node="icij:200",
        text="Ugland House",
        country="ky",
        n_members_served=4,
        member_uids=["icij:1", "icij:2", "icij:3", "icij:4"],
        n_global_edges=200,  # well above threshold
        leak_labels=[],
    )
    subs = _extract_shell_reuse_groups([], [addr], [])
    assert len(subs) == 1
    assert subs[0].kind == "shell_reuse_group"
    assert "Ugland House" in subs[0].seed_label


def test_extract_subclusters_orchestrator_dedupes_by_member_set() -> None:
    """If two extractors produce subclusters with identical member sets,
    only the higher-scoring one survives."""
    members = ["icij:1", "icij:2", "icij:3"]
    edges = _edges_df(
        [
            ("icij:30001", "icij:1", "officer_of"),
            ("icij:30001", "icij:2", "officer_of"),
            ("icij:30001", "icij:3", "officer_of"),
        ]
    )
    # A rare intermediary covers all three; community detection should
    # also produce the same group of three.
    rare = IntermediaryRepeat(
        node="icij:30001",
        name="X",
        country=None,
        n_members_served=3,
        member_uids=["icij:1", "icij:2", "icij:3"],
        n_global_edges=3,
        leak_labels=[],
    )
    subs = extract_subclusters(
        1,
        members,
        edges_df=edges,
        intermediaries=[rare],
    )
    # Both extractors propose the same set; dedup keeps the higher
    # interest_score (rare_intermediary_group=1.5 > community=1.0).
    member_sets = [frozenset(s.member_uids) for s in subs]
    assert len(member_sets) == len(set(member_sets))
    kept = next(s for s in subs if frozenset(s.member_uids) == frozenset(members))
    assert kept.kind == "rare_intermediary_group"


def test_extract_subclusters_handles_no_inputs_safely() -> None:
    assert extract_subclusters(1, [], edges_df=None) == []


def test_extract_subclusters_respects_max_cap() -> None:
    """When more candidates exist than the cap, the highest-scored
    ones are kept."""
    members = ["icij:1", "icij:2", "icij:3", "icij:4"]
    edges = _edges_df(
        [
            ("icij:30001", "icij:1", "officer_of"),
            ("icij:30001", "icij:2", "officer_of"),
            ("icij:30002", "icij:3", "officer_of"),
            ("icij:30002", "icij:4", "officer_of"),
        ]
    )
    subs = extract_subclusters(1, members, edges_df=edges, max_subclusters=1)
    assert len(subs) == 1


def test_render_index_includes_kind_summary_and_rows() -> None:
    # Renderer preserves the order it's given; the orchestrator already
    # sorts by interest_score desc, so pass them in that order here.
    subs = [
        Subcluster(
            subcluster_id="bridge_a__b",
            kind="bridge_neighborhood",
            member_uids=["icij:4", "icij:5"],
            narrative="B",
            interest_score=1.0,
        ),
        Subcluster(
            subcluster_id="comm_0",
            kind="community",
            member_uids=["icij:1", "icij:2", "icij:3"],
            narrative="N",
            interest_score=0.7,
        ),
    ]
    md = render_subcluster_index_markdown(42, subs, dedupe_run_id="abc")
    assert "Cluster 42 — subcluster index" in md
    assert "From dedupe run `abc`" in md
    assert "bridge_neighborhood (1)" in md
    assert "community (1)" in md
    assert "| 1 | `bridge_a__b` | bridge_neighborhood |" in md
    assert "| 2 | `comm_0` |" in md


def test_render_index_empty_message() -> None:
    md = render_subcluster_index_markdown(42, [])
    assert "No subclusters extracted" in md


def test_extract_shell_reuse_uses_officer_name_in_label() -> None:
    officer = OfficerRepeat(
        node="icij:301",
        name="Nominee Director Inc",
        country="gb",
        role=None,
        n_members_served=3,
        member_uids=["icij:1", "icij:2", "icij:3"],
        n_global_edges=500,
        leak_labels=[],
    )
    subs = _extract_shell_reuse_groups([], [], [officer])
    assert len(subs) == 1
    assert "Nominee Director Inc" in subs[0].seed_label
