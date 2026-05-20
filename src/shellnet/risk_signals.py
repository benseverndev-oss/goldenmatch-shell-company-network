"""AMLA Customer-Due-Diligence risk signals.

A focused subset of the risk-factor catalogue from the EU AMLA CDD
Regulatory Technical Standards (the draft RTS supplementing Reg.
(EU) 2024/1624). The full RTS catalogues dozens of risk factors;
this module covers the ones the GoldenMatch pipeline can actually
evidence from its own outputs (graph clusters, BODS edges, registry
hits, cross-jurisdiction twins).

A risk signal is a *finding*, not a verdict — every signal carries an
explicit rationale string that should be reproduced verbatim in any
downstream report. Severity is one of ``low`` / ``medium`` / ``high``
and maps to the AMLA "standard" / "enhanced" CDD escalation gates.

Scope: this module reports indicators that fit on the GoldenMatch
evidence base (corporate-structure, geography, name-lineage). It
deliberately does NOT make PEP findings, sanction findings, or
criminal-conduct findings — those require dedicated lookups and live
in other modules.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["low", "medium", "high"]


# AMLA RTS / FATF "increased risk" jurisdictions (illustrative subset).
# Source: FATF "Jurisdictions under Increased Monitoring" + "High-Risk
# Jurisdictions subject to a Call for Action" lists. Codes are ISO-3166
# alpha-2. The list rotates — keep this short and authoritative; deeper
# checks should go through a live FATF feed.
_HIGH_RISK_JURISDICTIONS: frozenset[str] = frozenset(
    {
        "ir",  # Iran (call for action)
        "kp",  # North Korea (call for action)
        "mm",  # Myanmar (call for action)
        "sy",  # Syria
        # increased-monitoring (as of FATF Oct-2025 plenary, illustrative):
        "ng",
        "za",
        "ph",
        "tr",
        "vn",
        "yem",
        "ye",
    }
)

# Jurisdictions commonly used as shell-company conduits. These are NOT
# "high risk" per AMLA, but show up disproportionately in structuring
# chains. AMLA RTS Art. 4(2)(c) calls this "complex ownership structures
# involving jurisdictions with low transparency requirements".
_OPACITY_JURISDICTIONS: frozenset[str] = frozenset(
    {"vg", "ky", "bs", "pa", "mt", "cy", "lu", "li", "im", "je", "gg", "bm", "ai", "tc"}
)


@dataclass(frozen=True)
class RiskSignal:
    """A single AMLA-RTS-style finding.

    Attributes:
        code: stable short identifier (e.g. ``geo.high-risk-juris``).
        severity: ``low`` / ``medium`` / ``high``.
        rationale: human-readable evidence string. Always include the
            specific facts that triggered the signal (entity uid, juris,
            counts) so the finding is auditable.
        amla_ref: optional pointer to the AMLA RTS article or FATF
            recommendation that motivates this signal.
        evidence: optional structured evidence payload for downstream
            consumers (CSV columns, JSON fields).
    """

    code: str
    severity: Severity
    rationale: str
    amla_ref: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Per-entity signals
# ---------------------------------------------------------------------------


def evaluate_entity(entity: dict[str, Any]) -> list[RiskSignal]:
    """Return AMLA-RTS-style risk signals for a single entity row.

    The entity dict is expected to carry (best-effort):
      - ``uid``: stable id
      - ``name``: company name
      - ``jurisdiction``: ISO-3166 alpha-2 (lowercase)
      - ``has_employees``: bool, if known
      - ``has_website``: bool, if known
      - ``incorporated_date``: ISO date string, if known
    Missing fields just suppress the corresponding signal.
    """

    signals: list[RiskSignal] = []
    juris = (entity.get("jurisdiction") or "").lower().strip()

    if juris in _HIGH_RISK_JURISDICTIONS:
        signals.append(
            RiskSignal(
                code="geo.high-risk-juris",
                severity="high",
                rationale=(
                    f"Entity {entity.get('uid', '?')} ({entity.get('name', '?')}) is "
                    f"incorporated in {juris.upper()}, an FATF high-risk / call-for-action "
                    "jurisdiction."
                ),
                amla_ref="AMLA RTS Art. 4(1)(b); FATF call-for-action list",
                evidence={"jurisdiction": juris},
            )
        )
    elif juris in _OPACITY_JURISDICTIONS:
        signals.append(
            RiskSignal(
                code="geo.opacity-juris",
                severity="medium",
                rationale=(
                    f"Entity {entity.get('uid', '?')} is incorporated in {juris.upper()}, "
                    "a jurisdiction commonly used for opaque ownership structures."
                ),
                amla_ref="AMLA RTS Art. 4(2)(c)",
                evidence={"jurisdiction": juris},
            )
        )

    if entity.get("has_employees") is False and entity.get("has_website") is False:
        signals.append(
            RiskSignal(
                code="struct.shell-profile",
                severity="medium",
                rationale=(
                    f"Entity {entity.get('uid', '?')} has no known employees and no "
                    "web presence — consistent with a shell-company profile."
                ),
                amla_ref="AMLA RTS Art. 4(2)(a) — entity with no genuine economic activity",
            )
        )

    return signals


# ---------------------------------------------------------------------------
# Cluster-level signals
# ---------------------------------------------------------------------------


def evaluate_cluster(
    profile: dict[str, Any],
    *,
    twins: Iterable[dict[str, Any]] | None = None,
    repeated_addresses: Iterable[dict[str, Any]] | None = None,
    repeated_officers: Iterable[dict[str, Any]] | None = None,
) -> list[RiskSignal]:
    """Return cluster-scoped AMLA risk signals.

    Args:
        profile: the ``cluster_<id>_profile.json`` payload (must carry
            ``community_id`` and ``members_sample``).
        twins: rows from ``cross_jurisdiction_twins.parquet`` (Phase 3)
            filtered to this cluster.
        repeated_addresses: rows from ``cluster_<id>_repeated_addresses.csv``.
        repeated_officers: rows from ``cluster_<id>_repeated_officers.csv``.
    """

    cid = profile.get("community_id", "?")
    signals: list[RiskSignal] = []

    members = list(profile.get("members_sample") or [])

    # 1. Multi-jurisdiction chain.
    juris_set: set[str] = {
        (m.get("jurisdiction") or "")[:2].lower() for m in members if m.get("jurisdiction")
    }
    juris_set.discard("")
    if len(juris_set) >= 3:
        signals.append(
            RiskSignal(
                code="struct.multi-juris-chain",
                severity="medium" if len(juris_set) < 5 else "high",
                rationale=(
                    f"Community #{cid} spans {len(juris_set)} jurisdictions "
                    f"({', '.join(sorted(juris_set))}). Multi-jurisdictional ownership "
                    "chains warrant enhanced CDD under AMLA RTS Art. 4(2)(c)."
                ),
                amla_ref="AMLA RTS Art. 4(2)(c)",
                evidence={"jurisdictions": sorted(juris_set), "count": len(juris_set)},
            )
        )

    # 2. Opacity-jurisdiction concentration.
    opacity_members = [
        m for m in members if (m.get("jurisdiction") or "")[:2].lower() in _OPACITY_JURISDICTIONS
    ]
    if opacity_members and len(opacity_members) >= max(2, len(members) // 3):
        signals.append(
            RiskSignal(
                code="struct.opacity-concentration",
                severity="high",
                rationale=(
                    f"{len(opacity_members)} of {len(members)} members of community "
                    f"#{cid} are incorporated in low-transparency jurisdictions."
                ),
                amla_ref="AMLA RTS Art. 4(2)(c)",
                evidence={
                    "opacity_member_count": len(opacity_members),
                    "total_members": len(members),
                },
            )
        )

    # 3. Cross-jurisdiction name twin (Phase 3 output).
    twin_rows = list(twins or [])
    if twin_rows:
        signals.append(
            RiskSignal(
                code="lineage.cross-juris-twin",
                severity="high",
                rationale=(
                    f"Community #{cid} contains {len(twin_rows)} name-lineage twin pairs "
                    "across jurisdictions (e.g. UK<->Malta). Successor / mirror entities "
                    "may be structured to obscure beneficial ownership."
                ),
                amla_ref="AMLA RTS Art. 4(2)(d) — successor entity / structuring",
                evidence={"twin_count": len(twin_rows)},
            )
        )

    # 4. Mass-shared address (registered-office stuffing).
    addr_rows = list(repeated_addresses or [])
    for a in addr_rows:
        n = int(a.get("n_linked_companies") or 0)
        if n >= 5:
            signals.append(
                RiskSignal(
                    code="struct.mass-shared-address",
                    severity="medium" if n < 15 else "high",
                    rationale=(
                        f"Address shared by {n} community-#{cid} entities: "
                        f"{a.get('address', '?')[:120]}. Registered-office stuffing is "
                        "an established shell-company indicator."
                    ),
                    amla_ref="AMLA RTS Art. 4(2)(a)",
                    evidence={"n_companies": n, "address": a.get("address", "")},
                )
            )

    # 5. Recurring nominee officer.
    officer_rows = list(repeated_officers or [])
    for o in officer_rows:
        n = int(o.get("n_linked_companies") or 0)
        if n >= 10:
            signals.append(
                RiskSignal(
                    code="struct.nominee-officer-pattern",
                    severity="medium" if n < 25 else "high",
                    rationale=(
                        f"Officer '{o.get('officer_name', '?')}' appears on {n} "
                        f"community-#{cid} entities. Nominee-director patterns require "
                        "verification of ultimate beneficial owner."
                    ),
                    amla_ref="AMLA RTS Art. 5 — nominee arrangements",
                    evidence={"officer_name": o.get("officer_name", ""), "n_companies": n},
                )
            )

    return signals


# ---------------------------------------------------------------------------
# Convenience: aggregate severity
# ---------------------------------------------------------------------------


_SEVERITY_ORDER: dict[Severity, int] = {"low": 1, "medium": 2, "high": 3}


def overall_severity(signals: Iterable[RiskSignal]) -> Severity | None:
    """Return the highest severity in ``signals`` (or None if empty)."""

    best: Severity | None = None
    best_rank = 0
    for s in signals:
        r = _SEVERITY_ORDER[s.severity]
        if r > best_rank:
            best_rank = r
            best = s.severity
    return best


def to_rows(signals: Iterable[RiskSignal]) -> list[dict[str, str]]:
    """Flatten signals to CSV-friendly rows."""

    return [
        {
            "code": s.code,
            "severity": s.severity,
            "rationale": s.rationale,
            "amla_ref": s.amla_ref,
            "evidence": ";".join(f"{k}={v}" for k, v in sorted(s.evidence.items())),
        }
        for s in signals
    ]
