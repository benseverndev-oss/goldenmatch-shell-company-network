"""Cluster-level anomaly / contradiction detectors.

The orchestrator ``detect_all`` returns a list of ``AnomalyFlag`` objects.
Each detector is a small pure function that produces zero or more flags
from a slice of the cluster's data — easy to unit-test in isolation,
easy to add to without touching the others.

Each flag carries an ``evidence`` dict so the briefing can show *why*
the flag fired, not just *that* it did.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import polars as pl

    from shellnet.investigations.cluster_explainer import (
        AddressRepeat,
        CentralityAnnotation,
        IntermediaryRepeat,
        MemberAttr,
        OfficerRepeat,
    )


@dataclass
class AnomalyFlag:
    """A single contradiction / anomaly raised by the orchestrator.

    ``kind`` is a short stable identifier (used by callers to gate UI / suppress
    duplicates); ``severity`` is one of ``low|medium|high``; ``message`` is a
    human-readable explanation; ``evidence`` is a free-form dict carrying the
    specific values that triggered the flag (jurisdictions, edge counts, dates,
    nodes) so the briefing can show its work.
    """

    kind: str
    severity: str
    message: str
    member_uids: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


# Default thresholds. Tunable per call.
SHELL_HUB_GLOBAL_DEGREE_THRESHOLD = 25  # global degree above which a shared
# feature is considered known shell infrastructure
ASYMMETRY_DEGREE_RATIO = 8  # max/min member-incident-edge ratio that trips
# the structural-asymmetry flag


def _parse_date(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.fromisoformat(str(v)).date()
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Individual detectors
# ---------------------------------------------------------------------------


def detect_cross_border_mirror(members: list[MemberAttr]) -> list[AnomalyFlag]:
    """A normalized name appearing under ≥2 jurisdictions — classic
    mirror-shell pattern that dedupe surfaces but doesn't itself flag."""
    by_name_jurs: dict[str, set[str]] = defaultdict(set)
    by_name_uids: dict[str, list[str]] = defaultdict(list)
    for m in members:
        nn = (m.normalized_name or "").strip()
        if not nn:
            continue
        j = (m.jurisdiction or "").strip().lower()
        if j:
            by_name_jurs[nn].add(j)
        by_name_uids[nn].append(m.entity_uid)
    out: list[AnomalyFlag] = []
    for nn, jurs in by_name_jurs.items():
        if len(jurs) >= 2:
            out.append(
                AnomalyFlag(
                    kind="cross_border_mirror",
                    severity="medium",
                    message=(
                        f"Normalized name `{nn}` appears under {len(jurs)} different "
                        f"jurisdictions ({', '.join(sorted(jurs))}). Possible mirror shells."
                    ),
                    member_uids=by_name_uids[nn],
                    evidence={"normalized_name": nn, "jurisdictions": sorted(jurs)},
                )
            )
    return out


def detect_status_contradiction(members: list[MemberAttr]) -> list[AnomalyFlag]:
    """Cluster contains both active and dormant/struck-off members."""
    any_dormant = any(m.is_dormant for m in members)
    any_active = any(
        (m.status or "").strip().lower() in {"active", "current", "registered"} for m in members
    )
    if not (any_dormant and any_active):
        return []
    dormant_uids = [m.entity_uid for m in members if m.is_dormant]
    active_uids = [
        m.entity_uid
        for m in members
        if (m.status or "").strip().lower() in {"active", "current", "registered"}
    ]
    return [
        AnomalyFlag(
            kind="status_contradiction",
            severity="medium",
            message=(
                "Cluster contains both active and dormant/struck-off entities. "
                "Worth checking which side is the live shell."
            ),
            member_uids=dormant_uids,
            evidence={"dormant": dormant_uids, "active": active_uids},
        )
    ]


