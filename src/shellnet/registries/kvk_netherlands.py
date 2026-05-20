"""Netherlands Kamer van Koophandel (KvK) adapter — limited free tier.

The KvK ``api.kvk.nl`` produces:

* **Free tier** (no contract required): basic company-name search,
  KvK number, trade names, place of business. **No officer or
  shareholder data.**
* **Paid tier** (contract + API key required): full structured
  UBO data, board members, signatories, financial summary.

For the structurally-interesting jurisdictions (officer reuse,
beneficial ownership), the paid tier is required. This adapter is
included so that the corroborate script can at least confirm that a
Dutch entity exists and surface the KvK number, then hand off to a
manual check.

Requires ``KVK_API_KEY`` env var when calling :meth:`lookup` or
:meth:`search`; without it, returns ``None`` / ``[]`` and logs a
notice.

API docs: https://developers.kvk.nl/
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from shellnet.registries.base import (
    RegistryAdapter,
    RegistryError,
    RegistryHit,
)

log = logging.getLogger(__name__)

_SEARCH_URL = "https://api.kvk.nl/api/v2/search/companies"
_LOOKUP_URL = "https://api.kvk.nl/api/v1/basisprofielen/{kvk_num}"


class KvkNetherlandsAdapter(RegistryAdapter):
    REGISTRY = "kvk_netherlands"
    JURISDICTION = "nl"

    def __init__(self, client: httpx.Client | None = None, *, api_key: str | None = None) -> None:
        self._client = client
        self._owns_client = client is None
        self._api_key = api_key or os.environ.get("KVK_API_KEY") or ""

    def _request(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if not self._api_key:
            log.info("kvk_netherlands: KVK_API_KEY not set; skipping live call")
            return None
        client = self._client or httpx.Client(timeout=20)
        try:
            r = client.get(
                url,
                params=params or {},
                headers={"Accept": "application/json", "apikey": self._api_key},
            )
            if r.status_code == 404:
                return None
            if r.status_code >= 400:
                raise RegistryError(f"kvk netherlands {url} -> HTTP {r.status_code}")
            return r.json()
        finally:
            if self._owns_client:
                client.close()

    def lookup(self, identifier: str) -> RegistryHit | None:
        kvk_num = identifier.strip().replace(" ", "")
        if not kvk_num.isdigit() or len(kvk_num) != 8:
            raise RegistryError(f"KvK identifier must be 8-digit number, got {identifier!r}")
        payload = self._request(_LOOKUP_URL.format(kvk_num=kvk_num))
        if not payload:
            return None
        return RegistryHit(
            registry=self.REGISTRY,
            jurisdiction=self.JURISDICTION,
            identifier=kvk_num,
            name=payload.get("naam") or "",
            status="active" if not payload.get("nonMailing") else "limited_mailing",
            incorporation_date=payload.get("formeleRegistratiedatum") or "",
            address="",  # paid tier only
            legal_form="",  # paid tier only
            sourceUrl=f"https://www.kvk.nl/zoeken/?source=alle&q={kvk_num}",
            notes=(
                "KvK basisprofiel only; officer/UBO/financial data requires "
                "the paid handelsregister tier."
            ),
        )

    def search(self, query: str, *, limit: int = 10) -> list[RegistryHit]:
        payload = self._request(_SEARCH_URL, {"q": query, "type": "rechtspersoon"})
        if not payload:
            return []
        out: list[RegistryHit] = []
        for r in (payload.get("resultaten") or [])[:limit]:
            kvk = str(r.get("kvkNummer", ""))
            out.append(
                RegistryHit(
                    registry=self.REGISTRY,
                    jurisdiction=self.JURISDICTION,
                    identifier=kvk,
                    name=r.get("handelsnaam") or "",
                    sourceUrl=f"https://www.kvk.nl/zoeken/?source=alle&q={kvk}",
                )
            )
        return out
