"""Smoke tests for national registry adapters.

Uses httpx MockTransport so the tests don't hit live registry APIs.
"""

from __future__ import annotations

import json

import httpx
import pytest

from shellnet.registries import RegistryError
from shellnet.registries.brreg_norway import BrregNorwayAdapter
from shellnet.registries.cro_ireland import CroIrelandAdapter
from shellnet.registries.inpi_france import InpiFranceAdapter
from shellnet.registries.kvk_netherlands import KvkNetherlandsAdapter


def _mock_client(handler) -> httpx.Client:
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


# ---- Norway ----------------------------------------------------------------


def test_brreg_lookup_happy_path():
    payloads = {
        "/api/enheter/974760673": {
            "navn": "DET NORSKE TEATERET",
            "organisasjonsnummer": "974760673",
            "registreringsdatoEnhetsregisteret": "1995-01-01",
            "organisasjonsform": {"kode": "STI"},
            "forretningsadresse": {
                "adresse": ["Kristian IVs gate 8"],
                "postnummer": "0164",
                "poststed": "OSLO",
                "land": "Norge",
            },
            "naeringskode1": {"kode": "90.010", "beskrivelse": "Utøvende kunstnere"},
        },
        "/api/enheter/974760673/roller": {
            "rollegrupper": [
                {
                    "type": {"beskrivelse": "Styre og daglig leder"},
                    "roller": [
                        {
                            "type": {"beskrivelse": "Daglig leder"},
                            "person": {"navn": {"fornavn": "ALICE", "etternavn": "TESTBRUKER"}},
                        }
                    ],
                }
            ]
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        for key, body in payloads.items():
            if request.url.path.endswith(key):
                return httpx.Response(200, json=body)
        return httpx.Response(404)

    a = BrregNorwayAdapter(client=_mock_client(handler))
    hit = a.lookup("974760673")
    assert hit is not None
    assert hit.name == "DET NORSKE TEATERET"
    assert hit.identifier == "974760673"
    assert hit.address.startswith("Kristian IVs gate 8")
    assert hit.activity_code == "90.010"
    assert len(hit.officers) == 1
    assert hit.officers[0].name == "ALICE TESTBRUKER"
    assert hit.officers[0].role == "Daglig leder"
    assert hit.sourceUrl.endswith("974760673")


def test_brreg_lookup_rejects_bad_identifier():
    a = BrregNorwayAdapter(client=_mock_client(lambda r: httpx.Response(200)))
    with pytest.raises(RegistryError, match="9 digits"):
        a.lookup("abc")


def test_brreg_lookup_not_found_returns_none():
    handler = lambda r: httpx.Response(404)  # noqa: E731
    a = BrregNorwayAdapter(client=_mock_client(handler))
    assert a.lookup("999999999") is None


def test_brreg_handles_410_deleted():
    def handler(request):
        if "/roller" in request.url.path:
            return httpx.Response(404)
        return httpx.Response(
            410,
            json={
                "navn": "DELETED CO",
                "organisasjonsnummer": "123456789",
                "slettedato": "2020-01-01",
            },
        )

    a = BrregNorwayAdapter(client=_mock_client(handler))
    hit = a.lookup("123456789")
    assert hit is not None
    assert hit.status == "deleted"
    assert hit.dissolution_date == "2020-01-01"


def test_brreg_search():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "_embedded": {
                    "enheter": [
                        {"navn": "FOO AS", "organisasjonsnummer": "111111111"},
                        {"navn": "FOO HOLDING AS", "organisasjonsnummer": "222222222"},
                    ]
                }
            },
        )

    a = BrregNorwayAdapter(client=_mock_client(handler))
    hits = a.search("foo", limit=10)
    assert len(hits) == 2
    assert {h.identifier for h in hits} == {"111111111", "222222222"}


# ---- France ----------------------------------------------------------------


