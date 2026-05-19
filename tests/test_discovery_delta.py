"""Tests for the discovery delta module."""

from __future__ import annotations

from shellnet.investigations.cluster_explainer import (
    AddressRepeat,
    CentralityAnnotation,
    JurisdictionProfile,
    MemberAttr,
    OfficerRepeat,
    build_explanation,
    compute_jurisdiction_profile,
)
from shellnet.investigations.discovery_delta import (
    DeltaRow,
    DiscoveryDelta,
    build_discovery_delta,
    render_discovery_delta_markdown,
)


def _m(
    uid: str,
    *,
    source: str = "icij",
    name: str = "X",
    jurisdiction: str | None = None,
    lei: str | None = None,
    company_number: str | None = None,
    address_raw: str | None = None,
) -> MemberAttr:
    return MemberAttr(
        entity_uid=uid,
        source=source,
        name=name,
        normalized_name=name.lower(),
        jurisdiction=jurisdiction,
        company_number=company_number,
        lei=lei,
        status=None,
        legal_form=None,
        address_raw=address_raw,
    )


def test_build_delta_for_two_member_cross_border_cluster() -> None:
    members = [
        _m(
            "icij:1",
            name="ACME BVI",
            jurisdiction="vg",
            company_number="C-1",
            address_raw="123 Road Town",
        ),
        _m("icij:2", name="ACME KY", jurisdiction="ky"),
    ]
    jur = compute_jurisdiction_profile(members)
    delta = build_discovery_delta(
        members,
        jurisdictions=jur,
        intermediaries=[],
        addresses=[],
        officers=[],
        sanctions_anchors=[],
        centrality=[],
        sources_present=["icij"],
        leaks_present=["Panama Papers"],
    )
    # Anchor = member with company_number ("icij:1").
    assert delta.anchor_uid == "icij:1"
    cats = [r.category for r in delta.rows]
    # Every dimension is present.
    for required in [
        "Identity",
        "Jurisdictional footprint",
        "Officers / nominees",
        "Registered addresses",
        "Cross-source corroboration",
        "Risk adjacency",
        "Structural position",
    ]:
        assert required in cats
    # Cross-border row fires the multi-jurisdiction headline.
    jur_row = next(r for r in delta.rows if r.category == "Jurisdictional footprint")
    assert "multi-jurisdiction" in jur_row.delta_summary
    # Overall headline lists the additional context.
    assert "siblings" in delta.overall_summary or "sibling member" in delta.overall_summary
    assert "2-jurisdiction" in delta.overall_summary or "jurisdiction span" in delta.overall_summary


def test_delta_picks_registry_anchored_member_as_anchor() -> None:
    members = [
        _m("icij:1", name="Plain", jurisdiction="vg"),
        _m("gleif:2", name="WithLEI", jurisdiction="gb", lei="GB12345"),
    ]
    jur = compute_jurisdiction_profile(members)
    delta = build_discovery_delta(
        members,
        jurisdictions=jur,
        intermediaries=[],
        addresses=[],
        officers=[],
        sanctions_anchors=[],
        centrality=[],
        sources_present=["icij", "gleif"],
        leaks_present=[],
    )
    assert delta.anchor_uid == "gleif:2"
    # Cross-source corroboration row picks up the 2-source signal.
    cross = next(r for r in delta.rows if r.category == "Cross-source corroboration")
    assert "2-source corroboration" in cross.delta_summary


def test_delta_surfaces_shared_officer_and_address_in_view() -> None:
    members = [
        _m("icij:1", name="A", jurisdiction="vg"),
        _m("icij:2", name="B", jurisdiction="ky"),
    ]
    jur = compute_jurisdiction_profile(members)
    officer = OfficerRepeat(
        node="icij:300",
        name="John Q. Public",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=15,
        leak_labels=[],
    )
    address = AddressRepeat(
        node="icij:200",
        text="Ugland House",
        country="ky",
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=500,
        leak_labels=[],
    )
    delta = build_discovery_delta(
        members,
        jurisdictions=jur,
        intermediaries=[],
        addresses=[address],
        officers=[officer],
        sanctions_anchors=[],
        centrality=[],
        sources_present=["icij"],
        leaks_present=[],
    )
    off_row = next(r for r in delta.rows if r.category == "Officers / nominees")
    addr_row = next(r for r in delta.rows if r.category == "Registered addresses")
    assert "John Q. Public" in off_row.goldenmatch_view
    assert "Ugland House" in addr_row.goldenmatch_view
    assert "shared by 2 cluster members" in addr_row.goldenmatch_view


