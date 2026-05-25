"""Tests for PSC-vs-acting-director grading (precision roadmap P1-P3)."""

from __future__ import annotations

import polars as pl

from shellnet.investigations import director_breach as db

_OFFICERS_MD = """# CARE SUPPORT PARTNERS LTD

## [OWUSU-ANSAH, Emmanuel](https://x/officers/aaa/appointments)

Correspondence address
81 Lothian Road, London, England, SW9 6TS

Role
Active
Director
Date of birth
August 1975
Appointed on
1 March 2026

## [ASANTE-FRIMPONG, Henry](https://x/officers/bbb/appointments)

Correspondence address
101a, Eltham High Street, London, England, SE9 1TD

Role
Resigned
Director
Date of birth
January 1968
Appointed on
16 November 2017
Resigned on
1 April 2026
"""


def test_normalize_person_handles_surname_comma_and_hyphen():
    assert db.normalize_person("ASANTE-FRIMPONG, Henry") == "henry asante frimpong"
    assert db.normalize_person("OWUSU-ANSAH, Emmanuel") == "emmanuel owusu ansah"


def test_parse_ch_officers():
    offs = db.parse_ch_officers(_OFFICERS_MD)
    assert len(offs) == 2
    emmanuel = next(o for o in offs if o["norm_name"] == "emmanuel owusu ansah")
    assert emmanuel["status"] == "active"
    assert emmanuel["kind"] == "director"
    assert emmanuel["dob_ym"] == "1975-08"


def test_grade_resigned_director_is_not_an_acting_breach():
    offs = db.parse_ch_officers(_OFFICERS_MD)
    g = db.grade_company(
        offs, "henry asante frimpong", "1968-01", "101a Eltham High Street London SE9 1TD"
    )
    assert g["breach_grade"] == "resigned_director"
    assert g["acting_director_breach"] == 0.0
    assert g["identity_confidence"] == 1.0  # name + dob + address all corroborate
    assert g["live_confirmed"] is False


def test_grade_active_director_is_an_acting_breach():
    offs = db.parse_ch_officers(_OFFICERS_MD)
    g = db.grade_company(offs, "emmanuel owusu ansah", "1975-08")
    assert g["breach_grade"] == "acting_director"
    assert g["acting_director_breach"] == 1.0
    assert g["live_confirmed"] is True


def test_grade_psc_only_when_not_an_officer():
    offs = db.parse_ch_officers(_OFFICERS_MD)
    g = db.grade_company(offs, "someone not listed", "1990-01")
    assert g["breach_grade"] == "psc_only"
    assert g["acting_director_breach"] == 0.0


def test_summarize_counts_grades():
    graded = pl.DataFrame(
        {"breach_grade": ["acting_director", "acting_director", "psc_only", "resigned_director"]}
    )
    s = db.summarize(graded)
    assert s["acting_director"] == 2
    assert s["psc_only"] == 1
    assert s["resigned_director"] == 1
    assert s["unknown"] == 0
