"""Interactive graph replay — frame-by-frame storyboard of how a
cluster emerges over time.

Driven by the temporal events from ``temporal.build_timeline``. The
output is a sequence of typed ``ReplayFrame`` snapshots, each carrying
the cumulative node + edge set at that date bucket plus a one-sentence
narrative for the period. Renders to:

* a Markdown storyboard (video-script-ready, no external deps)
* a JSON sequence (for downstream tools to render their own animation)
* per-frame PNG snapshots (optional — only when matplotlib is on the
  path; degrades silently otherwise)

The point is to show "how the system narrowed possibilities" — at each
frame, ``cumulative_uncertainty`` falls as more cross-source links land
and more registry anchors appear, so the curve is itself a piece of
methodology evidence.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shellnet.investigations.cluster_explainer import MemberAttr
    from shellnet.investigations.temporal import Timeline, TimelineEvent


@dataclass
class ReplayFrame:
    """Cumulative snapshot at a bucket boundary."""

    frame_idx: int
    bucket_end: date
    cumulative_nodes: list[str] = field(default_factory=list)
    cumulative_edges: list[tuple[str, str, str]] = field(default_factory=list)
    new_events: list[dict[str, Any]] = field(default_factory=list)
    narrative: str = ""
    cumulative_uncertainty: float = 1.0  # 1.0 = fully unknown, 0.0 = fully anchored
    n_registry_anchors_present: int = 0
    n_sources_present: int = 0


@dataclass
class ReplaySequence:
    cluster_id: int
    frames: list[ReplayFrame] = field(default_factory=list)
    members: list[MemberAttr] = field(default_factory=list)
    summary: str = ""


def _bucket_dates(events: list[TimelineEvent], n_frames: int) -> list[date]:
    if not events:
        return []
    start = events[0].date
    end = events[-1].date
    if start == end:
        return [end]
    total_days = (end - start).days
    if total_days <= 0 or n_frames <= 1:
        return [end]
    step = total_days // n_frames
    if step == 0:
        step = 1
    bucket_ends: list[date] = []
    cursor = start
    while cursor < end and len(bucket_ends) < n_frames - 1:
        from datetime import timedelta

        cursor = cursor + timedelta(days=step)
        bucket_ends.append(cursor)
    bucket_ends.append(end)
    return bucket_ends


def _narrate_period(new_events: list[TimelineEvent]) -> str:
    """One-sentence summary of what happened in this bucket."""
    if not new_events:
        return "no new activity"
    by_kind: dict[str, int] = {}
    leaks: set[str] = set()
    for e in new_events:
        by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
        if e.source_label:
            leaks.add(e.source_label)
    bits = [f"{n} {k}" for k, n in sorted(by_kind.items(), key=lambda kv: -kv[1])]
    msg = ", ".join(bits)
    if leaks:
        msg += f" — leaks: {', '.join(sorted(leaks))}"
    return msg


def build_replay(
    timeline: Timeline,
    members: list[MemberAttr],
    *,
    cluster_id: int,
    n_frames: int = 10,
) -> ReplaySequence:
    """Bucket timeline events into ``n_frames`` cumulative snapshots."""
    if not timeline.events:
        return ReplaySequence(
            cluster_id=cluster_id,
            members=list(members),
            summary="no temporal data available",
        )

    bucket_ends = _bucket_dates(timeline.events, n_frames)
    if not bucket_ends:
        return ReplaySequence(cluster_id=cluster_id, members=list(members), summary="no buckets")

    # Members with a registry anchor at any time (used for uncertainty).
    n_anchored_members = sum(1 for m in members if m.lei or m.company_number)
    member_uids = {m.entity_uid for m in members}

    cum_nodes: set[str] = set()
    cum_edges: list[tuple[str, str, str]] = []
    cum_edge_keys: set[tuple[str, str, str]] = set()
    cum_sources: set[str] = set()
    consumed = 0

    frames: list[ReplayFrame] = []
    for idx, b_end in enumerate(bucket_ends):
        # Pull events that land on or before this bucket end.
        new: list[TimelineEvent] = []
        while consumed < len(timeline.events) and timeline.events[consumed].date <= b_end:
            ev = timeline.events[consumed]
            new.append(ev)
            cum_nodes.add(ev.member_uid)
            if ev.other_node:
                cum_nodes.add(ev.other_node)
            # Track sources implied by the source_label (leak) or by which
            # member is in the corpus.
            for m in members:
                if m.entity_uid == ev.member_uid:
                    cum_sources.add(m.source)
            if ev.kind in {
                "officer_start",
                "address_start",
                "intermediary_start",
            }:
                key = (
                    ev.member_uid,
                    ev.other_node or "",
                    ev.kind.replace("_start", ""),
                )
                if key not in cum_edge_keys:
                    cum_edges.append(key)
                    cum_edge_keys.add(key)
            consumed += 1

        # Uncertainty heuristic: starts at 1.0, falls as registry-anchored
        # members appear and as cross-source corroboration grows.
        anchored_share = (n_anchored_members / max(len(members), 1)) if members else 0.0
        sources_share = (len(cum_sources) / 4.0) if members else 0.0  # 4+ saturates
        anchored_share = min(1.0, anchored_share)
        sources_share = min(1.0, sources_share)
        n_anchors_now = sum(
            1 for m in members if m.entity_uid in cum_nodes and (m.lei or m.company_number)
        )
        anchors_now_share = n_anchors_now / max(len(members), 1) if members else 0.0
        uncertainty = 1.0 - (0.4 * anchors_now_share + 0.3 * sources_share + 0.3 * anchored_share)
        uncertainty = max(0.0, min(1.0, uncertainty))

        # Member-only nodes that have appeared (separate count for headline).
        cum_member_nodes = cum_nodes & member_uids

        narrative_prefix = (
            f"by `{b_end.isoformat()}`: "
            f"{len(cum_member_nodes)} cluster member(s) live, "
            f"{len(cum_edges)} relationship(s)"
        )
        narrative_tail = _narrate_period(new) if new else "no new activity"
        narrative = f"{narrative_prefix}. This period: {narrative_tail}."

        frames.append(
            ReplayFrame(
                frame_idx=idx,
                bucket_end=b_end,
                cumulative_nodes=sorted(cum_nodes),
                cumulative_edges=list(cum_edges),
                new_events=[
                    {
                        "date": e.date.isoformat(),
                        "kind": e.kind,
                        "member_uid": e.member_uid,
                        "other_node": e.other_node,
                        "source_label": e.source_label,
                    }
                    for e in new
                ],
                narrative=narrative,
                cumulative_uncertainty=uncertainty,
                n_registry_anchors_present=n_anchors_now,
                n_sources_present=len(cum_sources),
            )
        )

    summary = (
        f"{len(frames)} frame(s), span `{bucket_ends[0]}` → `{bucket_ends[-1]}`, "
        f"final uncertainty {frames[-1].cumulative_uncertainty:.2f}"
    )
    return ReplaySequence(
        cluster_id=cluster_id, frames=frames, members=list(members), summary=summary
    )


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_replay_markdown(replay: ReplaySequence) -> str:
    """A video-script-ready storyboard. One section per frame."""
    lines: list[str] = []
    lines.append(f"# Graph replay — cluster {replay.cluster_id}")
    lines.append("")
    if not replay.frames:
        lines.append("_No temporal data available for this cluster._")
        return "\n".join(lines)
    lines.append(f"_{replay.summary}_")
    lines.append("")
    lines.append(
        "> Each frame is a cumulative snapshot. ``cumulative_uncertainty`` "
        "falls as more registry-anchored members appear and as cross-source "
        "corroboration grows — the curve is itself a piece of methodology "
        "evidence the audience can follow."
    )
    lines.append("")
    lines.append("## Uncertainty curve")
    lines.append("")
    lines.append("| frame | bucket end | nodes | edges | anchors | sources | uncertainty |")
    lines.append("| ---: | --- | ---: | ---: | ---: | ---: | ---: |")
    for f in replay.frames:
        lines.append(
            f"| {f.frame_idx} | `{f.bucket_end.isoformat()}` | "
            f"{len(f.cumulative_nodes)} | {len(f.cumulative_edges)} | "
            f"{f.n_registry_anchors_present} | {f.n_sources_present} | "
            f"{f.cumulative_uncertainty:.2f} |"
        )
    lines.append("")
    lines.append("## Frames")
    lines.append("")
    for f in replay.frames:
        lines.append(f"### Frame {f.frame_idx} — `{f.bucket_end.isoformat()}`")
        lines.append("")
        lines.append(f_unsafe := f"_{f.narrative}_")
        _ = f_unsafe
        lines.append("")
        if f.new_events:
            lines.append("New events this period:")
            lines.append("")
            for ev in f.new_events[:8]:
                lines.append(
                    f"- `{ev['date']}` **{ev['kind']}**: "
                    f"`{ev['member_uid']}` → `{ev.get('other_node') or ''}`"
                    + (f" ({ev['source_label']})" if ev.get("source_label") else "")
                )
            if len(f.new_events) > 8:
                lines.append(f"- _… {len(f.new_events) - 8} more_")
            lines.append("")
        lines.append(
            f"State: {len(f.cumulative_nodes)} node(s), "
            f"{len(f.cumulative_edges)} edge(s), "
            f"uncertainty {f.cumulative_uncertainty:.2f}."
        )
        lines.append("")
    return "\n".join(lines)


def render_replay_json(replay: ReplaySequence) -> str:
    obj = {
        "cluster_id": replay.cluster_id,
        "summary": replay.summary,
        "members": [
            {
                "entity_uid": m.entity_uid,
                "source": m.source,
                "name": m.name,
                "jurisdiction": m.jurisdiction,
                "lei": m.lei,
                "company_number": m.company_number,
            }
            for m in replay.members
        ],
        "frames": [asdict(f) for f in replay.frames],
    }
    return json.dumps(obj, default=str, indent=2, ensure_ascii=False)


def write_replay_png_frames(replay: ReplaySequence, out_dir: Path) -> list[Path]:
    """Optional per-frame PNG render. No-ops (returns []) when matplotlib
    isn't importable — keeps the rest of the pipeline working on
    headless / minimal environments."""
    try:
        import matplotlib.pyplot as plt  # noqa: F401
        import networkx as nx
    except ImportError:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    pos_cache: dict[str, tuple[float, float]] = {}

    for f in replay.frames:
        g = nx.Graph()
        for n in f.cumulative_nodes:
            g.add_node(n)
        for u, v, kind in f.cumulative_edges:
            if u and v:
                g.add_edge(u, v, kind=kind)
        # Stable layout: compute once on the final frame's graph; reuse.
        if not pos_cache:
            final = nx.Graph()
            last = replay.frames[-1]
            for n in last.cumulative_nodes:
                final.add_node(n)
            for u, v, _ in last.cumulative_edges:
                if u and v:
                    final.add_edge(u, v)
            pos_cache.update(nx.spring_layout(final, seed=42))

        from matplotlib import pyplot as _plt

        fig, ax = _plt.subplots(figsize=(8, 6))
        nx.draw_networkx_nodes(g, pos=pos_cache, ax=ax, node_size=120, alpha=0.85)
        nx.draw_networkx_edges(g, pos=pos_cache, ax=ax, alpha=0.4)
        ax.set_title(
            f"frame {f.frame_idx} — {f.bucket_end.isoformat()} (unc {f.cumulative_uncertainty:.2f})"
        )
        ax.axis("off")
        target = out_dir / f"frame_{f.frame_idx:02d}.png"
        fig.savefig(target, dpi=120, bbox_inches="tight")
        _plt.close(fig)
        paths.append(target)
    return paths
