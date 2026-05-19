"""Tests for the extended narrative-path generator."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from shellnet.investigations.cluster_explainer import (
    CentralityAnnotation,
    MemberAttr,
    NarrativePath,
    OfficerRepeat,
    PathStep,
)
from shellnet.investigations.narrative_paths import find_paths
from shellnet.matching.company_features import build_unified_table
from shellnet.sources import gleif, icij, opencorporates, opensanctions


def _m(
    uid: str,
    *,
    source: str = "icij",
    name: str = "X",
    jurisdiction: str | None = None,
    lei: str | None = None,
    company_number: str | None = None,
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
        address_raw=None,
    )


def test_path_step_dataclass_carries_label_and_kind() -> None:
    s = PathStep(kind="member", node="icij:1", label="A")
    assert s.kind == "member"
    assert s.label == "A"
    assert s.extra == {}


def test_narrative_path_dataclass_default_score_zero() -> None:
    p = NarrativePath(
        anchor_uid="icij:1",
        summary="…",
        steps=[PathStep(kind="member", node="icij:1", label="A")],
        terminus_kind="sibling",
    )
    assert p.score == 0.0


def test_find_paths_returns_empty_for_no_members() -> None:
    assert (
        find_paths(
            [], intermediaries=[], addresses=[], officers=[], sanctions_anchors=[], centrality=[]
        )
        == []
    )


def test_find_paths_returns_empty_when_no_shared_feature() -> None:
    members = [_m("icij:1", name="A"), _m("icij:2", name="B")]
    # No intermediaries/addresses/officers → no path can be built.
    assert (
        find_paths(
            members,
            intermediaries=[],
            addresses=[],
            officers=[],
            sanctions_anchors=[],
            centrality=[],
        )
        == []
    )


def test_find_paths_builds_basic_chain_via_shared_officer() -> None:
    members = [
        _m("icij:1", name="ACME BVI", jurisdiction="vg"),
        _m("icij:2", name="ACME KY", jurisdiction="ky"),
    ]
    officer = OfficerRepeat(
        node="icij:300",
        name="John Doe",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=2,
        leak_labels=["Panama Papers"],
    )
    paths = find_paths(
        members,
        intermediaries=[],
        addresses=[],
        officers=[officer],
        sanctions_anchors=[],
        centrality=[],
    )
    assert len(paths) == 1
    p = paths[0]
    # member → officer → sibling member
    kinds = [s.kind for s in p.steps]
    assert kinds[:3] == ["member", "officer", "member"]
    assert p.terminus_kind == "sibling"
    assert "John Doe" in " ".join(s.label for s in p.steps)


def test_find_paths_attaches_sanctions_terminus_when_anchor_provided() -> None:
    members = [
        _m("icij:1", name="ACME BVI", jurisdiction="vg"),
        _m("icij:2", name="ACME KY", jurisdiction="ky"),
    ]
    officer = OfficerRepeat(
        node="icij:300",
        name="John Doe",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=2,
        leak_labels=[],
    )
    sanctions = [
        {
            "target_entity_uid": "icij:999",  # unrelated to siblings
            "ref_entity_uid": "ofac:SDN-1",
            "ref_name": "Sanctioned Corp",
            "ref_lei": None,
            "score": 0.92,
        }
    ]
    paths = find_paths(
        members,
        intermediaries=[],
        addresses=[],
        officers=[officer],
        sanctions_anchors=sanctions,
        centrality=[],
    )
    assert paths
    # Cluster-level fallback: the last step is the sanctions anchor.
    p = paths[0]
    assert p.terminus_kind == "sanctions"
    assert p.steps[-1].kind == "anchor"
    assert "Sanctioned Corp" in p.steps[-1].label


def test_find_paths_attaches_registry_terminus_when_sibling_has_lei() -> None:
    members = [
        _m("icij:1", name="ACME BVI", jurisdiction="vg"),
        # Sibling carries an LEI ⇒ it's itself a registry-anchor terminus.
        _m("gleif:2", name="ACME LEI", jurisdiction="gb", lei="GB12345", source="gleif"),
    ]
    officer = OfficerRepeat(
        node="icij:300",
        name="John Doe",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:1", "gleif:2"],
        n_global_edges=2,
        leak_labels=[],
    )
    paths = find_paths(
        members,
        intermediaries=[],
        addresses=[],
        officers=[officer],
        sanctions_anchors=[],
        centrality=[],
    )
    assert paths
    p = paths[0]
    assert p.terminus_kind == "registry_anchor"
    assert p.steps[-1].kind == "anchor"
    assert "GB12345" in p.steps[-1].label


def test_find_paths_attaches_hidden_hub_terminus_as_last_resort() -> None:
    members = [
        _m("icij:1", name="ACME BVI", jurisdiction="vg"),
        _m("icij:2", name="ACME KY", jurisdiction="ky"),
    ]
    officer = OfficerRepeat(
        node="icij:300",
        name="John Doe",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=2,
        leak_labels=[],
    )
    cent = [
        CentralityAnnotation("icij:1", 0.0, 0.01, 1, 7, True),
        CentralityAnnotation("icij:2", 0.0, 0.01, 1, 7, True),
        CentralityAnnotation("icij:hub", 0.0, 0.40, 5, 7, False),
    ]
    paths = find_paths(
        members,
        intermediaries=[],
        addresses=[],
        officers=[officer],
        sanctions_anchors=[],
        centrality=cent,
    )
    assert paths
    p = paths[0]
    assert p.terminus_kind == "hidden_hub"
    assert "icij:hub" in p.steps[-1].label


def test_find_paths_sorts_by_score_descending() -> None:
    # Build two anchor candidates; the one whose sibling has an LEI should
    # outrank the bare cross-jurisdiction one.
    members = [
        _m("icij:1", name="A1", jurisdiction="vg"),
        _m("icij:2", name="A2", jurisdiction="ky"),
        _m("icij:3", name="B1", jurisdiction="vg"),
        _m("gleif:4", name="B2 LEI", jurisdiction="gb", lei="GB123", source="gleif"),
    ]
    officer_low = OfficerRepeat(
        node="icij:300",
        name="Low Officer",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=2,
        leak_labels=[],
    )
    officer_high = OfficerRepeat(
        node="icij:301",
        name="High Officer",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:3", "gleif:4"],
        n_global_edges=2,
        leak_labels=[],
    )
    paths = find_paths(
        members,
        intermediaries=[],
        addresses=[],
        officers=[officer_low, officer_high],
        sanctions_anchors=[],
        centrality=[],
        max_paths=3,
    )
    # Top path must include the LEI terminus.
    assert paths
    assert paths[0].terminus_kind == "registry_anchor"


# ---------------------------------------------------------------------------
# Integration against the staged ICIJ fixture
# ---------------------------------------------------------------------------


def _stage(tmp_path: Path, fixtures_dir: Path) -> tuple[Path, Path]:
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


def test_find_paths_walks_one_hop_past_sibling_using_fixture_edges(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    """When edges_df is provided, the walker takes one hop past the sibling
    looking for a richer terminus — e.g. a registered address."""
    interim, processed = _stage(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")

    # Build a minimal cluster with the shared-officer signal from the fixture.
    members = [
        _m("icij:10000001", name="ACME BVI", jurisdiction="vg"),
        _m("icij:10000002", name="ACME KY", jurisdiction="ky"),
    ]
    officer = OfficerRepeat(
        node="icij:30000001",
        name="John Q. Public",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:10000001", "icij:10000002"],
        n_global_edges=2,
        leak_labels=["Panama Papers", "Pandora Papers"],
    )
    paths = find_paths(
        members,
        intermediaries=[],
        addresses=[],
        officers=[officer],
        sanctions_anchors=[],
        centrality=[],
        edges_df=edges_df,
        company_df=company_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        max_hops=5,
    )
    assert paths
    p = paths[0]
    # The sibling ACME KY has a registered_address edge in the fixture, so
    # the walker extends one step past the sibling into that address.
    step_kinds = [s.kind for s in p.steps]
    assert "address" in step_kinds or len(step_kinds) >= 4


def test_find_paths_respects_max_paths_cap() -> None:
    members = [
        _m("icij:1", name="A1", jurisdiction="vg"),
        _m("icij:2", name="A2", jurisdiction="ky"),
    ]
    officer = OfficerRepeat(
        node="icij:300",
        name="John Doe",
        country="gb",
        role=None,
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=2,
        leak_labels=[],
    )
    paths = find_paths(
        members,
        intermediaries=[],
        addresses=[],
        officers=[officer],
        sanctions_anchors=[],
        centrality=[],
        max_paths=1,
    )
    assert len(paths) <= 1


def test_find_paths_terminus_kind_uses_known_vocabulary() -> None:
    members = [
        _m("icij:1", name="A", jurisdiction="vg"),
        _m("icij:2", name="B", jurisdiction="ky"),
    ]
    officer = OfficerRepeat(
        node="icij:300",
        name="X",
        country=None,
        role=None,
        n_members_served=2,
        member_uids=["icij:1", "icij:2"],
        n_global_edges=2,
        leak_labels=[],
    )
    paths = find_paths(
        members,
        intermediaries=[],
        addresses=[],
        officers=[officer],
        sanctions_anchors=[],
        centrality=[],
    )
    assert paths
    valid = {"sanctions", "registry_anchor", "hidden_hub", "sibling"}
    assert paths[0].terminus_kind in valid
