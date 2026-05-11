from datetime import date

import pytest
from pydantic import ValidationError

from shellnet.schemas import (
    AddressRecord,
    CompanyEntity,
    IdentifierRecord,
    PersonOrOfficer,
    RelationshipEdge,
    node_id,
)


def test_node_id_format() -> None:
    assert node_id("icij", "10000001") == "icij:10000001"


def test_company_entity_minimal() -> None:
    c = CompanyEntity(source="icij", source_id="abc", name="Foo Ltd")
    assert c.source == "icij"
    assert c.addresses == []
    assert c.identifiers == []


def test_company_entity_with_nested() -> None:
    c = CompanyEntity(
        source="opencorporates",
        source_id="gb/1234567",
        name="Foo Ltd",
        normalized_name="foo",
        jurisdiction="gb",
        incorporation_date=date(2003, 4, 10),
        addresses=[
            AddressRecord(source="opencorporates", raw_text="10 Downing", country="gb")
        ],
        identifiers=[
            IdentifierRecord(scheme="company_number", value="1234567", jurisdiction="gb")
        ],
    )
    assert c.identifiers[0].scheme == "company_number"
    assert c.addresses[0].country == "gb"


def test_company_entity_rejects_unknown_source() -> None:
    with pytest.raises(ValidationError):
        CompanyEntity(source="not_a_source", source_id="x", name="x")  # type: ignore[arg-type]


def test_relationship_edge_kind_is_constrained() -> None:
    e = RelationshipEdge(
        source="icij",
        src_node="icij:1",
        dst_node="icij:2",
        kind="officer_of",
    )
    assert e.kind == "officer_of"
    with pytest.raises(ValidationError):
        RelationshipEdge(
            source="icij",
            src_node="icij:1",
            dst_node="icij:2",
            kind="not_a_kind",  # type: ignore[arg-type]
        )


def test_person_record() -> None:
    p = PersonOrOfficer(source="icij", source_id="off-1", name="Jane Doe")
    assert p.name == "Jane Doe"