def detect_hidden_hub(
    centrality: list[CentralityAnnotation],
) -> list[AnomalyFlag]:
    """Highest-betweenness centrality node is a non-member and dominates
    the top member by ≥2×."""
    non_member_hubs = [c for c in centrality if not c.is_member and c.betweenness > 0]
    member_hubs = [c for c in centrality if c.is_member]
    if not (non_member_hubs and member_hubs):
        return []
    top_outside = max(non_member_hubs, key=lambda c: c.betweenness)
    top_inside = max((c.betweenness for c in member_hubs), default=0.0)
    if top_outside.betweenness <= 2 * (top_inside or 1e-9):
        return []
    return [
        AnomalyFlag(
            kind="hidden_hub",
            severity="high",
            message=(
                f"Non-member node `{top_outside.entity_uid}` has betweenness "
                f"{top_outside.betweenness:.4f}, more than 2× the top member's "
                f"({top_inside:.4f}). Likely the connective tissue."
            ),
            member_uids=[top_outside.entity_uid],
            evidence={
                "non_member_uid": top_outside.entity_uid,
                "non_member_betweenness": top_outside.betweenness,
                "top_member_betweenness": top_inside,
            },
        )
    ]


def detect_no_registry_anchor(members: list[MemberAttr]) -> list[AnomalyFlag]:
    """Multi-source cluster with no LEI / company_number on any member."""
    if not members or len({m.source for m in members}) < 2:
        return []
    if any(m.lei or m.company_number for m in members):
        return []
    return [
        AnomalyFlag(
            kind="no_registry_anchor",
            severity="low",
            message=(
                "Cluster spans multiple sources but no member carries an "
                "LEI or company_number. Identity rests on names + addresses."
            ),
            member_uids=[m.entity_uid for m in members],
            evidence={"sources": sorted({m.source for m in members})},
        )
    ]


def detect_overlapping_identities(members: list[MemberAttr]) -> list[AnomalyFlag]:
    """Two distinct members share an LEI (impossible) or a
    company_number+jurisdiction (impossible across rows that don't have
    a same-source explanation). The dedupe step should already have
    merged them — if they're still distinct rows in the cluster, the
    upstream feeds disagree."""
    out: list[AnomalyFlag] = []
    by_lei: dict[str, list[str]] = defaultdict(list)
    by_cn: dict[tuple[str, str], list[str]] = defaultdict(list)
    for m in members:
        if m.lei:
            by_lei[m.lei.upper()].append(m.entity_uid)
        if m.company_number and m.jurisdiction:
            by_cn[(m.company_number, m.jurisdiction.lower())].append(m.entity_uid)

    for lei, uids in by_lei.items():
        if len(set(uids)) >= 2:
            out.append(
                AnomalyFlag(
                    kind="overlapping_lei",
                    severity="high",
                    message=(
                        f"LEI `{lei}` is claimed by {len(set(uids))} distinct cluster "
                        "members. An LEI is globally unique — the sources disagree."
                    ),
                    member_uids=sorted(set(uids)),
                    evidence={"lei": lei, "claimants": sorted(set(uids))},
                )
            )
    for (cn, jur), uids in by_cn.items():
        if len(set(uids)) >= 2:
            out.append(
                AnomalyFlag(
                    kind="overlapping_company_number",
                    severity="medium",
                    message=(
                        f"Company number `{cn}` in `{jur}` is claimed by "
                        f"{len(set(uids))} distinct members."
                    ),
                    member_uids=sorted(set(uids)),
                    evidence={
                        "company_number": cn,
                        "jurisdiction": jur,
                        "claimants": sorted(set(uids)),
                    },
                )
            )
    return out


