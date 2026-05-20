"""France INPI / RNCS adapter.

The Institut national de la propriété industrielle (INPI) publishes
the Registre National du Commerce et des Sociétés (RNCS) at
``data.inpi.fr``. The public API at ``api.recherche-entreprises.fr``
is a free downstream that exposes the same data with no auth.

Identifier: 9-digit SIREN.

This adapter wraps ``api.recherche-entreprises.fr`` (Etalab project,
public-domain) which is more permissive than the INPI portal itself.

API docs: https://recherche-entreprises.api.gouv.fr/
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

_LOOKUP_URL = "https://recherche-entreprises.api.gouv.fr/search"


class InpiFranceAdapter(RegistryAdapter):
    REGISTRY = "inpi_france"
    JURISDICTION = "fr"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=20)
        try:
            r = client.get(_LOOKUP_URL, params=params, headers={"Accept": "application/json"})
            if r.status_code >= 400:
                raise RegistryError(f"inpi france -> HTTP {r.status_code}")
            return r.json()
        finally:
            if self._owns_client:
                client.close()

    def _hit_from_result(self, result: dict[str, Any]) -> RegistryHit:
        siren = result.get("siren") or ""
        siege = result.get("siege") or {}
        nature = result.get("nature_juridique") or ""

        officers: list[RegistryOfficer] = []
        for d in result.get("dirigeants") or []:
            given = (d.get("prenoms") or "").strip()
            family = (d.get("nom") or "").strip()
            corp = (d.get("denomination") or "").strip()
            display = corp or " ".join(p for p in (given, family) if p)
            if not display:
                continue
            officers.append(
                RegistryOfficer(
                    name=display,
                    role=d.get("qualite") or "",
                    nationality=d.get("nationalite") or "",
                    notes=(
                        f"DOB {d.get('annee_de_naissance', '?')}"
                        if d.get("annee_de_naissance")
                        else ""
                    ),
                )
            )

        addr = ", ".join(
            p
            for p in (
                siege.get("numero_voie", ""),
                siege.get("type_voie", ""),
                siege.get("libelle_voie", ""),
                siege.get("code_postal", ""),
                siege.get("libelle_commune", ""),
                siege.get("libelle_pays_etranger", "France" if siege else ""),
            )
            if p
        )

        return RegistryHit(
            registry=self.REGISTRY,
            jurisdiction=self.JURISDICTION,
            identifier=siren,
            name=result.get("nom_complet") or result.get("nom_raison_sociale") or "",
            status="active" if result.get("etat_administratif") == "A" else "ceased",
            incorporation_date=result.get("date_creation") or "",
            dissolution_date=result.get("date_cessation") or "",
            address=addr,
            legal_form=nature,
            activity_code=siege.get("activite_principale", "")
            or result.get("activite_principale", ""),
            activity_description=result.get("section_activite_principale", "") or "",
            sourceUrl=f"https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}",
            officers=officers,
        )

    def lookup(self, identifier: str) -> RegistryHit | None:
        siren = identifier.strip().replace(" ", "")
        if not siren.isdigit() or len(siren) != 9:
            raise RegistryError(f"INPI identifier must be 9-digit SIREN, got {identifier!r}")
        payload = self._request({"q": siren})
        results = payload.get("results") or []
        for r in results:
            if (r.get("siren") or "").lstrip("0") == siren.lstrip("0"):
                return self._hit_from_result(r)
        return None

    def search(self, query: str, *, limit: int = 10) -> list[RegistryHit]:
        payload = self._request({"q": query, "per_page": min(limit, 25)})
        return [self._hit_from_result(r) for r in (payload.get("results") or [])[:limit]]
