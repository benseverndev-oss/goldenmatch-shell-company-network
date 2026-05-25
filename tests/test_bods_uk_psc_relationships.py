"""Tests for the UK PSC person->company relationship layer in bods.ingest.

Can't hit the 3.5 GB live bundle, so we synthesise a minimal BODS bundle
matching the v0.4 column shape and run the ingest against pre-extracted
work-dir parquets (extraction is skipped when the members already exist).
"""

from __future__ import annotations

import polars as pl

from shellnet.sources import bods


def _write_bundle(work: pl.DataFrame | None = None, *, work_dir):
    """Write the minimal set of BODS member parquets bods.ingest reads."""
    work_dir.mkdir(parents=True, exist_ok=True)

    pl.DataFrame(
        {
            "_link": ["pl1", "pl2"],
            "statementId": ["stmt-aaa", "stmt-bbb"],
            "recordId": ["GB-COH-PER-04818143-HASHA", "GB-COH-PER-10695797-HASHB"],
            "declarationSubject": ["GB-COH-04818143", "GB-COH-10695797"],
        }
    ).write_parquet(work_dir / "person_statement.parquet")

    pl.DataFrame(
        {
            "_link_person_statement": ["pl1", "pl2"],
            "fullName": ["Igor Zyuzin", "Roman Trotsenko"],
            "familyName": ["Zyuzin", "Trotsenko"],
            "givenName": ["Igor", "Roman"],
        }
    ).write_parquet(work_dir / "person_recorddetails_names.parquet")

    pl.DataFrame({"_link_person_statement": ["pl1", "pl2"], "code": ["RU", "RU"]}).write_parquet(
        work_dir / "person_recorddetails_nationalities.parquet"
    )

    pl.DataFrame(
        {
            "_link": ["el1", "el2"],
            "statementId": ["ent-1", "ent-2"],
            "recordDetails_name": ["ORIEL RESOURCES LIMITED", "SIBERIAN GOLDFIELDS LIMITED"],
            "recordDetails_jurisdiction_code": ["GB", "GB"],
            "recordDetails_entityType_type": ["registeredEntity", "registeredEntity"],
        }
    ).write_parquet(work_dir / "entity_statement.parquet")

    pl.DataFrame(
        {
            "_link_entity_statement": ["el1", "el2"],
            "id": ["04818143", "10695797"],
            "scheme": ["GB-COH", "GB-COH"],
        }
    ).write_parquet(work_dir / "entity_recorddetails_identifiers.parquet")

    pl.DataFrame(
        {
            "_link_entity_statement": ["el1", "el2"],
            "address": ["1 Test St", "2 Test St"],
            "country_code": ["GB", "GB"],
        }
    ).write_parquet(work_dir / "entity_recorddetails_addresses.parquet")

    pl.DataFrame(
        {
            "_link": ["rl1", "rl2", "rl3"],
            "recordType": ["relationship", "relationship", "relationship"],
            "recordDetails_isComponent": [False, False, True],  # rl3 dropped
            "recordDetails_subject": ["GB-COH-04818143", "GB-COH-10695797", "GB-COH-10695797"],
            "recordDetails_interestedParty": [
                "GB-COH-PER-04818143-HASHA",
                "GB-COH-PER-10695797-HASHB",
                "GB-COH-PER-10695797-HASHB",
            ],
        }
    ).write_parquet(work_dir / "relationship_statement.parquet")

    pl.DataFrame(
        {
            "_link_relationship_statement": ["rl1", "rl2"],
            "type": ["shareholding", "votingRights"],
            "directOrIndirect": ["direct", "direct"],
            "share_minimum": [75.0, 25.0],
            "share_maximum": [100.0, 50.0],
            "startDate": ["2010-01-01", "2017-02-02"],
            "endDate": [None, None],
        }
    ).write_parquet(work_dir / "relationship_recorddetails_interests.parquet")


def _fake_zip(path):
    path.write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # minimal empty zip
    return path


def test_build_uk_psc_relationships(tmp_path):
    work = tmp_path / "work"
    _write_bundle(work_dir=work)
    rel = bods._build_uk_psc_relationships(work)

    # rl3 is a component sub-statement and must be dropped.
    assert rel.height == 2
    assert set(rel.columns) == set(bods._PSC_RELATIONSHIP_COLUMNS)

    by_company = {r["company_id"]: r for r in rel.iter_rows(named=True)}
    z = by_company["GB-COH-04818143"]
    assert z["source"] == "uk_psc"
    # person_source_id is the BODS statementId -> joins the unified person table.
    assert z["person_source_id"] == "stmt-aaa"
    assert z["person_record_id"] == "GB-COH-PER-04818143-HASHA"
    assert z["company_number"] == "04818143"  # GB-COH- prefix stripped
    assert z["control_type"] == "shareholding"
    assert z["direct_or_indirect"] == "direct"
    assert z["share_min"] == 75.0
    assert z["share_max"] == 100.0


def test_company_number_aligns_with_entities(tmp_path):
    """The relationship company_number must match uk_psc_entities.company_number
    so the two parquets join."""
    work = tmp_path / "work"
    _write_bundle(work_dir=work)
    rel = bods._build_uk_psc_relationships(work)
    ents = bods._build_entities(work)
    assert set(rel["company_number"].to_list()) <= set(ents["company_number"].to_list())


def test_ingest_emits_relationships(tmp_path):
    work = tmp_path / "work"
    _write_bundle(work_dir=work)
    out = tmp_path / "out"
    written = bods.ingest(
        zip_path=_fake_zip(tmp_path / "noop.zip"),
        out_dir=out,
        work_dir=work,
        keep_extracted=True,
    )
    assert "relationships" in written
    rel = pl.read_parquet(written["relationships"])
    assert rel.height == 2
    assert rel.filter(pl.col("person_source_id") == "stmt-aaa")["company_id"].to_list() == [
        "GB-COH-04818143"
    ]


def test_coh_company_number_helper():
    assert bods._coh_company_number("GB-COH-04818143") == "04818143"
    assert bods._coh_company_number("gb-coh-OC428060") == "OC428060"
    assert bods._coh_company_number(None) == ""
    assert bods._coh_company_number("") == ""
