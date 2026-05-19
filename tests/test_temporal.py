"""Tests for the temporal-reconstruction module."""

from __future__ import annotations

from datetime import date

import polars as pl

from shellnet.investigations.cluster_explainer import (
    MemberAttr,
    OfficerRepeat,
)
from shellnet.investigations.temporal import (
    EVENT_KINDS,
    Timeline,
    TimelineEvent,
    _parse_date,
    build_timeline,
    render_timeline_markdown,
)


def _m(
    uid: str,
    name: str,
    *,
    inc: date | None = None,
    dis: date | None = None,
    jurisdiction: str | None = None,
) -> MemberAttr:
    return MemberAttr(
        entity_uid=uid,
        source="icij",
        name=name,
        normalized_name=name.lower(),
        jurisdiction=jurisdiction,
        company_number=None,
        lei=None,
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


def test_parse_date_handles_string_and_date_and_none() -> None:
    assert _parse_date(None) is None
    assert _parse_date("") is None
    assert _parse_date(date(2020, 1, 1)) == date(2020, 1, 1)
    assert _parse_date("2020-01-01") == date(2020, 1, 1)
    assert _parse_date("not a date") is None


def test_build_timeline_emits_incorporation_and_dissolution_events() -> None:
    members = [
        _m("icij:1", "A", inc=date(2010, 1, 1), dis=date(2018, 6, 30)),
        _m("icij:2", "B", inc=date(2012, 3, 15)),
    ]
    tl = build_timeline(members)
    kinds = [e.kind for e in tl.events]
    assert kinds.count("incorporation") == 2
    assert kinds.count("dissolution") == 1
    # Sorted by date.
    assert tl.events[0].date <= tl.events[-1].date
    assert tl.span_start == date(2010, 1, 1)
    assert tl.span_end == date(2018, 6, 30)


def test_build_timeline_emits_edge_start_and_end_events() -> None:
    members = [_m("icij:1", "A"), _m("icij:2", "B")]
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
                date(2012, 1, 1),
                date(2018, 6, 30),
                "Pandora Papers",
            ),
            (
                "icij:1",
                "icij:20000A",
                "registered_address",
                date(2010, 4, 1),
                None,
                "Panama Papers",
            ),
        ]
    )
    tl = build_timeline(members, edges_df=edges)
    kinds = [e.kind for e in tl.events]
    assert "officer_start" in kinds
    assert "officer_end" in kinds
    assert "address_start" in kinds
    # Leak labels propagate.
    assert any(e.source_label == "Panama Papers" for e in tl.events)


def test_build_timeline_computes_per_member_churn_counters() -> None:
    members = [_m("icij:1", "A")]
    edges = _edges_df(
        [
            ("icij:1", "icij:30000A", "officer_of", date(2010, 1, 1), date(2012, 1, 1), None),
            ("icij:1", "icij:30000B", "officer_of", date(2012, 2, 1), date(2014, 1, 1), None),
            ("icij:1", "icij:40000A", "intermediary_of", date(2010, 1, 1), None, None),
        ]
    )
    tl = build_timeline(members, edges_df=edges)
    lc = tl.lifecycles[0]
    # Two officer start_date events + two officer end_date events ⇒ 4 changes.
    assert lc.n_officer_changes == 4
    # One intermediary_start (no end_date).
    assert lc.n_intermediary_changes == 1
    assert lc.n_address_changes == 0


def test_build_timeline_computes_emergence_curve() -> None:
    members = [
        _m("icij:1", "A", inc=date(2010, 1, 1)),
        _m("icij:2", "B", inc=date(2012, 1, 1)),
        _m("icij:3", "C", inc=date(2012, 6, 1)),
    ]
    tl = build_timeline(members)
    assert tl.emergence_by_year[2010] == 1
    assert tl.emergence_by_year[2012] == 3
    assert max(tl.emergence_by_year.values()) == 3


