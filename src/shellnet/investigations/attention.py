"""Human attention optimizer — rank clusters by where an investigator
should look next.

Sits on top of every other ranker. Inputs are the parquets they produce
(plus optional defensibility from ``rank_clusters.py``); the output is
a single ``attention_score`` per cluster decomposed into six named
components so the briefing can show its work:

* ``novelty`` — how far this cluster sits in the upper percentile of
  the corpus on any investigative-feature axis. Boutique-rare
  signals score higher than ordinary ones.
* ``structural_anomaly`` — anomaly count weighted by severity.
* ``uncertainty_concentration`` — anomalies that specifically indicate
  conflicting or partial data (overlapping ids, no registry anchor,
  structural asymmetry).
* ``graph_centrality`` — eigenvector / betweenness signals already in
  the investigative feature set, surfaced separately so the attention
  ranker can weight them differently from the rest.
* ``evidence_density`` — number of corpus edges + leak labels + source
  filings; clusters with thicker evidence trails validate faster.
* ``cross_source_convergence`` — sources and leak-label diversity.

The CLI applies a diversity post-filter so the top-N output is not all
the same kind of cluster — different ``top_anomaly_kind`` headlines
take precedence so an investigator's queue doesn't look like 50
copies of the same finding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import polars as pl


@dataclass
class AttentionScore:
    cluster_id: int
    score: float
    components: dict[str, float] = field(default_factory=dict)
    headline: str = ""
    next_action: str = ""
    kind_tag: str = ""  # used for diversity post-filtering
    evidence: dict[str, Any] = field(default_factory=dict)


# Component weights — equal by default, tunable per call.
DEFAULT_WEIGHTS: dict[str, float] = {
    "novelty": 1.0,
    "structural_anomaly": 1.0,
    "uncertainty_concentration": 1.0,
    "graph_centrality": 1.0,
    "evidence_density": 1.0,
    "cross_source_convergence": 1.0,
}

# Anomaly kinds whose presence raises *uncertainty* specifically (not
# just structural risk). These are conflicts and partial signals.
UNCERTAINTY_ANOMALY_KINDS: frozenset[str] = frozenset(
    {
        "overlapping_lei",
        "overlapping_company_number",
        "no_registry_anchor",
        "structural_asymmetry",
        "contradictory_officer",
    }
)

SEVERITY_WEIGHTS = {"high": 3.0, "medium": 2.0, "low": 1.0}


# ---------------------------------------------------------------------------
# Per-cluster scoring
# ---------------------------------------------------------------------------


def _percentile(values: list[float], v: float) -> float:
    """Return the fraction of ``values`` strictly less than ``v`` (in [0, 1])."""
    if not values:
        return 0.0
    n_below = sum(1 for x in values if x < v)
    return n_below / len(values)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _next_action_for_row(r: dict[str, Any]) -> str:
    """Heuristic 'what to do next' string per cluster row."""
    top_anom = r.get("top_anomaly_kind") or ""
    if top_anom == "shell_reuse_anomaly":
        feat = r.get("top_address") or r.get("top_officer") or r.get("top_intermediary") or "?"
        return f"Trace the high-degree shared infrastructure: `{feat}`."
    if top_anom == "hidden_hub":
        return "Pull connections from the non-member hub node identified by centrality."
    if top_anom == "contradictory_officer":
        return (
            f"Audit officer `{r.get('top_officer') or '?'}` — appears across "
            "active and dormant members."
        )
    if top_anom in {"overlapping_lei", "overlapping_company_number"}:
        return "Reconcile cross-source identifier conflict before publishing."
    if top_anom == "impossible_timeline":
        return "Investigate timeline violation — date metadata is internally inconsistent."
    if top_anom == "cross_border_mirror":
        return (
            f"Validate the mirror across jurisdictions `{r.get('jurisdictions') or '?'}` — "
            "candidate same-entity in multiple registries."
        )
    if float(r.get("sanctions_proximity") or 0) > 0:
        return "Validate the sanctions list-match anchor against the official record."
    if float(r.get("registry_anchor_density") or 0) == 0 and (r.get("n_sources") or 0) >= 2:
        return "Cluster has no registry anchor — locate a national-registry record before claims."
    if float(r.get("cross_jurisdiction_bridge") or 0) >= 0.8:
        return f"Map the cross-jurisdiction bridge ({r.get('jurisdictions') or '?'})."
    return "Open the cluster briefing and review repeats + anomalies."


def _headline_for_row(r: dict[str, Any], components: dict[str, float]) -> str:
    """One-sentence 'why look here next'."""
    score = float(r.get("investigative_score") or 0)
    n_anom = int(r.get("n_anomalies") or 0)
    src = (r.get("sources") or "").split("|") if r.get("sources") else []
    n_jur = (r.get("jurisdictions") or "").count("|") + (1 if r.get("jurisdictions") else 0)
    top_component = max(components, key=components.get) if components else "?"
    return (
        f"size={r.get('size')}, sources={len(src)}, jurisdictions={n_jur}, "
        f"investigative={score:.2f}, anomalies={n_anom}; "
        f"top component → {top_component}."
    )


# ---------------------------------------------------------------------------
# Batch ranker
# ---------------------------------------------------------------------------


def rank_by_attention(
    investigative_df: pl.DataFrame,
    *,
    defensibility_df: pl.DataFrame | None = None,
    weights: dict[str, float] | None = None,
) -> pl.DataFrame:
    """Compute an ``attention_score`` per cluster row.

    ``investigative_df`` must carry the columns emitted by
    ``investigative_ranking.rank_clusters_by_investigative_value`` (in
    its extended shape: investigative components + anomaly counters +
    edge / leak / source counters).
    """
    if investigative_df.height == 0:
        return pl.DataFrame(
            schema={
                "cluster_id": pl.Int64,
                "attention_score": pl.Float64,
                "novelty": pl.Float64,
                "structural_anomaly": pl.Float64,
                "uncertainty_concentration": pl.Float64,
                "graph_centrality": pl.Float64,
                "evidence_density": pl.Float64,
                "cross_source_convergence": pl.Float64,
                "headline": pl.String,
                "next_action": pl.String,
                "kind_tag": pl.String,
                "size": pl.Int64,
                "sources": pl.String,
                "jurisdictions": pl.String,
                "investigative_score": pl.Float64,
                "n_anomalies": pl.Int64,
                "top_anomaly_kind": pl.String,
                "n_edges_incident": pl.Int64,
                "n_leak_labels": pl.Int64,
                "defensibility": pl.Float64,
            }
        )

    weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    df = investigative_df
    if defensibility_df is not None and "cluster_id" in defensibility_df.columns:
        cols = ["cluster_id"]
        if "score" in defensibility_df.columns:
            cols.append("score")
        sub = defensibility_df.select(cols)
        if "score" in sub.columns:
            sub = sub.rename({"score": "defensibility"})
        df = df.join(sub, on="cluster_id", how="left")
    elif "defensibility" not in df.columns:
        df = df.with_columns(pl.lit(None, dtype=pl.Float64).alias("defensibility"))

    inv_scores = df["investigative_score"].to_list()
    edge_counts = (
        df["n_edges_incident"].to_list() if "n_edges_incident" in df.columns else [0] * df.height
    )
    leak_counts = (
        df["n_leak_labels"].to_list() if "n_leak_labels" in df.columns else [0] * df.height
    )
    source_counts = df["n_sources"].to_list() if "n_sources" in df.columns else [0] * df.height
    centrality_values = df["hidden_central_entity"].to_list() if df.height else [0.0]
    centrality_max = max([0.0, *centrality_values])

    rows: list[dict[str, Any]] = []
    for r in df.iter_rows(named=True):
        # novelty: percentile of investigative_score against the corpus.
        novelty = _percentile(inv_scores, float(r["investigative_score"]))

        # structural_anomaly: severity-weighted anomaly count, normalised.
        n_anom = int(r.get("n_anomalies") or 0)
        n_high = int(r.get("n_high_severity_anomalies") or 0)
        n_med_low = max(0, n_anom - n_high)
        anom_raw = n_high * SEVERITY_WEIGHTS["high"] + n_med_low * SEVERITY_WEIGHTS["medium"]
        structural_anomaly = _clamp01(anom_raw / 10.0)

        # uncertainty_concentration: kinds in UNCERTAINTY_ANOMALY_KINDS +
        # a registry-anchor floor + an opensanctions-only-source bonus.
        top_kind = r.get("top_anomaly_kind") or ""
        uncertainty_terms = 0.0
        if top_kind in UNCERTAINTY_ANOMALY_KINDS:
            uncertainty_terms += 0.5
        if float(r.get("registry_anchor_density") or 0) == 0 and int(r.get("n_sources") or 0) >= 2:
            uncertainty_terms += 0.3
        if (r.get("sources") or "").startswith("opensanctions") and int(
            r.get("n_sources") or 0
        ) == 1:
            uncertainty_terms += 0.2
        uncertainty_concentration = _clamp01(uncertainty_terms)

        # graph_centrality: corpus-scaled hidden_central_entity.
        centrality_raw = float(r.get("hidden_central_entity") or 0)
        graph_centrality = _clamp01(centrality_raw / centrality_max) if centrality_max > 0 else 0.0

        # evidence_density: corpus percentile of edges + leaks, averaged.
        e_p = _percentile(edge_counts, float(r.get("n_edges_incident") or 0))
        l_p = _percentile(leak_counts, float(r.get("n_leak_labels") or 0))
        evidence_density = _clamp01((e_p + l_p) / 2.0)

        # cross_source_convergence: source count + sanctions term + percentile.
        n_src = int(r.get("n_sources") or 0)
        src_term = min(n_src, 4) / 4.0
        sanc_term = 0.3 if float(r.get("sanctions_proximity") or 0) > 0 else 0.0
        s_p = _percentile(source_counts, float(n_src))
        cross_source_convergence = _clamp01(0.5 * src_term + 0.3 * sanc_term + 0.2 * s_p)

        components = {
            "novelty": novelty,
            "structural_anomaly": structural_anomaly,
            "uncertainty_concentration": uncertainty_concentration,
            "graph_centrality": graph_centrality,
            "evidence_density": evidence_density,
            "cross_source_convergence": cross_source_convergence,
        }
        score = sum(weights[k] * v for k, v in components.items())

        headline = _headline_for_row(r, components)
        next_action = _next_action_for_row(r)
        kind_tag = top_kind or "uncategorised"

        rows.append(
            {
                "cluster_id": int(r["cluster_id"]),
                "attention_score": score,
                **components,
                "headline": headline,
                "next_action": next_action,
                "kind_tag": kind_tag,
                "size": int(r.get("size") or 0),
                "sources": r.get("sources") or "",
                "jurisdictions": r.get("jurisdictions") or "",
                "investigative_score": float(r.get("investigative_score") or 0),
                "n_anomalies": int(r.get("n_anomalies") or 0),
                "top_anomaly_kind": top_kind,
                "n_edges_incident": int(r.get("n_edges_incident") or 0),
                "n_leak_labels": int(r.get("n_leak_labels") or 0),
                "defensibility": (
                    float(r["defensibility"]) if r.get("defensibility") is not None else None
                ),
            }
        )

    return pl.DataFrame(rows).sort(
        ["attention_score", "investigative_score"], descending=[True, True]
    )


# ---------------------------------------------------------------------------
# Diversity-aware next-actions queue
# ---------------------------------------------------------------------------


def select_diverse_queue(ranking_df: pl.DataFrame, *, top_n: int = 10) -> pl.DataFrame:
    """Pick the top-``top_n`` rows with at most one cluster per
    ``kind_tag``; once a tag's been picked, fall back to lower-ranked
    candidates from already-seen tags so the queue still fills."""
    if ranking_df.height == 0:
        return ranking_df
    out_rows: list[dict[str, Any]] = []
    seen_tags: set[str] = set()
    overflow: list[dict[str, Any]] = []
    for r in ranking_df.iter_rows(named=True):
        if r["kind_tag"] not in seen_tags:
            out_rows.append(r)
            seen_tags.add(r["kind_tag"])
            if len(out_rows) == top_n:
                return pl.DataFrame(out_rows)
        else:
            overflow.append(r)
    for r in overflow:
        out_rows.append(r)
        if len(out_rows) == top_n:
            break
    return pl.DataFrame(out_rows) if out_rows else ranking_df.head(0)


# ---------------------------------------------------------------------------
# Markdown renderers
# ---------------------------------------------------------------------------


def render_attention_ranking_markdown(
    ranking_df: pl.DataFrame,
    *,
    top_n: int = 50,
    dedupe_run_id: str | None = None,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now(UTC)
    lines: list[str] = []
    lines.append("# Clusters ranked by investigator-attention")
    lines.append("")
    lines.append(
        f"Generated `{generated_at.isoformat(timespec='seconds')}`"
        + (f" from dedupe run `{dedupe_run_id}`." if dedupe_run_id else ".")
    )
    lines.append("")
    lines.append(
        "> The attention score is a weighted sum of six components — novelty, "
        "structural_anomaly, uncertainty_concentration, graph_centrality, "
        "evidence_density, cross_source_convergence — each in [0, 1] and "
        "explained per row. The order is investigator-priority, not "
        "publication-priority: clusters needing review *first* score higher."
    )
    lines.append("")
    if ranking_df.height == 0:
        lines.append("_No clusters scored._")
        return "\n".join(lines)

    lines.append(f"## Top {min(top_n, ranking_df.height)}")
    lines.append("")
    lines.append(
        "| # | cluster_id | attn | invest | def | "
        "nov | anom | unc | cent | evid | conv | kind | next action |"
    )
    lines.append(
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"
    )
    for i, r in enumerate(ranking_df.head(top_n).iter_rows(named=True), start=1):
        defens = f"{r['defensibility']:.2f}" if r.get("defensibility") is not None else ""
        next_action = (
            (r.get("next_action") or "").replace("|", "/").replace("\n", " ").strip()[:120]
        )
        lines.append(
            f"| {i} | {r['cluster_id']} | {r['attention_score']:.2f} | "
            f"{r['investigative_score']:.2f} | {defens} | "
            f"{r['novelty']:.2f} | {r['structural_anomaly']:.2f} | "
            f"{r['uncertainty_concentration']:.2f} | "
            f"{r['graph_centrality']:.2f} | {r['evidence_density']:.2f} | "
            f"{r['cross_source_convergence']:.2f} | "
            f"{r.get('top_anomaly_kind') or '·'} | {next_action} |"
        )
    return "\n".join(lines)


def render_next_actions_markdown(
    queue_df: pl.DataFrame,
    *,
    dedupe_run_id: str | None = None,
    generated_at: datetime | None = None,
) -> str:
    """The diversity-filtered next-actions queue. One representative
    per ``kind_tag`` until the cap is reached."""
    generated_at = generated_at or datetime.now(UTC)
    lines: list[str] = []
    lines.append("# Next-actions queue — investigator attention")
    lines.append("")
    lines.append(
        f"Generated `{generated_at.isoformat(timespec='seconds')}`"
        + (f" from dedupe run `{dedupe_run_id}`." if dedupe_run_id else ".")
    )
    lines.append("")
    lines.append(
        "> One representative per attention-kind so the queue doesn't look "
        "like 50 copies of the same finding. Open each in `explain_cluster` "
        "or the matching evidence bundle."
    )
    lines.append("")
    if queue_df.height == 0:
        lines.append("_Queue empty._")
        return "\n".join(lines)
    for i, r in enumerate(queue_df.iter_rows(named=True), start=1):
        lines.append(f"## {i}. Cluster `{r['cluster_id']}` — {r.get('kind_tag') or '·'}")
        lines.append("")
        lines.append(f"- **Attention score**: {r['attention_score']:.2f}")
        lines.append(f"- **Why**: {r.get('headline') or ''}")
        lines.append(f"- **Next action**: {r.get('next_action') or ''}")
        lines.append("")
        bits = []
        for k in (
            "novelty",
            "structural_anomaly",
            "uncertainty_concentration",
            "graph_centrality",
            "evidence_density",
            "cross_source_convergence",
        ):
            bits.append(f"{k}={r[k]:.2f}")
        lines.append("- Components: " + ", ".join(bits))
        lines.append("")
    return "\n".join(lines)
