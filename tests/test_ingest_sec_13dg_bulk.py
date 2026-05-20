"""Phase 6 — SEC 13D/G bulk-ingest tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ingest_sec_13dg_bulk.py"


def _load():
    spec = importlib.util.spec_from_file_location("ingest_sec_13dg_bulk", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["ingest_sec_13dg_bulk"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load()


# A realistic form.idx slice from EDGAR. Header + dashes + a handful of
# fixed-width rows. Columns: Form Type (12), Company Name (62), CIK,
# Date Filed, Filename.
_FORM_IDX_SAMPLE = """\
Description:           Master Index of EDGAR Dissemination Feed
Last Data Received:    October 14, 2025
Comments:              webmaster@sec.gov
Anonymous FTP:         ftp://ftp.sec.gov/edgar/

 Form Type      Company Name                                                  CIK         Date Filed  Filename
-----------------------------------------------------------------------------------------------------------------------
10-K        ACME WIDGETS INC                                              0000123456  2025-10-01  edgar/data/123456/0000123456-25-000001.txt
SC 13D      EXAMPLE FUND LP                                               0000999999  2025-10-02  edgar/data/999999/0000999999-25-000002.txt
SC 13G/A    ANOTHER FUND LLC                                              0000888888  2025-10-03  edgar/data/888888/0000888888-25-000003.txt
SC 13E3     SHOULD BE IGNORED INC                                         0000777777  2025-10-04  edgar/data/777777/0000777777-25-000004.txt
8-K         IRRELEVANT CO                                                 0000111111  2025-10-05  edgar/data/111111/0000111111-25-000005.txt
"""


def test_parse_form_idx_filters_to_13d_13g(mod):
    entries = mod.parse_form_idx(_FORM_IDX_SAMPLE)
    forms = sorted(e.form for e in entries)
    assert forms == ["SC 13D", "SC 13G/A"]
    # SC 13E3 must NOT slip through.
    assert all("13E" not in e.form for e in entries)


def test_parse_form_idx_pads_cik(mod):
    entries = mod.parse_form_idx(_FORM_IDX_SAMPLE)
    for e in entries:
        assert len(e.cik) == 10
        assert e.cik.isdigit()


_SGML_SAMPLE = """\
<SEC-HEADER>0000999999-25-000002.hdr.sgml : 20251002
ACCESSION NUMBER:		0000999999-25-000002
CONFORMED SUBMISSION TYPE:	SC 13D
PUBLIC DOCUMENT COUNT:		3
FILED AS OF DATE:		20251002

SUBJECT COMPANY:

	COMPANY DATA:
<COMPANY-CONFORMED-NAME>TARGET WIDGETS CORP
<CENTRAL-INDEX-KEY>0001234567
<CIK>0001234567
<STANDARD-INDUSTRIAL-CLASSIFICATION>3990

FILER:

	COMPANY DATA:
<COMPANY-CONFORMED-NAME>EXAMPLE FUND LP
<CIK>0000999999
<STATE-OF-INCORPORATION>DE
</SEC-HEADER>
... rest of filing ...
"""


def test_parse_sgml_header_extracts_subject_and_filer(mod):
    fields = mod.parse_sgml_header(_SGML_SAMPLE)
    assert fields.get("subject-company.COMPANY-CONFORMED-NAME") == "TARGET WIDGETS CORP"
    assert fields.get("subject-company.CIK") == "0001234567"
    assert fields.get("filer.COMPANY-CONFORMED-NAME") == "EXAMPLE FUND LP"
    assert fields.get("filer.CIK") == "0000999999"


def test_extract_edge(mod):
    fields = mod.parse_sgml_header(_SGML_SAMPLE)
    edge = mod.extract_edge_from_sgml(
        fields, accession="0000999999-25-000002", form="SC 13D", filed_date="2025-10-02"
    )
    assert edge is not None
    assert edge.filer_cik == "0000999999"
    assert edge.subject_cik == "0001234567"
    assert edge.filer_name == "EXAMPLE FUND LP"
    assert edge.subject_name == "TARGET WIDGETS CORP"


def test_extract_edge_returns_none_when_subject_missing(mod):
    # Filer present, subject absent.
    fields = {"filer.CIK": "0000999999"}
    edge = mod.extract_edge_from_sgml(fields, accession="x", form="SC 13D", filed_date="2025-10-02")
    assert edge is None


def test_accession_from_index_path(mod):
    p = "edgar/data/999999/0000999999-25-000002.txt"
    assert mod.accession_from_index_path(p) == "0000999999-25-000002"


def test_build_edges_with_injected_fetcher(mod):
    entries = mod.parse_form_idx(_FORM_IDX_SAMPLE)
    sgml_by_path = {entries[0].path: _SGML_SAMPLE}

    def fake_fetch(path: str) -> str:
        return sgml_by_path.get(path, "")  # second filing returns empty -> no edge

    edges = mod.build_edges(entries, fake_fetch)
    # Only the first filing produces a usable edge; the second's empty SGML
    # has no subject/filer.
    assert len(edges) == 1
    assert edges[0].subject_cik == "0001234567"


def test_build_edges_swallows_fetch_errors(mod):
    entries = mod.parse_form_idx(_FORM_IDX_SAMPLE)

    def failing_fetch(path: str) -> str:
        raise RuntimeError("network down")

    # Should not raise — failed fetches are logged + skipped.
    edges = mod.build_edges(entries, failing_fetch)
    assert edges == []


def test_edges_to_parquet_round_trip(mod, tmp_path: Path):
    edges = [
        mod.Filing13DGEdge(
            accession="0000999999-25-000002",
            form="SC 13D",
            filed_date="2025-10-02",
            filer_cik="0000999999",
            filer_name="EXAMPLE FUND LP",
            subject_cik="0001234567",
            subject_name="TARGET WIDGETS CORP",
        )
    ]
    out = tmp_path / "edges.parquet"
    mod.edges_to_parquet(edges, out)
    df = pl.read_parquet(out)
    assert df.height == 1
    assert df["filer_cik"][0] == "0000999999"
    assert set(df.columns) == {
        "accession",
        "form",
        "filed_date",
        "filer_cik",
        "filer_name",
        "subject_cik",
        "subject_name",
    }


def test_edges_to_parquet_empty_writes_schema(mod, tmp_path: Path):
    out = tmp_path / "empty.parquet"
    mod.edges_to_parquet([], out)
    df = pl.read_parquet(out)
    assert df.height == 0
    assert "filer_cik" in df.columns


def test_no_hardcoded_absolute_paths():
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    for token in ("C:\\Users", "/home/", "/Users/"):
        assert token not in src
