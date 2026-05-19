"""Temporal reconstruction — turn a static cluster into a chronology.

Pulls dates out of ``MemberAttr`` (incorporation_date / dissolution_date)
and out of edges_df (start_date / end_date on officer / intermediary /
address relationships) and assembles them into a single sorted event
stream. Derived signals:

* per-member lifecycle spans
* intermediary / officer reuse over time
* cluster emergence curve (cumulative incorporations per year)
* ownership churn (rate of officer / intermediary start-end edges)

Pure functions; the renderer is plain Markdown with a small ASCII span
chart so a Markdown reader can scan the cluster's behaviour at a glance.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import polars as pl

    from shellnet.investigations.cluster_explainer import (
        AddressRepeat,
        IntermediaryRepeat,
        MemberAttr,
        OfficerRepeat,
    )


EVENT_KINDS = (
    "incorporation",
    "dissolution",
    "officer_start",
    "officer_end",
    "address_start",
    "address_end",
    "intermediary_start",
    "intermediary_end",
)


@dataclass
class TimelineEvent:
    """One dated event involving a cluster member."""

    date: date
    kind: str
    member_uid: str
    other_node: str | None
    label: str  # human-readable
    source_label: str | None = None  # leak (Panama Papers, Pandora Papers, etc.)


@dataclass
class MemberLifecycle:
    """Per-member span. ``alive_to`` is None if the entity is still active."""

    member_uid: str
    name: str
    incorporation: date | None
    dissolution: date | None
    n_officer_changes: int = 0
    n_intermediary_changes: int = 0
    n_address_changes: int = 0


@dataclass
class FeatureReuseWindow:
    """A shared feature's per-member time window — when each cluster
    member used the intermediary / officer / address."""

    feature_kind: str  # 'intermediary' | 'officer' | 'address'
    feature_node: str
    feature_label: str
    windows: list[dict[str, Any]] = field(default_factory=list)
    # Each window: {"member_uid": ..., "start": date|None, "end": date|None,
    #               "source_label": ...}


@dataclass
class Timeline:
    events: list[TimelineEvent]
    lifecycles: list[MemberLifecycle]
    reuse_windows: list[FeatureReuseWindow]
    emergence_by_year: dict[int, int]  # year -> cumulative incorporations
    churn_rate: float  # officer+intermediary changes per active member-year
    span_start: date | None
    span_end: date | None


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


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


def _classify_edge_kind(kind_raw: str | None) -> str:
    k = (kind_raw or "").lower()
    if "address" in k:
        return "address"
    if "intermediar" in k:
        return "intermediary"
    if "officer" in k:
        return "officer"
    return "other"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _events_from_members(members: list[MemberAttr]) -> list[TimelineEvent]:
    out: list[TimelineEvent] = []
    for m in members:
        inc = _parse_date(m.incorporation_date)
        if inc is not None:
            out.append(
                TimelineEvent(
                    date=inc,
                    kind="incorporation",
                    member_uid=m.entity_uid,
                    other_node=None,
                    label=f"`{m.name}` incorporated in {m.jurisdiction or '?'}",
                )
            )
        dis = _parse_date(m.dissolution_date)
        if dis is not None:
            out.append(
                TimelineEvent(
                    date=dis,
                    kind="dissolution",
                    member_uid=m.entity_uid,
                    other_node=None,
                    label=f"`{m.name}` dissolved / struck off",
                )
            )
    return out


def _events_from_edges(
    member_uids: list[str], edges_df: pl.DataFrame | None
) -> list[TimelineEvent]:
    if edges_df is None or edges_df.height == 0:
        return []
    member_set = set(member_uids)
    import polars as pl  # runtime

    sub = edges_df.filter(
        pl.col("src_node").is_in(member_uids) | pl.col("dst_node").is_in(member_uids)
    )
    if sub.height == 0:
        return []
    has_start = "start_date" in sub.columns
    has_end = "end_date" in sub.columns
    out: list[TimelineEvent] = []
    for r in sub.iter_rows(named=True):
        s, d = r["src_node"], r["dst_node"]
        if s in member_set:
            member_uid, other = s, d
        elif d in member_set:
            member_uid, other = d, s
        else:
            continue
        kind = _classify_edge_kind(r.get("kind_raw"))
        if kind == "other":
            continue
        leak = r.get("source_label")
        start = _parse_date(r.get("start_date")) if has_start else None
        end = _parse_date(r.get("end_date")) if has_end else None
        if start is not None:
            out.append(
                TimelineEvent(
                    date=start,
                    kind=f"{kind}_start",
                    member_uid=member_uid,
                    other_node=other,
                    label=f"{kind} edge to `{other}` begins",
                    source_label=leak,
                )
            )
        if end is not None:
            out.append(
                TimelineEvent(
                    date=end,
                    kind=f"{kind}_end",
                    member_uid=member_uid,
                    other_node=other,
                    label=f"{kind} edge to `{other}` ends",
                    source_label=leak,
                )
            )
    return out


def _reuse_windows(
    repeats: list[Any],
    feature_kind: str,
    edges_df: pl.DataFrame | None,
) -> list[FeatureReuseWindow]:
    if not repeats or edges_df is None or edges_df.height == 0:
        return []
    has_start = "start_date" in edges_df.columns
    has_end = "end_date" in edges_df.columns
    import polars as pl

    out: list[FeatureReuseWindow] = []
    for repeat in repeats:
        feature_node = repeat.node
        sub = edges_df.filter(
            (pl.col("src_node") == feature_node) | (pl.col("dst_node") == feature_node)
        )
        if sub.height == 0:
            continue
        windows: list[dict[str, Any]] = []
        for r in sub.iter_rows(named=True):
            s, d = r["src_node"], r["dst_node"]
            other = d if s == feature_node else s
            if other not in set(repeat.member_uids):
                continue
            windows.append(
                {
                    "member_uid": other,
                    "start": _parse_date(r.get("start_date")) if has_start else None,
                    "end": _parse_date(r.get("end_date")) if has_end else None,
                    "source_label": r.get("source_label"),
                }
            )
        if not windows:
            continue
        label = getattr(repeat, "name", None) or getattr(repeat, "text", None) or feature_node
        out.append(
            FeatureReuseWindow(
                feature_kind=feature_kind,
                feature_node=feature_node,
                feature_label=str(label)[:60],
                windows=windows,
            )
        )
    return out


def build_timeline(
    members: list[MemberAttr],
    *,
    edges_df: pl.DataFrame | None = None,
    intermediaries: list[IntermediaryRepeat] | None = None,
    addresses: list[AddressRepeat] | None = None,
    officers: list[OfficerRepeat] | None = None,
) -> Timeline:
    """Assemble a full per-cluster chronology."""
    member_events = _events_from_members(members)
    edge_events = _events_from_edges([m.entity_uid for m in members], edges_df)
    all_events = sorted(member_events + edge_events, key=lambda e: (e.date, e.kind))

    # Per-member lifecycles + churn counters.
    lifecycle_by_uid: dict[str, MemberLifecycle] = {}
    for m in members:
        lifecycle_by_uid[m.entity_uid] = MemberLifecycle(
            member_uid=m.entity_uid,
            name=m.name or m.entity_uid,
            incorporation=_parse_date(m.incorporation_date),
            dissolution=_parse_date(m.dissolution_date),
        )
    for ev in edge_events:
        lc = lifecycle_by_uid.get(ev.member_uid)
        if lc is None:
            continue
        if ev.kind in {"officer_start", "officer_end"}:
            lc.n_officer_changes += 1
        elif ev.kind in {"intermediary_start", "intermediary_end"}:
            lc.n_intermediary_changes += 1
        elif ev.kind in {"address_start", "address_end"}:
            lc.n_address_changes += 1

    # Cluster emergence curve — cumulative incorporations per year.
    inc_years = sorted(ev.date.year for ev in member_events if ev.kind == "incorporation")
    emergence_by_year: dict[int, int] = {}
    for running, y in enumerate(inc_years, start=1):
        emergence_by_year[y] = running

    # Churn rate: officer + intermediary edge events per active member-year.
    n_member_years = 0
    for lc in lifecycle_by_uid.values():
        if lc.incorporation is None:
            continue
        end = lc.dissolution or date.today()
        years = max(1, (end - lc.incorporation).days // 365)
        n_member_years += years
    n_changes = sum(
        1
        for ev in edge_events
        if ev.kind in {"officer_start", "officer_end", "intermediary_start", "intermediary_end"}
    )
    churn_rate = (n_changes / n_member_years) if n_member_years else 0.0

    reuse_windows: list[FeatureReuseWindow] = []
    reuse_windows.extend(_reuse_windows(intermediaries or [], "intermediary", edges_df))
    reuse_windows.extend(_reuse_windows(officers or [], "officer", edges_df))
    reuse_windows.extend(_reuse_windows(addresses or [], "address", edges_df))

    if all_events:
        span_start = min(e.date for e in all_events)
        span_end = max(e.date for e in all_events)
    else:
        span_start = None
        span_end = None

    return Timeline(
        events=all_events,
        lifecycles=list(lifecycle_by_uid.values()),
        reuse_windows=reuse_windows,
        emergence_by_year=emergence_by_year,
        churn_rate=churn_rate,
        span_start=span_start,
        span_end=span_end,
    )


# ---------------------------------------------------------------------------
# ASCII span chart
# ---------------------------------------------------------------------------


def _ascii_span_chart(
    lifecycles: list[MemberLifecycle],
    span_start: date | None,
    span_end: date | None,
    *,
    width: int = 40,
) -> list[str]:
    if not lifecycles or span_start is None or span_end is None:
        return []
    total_days = max((span_end - span_start).days, 1)

    def _pos(d: date) -> int:
        days = max(0, (d - span_start).days)
        return min(width - 1, int(width * days / total_days))

    lines: list[str] = []
    name_w = min(28, max((len(lc.name) for lc in lifecycles), default=10))
    for lc in lifecycles:
        if lc.incorporation is None:
            continue
        end = lc.dissolution or span_end
        i = _pos(lc.incorporation)
        e = _pos(end)
        bar = [" "] * width
        for k in range(i, e + 1):
            bar[k] = "─"
        bar[i] = "├"
        bar[e] = "┤" if lc.dissolution else "▶"
        name = lc.name[:name_w].ljust(name_w)
        inc = lc.incorporation.isoformat()
        endstr = lc.dissolution.isoformat() if lc.dissolution else "active"
        lines.append(f"  {name} {inc}  {''.join(bar)}  {endstr}")
    if lines:
        scale_left = f"{span_start.isoformat()}".ljust(width // 2 + 1)
        scale_right = f"{span_end.isoformat()}".rjust(width - len(scale_left))
        lines.append(f"  {' ' * name_w}            {scale_left}{scale_right}")
    return lines


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def render_timeline_markdown(
    timeline: Timeline, *, max_events: int = 20, max_reuse: int = 5
) -> str:
    lines: list[str] = []
    lines.append("## Timeline / organizational behavior")
    lines.append("")
    if not timeline.events and not timeline.lifecycles:
        lines.append("_No date information available for this cluster._")
        return "\n".join(lines)

    # Headline
    if timeline.span_start and timeline.span_end:
        span_years = max(1, (timeline.span_end - timeline.span_start).days // 365)
        lines.append(
            f"Span: `{timeline.span_start}` → `{timeline.span_end}` "
            f"(~{span_years} year(s)). "
            f"Officer + intermediary churn: {timeline.churn_rate:.2f} change(s) "
            "per active member-year."
        )
        lines.append("")

    # Member lifecycle spans (ASCII chart)
    chart = _ascii_span_chart(timeline.lifecycles, timeline.span_start, timeline.span_end)
    if chart:
        lines.append("### Member lifecycles")
        lines.append("")
        lines.append("```")
        lines.extend(chart)
        lines.append("```")
        lines.append("")

    # Cluster emergence
    if timeline.emergence_by_year:
        lines.append("### Cluster emergence (cumulative incorporations)")
        lines.append("")
        lines.append("| year | cumulative |")
        lines.append("| ---: | ---: |")
        for y in sorted(timeline.emergence_by_year):
            lines.append(f"| {y} | {timeline.emergence_by_year[y]} |")
        lines.append("")

    # Top events
    if timeline.events:
        lines.append(f"### First {min(max_events, len(timeline.events))} events")
        lines.append("")
        lines.append("| date | kind | member | other | label | leak |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for ev in timeline.events[:max_events]:
            lines.append(
                "| {d} | {k} | `{m}` | `{o}` | {lab} | {leak} |".format(
                    d=ev.date.isoformat(),
                    k=ev.kind,
                    m=ev.member_uid,
                    o=ev.other_node or "",
                    lab=(ev.label or "").replace("|", "/")[:80],
                    leak=ev.source_label or "",
                )
            )
        lines.append("")

    # Feature reuse windows (top intermediaries / officers / addresses)
    interesting_reuse = [w for w in timeline.reuse_windows if len(w.windows) >= 2][:max_reuse]
    if interesting_reuse:
        lines.append("### Feature reuse over time")
        lines.append("")
        for w in interesting_reuse:
            lines.append(f"**{w.feature_kind}** `{w.feature_label}` ({w.feature_node})")
            lines.append("")
            lines.append("| member | start | end | leak |")
            lines.append("| --- | --- | --- | --- |")
            for win in w.windows:
                lines.append(
                    "| `{m}` | {s} | {e} | {leak} |".format(
                        m=win["member_uid"],
                        s=win["start"].isoformat() if win["start"] else "",
                        e=win["end"].isoformat() if win["end"] else "",
                        leak=win.get("source_label") or "",
                    )
                )
            lines.append("")

    # Ownership-churn summary per member
    churners = [
        lc for lc in timeline.lifecycles if (lc.n_officer_changes + lc.n_intermediary_changes) > 0
    ]
    if churners:
        lines.append("### Ownership churn per member")
        lines.append("")
        lines.append("| member | officer changes | intermediary changes | address changes |")
        lines.append("| --- | ---: | ---: | ---: |")
        for lc in sorted(
            churners,
            key=lambda x: -(x.n_officer_changes + x.n_intermediary_changes),
        ):
            lines.append(
                f"| `{lc.member_uid}` | {lc.n_officer_changes} | "
                f"{lc.n_intermediary_changes} | {lc.n_address_changes} |"
            )
        lines.append("")

    # Event-kind distribution summary
    kinds = Counter(ev.kind for ev in timeline.events)
    if kinds:
        bits = ", ".join(f"{k}={n}" for k, n in kinds.most_common())
        lines.append(f"_Event-kind distribution: {bits}._")
        lines.append("")

    return "\n".join(lines)
