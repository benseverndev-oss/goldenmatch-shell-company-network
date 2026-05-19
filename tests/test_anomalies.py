"""Unit tests for cluster-level anomaly detectors.

Each detector is exercised in isolation with the smallest hand-crafted
inputs needed to make the rule fire (or not fire). Integration with the
broader ``build_explanation`` orchestrator is tested in
``test_cluster_explainer.py``.
"""

from __future__ import annotations

from datetime import date

import polars as pl

from shellnet.investigations.anomalies import (
    AnomalyFlag,
    detect_all,
    detect_contradictory_officers,
    detect_cross_border_mirror,
    detect_hidden_hub,
    detect_impossible_timeline,
    detect_no_registry_anchor,
    detect_overlapping_identities,
    detect_shell_reuse_anomaly,
    detect_status_contradiction,
    detect_structural_asymmetry,
)
from shellnet.investigations.cluster_explainer import (
    AddressRepeat,
    CentralityAnnotation,
    IntermediaryRepeat,
    MemberAttr,
    OfficerRepeat,
)


def _m(
    uid: str,
    *,
    source: str = "icij",
    name: str = "X",
    normalized_name: str | None = None,
    jurisdiction: str | None = None,
    company_number: str | None = None,
    lei: str | None = None,
    status: str | None = None,
    incorporation_date=None,
    dissolution_date=None,
) -> MemberAttr:
    return MemberAttr(
        entity_uid=uid,
        source=source,
        name=name,
        normalized_name=normalized_name or name.lower(),
        jurisdiction=jurisdiction,
        company_number=company_number,
        lei=lei,
        status=status,
        legal_form=None,
        address_raw=None,
        incorporation_date=incorporation_date,
        dissolution_date=dissolution_date,
    )


# ---------------------------------------------------------------------------
# Per-detector tests
# ---------------------------------------------------------------------------


def test_cross_border_mirror_fires_on_same_name_two_jurisdictions() -> None:
    flags = detect_cross_border_mirror(
        [
            _m("icij:a", name="ACME", normalized_name="acme", jurisdiction="vg"),
            _m("icij:b", name="ACME", normalized_name="acme", jurisdiction="ky"),
        ]
    )
    assert len(flags) == 1
    f = flags[0]
    assert f.kind == "cross_border_mirror"
    assert f.severity == "medium"
    assert set(f.evidence["jurisdictions"]) == {"vg", "ky"}


def test_cross_border_mirror_silent_when_single_jurisdiction() -> None:
    flags = detect_cross_border_mirror(
        [
            _m("icij:a", normalized_name="x", jurisdiction="vg"),
            _m("icij:b", normalized_name="x", jurisdiction="vg"),
        ]
    )
    assert flags == []


def test_status_contradiction_fires_on_mixed_active_dormant() -> None:
    flags = detect_status_contradiction(
        [
            _m("icij:a", status="Active"),
            _m("icij:b", status="Struck off"),
        ]
    )
    assert len(flags) == 1
    assert flags[0].kind == "status_contradiction"
    assert "icij:a" in flags[0].evidence["active"]
    assert "icij:b" in flags[0].evidence["dormant"]


def test_status_contradiction_silent_when_all_active() -> None:
    flags = detect_status_contradiction(
        [_m("icij:a", status="Active"), _m("icij:b", status="Active")]
    )
    assert flags == []


def test_hidden_hub_fires_when_nonmember_betweenness_dominates() -> None:
    cent = [
        CentralityAnnotation("icij:a", 0.0, 0.01, 1, 7, True),
        CentralityAnnotation("icij:b", 0.0, 0.02, 1, 7, True),
        CentralityAnnotation("icij:hub", 0.0, 0.50, 5, 7, False),
    ]
    flags = detect_hidden_hub(cent)
    assert len(flags) == 1
    assert flags[0].kind == "hidden_hub"
    assert flags[0].severity == "high"
    assert flags[0].evidence["non_member_uid"] == "icij:hub"


def test_hidden_hub_silent_when_no_nonmember_present() -> None:
    cent = [
        CentralityAnnotation("icij:a", 0.0, 0.1, 1, 7, True),
        CentralityAnnotation("icij:b", 0.0, 0.05, 1, 7, True),
    ]
    assert detect_hidden_hub(cent) == []