def detect_contradictory_officers(
    members: list[MemberAttr],
    officers: list[OfficerRepeat],
) -> list[AnomalyFlag]:
    """A shared officer directs both an active member and a dormant
    member of the cluster — worth a look (was the officer reappointed
    after struck-off, or is the dormant date wrong?)."""
    out: list[AnomalyFlag] = []
    status_by_uid = {m.entity_uid: (m.status or "").strip().lower() for m in members}
    dormant_uids = {m.entity_uid for m in members if m.is_dormant}
    active_uids = {
        uid for uid, st in status_by_uid.items() if st in {"active", "current", "registered"}
    }
    for officer in officers:
        served = set(officer.member_uids)
        hits_dormant = served & dormant_uids
        hits_active = served & active_uids
        if hits_dormant and hits_active:
            out.append(
                AnomalyFlag(
                    kind="contradictory_officer",
                    severity="medium",
                    message=(
                        f"Officer `{officer.name or officer.node}` directs both "
                        f"active and dormant cluster members "
                        f"({len(hits_active)}/{len(hits_dormant)} respectively)."
                    ),
                    member_uids=sorted(served),
                    evidence={
                        "officer_node": officer.node,
                        "officer_name": officer.name,
                        "active_members": sorted(hits_active),
                        "dormant_members": sorted(hits_dormant),
                    },
                )
            )
    return out


def detect_shell_reuse_anomaly(
    intermediaries: list[IntermediaryRepeat],
    addresses: list[AddressRepeat],
    officers: list[OfficerRepeat],
    *,
    threshold: int = SHELL_HUB_GLOBAL_DEGREE_THRESHOLD,
) -> list[AnomalyFlag]:
    """A shared feature whose global degree is dramatically higher than
    the cluster's own incident count — i.e. it connects to many other
    entities in the corpus too, the classic 'this address services 500
    shells' signal."""
    out: list[AnomalyFlag] = []
    for repeat, kind in (
        *((i, "intermediary") for i in intermediaries),
        *((a, "address") for a in addresses),
        *((o, "officer") for o in officers),
    ):
        if repeat.n_global_edges < threshold:
            continue
        severity = "high" if repeat.n_global_edges >= threshold * 4 else "medium"
        label = (repeat.name if kind != "address" else (repeat.text or repeat.node)) or repeat.node
        out.append(
            AnomalyFlag(
                kind="shell_reuse_anomaly",
                severity=severity,
                message=(
                    f"Shared {kind} `{label}` has {repeat.n_global_edges} edges "
                    f"across the corpus — appears to be known shell infrastructure "
                    f"(threshold {threshold})."
                ),
                member_uids=list(repeat.member_uids),
                evidence={
                    "kind": kind,
                    "node": repeat.node,
                    "label": label,
                    "n_global_edges": repeat.n_global_edges,
                    "n_members_served": repeat.n_members_served,
                    "threshold": threshold,
                },
            )
        )
    return out


def detect_structural_asymmetry(
    members: list[MemberAttr],
    edges_df: pl.DataFrame | None,
    *,
    ratio_threshold: int = ASYMMETRY_DEGREE_RATIO,
) -> list[AnomalyFlag]:
    """Cluster members with wildly uneven incident-edge counts — one or
    two members carry the entire structural weight while the rest look
    like dangling siblings."""
    if edges_df is None or edges_df.height == 0 or len(members) < 2:
        return []
    member_uids = [m.entity_uid for m in members]
    import polars as pl  # local — keeps the runtime import out of type-check land

    sub = edges_df.filter(
        pl.col("src_node").is_in(member_uids) | pl.col("dst_node").is_in(member_uids)
    )
    incident: dict[str, int] = {uid: 0 for uid in member_uids}
    for r in sub.iter_rows(named=True):
        s, d = r["src_node"], r["dst_node"]
        if s in incident:
            incident[s] += 1
        if d in incident:
            incident[d] += 1
    counts = list(incident.values())
    if not counts:
        return []
    max_c = max(counts)
    # Treat zero-incident members as one for ratio purposes — if some have
    # zero, the asymmetry is real and we want it to fire.
    min_c = min(counts)
    effective_min = min_c if min_c > 0 else 1
    if max_c < ratio_threshold:
        return []
    if max_c < effective_min * ratio_threshold:
        return []
    dominant = [uid for uid, c in incident.items() if c == max_c]
    isolated = [uid for uid, c in incident.items() if c == min_c]
    return [
        AnomalyFlag(
            kind="structural_asymmetry",
            severity="medium",
            message=(
                f"Edge-count asymmetry across cluster members: max={max_c}, "
                f"min={min_c}. One or two members carry the structural weight."
            ),
            member_uids=sorted(set(dominant) | set(isolated)),
            evidence={"incident_counts": incident, "dominant": dominant, "isolated": isolated},
        )
    ]


