"""Tests for the Cluster Explanation Engine."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from shellnet.investigations.cluster_explainer import (
    AnomalyFlag,
    CentralityAnnotation,
    MemberAttr,
    build_explanation,
    compute_jurisdiction_profile,
    detect_anomalies,
    gather_member_attrs,
    gather_repeats,
    load_cluster_members_from_parquet,
    render_explanation_markdown,
    score_investigative_value,
)
from shellnet.matching.company_features import build_unified_table
from shellnet.sources import gleif, icij, opencorporates, opensanctions


def _stage_full_fixtures(tmp_path: Path, fixtures_dir: Path) -> tuple[Path, Path]:
    """Mirror of the staging helper in test_investigate_entity.py."""
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
        input_path=fixtures_dir / "opensanctions_entities_sample.json", out_dir=interim
    )

    processed = tmp_path / "processed"
    build_unified_table(interim_dir=interim, out_dir=processed)
    return interim, processed


def _make_clusters_parquet(tmp_path: Path) -> Path:
    """Synthesize a clusters parquet over the fixture's ICIJ entities.

    Cluster 1: the two ACME HOLDINGS entries (BVI + KY) — a textbook
    cross-border mirror with a shared officer (node 30000001 / Jean Doe).
    Cluster 2: the two Sunrise Trading entries (PA + BVI) — one struck-off,
    one active, sharing an intermediary (node 40000001).
    """
    df = pl.DataFrame(
        {
            "cluster_id": [1, 1, 2, 2],
            "entity_uid": [
                "icij:10000001",
                "icij:10000002",
                "icij:10000003",
                "icij:10000004",
            ],
        }
    )
    path = tmp_path / "clusters.parquet"
    df.write_parquet(path)
    return path


# ---------------------------------------------------------------------------
# Pure-function unit tests
# ---------------------------------------------------------------------------


def test_compute_jurisdiction_profile_flags_cross_border_and_secrecy() -> None:
    members = [
        MemberAttr("icij:1", "icij", "X", "x", "vg", None, None, None, None, None),
        MemberAttr("icij:2", "icij", "Y", "y", "ky", None, None, None, None, None),
        MemberAttr("icij:3", "icij", "Z", "z", None, None, None, None, None, None),
    ]
    p = compute_jurisdiction_profile(members)
    assert p.counts == {"vg": 1, "ky": 1}
    assert p.is_cross_border
    assert set(p.secrecy_jurisdictions) == {"vg", "ky"}
    assert p.n_unknown == 1


def test_score_investigative_value_components_in_unit_interval() -> None:
    members = [
        MemberAttr("icij:1", "icij", "X", "x", "vg", None, "GB123", None, None, None),
        MemberAttr("os:2", "opensanctions", "Y", "y", "ru", None, None, None, None, None),
    ]
    jur = compute_jurisdiction_profile(members)
    f = score_investigative_value(
        members=members,
        intermediaries=[],
        addresses=[],
        officers=[],
        jurisdictions=jur,
        sanctions_anchors=[],
        centrality=[],
    )
    for v in (
        f.intermediary_rarity,
        f.cross_jurisdiction_bridge,
        f.sanctions_proximity,
        f.registry_anchor_density,
        f.hidden_central_entity,
        f.dormant_but_connected,
        f.shell_reuse,
    ):
        assert 0.0 <= v <= 1.0
    # Direct opensanctions member must push sanctions_proximity above 0.
    assert f.sanctions_proximity > 0
    # Cross-border (vg + ru) must push bridge above 0.
    assert f.cross_jurisdiction_bridge > 0
    # 1/2 members carry a company_number ⇒ registry density = 0.5.
    assert f.registry_anchor_density == 0.5


def test_detect_anomalies_flags_cross_border_mirror_and_status_contradiction() -> None:
    members = [
        MemberAttr(
            "icij:a", "icij", "ACME HOLDINGS LIMITED", "acme holdings", "vg",
            None, None, "Active", None, None,
        ),
        MemberAttr(
            "icij:b", "icij", "Acme Holdings Ltd", "acme holdings", "ky",
            None, None, "Struck off", None, None,
        ),
    ]
    flags = detect_anomalies(members, edges_df=None, centrality=[])
    kinds = {f.kind for f in flags}
    assert "cross_border_mirror" in kinds
    assert "status_contradiction" in kinds


def test_detect_anomalies_flags_hidden_hub_when_nonmember_betweenness_dominates() -> None:
    members = [
        MemberAttr("icij:a", "icij", "A", "a", "vg", None, None, None, None, None),
        MemberAttr("icij:b", "icij", "B", "b", "vg", None, None, None, None, None),
    ]
    centrality = [
        CentralityAnnotation("icij:a", 0.0, 0.01, 1, 7, True),
        CentralityAnnotation("icij:b", 0.0, 0.02, 1, 7, True),
        # Non-member with 5x the betweenness — should fire hidden_hub.
        CentralityAnnotation("icij:hub", 0.0, 0.50, 5, 7, False),
    ]
    flags = detect_anomalies(members, edges_df=None, centrality=centrality)
    assert any(f.kind == "hidden_hub" for f in flags)


def test_load_cluster_members_from_parquet_returns_uids(tmp_path: Path) -> None:
    df = pl.DataFrame(
        {"cluster_id": [1, 1, 2], "entity_uid": ["icij:a", "icij:b", "icij:c"]}
    )
    path = tmp_path / "c.parquet"
    df.write_parquet(path)
    loaded = pl.read_parquet(path)
    assert sorted(load_cluster_members_from_parquet(loaded, 1)) == ["icij:a", "icij:b"]
    assert load_cluster_members_from_parquet(loaded, 99) == []


# ---------------------------------------------------------------------------
# Integration tests over the staged fixture corpus
# ---------------------------------------------------------------------------


def test_gather_member_attrs_returns_unified_columns(tmp_path: Path, fixtures_dir: Path) -> None:
    _, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    members = gather_member_attrs(company_df, ["icij:10000001", "icij:10000002"])
    assert {m.entity_uid for m in members} == {"icij:10000001", "icij:10000002"}
    juris = {m.jurisdiction for m in members}
    assert {"vg", "ky"}.issubset(juris)


def test_gather_repeats_finds_shared_officer_for_acme_cluster(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")

    # Cluster of the two ACME entities — fixture has officer 30000001 wired
    # to both 10000001 (Panama Papers) and 10000002 (Pandora Papers).
    inters, addrs, offs = gather_repeats(
        ["icij:10000001", "icij:10000002"],
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    assert offs, "expected at least one shared officer across the ACME cluster"
    top = offs[0]
    assert top.node == "icij:30000001"
    assert top.n_members_served == 2
    assert set(top.member_uids) == {"icij:10000001", "icij:10000002"}
    # Both leak labels appear across the two officer edges.
    assert {"Panama Papers", "Pandora Papers"}.issubset(set(top.leak_labels))
    # ACME members have distinct addresses ⇒ no shared address.
    assert addrs == []


def test_build_explanation_acme_cluster_end_to_end(tmp_path: Path, fixtures_dir: Path) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")

    expl = build_explanation(
        1,
        ["icij:10000001", "icij:10000002"],
        company_df=company_df,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    assert expl.cluster_id == 1
    assert len(expl.members) == 2
    assert expl.jurisdictions.is_cross_border
    assert set(expl.jurisdictions.secrecy_jurisdictions) == {"vg", "ky"}
    assert any(o.node == "icij:30000001" for o in expl.officers)
    # Cross-border mirror anomaly must fire on identical normalized name
    # across two jurisdictions.
    assert any(a.kind == "cross_border_mirror" for a in expl.anomalies)
    # Investigative-value features: cross-jurisdiction bridge > 0 because of
    # vg + ky (both secrecy); registry density 0 (no LEI / cn on either).
    assert expl.features.cross_jurisdiction_bridge > 0
    assert expl.features.registry_anchor_density == 0.0
    assert 0.0 <= expl.features.total <= 7.0
    # Narrative path should exist and reference the shared officer.
    assert expl.paths
    p0 = expl.paths[0]
    assert "shares officer" in " ".join(p0.steps) or "shares" in p0.summary


def test_build_explanation_sunrise_cluster_flags_dormant(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")

    expl = build_explanation(
        2,
        ["icij:10000003", "icij:10000004"],
        company_df=company_df,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    # One member is "Struck off" ⇒ status_contradiction flag fires because
    # the other is Active.
    assert any(a.kind == "status_contradiction" for a in expl.anomalies)
    dormant_uids = {m.entity_uid for m in expl.members if m.is_dormant}
    assert dormant_uids == {"icij:10000003"}


def test_render_explanation_markdown_contains_key_sections(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")

    expl = build_explanation(
        1,
        ["icij:10000001", "icij:10000002"],
        company_df=company_df,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    md = render_explanation_markdown(
        expl, dedupe_run_id="test-run-id", inputs_meta={"corpus": "fixture"}
    )
    assert "# Cluster 1 — investigative briefing" in md
    assert "## Why this matters" in md
    assert "## Members" in md
    assert "## Anomalies / contradictions" in md
    assert "## Narrative paths" in md
    assert "## Suggested investigation targets" in md
    assert "## Provenance" in md
    assert "test-run-id" in md
    # Shared officer must appear in the table.
    assert "icij:30000001" in md
    # Hypothesis caveat is non-negotiable.
    assert "Hypothesis, not proof" in md


def test_explainer_round_trip_via_clusters_parquet_offline(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    """Exercises the offline-loader path the CLI uses when DATABASE_URL
    isn't set: read members from a parquet, not from Postgres."""
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    edges_df = pl.read_parquet(interim / "icij_edges.parquet")
    addresses_df = pl.read_parquet(interim / "icij_addresses.parquet")
    officers_df = pl.read_parquet(interim / "icij_officers.parquet")
    intermediaries_df = pl.read_parquet(interim / "icij_intermediaries.parquet")
    cl_path = _make_clusters_parquet(tmp_path)
    cl_df = pl.read_parquet(cl_path)

    uids = load_cluster_members_from_parquet(cl_df, 1)
    assert sorted(uids) == ["icij:10000001", "icij:10000002"]
    expl = build_explanation(
        1, uids,
        company_df=company_df,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    assert expl.cluster_id == 1
    assert len(expl.members) == 2


def test_explainer_degrades_gracefully_without_edges(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    _, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    company_df = pl.read_parquet(processed / "company_entities.parquet")
    expl = build_explanation(
        1,
        ["icij:10000001", "icij:10000002"],
        company_df=company_df,
        edges_df=None,
    )
    # No edges ⇒ no repeats, no narrative paths, but members + jurisdiction
    # still work; investigative score stays bounded.
    assert expl.intermediaries == []
    assert expl.addresses == []
    assert expl.officers == []
    assert expl.paths == []
    assert 0.0 <= expl.features.total <= 7.0
    # Cross-border mirror anomaly still fires (it depends only on members).
    assert any(a.kind == "cross_border_mirror" for a in expl.anomalies)


def test_anomaly_flag_dataclass_shape() -> None:
    f = AnomalyFlag(kind="x", severity="high", message="m", member_uids=["a"])
    assert f.kind == "x"
    assert f.severity == "high"
    assert f.member_uids == ["a"]
