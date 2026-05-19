"""Rank every multi-member cluster by *investigative value* — the
'why this matters' axis, complementary to ``rank_clusters.defensibility``.

This is the batch driver behind ``scripts/rank_by_investigative_value.py``.
It re-uses the per-cluster scoring primitives in ``cluster_explainer`` but
walks ``edges_df`` exactly once across all clusters so scoring 10k+
multi-member clusters stays linear in the edge count rather than
quadratic.

Output is a polars DataFrame with one row per cluster — same shape as
``cluster_ranking.parquet`` so the two rankings can be joined downstream
on ``cluster_id`` to see clusters that are *both* well-formed (high
defensibility) and *interesting* (high investigative value).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

import polars as pl

from shellnet.investigations.cluster_explainer import (
    AddressRepeat,
    IntermediaryRepeat,
    OfficerRepeat,
    _classify_edge_kind,
    _lookup_by_source_id,
    annotate_centrality,
    compute_jurisdiction_profile,
    filter_sanctions_anchors,
    gather_member_attrs,
    score_investigative_value,
)


def _global_degree_from_edges(edges_df: pl.DataFrame) -> dict[str, int]:
    if edges_df.height == 0:
        return {}
    src = Counter(edges_df.get_column("src_node").to_list())
    dst = Counter(edges_df.get_column("dst_node").to_list())
    out: dict[str, int] = defaultdict(int)
    for n, c in src.items():
        out[n] += c
    for n, c in dst.items():
        out[n] += c
    return out


def _batch_gather_repeats(
    cluster_members: dict[int, list[str]],
    *,
    edges_df: pl.DataFrame | None,
    addresses_df: pl.DataFrame | None,
    officers_df: pl.DataFrame | None,
    intermediaries_df: pl.DataFrame | None,
    min_members: int = 2,
    top_n: int = 10,
) -> dict[int, tuple[list[IntermediaryRepeat], list[AddressRepeat], list[OfficerRepeat]]]:
    """One pass over ``edges_df`` to derive shared-feature repeats for every
    cluster simultaneously. Returns ``cluster_id ->
    (intermediaries, addresses, officers)``."""
    empty: tuple[list[IntermediaryRepeat], list[AddressRepeat], list[OfficerRepeat]] = (
        [],
        [],
        [],
    )
    if not cluster_members or edges_df is None or edges_df.height == 0:
        return {cid: empty for cid in cluster_members}

    uid_to_cluster: dict[str, int] = {}
    all_member_uids: list[str] = []
    for cid, uids in cluster_members.items():
        for u in uids:
            uid_to_cluster[u] = cid
            all_member_uids.append(u)

    member_set = set(uid_to_cluster.keys())
    if not member_set:
        return {cid: empty for cid in cluster_members}

    incident = edges_df.filter(
        pl.col("src_node").is_in(all_member_uids) | pl.col("dst_node").is_in(all_member_uids)
    )

    addr_lookup = _lookup_by_source_id(addresses_df)
    off_lookup = _lookup_by_source_id(officers_df)
    inter_lookup = _lookup_by_source_id(intermediaries_df)
    global_deg = _global_degree_from_edges(edges_df)

    # (cluster_id, other_node, kind) -> {member_uid: leak_label}
    bucket: dict[tuple[int, str, str], dict[str, str]] = defaultdict(dict)
    for r in incident.iter_rows(named=True):
        s, d = r["src_node"], r["dst_node"]
        kind = _classify_edge_kind(r.get("kind_raw"))
        if kind == "other":
            continue
        if s in member_set:
            member_uid, other = s, d
        elif d in member_set:
            member_uid, other = d, s
        else:
            continue
        cid = uid_to_cluster[member_uid]
        bucket[(cid, other, kind)][member_uid] = r.get("source_label") or ""

    per_cluster: dict[
        int, tuple[list[IntermediaryRepeat], list[AddressRepeat], list[OfficerRepeat]]
    ] = {cid: ([], [], []) for cid in cluster_members}

    for (cid, other, kind), members in bucket.items():
        if len(members) < min_members:
            continue
        sid = other.split(":", 1)[1] if ":" in other else other
        leak_labels = sorted({lbl for lbl in members.values() if lbl})
        n_global = int(global_deg.get(other, 0))
        if kind == "address":
            meta = addr_lookup.get(sid) or {}
            per_cluster[cid][1].append(
                AddressRepeat(
                    node=other,
                    text=meta.get("raw_text") or meta.get("normalized_text"),
                    country=meta.get("country"),
                    n_members_served=len(members),
                    member_uids=sorted(members.keys()),
                    n_global_edges=n_global,
                    leak_labels=leak_labels,
                )
            )
        elif kind == "officer":
            meta = off_lookup.get(sid) or {}
            per_cluster[cid][2].append(
                OfficerRepeat(
                    node=other,
                    name=meta.get("name"),
                    country=meta.get("country"),
                    role=None,
                    n_members_served=len(members),
                    member_uids=sorted(members.keys()),
                    n_global_edges=n_global,
                    leak_labels=leak_labels,
                )
            )
        elif kind == "intermediary":
            meta = inter_lookup.get(sid) or {}
            per_cluster[cid][0].append(
                IntermediaryRepeat(
                    node=other,
                    name=meta.get("name"),
                    country=meta.get("country"),
                    n_members_served=len(members),
                    member_uids=sorted(members.keys()),
                    n_global_edges=n_global,
                    leak_labels=leak_labels,
                )
            )

    for cid, (inters, addrs, offs) in per_cluster.items():
        inters.sort(key=lambda x: (-x.n_members_served, -x.n_global_edges))
        addrs.sort(key=lambda x: (-x.n_members_served, -x.n_global_edges))
        offs.sort(key=lambda x: (-x.n_members_served, -x.n_global_edges))
        per_cluster[cid] = (inters[:top_n], addrs[:top_n], offs[:top_n])

    return per_cluster


def rank_clusters_by_investigative_value(
    cluster_members: dict[int, list[str]],
    *,
    company_df: pl.DataFrame,
    edges_df: pl.DataFrame | None = None,
    addresses_df: pl.DataFrame | None = None,
    officers_df: pl.DataFrame | None = None,
    intermediaries_df: pl.DataFrame | None = None,
    centrality_df: pl.DataFrame | None = None,
    sanctions_df: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Score every cluster and return a polars DataFrame sorted by
    ``investigative_score`` descending.

    Columns:
    - ``cluster_id``, ``size``, ``sources``, ``jurisdictions``,
      ``leaks_present``
    - the seven feature columns from ``InvestigativeFeatures``
    - ``investigative_score`` (= total of the seven)
    - ``top_intermediary``, ``top_address``, ``top_officer`` (display)
    - ``sample_names`` (display)
    """
    if not cluster_members:
        return pl.DataFrame(
            schema={
                "cluster_id": pl.Int64,
                "size": pl.Int64,
                "sources": pl.String,
                "jurisdictions": pl.String,
                "leaks_present": pl.String,
                "intermediary_rarity": pl.Float64,
                "cross_jurisdiction_bridge": pl.Float64,
                "sanctions_proximity": pl.Float64,
                "registry_anchor_density": pl.Float64,
                "hidden_central_entity": pl.Float64,
                "dormant_but_connected": pl.Float64,
                "shell_reuse": pl.Float64,
                "investigative_score": pl.Float64,
                "n_anomalies": pl.Int64,
                "n_high_severity_anomalies": pl.Int64,
                "top_anomaly_kind": pl.String,
                "n_edges_incident": pl.Int64,
                "n_leak_labels": pl.Int64,
                "n_sources": pl.Int64,
                "top_intermediary": pl.String,
                "top_address": pl.String,
                "top_officer": pl.String,
                "sample_names": pl.String,
            }
        )

    repeats_by_cluster = _batch_gather_repeats(
        cluster_members,
        edges_df=edges_df,
        addresses_df=addresses_df,
        officers_df=officers_df,
        intermediaries_df=intermediaries_df,
    )

    # Late import — anomalies pulls dataclasses from this module under
    # TYPE_CHECKING, so the runtime import lands here.
    from shellnet.investigations.anomalies import detect_all

    rows: list[dict[str, Any]] = []
    for cid, uids in cluster_members.items():
        members = gather_member_attrs(company_df, uids)
        inters, addrs, offs = repeats_by_cluster.get(cid, ([], [], []))
        jur = compute_jurisdiction_profile(members)
        cent = annotate_centrality(centrality_df, [m.entity_uid for m in members])
        sanctions = filter_sanctions_anchors(sanctions_df, [m.entity_uid for m in members])
        f = score_investigative_value(
            members=members,
            intermediaries=inters,
            addresses=addrs,
            officers=offs,
            jurisdictions=jur,
            sanctions_anchors=sanctions,
            centrality=cent,
        )
        flags = detect_all(
            members,
            intermediaries=inters,
            addresses=addrs,
            officers=offs,
            centrality=cent,
            edges_df=edges_df,
        )
        n_high = sum(1 for fl in flags if fl.severity == "high")
        top_anomaly_kind = flags[0].kind if flags else ""

        leaks: set[str] = set()
        for repeat in (*inters, *addrs, *offs):
            leaks.update(repeat.leak_labels)

        # Edge-density signal: edges incident to any cluster member in the
        # full edges_df. Computed cheaply once per cluster.
        n_edges = 0
        if edges_df is not None and edges_df.height:
            n_edges = edges_df.filter(
                pl.col("src_node").is_in(uids) | pl.col("dst_node").is_in(uids)
            ).height

        rows.append(
            {
                "cluster_id": int(cid),
                "size": len(members),
                "sources": "|".join(sorted({m.source for m in members})),
                "jurisdictions": "|".join(
                    f"{j}={n}" for j, n in sorted(jur.counts.items(), key=lambda kv: -kv[1])
                ),
                "leaks_present": "|".join(sorted(leaks)),
                "intermediary_rarity": f.intermediary_rarity,
                "cross_jurisdiction_bridge": f.cross_jurisdiction_bridge,
                "sanctions_proximity": f.sanctions_proximity,
                "registry_anchor_density": f.registry_anchor_density,
                "hidden_central_entity": f.hidden_central_entity,
                "dormant_but_connected": f.dormant_but_connected,
                "shell_reuse": f.shell_reuse,
                "investigative_score": f.total,
                "n_anomalies": len(flags),
                "n_high_severity_anomalies": n_high,
                "top_anomaly_kind": top_anomaly_kind,
                "n_edges_incident": n_edges,
                "n_leak_labels": len(leaks),
                "n_sources": len({m.source for m in members}),
                "top_intermediary": ((inters[0].name or inters[0].node)[:60] if inters else ""),
                "top_address": ((addrs[0].text or addrs[0].node)[:80] if addrs else ""),
                "top_officer": ((offs[0].name or offs[0].node)[:60] if offs else ""),
                "sample_names": " · ".join(m.name[:30] for m in members if m.name)[:120],
            }
        )

    return pl.DataFrame(rows).sort(["investigative_score", "size"], descending=[True, True])


