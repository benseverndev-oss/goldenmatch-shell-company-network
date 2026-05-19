"""Discovery delta — contrast 'what ordinary search reveals' vs
'what GoldenMatch surfaced' for a given cluster.

The point is to make the system's value visible in the briefing
itself: for a chosen anchor member (typically the registry-anchored
one a journalist would land on first), generate side-by-side rows
that show what a single-record registry lookup would yield against
what the cluster + repeats + cross-source links + centrality reveal
collectively.

Pure functions and dataclasses only. The renderer is plain Markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shellnet.investigations.cluster_explainer import (
        AddressRepeat,
        CentralityAnnotation,
        IntermediaryRepeat,
        JurisdictionProfile,
        MemberAttr,
        OfficerRepeat,
    )


@dataclass
class DeltaRow:
    """One contrast row. ``standard_view`` reads as what you'd see if
    you only looked up ``anchor`` in its own registry; ``goldenmatch_view``
    reads as what the cluster surfaced collectively. ``delta_summary``
    is a one-line headline (used by the briefing's headline strip)."""

    category: str
    standard_view: str
    goldenmatch_view: str
    delta_summary: str


@dataclass
class DiscoveryDelta:
    anchor_uid: str
    anchor_name: str
    anchor_jurisdiction: str | None
    rows: list[DeltaRow] = field(default_factory=list)
    overall_summary: str = ""


def _pick_anchor(members: list[MemberAttr]) -> MemberAttr | None:
    """Pick the cluster member a journalist is most likely to start
    from: one with a registry id (LEI / company_number), then any
    member in the seed-jurisdiction the user typed (we approximate
    via the most common jurisdiction), then the first member."""
    if not members:
        return None
    anchored = [m for m in members if m.lei or m.company_number]
    if anchored:
        return anchored[0]
    return members[0]


def build_discovery_delta(
    members: list[MemberAttr],
    *,
    jurisdictions: JurisdictionProfile,
    intermediaries: list[IntermediaryRepeat],
    addresses: list[AddressRepeat],
    officers: list[OfficerRepeat],
    sanctions_anchors: list[dict[str, Any]],
    centrality: list[CentralityAnnotation],
    sources_present: list[str],
    leaks_present: list[str],
    anchor: MemberAttr | None = None,
) -> DiscoveryDelta:
    """Assemble the contrast table for a single anchor member.

    Returns rows in a stable order so consecutive briefings render the
    same shape; missing data shows as ``"—"`` on the GoldenMatch side
    rather than getting elided, so the absence is itself visible."""
    if not members:
        return DiscoveryDelta(anchor_uid="", anchor_name="", anchor_jurisdiction=None)

    anchor = anchor or _pick_anchor(members)
    if anchor is None:
        return DiscoveryDelta(anchor_uid="", anchor_name="", anchor_jurisdiction=None)

    other_members = [m for m in members if m.entity_uid != anchor.entity_uid]
    rows: list[DeltaRow] = []

    # ----- Identity -----
    n_total = len(members)
    n_other_jurs = len({m.jurisdiction for m in members if m.jurisdiction})
    std_identity = f"`{anchor.name}` ({anchor.jurisdiction or 'unknown jurisdiction'})" + (
        f", registry id `{anchor.lei or anchor.company_number}`"
        if (anchor.lei or anchor.company_number)
        else ""
    )
    if n_total == 1:
        gm_identity = "no additional cluster members"
        delta = "isolated entity"
    else:
        gm_identity = (
            f"part of a {n_total}-member cluster spanning {n_other_jurs} "
            "jurisdiction(s); other members include "
            + ", ".join(f"`{m.name}` ({m.jurisdiction or '?'})" for m in other_members[:3])
            + ("…" if len(other_members) > 3 else "")
        )
        delta = f"isolated company → {n_total}-member cluster"
    rows.append(DeltaRow("Identity", std_identity, gm_identity, delta))

    # ----- Jurisdictional footprint -----
    std_jur = f"single jurisdiction (`{anchor.jurisdiction or '?'}`)"
    if jurisdictions.is_cross_border:
        gm_jur = (
            f"{len(jurisdictions.counts)} jurisdiction(s): "
            + ", ".join(
                f"{j} ({n})" for j, n in sorted(jurisdictions.counts.items(), key=lambda kv: -kv[1])
            )
            + (
                f"; secrecy-listed: {', '.join(jurisdictions.secrecy_jurisdictions)}"
                if jurisdictions.secrecy_jurisdictions
                else ""
            )
        )
        delta = "no cross-border view → multi-jurisdiction bridge"
    else:
        gm_jur = f"single jurisdiction (`{anchor.jurisdiction or '?'}`)"
        delta = "no jurisdictional expansion"
    rows.append(DeltaRow("Jurisdictional footprint", std_jur, gm_jur, delta))

    # ----- Officers / nominees -----
    std_officers = (
        f"officers as listed in `{anchor.source}` for "
        f"`{anchor.company_number or anchor.entity_uid}`"
    )
    if officers:
        top = officers[0]
        gm_officers = (
            f"{len(officers)} shared officer(s) across cluster members; "
            f"top: `{top.name or top.node}` "
            f"(serves {top.n_members_served}/{n_total} members, "
            f"corpus degree {top.n_global_edges})"
        )
        delta = (
            f"one nominee → {sum(o.n_global_edges for o in officers)}-edge officer infrastructure"
        )
    else:
        gm_officers = "no officers shared across cluster members"
        delta = "no shared-officer signal"
    rows.append(DeltaRow("Officers / nominees", std_officers, gm_officers, delta))

    # ----- Addresses -----
    std_address = (
        f"registered address as listed in `{anchor.source}`: "
        f"`{(anchor.address_raw or 'not provided')[:80]}`"
    )
    if addresses:
        top = addresses[0]
        gm_address = (
            f"{len(addresses)} shared address(es); "
            f"top: `{(top.text or top.node)[:60]}` "
            f"(shared by {top.n_members_served} cluster members; "
            f"corpus degree {top.n_global_edges})"
        )
        delta = f"single registered address → shared infrastructure ({len(addresses)})"
    else:
        gm_address = "no addresses shared across cluster members"
        delta = "no shared-address signal"
    rows.append(DeltaRow("Registered addresses", std_address, gm_address, delta))

    # ----- Cross-source corroboration -----
    std_cross = f"single source: `{anchor.source}`"
    if len(sources_present) >= 2:
        gm_cross = (
            f"{len(sources_present)} sources corroborate this cluster: "
            f"{', '.join(sources_present)}"
            + (f"; leaks: {', '.join(leaks_present)}" if leaks_present else "")
        )
        delta = f"single source → {len(sources_present)}-source corroboration"
    else:
        gm_cross = f"only source: {sources_present[0] if sources_present else '?'}"
        delta = "no cross-source corroboration"
    rows.append(DeltaRow("Cross-source corroboration", std_cross, gm_cross, delta))

    # ----- Risk adjacency -----
    std_risk = "no automatic risk flags (registry lookup does not check sanctions)"
    direct_os = sum(1 for m in members if m.source == "opensanctions")
    if sanctions_anchors or direct_os:
        bits = []
        if direct_os:
            bits.append(f"{direct_os} direct opensanctions member(s)")
        if sanctions_anchors:
            bits.append(f"{len(sanctions_anchors)} list-match anchor(s)")
        gm_risk = "; ".join(bits)
        delta = "no risk view → sanctions adjacency surfaced"
    else:
        gm_risk = "no sanctions adjacency within 1 hop"
        delta = "no sanctions adjacency found"
    rows.append(DeltaRow("Risk adjacency", std_risk, gm_risk, delta))

    # ----- Structural position -----
    std_struct = "structural position unknown (registry lookup is a flat record)"
    anchor_centrality = next(
        (c for c in centrality if c.entity_uid == anchor.entity_uid and c.is_member),
        None,
    )
    member_count_in_cent = sum(1 for c in centrality if c.is_member)
    non_member_in_cent = [c for c in centrality if not c.is_member]
    if anchor_centrality is not None:
        # Estimate the anchor's rank within the cluster's centrality table.
        sorted_member = sorted(
            (c for c in centrality if c.is_member),
            key=lambda c: -c.betweenness,
        )
        rank = next(
            (i + 1 for i, c in enumerate(sorted_member) if c.entity_uid == anchor.entity_uid),
            None,
        )
        gm_struct = (
            f"betweenness {anchor_centrality.betweenness:.4f}, eigenvector "
            f"{anchor_centrality.eigenvector:.4f}"
            + (
                f"; rank {rank}/{member_count_in_cent} within the cluster"
                if rank is not None
                else ""
            )
            + (
                f"; community {anchor_centrality.community_id}"
                if anchor_centrality.community_id is not None
                else ""
            )
        )
        if non_member_in_cent:
            top_hub = max(non_member_in_cent, key=lambda c: c.betweenness)
            gm_struct += (
                f"; hidden hub `{top_hub.entity_uid}` "
                f"(betweenness {top_hub.betweenness:.4f}) glues the community"
            )
        delta = "flat record → graph-centrality position with hidden hub"
    elif centrality:
        gm_struct = "centrality computed but anchor not in the sub-graph (low connectivity)"
        delta = "anchor is peripheral within the cluster"
    else:
        gm_struct = "centrality not computed for this run"
        delta = "no centrality input"
    rows.append(DeltaRow("Structural position", std_struct, gm_struct, delta))

    # Overall summary: 1-2 sentences synthesizing the deltas that fired.
    bullets: list[str] = []
    if n_total > 1:
        bullets.append(f"{n_total - 1} sibling member(s) you wouldn't have seen")
    if jurisdictions.is_cross_border:
        bullets.append(f"{len(jurisdictions.counts)}-jurisdiction span")
    if officers:
        bullets.append(f"{len(officers)} shared officer(s)")
    if addresses:
        bullets.append(f"{len(addresses)} shared address(es)")
    if len(sources_present) >= 2:
        bullets.append(f"{len(sources_present)}-source corroboration")
    if sanctions_anchors or direct_os:
        bullets.append("sanctions adjacency")
    overall = (
        "Standard registry search would have shown "
        f"`{anchor.name}` as a single record. GoldenMatch added: "
        + ("; ".join(bullets) if bullets else "no additional structural context.")
    )

    return DiscoveryDelta(
        anchor_uid=anchor.entity_uid,
        anchor_name=anchor.name,
        anchor_jurisdiction=anchor.jurisdiction,
        rows=rows,
        overall_summary=overall,
    )


def render_discovery_delta_markdown(delta: DiscoveryDelta) -> str:
    """Side-by-side table. Empty deltas (no rows) render as a single
    explanatory line so the section's presence is consistent across
    briefings."""
    lines: list[str] = []
    lines.append("## Discovery delta — standard search vs GoldenMatch")
    lines.append("")
    if not delta.rows:
        lines.append("_Anchor member not selected; discovery delta unavailable._")
        return "\n".join(lines)
    lines.append(
        f"Anchor: `{delta.anchor_uid}` — `{delta.anchor_name}` ({delta.anchor_jurisdiction or '?'})"
    )
    lines.append("")
    lines.append(f"**Headline:** {delta.overall_summary}")
    lines.append("")
    lines.append("| Dimension | Standard search | GoldenMatch surfaced | Delta |")
    lines.append("| --- | --- | --- | --- |")
    for r in delta.rows:
        std = r.standard_view.replace("|", "/").replace("\n", " ").strip()
        gm = r.goldenmatch_view.replace("|", "/").replace("\n", " ").strip()
        d = r.delta_summary.replace("|", "/").replace("\n", " ").strip()
        lines.append(f"| **{r.category}** | {std} | {gm} | {d} |")
    return "\n".join(lines)
