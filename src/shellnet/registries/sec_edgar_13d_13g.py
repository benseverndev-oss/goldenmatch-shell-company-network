"""SEC EDGAR Schedule 13D/13G adapter.

Schedule 13D/13G are mandatory SEC disclosures filed by anyone who
acquires beneficial ownership of more than 5% of a class of voting
securities of a US-listed public company. They name the filer
(beneficial owner) and the subject company, and disclose the number
of shares + percentage.

This adapter wraps SEC EDGAR's public full-text search to surface
these filings for a given company name or CIK, then parses the
filing index for filer + subject metadata.

API docs:
* https://efts.sec.gov/LATEST/search-index — full-text search (JSON)
* https://www.sec.gov/cgi-bin/browse-edgar — per-CIK filing list (HTML)
* https://data.sec.gov/submissions/CIK{CIK10}.json — per-CIK
  submissions index (JSON)

No API key required. SEC asks all users to send a descriptive
User-Agent identifying the application + a contact email; the
adapter sets one by default.

What's returned
---------------
A ``RegistryHit`` per matched **subject company**, with a synthetic
``officers`` list containing one entry per **filer** of a 13D/13G
on that company (role = ``Schedule 13D/G filer``, notes carry
filing date + accession). Beneficial ownership percentages live in
the filing body, which this MVP doesn't yet parse — surfacing the
filer/subject relationship is enough for cluster corroboration.

Coverage notes
--------------
* Only US-listed entities. Foreign-private-issuer 13D/G filings
  exist too but are rare.
* The XML parser for deeper structure (NumberOfShares, Percent,
  CUSIP, group membership) is a follow-up. Today's adapter returns
  the filer name + filing accession; the reviewer follows up with
  the actual filing URL when they want the percentages.
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

_FTS_URL = "https://efts.sec.gov/LATEST/search-index"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"

# Forms we care about. 13D/G plus amendments. 13F (institutional
# managers) and 13H (large trader) are different beasts and excluded.
_FORMS = "SC 13D,SC 13D/A,SC 13G,SC 13G/A"

_DEFAULT_USER_AGENT = (
    "GoldenMatch shell-company-network discovery pipeline "
    "https://github.com/benseverndev-oss/goldenmatch-shell-company-network "
    "ben@example.com"
)


class SecEdgar13DAdapter(RegistryAdapter):
    REGISTRY = "sec_edgar_13d_13g"
    JURISDICTION = "us"

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        user_agent: str | None = None,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._user_agent = user_agent or _DEFAULT_USER_AGENT

    def _headers(self) -> dict[str, str]:
        # SEC requires User-Agent. Accept-Encoding helps EDGAR identify
        # legitimate clients. Host is sometimes checked too.
        return {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=20)
        try:
            r = client.get(url, params=params or {}, headers=self._headers())
            if r.status_code == 404:
                return {}
            if r.status_code >= 400:
                raise RegistryError(f"sec edgar {url} -> HTTP {r.status_code}")
            return r.json()
        finally:
            if self._owns_client:
                client.close()

    # --- Two entry points: by CIK, or by company-name search ---------------

    def lookup(self, identifier: str) -> RegistryHit | None:
        """``identifier`` is a CIK (zero-padded or not)."""

        cik = identifier.strip().lstrip("0") or "0"
        if not cik.isdigit():
            raise RegistryError(f"CIK must be numeric, got {identifier!r}")
        cik10 = cik.zfill(10)

        # Submissions API gives us the canonical company name + every
        # filing they've made.
        sub = self._get(_SUBMISSIONS_URL.format(cik10=cik10))
        if not sub:
            return None
        recent = (sub.get("filings") or {}).get("recent") or {}
        forms = recent.get("form") or []
        accs = recent.get("accessionNumber") or []
        dates = recent.get("filingDate") or []
        primary_docs = recent.get("primaryDocument") or []

        # Filings on this CIK that ARE 13D/G filings (i.e. where this CIK
        # is the FILER, not the subject). We also want filings where this
        # CIK is the subject; the submissions index conveniently includes
        # both (EDGAR cross-references them).
        wanted = {"SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"}
        filings = []
        for i, form in enumerate(forms):
            if form in wanted:
                filings.append(
                    {
                        "form": form,
                        "filing_date": dates[i] if i < len(dates) else "",
                        "accession": accs[i] if i < len(accs) else "",
                        "primary_doc": (primary_docs[i] if i < len(primary_docs) else ""),
                    }
                )

        # Build a synthetic "officer" entry per filing — role labelled
        # so a downstream consumer knows this is filing metadata, not a
        # company officer.
        officers = [
            RegistryOfficer(
                name=f"Filing {f['accession']}",
                role=f"Schedule {f['form']} ({'subject' if 'subject' in f else 'filer'})",
                start_date=f["filing_date"],
                notes=(
                    f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                    f"{f['accession'].replace('-', '')}/{f['primary_doc'] or 'index.json'}"
                    if f["accession"]
                    else ""
                ),
            )
            for f in filings
        ]

        return RegistryHit(
            registry=self.REGISTRY,
            jurisdiction=self.JURISDICTION,
            identifier=cik,
            name=sub.get("name") or "",
            status="active" if not sub.get("formerNames") else "renamed",
            incorporation_date="",  # not in submissions API
            address=", ".join(
                p
                for p in (
                    (sub.get("addresses") or {}).get("business", {}).get("street1", ""),
                    (sub.get("addresses") or {}).get("business", {}).get("city", ""),
                    (sub.get("addresses") or {}).get("business", {}).get("stateOrCountry", ""),
                    (sub.get("addresses") or {}).get("business", {}).get("zipCode", ""),
                )
                if p
            ),
            legal_form=sub.get("entityType") or "",
            sourceUrl=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
            officers=officers,
            notes=(
                f"{len(filings)} Schedule 13D/G filings found for CIK {cik}. "
                "Each Schedule 13D/G filing names a >5% beneficial owner; "
                "the percentages live in the filing body, fetch the "
                "primary_doc URL to extract."
            ),
        )

    def search(self, query: str, *, limit: int = 10) -> list[RegistryHit]:
        """Full-text search across EDGAR 13D/G filings. Returns one
        ``RegistryHit`` per matched filing (subject company).

        Note: EDGAR's full-text-search endpoint returns FILINGS, not
        companies. We dedupe by CIK before returning.
        """

        payload = self._get(
            _FTS_URL,
            {
                "q": query,
                "forms": _FORMS,
                "hits": min(limit * 3, 100),  # over-fetch to allow CIK dedup
            },
        )
        hits = (payload.get("hits") or {}).get("hits") or []
        seen_ciks: set[str] = set()
        out: list[RegistryHit] = []
        for h in hits:
            src = h.get("_source") or {}
            adsh = h.get("_id") or src.get("adsh") or ""
            display = src.get("display_names") or []
            # display_names format: ["NAME /STATE/  (CIK 0000123456)", ...]
            for d in display:
                m = _extract_cik(d)
                if not m or m in seen_ciks:
                    continue
                seen_ciks.add(m)
                name = d.split("  (CIK")[0].strip()
                out.append(
                    RegistryHit(
                        registry=self.REGISTRY,
                        jurisdiction=self.JURISDICTION,
                        identifier=m.lstrip("0") or "0",
                        name=name,
                        sourceUrl=(
                            f"https://www.sec.gov/cgi-bin/browse-edgar?"
                            f"action=getcompany&CIK={m}&type=SC+13"
                        ),
                        notes=(
                            f"matched on accession {adsh}, "
                            f"form {src.get('form', '?')}, "
                            f"filed {src.get('file_date', '?')}"
                        ),
                    )
                )
                if len(out) >= limit:
                    return out
        return out


def _extract_cik(display_name: str) -> str:
    """Pull the 10-digit padded CIK out of an EDGAR display_names string.

    Display format example::

        "BOSTON CELTICS LIMITED PARTNERSHIP /DE/  (CIK 0001059969)"
    """

    idx = display_name.find("CIK ")
    if idx < 0:
        return ""
    tail = display_name[idx + 4 :].rstrip(") ").strip()
    return tail if tail.isdigit() else ""
