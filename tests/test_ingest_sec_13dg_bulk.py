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


# ---------------------------------------------------------------------------
# Real-corpus regression fixtures. These are actual SCHEDULE 13D / 13G
# headers pulled from EDGAR's 2025 Q4 full-index in the Phase 9 fix.
# The original synthetic fixture used the legacy bracketed format and
# passed unit tests while extracting zero edges from real filings; these
# fixtures lock the parser to the modern plain-text format.
# ---------------------------------------------------------------------------

FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "sec_13dg"


def test_real_corpus_schedule_13d(mod):
    """Live EDGAR SCHEDULE 13D filing: Catsimatidis Jr -> 1stdibs.com."""
    text = (FIXTURES_DIR / "schedule_13d.txt").read_text(encoding="utf-8")
    fields = mod.parse_sgml_header(text)
    # Subject side
    assert fields.get("subject-company.COMPANY CONFORMED NAME") == "1stdibs.com, Inc."
    assert fields.get("subject-company.CENTRAL INDEX KEY") == "0001600641"
    # Filer side uses the modern FILED BY: marker, not FILER:
    assert fields.get("filed-by.COMPANY CONFORMED NAME") == "Catsimatidis John A. Jr"
    assert fields.get("filed-by.CENTRAL INDEX KEY") == "0002022852"

    edge = mod.extract_edge_from_sgml(
        fields, accession="0001104659-25-115101", form="SCHEDULE 13D", filed_date="2025-11-21"
    )
    assert edge is not None
    assert edge.filer_cik == "0002022852"
    assert edge.subject_cik == "0001600641"
    assert "Catsimatidis" in edge.filer_name
    assert "1stdibs" in edge.subject_name


def test_real_corpus_schedule_13g(mod):
    """Live EDGAR SCHEDULE 13G: Newtyn Management -> 1-800-Flowers."""
    text = (FIXTURES_DIR / "schedule_13g.txt").read_text(encoding="utf-8")
    fields = mod.parse_sgml_header(text)
    edge = mod.extract_edge_from_sgml(
        fields, accession="0001493152-25-021595", form="SCHEDULE 13G", filed_date="2025-12-15"
    )
    assert edge is not None
    assert edge.filer_cik == "0001569241"
    assert edge.subject_cik == "0001084869"


def test_phase13_year_quarter_parser(mod):
    """The --year-quarter argparse type accepts valid 'YYYY/Q' and rejects junk."""
    import argparse

    assert mod._parse_year_quarter("2025/4") == (2025, 4)
    assert mod._parse_year_quarter("2024/1") == (2024, 1)
    with pytest.raises(argparse.ArgumentTypeError):
        mod._parse_year_quarter("2025-4")
    with pytest.raises(argparse.ArgumentTypeError):
        mod._parse_year_quarter("2025/5")  # quarter out of range
    with pytest.raises(argparse.ArgumentTypeError):
        mod._parse_year_quarter("not/a/spec")


def test_phase13_main_iterates_multiple_quarters(mod, tmp_path, monkeypatch):
    """main() with --year-quarter 2025/1 2025/2 must call fetch_idx twice
    and concatenate edges from both quarters into the output parquet."""
    import polars as pl

    calls: list[tuple[int, int]] = []
    canned_idx = (
        " Form Type      Company Name                                                  CIK         Date Filed  File Name\n"
        + "-" * 130
        + "\n"
        "SCHEDULE 13D     Subject Q1                                                    1111111     2025-02-01  edgar/data/1111111/A1.txt\n"
        "SCHEDULE 13D     Subject Q2                                                    2222222     2025-05-01  edgar/data/2222222/A2.txt\n"
    )

    def fake_idx(year: int, quarter: int) -> str:
        calls.append((year, quarter))
        return canned_idx

    sgml_template = (
        "<SEC-HEADER>\n"
        "ACCESSION NUMBER:\t\t{acc}\n"
        "SUBJECT COMPANY:\t\n"
        "\tCOMPANY DATA:\t\n"
        "\t\tCOMPANY CONFORMED NAME:\t\t\tTarget Inc\n"
        "\t\tCENTRAL INDEX KEY:\t\t\t{subject}\n"
        "FILED BY:\t\n"
        "\tCOMPANY DATA:\t\n"
        "\t\tCOMPANY CONFORMED NAME:\t\t\tFiler LLC\n"
        "\t\tCENTRAL INDEX KEY:\t\t\t{filer}\n"
        "</SEC-HEADER>\n"
    )

    def fake_filing(path: str) -> str:
        # accession derived from the path
        acc = mod.accession_from_index_path(path)
        # CIK based on path so each call produces distinct edges
        cik = path.split("/")[-2]
        return sgml_template.format(acc=acc, subject=cik.zfill(10), filer="0009999999")

    monkeypatch.setattr(mod, "_http_fetcher", lambda ua: (fake_idx, fake_filing))

    out = tmp_path / "edges.parquet"
    rc = mod.main(
        ["--year-quarter", "2025/1", "2025/2", "--out", str(out), "--user-agent", "test test@test"]
    )
    assert rc == 0
    assert calls == [(2025, 1), (2025, 2)]
    df = pl.read_parquet(out)
    assert df.height == 2  # one edge per quarter
    accessions = set(df["accession"].to_list())
    assert accessions == {"A1", "A2"}


