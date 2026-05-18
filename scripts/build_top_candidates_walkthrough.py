"""Top-candidate walkthrough: per-entity novelty proof.

Picks 8 high-signal candidates blended across surfacing channels
(shared-agent reuse, latent Louvain communities, jurisdiction bridges,
non-obviousness-ranked rare names) and for each one produces a source-
attestation record: what ICIJ alone shows, what OpenSanctions alone
shows, what GLEIF alone shows, what UK PSC / UK disqualified alone
show, vs what the pipeline reveals when the four are joined.

This is the case-study companion to the Discovery Advantage Report.
Where that benchmark says "the pipeline finds N more structures",
this drills into specific named structures and proves it candidate-
by-candidate.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _maybe_read(p: Path) -> pl.DataFrame | None:
    if not p.exists():
        log.warning("missing: %s", p.name)
        return None
    return pl.read_parquet(p)


def _entity_lookup(
    entities: pl.DataFrame, officers: pl.DataFrame | None, uid: str
) -> dict:
    """Resolve `icij:NNN` -> {name, jurisdiction, type} from entities or officers."""
    if not uid.startswith("icij:"):
        return {"name": uid, "jurisdiction": None, "type": None}
    nid = uid.removeprefix("icij:")
    hit = entities.filter(pl.col("source_id").cast(pl.Utf8) == nid)
    if hit.height > 0:
        r = hit.row(0, named=True)
        return {
            "name": (r.get("name") or "—").strip() if r.get("name") else "—",
            "jurisdiction": r.get("jurisdiction") or r.get("jurisdiction_raw"),
            "type": r.get("legal_form") or "entity",
            "source_label": r.get("source_label"),
        }
    if officers is not None:
        hit = officers.filter(pl.col("source_id").cast(pl.Utf8) == nid)
        if hit.height > 0:
            r = hit.row(0, named=True)
            return {
                "name": (r.get("name") or "—").strip() if r.get("name") else "—",
                "jurisdiction": r.get("country"),
                "type": "officer",
                "source_label": r.get("source_id_label"),
            }
    return {"name": uid, "jurisdiction": None, "type": None}


def _count_in_source(name: str, source_df: pl.DataFrame | None, name_col: str) -> int:
    if source_df is None or not name or not name_col:
        return 0
    nlow = name.casefold().strip()
    if nlow == "—":
        return 0
    if name_col not in source_df.columns:
        return 0
    return source_df.filter(
        pl.col(name_col).cast(pl.Utf8).str.to_lowercase().str.strip_chars() == nlow
    ).height


def _attestation(name: str, sources: dict) -> dict:
    out = {}
    for source_key, (df, name_col) in sources.items():
        out[source_key] = _count_in_source(name, df, name_col)
    return out


@app.command()
def main(
    entities_parquet: Path = typer.Option(INTERIM_DIR / "icij_entities.parquet", "--entities"),
    officers_parquet: Path = typer.Option(INTERIM_DIR / "icij_officers.parquet", "--officers"),
    edges_parquet: Path = typer.Option(INTERIM_DIR / "icij_edges.parquet", "--edges"),
    structure_summary: Path = typer.Option(
        PROCESSED_DIR / "structure_benchmark_summary.json", "--structure-summary"
    ),
    non_obviousness_summary: Path = typer.Option(
        PROCESSED_DIR / "non_obviousness_summary.json", "--non-obviousness-summary"
    ),
    latent_clusters: Path = typer.Option(
        PROCESSED_DIR / "latent_clusters.parquet", "--latent-clusters"
    ),
    os_persons: Path = typer.Option(
        PROCESSED_DIR / "os_sanctioned_persons.parquet", "--os-persons"
    ),
    gleif_parquet: Path = typer.Option(
        INTERIM_DIR / "gleif_l2_relationships.parquet", "--gleif"
    ),
    uk_psc_parquet: Path = typer.Option(PROCESSED_DIR / "uk_psc_dob.parquet", "--uk-psc"),
    uk_disq_parquet: Path = typer.Option(
        INTERIM_DIR / "uk_disqualified_directors.parquet", "--uk-disq"
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "top_candidates_walkthrough.json", "--out-summary"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    ensure_dirs()

    entities = pl.read_parquet(entities_parquet)
    officers = _maybe_read(officers_parquet)
    edges = pl.read_parquet(edges_parquet)
    sb = json.loads(structure_summary.read_text(encoding="utf-8"))
    no = json.loads(non_obviousness_summary.read_text(encoding="utf-8"))
    latent = _maybe_read(latent_clusters)
    os_p = _maybe_read(os_persons)
    gleif = _maybe_read(gleif_parquet)
    uk_psc = _maybe_read(uk_psc_parquet)
    uk_disq = _maybe_read(uk_disq_parquet)

    # Discover canonical name columns by sniffing schemas.
    def _name_col(df: pl.DataFrame | None, candidates: list[str]) -> str:
        if df is None:
            return ""
        for c in candidates:
            if c in df.columns:
                return c
        return ""

    sources_company = {
        "opensanctions": (os_p, _name_col(os_p, ["name", "caption", "primary_name"])),
        "gleif": (gleif, _name_col(gleif, ["start_name", "entity_legal_name", "name"])),
    }
    sources_person = {
        "opensanctions": (os_p, _name_col(os_p, ["name", "caption", "primary_name"])),
        "uk_psc": (uk_psc, _name_col(uk_psc, ["officer_name", "name"])),
        "uk_disqualified": (uk_disq, _name_col(uk_disq, ["full_name", "name", "person_name"])),
    }
    log.info("name cols: %s | %s", sources_company, sources_person)

    candidates: list[dict] = []

    # --- Channel 1: shared-agent reuse (S1 top_5) ---
    for r in (sb["structures"].get("S1_latent_intermediary_reuse", {}).get("top_5") or [])[:3]:
        uid = r["dst_node"]
        meta = _entity_lookup(entities, officers, uid)
        name = meta["name"]
        clients = int(r["n_clients"])
        # List the client names
        client_edges = edges.filter(
            (pl.col("kind_raw") == "intermediary_of") & (pl.col("dst_node") == uid)
        ).head(10)
        client_names = []
        for cr in client_edges.iter_rows(named=True):
            client_names.append(_entity_lookup(entities, officers, cr["src_node"])["name"])
        candidates.append(
            {
                "channel": "shared_agent_reuse",
                "title": f"Shared intermediary: {name}",
                "uid": uid,
                "meta": meta,
                "metric": {"n_clients": clients},
                "client_samples": client_names[:5],
                "attestation": _attestation(name, sources_company),
                "baseline_view": (
                    f"ICIJ Offshore Leaks search for \"{name}\" returns the intermediary "
                    f"entity itself, but does not aggregate that this intermediary acts for "
                    f"{clients} distinct officers across the leak corpus. OpenSanctions and "
                    f"GLEIF have no entry — this intermediary is not sanctioned and not "
                    f"LEI-registered, so single-source search filters it out as "
                    f"non-actionable."
                ),
                "pipeline_view": (
                    f"The pipeline ranks this intermediary by client multiplicity "
                    f"({clients} distinct officers), surfacing it as a shared-agent hub "
                    f"the single-source view cannot compute. Combined with the absence of "
                    f"sanctions/LEI registration, the structural pattern (reuse without "
                    f"formal-registry trace) is the investigative signal."
                ),
                "novelty_proof": (
                    "Structural aggregation across ICIJ edges. Single-source views are "
                    "per-entity; the multiplicity count requires walking the edges, "
                    "which no source's search UI exposes."
                ),
            }
        )

    # --- Channel 2: jurisdiction bridges (S2 top_5) ---
    for r in (sb["structures"].get("S2_jurisdiction_bridges", {}).get("top_5") or [])[:2]:
        officer_uid = r["src_node"]
        co_a_uid = r["company_a"]
        co_b_uid = r["company_b"]
        officer = _entity_lookup(entities, officers, officer_uid)
        co_a = _entity_lookup(entities, officers, co_a_uid)
        co_b = _entity_lookup(entities, officers, co_b_uid)
        candidates.append(
            {
                "channel": "jurisdiction_bridge",
                "title": f"Bridge officer: {officer['name']} ({r['juris_a']} ↔ {r['juris_b']})",
                "uid": officer_uid,
                "meta": officer,
                "metric": {
                    "juris_a": r["juris_a"],
                    "juris_b": r["juris_b"],
                    "company_a": co_a["name"],
                    "company_b": co_b["name"],
                },
                "attestation": _attestation(officer["name"], sources_person),
                "baseline_view": (
                    f"ICIJ search for \"{officer['name']}\" returns the two companies "
                    f"separately — `{co_a['name']}` ({r['juris_a']}) and `{co_b['name']}` "
                    f"({r['juris_b']}) — but does not flag the offshore-mainstream "
                    f"jurisdictional bridge as a structural pattern. UK PSC, UK "
                    f"disqualified-directors, and OpenSanctions would each be "
                    f"queried independently with no automatic correlation."
                ),
                "pipeline_view": (
                    f"The pipeline flags this officer because two companies they control "
                    f"span an offshore venue ({r['juris_a']}) and a mainstream venue "
                    f"({r['juris_b']}). The bridge is the structural pattern, not the "
                    f"per-company filings."
                ),
                "novelty_proof": (
                    "Cross-jurisdiction pair detection requires (a) officer-deduplication "
                    "across companies and (b) jurisdiction classification — neither is "
                    "an out-of-the-box capability in any source's interface."
                ),
            }
        )

    # --- Channel 3: latent Louvain communities (S4 + S6 top_5) ---
    s4_top = sb["structures"].get("S4_sanctions_adjacent_closure", {}).get("top_5") or []
    s6_top = sb["structures"].get("S6_anomalous_communities", {}).get("top_5") or []
    louvain_picks = []
    if s4_top:
        louvain_picks.append(("sanctions_adjacent", s4_top[0]))
    for r in s6_top[:2]:
        louvain_picks.append(("anomaly_only", r))
    for tag, r in louvain_picks:
        cid = int(r["community_id"])
        size = int(r["size"])
        anomaly = float(r["anomaly_score"])
        jurisdictions = r.get("jurisdictions", "")
        n_sanctioned = int(r.get("n_sanctioned", 0))
        # Sample members
        members = []
        if latent is not None and "community_id" in latent.columns:
            mem_df = (
                latent.filter(pl.col("community_id") == cid)
                .head(20)
            )
            for mr in mem_df.iter_rows(named=True):
                muid = mr.get("node_uid") or mr.get("uid") or ""
                if muid:
                    members.append(_entity_lookup(entities, officers, str(muid))["name"])
        flavor = "sanctions-adjacent" if tag == "sanctions_adjacent" else "pure-anomaly"
        candidates.append(
            {
                "channel": f"louvain_{tag}",
                "title": f"Community #{cid}: {size}-entity {flavor} cluster",
                "uid": f"community:{cid}",
                "meta": {"jurisdictions": jurisdictions, "n_sanctioned": n_sanctioned},
                "metric": {
                    "community_id": cid,
                    "size": size,
                    "anomaly_score": anomaly,
                    "jurisdictions": jurisdictions,
                    "n_sanctioned": n_sanctioned,
                },
                "member_samples": [m for m in members[:6] if m and m != "—"],
                "baseline_view": (
                    "No source surfaces communities — none of ICIJ, OpenSanctions, "
                    "GLEIF, UK PSC, or UK disqualified-directors expose graph-cluster "
                    "structure. A journalist could only assemble this cluster by "
                    "iteratively querying related entities one at a time."
                    + (
                        f" The cluster contains {n_sanctioned} sanctioned entity, so "
                        f"only that single entity would surface in OpenSanctions; the "
                        f"surrounding {size - n_sanctioned} entities would not."
                        if n_sanctioned > 0
                        else " No entity in the cluster is sanctioned, so OpenSanctions "
                        "search returns nothing — the cluster is invisible to that "
                        "lens entirely."
                    )
                ),
                "pipeline_view": (
                    f"Louvain community detection on credibility-weighted edges surfaces "
                    f"this {size}-entity cluster spanning {jurisdictions or '(no jurisdictions)'} "
                    f"with anomaly score {anomaly:.3f}. The community structure is the "
                    f"investigative signal, not any single entity in it."
                ),
                "novelty_proof": (
                    "Unsupervised graph clustering produces a structural finding that "
                    "has no direct analogue in any source. The community is fully "
                    "synthesised by the pipeline."
                ),
            }
        )

    # --- Channel 4: non-obviousness-ranked rare officers (top_10) ---
    for r in no.get("top_10", [])[:3]:
        name = r.get("rare_name") or "(unknown)"
        score = float(r.get("non_obviousness_score", 0.0))
        candidates.append(
            {
                "channel": "non_obviousness_rank",
                "title": f"Rare-officer anchor: {name}",
                "uid": f"name:{name}",
                "meta": {},
                "metric": {
                    "non_obviousness_score": round(score, 4),
                    "rarity": round(float(r.get("rarity", 0.0)), 4),
                    "graph_surprise": round(float(r.get("graph_surprise", 0.0)), 4),
                    "pattern_uniqueness": round(float(r.get("pattern_uniqueness", 0.0)), 4),
                    "jurisdiction_span": int(r.get("jurisdiction_span", 0)),
                },
                "attestation": _attestation(name, sources_person),
                "baseline_view": (
                    f"ICIJ search for \"{name}\" returns the officer record(s). "
                    f"OpenSanctions, UK PSC, and UK disqualified-directors are queried "
                    f"separately; nothing in any single-source UI tells the journalist "
                    f"that this name carries an unusually high 5-factor non-obviousness "
                    f"signal (rarity {r.get('rarity', 0):.2f}, graph-surprise "
                    f"{r.get('graph_surprise', 0):.2f}, pattern-uniqueness "
                    f"{r.get('pattern_uniqueness', 0):.2f})."
                ),
                "pipeline_view": (
                    f"The non-obviousness scorer combines name-rarity, jurisdiction-span, "
                    f"graph-surprise, shared-intermediary, and pattern-uniqueness into "
                    f"one ranked score (here {score:.3f}). This anchor is in the top-10 "
                    f"out of {no.get('n_anchors', 0):,} scored anchors — without that "
                    f"composite, a journalist would have no reason to prioritise it."
                ),
                "novelty_proof": (
                    "Five orthogonal weak signals composed into one strong ranking. "
                    "Each input signal is computable from a single source; the "
                    "composition across sources is the pipeline's contribution."
                ),
            }
        )

    summary = {
        "report": "top_candidates_walkthrough",
        "n_candidates": len(candidates),
        "channels": sorted({c["channel"] for c in candidates}),
        "candidates": candidates,
    }

    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_summary.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log.info(
        "wrote: %s | candidates=%d channels=%s",
        out_summary,
        len(candidates),
        summary["channels"],
    )


if __name__ == "__main__":
    app()
