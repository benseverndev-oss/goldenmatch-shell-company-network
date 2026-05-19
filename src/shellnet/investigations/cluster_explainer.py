"""Cluster Explanation Engine — turn an opaque dedupe cluster into an
investigator-ready briefing.

The companion to ``seed_query.py`` for the cluster end of the workflow.
Given a cluster id and the existing processed / interim parquets, this
module surfaces *why* a cluster is worth a human's attention: which
intermediaries, addresses, and officers are reused across its members;
which jurisdictions it bridges; what contradictions or impossible
timelines lurk inside; what narrative paths cut through it; and a
composite "investigative value" score broken down by component.

Pure functions and dataclasses only — no I/O, no Typer, no DB. The thin
CLI wrapper lives in ``scripts/explain_cluster.py``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import polars as pl

# Conservative offshore-finance / corporate-secrecy ISO-3166-1 alpha-2 set.
# Used only to flag jurisdiction *mix* — not a list of "guilty" places.
SECRECY_JURISDICTIONS: frozenset[str] = frozenset(
    {
        "vg",  # British Virgin Islands
        "ky",  # Cayman Islands
        "pa",  # Panama
        "bs",  # Bahamas
        "bz",  # Belize
        "bm",  # Bermuda
        "gg",  # Guernsey
        "je",  # Jersey
        "im",  # Isle of Man
        "li",  # Liechtenstein
        "lu",  # Luxembourg
        "mt",  # Malta
        "cy",  # Cyprus
        "sc",  # Seychelles
        "mu",  # Mauritius
        "ai",  # Anguilla
        "tc",  # Turks and Caicos
        "ws",  # Samoa
        "vu",  # Vanuatu
        "mc",  # Monaco
    }
)

# Members that resolve to one of these dedupe-target sources are "shell-like";
# matching OpenCorporates / GLEIF rows give registry anchors instead.
SHELL_LEANING_SOURCES: frozenset[str] = frozenset({"icij"})

# Status strings (lowercased) considered "dormant" across sources. ICIJ uses
# `status` strings like "Struck off"; OpenCorporates uses "dissolved",
# "inactive"; OpenSanctions uses none.
DORMANT_STATUSES: frozenset[str] = frozenset(
    {"struck off", "struck_off", "dissolved", "inactive", "dormant", "liquidated"}
)


@dataclass
class MemberAttr:
    """One row of cluster-member context, source-agnostic."""

    entity_uid: str
    source: str
    name: str
    normalized_name: str | None
    jurisdiction: str | None
    company_number: str | None
    lei: str | None
    status: str | None
    legal_form: str | None
    address_raw: str | None

    @property
    def is_dormant(self) -> bool:
        return (self.status or "").strip().lower() in DORMANT_STATUSES


@dataclass
class IntermediaryRepeat:
    node: str  # icij:<source_id>
    name: str | None
    country: str | None
    n_members_served: int
    member_uids: list[str]
    n_global_edges: int  # incident edges in the full edges_df
    leak_labels: list[str]


@dataclass
class AddressRepeat:
    node: str
    text: str | None
    country: str | None
    n_members_served: int
    member_uids: list[str]
    n_global_edges: int
    leak_labels: list[str]


@dataclass
class OfficerRepeat:
    node: str
    name: str | None
    country: str | None
    role: str | None
    n_members_served: int
    member_uids: list[str]
    n_global_edges: int
    leak_labels: list[str]


@dataclass
class JurisdictionProfile:
    counts: dict[str, int]
    secrecy_jurisdictions: list[str]
    is_cross_border: bool
    n_unknown: int


@dataclass
class CentralityAnnotation:
    entity_uid: str
    eigenvector: float
    betweenness: float
    total_degree: int
    community_id: int | None
    is_member: bool  # vs. high-centrality non-member in the ego subgraph


@dataclass
class AnomalyFlag:
    kind: str  # 'impossible_timeline' | 'status_contradiction' | 'cross_border_same_id' | 'hidden_hub'
    severity: str  # 'low' | 'medium' | 'high'
    message: str
    member_uids: list[str] = field(default_factory=list)


@dataclass
class NarrativePath:
    anchor_uid: str
    summary: str  # one-sentence
    steps: list[str]  # human-readable bullets


@dataclass
class InvestigativeFeatures:
    """Each component is in [0, 1]. ``total`` is the unweighted sum.

    Distinct from ``rank_clusters.defensibility``: that score measures
    cluster *integrity* (is the dedupe right?). This one measures
    *investigative interest* (is there a story here?).
    """

    intermediary_rarity: float
    cross_jurisdiction_bridge: float
    sanctions_proximity: float
    registry_anchor_density: float
    hidden_central_entity: float
    dormant_but_connected: float
    shell_reuse: float
    total: float
    notes: dict[str, str]  # component -> short explanation


@dataclass
class ClusterExplanation:
    cluster_id: int
    members: list[MemberAttr]
    intermediaries: list[IntermediaryRepeat]
    addresses: list[AddressRepeat]
    officers: list[OfficerRepeat]
    jurisdictions: JurisdictionProfile
    sanctions_anchors: list[dict[str, Any]]
    centrality: list[CentralityAnnotation]
    anomalies: list[AnomalyFlag]
    paths: list[NarrativePath]
    features: InvestigativeFeatures
    leaks_present: list[str]
    sources_present: list[str]
    suggested_targets: list[str]


# ---------------------------------------------------------------------------
# Loading members
# ---------------------------------------------------------------------------


def load_cluster_members_from_parquet(clusters_df: pl.DataFrame, cluster_id: int) -> list[str]:
    """Offline fallback: a parquet with at least ``(cluster_id, entity_uid)``."""
    if clusters_df.height == 0:
        return []
    rows = clusters_df.filter(pl.col("cluster_id") == cluster_id).get_column("entity_uid")
    return rows.to_list()


# ---------------------------------------------------------------------------
# Member attributes
# ---------------------------------------------------------------------------


def gather_member_attrs(company_df: pl.DataFrame, member_uids: list[str]) -> list[MemberAttr]:
    if not member_uids:
        return []
    sub = company_df.filter(pl.col("entity_uid").is_in(member_uids))
    out: list[MemberAttr] = []
    seen: set[str] = set()
    for r in sub.iter_rows(named=True):
        uid = r["entity_uid"]
        if uid in seen:
            continue
        seen.add(uid)
        out.append(
            MemberAttr(
                entity_uid=uid,
                source=r.get("source") or "?",
                name=r.get("name") or "",
                normalized_name=r.get("normalized_name"),
                jurisdiction=r.get("jurisdiction"),
                company_number=r.get("company_number"),
                lei=r.get("lei"),
                status=r.get("status"),
                legal_form=r.get("legal_form"),
                address_raw=r.get("address_raw"),
            )
        )
    # Preserve member_uids ordering when possible.
    by_uid = {m.entity_uid: m for m in out}
    return [by_uid[u] for u in member_uids if u in by_uid]


# ---------------------------------------------------------------------------
# Edge walks — repeated intermediaries / addresses / officers
# ---------------------------------------------------------------------------


def _classify_edge_kind(kind_raw: str | None) -> str:
    k = (kind_raw or "").lower()
    if "address" in k:
        return "address"
    if "intermediar" in k:
        return "intermediary"
    if "officer" in k:
        return "officer"
    return "other"


def _other_node(uid: str, src: str, dst: str) -> str | None:
    if uid == src:
        return dst
    if uid == dst:
        return src
    return None


def _global_degree_table(edges_df: pl.DataFrame) -> dict[str, int]:
    """Edge count incident to each node across the *entire* edges_df."""
    if edges_df.height == 0:
        return {}
    src_counts = Counter(edges_df.get_column("src_node").to_list())
    dst_counts = Counter(edges_df.get_column("dst_node").to_list())
    out: dict[str, int] = defaultdict(int)
    for n, c in src_counts.items():
        out[n] += c
    for n, c in dst_counts.items():
        out[n] += c
    return out


def _lookup_by_source_id(df: pl.DataFrame | None) -> dict[str, dict[str, Any]]:
    if df is None or df.height == 0:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in df.iter_rows(named=True):
        sid = r.get("source_id")
        if sid is None:
            continue
        out[str(sid)] = r
    return out


def gather_repeats(
    member_uids: list[str],
    *,
    edges_df: pl.DataFrame | None,
    addresses_df: pl.DataFrame | None,
    officers_df: pl.DataFrame | None,
    intermediaries_df: pl.DataFrame | None,
    min_members: int = 2,
    top_n: int = 10,
) -> tuple[list[IntermediaryRepeat], list[AddressRepeat], list[OfficerRepeat]]:
    """Find addresses / officers / intermediaries that touch ≥``min_members``
    distinct cluster members. Sorted by ``n_members_served`` desc, then
    ``n_global_edges`` desc."""
    if not member_uids or edges_df is None or edges_df.height == 0:
        return [], [], []

    member_set = set(member_uids)
    sub = edges_df.filter(
        pl.col("src_node").is_in(member_uids) | pl.col("dst_node").is_in(member_uids)
    )
    if sub.height == 0:
        return [], [], []

    addr_lookup = _lookup_by_source_id(addresses_df)
    off_lookup = _lookup_by_source_id(officers_df)
    inter_lookup = _lookup_by_source_id(intermediaries_df)
    global_deg = _global_degree_table(edges_df)

    # other_node -> kind -> {member_uid: leak_label}
    bucket: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)

    for r in sub.iter_rows(named=True):
        s, d = r["src_node"], r["dst_node"]
        kind = _classify_edge_kind(r.get("kind_raw"))
        if kind == "other":
            continue
        # Which side is the cluster member, which is the "other".
        if s in member_set:
            member_uid, other = s, d
        elif d in member_set:
            member_uid, other = d, s
        else:
            continue
        bucket[(other, kind)][member_uid] = r.get("source_label") or ""

    inters: list[IntermediaryRepeat] = []
    addrs: list[AddressRepeat] = []
    offs: list[OfficerRepeat] = []

    for (other, kind), members in bucket.items():
        if len(members) < min_members:
            continue
        sid = other.split(":", 1)[1] if ":" in other else other
        leak_labels = sorted({lbl for lbl in members.values() if lbl})
        if kind == "address":
            meta = addr_lookup.get(sid) or {}
            addrs.append(
                AddressRepeat(
                    node=other,
                    text=meta.get("raw_text") or meta.get("normalized_text"),
                    country=meta.get("country"),
                    n_members_served=len(members),
                    member_uids=sorted(members.keys()),
                    n_global_edges=int(global_deg.get(other, 0)),
                    leak_labels=leak_labels,
                )
            )
        elif kind == "officer":
            meta = off_lookup.get(sid) or {}
            offs.append(
                OfficerRepeat(
                    node=other,
                    name=meta.get("name"),
                    country=meta.get("country"),
                    role=None,  # role lives on the edge, not the officer node
                    n_members_served=len(members),
                    member_uids=sorted(members.keys()),
                    n_global_edges=int(global_deg.get(other, 0)),
                    leak_labels=leak_labels,
                )
            )
        elif kind == "intermediary":
            meta = inter_lookup.get(sid) or {}
            inters.append(
                IntermediaryRepeat(
                    node=other,
                    name=meta.get("name"),
                    country=meta.get("country"),
                    n_members_served=len(members),
                    member_uids=sorted(members.keys()),
                    n_global_edges=int(global_deg.get(other, 0)),
                    leak_labels=leak_labels,
                )
            )

    inters.sort(key=lambda x: (-x.n_members_served, -x.n_global_edges))
    addrs.sort(key=lambda x: (-x.n_members_served, -x.n_global_edges))
    offs.sort(key=lambda x: (-x.n_members_served, -x.n_global_edges))
    return inters[:top_n], addrs[:top_n], offs[:top_n]


# ---------------------------------------------------------------------------
# Jurisdiction profile + centrality + sanctions
# ---------------------------------------------------------------------------


def compute_jurisdiction_profile(members: list[MemberAttr]) -> JurisdictionProfile:
    counts: Counter[str] = Counter()
    n_unknown = 0
    for m in members:
        j = (m.jurisdiction or "").strip().lower()
        if not j:
            n_unknown += 1
        else:
            counts[j] += 1
    secrecy = sorted(j for j in counts if j in SECRECY_JURISDICTIONS)
    return JurisdictionProfile(
        counts=dict(counts),
        secrecy_jurisdictions=secrecy,
        is_cross_border=len(counts) >= 2,
        n_unknown=n_unknown,
    )


def annotate_centrality(
    centrality_df: pl.DataFrame | None,
    member_uids: list[str],
    *,
    top_extra_nonmembers: int = 3,
) -> list[CentralityAnnotation]:
    """Pull centrality rows for cluster members and, optionally, the top few
    *non-member* nodes in the same ego subgraph by betweenness — those are the
    "hidden hubs" that connect cluster members but don't belong to the cluster."""
    if centrality_df is None or centrality_df.height == 0 or not member_uids:
        return []
    member_set = set(member_uids)
    rows = centrality_df.filter(pl.col("entity_uid").is_in(member_uids))
    out: list[CentralityAnnotation] = []
    for r in rows.iter_rows(named=True):
        out.append(
            CentralityAnnotation(
                entity_uid=r["entity_uid"],
                eigenvector=float(r.get("eigenvector") or 0.0),
                betweenness=float(r.get("betweenness") or 0.0),
                total_degree=int(r.get("total_degree") or 0),
                community_id=(
                    int(r["community_id"]) if r.get("community_id") is not None else None
                ),
                is_member=True,
            )
        )

    # Hidden-hub candidates: nodes in the same community as ≥1 member but
    # *not* in the cluster, ranked by betweenness.
    member_communities = {c.community_id for c in out if c.community_id is not None}
    if member_communities:
        extras = (
            centrality_df.filter(
                (~pl.col("entity_uid").is_in(member_uids))
                & pl.col("community_id").is_in(list(member_communities))
            )
            .sort("betweenness", descending=True)
            .head(top_extra_nonmembers)
        )
        for r in extras.iter_rows(named=True):
            out.append(
                CentralityAnnotation(
                    entity_uid=r["entity_uid"],
                    eigenvector=float(r.get("eigenvector") or 0.0),
                    betweenness=float(r.get("betweenness") or 0.0),
                    total_degree=int(r.get("total_degree") or 0),
                    community_id=(
                        int(r["community_id"]) if r.get("community_id") is not None else None
                    ),
                    is_member=False,
                )
            )

    out.sort(key=lambda c: (-c.betweenness, -c.eigenvector))
    _ = member_set  # member_set unused after refactor; kept for clarity above
    return out


