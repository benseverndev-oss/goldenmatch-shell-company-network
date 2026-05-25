"""Tests for the disqualified-director-still-acting detector (Phase 4)."""

from __future__ import annotations

import polars as pl

from shellnet.investigations import regulatory_breach as rb


def test_normalize_dob_ym():
    assert rb.normalize_dob_ym("26/10/1979") == "1979-10"
    assert rb.normalize_dob_ym("1/2/1980") == "1980-02"
    assert rb.normalize_dob_ym("1972-06") == "1972-06"
    assert rb.normalize_dob_ym("1972-06-15") == "1972-06"
    assert rb.normalize_dob_ym(None) is None
    assert rb.normalize_dob_ym("garbage") is None


def _frames():
    disqualified = pl.DataFrame(
        {
            "norm_name": ["john smith", "jane doe"],
            "dob_ym": ["1970-05", "1982-03"],
            "conduct": ["traded while insolvent", "misapplied funds"],
        }
    )
    psc_identity = pl.DataFrame(
        {
            "person_source_id": ["p1", "p2"],
            "norm_name": ["john smith", "someone else"],
            "dob_ym": ["1970-05", "1990-01"],
        }
    )
    relationships = pl.DataFrame(
        {
            "person_source_id": ["p1", "p1"],
            "company_id": ["GB-COH-CURRENT", "GB-COH-CEASED"],
            "end_date": [None, "2019-01-01"],
        }
    )
    return disqualified, psc_identity, relationships


def test_detect_disqualified_psc_current_only():
    disqualified, psc_identity, relationships = _frames()
    out = rb.detect_disqualified_psc(disqualified, psc_identity, relationships)
    # john smith matches by name+dob and currently controls GB-COH-CURRENT;
    # the ceased stake and the unmatched jane doe are excluded.
    assert out.height == 1
    row = out.row(0, named=True)
    assert row["lead_id"] == "GB-COH-CURRENT"
    assert row["regulatory_breach"] == 1.0
    assert row["disqualified_name"] == "john smith"
    assert set(out.columns) == set(rb.BREACH_COLUMNS)


def test_detect_disqualified_psc_includes_ceased_when_not_current():
    disqualified, psc_identity, relationships = _frames()
    out = rb.detect_disqualified_psc(
        disqualified, psc_identity, relationships, require_current=False
    )
    assert set(out["lead_id"].to_list()) == {"GB-COH-CURRENT", "GB-COH-CEASED"}


def test_no_match_returns_empty_with_schema():
    disqualified = pl.DataFrame({"norm_name": ["nobody"], "dob_ym": ["1900-01"], "conduct": ["x"]})
    psc_identity = pl.DataFrame(
        schema={"person_source_id": pl.Utf8, "norm_name": pl.Utf8, "dob_ym": pl.Utf8}
    )
    relationships = pl.DataFrame(
        schema={"person_source_id": pl.Utf8, "company_id": pl.Utf8, "end_date": pl.Utf8}
    )
    out = rb.detect_disqualified_psc(disqualified, psc_identity, relationships)
    assert out.height == 0
    assert set(out.columns) == set(rb.BREACH_COLUMNS)
