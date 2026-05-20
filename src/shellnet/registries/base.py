"""Base classes for national-registry adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field


class RegistryError(Exception):
    """Raised when a registry lookup fails in a way the caller should know
    about (HTTP non-200, malformed payload, missing required field).
    Recoverable misses (entity not found) return ``None`` instead."""


@dataclass(frozen=True)
class RegistryOfficer:
    """One officer/director/shareholder record. Mirrors the subset of FTM
    Directorship + Ownership we actually consume in the corroborate pack."""

    name: str
    role: str
    start_date: str = ""
    end_date: str = ""
    nationality: str = ""
    notes: str = ""


@dataclass(frozen=True)
class RegistryHit:
    """Normalised result of a registry lookup.

    Drops into the corroborate evidence ledger without reshape:
    ``RegistryHit.to_dict()`` is a flat JSON-serialisable dict.
    """

    registry: str  # e.g. "brreg_norway", "inpi_france"
    jurisdiction: str  # ISO 3166-1 alpha-2 lower-case
    identifier: str  # the official national registry ID looked up
    name: str
    status: str = ""
    incorporation_date: str = ""
    dissolution_date: str = ""
    address: str = ""
    legal_form: str = ""
    activity_code: str = ""  # NACE or equivalent
    activity_description: str = ""
    sourceUrl: str = ""  # noqa: N815 — matches FTM property name
    officers: list[RegistryOfficer] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["officers"] = [asdict(o) for o in self.officers]
        return d


class RegistryAdapter(ABC):
    """All concrete adapters implement :meth:`lookup` and expose a static
    ``REGISTRY`` and ``JURISDICTION`` identifier."""

    REGISTRY: str = ""
    JURISDICTION: str = ""

    @abstractmethod
    def lookup(self, identifier: str) -> RegistryHit | None:
        """Look up by the registry's native identifier. Returns ``None``
        when the entity isn't found; raises :class:`RegistryError` on
        transport failure."""

    @abstractmethod
    def search(self, query: str, *, limit: int = 10) -> list[RegistryHit]:
        """Name-based search. May return shallow hits (no officers); call
        :meth:`lookup` with the returned identifier to enrich."""
