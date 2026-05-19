"""Subcluster extraction — slice a huge cluster into narratable pieces.

33k-member dedupe clusters are unusable as single units. This module
identifies five kinds of investigatable substructure:

1. ``community`` — Louvain communities of the cluster's incident
   subgraph; the natural "neighborhoods" the larger cluster contains.
2. ``bridge_neighborhood`` — sets of members straddling a bridge edge
   (one whose removal disconnects the subgraph). Often the connective
   tissue worth following.
3. ``rare_intermediary_group`` — the cluster members served by a
   shared intermediary that has a *low* corpus-wide degree (boutique
   nominee territory).
4. ``high_centrality_core`` — top-K cluster members by centrality plus
   their immediate cluster-side neighbors; the structural backbone.
5. ``shell_reuse_group`` — cluster members touching a shared feature
   whose corpus-wide degree is *high* (known shell infrastructure).

Each ``Subcluster`` is just a member-uid subset + a seed node + a
short narrative + an interest score. Downstream callers feed the
subset back into ``cluster_explainer.build_explanation`` to get a full
per-subcluster briefing.

Pure functions; the NetworkX work is local to the call.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import polars as pl

    from shellnet.investigations.cluster_explainer import (
        AddressRepeat,
        CentralityAnnotation,
        IntermediaryRepeat,
        OfficerRepeat,
    )


@dataclass
class Subcluster:
    """A narratable slice of a larger cluster."""

    subcluster_id: str  # stable id, e.g. "comm_3" / "bridge_icij:200--icij:201"
    kind: str  # community | bridge_neighborhood | rare_intermediary_group |
    #            high_centrality_core | shell_reuse_group
    member_uids: list[str]
    seed_node: str | None = None  # the feature / bridge / community label
    seed_label: str | None = None  # human-readable label of the seed
    narrative: str = ""
    interest_score: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.member_uids)


# Tunable thresholds.
RARE_INTERMEDIARY_GLOBAL_DEGREE = 10  # corpus-wide edge count below which a
# shared intermediary qualifies as "rare/boutique"
SHELL_HUB_THRESHOLD = 25  # corpus-wide edge count above which a shared
# feature qualifies as "known shell infrastructure"
HIGH_CENTRALITY_TOP_K = 5  # how many top-centrality members anchor the core
MIN_COMMUNITY_SIZE = 3  # smaller Louvain communities are dropped
MAX_SUBCLUSTERS = 30  # safety cap


# ---------------------------------------------------------------------------
# Per-kind extractors
# ---------------------------------------------------------------------------


def _extract_communities(member_uids: list[str], edges_df: pl.DataFrame | None) -> list[Subcluster]:
    """Louvain on the cluster's incident undirected subgraph. Each
    community of ≥``MIN_COMMUNITY_SIZE`` cluster members becomes a
    subcluster."""
    if not member_uids or edges_df is None or edges_df.height == 0:
        return []
    import networkx as nx
    import polars as pl

    members = set(member_uids)
    sub = edges_df.filter(
        pl.col("src_node").is_in(member_uids) | pl.col("dst_node").is_in(member_uids)
    )
    if sub.height == 0:
        return []
    g = nx.Graph()
    g.add_nodes_from(member_uids)
    for r in sub.iter_rows(named=True):
        s, d = r["src_node"], r["dst_node"]
        # Keep only edges that connect two cluster members, OR a member to
        # a side-node (officer/address/intermediary). The side-node lets
        # community detection group members that share an officer.
        if s in members or d in members:
            g.add_edge(s, d)

    if g.number_of_edges() == 0:
        return []

    try:
        communities = nx.community.louvain_communities(g, seed=42)
    except Exception:  # noqa: BLE001
        return []

    out: list[Subcluster] = []
    for cid, comm in enumerate(communities):
        # Project the community back onto cluster members only.
        members_in_comm = sorted(n for n in comm if n in members)
        if len(members_in_comm) < MIN_COMMUNITY_SIZE:
            continue
        # Use the community's modularity contribution as the interest score.
        score = float(len(members_in_comm)) / max(len(member_uids), 1)
        out.append(
            Subcluster(
                subcluster_id=f"comm_{cid}",
                kind="community",
                member_uids=members_in_comm,
                seed_node=None,
                seed_label=f"Louvain community {cid}",
                narrative=(
                    f"Louvain community {cid} — {len(members_in_comm)} of "
                    f"{len(member_uids)} cluster members "
                    f"({100 * score:.0f}% of the cluster) form a dense sub-neighborhood."
                ),
                interest_score=score,
                evidence={
                    "n_members_in_community": len(members_in_comm),
                    "n_total_members": len(member_uids),
                },
            )
        )
    return out


def _extract_bridge_neighborhoods(
    member_uids: list[str], edges_df: pl.DataFrame | None
) -> list[Subcluster]:
    """Bridge edges of the cluster's incident undirected subgraph.
    Each bridge becomes a subcluster of the two endpoints + their
    immediate neighbors among cluster members."""
    if not member_uids or edges_df is None or edges_df.height == 0:
        return []
    import networkx as nx
    import polars as pl

    members = set(member_uids)
    sub = edges_df.filter(
        pl.col("src_node").is_in(member_uids) | pl.col("dst_node").is_in(member_uids)
    )
    if sub.height == 0:
        return []
    g = nx.Graph()
    g.add_nodes_from(member_uids)
    for r in sub.iter_rows(named=True):
        s, d = r["src_node"], r["dst_node"]
        if s in members or d in members:
            g.add_edge(s, d)
    if g.number_of_edges() == 0:
        return []

    out: list[Subcluster] = []
    try:
        bridges = list(nx.bridges(g))
    except nx.NetworkXNotImplemented:
        return []
    for u, v in bridges:
        # Only keep bridges incident to at least one cluster member.
        if not ({u, v} & members):
            continue
        nbrs = set()
        for endpoint in (u, v):
            if endpoint not in g:
                continue
            for nb in g.neighbors(endpoint):
                if nb in members:
                    nbrs.add(nb)
        neighborhood = sorted(nbrs)
        if len(neighborhood) < 2:
            continue
        label = f"{u}↔{v}"
        out.append(
            Subcluster(
                subcluster_id=f"bridge_{u}__{v}",
                kind="bridge_neighborhood",
                member_uids=neighborhood,
                seed_node=u,
                seed_label=label,
                narrative=(
                    f"Bridge edge `{label}` — removing it disconnects the "
                    f"subgraph. {len(neighborhood)} cluster member(s) sit "
                    "on either side; this is the connective tissue."
                ),
                interest_score=1.0,  # bridges are intrinsically interesting
                evidence={"bridge_edge": [u, v], "neighbors": neighborhood},
            )
        )
    return out


def _extract_rare_intermediary_groups(
    intermediaries: list[IntermediaryRepeat],
    *,
    rare_threshold: int = RARE_INTERMEDIARY_GLOBAL_DEGREE,
) -> list[Subcluster]:
    """For each intermediary in ``intermediaries`` with corpus-wide
    degree below ``rare_threshold``, the members it serves form a
    subcluster — boutique-nominee territory."""
    out: list[Subcluster] = []
    for inter in intermediaries:
        if inter.n_global_edges > rare_threshold:
            continue
        if inter.n_members_served < 2:
            continue
        label = inter.name or inter.node
        out.append(
            Subcluster(
                subcluster_id=f"rare_inter_{inter.node}",
                kind="rare_intermediary_group",
                member_uids=sorted(inter.member_uids),
                seed_node=inter.node,
                seed_label=label,
                narrative=(
                    f"Rare intermediary `{label}` ({inter.country or '?'}) — "
                    f"only {inter.n_global_edges} edge(s) in the corpus, "
                    f"yet serves {inter.n_members_served} cluster members."
                ),
                interest_score=1.5,  # rarity is a strong signal
                evidence={
                    "intermediary_node": inter.node,
                    "n_global_edges": inter.n_global_edges,
                    "rare_threshold": rare_threshold,
                },
            )
        )
    return out


def _extract_high_centrality_core(
    centrality: list[CentralityAnnotation],
    *,
    top_k: int = HIGH_CENTRALITY_TOP_K,
) -> list[Subcluster]:
    """Top-``top_k`` cluster members by betweenness centrality."""
    if not centrality:
        return []
    member_centrality = [c for c in centrality if c.is_member]
    if len(member_centrality) < 2:
        return []
    ranked = sorted(member_centrality, key=lambda c: -c.betweenness)[:top_k]
    if all(c.betweenness == 0 for c in ranked):
        return []
    members_in_core = sorted({c.entity_uid for c in ranked})
    return [
        Subcluster(
            subcluster_id="core_betweenness",
            kind="high_centrality_core",
            member_uids=members_in_core,
            seed_node=ranked[0].entity_uid,
            seed_label=f"top-{len(members_in_core)} by betweenness",
            narrative=(
                f"Structural backbone of the cluster — the {len(members_in_core)} "
                f"members with the highest betweenness centrality, "
                f"led by `{ranked[0].entity_uid}` ({ranked[0].betweenness:.4f})."
            ),
            interest_score=0.8,
            evidence={
                "anchor": ranked[0].entity_uid,
                "top_betweenness": ranked[0].betweenness,
                "ranked_members": members_in_core,
            },
        )
    ]


def _extract_shell_reuse_groups(
    intermediaries: list[IntermediaryRepeat],
    addresses: list[AddressRepeat],
    officers: list[OfficerRepeat],
    *,
    shell_threshold: int = SHELL_HUB_THRESHOLD,
) -> list[Subcluster]:
    """For each shared feature with corpus-wide degree ≥``shell_threshold``,
    the members touching it form a subcluster — known shell infrastructure."""
    out: list[Subcluster] = []
    for repeat, kind in (
        *((i, "intermediary") for i in intermediaries),
        *((a, "address") for a in addresses),
        *((o, "officer") for o in officers),
    ):
        if repeat.n_global_edges < shell_threshold:
            continue
        if repeat.n_members_served < 2:
            continue
        label = getattr(repeat, "name", None) or getattr(repeat, "text", None) or repeat.node
        out.append(
            Subcluster(
                subcluster_id=f"shell_reuse_{repeat.node}",
                kind="shell_reuse_group",
                member_uids=sorted(repeat.member_uids),
                seed_node=repeat.node,
                seed_label=str(label)[:80],
                narrative=(
                    f"Shell reuse — {kind} `{label}` has "
                    f"{repeat.n_global_edges} corpus edges and touches "
                    f"{repeat.n_members_served} cluster members. Likely "
                    f"known shell infrastructure."
                ),
                interest_score=1.2,
                evidence={
                    "kind": kind,
                    "feature_node": repeat.node,
                    "n_global_edges": repeat.n_global_edges,
                    "shell_threshold": shell_threshold,
                },
            )
        )
    return out


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def extract_subclusters(
    cluster_id: int,
    member_uids: list[str],
    *,
    edges_df: pl.DataFrame | None = None,
    intermediaries: list[IntermediaryRepeat] | None = None,
    addresses: list[AddressRepeat] | None = None,
    officers: list[OfficerRepeat] | None = None,
    centrality: list[CentralityAnnotation] | None = None,
    max_subclusters: int = MAX_SUBCLUSTERS,
) -> list[Subcluster]:
    """Run every extractor and concatenate the results, sorted by
    ``interest_score`` desc. Duplicate subclusters (same member-uid
    set) are deduped, keeping the higher-scoring representative."""
    intermediaries = intermediaries or []
    addresses = addresses or []
    officers = officers or []
    centrality = centrality or []

    subs: list[Subcluster] = []
    subs.extend(_extract_communities(member_uids, edges_df))
    subs.extend(_extract_bridge_neighborhoods(member_uids, edges_df))
    subs.extend(_extract_rare_intermediary_groups(intermediaries))
    subs.extend(_extract_high_centrality_core(centrality))
    subs.extend(_extract_shell_reuse_groups(intermediaries, addresses, officers))

    # Dedupe by member set, keep highest-scoring.
    subs.sort(key=lambda s: -s.interest_score)
    out: list[Subcluster] = []
    seen: set[frozenset[str]] = set()
    for s in subs:
        sig = frozenset(s.member_uids)
        if sig in seen:
            continue
        seen.add(sig)
        out.append(s)
        if len(out) >= max_subclusters:
            break

    _ = cluster_id  # cluster_id reserved for future per-id stable IDs
    return out


def render_subcluster_index_markdown(
    cluster_id: int,
    subclusters: list[Subcluster],
    *,
    dedupe_run_id: str | None = None,
) -> str:
    """Top-level index that maps each subcluster's id → kind → narrative.
    Per-subcluster full briefings are produced by feeding ``member_uids``
    back into ``cluster_explainer.build_explanation``."""
    lines: list[str] = []
    lines.append(f"# Cluster {cluster_id} — subcluster index")
    lines.append("")
    lines.append(f"From dedupe run `{dedupe_run_id}`." if dedupe_run_id else "")
    if dedupe_run_id:
        lines.append("")
    if not subclusters:
        lines.append("_No subclusters extracted. The cluster may be too small or too sparse._")
        return "\n".join(lines)
    by_kind: dict[str, list[Subcluster]] = defaultdict(list)
    for s in subclusters:
        by_kind[s.kind].append(s)
    lines.append(
        f"**{len(subclusters)} subcluster(s)** across "
        f"**{len(by_kind)} kind(s)**: "
        + ", ".join(f"{k} ({len(v)})" for k, v in sorted(by_kind.items()))
        + "."
    )
    lines.append("")
    lines.append("| # | id | kind | size | interest | narrative |")
    lines.append("| ---: | --- | --- | ---: | ---: | --- |")
    for i, s in enumerate(subclusters, start=1):
        narrative = s.narrative.replace("|", "/").replace("\n", " ").strip()[:120]
        lines.append(
            f"| {i} | `{s.subcluster_id}` | {s.kind} | {s.size} | "
            f"{s.interest_score:.2f} | {narrative} |"
        )
    return "\n".join(lines)