def test_phase13_legacy_year_quarter_flags_still_work(mod, tmp_path, monkeypatch):
    """Backwards compat: --year 2025 --quarter 4 still ingests one quarter."""
    import polars as pl

    calls: list[tuple[int, int]] = []

    def fake_idx(year: int, quarter: int) -> str:
        calls.append((year, quarter))
        return ""  # empty index -> no entries

    monkeypatch.setattr(mod, "_http_fetcher", lambda ua: (fake_idx, lambda p: ""))
    out = tmp_path / "edges.parquet"
    rc = mod.main(
        ["--year", "2025", "--quarter", "4", "--out", str(out), "--user-agent", "test test@test"]
    )
    assert rc == 0
    assert calls == [(2025, 4)]
    # Empty parquet written with correct schema.
    df = pl.read_parquet(out)
    assert df.height == 0
    assert "filer_cik" in df.columns


def test_phase13_dedupes_accessions_across_quarters(mod, tmp_path, monkeypatch):
    """If the same accession appears in two quarters' indexes (e.g. an
    amendment straddles a quarter boundary), it surfaces once in the
    output."""
    import polars as pl

    idx_q1 = (
        " Form Type      Company Name                                                  CIK         Date Filed  File Name\n"
        + "-" * 130
        + "\n"
        "SCHEDULE 13D     Same Filing                                                   1111111     2025-03-30  edgar/data/1111111/SAME.txt\n"
    )
    idx_q2 = (
        " Form Type      Company Name                                                  CIK         Date Filed  File Name\n"
        + "-" * 130
        + "\n"
        "SCHEDULE 13D     Same Filing                                                   1111111     2025-04-01  edgar/data/1111111/SAME.txt\n"
    )
    sgml = (
        "<SEC-HEADER>\n"
        "SUBJECT COMPANY:\t\n"
        "\tCOMPANY DATA:\t\n"
        "\t\tCOMPANY CONFORMED NAME:\t\t\tTarget\n"
        "\t\tCENTRAL INDEX KEY:\t\t\t0001111111\n"
        "FILED BY:\t\n"
        "\tCOMPANY DATA:\t\n"
        "\t\tCOMPANY CONFORMED NAME:\t\t\tFiler\n"
        "\t\tCENTRAL INDEX KEY:\t\t\t0009999999\n"
        "</SEC-HEADER>\n"
    )

    def fake_idx(year: int, quarter: int) -> str:
        return idx_q1 if quarter == 1 else idx_q2

    monkeypatch.setattr(mod, "_http_fetcher", lambda ua: (fake_idx, lambda p: sgml))
    out = tmp_path / "edges.parquet"
    rc = mod.main(
        [
            "--year-quarter",
            "2025/1",
            "2025/2",
            "--out",
            str(out),
            "--user-agent",
            "test test@test",
        ]
    )
    assert rc == 0
    df = pl.read_parquet(out)
    assert df.height == 1, f"expected dedup to one edge, got {df.height}"


def test_form_idx_accepts_schedule_13d_and_13g(mod):
    """SEC renamed forms from 'SC 13D' / 'SC 13G' to 'SCHEDULE 13D' / 'SCHEDULE 13G'.
    The parser must match the new names AND continue rejecting SC 13E3 etc."""
    sample = (
        " Form Type      Company Name                                                  CIK         Date Filed  File Name\n"
        "-" * 130 + "\n"
        "SCHEDULE 13D     1stdibs.com, Inc.                                             1600641     2025-11-21  edgar/data/1600641/0001104659-25-115101.txt\n"
        "SCHEDULE 13G/A   1 800 FLOWERS COM INC                                         1084869     2025-12-15  edgar/data/1084869/0001493152-25-021598.txt\n"
        "SC 13E3          5&2 Studios, Inc.                                             1733443     2025-12-31  edgar/data/1733443/0001104659-25-125664.txt\n"
        "10-K             ACME INC                                                      0000001     2025-10-01  edgar/data/1/0000001.txt\n"
    )
    entries = mod.parse_form_idx(sample)
    forms = sorted(e.form for e in entries)
    assert forms == ["SCHEDULE 13D", "SCHEDULE 13G/A"]
    # SC 13E3 must NOT slip through (it has the "SC 13" substring).
    assert all("13E" not in e.form for e in entries)
