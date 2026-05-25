"""Tests for the sanctions-evasion timing detector (roadmap Phase 1)."""

from __future__ import annotations

import polars as pl

from shellnet.investigations import evasion_timing as et


def test_build_designation_dates_flags_placeholder():
    os_ents = pl.DataFrame(
        {
            "source_id": ["aeza", "volozh", "notsanctioned"],
            "name": ["AEZA INTERNATIONAL LTD", "Arkady Volozh", "Acme Ltd"],
            "first_seen": [
                "2025-07-01T14:10:03",
                "2022-01-01T00:00:00",
                "2024-05-01T00:00:00",
            ],
            "topics": [["sanction"], ["sanction"], ["poi"]],
        }
    )
    out = et.build_designation_dates(os_ents)
    assert set(out["os_id"].to_list()) == {"aeza", "volozh"}  # poi dropped
    m = {r["os_id"]: r for r in out.iter_rows(named=True)}
    assert str(m["aeza"]["designation_date"]) == "2025-07-01"
    assert m["aeza"]["date_quality"] == "dataset_first_seen"
    assert m["volozh"]["date_quality"] == "placeholder"


def _frames():
    # Principal P (statementId p1) is sanctioned (os_id S), designated 2022-03-01,
    # controls company C. A same-surname successor's stake starts 40 days later;
    # an unrelated PSC's stake started years earlier (out of window).
    survivors = pl.DataFrame(
        {
            "target_entity_uid": ["uk_psc:p1", "icij:999"],
            "ref_entity_uid": ["opensanctions:S", "opensanctions:S"],
            "target_name": ["Boris Ivanov", "Some Icij Person"],
        }
    )
    relationships = pl.DataFrame(
        {
            "person_source_id": ["p1", "succ", "old"],
            "company_id": ["GB-COH-111", "GB-COH-111", "GB-COH-111"],
            "company_number": ["111", "111", "111"],
            "start_date": ["2015-01-01", "2022-04-10", "2010-01-01"],
            "end_date": ["2022-03-05", None, None],
        }
    )
    designations = pl.DataFrame(
        {
            "os_id": ["S"],
            "name": ["Boris Ivanov"],
            "designation_date": [pl.Series(["2022-03-01"]).str.strptime(pl.Date)[0]],
            "date_quality": ["dataset_first_seen"],
        }
    )
    persons = pl.DataFrame(
        {
            "source_id": ["p1", "succ", "old"],
            "name": ["Boris Ivanov", "Marina Ivanova", "Unrelated Person"],
        }
    )
    return survivors, relationships, designations, persons


def test_detect_evasion_timing_flags_near_designation_transfer():
    survivors, relationships, designations, persons = _frames()
    out = et.detect_evasion_timing(survivors, relationships, designations, persons, window_days=180)
    # The same-surname successor 40 days after designation is flagged;
    # the 2010 unrelated stake is out of window.
    assert out.height == 1
    row = out.row(0, named=True)
    assert row["company_id"] == "GB-COH-111"
    assert row["successor_name"] == "Marina Ivanova"
    assert row["delta_days"] == 40
    assert row["same_surname"] is True
    assert set(out.columns) == set(et.EVASION_COLUMNS)


def test_detect_evasion_timing_respects_window():
    survivors, relationships, designations, persons = _frames()
    out = et.detect_evasion_timing(survivors, relationships, designations, persons, window_days=10)
    # 40-day gap now exceeds the window -> nothing.
    assert out.height == 0