def test_build_timeline_computes_reuse_windows_per_feature() -> None:
    members = [_m("icij:1", "A"), _m("icij:2", "B")]
    edges = _edges_df(
        [
            ("icij:1", "icij:30000A", "officer_of", date(2010, 1, 1), None, "Panama Papers"),
            ("icij:2", "icij:30000A", "officer_of", date(2012, 1, 1), None, "Pandora Papers"),
        ]
    )
    officer = OfficerRepeat(
        node="icij:30000A",
        name="John Doe",
        country=None,
        role=None,
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=2,
        leak_labels=["Panama Papers", "Pandora Papers"],
    )
    tl = build_timeline(members, edges_df=edges, officers=[officer])
    assert len(tl.reuse_windows) == 1
    w = tl.reuse_windows[0]
    assert w.feature_kind == "officer"
    assert w.feature_node == "icij:30000A"
    assert len(w.windows) == 2
    # Both members appear with their own start dates.
    starts = sorted(win["start"] for win in w.windows)
    assert starts == [date(2010, 1, 1), date(2012, 1, 1)]


def test_build_timeline_handles_empty_inputs() -> None:
    tl = build_timeline([])
    assert tl.events == []
    assert tl.lifecycles == []
    assert tl.reuse_windows == []
    assert tl.churn_rate == 0.0
    assert tl.span_start is None


def test_build_timeline_churn_rate_normalised_by_member_years() -> None:
    members = [_m("icij:1", "A", inc=date(2010, 1, 1), dis=date(2020, 1, 1))]  # ~10 years
    edges = _edges_df(
        [
            ("icij:1", "icij:30000A", "officer_of", date(2010, 1, 1), date(2015, 1, 1), None),
            ("icij:1", "icij:30000B", "officer_of", date(2015, 6, 1), date(2020, 1, 1), None),
        ]
    )
    tl = build_timeline(members, edges_df=edges)
    # 4 officer events / 10 member-years ≈ 0.4 changes/year.
    assert 0.3 <= tl.churn_rate <= 0.5


def test_render_timeline_markdown_includes_key_sections() -> None:
    members = [_m("icij:1", "A", inc=date(2010, 1, 1), dis=date(2018, 6, 30))]
    edges = _edges_df(
        [("icij:1", "icij:30000A", "officer_of", date(2011, 1, 1), None, "Panama Papers")]
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
    # Add a second member so the reuse window includes both.
    members.append(_m("icij:2", "B", inc=date(2012, 1, 1)))
    edges = pl.concat(
        [
            edges,
            _edges_df(
                [
                    (
                        "icij:2",
                        "icij:30000A",
                        "officer_of",
                        date(2012, 6, 1),
                        None,
                        "Pandora Papers",
                    )
                ]
            ),
        ]
    )
    officer.n_members_served = 2
    officer.member_uids = ["icij:1", "icij:2"]
    tl = build_timeline(members, edges_df=edges, officers=[officer])
    md = render_timeline_markdown(tl)
    assert "## Timeline / organizational behavior" in md
    assert "Member lifecycles" in md
    assert "Cluster emergence" in md
    assert "events" in md.lower()
    assert "Feature reuse over time" in md
    assert "Ownership churn per member" in md


def test_render_timeline_markdown_handles_empty() -> None:
    md = render_timeline_markdown(
        Timeline(
            events=[],
            lifecycles=[],
            reuse_windows=[],
            emergence_by_year={},
            churn_rate=0.0,
            span_start=None,
            span_end=None,
        )
    )
    assert "No date information" in md


def test_event_kinds_vocabulary_is_closed_set() -> None:
    """Sanity: detector kinds we emit must all be in EVENT_KINDS."""
    members = [_m("icij:1", "A", inc=date(2010, 1, 1), dis=date(2018, 1, 1))]
    edges = _edges_df(
        [
            (
                "icij:1",
                "icij:20000A",
                "registered_address",
                date(2010, 1, 1),
                date(2011, 1, 1),
                None,
            ),
            ("icij:1", "icij:30000A", "officer_of", date(2010, 1, 1), date(2011, 1, 1), None),
            ("icij:1", "icij:40000A", "intermediary_of", date(2010, 1, 1), date(2011, 1, 1), None),
        ]
    )
    tl = build_timeline(members, edges_df=edges)
    for ev in tl.events:
        assert ev.kind in EVENT_KINDS, ev.kind


def test_timeline_event_dataclass_carries_required_fields() -> None:
    ev = TimelineEvent(
        date=date(2020, 1, 1),
        kind="incorporation",
        member_uid="icij:1",
        other_node=None,
        label="x",
    )
    assert ev.source_label is None
    assert ev.kind == "incorporation"
