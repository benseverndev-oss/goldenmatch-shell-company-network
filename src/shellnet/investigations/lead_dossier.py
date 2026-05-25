"""Per-lead evidence dossier + verification gate (roadmap Phase 5, issue #160).

For each ranked wrongdoing lead, build a verifiable dossier: primary-source
deep links, the signals that produced it, a right-of-reply stub, and a
mandatory defamation/ethics checklist. Nothing should be published until the
checklist is fully ticked — :func:`is_cleared` enforces that programmatically.

Pure string-building so it is unit-testable without I/O.
"""

from __future__ import annotations

import re

__all__ = [
    "CHECKLIST",
    "companies_house_url",
    "opensanctions_url",
    "build_dossier",
    "is_cleared",
]

_CH = "https://find-and-update.company-information.service.gov.uk/company/"
_OS = "https://www.opensanctions.org/entities/"

# Every item must be ticked ("[x]") before a lead leaves the repo.
CHECKLIST: tuple[str, ...] = (
    "Company-level facts confirmed against Companies House (status, officers, filings)",
    "Sanctions / disqualification confirmed on the source register",
    "Identity disambiguated (name + DOB / address — not a namesake)",
    "Current control / role confirmed (not a stale or historical record)",
    "Claims separated into public-record fact vs inference",
    "Subject offered a right of reply",
)


def companies_house_url(company_id: str | None, *, psc: bool = False) -> str | None:
    if not company_id:
        return None
    number = company_id.upper().removeprefix("GB-COH-")
    url = f"{_CH}{number}"
    return f"{url}/persons-with-significant-control" if psc else url


def opensanctions_url(os_id: str | None) -> str | None:
    return f"{_OS}{os_id}" if os_id else None


def build_dossier(lead: dict) -> str:
    """Render a verification dossier markdown for one lead.

    ``lead`` is a row dict from the ranked queue; recognised keys include
    ``lead_id``, ``company_name``, ``wrongdoing_score``, ``active_status``,
    ``harm_category``, ``principal_name``, ``successor_name``,
    ``principal_os_id``, ``disqualified_name``, ``conduct``, and any signal
    columns.
    """
    cid = lead.get("lead_id")
    title = lead.get("company_name") or cid or "(unknown lead)"
    ch = companies_house_url(cid)
    ch_psc = companies_house_url(cid, psc=True)
    os_url = opensanctions_url(lead.get("principal_os_id"))

    lines = [
        f"# Lead dossier: {title}",
        "",
        "> **Lead, not a verdict.** Generated for human verification. Do not publish "
        "any identity-linked claim until every checklist box below is ticked.",
        "",
        "## At a glance",
        f"- **Company:** {title} (`{cid}`)",
        f"- **Wrongdoing score:** {lead.get('wrongdoing_score', '?')}",
        f"- **Live status:** {lead.get('active_status') or lead.get('active') or 'unknown'}",
        f"- **Harm category:** {lead.get('harm_category') or 'none'}",
    ]
    people = [
        p
        for p in (
            lead.get("principal_name"),
            lead.get("successor_name"),
            lead.get("disqualified_name"),
        )
        if p
    ]
    if people:
        lines.append(f"- **People:** {', '.join(dict.fromkeys(people))}")
    if lead.get("conduct"):
        lines.append(f"- **Cited conduct:** {lead['conduct']}")

    lines += ["", "## Primary sources (verify each)"]
    if ch:
        lines.append(f"- Companies House overview: {ch}")
        lines.append(f"- Persons with significant control: {ch_psc}")
    if os_url:
        lines.append(f"- OpenSanctions entity: {os_url}")
    lines.append("- Filing history / accounts: see the Companies House 'Filing history' tab")

    lines += ["", "## Why it surfaced (signals)"]
    for k, v in lead.items():
        if (
            k
            in {
                "evasion_timing",
                "regulatory_breach",
                "nominee_front",
                "sanctioned_parent",
                "bank_or_court_flag",
            }
            and v
        ):
            lines.append(f"- `{k}` = {v}")

    lines += ["", "## Right of reply (draft)", "", _right_of_reply(title)]

    lines += ["", "## Verification & defamation checklist"]
    lines += [f"- [ ] {item}" for item in CHECKLIST]
    lines += [
        "",
        "_Publishing is blocked until all boxes are `[x]`. "
        "Sanctions/disqualification/dissolution are public-record facts; "
        "intent and current control are not — confirm before asserting._",
        "",
    ]
    return "\n".join(lines)


def _right_of_reply(title: str) -> str:
    return (
        f"> We are examining public records concerning {title} and individuals "
        "connected to it, including company-control and sanctions/disqualification "
        "data. We would welcome any comment or correction before publication. "
        "[Insert specific questions and a response deadline.]"
    )


def is_cleared(dossier_markdown: str) -> bool:
    """True only if every checklist item is ticked (``[x]``) and none remain ``[ ]``."""
    if "[ ]" in dossier_markdown:
        return False
    ticked = len(re.findall(r"- \[x\]", dossier_markdown, flags=re.IGNORECASE))
    return ticked >= len(CHECKLIST)
