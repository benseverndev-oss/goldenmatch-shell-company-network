"""Tests for the interactive graph replay module."""

from __future__ import annotations

import json
from datetime import date

import polars as pl

from shellnet.investigations.cluster_explainer import MemberAttr, OfficerRepeat
from shellnet.investigations.graph_replay import (
    ReplayFrame,
    ReplaySequence,
    build_replay,
    render_replay_json,
    render_replay_markdown,
    write_replay_png_frames,
)
from shellnet.investigations.temporal import Timeline, build_timeline


def _m(
    uid: str,
    name: str,
    *,
    inc: date | None = None,
    dis: date | None = None,
    lei: str | None = None,
    source: str = "icij",
) -> MemberAttr:
    return MemberAttr(
        entity_uid=uid,
        source=source,
        name=name,
        normalized_name=name.lower(),
        jurisdiction=None,
        company_number=None,
        lei=lei,
        status=None,
        legal_form=None,
        address_raw=None,
        incorporation_date=inc,
        dissolution_date=dis,
    )


def _edges_df(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "src_node": [r[0] for r in rows],
            "dst_node": [r[1] for r in rows],
            "kind_raw": [r[2] for r in rows],
            "start_date": [r[3] for r in rows],
            "end_date": [r[4] for r in rows],
            "source_label": [r[5] if len(r) > 5 else None for r in rows],
        }
    )


def test_build_replay_returns_empty_for_no_timeline() -> None:
    tl = Timeline(
        events=[],
        lifecycles=[],
        reuse_windows=[],
        emergence_by_year={},
        churn_rate=0.0,
        span_start=None,
        span_end=None,
    )
    rep = build_replay(tl, [], cluster_id=1)
    assert rep.frames == []
    assert "no temporal data" in rep.summary


def test_build_replay_produces_requested_frame_count_with_dense_events() -> None:
    members = [
        _m("icij:1", "A", inc=date(2010, 1, 1)),
        _m("icij:2", "B", inc=date(2012, 1, 1)),
        _m("icij:3", "C", inc=date(2014, 1, 1)),
        _m("icij:4", "D", inc=date(2016, 1, 1), dis=date(2020, 6, 30)),
    ]
    tl = build_timeline(members)
    rep = build_replay(tl, members, cluster_id=1, n_frames=5)
    assert len(rep.frames) >= 1
    assert len(rep.frames) <= 5
    # Each frame's bucket_end must be monotonic.
    bes = [f.bucket_end for f in rep.frames]
    assert bes == sorted(bes)


def test_replay_frames_accumulate_nodes_and_edges() -> None:
    members = [
        _m("icij:1", "A", inc=date(2010, 1, 1)),
        _m("icij:2", "B", inc=date(2014, 1, 1)),
    ]
    edges = _edges_df(
        [
            (
                "icij:1",
                "icij:30000A",
                "officer_of",
                date(2010, 4, 1),
                None,
                "Panama Papers",
            ),
            (
                "icij:2",
                "icij:30000A",
                "officer_of",
                date(2014, 4, 1),
                None,
                "Pandora Papers",
            ),
        ]
    )
    tl = build_timeline(members, edges_df=edges)
    rep = build_replay(tl, members, cluster_id=1, n_frames=4)
    # By the last frame, both members and both edges have arrived.
    last = rep.frames[-1]
    assert "icij:1" in last.cumulative_nodes
    assert "icij:2" in last.cumulative_nodes
    assert "icij:30000A" in last.cumulative_nodes
    assert len(last.cumulative_edges) >= 2
    # Node and edge counts are monotonically non-decreasing across frames.
    for a, b in zip(rep.frames[:-1], rep.frames[1:], strict=True):
        assert len(b.cumulative_nodes) >= len(a.cumulative_nodes)
        assert len(b.cumulative_edges) >= len(a.cumulative_edges)


def test_uncertainty_falls_as_anchored_members_appear() -> None:
    members = [
        _m("icij:1", "A", inc=date(2010, 1, 1)),  # no anchor
        _m("gleif:2", "B", inc=date(2014, 1, 1), lei="GB12345", source="gleif"),
    ]
    tl = build_timeline(members)
    rep = build_replay(tl, members, cluster_id=1, n_frames=4)
    # First frame: only icij:1 has been incorporated; the gleif member with
    # the LEI hasn't appeared yet → high uncertainty.
    # Last frame: both present → lower uncertainty.
    assert rep.frames[-1].cumulative_uncertainty <= rep.frames[0].cumulative_uncertainty