def test_no_registry_anchor_fires_for_multi_source_no_anchor() -> None:
    flags = detect_no_registry_anchor(
        [
            _m("icij:a", source="icij"),
            _m("os:b", source="opensanctions"),
        ]
    )
    assert len(flags) == 1
    assert flags[0].kind == "no_registry_anchor"
    assert flags[0].severity == "low"


def test_no_registry_anchor_silent_when_lei_present() -> None:
    flags = detect_no_registry_anchor(
        [
            _m("icij:a", source="icij"),
            _m("gleif:b", source="gleif", lei="GB123"),
        ]
    )
    assert flags == []


def test_overlapping_lei_fires_when_two_members_share_lei() -> None:
    flags = detect_overlapping_identities(
        [
            _m("icij:a", lei="GB12345"),
            _m("oc:b", lei="GB12345"),
        ]
    )
    assert any(f.kind == "overlapping_lei" for f in flags)
    f = next(f for f in flags if f.kind == "overlapping_lei")
    assert f.severity == "high"
    assert f.evidence["lei"] == "GB12345"


def test_overlapping_company_number_fires_when_two_members_share_cn() -> None:
    flags = detect_overlapping_identities(
        [
            _m("icij:a", company_number="111", jurisdiction="gb"),
            _m("oc:b", company_number="111", jurisdiction="gb"),
        ]
    )
    assert any(f.kind == "overlapping_company_number" for f in flags)


def test_contradictory_officer_fires_when_officer_serves_active_and_dormant() -> None:
    members = [
        _m("icij:a", status="Active"),
        _m("icij:b", status="Struck off"),
    ]
    officer = OfficerRepeat(
        node="icij:300",
        name="Mr Director",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:a", "icij:b"],
        n_global_edges=2,
        leak_labels=["Panama Papers"],
    )
    flags = detect_contradictory_officers(members, [officer])
    assert len(flags) == 1
    assert flags[0].kind == "contradictory_officer"
    assert "Mr Director" in flags[0].message


def test_shell_reuse_anomaly_fires_above_threshold() -> None:
    high_use_addr = AddressRepeat(
        node="icij:200",
        text="Ugland House",
        country="ky",
        n_members_served=2,
        member_uids=["icij:a", "icij:b"],
        n_global_edges=120,  # well above default threshold (25)
        leak_labels=["Paradise Papers"],
    )
    flags = detect_shell_reuse_anomaly([], [high_use_addr], [])
    assert len(flags) == 1
    assert flags[0].kind == "shell_reuse_anomaly"
    assert flags[0].severity == "high"  # >= 4× threshold
    assert flags[0].evidence["n_global_edges"] == 120


def test_shell_reuse_anomaly_silent_below_threshold() -> None:
    low_addr = AddressRepeat(
        node="icij:201",
        text="Small Office",
        country="vg",
        n_members_served=2,
        member_uids=["icij:a", "icij:b"],
        n_global_edges=2,
        leak_labels=[],
    )
    assert detect_shell_reuse_anomaly([], [low_addr], []) == []


def test_structural_asymmetry_fires_when_one_member_dominates() -> None:
    # Member 'a' has 12 incident edges; member 'b' has 0.
    edges = pl.DataFrame(
        {
            "src_node": ["icij:a"] * 12,
            "dst_node": [f"icij:30000{i:03d}" for i in range(12)],
            "kind_raw": ["officer_of"] * 12,
        }
    )
    members = [_m("icij:a"), _m("icij:b")]
    flags = detect_structural_asymmetry(members, edges, ratio_threshold=4)
    assert len(flags) == 1
    assert flags[0].kind == "structural_asymmetry"
    assert flags[0].evidence["incident_counts"]["icij:a"] == 12
    assert flags[0].evidence["incident_counts"]["icij:b"] == 0


def test_structural_asymmetry_silent_when_balanced() -> None:
    edges = pl.DataFrame(
        {
            "src_node": ["icij:a", "icij:b"],
            "dst_node": ["icij:c", "icij:d"],
            "kind_raw": ["officer_of", "officer_of"],
        }
    )
    flags = detect_structural_asymmetry([_m("icij:a"), _m("icij:b")], edges)
    assert flags == []


