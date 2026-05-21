"""Probe OpenCorporates + Wayback Machine for a Maltese company.

Fallback when the Malta Business Registry public search isn't
accessible (account-gated, IP-blocked, or behind paywall). Produces
the same evidence-record YAML shape described in
``docs/investigations/rhea_marine_mbr_query_plan.md`` so the
investigator can drop the output straight into a bundle.

Two data sources:

1. **OpenCorporates** (``https://api.opencorporates.com/v0.4.8/``)
   mirrors MBR with a ~12-month lag. **API token required as of 2025**
   — free-tier signup at https://opencorporates.com/users/sign_up
   gives 200 requests/day with no card. Set the env var
   ``OPENCORPORATES_API_TOKEN`` before running. Returns JSON:
   registration number, current status, officers (current +
   historical), registered address.

2. **Wayback Machine** (``https://archive.org/wayback/available``)
   for prior snapshots of the MBR portal page if OpenCorporates is
   stale or empty. Falls back gracefully if Wayback has no snapshot.

This script does **not** access the paid MBR documents (Form K, Form
B). Those still require a human + a Malta Business Registry account.
What it does provide is the cheapest possible confirmation that the
entity exists, what its current status is, and whether the officer
roster materially differs from the ICIJ Paradise Papers vintage.

Outputs::

    data/investigations/<slug>/
        opencorporates_search.json     # raw API response
        opencorporates_company.json    # detail page if a match was picked
        wayback_snapshots.json         # available snapshot URLs (no fetch)
        evidence_record.yaml           # the per-entity verdict scaffold

Usage::

    uv run python scripts/probe_mbr_company.py \\
        --name "RHEA MARINE LTD" \\
        --slug rhea_marine \\
        --jurisdiction mt
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

log = logging.getLogger("probe_mbr_company")

_OC_SEARCH_URL = "https://api.opencorporates.com/v0.4.8/companies/search"
_OC_COMPANY_URL = "https://api.opencorporates.com/v0.4.8/companies/{juris}/{number}"
_WAYBACK_AVAILABLE_URL = "https://archive.org/wayback/available"

_DEFAULT_UA = "Ben Severn bsevern@mjhlifesciences.com (case-study research)"


@dataclass
class ProbeResult:
    """Aggregate of what we learned about one company."""

    name: str
    slug: str
    jurisdiction: str
    opencorporates_match: dict | None = None
    opencorporates_detail: dict | None = None
    wayback_snapshot_url: str | None = None
    error: str | None = None

    def to_evidence_record(self, icij_context: dict | None = None) -> str:
        """Render the YAML scaffold described in the query-plan doc.

        ``icij_context`` is the partial record the caller already
        knows from ICIJ — officers in Paradise Papers, address,
        date of incorporation. We embed it so the file is the full
        before/after picture in one place.
        """

        oc = self.opencorporates_detail or self.opencorporates_match or {}
        company = oc.get("company") if "company" in oc else oc
        company = company or {}
        officers = []
        for o in company.get("officers") or []:
            entry = o.get("officer") if "officer" in o else o
            officers.append(
                {
                    "name": entry.get("name", ""),
                    "position": entry.get("position", ""),
                    "start_date": entry.get("start_date", ""),
                    "end_date": entry.get("end_date", ""),
                }
            )

        record = {
            "entity": self.name,
            "slug": self.slug,
            "jurisdiction": self.jurisdiction,
            "opencorporates": {
                "found": company is not None and bool(company.get("name")),
                "registration_number": company.get("company_number", ""),
                "status": company.get("current_status", ""),
                "incorporation_date": company.get("incorporation_date", ""),
                "registered_address": company.get("registered_address_in_full", ""),
                "officers": officers,
                "url": company.get("opencorporates_url", ""),
            },
            "wayback_snapshot_url": self.wayback_snapshot_url,
            "icij_context": icij_context or {},
            "error": self.error,
            "verdict": "pending_review",
            "verdict_rationale": (
                "OpenCorporates + Wayback automation completed; human review of "
                "officer roster and registered-office continuity required to "
                "promote this from pending_review to confirmed_same / "
                "different_entity / ambiguous. See "
                "docs/investigations/rhea_marine_mbr_query_plan.md for the "
                "decision rules."
            ),
        }
        # YAML-ish, hand-rolled to avoid the yaml dep. Stable key order.
        return json.dumps(record, indent=2, sort_keys=True)


def _http_get_factory(
    user_agent: str,
) -> Callable[[str, dict | None], tuple[int, dict | None, bytes]]:
    """Return ``(url, params) -> (status, json_or_None, raw_body)``."""

    import httpx

    def fetcher(url: str, params: dict | None = None) -> tuple[int, dict | None, bytes]:
        with httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        ) as client:
            r = client.get(url, params=params)
            try:
                return r.status_code, r.json(), r.content
            except (json.JSONDecodeError, ValueError):
                return r.status_code, None, r.content

    return fetcher


def _params_with_token(params: dict) -> dict:
    """Attach OPENCORPORATES_API_TOKEN to params if the env var is set.

    OpenCorporates tightened access in 2025: even read-only search
    returns 401 without a token. Free-tier signup at
    https://opencorporates.com/users/sign_up (5 minutes, 200 requests
    per day, no card required).
    """
    token = os.environ.get("OPENCORPORATES_API_TOKEN")
    if token:
        params = dict(params)
        params["api_token"] = token
    return params


def search_opencorporates(
    name: str,
    *,
    jurisdiction: str = "mt",
    fetcher: Callable[[str, dict | None], tuple[int, dict | None, bytes]] | None = None,
) -> dict | None:
    """Run an OpenCorporates name search restricted to one jurisdiction.

    Returns the first match (highest-relevance), or None if no match.
    """

    if fetcher is None:
        fetcher = _http_get_factory(_DEFAULT_UA)
    status, payload, _ = fetcher(
        _OC_SEARCH_URL,
        _params_with_token({"q": name, "jurisdiction_code": jurisdiction, "order": "score"}),
    )
    if status == 401:
        log.warning(
            "OpenCorporates returned 401 for %s. Free-tier signup is required "
            "as of 2025: https://opencorporates.com/users/sign_up. After "
            "signup, set OPENCORPORATES_API_TOKEN and re-run.",
            name,
        )
        return None
    if status != 200 or not payload:
        log.warning("OpenCorporates search failed: status=%s for %s", status, name)
        return None
    results = (payload.get("results") or {}).get("companies") or []
    if not results:
        log.info("OpenCorporates: no match for %s in %s", name, jurisdiction)
        return None
    # Take the top match. The wrapper structure is ``[{"company": {...}}, ...]``.
    return results[0]


def fetch_opencorporates_detail(
    jurisdiction: str,
    company_number: str,
    *,
    fetcher: Callable[[str, dict | None], tuple[int, dict | None, bytes]] | None = None,
) -> dict | None:
    """Pull the full OpenCorporates company detail (officers history,
    filings list). Free tier rate-limit is generous for 1-2 lookups."""

    if fetcher is None:
        fetcher = _http_get_factory(_DEFAULT_UA)
    url = _OC_COMPANY_URL.format(juris=jurisdiction, number=company_number)
    status, payload, _ = fetcher(url, _params_with_token({}))
    if status != 200 or not payload:
        log.warning(
            "OpenCorporates detail failed: status=%s for %s/%s",
            status,
            jurisdiction,
            company_number,
        )
        return None
    return (payload.get("results") or {}).get("company")


def find_wayback_snapshot(
    target_url: str,
    *,
    fetcher: Callable[[str, dict | None], tuple[int, dict | None, bytes]] | None = None,
) -> str | None:
    """Ask the Wayback Machine whether it has a snapshot of ``target_url``.

    Returns the canonical archive URL or None.
    """

    if fetcher is None:
        fetcher = _http_get_factory(_DEFAULT_UA)
    status, payload, _ = fetcher(_WAYBACK_AVAILABLE_URL, {"url": target_url})
    if status != 200 or not payload:
        return None
    snap = (payload.get("archived_snapshots") or {}).get("closest") or {}
    return snap.get("url") or None


def probe(
    name: str,
    slug: str,
    *,
    jurisdiction: str = "mt",
    out_dir: Path | None = None,
    icij_context: dict | None = None,
    fetcher: Callable[[str, dict | None], tuple[int, dict | None, bytes]] | None = None,
    min_interval_s: float = 1.0,
) -> ProbeResult:
    """Run the full probe and write outputs under
    ``out_dir / slug / *``."""

    out_dir = out_dir or _REPO_ROOT / "data" / "investigations"
    target = out_dir / slug
    target.mkdir(parents=True, exist_ok=True)

    if fetcher is None:
        fetcher = _http_get_factory(_DEFAULT_UA)

    result = ProbeResult(name=name, slug=slug, jurisdiction=jurisdiction)

    # 1. OpenCorporates name search
    log.info("OpenCorporates name search: %s", name)
    match_wrap = search_opencorporates(name, jurisdiction=jurisdiction, fetcher=fetcher)
    (target / "opencorporates_search.json").write_text(
        json.dumps(match_wrap or {}, indent=2, sort_keys=True), encoding="utf-8"
    )
    if not match_wrap:
        result.error = "opencorporates: no match"
        (target / "evidence_record.yaml").write_text(
            result.to_evidence_record(icij_context=icij_context), encoding="utf-8"
        )
        return result
    company = match_wrap.get("company") if "company" in match_wrap else match_wrap
    result.opencorporates_match = company

    # 2. Detail fetch (officers history, registered address)
    time.sleep(min_interval_s)
    number = company.get("company_number")
    if number:
        log.info("OpenCorporates detail: %s/%s", jurisdiction, number)
        detail = fetch_opencorporates_detail(jurisdiction, number, fetcher=fetcher)
        if detail:
            result.opencorporates_detail = detail
            (target / "opencorporates_company.json").write_text(
                json.dumps(detail, indent=2, sort_keys=True), encoding="utf-8"
            )

    # 3. Wayback snapshot of the OpenCorporates page (best-effort)
    oc_url = company.get("opencorporates_url")
    if oc_url:
        time.sleep(min_interval_s)
        log.info("Wayback availability: %s", oc_url)
        result.wayback_snapshot_url = find_wayback_snapshot(oc_url, fetcher=fetcher)
        (target / "wayback_snapshots.json").write_text(
            json.dumps(
                {"target_url": oc_url, "snapshot_url": result.wayback_snapshot_url},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    (target / "evidence_record.yaml").write_text(
        result.to_evidence_record(icij_context=icij_context), encoding="utf-8"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--name",
        type=str,
        required=True,
        help='Company name to search (e.g. "RHEA MARINE LTD").',
    )
    p.add_argument(
        "--slug",
        type=str,
        required=True,
        help="Filesystem-safe slug for the output dir (e.g. rhea_marine).",
    )
    p.add_argument(
        "--jurisdiction",
        type=str,
        default="mt",
        help="OpenCorporates jurisdiction code. Default 'mt' (Malta).",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override the default data/investigations/ root.",
    )
    p.add_argument(
        "--icij-officers",
        type=str,
        default="",
        help=(
            "Pipe-separated list of officer names from ICIJ for context. "
            "Surfaces in the evidence_record so the reviewer can diff "
            "against the OpenCorporates roster."
        ),
    )
    p.add_argument(
        "--icij-address",
        type=str,
        default="",
        help="ICIJ registered office for context.",
    )
    p.add_argument(
        "--icij-incorporation",
        type=str,
        default="",
        help="ICIJ-reported incorporation date for context.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    icij_context: dict[str, object] = {}
    if args.icij_officers:
        icij_context["officers"] = [o.strip() for o in args.icij_officers.split("|") if o.strip()]
    if args.icij_address:
        icij_context["registered_address"] = args.icij_address
    if args.icij_incorporation:
        icij_context["incorporation_date"] = args.icij_incorporation

    result = probe(
        args.name,
        args.slug,
        jurisdiction=args.jurisdiction,
        out_dir=args.out_dir,
        icij_context=icij_context or None,
    )
    if result.error:
        log.warning("probe finished with error: %s", result.error)
    else:
        log.info("probe complete; see %s/%s/", args.out_dir or "data/investigations", args.slug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