def test_uncertainty_in_unit_interval() -> None:
    members = [_m("icij:1", "A", inc=date(2010, 1, 1))]
    tl = build_timeline(members)
    rep = build_replay(tl, members, cluster_id=1, n_frames=3)
    for f in rep.frames:
        assert 0.0 <= f.cumulative_uncertainty <= 1.0


def test_new_events_contain_per_period_event_payload() -> None:
    members = [
        _m("icij:1", "A", inc=date(2010, 1, 1)),
        _m("icij:2", "B", inc=date(2015, 1, 1)),
    ]
    tl = build_timeline(members)
    rep = build_replay(tl, members, cluster_id=1, n_frames=2)
    # First frame must have at least one new event (icij:1 incorporation);
    # the union of new_events across all frames must equal all timeline events.
    flat = [ev for f in rep.frames for ev in f.new_events]
    assert len(flat) == len(tl.events)
    # Every dict carries the keys the renderer expects.
    for ev in flat:
        assert set(["date", "kind", "member_uid", "other_node", "source_label"]) <= set(ev.keys())


def test_n_registry_anchors_present_climbs_when_anchored_member_appears() -> None:
    members = [
        _m("icij:1", "A", inc=date(2010, 1, 1)),
        _m("gleif:2", "B", inc=date(2015, 1, 1), lei="GB12345", source="gleif"),
    ]
    tl = build_timeline(members)
    rep = build_replay(tl, members, cluster_id=1, n_frames=2)
    first = rep.frames[0]
    last = rep.frames[-1]
    assert last.n_registry_anchors_present >= first.n_registry_anchors_present
    assert last.n_registry_anchors_present == 1


def test_render_markdown_includes_uncertainty_curve_and_frame_sections() -> None:
    members = [
        _m("icij:1", "A", inc=date(2010, 1, 1)),
        _m("icij:2", "B", inc=date(2015, 1, 1)),
    ]
    edges = _edges_df(
        [
            ("icij:1", "icij:30000A", "officer_of", date(2010, 4, 1), None, "Panama Papers"),
        ]
    )
    officer = OfficerRepeat(
        node="icij:30000A",
        name="Director",
        country=None,
        role=None,
        n_members_served=1,
        member_uids=["icij:1"],
        n_global_edges=1,
        leak_labels=["Panama Papers"],
    )
    tl = build_timeline(members, edges_df=edges, officers=[officer])
    rep = build_replay(tl, members, cluster_id=42, n_frames=3)
    md = render_replay_markdown(rep)
    assert "# Graph replay — cluster 42" in md
    assert "## Uncertainty curve" in md
    assert "## Frames" in md
    assert "Frame 0" in md
    assert "Panama Papers" in md


def test_render_markdown_handles_empty_replay() -> None:
    rep = ReplaySequence(cluster_id=1, frames=[], members=[], summary="empty")
    md = render_replay_markdown(rep)
    assert "No temporal data" in md


def test_render_json_round_trips_with_frame_payload() -> None:
    members = [_m("icij:1", "A", inc=date(2010, 1, 1))]
    tl = build_timeline(members)
    rep = build_replay(tl, members, cluster_id=7, n_frames=2)
    raw = render_replay_json(rep)
    obj = json.loads(raw)
    assert obj["cluster_id"] == 7
    assert isinstance(obj["frames"], list)
    assert obj["frames"][0]["frame_idx"] == 0


def test_replay_frame_dataclass_default_uncertainty() -> None:
    f = ReplayFrame(frame_idx=0, bucket_end=date(2020, 1, 1))
    assert f.cumulative_uncertainty == 1.0
    assert f.cumulative_nodes == []
    assert f.cumulative_edges == []


def test_write_png_frames_silently_degrades_without_matplotlib(tmp_path) -> None:
    """If matplotlib isn't importable, ``write_replay_png_frames`` must
    return ``[]`` instead of raising — the rest of the pipeline stays
    intact on headless environments."""
    import importlib

    # Try a real call; if matplotlib *is* installed we just confirm
    # it returns a non-empty list of png paths.
    members = [_m("icij:1", "A", inc=date(2010, 1, 1))]
    tl = build_timeline(members)
    rep = build_replay(tl, members, cluster_id=1, n_frames=2)
    out = write_replay_png_frames(rep, tmp_path)
    # Either: matplotlib is missing ⇒ no files; or installed ⇒ paths exist.
    if out:
        assert all(p.exists() for p in out)
    try:
        importlib.import_module("matplotlib")
        # If matplotlib is here, at least one frame should have rendered.
        assert out
    except ImportError:
        assert out == []
