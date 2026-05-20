"""Ireland Companies Registration Office (CRO) adapter — limited.

The CRO Open Data Portal at ``data.cro.ie`` (CKAN) ships the public
company directory as a flat CSV: company number, name, status,
type, company type, registered address, date registered, last
annual return date.

What's NOT in the open dataset:

* Director / secretary names
* Shareholder data
* Beneficial ownership (RBO — Register of Beneficial Ownership)

For those a paid CORE search (https://core.cro.ie/) or RBO portal
account is required. This adapter therefore returns a thin
``RegistryHit`` with company-level metadata only and leaves
``officers=[]``. Don't rely on Ireland coverage for officer-level
corroboration without a manual CORE check.

API: https://data.cro.ie/

(Currently a stub that hits the CKAN datastore API; if the dataset
isn't reachable, returns ``None``.)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from shellnet.registries.base import (
    RegistryAdapter,
    RegistryError,
    RegistryHit,
)

log = logging.getLogger(__name__)

_DATASET_URL = "https://data.cro.ie/api/3/action/datastore_search"


class CroIrelandAdapter(RegistryAdapter):
    REGISTRY = "cro_ireland"
    JURISDICTION = "ie"

    def __init__(self, client: httpx.Client | None = None, *, resource_id: str = "") -> None:
        self._client = client
        self._owns_client = client is None
        self._resource_id = resource_id  # CKAN resource id for the active dataset

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=20)
        try:
            r = client.get(_DATASET_URL, params=params, headers={"Accept": "application/json"})
            if r.status_code >= 400:
                raise RegistryError(f"cro ireland -> HTTP {r.status_code}")
            return r.json()
        finally:
            if self._owns_client:
                client.close()

    def lookup(self, identifier: str) -> RegistryHit | None:
        if not self._resource_id:
            log.info("cro_ireland: no CKAN resource_id configured; skipping lookup")
            return None
        co_num = identifier.strip().lstrip("0")
        if not co_num.isdigit():
            raise RegistryError(f"CRO identifier must be numeric, got {identifier!r}")
        payload = self._request(
            {"resource_id": self._resource_id, "filters": f'{{"COMPANY_NUM":"{co_num}"}}'}
        )
        records = (payload.get("result") or {}).get("records") or []
        if not records:
            return None
        r = records[0]
        return RegistryHit(
            registry=self.REGISTRY,
            jurisdiction=self.JURISDICTION,
            identifier=co_num,
            name=r.get("COMPANY_NAME") or "",
            status=r.get("COMPANY_STATUS_DESC") or r.get("COMPANY_STATUS") or "",
            incorporation_date=r.get("COMPANY_REG_DATE") or "",
            address=r.get("COMPANY_ADDRESS") or "",
            legal_form=r.get("COMPANY_TYPE_DESC") or "",
            sourceUrl=f"https://core.cro.ie/search/company/{co_num}",
            notes="CRO open data does not expose officers; manual CORE check required.",
        )

    def search(self, query: str, *, limit: int = 10) -> list[RegistryHit]:
        if not self._resource_id:
            return []
        payload = self._request(
            {"resource_id": self._resource_id, "q": query, "limit": min(limit, 50)}
        )
        out: list[RegistryHit] = []
        for r in ((payload.get("result") or {}).get("records") or [])[:limit]:
            out.append(
                RegistryHit(
                    registry=self.REGISTRY,
                    jurisdiction=self.JURISDICTION,
                    identifier=str(r.get("COMPANY_NUM", "")).lstrip("0"),
                    name=r.get("COMPANY_NAME") or "",
                    status=r.get("COMPANY_STATUS_DESC") or "",
                    sourceUrl=(
                        "https://core.cro.ie/search/company/"
                        + str(r.get("COMPANY_NUM", "")).lstrip("0")
                    ),
                )
            )
        return out