def test_inpi_lookup_happy_path():
    payload = {
        "results": [
            {
                "siren": "552120222",
                "nom_complet": "EDF",
                "nom_raison_sociale": "EDF",
                "date_creation": "1946-04-08",
                "etat_administratif": "A",
                "nature_juridique": "Société anonyme à conseil d'administration",
                "section_activite_principale": "Production et distribution d'électricité",
                "siege": {
                    "numero_voie": "22",
                    "type_voie": "AV",
                    "libelle_voie": "DE WAGRAM",
                    "code_postal": "75008",
                    "libelle_commune": "PARIS",
                    "activite_principale": "35.11Z",
                },
                "dirigeants": [
                    {
                        "prenoms": "Luc",
                        "nom": "Rémont",
                        "qualite": "PRÉSIDENT-DIRECTEUR GÉNÉRAL",
                        "annee_de_naissance": "1971",
                    }
                ],
            }
        ]
    }

    def handler(request):
        assert "552120222" in (request.url.params.get("q") or "")
        return httpx.Response(200, json=payload)

    a = InpiFranceAdapter(client=_mock_client(handler))
    hit = a.lookup("552120222")
    assert hit is not None
    assert hit.name == "EDF"
    assert hit.identifier == "552120222"
    assert hit.activity_code == "35.11Z"
    assert hit.officers[0].name == "Luc Rémont"
    assert "DOB 1971" in hit.officers[0].notes


def test_inpi_rejects_bad_siren():
    a = InpiFranceAdapter(client=_mock_client(lambda r: httpx.Response(200, json={"results": []})))
    with pytest.raises(RegistryError, match="9-digit SIREN"):
        a.lookup("123")


def test_inpi_search():
    payload = {
        "results": [
            {"siren": "552120222", "nom_complet": "EDF"},
            {"siren": "552081317", "nom_complet": "TOTAL ENERGIES SE"},
        ]
    }
    handler = lambda r: httpx.Response(200, json=payload)  # noqa: E731
    a = InpiFranceAdapter(client=_mock_client(handler))
    hits = a.search("energie", limit=10)
    assert len(hits) == 2


# ---- Ireland (stub-style behaviour) ----------------------------------------


def test_cro_no_resource_id_returns_none(caplog):
    a = CroIrelandAdapter(client=_mock_client(lambda r: httpx.Response(200, json={})))
    assert a.lookup("123456") is None
    assert a.search("foo") == []


def test_cro_with_resource_id():
    payload = {
        "result": {
            "records": [
                {
                    "COMPANY_NUM": "12345",
                    "COMPANY_NAME": "TEST IRELAND LTD",
                    "COMPANY_STATUS_DESC": "Normal",
                    "COMPANY_REG_DATE": "2000-01-01",
                    "COMPANY_ADDRESS": "1 Dame Street, Dublin 2",
                    "COMPANY_TYPE_DESC": "Private Company Limited By Shares",
                }
            ]
        }
    }
    handler = lambda r: httpx.Response(200, json=payload)  # noqa: E731
    a = CroIrelandAdapter(client=_mock_client(handler), resource_id="abc-123")
    hit = a.lookup("12345")
    assert hit is not None
    assert hit.name == "TEST IRELAND LTD"
    assert hit.officers == []  # CRO open data has no officers
    assert "manual CORE" in hit.notes


# ---- Netherlands (key-gated) ----------------------------------------------


def test_kvk_without_key_skips(caplog):
    a = KvkNetherlandsAdapter(api_key="")
    assert a.lookup("12345678") is None
    assert a.search("foo") == []


def test_kvk_with_key():
    payload = {"naam": "TEST NL B.V.", "formeleRegistratiedatum": "2010-01-01"}
    handler = lambda r: httpx.Response(200, json=payload)  # noqa: E731
    a = KvkNetherlandsAdapter(client=_mock_client(handler), api_key="dummy")
    hit = a.lookup("12345678")
    assert hit is not None
    assert hit.name == "TEST NL B.V."
    assert "paid handelsregister tier" in hit.notes


def test_kvk_rejects_bad_identifier():
    a = KvkNetherlandsAdapter(api_key="dummy")
    with pytest.raises(RegistryError, match="8-digit"):
        a.lookup("abc")


# ---- Shape contract --------------------------------------------------------


def test_registry_hit_serialises():
    a = BrregNorwayAdapter(
        client=_mock_client(
            lambda r: httpx.Response(
                200,
                json={
                    "navn": "X AS",
                    "organisasjonsnummer": "111111111",
                },
            )
        )
    )
    hit = a.lookup("111111111")
    assert hit is not None
    d = hit.to_dict()
    json.dumps(d)  # serialises clean
    assert d["registry"] == "brreg_norway"
    assert isinstance(d["officers"], list)