def detect_impossible_timeline(
    members: list[MemberAttr],
    edges_df: pl.DataFrame | None,
) -> list[AnomalyFlag]:
    """An edge with ``start_date`` after the member's ``dissolution_date``
    or before its ``incorporation_date`` — relationships that couldn't
    have existed at the time they're claimed to have started.

    Only fires when the unified table actually carries those dates for the
    member; otherwise stays silent rather than emitting false positives.
    """
    if edges_df is None or edges_df.height == 0:
        return []
    if "start_date" not in edges_df.columns:
        return []
    out: list[AnomalyFlag] = []
    import polars as pl

    for m in members:
        inc = _parse_date(getattr(m, "incorporation_date", None))
        dis = _parse_date(getattr(m, "dissolution_date", None))
        if inc is None and dis is None:
            continue
        sub = edges_df.filter(
            (pl.col("src_node") == m.entity_uid) | (pl.col("dst_node") == m.entity_uid)
        )
        violations: list[dict[str, Any]] = []
        for r in sub.iter_rows(named=True):
            start = _parse_date(r.get("start_date"))
            if start is None:
                continue
            if inc and start < inc:
                violations.append(
                    {
                        "kind_raw": r.get("kind_raw"),
                        "start": str(start),
                        "incorporation_date": str(inc),
                        "rule": "edge_starts_before_incorporation",
                    }
                )
            if dis and start > dis:
                violations.append(
                    {
                        "kind_raw": r.get("kind_raw"),
                        "start": str(start),
                        "dissolution_date": str(dis),
                        "rule": "edge_starts_after_dissolution",
                    }
                )
        if violations:
            out.append(
                AnomalyFlag(
                    kind="impossible_timeline",
                    severity="high",
                    message=(
                        f"`{m.entity_uid}` has {len(violations)} edge(s) whose "
                        f"start_date falls outside its [incorporation, dissolution] "
                        f"window."
                    ),
                    member_uids=[m.entity_uid],
                    evidence={"violations": violations[:10]},
                )
            )
    return out


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def detect_all(
    members: list[MemberAttr],
    *,
    intermediaries: list[IntermediaryRepeat] | None = None,
    addresses: list[AddressRepeat] | None = None,
    officers: list[OfficerRepeat] | None = None,
    centrality: list[CentralityAnnotation] | None = None,
    edges_df: pl.DataFrame | None = None,
) -> list[AnomalyFlag]:
    """Run every detector and concatenate the results.

    All detector inputs are optional; detectors that don't have what they
    need degrade silently to an empty list rather than firing false
    positives."""
    intermediaries = intermediaries or []
    addresses = addresses or []
    officers = officers or []
    centrality = centrality or []

    flags: list[AnomalyFlag] = []
    flags.extend(detect_cross_border_mirror(members))
    flags.extend(detect_status_contradiction(members))
    flags.extend(detect_hidden_hub(centrality))
    flags.extend(detect_no_registry_anchor(members))
    flags.extend(detect_overlapping_identities(members))
    flags.extend(detect_contradictory_officers(members, officers))
    flags.extend(detect_shell_reuse_anomaly(intermediaries, addresses, officers))
    flags.extend(detect_structural_asymmetry(members, edges_df))
    flags.extend(detect_impossible_timeline(members, edges_df))

    # Sort high → medium → low so the most actionable flags surface first.
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    flags.sort(key=lambda f: (sev_rank.get(f.severity, 9), f.kind))
    return flags
