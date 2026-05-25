"""Parse a Companies House overview page (roadmap Phase 3, issue #158).

The live status enrichment fetches the CH overview page via Firecrawl (CH isn't
in the network allowlist; Firecrawl is) and parses the markdown here. Kept pure
so it is testable without network.
"""

from __future__ import annotations

import re

__all__ = ["parse_ch_overview", "to_active_flag"]

# Statuses that still represent a live/ongoing target (the story isn't over).
_LIVE_STATUSES = {
    "active",
    "liquidation",
    "administration",
    "receivership",
    "voluntary arrangement",
}


def _grab(label: str, md: str) -> str | None:
    m = re.search(re.escape(label) + r"\s*\n+\s*([^\n]+)", md)
    return m.group(1).strip() if m else None


def _company_name(md: str) -> str | None:
    """The company name is the first H1 heading. The CH page's leading heading
    is the cookie-consent banner (an H2 ``## Cookies...``), so take the first
    single-``#`` line and skip ``##`` boilerplate."""
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip().strip("*").strip() or None
    return None


def parse_ch_overview(markdown: str) -> dict[str, object]:
    """Extract name / status / type / incorporation / SIC codes from CH markdown."""
    md = markdown or ""
    sics = re.findall(r"\b(\d{4,5})\b\s*[-–]\s*[A-Za-z]", md)
    # SIC codes appear in a "Nature of business (SIC)" block; fall back to any
    # 4-5 digit code immediately followed by a description dash.
    nature = re.search(r"Nature of business.*?(?=\n#|\Z)", md, re.S)
    if nature:
        sics = re.findall(r"\b(\d{4,5})\b", nature.group(0)) or sics
    return {
        "company_name": _company_name(md),
        "company_status": (_grab("Company status", md) or "").lower() or None,
        "company_type": _grab("Company type", md),
        "incorporated_on": _grab("Incorporated on", md),
        "sic_codes": sorted(set(sics)),
    }


def to_active_flag(status: str | None) -> bool | None:
    """Map a CH status string to the tri-state ``active`` flag.

    ``None`` when unknown; ``False`` only for terminal states (dissolved /
    closed). Liquidation/administration count as ``True`` — still a live,
    ongoing target.
    """
    if not status:
        return None
    s = status.lower()
    if "dissolved" in s or "closed" in s or "converted" in s:
        return False
    if any(live in s for live in _LIVE_STATUSES):
        return True
    return None
