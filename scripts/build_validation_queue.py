"""Validation queue: top candidates for manual deep-validation.

Combines every existing surfacing channel into one ranked queue scored
on four axes:

  priority = (strange ^ α) × (confident ^ β) × (connected ^ γ) × (underreported ^ δ)

with defaults α=1.2, β=1.0, γ=0.7, δ=1.3 — privileges
"weird + unreported" over "big + safe".

Operationalised:
  strange       = anomaly_score (from confidence_community_anomalies)
  confident     = cluster_confidence (from confidence_cluster_scored)
  connected     = log(size) / log(max_size)
  underreported = 1 - source_attestation_density

Source-attestation density is the fraction of member names that appear
(by casefold-equality) in any of OpenSanctions / GLEIF / UK PSC /
UK disqualified. Low density means the cluster is unreported in
formal-registry channels.

Output: validation_queue.parquet (top-N with full supporting evidence).
The companion renderer produces docs/reports/validation_queue.md
which is the case-by-case input to manual validation. Step 3 of the
4-step plan (manual validation) is NOT automated — see
docs/validation/template.md for the workbook to fill in per candidate.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


_STRICT_THRESHOLD = 0.9  # community membership read at this threshold


def _maybe_read(p: Path) -> pl.DataFrame | None:
    if not p.exists():
        log.warning("missing: %s", p.name)
        return None
    return pl.read_parquet(p)


def _build_uid_name_map(entities: pl.DataFrame, officers: pl.DataFrame | None) -> dict[str, str]:
    """uid (icij:NNN) -> normalised lowercase name."""
    out: dict[str, str] = {}
    for r in entities.select("source_id", "name").iter_rows(named=True):
        if r["source_id"] is None or r["name"] is None:
            continue
        out[f"icij:{r['source_id']}"] = str(r["name"]).casefold().strip()
    if officers is not None:
        for r in officers.select("source_id", "name").iter_rows(named=True):
            if r["source_id"] is None or r["name"] is None:
                continue
            out[f"icij:{r['source_id']}"] = str(r["name"]).casefold().strip()
    return out


def _build_attestation_name_set(df: pl.DataFrame | None, candidates: list[str]) -> set[str]:
    if df is None:
        return set()
    for c in candidates:
        if c in df.columns:
            return {
                str(v).casefold().strip() for v in df.select(c).to_series().drop_nulls().to_list()
            }
    return set()


@app.command()
def main(
    cluster_scored: Path = typer.Option(
        PROCESSED_DIR / "confidence_cluster_scored.parquet", "--cluster-scored"
    ),
    anomalies: Path = typer.Option(
        PROCESSED_DIR / "confidence_community_anomalies.parquet", "--anomalies"
    ),
    communities: Path = typer.Option(
        PROCESSED_DIR / "confidence_communities.parquet", "--communities"
    ),
    entities_parquet: Path = typer.Option(INTERIM_DIR / "icij_entities.parquet", "--entities"),
    officers_parquet: Path = typer.Option(INTERIM_DIR / "icij_officers.parquet", "--officers"),
    os_persons: Path = typer.Option(
        PROCESSED_DIR / "os_sanctioned_persons.parquet", "--os-persons"
    ),
    gleif_parquet: Path = typer.Option(INTERIM_DIR / "gleif_l2_relationships.parquet", "--gleif"),
    uk_psc_parquet: Path = typer.Option(PROCESSED_DIR / "uk_psc_dob.parquet", "--uk-psc"),
    uk_disq_parquet: Path = typer.Option(
        INTERIM_DIR / "uk_disqualified_directors.parquet", "--uk-disq"
    ),
    out_parquet: Path = typer.Option(PROCESSED_DIR / "validation_queue.parquet", "--out-parquet"),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "validation_queue_summary.json", "--out-summary"
    ),
    top_n: int = typer.Option(20, "--top-n"),
    alpha: float = typer.Option(1.2, "--alpha", help="weight on strangeness"),
    beta: float = typer.Option(1.0, "--beta", help="weight on confidence"),
    gamma: float = typer.Option(0.7, "--gamma", help="weight on connectedness"),
    delta: float = typer.Option(1.3, "--delta", help="weight on underreportedness"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()

    scored = pl.read_parquet(cluster_scored)
    anom = pl.read_parquet(anomalies)
    comm = pl.read_parquet(communities)
    entities = pl.read_parquet(entities_parquet)
    officers = _maybe_read(officers_parquet)
    os_p = _maybe_read(os_persons)
    gleif = _maybe_read(gleif_parquet)
    uk_psc = _maybe_read(uk_psc_parquet)
    uk_disq = _maybe_read(uk_disq_parquet)

    # Join cluster_scored × anomalies on community_id.
    # Anomalies parquet has `size` too; rename to avoid the join clash.
    anom_renamed = anom.rename({"size": "size_anom"})
    base = scored.join(
        anom_renamed.select(
            "community_id", "anomaly_score", "seed_density", "isolation", "size_deviation"
        ),
        on="community_id",
        how="left",
    )
    log.info("joined cluster_scored × anomalies: %d rows", base.height)

    # Max cluster size for connectedness normalisation.
    max_size = int(base.select(pl.col("size").max()).item() or 1)
    log.info("max cluster size in scope: %d", max_size)

    # Build the uid -> name map for member-name resolution.
    uid_to_name = _build_uid_name_map(entities, officers)
    log.info("name map: %d uids resolved", len(uid_to_name))

    # Build attestation name sets.
    os_names = _build_attestation_name_set(os_p, ["name", "caption", "primary_name"])
    gleif_names = _build_attestation_name_set(gleif, ["start_name", "entity_legal_name", "name"])
    uk_psc_names = _build_attestation_name_set(uk_psc, ["officer_name", "name"])
    uk_disq_names = _build_attestation_name_set(uk_disq, ["full_name", "name", "person_name"])
    all_attest = os_names | gleif_names | uk_psc_names | uk_disq_names
    log.info(
        "attestation pools: OS=%d GLEIF=%d UK_PSC=%d UK_DISQ=%d (union=%d)",
        len(os_names),
        len(gleif_names),
        len(uk_psc_names),
        len(uk_disq_names),
        len(all_attest),
    )

    # Per-community member lookup at strict threshold.
    strict_members = comm.filter(pl.col("threshold") == _STRICT_THRESHOLD).select(
        "community_id", "node_uid"
    )
    cid_to_members: dict[int, list[str]] = {}
    for r in strict_members.iter_rows(named=True):
        cid_to_members.setdefault(int(r["community_id"]), []).append(str(r["node_uid"]))

    # Per-community attestation density.
    def _attest_density(cid: int) -> float:
        members = cid_to_members.get(cid, [])
        if not members:
            return 0.0
        hits = 0
        for uid in members:
            name = uid_to_name.get(uid)
            if name and name in all_attest:
                hits += 1
        return hits / len(members)

    rows: list[dict] = []
    for r in base.iter_rows(named=True):
        cid = int(r["community_id"])
        size = int(r["size"])
        if size < 3:
            # Singletons and pairs are not investigatively useful.
            continue
        confidence = float(r.get("cluster_confidence") or 0.0)
        anomaly = float(r.get("anomaly_score") or 0.0)
        connected = math.log(size) / math.log(max_size) if max_size > 1 else 0.0
        attest_density = _attest_density(cid)
        underreported = 1.0 - attest_density

        # Clamp components into (0, 1] before exponentiation to avoid 0^x
        # zeroing the whole product on a single weak axis. Floor at 0.01.
        s = max(anomaly, 0.01)
        c = max(confidence, 0.01)
        k = max(connected, 0.01)
        u = max(underreported, 0.01)
        priority = (s**alpha) * (c**beta) * (k**gamma) * (u**delta)

        members = cid_to_members.get(cid, [])
        # Resolve to display names (preserving original case where possible).
        display_names: list[str] = []
        for uid in members[:10]:
            # Original-case lookup.
            nid = uid.removeprefix("icij:")
            ent_hit = entities.filter(pl.col("source_id").cast(pl.Utf8) == nid)
            if ent_hit.height > 0:
                display_names.append(str(ent_hit.row(0, named=True).get("name") or uid))
                continue
            if officers is not None:
                off_hit = officers.filter(pl.col("source_id").cast(pl.Utf8) == nid)
                if off_hit.height > 0:
                    display_names.append(str(off_hit.row(0, named=True).get("name") or uid))
                    continue
            display_names.append(uid)

        rows.append(
            {
                "community_id": cid,
                "size": size,
                "anomaly_score": round(anomaly, 4),
                "cluster_confidence": round(confidence, 4),
                "connectedness": round(connected, 4),
                "attestation_density": round(attest_density, 4),
                "underreportedness": round(underreported, 4),
                "mean_edge_credibility": float(r.get("mean_edge_credibility") or 0.0),
                "contradiction_density": float(r.get("contradiction_density") or 0.0),
                "n_seeds": int(r.get("n_seeds") or 0),
                "isolation": float(r.get("isolation") or 0.0),
                "priority_score": round(priority, 6),
                "member_uids_sample": members[:10],
                "member_names_sample": display_names,
            }
        )

    queue_df = pl.DataFrame(rows).sort("priority_score", descending=True)
    log.info("queue eligible (size >=3): %d communities", queue_df.height)
    queue_df.head(top_n).write_parquet(out_parquet)
    log.info("wrote top-%d queue to %s", top_n, out_parquet)

    summary = {
        "report": "validation_queue",
        "weighting": {"alpha": alpha, "beta": beta, "gamma": gamma, "delta": delta},
        "formula": (
            "priority = (strange ^ α) × (confident ^ β) × (connected ^ γ) × (underreported ^ δ)"
        ),
        "scope_note": (
            "Drawn from the dossier-anchored confidence subgraph "
            "(2-hop around 363 dossier seeds, ~7-8k nodes). This is more "
            "analytically rigorous than corpus-wide because it has the full "
            "uncertainty-propagation stack computed (mean_edge_credibility, "
            "contradiction_density, cluster_confidence). A v2 covering the "
            "full 3.3M-edge corpus would require running confidence-graph "
            "scoring at corpus scale, which is parked."
        ),
        "n_communities_eligible": int(queue_df.height),
        "top_n": top_n,
        "max_cluster_size": max_size,
        "attestation_pools": {
            "OpenSanctions": len(os_names),
            "GLEIF": len(gleif_names),
            "UK_PSC": len(uk_psc_names),
            "UK_disqualified": len(uk_disq_names),
            "union": len(all_attest),
        },
        "priority_distribution": {
            "max": float(queue_df.select(pl.col("priority_score").max()).item() or 0.0),
            "p95": float(queue_df.select(pl.col("priority_score").quantile(0.95)).item() or 0.0),
            "median": float(queue_df.select(pl.col("priority_score").median()).item() or 0.0),
            "min": float(queue_df.select(pl.col("priority_score").min()).item() or 0.0),
        },
    }
    out_summary.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log.info("wrote summary: %s", out_summary)


if __name__ == "__main__":
    app()
