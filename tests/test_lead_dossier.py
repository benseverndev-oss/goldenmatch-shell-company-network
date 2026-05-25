"""Tests for the lead dossier + verification gate (roadmap Phase 5)."""

from __future__ import annotations

from shellnet.investigations import lead_dossier as ld


def test_url_helpers():
    assert ld.companies_house_url("GB-COH-15109642").endswith("/company/15109642")
    assert ld.companies_house_url("GB-COH-15109642", psc=True).endswith(
        "/persons-with-significant-control"
    )
    assert ld.companies_house_url(None) is None
    assert ld.opensanctions_url("Q4194951").endswith("/entities/Q4194951")
    assert ld.opensanctions_url(None) is None


def _lead():
    return {
        "lead_id": "GB-COH-13287342",
        "company_name": "NORD GOLD PLC",
        "wrongdoing_score": 1.0,
        "active_status": "dissolved",
        "harm_category": "none",
        "principal_name": "Mr Nikita Mordashov",
        "successor_name": "Mrs Marina Aleksandrovna Mordashova",
        "principal_os_id": "NK-XYZ",
        "evasion_timing": 1.0,
    }


def test_build_dossier_has_sources_and_checklist():
    md = ld.build_dossier(_lead())
    assert "NORD GOLD PLC" in md
    assert "/company/13287342" in md  # Companies House deep link
    assert "/entities/NK-XYZ" in md  # OpenSanctions deep link
    assert "Right of reply" in md
    assert "evasion_timing" in md
    # every checklist item present, all unticked
    for item in ld.CHECKLIST:
        assert f"- [ ] {item}" in md


def test_gate_blocks_until_all_ticked():
    md = ld.build_dossier(_lead())
    assert ld.is_cleared(md) is False  # fresh dossier is not publishable
    ticked = md.replace("- [ ]", "- [x]")
    assert ld.is_cleared(ticked) is True
    # one box left unticked -> still blocked
    partially = md.replace("- [ ]", "- [x]", len(ld.CHECKLIST) - 1)
    assert ld.is_cleared(partially) is False