def test_delta_surfaces_sanctions_when_present() -> None:
    members = [_m("icij:1", name="A", jurisdiction="vg")]
    jur = compute_jurisdiction_profile(members)
    delta = build_discovery_delta(
        members,
        jurisdictions=jur,
        intermediaries=[],
        addresses=[],
        officers=[],
        sanctions_anchors=[
            {
                "target_entity_uid": "icij:1",
                "ref_entity_uid": "ofac:1",
                "ref_name": "Sanctioned Co",
                "score": 0.92,
            }
        ],
        centrality=[],
        sources_present=["icij"],
        leaks_present=[],
    )
    risk = next(r for r in delta.rows if r.category == "Risk adjacency")
    assert "list-match anchor" in risk.goldenmatch_view
    assert "sanctions adjacency" in risk.delta_summary


def test_delta_includes_centrality_position_when_available() -> None:
    members = [_m("icij:1", name="A", jurisdiction="vg"), _m("icij:2", name="B", jurisdiction="vg")]
    jur = compute_jurisdiction_profile(members)
    cent = [
        CentralityAnnotation("icij:1", 0.3, 0.05, 4, 7, True),
        CentralityAnnotation("icij:2", 0.1, 0.01, 2, 7, True),
        CentralityAnnotation("icij:hub", 0.0, 0.40, 5, 7, False),
    ]
    delta = build_discovery_delta(
        members,
        jurisdictions=jur,
        intermediaries=[],
        addresses=[],
        officers=[],
        sanctions_anchors=[],
        centrality=cent,
        sources_present=["icij"],
        leaks_present=[],
    )
    struct = next(r for r in delta.rows if r.category == "Structural position")
    assert "betweenness" in struct.goldenmatch_view
    assert "hidden hub" in struct.goldenmatch_view
    assert "rank" in struct.goldenmatch_view


def test_delta_handles_empty_members_gracefully() -> None:
    jur = JurisdictionProfile(
        counts={}, secrecy_jurisdictions=[], is_cross_border=False, n_unknown=0
    )
    delta = build_discovery_delta(
        [],
        jurisdictions=jur,
        intermediaries=[],
        addresses=[],
        officers=[],
        sanctions_anchors=[],
        centrality=[],
        sources_present=[],
        leaks_present=[],
    )
    assert delta.rows == []
    assert delta.anchor_uid == ""


def test_render_markdown_produces_table_header_and_row_per_dimension() -> None:
    members = [
        _m("icij:1", name="A", jurisdiction="vg"),
        _m("icij:2", name="B", jurisdiction="ky"),
    ]
    jur = compute_jurisdiction_profile(members)
    delta = build_discovery_delta(
        members,
        jurisdictions=jur,
        intermediaries=[],
        addresses=[],
        officers=[],
        sanctions_anchors=[],
        centrality=[],
        sources_present=["icij"],
        leaks_present=[],
    )
    md = render_discovery_delta_markdown(delta)
    assert "## Discovery delta" in md
    assert "| Dimension | Standard search | GoldenMatch surfaced | Delta |" in md
    for cat in ("Identity", "Jurisdictional footprint", "Risk adjacency"):
        assert f"**{cat}**" in md


def test_render_markdown_no_rows_renders_unavailable_message() -> None:
    md = render_discovery_delta_markdown(
        DiscoveryDelta(anchor_uid="", anchor_name="", anchor_jurisdiction=None)
    )
    assert "Discovery delta" in md
    assert "unavailable" in md


def test_build_explanation_attaches_delta() -> None:
    """Integration: build_explanation now populates the delta automatically."""
    import polars as pl

    company_df = pl.DataFrame(
        {
            "entity_uid": ["icij:1", "icij:2"],
            "source": ["icij", "icij"],
            "name": ["A", "B"],
            "normalized_name": ["a", "b"],
            "jurisdiction": ["vg", "ky"],
            "company_number": [None, None],
            "lei": [None, None],
            "status": [None, None],
            "legal_form": [None, None],
            "address_raw": [None, None],
        }
    )
    expl = build_explanation(1, ["icij:1", "icij:2"], company_df=company_df, edges_df=None)
    assert expl.discovery_delta is not None
    assert expl.discovery_delta.rows
    assert isinstance(expl.discovery_delta.rows[0], DeltaRow)
