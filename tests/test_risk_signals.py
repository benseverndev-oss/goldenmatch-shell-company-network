"""Phase 5 — AMLA CDD risk-signals tests."""

from __future__ import annotations

from shellnet.risk_signals import (
    RiskSignal,
    evaluate_cluster,
    evaluate_entity,
    overall_severity,
    to_rows,
)


def test_high_risk_jurisdiction_flagged():
    sig = evaluate_entity({"uid": "x", "name": "ACME", "jurisdiction": "ir"})
    codes = {s.code for s in sig}
    assert "geo.high-risk-juris" in codes
    assert all(s.severity == "high" for s in sig if s.code == "geo.high-risk-juris")


def test_opacity_jurisdiction_flagged_separately():
    sig = evaluate_entity({"uid": "x", "name": "ACME", "jurisdiction": "mt"})
    codes = {s.code for s in sig}
    assert "geo.opacity-juris" in codes
    assert "geo.high-risk-juris" not in codes


def test_no_signal_for_low_risk_juris():
    sig = evaluate_entity({"uid": "x", "name": "ACME", "jurisdiction": "us"})
    codes = {s.code for s in sig}
    assert "geo.high-risk-juris" not in codes
    assert "geo.opacity-juris" not in codes


def test_shell_profile_signal():
    sig = evaluate_entity(
        {
            "uid": "x",
            "name": "ACME",
            "jurisdiction": "us",
            "has_employees": False,
            "has_website": False,
        }
    )
    codes = {s.code for s in sig}
    assert "struct.shell-profile" in codes


def test_multi_jurisdiction_cluster_signal():
    profile = {
        "community_id": 99,
        "members_sample": [
            {"uid": "1", "jurisdiction": "mt"},
            {"uid": "2", "jurisdiction": "gb"},
            {"uid": "3", "jurisdiction": "ky"},
        ],
    }
    sig = evaluate_cluster(profile)
    codes = {s.code for s in sig}
    assert "struct.multi-juris-chain" in codes


def test_opacity_concentration_signal():
    profile = {
        "community_id": 99,
        "members_sample": [
            {"uid": "1", "jurisdiction": "mt"},
            {"uid": "2", "jurisdiction": "vg"},
            {"uid": "3", "jurisdiction": "ky"},
            {"uid": "4", "jurisdiction": "us"},
        ],
    }
    sig = evaluate_cluster(profile)
    codes = {s.code for s in sig}
    assert "struct.opacity-concentration" in codes


def test_cross_juris_twin_signal():
    profile = {"community_id": 99, "members_sample": []}
    twins = [{"src_uid": "a", "dst_uid": "b", "match_type": "strict_root"}]
    sig = evaluate_cluster(profile, twins=twins)
    codes = {s.code for s in sig}
    assert "lineage.cross-juris-twin" in codes


def test_mass_shared_address_signal():
    profile = {"community_id": 99, "members_sample": []}
    addrs = [{"address": "1 Triq Malta", "n_linked_companies": "20"}]
    sig = evaluate_cluster(profile, repeated_addresses=addrs)
    codes = {s.code for s in sig}
    assert "struct.mass-shared-address" in codes
    assert all(s.severity == "high" for s in sig if s.code == "struct.mass-shared-address")


def test_nominee_officer_signal():
    profile = {"community_id": 99, "members_sample": []}
    officers = [{"officer_name": "JANE DOE", "n_linked_companies": "30"}]
    sig = evaluate_cluster(profile, repeated_officers=officers)
    codes = {s.code for s in sig}
    assert "struct.nominee-officer-pattern" in codes


def test_overall_severity_picks_highest():
    sigs = [
        RiskSignal(code="a", severity="low", rationale=""),
        RiskSignal(code="b", severity="high", rationale=""),
        RiskSignal(code="c", severity="medium", rationale=""),
    ]
    assert overall_severity(sigs) == "high"
    assert overall_severity([]) is None


def test_to_rows_shape():
    sigs = [
        RiskSignal(
            code="x",
            severity="medium",
            rationale="why",
            amla_ref="AMLA RTS Art. 4",
            evidence={"k": "v"},
        ),
    ]
    rows = to_rows(sigs)
    assert rows[0]["code"] == "x"
    assert rows[0]["severity"] == "medium"
    assert "k=v" in rows[0]["evidence"]


def test_rationale_carries_specific_facts():
    """Defamation-hazard guard: every rationale must name the entity / juris."""
    sigs = evaluate_entity({"uid": "icij:E1", "name": "ACME", "jurisdiction": "ir"})
    for s in sigs:
        assert "icij:E1" in s.rationale or "ACME" in s.rationale
        assert "IR" in s.rationale or "ir" in s.rationale
