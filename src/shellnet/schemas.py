"""Canonical Pydantic schemas for the unified company graph.

These are the *target* shapes — every source adapter maps its native records
into these models so downstream normalization, matching, and graph code can
stay source-agnostic. The `raw` field always carries the untouched source
record so we can re-derive fields if normalization changes.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourceName = Literal["icij", "opencorporates", "gleif", "opensanctions"]
RelationshipKind = Literal[
    "officer_of",  # person → company
    "intermediary_of",  # entity → company (ICIJ-specific)
    "shareholder_of",  # entity → company
    "parent_of",  # company → company (ownership / control)
    "registered_at",  # company → address
    "associated_with",  # generic, weak
    "same_as",  # cross-source identity hypothesis
]


class IdentifierRecord(BaseModel):
    """A registry/regulatory identifier attached to a company or person.

    Examples: LEI, OpenCorporates ID, jurisdiction-specific company number,
    sanctions list ID, ICIJ node id.
    """

    model_config = ConfigDict(extra="ignore")

    scheme: str  # "lei", "opencorporates", "company_number", "icij_node", "opensanctions", ...
    value: str
    jurisdiction: str | None = None  # ISO-3166-1 alpha-2 where it makes sense


class AddressRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source: SourceName
    source_id: str | None = None
    raw_text: str
    normalized_text: str | None = None
    country: str | None = None  # ISO-3166-1 alpha-2 if known
    locality: str | None = None
    region: str | None = None
    postal_code: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class CompanyEntity(BaseModel):
    """Canonical shape for any legal entity coming out of an adapter."""

    model_config = ConfigDict(extra="ignore")

    source: SourceName
    source_id: str
    name: str
    normalized_name: str | None = None
    jurisdiction: str | None = None  # ISO-3166-1 alpha-2 ("us", "ky", "vg", ...)
    incorporation_date: date | None = None
    dissolution_date: date | None = None
    status: str | None = None  # "active", "dissolved", "inactive", source-specific
    legal_form: str | None = None  # "ltd", "llc", "trust", source-specific
    addresses: list[AddressRecord] = Field(default_factory=list)
    identifiers: list[IdentifierRecord] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class PersonOrOfficer(BaseModel):
    """A natural person or non-corporate officer record."""

    model_config = ConfigDict(extra="ignore")

    source: SourceName
    source_id: str
    name: str
    normalized_name: str | None = None
    nationality: str | None = None
    addresses: list[AddressRecord] = Field(default_factory=list)
    identifiers: list[IdentifierRecord] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class RelationshipEdge(BaseModel):
    """A directed edge between two nodes in the unified graph.

    Node identifiers are the canonical ``"<source>:<source_id>"`` strings,
    so edges from different sources can co-exist without renumbering.
    """

    model_config = ConfigDict(extra="ignore")

    source: SourceName
    source_id: str | None = None  # provider's edge id if any
    src_node: str  # "<source>:<source_id>"
    dst_node: str  # "<source>:<source_id>"
    kind: RelationshipKind
    role: str | None = None  # provider-specific role label
    start_date: date | None = None
    end_date: date | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


def node_id(source: SourceName, source_id: str) -> str:
    """Build a stable cross-source node identifier."""
    return f"{source}:{source_id}"
