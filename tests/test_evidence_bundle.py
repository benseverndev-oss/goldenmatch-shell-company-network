"""Tests for the evidence-bundle module."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from shellnet.investigations.cluster_explainer import MemberAttr
from shellnet.investigations.evidence_bundle import (
    EvidenceBundle,
    LeakReference,
    RegistryLink,
    SourceFiling,
    build_evidence_bundle,
    write_bundle,
)


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


def _edges_df(rows: list[tuple]) -> pl.DataFrame:
    """rows: (src, dst, kind_raw, source_label, start_date, end_date)"""
    return pl.DataFrame(
        {
            "src_node": [r[0] for r in rows],
            "dst_node": [r[1] for r in rows],
            "kind_raw": [r[2] for r in rows],
            "source_label": [r[3] for r in rows],
            "start_date": [r[4] for r in rows],
            "end_date": [r[5] for r in rows],
        }
    )


def test_build_bundle_with_no_inputs_returns_empty_sections() -> None:
    bundle = build_evidence_bundle(1, [])
    assert bundle.cluster_id == 1
    assert bundle.members == []
    assert bundle.source_filings == []
    assert bundle.edges == []
    assert bundle.leak_references == []
    assert bundle.registry_links == []
    assert bundle.sanctions_records == []


def test_registry_links_emitted_for_lei_and_company_number_and_opensanctions() -> None:
    members = [
        _m("gleif:GB123", source="gleif", lei="GB12345"),
        _m("oc:abc", source="opencorporates", jurisdiction="gb", company_number="C001"),
        _m("opensanctions:NK-1234", source="opensanctions"),
    ]
    bundle = build_evidence_bundle(1, members)
    by_source = {rl.source for rl in bundle.registry_links}
    assert "gleif" in by_source
    assert "opencorporates" in by_source
    assert "opensanctions" in by_source
    urls = " ".join(rl.url for rl in bundle.registry_links)
    assert "gleif.org/lei/GB12345" in urls
    assert "opencorporates.com/companies/gb/C001" in urls
    assert "opensanctions.org/entities/NK-1234" in urls


def test_gather_edges_keeps_provenance_columns() -> None:
    members = [_m("icij:1"), _m("icij:2")]
    edges = _edges_df(
        [
            ("icij:1", "icij:30000A", "officer_of", "Panama Papers", "2010-01-01", None),
            ("icij:2", "icij:30000A", "officer_of", "Pandora Papers", "2012-01-01", None),
        ]
    )
    bundle = build_evidence_bundle(1, members, edges_df=edges)
    assert len(bundle.edges) == 2
    # Required provenance columns present.
    for e in bundle.edges:
        assert "src_node" in e
        assert "dst_node" in e
        assert "kind_raw" in e
        assert "source_label" in e


def test_gather_leaks_aggregates_by_leak_label() -> None:
    members = [_m("icij:1"), _m("icij:2")]
    edges = _edges_df(
        [
            ("icij:1", "icij:30000A", "officer_of", "Panama Papers", "2010-01-01", None),
            ("icij:2", "icij:30000A", "officer_of", "Panama Papers", "2012-01-01", "2018-06-30"),
            ("icij:1", "icij:20000A", "registered_address", "Pandora Papers", "2011-01-01", None),
        ]
    )
    bundle = build_evidence_bundle(1, members, edges_df=edges)
    labels = {lr.leak_label: lr for lr in bundle.leak_references}
    assert {"Panama Papers", "Pandora Papers"} <= set(labels)
    assert labels["Panama Papers"].n_edges == 2
    assert labels["Panama Papers"].first_date == "2010-01-01"
    assert labels["Panama Papers"].last_date == "2018-06-30"


def test_source_filings_pulled_from_per_source_parquets() -> None:
    members = [_m("icij:10000001", name="ACME BVI")]
    icij_entities = pl.DataFrame(
        {
            "source_id": ["10000001"],
            "name": ["ACME BVI"],
            "raw": [{"node_id": "10000001", "name": "ACME BVI", "jurisdiction": "VGB"}],
        }
    )
    bundle = build_evidence_bundle(
        1, members, source_dfs={"icij": icij_entities, "opencorporates": None}
    )
    assert len(bundle.source_filings) == 1
    sf = bundle.source_filings[0]
    assert sf.source == "icij"
    assert sf.source_id == "10000001"
    assert sf.record["node_id"] == "10000001"


def test_gather_sanctions_filters_to_cluster_members() -> None:
    members = [_m("icij:1"), _m("icij:2")]
    sanctions = pl.DataFrame(
        {
            "target_entity_uid": ["icij:1", "icij:99"],
            "ref_entity_uid": ["ofac:SDN-1", "ofac:SDN-2"],
            "ref_name": ["Sanc Co", "Other"],
            "ref_lei": [None, None],
            "ref_jurisdiction": ["ru", "ir"],
            "score": [0.91, 0.85],
            "band": ["high", "medium"],
        }
    )
    bundle = build_evidence_bundle(1, members, sanctions_df=sanctions)
    # Only the member-targeted record survives.
    assert len(bundle.sanctions_records) == 1
    sr = bundle.sanctions_records[0]
    assert sr.target_entity_uid == "icij:1"
    assert sr.ref_name == "Sanc Co"
    assert sr.score == 0.91


def test_write_bundle_creates_expected_files(tmp_path: Path) -> None:
    members = [_m("icij:1", name="A", lei="GB12345")]
    edges = _edges_df(
        [("icij:1", "icij:30000A", "officer_of", "Panama Papers", "2010-01-01", None)]
    )
    sanctions = pl.DataFrame(
        {
            "target_entity_uid": ["icij:1"],
            "ref_entity_uid": ["ofac:SDN-1"],
            "ref_name": ["Sanc"],
            "ref_lei": [None],
            "ref_jurisdiction": ["ru"],
            "score": [0.9],
            "band": ["high"],
        }
    )
    icij_entities = pl.DataFrame(
        {
            "source_id": ["1"],
            "name": ["A"],
            "raw": [{"node_id": "1", "name": "A"}],
        }
    )
    bundle = build_evidence_bundle(
        42,
        members,
        edges_df=edges,
        source_dfs={"icij": icij_entities},
        sanctions_df=sanctions,
    )
    out = write_bundle(bundle, tmp_path)
    assert out == tmp_path / "cluster_42"
    # All expected artifacts present.
    assert (out / "manifest.md").exists()
    assert (out / "bundle.json").exists()
    assert (out / "edges.csv").exists()
    assert (out / "leak_index.md").exists()
    assert (out / "registry_links.md").exists()
    assert (out / "sanctions_records.json").exists()
    assert (out / "source_filings" / "icij_1.json").exists()
    # bundle.json round-trips with the right counts.
    manifest = json.loads((out / "bundle.json").read_text())
    assert manifest["cluster_id"] == 42
    assert manifest["n_members"] == 1
    assert manifest["n_edges"] == 1
    assert manifest["n_source_filings"] == 1
    assert manifest["n_sanctions_records"] == 1
    assert manifest["leak_labels"] == ["Panama Papers"]


def test_write_bundle_handles_minimal_bundle(tmp_path: Path) -> None:
    """No edges, no sources_dfs, no sanctions ⇒ only manifest.md and
    bundle.json (+ registry_links.md if a member has LEI)."""
    members = [_m("icij:1", name="A")]
    bundle = build_evidence_bundle(7, members)
    out = write_bundle(bundle, tmp_path)
    assert (out / "manifest.md").exists()
    assert (out / "bundle.json").exists()
    # No edges → no edges.csv.
    assert not (out / "edges.csv").exists()
    # No leaks → no leak_index.md.
    assert not (out / "leak_index.md").exists()
    # No LEI / cn / opensanctions → no registry_links.md.
    assert not (out / "registry_links.md").exists()


def test_dataclasses_default_initializable() -> None:
    bundle = EvidenceBundle(cluster_id=1, members=[])
    assert bundle.source_filings == []
    sf = SourceFiling(member_uid="icij:1", source="icij", source_id="1", name="A", record={})
    assert sf.record == {}
    lr = LeakReference(
        leak_label="Panama Papers",
        n_edges=1,
        first_date="2010-01-01",
        last_date="2010-01-01",
        sample_nodes=["icij:1"],
    )
    assert lr.n_edges == 1
    rl = RegistryLink(
        member_uid="icij:1", source="gleif", label="x", url="https://www.gleif.org/lei/X"
    )
    assert rl.url.startswith("https://")
