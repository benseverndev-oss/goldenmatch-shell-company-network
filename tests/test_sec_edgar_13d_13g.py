"""Smoke tests for SEC EDGAR Schedule 13D/13G adapter."""

from __future__ import annotations

import httpx
import pytest

from shellnet.registries import RegistryError
from shellnet.registries.sec_edgar_13d_13g import (
    SecEdgar13DAdapter,
    _extract_cik,
)


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_extract_cik():
    assert _extract_cik("BOSTON CELTICS LIMITED PARTNERSHIP /DE/  (CIK 0001059969)") == "0001059969"
    assert _extract_cik("HENLEY LIMITED PARTNERSHIP  (CIK 0001059969)") == "0001059969"
    assert _extract_cik("no cik here") == ""
    assert _extract_cik("(CIK abc)") == ""


def test_lookup_by_cik_returns_filings():
    payload = {
        "name": "BOSTON CELTICS LIMITED PARTNERSHIP",
        "entityType": "limited-partnership",
        "addresses": {
            "business": {"street1": "151 MERRIMAC", "city": "BOSTON", "stateOrCountry": "MA"}
        },
        "filings": {
            "recent": {
                "form": ["SC 13E3", "SC 13D", "SC 13G/A", "10-K"],
                "accessionNumber": [
                    "0000910647-03-000068",
                    "0000910647-02-000050",
                    "0000910647-99-000300",
                    "0000910647-02-000191",
                ],
                "filingDate": ["2003-02-14", "2002-05-01", "1999-06-30", "2002-09-27"],
                "primaryDocument": ["a.htm", "b.htm", "c.htm", "d.htm"],
            }
        },
    }

    def handler(request):
        return httpx.Response(200, json=payload)

    a = SecEdgar13DAdapter(client=_mock_client(handler))
    hit = a.lookup("1059969")
    assert hit is not None
    assert hit.name.startswith("BOSTON CELTICS")
    assert hit.identifier == "1059969"
    # Only the SC 13D and SC 13G/A should make it through; SC 13E3 + 10-K excluded.
    assert len(hit.officers) == 2
    forms = {o.role.split()[1] for o in hit.officers}
    assert forms == {"13D", "13G/A"} or all(
        f.startswith("Schedule") for f in (o.role for o in hit.officers)
    )
    assert all("sec.gov/Archives" in (o.notes or "") for o in hit.officers)


def test_lookup_unknown_cik_returns_none():
    handler = lambda r: httpx.Response(404)  # noqa: E731
    a = SecEdgar13DAdapter(client=_mock_client(handler))
    assert a.lookup("9999999") is None


def test_lookup_rejects_bad_identifier():
    a = SecEdgar13DAdapter(client=_mock_client(lambda r: httpx.Response(200)))
    with pytest.raises(RegistryError, match="numeric"):
        a.lookup("abc")


def test_search_dedupes_by_cik():
    payload = {
        "hits": {
            "hits": [
                {
                    "_id": "0000910647-03-000068",
                    "_source": {
                        "form": "SC 13E3",
                        "file_date": "2003-02-14",
                        "display_names": ["HENLEY LIMITED PARTNERSHIP  (CIK 0001059969)"],
                    },
                },
                {
                    "_id": "0000910647-02-000050",
                    "_source": {
                        "form": "SC 13D",
                        "file_date": "2002-05-01",
                        "display_names": ["HENLEY LIMITED PARTNERSHIP  (CIK 0001059969)"],
                    },
                },
                {
                    "_id": "0000910647-04-000111",
                    "_source": {
                        "form": "SC 13G",
                        "file_date": "2004-03-01",
                        "display_names": ["AMERICAN GOOSE CO  (CIK 0000999111)"],
                    },
                },
            ]
        }
    }
    handler = lambda r: httpx.Response(200, json=payload)  # noqa: E731
    a = SecEdgar13DAdapter(client=_mock_client(handler))
    hits = a.search("corvus capital", limit=10)
    # Two unique CIKs.
    assert len(hits) == 2
    assert {h.identifier for h in hits} == {"1059969", "999111"}


def test_search_respects_limit():
    payload = {
        "hits": {
            "hits": [
                {
                    "_id": f"acc-{i}",
                    "_source": {
                        "form": "SC 13D",
                        "file_date": "2023-01-01",
                        "display_names": [f"COMPANY {i}  (CIK 000000{i:04d})"],
                    },
                }
                for i in range(10)
            ]
        }
    }
    handler = lambda r: httpx.Response(200, json=payload)  # noqa: E731
    a = SecEdgar13DAdapter(client=_mock_client(handler))
    hits = a.search("anything", limit=3)
    assert len(hits) == 3


def test_user_agent_is_set():
    seen = {}

    def handler(request):
        seen["ua"] = request.headers.get("User-Agent")
        return httpx.Response(404)

    a = SecEdgar13DAdapter(client=_mock_client(handler))
    a.lookup("123")
    assert "goldenmatch" in seen["ua"].lower()
