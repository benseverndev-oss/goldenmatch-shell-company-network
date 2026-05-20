"""Norway Brønnøysundregistrene (BRREG) adapter.

The Enhetsregisteret API at ``data.brreg.no`` is open, NLOD-licensed,
and requires no API key. It returns full entity profiles including
official name, registered address, organisation form, NACE activity
code, status, plus the named role-holders (CEO/daglig leder, board
chair, board members, deputy members, signatures).

API docs: https://data.brreg.no/enhetsregisteret/oppslag/

Identifier shape: 9-digit organisasjonsnummer (e.g. ``974760673``).

Coverage notes:
* Returns 410 when an entity has been deleted from the register
  ("slettet"). We translate that to ``status="deleted"`` on the hit
  rather than treating it as a transport error, because the
  deletion itself is data the reviewer wants.
* Personal data on board members is restricted in the public API —
  the role-holder lookup returns names but not DOBs or addresses.
* Beneficial ownership is published separately at the BRØST
  registry (Reelle rettighetshavere); not in this adapter yet.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from shellnet.registries.base import (
    RegistryAdapter,
    RegistryError,
    RegistryHit,
    RegistryOfficer,
)

log = logging.getLogger(__name__)

_ENHET_URL = "https://data.brreg.no/enhetsregisteret/api/enheter/{org_id}"
_ROLES_URL = "https://data.brreg.no/enhetsregisteret/api/enheter/{org_id}/roller"
_SEARCH_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"


class BrregNorwayAdapter(RegistryAdapter):
    REGISTRY = "brreg_norway"
    JURISDICTION = "no"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    def _get(self, url: str) -> dict[str, Any] | None:
        client = self._client or httpx.Client(timeout=20)
        try:
            r = client.get(url, headers={"Accept": "application/json"})
            if r.status_code == 404:
                return None
            if r.status_code == 410:
                # Gone — entity has been deleted from the register.
                return {"_brreg_deleted": True, **(r.json() if r.content else {})}
            if r.status_code >= 400:
                raise RegistryError(f"brreg {url} -> HTTP {r.status_code}")
            return r.json()
        finally:
            if self._owns_client:
                client.close()

    def lookup(self, identifier: str) -> RegistryHit | None:
        org_id = identifier.strip().replace(" ", "")
        if not org_id.isdigit() or len(org_id) != 9:
            raise RegistryError(f"BRREG identifier must be 9 digits, got {identifier!r}")

        entity = self._get(_ENHET_URL.format(org_id=org_id))
        if entity is None:
            return None

        deleted = bool(entity.get("_brreg_deleted") or entity.get("slettedato"))
        status = (
            "deleted"
            if deleted
            else "active"
            if not entity.get("konkurs") and not entity.get("underAvvikling")
            else ("bankrupt" if entity.get("konkurs") else "in_liquidation")
        )

        address_obj = entity.get("forretningsadresse") or {}
        address_parts = [
            *(address_obj.get("adresse") or []),
            address_obj.get("postnummer", ""),
            address_obj.get("poststed", ""),
            address_obj.get("land", ""),
        ]
        address = ", ".join(p for p in address_parts if p)

        nace = entity.get("naeringskode1") or {}
        legal_form = (entity.get("organisasjonsform") or {}).get("kode", "") or ""

        officers: list[RegistryOfficer] = []
        try:
            roles_payload = self._get(_ROLES_URL.format(org_id=org_id))
        except RegistryError as exc:
            log.warning("brreg roles fetch failed for %s: %s", org_id, exc)
            roles_payload = None

        for group in (roles_payload or {}).get("rollegrupper") or []:
            role_type = (group.get("type") or {}).get("beskrivelse", "")
            for person in group.get("roller") or []:
                role_desc = (person.get("type") or {}).get("beskrivelse", role_type)
                pname = person.get("person") or {}
                given = (pname.get("navn") or {}).get("fornavn", "")
                family = (pname.get("navn") or {}).get("etternavn", "")
                # Sometimes the role-holder is an organisation; fall back
                # to organisasjon.navn[0] in that case.
                if not given and not family:
                    org = person.get("organisasjon") or {}
                    name = " ".join(org.get("navn", []) or []).strip()
                else:
                    name = " ".join(p for p in (given, family) if p).strip()
                if not name:
                    continue
                officers.append(
                    RegistryOfficer(
                        name=name,
                        role=role_desc,
                        start_date=person.get("fratraadt") and "" or "",
                        nationality="",  # BRREG public API doesn't expose nationality
                    )
                )

        return RegistryHit(
            registry=self.REGISTRY,
            jurisdiction=self.JURISDICTION,
            identifier=org_id,
            name=entity.get("navn") or "",
            status=status,
            incorporation_date=entity.get("registreringsdatoEnhetsregisteret") or "",
            dissolution_date=entity.get("slettedato") or "",
            address=address,
            legal_form=legal_form,
            activity_code=nace.get("kode", "") or "",
            activity_description=nace.get("beskrivelse", "") or "",
            sourceUrl=f"https://virksomhet.brreg.no/nb/oppslag/enheter/{org_id}",
            officers=officers,
        )

    def search(self, query: str, *, limit: int = 10) -> list[RegistryHit]:
        client = self._client or httpx.Client(timeout=20)
        try:
            r = client.get(
                _SEARCH_URL,
                params={"navn": query, "size": min(limit, 50)},
                headers={"Accept": "application/json"},
            )
            if r.status_code >= 400:
                raise RegistryError(f"brreg search -> HTTP {r.status_code}")
            payload = r.json()
        finally:
            if self._owns_client:
                client.close()

        out: list[RegistryHit] = []
        for ent in (payload.get("_embedded") or {}).get("enheter", [])[:limit]:
            out.append(
                RegistryHit(
                    registry=self.REGISTRY,
                    jurisdiction=self.JURISDICTION,
                    identifier=str(ent.get("organisasjonsnummer", "")),
                    name=ent.get("navn") or "",
                    status="active",
                    sourceUrl=f"https://virksomhet.brreg.no/nb/oppslag/enheter/{ent.get('organisasjonsnummer')}",
                )
            )
        return out
