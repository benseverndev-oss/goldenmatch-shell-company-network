"""Narrative-path generation — multi-hop investigative chains.

Where ``cluster_explainer.build_explanation`` already knows which
shared features link cluster members, this module walks one or two
hops *past* the cluster sibling into a "terminus anchor" — a
registry-anchored entity (LEI / company number), a sanctions list-match
hit, or a hidden hub identified by centrality. The output is a small
list of typed, scored paths suitable for both Markdown briefings and
storyboard generation.

Pure functions only; no I/O, no logging at import.
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
        MemberAttr,
        OfficerRepeat,
    )


@dataclass
class PathStep:
    """One node in a narrative path. ``kind`` is the role the node plays
    in the story (``member``, ``officer``, ``address``, ``intermediary``,
    ``entity``, ``anchor``); ``label`` is the human-readable string the
    Markdown renderer shows."""

    kind: str
    node: str
    label: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class NarrativePath:
    """A 3-to-6 step chain from an anchor cluster member to a terminus.

    ``terminus_kind`` is one of ``sanctions`` | ``registry_anchor`` |
    ``hidden_hub`` | ``sibling`` | ``none``; it's the most-anchored
    endpoint the walker could find from the anchor. ``score`` is a
    heuristic for ranking paths (longer + better terminus + heterogeneous
    edges scores higher)."""

    anchor_uid: str
    summary: str
    steps: list[PathStep]
    terminus_kind: str
    score: float = 0.0


_KIND_SCORE = {
    "sanctions": 4.0,
    "registry_anchor": 3.0,
    "hidden_hub": 2.5,
    "sibling": 1.0,
    "none": 0.0,
}


def _label_for_repeat(repeat: Any, kind: str) -> str:
    if kind == "address":
        return (getattr(repeat, "text", None) or repeat.node)[:80]
    return (getattr(repeat, "name", None) or repeat.node)[:60]


def _classify_edge_kind(kind_raw: str | None) -> str:
    k = (kind_raw or "").lower()
    if "address" in k:
        return "address"
    if "intermediar" in k:
        return "intermediary"
    if "officer" in k:
        return "officer"
    return "other"


def _walk_one_hop_from_sibling(
    sibling_uid: str,
    cluster_uids: set[str],
    *,
    edges_df: pl.DataFrame | None,
    addresses_df_lookup: dict[str, dict[str, Any]],
    officers_df_lookup: dict[str, dict[str, Any]],
    intermediaries_df_lookup: dict[str, dict[str, Any]],
    company_by_uid: dict[str, dict[str, Any]],
) -> list[PathStep]:
    """From a sibling cluster member, take one hop outward. Returns the
    most-informative next-step PathStep if any, else an empty list."""
    if edges_df is None or edges_df.height == 0:
        return []
    import polars as pl  # runtime-only

    sub = edges_df.filter((pl.col("src_node") == sibling_uid) | (pl.col("dst_node") == sibling_uid))
    if sub.height == 0:
        return []

    # Score candidates: prefer addresses (geographic anchor) and intermediaries
    # over officers; prefer nodes pointing into the unified company table
    # (their existence means they're cross-referenced).
    best: tuple[float, PathStep] | None = None
    for r in sub.iter_rows(named=True):
        s, d = r["src_node"], r["dst_node"]
        other = d if s == sibling_uid else s
        if other in cluster_uids:
            continue  # stay outside the cluster
        kind = _classify_edge_kind(r.get("kind_raw"))
        if kind == "other":
            # Could still be an entity-to-entity edge; check the unified table.
            if other in company_by_uid:
                co = company_by_uid[other]
                label = f"`{co.get('name') or other}` ({co.get('jurisdiction') or '?'}, {co.get('source') or '?'})"
                step = PathStep(
                    kind="entity",
                    node=other,
                    label=label,
                    extra={"jurisdiction": co.get("jurisdiction"), "source": co.get("source")},
                )
                priority = 1.5
            else:
                continue
        elif kind == "address":
            sid = other.split(":", 1)[1] if ":" in other else other
            meta = addresses_df_lookup.get(sid) or {}
            label = (meta.get("raw_text") or meta.get("normalized_text") or other)[:80]
            step = PathStep(
                kind="address",
                node=other,
                label=label,
                extra={"country": meta.get("country"), "leak": r.get("source_label")},
            )
            priority = 2.0
        elif kind == "intermediary":
            sid = other.split(":", 1)[1] if ":" in other else other
            meta = intermediaries_df_lookup.get(sid) or {}
            label = (meta.get("name") or other)[:60]
            step = PathStep(
                kind="intermediary",
                node=other,
                label=label,
                extra={"country": meta.get("country"), "leak": r.get("source_label")},
            )
            priority = 1.8
        else:  # officer
            sid = other.split(":", 1)[1] if ":" in other else other
            meta = officers_df_lookup.get(sid) or {}
            label = (meta.get("name") or other)[:60]
            step = PathStep(
                kind="officer",
                node=other,
                label=label,
                extra={"country": meta.get("country"), "leak": r.get("source_label")},
            )
            priority = 1.3
        if best is None or priority > best[0]:
            best = (priority, step)
    return [best[1]] if best else []


def _terminus_from_member(
    member: MemberAttr,
    *,
    sanctions_anchors: list[dict[str, Any]],
) -> tuple[str, PathStep] | None:
    """If ``member`` is itself an anchor terminus, return the appropriate
    step. Direct opensanctions membership wins over LEI/company-number."""
    if member.source == "opensanctions":
        return (
            "sanctions",
            PathStep(
                kind="anchor",
                node=member.entity_uid,
                label=f"sanctions list entry `{member.name}` ({member.jurisdiction or '?'})",
                extra={"anchor_kind": "direct_sanctions"},
            ),
        )
    target_uid = member.entity_uid
    for anc in sanctions_anchors:
        if anc.get("target_entity_uid") == target_uid:
            return (
                "sanctions",
                PathStep(
                    kind="anchor",
                    node=target_uid,
                    label=(
                        f"list-match anchor `{anc.get('ref_name') or anc.get('ref_lei') or '?'}`"
                    ),
                    extra={"anchor_kind": "list_match", "score": anc.get("score")},
                ),
            )
    if member.lei or member.company_number:
        return (
            "registry_anchor",
            PathStep(
                kind="anchor",
                node=member.entity_uid,
                label=(
                    f"registry anchor `{member.lei or member.company_number}` ({member.source})"
                ),
                extra={
                    "lei": member.lei,
                    "company_number": member.company_number,
                },
            ),
        )
    return None


def _select_anchors(
    members: list[MemberAttr],
    centrality: list[CentralityAnnotation],
    *,
    max_anchors: int,
) -> list[MemberAttr]:
    """Rank cluster members by anchor-worthiness. Higher betweenness +
    presence of registry id pushes them up. Returns ``members`` sorted
    desc."""
    by_uid = {m.entity_uid: m for m in members}
    scores: dict[str, float] = defaultdict(float)
    for c in centrality:
        if c.is_member and c.entity_uid in by_uid:
            scores[c.entity_uid] += c.betweenness
    for m in members:
        if m.lei or m.company_number:
            scores[m.entity_uid] += 0.5
        # Direct sanctions members are themselves the story — keep them high.
        if m.source == "opensanctions":
            scores[m.entity_uid] += 2.0
    ranked = sorted(
        members,
        key=lambda m: (-scores.get(m.entity_uid, 0.0), m.entity_uid),
    )
    return ranked[:max_anchors]


def find_paths(
    members: list[MemberAttr],
    *,
    intermediaries: list[IntermediaryRepeat],
    addresses: list[AddressRepeat],
    officers: list[OfficerRepeat],
    sanctions_anchors: list[dict[str, Any]],
    centrality: list[CentralityAnnotation],
    edges_df: pl.DataFrame | None = None,
    company_df: pl.DataFrame | None = None,
    addresses_df: pl.DataFrame | None = None,
    officers_df: pl.DataFrame | None = None,
    intermediaries_df: pl.DataFrame | None = None,
    max_hops: int = 5,
    max_paths: int = 3,
) -> list[NarrativePath]:
    """Build short narrative chains.

    Anchor → shared-feature → sibling → (optional) one-hop outward →
    terminus. The terminus is whichever of the following can be reached:
    a sanctions anchor, a registry-anchored entity (LEI / company
    number), or a hidden-hub centrality node. If none can be reached
    the path falls back to the sibling (``terminus_kind='sibling'``).
    Paths are sorted by score descending.
    """
    if not members:
        return []
    cluster_uids = {m.entity_uid for m in members}
    by_uid = {m.entity_uid: m for m in members}

    # Pre-compute side lookups so we don't rebuild them per anchor.
    addr_lookup: dict[str, dict[str, Any]] = {}
    if addresses_df is not None and addresses_df.height:
        for r in addresses_df.iter_rows(named=True):
            sid = r.get("source_id")
            if sid is not None:
                addr_lookup[str(sid)] = r
    off_lookup: dict[str, dict[str, Any]] = {}
    if officers_df is not None and officers_df.height:
        for r in officers_df.iter_rows(named=True):
            sid = r.get("source_id")
            if sid is not None:
                off_lookup[str(sid)] = r
    inter_lookup: dict[str, dict[str, Any]] = {}
    if intermediaries_df is not None and intermediaries_df.height:
        for r in intermediaries_df.iter_rows(named=True):
            sid = r.get("source_id")
            if sid is not None:
                inter_lookup[str(sid)] = r
    company_by_uid: dict[str, dict[str, Any]] = {}
    if company_df is not None and company_df.height:
        for r in company_df.iter_rows(named=True):
            uid = r.get("entity_uid")
            if uid is not None:
                company_by_uid[uid] = r

    hidden_hub: PathStep | None = None
    for c in centrality:
        if not c.is_member and c.betweenness > 0:
            hidden_hub = PathStep(
                kind="anchor",
                node=c.entity_uid,
                label=f"hidden hub `{c.entity_uid}` (betweenness {c.betweenness:.4f})",
                extra={"anchor_kind": "hidden_hub", "betweenness": c.betweenness},
            )
            break

    anchors = _select_anchors(members, centrality, max_anchors=max_paths * 2)

    candidates: list[NarrativePath] = []

    for anchor in anchors:
        # 1. Find a shared feature touching this anchor.
        repeats_options: list[tuple[Any, str]] = [
            *((r, "intermediary") for r in intermediaries),
            *((r, "address") for r in addresses),
            *((r, "officer") for r in officers),
        ]
        feature = next(
            ((rep, kind) for rep, kind in repeats_options if anchor.entity_uid in rep.member_uids),
            None,
        )
        if feature is None:
            # No shared feature — skip; the suggestion-targets section will
            # still call this out.
            continue
        repeat, kind = feature

        steps: list[PathStep] = [
            PathStep(
                kind="member",
                node=anchor.entity_uid,
                label=(f"`{anchor.name}` ({anchor.jurisdiction or '?'}, {anchor.source})"),
                extra={
                    "lei": anchor.lei,
                    "company_number": anchor.company_number,
                },
            ),
            PathStep(
                kind=kind,
                node=repeat.node,
                label=_label_for_repeat(repeat, kind),
                extra={
                    "country": repeat.country,
                    "leak_labels": repeat.leak_labels,
                    "n_global_edges": repeat.n_global_edges,
                },
            ),
        ]

        # 2. Hop to a sibling cluster member served by the feature.
        siblings = [u for u in repeat.member_uids if u != anchor.entity_uid]
        sibling = by_uid.get(siblings[0]) if siblings else None
        if sibling is not None:
            steps.append(
                PathStep(
                    kind="member",
                    node=sibling.entity_uid,
                    label=(f"`{sibling.name}` ({sibling.jurisdiction or '?'}, {sibling.source})"),
                    extra={
                        "lei": sibling.lei,
                        "company_number": sibling.company_number,
                    },
                )
            )

        # 3. Terminus: if the sibling itself is anchor-worthy, the path
        #    ends there. Otherwise, take one hop outward and look for a
        #    terminus in the broader graph; if still nothing, attach the
        #    hidden hub (if any), else stay at the sibling.
        terminus_kind = "sibling"
        terminus_step: PathStep | None = None
        if sibling is not None:
            terminal = _terminus_from_member(sibling, sanctions_anchors=sanctions_anchors)
            if terminal is not None:
                terminus_kind, terminus_step = terminal

        if terminus_step is None and sibling is not None and max_hops >= 4 and edges_df is not None:
            extra_steps = _walk_one_hop_from_sibling(
                sibling.entity_uid,
                cluster_uids,
                edges_df=edges_df,
                addresses_df_lookup=addr_lookup,
                officers_df_lookup=off_lookup,
                intermediaries_df_lookup=inter_lookup,
                company_by_uid=company_by_uid,
            )
            steps.extend(extra_steps)
            # If the extra step landed on a unified-table entity with an
            # LEI or company_number, that's a registry anchor terminus.
            for st in extra_steps:
                if st.kind == "entity":
                    co = company_by_uid.get(st.node, {})
                    if co.get("lei") or co.get("company_number"):
                        terminus_kind = "registry_anchor"
                        terminus_step = PathStep(
                            kind="anchor",
                            node=st.node,
                            label=(
                                f"registry anchor "
                                f"`{co.get('lei') or co.get('company_number')}` "
                                f"({co.get('source') or '?'})"
                            ),
                            extra={
                                "lei": co.get("lei"),
                                "company_number": co.get("company_number"),
                            },
                        )

        # 4. If still no terminus, try the cluster's sanctions anchors,
        #    then the hidden hub.
        if terminus_step is None and sanctions_anchors:
            anc = sanctions_anchors[0]
            terminus_kind = "sanctions"
            terminus_step = PathStep(
                kind="anchor",
                node=anc.get("ref_entity_uid") or "?",
                label=(f"list-match anchor `{anc.get('ref_name') or anc.get('ref_lei') or '?'}`"),
                extra={"anchor_kind": "list_match", "score": anc.get("score")},
            )
        if terminus_step is None and hidden_hub is not None:
            terminus_kind = "hidden_hub"
            terminus_step = hidden_hub

        if terminus_step is not None:
            steps.append(terminus_step)

        # 5. Score: length + terminus quality + edge-kind diversity.
        diversity = len({s.kind for s in steps})
        score = len(steps) * 0.5 + _KIND_SCORE.get(terminus_kind, 0.0) + diversity * 0.3

        feature_label = (
            "intermediary"
            if kind == "intermediary"
            else "address"
            if kind == "address"
            else "officer"
        )
        if terminus_kind == "sibling":
            tail = "via recurring offshore infrastructure"
        elif terminus_kind == "sanctions":
            tail = "with a sanctions anchor at the end of the chain"
        elif terminus_kind == "registry_anchor":
            tail = "ending at a registry-anchored entity"
        elif terminus_kind == "hidden_hub":
            tail = "ending at a hidden hub node"
        else:
            tail = "via shared offshore infrastructure"
        n_sibs = len(siblings)
        summary = (
            f"`{anchor.name}` is structurally linked to {n_sibs} other "
            f"cluster member(s) through a shared {feature_label}, {tail}."
        )

        candidates.append(
            NarrativePath(
                anchor_uid=anchor.entity_uid,
                summary=summary,
                steps=steps,
                terminus_kind=terminus_kind,
                score=score,
            )
        )

    # Dedupe forward + reverse traversals of the same chain by node-set,
    # keeping the highest-scoring representative (so a registry-anchor or
    # sanctions terminus beats a plain sibling terminus on the same nodes).
    candidates.sort(key=lambda p: -p.score)
    out: list[NarrativePath] = []
    seen_signatures: set[frozenset[str]] = set()
    for p in candidates:
        sig = frozenset(s.node for s in p.steps)
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)
        out.append(p)
        if len(out) >= max_paths:
            break
    return out