def render_investigative_ranking_markdown(
    ranking_df: pl.DataFrame,
    *,
    defensibility_df: pl.DataFrame | None = None,
    top_n: int = 50,
    dedupe_run_id: str | None = None,
    generated_at: datetime | None = None,
    inputs_meta: dict[str, Any] | None = None,
) -> str:
    """Top-N investigative-value ranking. If ``defensibility_df`` is
    supplied (the ``cluster_ranking.parquet`` produced by
    ``scripts/rank_clusters.py``), it is joined on ``cluster_id`` so the
    table shows both axes side-by-side."""
    generated_at = generated_at or datetime.now(UTC)
    inputs_meta = inputs_meta or {}
    lines: list[str] = []
    lines.append("# Clusters ranked by investigative value")
    lines.append("")
    lines.append(
        f"Generated `{generated_at.isoformat(timespec='seconds')}`"
        + (f" from dedupe run `{dedupe_run_id}`." if dedupe_run_id else ".")
    )
    lines.append("")
    lines.append(
        '> Investigative value asks **"is there a story here?"** — distinct from '
        'the existing defensibility score, which asks **"is the dedupe right?"** '
        "Clusters that rank high on *both* axes are the strongest publication "
        "candidates. Treat the score as a hypothesis-ranker, not a finding."
    )
    lines.append("")
    lines.append(
        "Score components (each in [0, 1], summed unweighted): "
        "`intermediary_rarity`, `cross_jurisdiction_bridge`, `sanctions_proximity`, "
        "`registry_anchor_density`, `hidden_central_entity`, `dormant_but_connected`, "
        "`shell_reuse`. See `cluster_explainer.score_investigative_value` for "
        "definitions."
    )
    lines.append("")

    df = ranking_df.head(top_n)

    joined = defensibility_df is not None and "cluster_id" in (
        defensibility_df.columns if defensibility_df is not None else []
    )
    if joined and defensibility_df is not None:
        cols = ["cluster_id"]
        if "score" in defensibility_df.columns:
            cols.append("score")
        df = df.join(
            defensibility_df.select(cols).rename({"score": "defensibility"})
            if "score" in defensibility_df.columns
            else defensibility_df.select(cols),
            on="cluster_id",
            how="left",
        )

    lines.append(f"## Top {min(top_n, ranking_df.height)}")
    lines.append("")
    header_cols = [
        "cluster_id",
        "inv_score",
    ]
    if joined and "defensibility" in df.columns:
        header_cols.append("defensibility")
    header_cols += [
        "size",
        "src",
        "jur",
        "rarity",
        "bridge",
        "sanc",
        "anchor",
        "hidden",
        "dormant",
        "reuse",
        "top intermediary",
        "top address",
        "sample names",
    ]
    numeric_cols = {
        "cluster_id",
        "size",
        "inv_score",
        "defensibility",
        "rarity",
        "bridge",
        "sanc",
        "anchor",
        "hidden",
        "dormant",
        "reuse",
    }
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append(
        "| " + " | ".join("---:" if c in numeric_cols else "---" for c in header_cols) + " |"
    )

    for r in df.iter_rows(named=True):
        cells = [
            str(r["cluster_id"]),
            f"{r['investigative_score']:.2f}",
        ]
        if joined and "defensibility" in df.columns:
            d = r.get("defensibility")
            cells.append(f"{d:.2f}" if d is not None else "")
        cells += [
            str(r["size"]),
            r["sources"],
            r["jurisdictions"],
            f"{r['intermediary_rarity']:.2f}",
            f"{r['cross_jurisdiction_bridge']:.2f}",
            f"{r['sanctions_proximity']:.2f}",
            f"{r['registry_anchor_density']:.2f}",
            f"{r['hidden_central_entity']:.2f}",
            f"{r['dormant_but_connected']:.2f}",
            f"{r['shell_reuse']:.2f}",
            r["top_intermediary"],
            r["top_address"][:60],
            r["sample_names"],
        ]
        lines.append("| " + " | ".join(_md_cell(c) for c in cells) + " |")

    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Clusters scored: {ranking_df.height}")
    if dedupe_run_id:
        lines.append(f"- Dedupe run: `{dedupe_run_id}`")
    if joined:
        lines.append("- Joined with defensibility from `cluster_ranking.parquet`.")
    for k, v in inputs_meta.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    return "\n".join(lines)


def _md_cell(s: Any) -> str:
    if s is None:
        return ""
    return str(s).replace("|", "/").replace("\n", " ").strip()