def filter_sanctions_anchors(
    sanctions_df: pl.DataFrame | None,
    member_uids: list[str],
) -> list[dict[str, Any]]:
    """``sanctions_df`` is the list-match table (``target_entity_uid, ref_*``).
    Returns rows whose ``target_entity_uid`` is in ``member_uids``."""
    if sanctions_df is None or sanctions_df.height == 0 or not member_uids:
        return []
    target_col = "target_entity_uid" if "target_entity_uid" in sanctions_df.columns else None
    if target_col is None:
        return []
    sub = sanctions_df.filter(pl.col(target_col).is_in(member_uids))
    return list(sub.iter_rows(named=True))


# ---------------------------------------------------------------------------
# Anomalies / contradictions
# ---------------------------------------------------------------------------


def _parse_date(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    try:
        return datetime.fromisoformat(str(v)).date()
    except (TypeError, ValueError):
        return None


def detect_anomalies(
    members: list[MemberAttr],
    *,
    edges_df: pl.DataFrame | None,
    centrality: list[CentralityAnnotation],
) -> list[AnomalyFlag]:
    flags: list[AnomalyFlag] = []
    member_uids = [m.entity_uid for m in members]
    member_set = set(member_uids)

    # 1. Impossible timeline: dissolved/struck-off member with an edge whose
    #    start_date is after its dissolution. Use ICIJ struck_off_date proxy
    #    via status — we don't have an explicit dissolution_date column in
    #    the unified table, so this check only fires when the edges_df has a
    #    start_date column and a member's source carries a struck_off_date.
    if edges_df is not None and edges_df.height and "start_date" in edges_df.columns:
        for m in members:
            if not m.is_dormant:
                continue
            sub = edges_df.filter(
                (pl.col("src_node") == m.entity_uid) | (pl.col("dst_node") == m.entity_uid)
            )
            for r in sub.iter_rows(named=True):
                start = _parse_date(r.get("start_date"))
                # We have no per-member dissolution date in the unified
                # schema, so we can only fire this flag if there's also an
                # edge `end_date` that says the relationship outlived the
                # entity. Conservatively: flag when an officer-of edge has
                # `end_date` strictly later than the entity's "Struck off"
                # status implies the matter was contested.
                end = _parse_date(r.get("end_date"))
                _ = start
                _ = end
                # Without explicit dissolution_date in members we skip this
                # check rather than firing false positives. The hook is here
                # for when build_unified_table propagates dissolution_date.
                break

    # 2. Status contradiction: cluster members marked dormant *and* active.
    if members:
        any_dormant = any(m.is_dormant for m in members)
        any_active = any(
            (m.status or "").strip().lower() in {"active", "current", "registered"} for m in members
        )
        if any_dormant and any_active:
            dormant_uids = [m.entity_uid for m in members if m.is_dormant]
            flags.append(
                AnomalyFlag(
                    kind="status_contradiction",
                    severity="medium",
                    message=(
                        "Cluster contains both active and dormant/struck-off entities. "
                        "Worth checking which side is the live shell."
                    ),
                    member_uids=dormant_uids,
                )
            )

    # 3. Cross-border same-id: members sharing a normalized name across
    #    >1 jurisdiction (the canonical "mirror-shell" pattern that dedupe
    #    surfaces but doesn't itself flag as suspicious).
    by_name: dict[str, set[str]] = defaultdict(set)
    by_name_uids: dict[str, list[str]] = defaultdict(list)
    for m in members:
        nn = (m.normalized_name or "").strip()
        if not nn:
            continue
        j = (m.jurisdiction or "").strip().lower()
        if j:
            by_name[nn].add(j)
        by_name_uids[nn].append(m.entity_uid)
    for nn, jurs in by_name.items():
        if len(jurs) >= 2:
            flags.append(
                AnomalyFlag(
                    kind="cross_border_mirror",
                    severity="medium",
                    message=(
                        f"Normalized name `{nn}` appears under {len(jurs)} different "
                        f"jurisdictions ({', '.join(sorted(jurs))}). Possible mirror shells."
                    ),
                    member_uids=by_name_uids[nn],
                )
            )

    # 4. Hidden hub: highest-betweenness centrality node is *not* a cluster
    #    member but sits in a shared community.
    non_member_hubs = [c for c in centrality if not c.is_member and c.betweenness > 0]
    member_hubs = [c for c in centrality if c.is_member]
    if non_member_hubs and member_hubs:
        top_outside = max(non_member_hubs, key=lambda c: c.betweenness)
        top_inside = max((c.betweenness for c in member_hubs), default=0.0)
        if top_outside.betweenness > 2 * (top_inside or 1e-9):
            flags.append(
                AnomalyFlag(
                    kind="hidden_hub",
                    severity="high",
                    message=(
                        f"Non-member node `{top_outside.entity_uid}` has betweenness "
                        f"{top_outside.betweenness:.4f}, more than 2× the top "
                        f"member's ({top_inside:.4f}). Likely the connective tissue."
                    ),
                    member_uids=[top_outside.entity_uid],
                )
            )

    # 5. LEI / company-number coverage of 0 across an otherwise multi-source
    #    cluster — i.e. the cluster spans sources but none of them anchors
    #    to a real registry. This is "shell-only" by signal.
    if (
        members
        and len({m.source for m in members}) >= 2
        and not any(m.lei or m.company_number for m in members)
    ):
        flags.append(
            AnomalyFlag(
                kind="no_registry_anchor",
                severity="low",
                message=(
                    "Cluster spans multiple sources but no member carries an "
                    "LEI or company_number. Identity rests on names + addresses."
                ),
                member_uids=member_uids,
            )
        )

    _ = member_set
    return flags


# ---------------------------------------------------------------------------
# Investigative-value scoring
# ---------------------------------------------------------------------------


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def score_investigative_value(
    *,
    members: list[MemberAttr],
    intermediaries: list[IntermediaryRepeat],
    addresses: list[AddressRepeat],
    officers: list[OfficerRepeat],
    jurisdictions: JurisdictionProfile,
    sanctions_anchors: list[dict[str, Any]],
    centrality: list[CentralityAnnotation],
    rarity_threshold: int = 10,
    reuse_threshold: int = 5,
) -> InvestigativeFeatures:
    """Each component is in [0, 1]. The total is unweighted; the caller can
    re-weight on top of it. Components and their meanings live alongside the
    scalar so the briefing can explain itself."""
    notes: dict[str, str] = {}

    # --- intermediary rarity: 1.0 if a shared intermediary has a *low*
    #     global edge count (it serves few entities elsewhere — closer to
    #     boutique-nominee territory). 0 if no shared intermediary exists.
    if intermediaries:
        min_global = min(i.n_global_edges for i in intermediaries)
        # Inverse-rarity: lower global degree → higher rarity.
        intermediary_rarity = _clamp01(1.0 - (min_global / max(rarity_threshold * 5, 1)))
        notes["intermediary_rarity"] = (
            f"top shared intermediary appears in {min_global} edge(s) globally; "
            f"lower = more boutique = more interesting"
        )
    else:
        intermediary_rarity = 0.0
        notes["intermediary_rarity"] = "no intermediary serves ≥2 cluster members"

    # --- cross-jurisdiction bridge: jurisdictions count, with extra credit
    #     for crossing into secrecy jurisdictions.
    n_jurs = len(jurisdictions.counts)
    secrecy_share = len(jurisdictions.secrecy_jurisdictions) / n_jurs if n_jurs else 0.0
    bridge_raw = (n_jurs - 1) * 0.4 + secrecy_share * 0.6
    cross_jurisdiction_bridge = _clamp01(bridge_raw)
    notes["cross_jurisdiction_bridge"] = (
        f"{n_jurs} jurisdiction(s); {len(jurisdictions.secrecy_jurisdictions)} secrecy-listed"
    )

    # --- sanctions proximity: 1.0 if any member is directly on a sanctions
    #     list, 0.5 if list-match anchor scores ≥ 0.85, scaled by share.
    direct_sanctions = sum(1 for m in members if m.source == "opensanctions")
    anchor_share = (
        sum(1 for a in sanctions_anchors if float(a.get("score", 0) or 0) >= 0.85)
        / max(len(members), 1)
        if sanctions_anchors
        else 0.0
    )
    sanctions_proximity = _clamp01((direct_sanctions / max(len(members), 1)) + 0.5 * anchor_share)
    notes["sanctions_proximity"] = (
        f"{direct_sanctions} direct opensanctions member(s); "
        f"{len(sanctions_anchors)} list-match anchor(s)"
    )

    # --- registry anchor density: share of members with LEI or company number.
    if members:
        anchored = sum(1 for m in members if m.lei or m.company_number)
        registry_anchor_density = _clamp01(anchored / len(members))
        notes["registry_anchor_density"] = (
            f"{anchored}/{len(members)} member(s) carry an LEI or company_number"
        )
    else:
        registry_anchor_density = 0.0
        notes["registry_anchor_density"] = "no members"

    # --- hidden central entity: a non-member node has betweenness > 2x the
    #     top member's. We already detect this as an anomaly; mirror it as
    #     a feature.
    hidden = 0.0
    member_b = [c.betweenness for c in centrality if c.is_member]
    nonmember_b = [c.betweenness for c in centrality if not c.is_member]
    if nonmember_b:
        top_out = max(nonmember_b)
        top_in = max(member_b or [0.0])
        if top_in == 0 and top_out > 0:
            hidden = 1.0
        elif top_in > 0:
            hidden = _clamp01(top_out / (top_in * 4))
    hidden_central_entity = hidden
    notes["hidden_central_entity"] = (
        "non-member node sits in the cluster's community with elevated betweenness"
        if hidden > 0
        else "no hidden hub detected (or no centrality data)"
    )

    # --- dormant-but-connected: share of dormant members that still have a
    #     repeat-edge to a live address/intermediary/officer.
    dormant_uids = {m.entity_uid for m in members if m.is_dormant}
    connected_dormant = 0
    if dormant_uids:
        for repeat in (*intermediaries, *addresses, *officers):
            if any(u in dormant_uids for u in repeat.member_uids):
                connected_dormant += 1
        dormant_but_connected = _clamp01(connected_dormant / max(len(dormant_uids) * 3, 1))
    else:
        dormant_but_connected = 0.0
    notes["dormant_but_connected"] = (
        f"{len(dormant_uids)} dormant member(s); "
        f"{connected_dormant} shared-feature edge(s) touch them"
    )

    # --- shell reuse: a shared intermediary, address, or officer that also
    #     has high global degree (it's a known hub serving many entities —
    #     classic nominee-director / corporate-services-firm signal).
    reuse_max = 0
    for repeat in (*intermediaries, *addresses, *officers):
        reuse_max = max(reuse_max, repeat.n_global_edges)
    shell_reuse = _clamp01(reuse_max / max(reuse_threshold * 4, 1))
    notes["shell_reuse"] = (
        f"top shared intermediary/address/officer has {reuse_max} edges in the corpus"
    )

    total = (
        intermediary_rarity
        + cross_jurisdiction_bridge
        + sanctions_proximity
        + registry_anchor_density
        + hidden_central_entity
        + dormant_but_connected
        + shell_reuse
    )
    return InvestigativeFeatures(
        intermediary_rarity=intermediary_rarity,
        cross_jurisdiction_bridge=cross_jurisdiction_bridge,
        sanctions_proximity=sanctions_proximity,
        registry_anchor_density=registry_anchor_density,
        hidden_central_entity=hidden_central_entity,
        dormant_but_connected=dormant_but_connected,
        shell_reuse=shell_reuse,
        total=total,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Narrative-path generation
# ---------------------------------------------------------------------------


def build_narrative_paths(
    members: list[MemberAttr],
    *,
    intermediaries: list[IntermediaryRepeat],
    addresses: list[AddressRepeat],
    officers: list[OfficerRepeat],
    sanctions_anchors: list[dict[str, Any]],
    centrality: list[CentralityAnnotation],
    max_paths: int = 3,
) -> list[NarrativePath]:
    """A handful of short, human-readable paths from an anchor member through
    a shared feature into something investigative (cross-jurisdiction sibling,
    sanctions anchor, hidden hub). Quality over quantity."""
    if not members:
        return []
    by_uid = {m.entity_uid: m for m in members}
    anchor_score: dict[str, float] = {}
    # Prefer members that anchor centrality, then registry-anchored ones.
    for c in centrality:
        if c.is_member:
            anchor_score[c.entity_uid] = anchor_score.get(c.entity_uid, 0.0) + c.betweenness
    for m in members:
        if m.lei or m.company_number:
            anchor_score[m.entity_uid] = anchor_score.get(m.entity_uid, 0.0) + 0.5
    ranked = sorted(
        members,
        key=lambda m: (-anchor_score.get(m.entity_uid, 0.0), m.entity_uid),
    )

    out: list[NarrativePath] = []

    for anchor in ranked:
        if len(out) >= max_paths:
            break
        steps: list[str] = []
        steps.append(
            f"`{anchor.entity_uid}` — `{anchor.name}` ({anchor.jurisdiction or '?'}, "
            f"{anchor.source})"
        )
        # Find a shared feature touching this anchor.
        used_feature = None
        for repeat in (*intermediaries, *addresses, *officers):
            if anchor.entity_uid not in repeat.member_uids:
                continue
            used_feature = repeat
            break
        if used_feature is None:
            continue

        if isinstance(used_feature, IntermediaryRepeat):
            steps.append(
                f"→ shares intermediary `{used_feature.name or used_feature.node}` "
                f"({used_feature.country or '?'}) "
                f"[{', '.join(used_feature.leak_labels) or 'no leak label'}]"
            )
        elif isinstance(used_feature, AddressRepeat):
            steps.append(
                f"→ registered at shared address `{(used_feature.text or used_feature.node)[:60]}` "
                f"({used_feature.country or '?'})"
            )
        else:  # OfficerRepeat
            steps.append(
                f"→ shares officer `{used_feature.name or used_feature.node}` "
                f"({used_feature.country or '?'})"
            )

        siblings = [u for u in used_feature.member_uids if u != anchor.entity_uid]
        for sib_uid in siblings[:2]:
            sib = by_uid.get(sib_uid)
            if sib is None:
                continue
            steps.append(
                f"→ `{sib.entity_uid}` — `{sib.name}` ({sib.jurisdiction or '?'}, {sib.source})"
            )

        # Tail with sanctions or hidden hub if any.
        if sanctions_anchors:
            anc = sanctions_anchors[0]
            steps.append(
                f"→ list-match anchor `{anc.get('ref_name') or anc.get('ref_lei') or '?'}`"
            )
            summary_tail = "with a list-match anchor at the end of the chain"
        else:
            hidden = next((c for c in centrality if not c.is_member), None)
            if hidden is not None:
                steps.append(
                    f"→ hidden hub `{hidden.entity_uid}` (betweenness {hidden.betweenness:.4f})"
                )
                summary_tail = "ending at a hidden hub node"
            else:
                summary_tail = "via repeated offshore infrastructure"

        feature_label = (
            "intermediary"
            if isinstance(used_feature, IntermediaryRepeat)
            else "address"
            if isinstance(used_feature, AddressRepeat)
            else "officer"
        )
        summary = (
            f"`{anchor.name}` is structurally linked to {len(siblings)} other "
            f"cluster member(s) through a shared {feature_label}, {summary_tail}."
        )
        out.append(NarrativePath(anchor_uid=anchor.entity_uid, summary=summary, steps=steps))

    return out


# ---------------------------------------------------------------------------
# Suggested targets
# ---------------------------------------------------------------------------


def suggest_investigation_targets(
    *,
    members: list[MemberAttr],
    intermediaries: list[IntermediaryRepeat],
    addresses: list[AddressRepeat],
    centrality: list[CentralityAnnotation],
    features: InvestigativeFeatures,
    sanctions_anchors: list[dict[str, Any]],
) -> list[str]:
    out: list[str] = []
    if intermediaries:
        top = intermediaries[0]
        out.append(
            f"Trace intermediary `{top.name or top.node}` "
            f"({top.country or '?'}) — services {top.n_members_served} cluster members "
            f"and {top.n_global_edges} entities corpus-wide."
        )
    if addresses:
        top = addresses[0]
        out.append(
            f"Walk address `{(top.text or top.node)[:80]}` "
            f"({top.country or '?'}) — shared by {top.n_members_served} cluster members."
        )
    if features.hidden_central_entity > 0.5:
        hidden_hub = next((c for c in centrality if not c.is_member), None)
        if hidden_hub is not None:
            out.append(
                f"Pull connections from `{hidden_hub.entity_uid}` — non-member node "
                f"with betweenness {hidden_hub.betweenness:.4f}; appears to glue the cluster."
            )
    if sanctions_anchors:
        anc = sanctions_anchors[0]
        out.append(
            f"Validate sanctions anchor: {anc.get('ref_name')} "
            f"(LEI {anc.get('ref_lei') or '?'}, score {anc.get('score') or '?'})."
        )
    if not (sanctions_anchors or any(m.lei or m.company_number for m in members)):
        out.append(
            "Cluster has no registry or sanctions anchor — confirm whether any member "
            "exists in a national registry before publishing identity claims."
        )
    if not out:
        out.append("No automatic suggestions — review the tables manually.")
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def build_explanation(
    cluster_id: int,
    member_uids: list[str],
    *,
    company_df: pl.DataFrame,
    edges_df: pl.DataFrame | None,
    addresses_df: pl.DataFrame | None = None,
    officers_df: pl.DataFrame | None = None,
    intermediaries_df: pl.DataFrame | None = None,
    centrality_df: pl.DataFrame | None = None,
    sanctions_df: pl.DataFrame | None = None,
) -> ClusterExplanation:
    """Single-call assembly. All inputs except ``company_df`` are optional;
    missing inputs degrade gracefully (empty lists, zeroed feature components)."""
    members = gather_member_attrs(company_df, member_uids)
    intermediaries, addresses, officers = gather_repeats(
        [m.entity_uid for m in members],
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )
    jurisdictions = compute_jurisdiction_profile(members)
    centrality = annotate_centrality(centrality_df, [m.entity_uid for m in members])
    sanctions_anchors = filter_sanctions_anchors(sanctions_df, [m.entity_uid for m in members])
    anomalies = detect_anomalies(members, edges_df=edges_df, centrality=centrality)
    features = score_investigative_value(
        members=members,
        intermediaries=intermediaries,
        addresses=addresses,
        officers=officers,
        jurisdictions=jurisdictions,
        sanctions_anchors=sanctions_anchors,
        centrality=centrality,
    )
    paths = build_narrative_paths(
        members,
        intermediaries=intermediaries,
        addresses=addresses,
        officers=officers,
        sanctions_anchors=sanctions_anchors,
        centrality=centrality,
    )
    suggested = suggest_investigation_targets(
        members=members,
        intermediaries=intermediaries,
        addresses=addresses,
        centrality=centrality,
        features=features,
        sanctions_anchors=sanctions_anchors,
    )

    leaks: set[str] = set()
    for repeat in (*intermediaries, *addresses, *officers):
        leaks.update(repeat.leak_labels)
    sources_present = sorted({m.source for m in members})

    return ClusterExplanation(
        cluster_id=cluster_id,
        members=members,
        intermediaries=intermediaries,
        addresses=addresses,
        officers=officers,
        jurisdictions=jurisdictions,
        sanctions_anchors=sanctions_anchors,
        centrality=centrality,
        anomalies=anomalies,
        paths=paths,
        features=features,
        leaks_present=sorted(leaks),
        sources_present=sources_present,
        suggested_targets=suggested,
    )


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _md_escape(s: Any) -> str:
    if s is None:
        return ""
    return str(s).replace("|", "/").replace("\n", " ").strip()


def render_explanation_markdown(
    expl: ClusterExplanation,
    *,
    dedupe_run_id: str | None = None,
    inputs_meta: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Investigator-ready briefing. Pure string-in, string-out."""
    generated_at = generated_at or datetime.now(UTC)
    inputs_meta = inputs_meta or {}
    lines: list[str] = []
    lines.append(f"# Cluster {expl.cluster_id} — investigative briefing")
    lines.append("")
    lines.append(
        f"Generated `{generated_at.isoformat(timespec='seconds')}`"
        + (f" from dedupe run `{dedupe_run_id}`." if dedupe_run_id else ".")
    )
    lines.append("")
    lines.append(
        "> **Hypothesis, not proof.** Repeated intermediaries and addresses are "
        "structural signals, not findings. Every link below requires human review "
        "before any identity-linked claim is made."
    )
    lines.append("")

    # ----- Headline -----
    lines.append("## Headline")
    lines.append("")
    lines.append(
        f"- **{len(expl.members)} member(s)** across **{len(expl.sources_present)} source(s)** "
        f"({', '.join(expl.sources_present) or 'none'})."
    )
    if expl.jurisdictions.counts:
        jur_str = ", ".join(
            f"{j}={n}" for j, n in sorted(expl.jurisdictions.counts.items(), key=lambda kv: -kv[1])
        )
        lines.append(
            f"- **Jurisdictions:** {jur_str}"
            + (
                f" (secrecy-listed: {', '.join(expl.jurisdictions.secrecy_jurisdictions)})"
                if expl.jurisdictions.secrecy_jurisdictions
                else ""
            )
            + "."
        )
    else:
        lines.append("- **Jurisdictions:** none recorded.")
    if expl.leaks_present:
        lines.append(f"- **Leaks present:** {', '.join(expl.leaks_present)}.")
    if expl.intermediaries:
        top = expl.intermediaries[0]
        lines.append(
            f"- **Top shared intermediary:** `{top.name or top.node}` "
            f"({top.country or '?'}) — services {top.n_members_served}/{len(expl.members)} members."
        )
    if expl.addresses:
        top = expl.addresses[0]
        lines.append(
            f"- **Top shared address:** `{(top.text or top.node)[:80]}` "
            f"— shared by {top.n_members_served}/{len(expl.members)} members."
        )
    if expl.sanctions_anchors:
        lines.append(
            f"- **Sanctions adjacency:** {len(expl.sanctions_anchors)} list-match anchor(s)."
        )
    lines.append("")

    # ----- Investigative value -----
    f = expl.features
    lines.append("## Why this matters")
    lines.append("")
    lines.append(
        f"**Investigative-value score: {f.total:.2f} / 7.00** "
        "(unweighted sum of components below; each in [0, 1])."
    )
    lines.append("")
    lines.append("| component | value | meaning |")
    lines.append("| --- | ---: | --- |")
    for name, val in [
        ("intermediary_rarity", f.intermediary_rarity),
        ("cross_jurisdiction_bridge", f.cross_jurisdiction_bridge),
        ("sanctions_proximity", f.sanctions_proximity),
        ("registry_anchor_density", f.registry_anchor_density),
        ("hidden_central_entity", f.hidden_central_entity),
        ("dormant_but_connected", f.dormant_but_connected),
        ("shell_reuse", f.shell_reuse),
    ]:
        lines.append(f"| `{name}` | {val:.2f} | {_md_escape(f.notes.get(name, ''))} |")
    lines.append("")

    # ----- Members -----
    lines.append("## Members")
    lines.append("")
    lines.append("| entity_uid | source | name | jur | status | lei | company_number |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for m in expl.members:
        lines.append(
            "| `{uid}` | {src} | `{name}` | {jur} | {st} | {lei} | {cn} |".format(
                uid=m.entity_uid,
                src=m.source,
                name=_md_escape(m.name)[:60],
                jur=m.jurisdiction or "?",
                st=_md_escape(m.status),
                lei=m.lei or "",
                cn=m.company_number or "",
            )
        )
    lines.append("")

    # ----- Repeats -----
    if expl.intermediaries:
        lines.append("## Repeated intermediaries")
        lines.append("")
        lines.append("| node | name | country | served | global_deg | leaks |")
        lines.append("| --- | --- | --- | ---: | ---: | --- |")
        for r in expl.intermediaries:
            lines.append(
                "| `{n}` | {nm} | {c} | {s} | {g} | {lk} |".format(
                    n=r.node,
                    nm=_md_escape(r.name)[:60],
                    c=r.country or "?",
                    s=r.n_members_served,
                    g=r.n_global_edges,
                    lk=_md_escape(", ".join(r.leak_labels)),
                )
            )
        lines.append("")

    if expl.addresses:
        lines.append("## Repeated addresses")
        lines.append("")
        lines.append("| node | text | country | served | global_deg | leaks |")
        lines.append("| --- | --- | --- | ---: | ---: | --- |")
        for r in expl.addresses:
            lines.append(
                "| `{n}` | {t} | {c} | {s} | {g} | {lk} |".format(
                    n=r.node,
                    t=_md_escape(r.text)[:80],
                    c=r.country or "?",
                    s=r.n_members_served,
                    g=r.n_global_edges,
                    lk=_md_escape(", ".join(r.leak_labels)),
                )
            )
        lines.append("")

    if expl.officers:
        lines.append("## Repeated officers")
        lines.append("")
        lines.append("| node | name | country | served | global_deg | leaks |")
        lines.append("| --- | --- | --- | ---: | ---: | --- |")
        for r in expl.officers:
            lines.append(
                "| `{n}` | {nm} | {c} | {s} | {g} | {lk} |".format(
                    n=r.node,
                    nm=_md_escape(r.name)[:60],
                    c=r.country or "?",
                    s=r.n_members_served,
                    g=r.n_global_edges,
                    lk=_md_escape(", ".join(r.leak_labels)),
                )
            )
        lines.append("")

    # ----- Centrality -----
    if expl.centrality:
        lines.append("## Centrality")
        lines.append("")
        lines.append("| entity_uid | member? | community | eigenvector | betweenness | degree |")
        lines.append("| --- | :-: | ---: | ---: | ---: | ---: |")
        for c in expl.centrality:
            lines.append(
                "| `{uid}` | {mb} | {co} | {eg:.4f} | {bc:.4f} | {dg} |".format(
                    uid=c.entity_uid,
                    mb="✓" if c.is_member else "·",
                    co=c.community_id if c.community_id is not None else "",
                    eg=c.eigenvector,
                    bc=c.betweenness,
                    dg=c.total_degree,
                )
            )
        lines.append("")

    # ----- Sanctions -----
    if expl.sanctions_anchors:
        lines.append("## Sanctions / list-match anchors")
        lines.append("")
        lines.append("| target_uid | ref_name | ref_lei | jur | score |")
        lines.append("| --- | --- | --- | --- | ---: |")
        for a in expl.sanctions_anchors:
            lines.append(
                "| `{t}` | `{rn}` | `{lei}` | {j} | {s} |".format(
                    t=a.get("target_entity_uid", ""),
                    rn=_md_escape(a.get("ref_name"))[:60],
                    lei=a.get("ref_lei") or "",
                    j=a.get("ref_jurisdiction") or "?",
                    s=f"{float(a['score']):.3f}" if a.get("score") is not None else "?",
                )
            )
        lines.append("")

    # ----- Anomalies -----
    lines.append("## Anomalies / contradictions")
    lines.append("")
    if expl.anomalies:
        for a in expl.anomalies:
            lines.append(f"- **[{a.severity}] {a.kind}** — {_md_escape(a.message)}")
    else:
        lines.append("_No automatic anomalies surfaced._")
    lines.append("")

    # ----- Narrative paths -----
    lines.append("## Narrative paths")
    lines.append("")
    if expl.paths:
        for i, p in enumerate(expl.paths, start=1):
            lines.append(f"### Path {i}")
            lines.append("")
            lines.append(f"_{p.summary}_")
            lines.append("")
            for s in p.steps:
                lines.append(f"- {s}")
            lines.append("")
    else:
        lines.append("_No automatic paths generated (insufficient shared features)._ ")
        lines.append("")

    # ----- Suggested targets -----
    lines.append("## Suggested investigation targets")
    lines.append("")
    for t in expl.suggested_targets:
        lines.append(f"- {t}")
    lines.append("")

    # ----- Provenance -----
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Cluster id: `{expl.cluster_id}`")
    lines.append(f"- Members: {len(expl.members)}")
    lines.append(f"- Sources present: {', '.join(expl.sources_present) or 'none'}")
    if dedupe_run_id:
        lines.append(f"- Dedupe run: `{dedupe_run_id}`")
    for k, v in inputs_meta.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    return "\n".join(lines)


def default_explanation_path(reports_root: Any, cluster_id: int) -> Any:
    from pathlib import Path

    return Path(reports_root) / "cluster_explanations" / f"cluster_{cluster_id}.md"
