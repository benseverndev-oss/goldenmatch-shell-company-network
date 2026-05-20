"""Phase 2 — registry lookups integration test."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "corroborate_validation_pack.py"


def _load():
    spec = importlib.util.spec_from_file_location("corroborate_validation_pack", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["corroborate_validation_pack"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def cv():
    return _load()


def test_registry_hits_headers_present(cv):
    assert hasattr(cv, "REGISTRY_HITS_HEADERS")
    assert "cluster_member" in cv.REGISTRY_HITS_HEADERS
    assert "publication_safe" in cv.REGISTRY_HITS_HEADERS
    assert "officer_overlap" in cv.REGISTRY_HITS_HEADERS
    assert len(set(cv.REGISTRY_HITS_HEADERS)) == len(cv.REGISTRY_HITS_HEADERS)


def test_juris_map_present(cv):
    assert "no" in cv._JURIS_TO_ADAPTER
    assert "fr" in cv._JURIS_TO_ADAPTER
    assert "us" in cv._JURIS_TO_ADAPTER
    # Malta is intentionally NOT in the map — no MFSA adapter today.
    assert "mt" not in cv._JURIS_TO_ADAPTER


def test_lookups_skip_unsupported_jurisdictions(cv, tmp_path, monkeypatch):
    """Cluster-47-style pack (all-MT) should produce zero registry hits."""

    pack_dir = tmp_path / "validation"
    data = pack_dir / "data"
    data.mkdir(parents=True)
    pack_dir_inner = pack_dir
    # Minimal profile + cluster CSVs.
    profile = {
        "community_id": 999,
        "person": "test person",
        "person_uids": [],
        "members_sample": [
            {"uid": "icij:1", "name": "MALTA CO LTD", "jurisdiction": "mt", "seed": False},
            {"uid": "icij:2", "name": "OTHER MALTA LTD", "jurisdiction": "mt", "seed": False},
        ],
        "n_members": 2,
        "queue_row": {},
        "cluster_scored": {},
        "ordinary_vs_unusual": {},
    }
    (data / "cluster_999_profile.json").write_text(json.dumps(profile), encoding="utf-8")
    for name in (
        "cluster_999_person_overlap.csv",
        "cluster_999_person_company_roles.csv",
        "cluster_999_repeated_addresses.csv",
        "cluster_999_repeated_officers.csv",
        "cluster_999_repeated_agents.csv",
        "cluster_999_company_themes.csv",
        "cluster_999_external_search_queries.csv",
    ):
        (data / name).write_text("dummy\n", encoding="utf-8")

    inputs = cv.load_pack(community_id=999, person="test person", pack_dir=pack_dir_inner)
    hits = cv.run_registry_lookups(inputs)
    assert hits == []


def test_lookups_dispatch_norway(cv, monkeypatch, tmp_path):
    """A cluster member with jurisdiction=no should hit BrregNorwayAdapter."""

    from shellnet.registries import RegistryHit, RegistryOfficer

    captured: list[str] = []

    class FakeBrreg:
        REGISTRY = "brreg_norway"
        JURISDICTION = "no"

        def search(self, query, *, limit=3):  # noqa: ARG002
            captured.append(query)
            return [
                RegistryHit(
                    registry="brreg_norway",
                    jurisdiction="no",
                    identifier="999111222",
                    name="NORDIC HOLDING AS",
                    sourceUrl="https://example.com/no/999111222",
                    officers=[
                        RegistryOfficer(name="STUART GORDON CRAIG", role="Auditor", start_date=""),
                    ],
                ),
            ]

    monkeypatch.setattr(
        "shellnet.registries.brreg_norway.BrregNorwayAdapter", FakeBrreg, raising=False
    )

    # Repurpose the helper's import-time pattern.
    pack_dir = tmp_path / "validation"
    data = pack_dir / "data"
    data.mkdir(parents=True)
    profile = {
        "community_id": 999,
        "members_sample": [
            {"uid": "oo:1", "name": "NORDIC HOLDING AS", "jurisdiction": "no", "seed": False},
        ],
        "n_members": 1,
        "queue_row": {},
        "cluster_scored": {},
        "ordinary_vs_unusual": {},
    }
    (data / "cluster_999_profile.json").write_text(json.dumps(profile), encoding="utf-8")
    # Officer matching Norway hit — should bump officer_overlap to 1.
    (data / "cluster_999_repeated_officers.csv").write_text(
        "officer_name,n_linked_companies,linked_companies,roles,source_label,confidence\n"
        "STUART GORDON CRAIG,1,NORDIC HOLDING AS,auditor of,,0.85\n",
        encoding="utf-8",
    )
    for n in (
        "cluster_999_person_overlap.csv",
        "cluster_999_person_company_roles.csv",
        "cluster_999_repeated_addresses.csv",
        "cluster_999_repeated_agents.csv",
        "cluster_999_company_themes.csv",
        "cluster_999_external_search_queries.csv",
    ):
        (data / n).write_text("dummy\n", encoding="utf-8")

    inputs = cv.load_pack(community_id=999, person="x", pack_dir=pack_dir)
    hits = cv.run_registry_lookups(inputs)
    assert any(h["registry"] == "brreg_norway" for h in hits)
    n_hit = next(h for h in hits if h["registry"] == "brreg_norway")
    assert n_hit["officer_overlap"] == "1"
    assert n_hit["publication_safe"] == "true"