def test_impossible_timeline_fires_when_edge_starts_after_dissolution() -> None:
    member = _m(
        "icij:a",
        incorporation_date=date(2000, 1, 1),
        dissolution_date=date(2015, 12, 31),
    )
    edges = pl.DataFrame(
        {
            "src_node": ["icij:a"],
            "dst_node": ["icij:30000001"],
            "kind_raw": ["officer_of"],
            "start_date": [date(2020, 6, 1)],
            "end_date": [None],
        }
    )
    flags = detect_impossible_timeline([member], edges)
    assert len(flags) == 1
    assert flags[0].kind == "impossible_timeline"
    assert flags[0].severity == "high"
    assert flags[0].evidence["violations"]
    assert flags[0].evidence["violations"][0]["rule"] == "edge_starts_after_dissolution"


def test_impossible_timeline_fires_when_edge_starts_before_incorporation() -> None:
    member = _m("icij:a", incorporation_date=date(2010, 1, 1))
    edges = pl.DataFrame(
        {
            "src_node": ["icij:a"],
            "dst_node": ["icij:30000001"],
            "kind_raw": ["officer_of"],
            "start_date": [date(2000, 6, 1)],
            "end_date": [None],
        }
    )
    flags = detect_impossible_timeline([member], edges)
    assert len(flags) == 1
    assert flags[0].evidence["violations"][0]["rule"] == "edge_starts_before_incorporation"


def test_impossible_timeline_silent_when_dates_missing() -> None:
    member = _m("icij:a")  # no dates
    edges = pl.DataFrame(
        {
            "src_node": ["icij:a"],
            "dst_node": ["icij:30000001"],
            "kind_raw": ["officer_of"],
            "start_date": [date(2020, 1, 1)],
            "end_date": [None],
        }
    )
    assert detect_impossible_timeline([member], edges) == []


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def test_detect_all_returns_flags_sorted_by_severity() -> None:
    members = [
        _m("icij:a", source="icij", normalized_name="x", jurisdiction="vg", status="Active"),
        _m(
            "os:b",
            source="opensanctions",
            normalized_name="x",
            jurisdiction="ky",
            status="Struck off",
        ),
    ]
    high_use_addr = AddressRepeat(
        node="icij:200",
        text="Ugland House",
        country="ky",
        n_members_served=2,
        member_uids=["icij:a", "os:b"],
        n_global_edges=120,
        leak_labels=[],
    )
    cent = [
        CentralityAnnotation("icij:a", 0.0, 0.01, 1, 7, True),
        CentralityAnnotation("os:b", 0.0, 0.02, 1, 7, True),
        CentralityAnnotation("icij:hub", 0.0, 0.50, 5, 7, False),
    ]
    flags = detect_all(
        members,
        addresses=[high_use_addr],
        centrality=cent,
    )
    kinds = [f.kind for f in flags]
    # All three high-severity flags surface and come first in the list.
    assert "hidden_hub" in kinds
    assert "shell_reuse_anomaly" in kinds
    assert flags[0].severity == "high"
    sev_order = ["high", "medium", "low"]
    last_idx = -1
    for f in flags:
        idx = sev_order.index(f.severity)
        assert idx >= last_idx, f"severity order broken at {f.kind}"
        last_idx = idx


def test_detect_all_handles_empty_inputs_silently() -> None:
    assert detect_all([]) == []


def test_anomaly_flag_default_evidence_is_empty_dict() -> None:
    f = AnomalyFlag(kind="x", severity="low", message="m")
    assert f.evidence == {}
    assert f.member_uids == []


def test_intermediary_repeat_anomaly_uses_name_in_label() -> None:
    rep = IntermediaryRepeat(
        node="icij:400",
        name="Mossack & Co",
        country="pa",
        n_members_served=2,
        member_uids=["icij:a", "icij:b"],
        n_global_edges=200,
        leak_labels=["Panama Papers"],
    )
    flags = detect_shell_reuse_anomaly([rep], [], [])
    assert flags and "Mossack & Co" in flags[0].message
