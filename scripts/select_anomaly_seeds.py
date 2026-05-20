"""Select cluster-member UIDs from the top-N anomaly-ranked communities.

Phase 11 of the data-source-utilization roadmap. The current
``build_confidence_graph`` BFS anchors on 363 rare-officer dossier
seeds. That set is narrow and biased toward people-side anchors; it
misses high-anomaly company-side clusters that the Phase 7 recluster
already surfaced. This script reads the previous recluster's anomaly
report and emits a parquet of UIDs from the top-N anomaly-ranked
communities, ready to feed back into the next recluster via the
``--extra-seeds`` flag.

Reads:
* ``processed/confidence_community_anomalies.parquet`` (anomaly scores)
* ``processed/confidence_communities.parquet`` (per-node membership)

Writes:
* ``processed/anomaly_seed_uids.parquet`` columns::

    uid               str    the node UID to seed the next BFS on
    community_id      i64    which community this UID came from
    anomaly_score     f64    that community's score (joined back)

Why a separate script instead of inline in build_confidence_graph:
* The anomaly table is an output of build_confidence_graph itself,
  so this script must run AFTER one recluster pass and BEFORE the
  next. Inlining would create a chicken-and-egg dependency.
* Keeping it standalone makes the seed-set composition auditable —
  the parquet is committed alongside the report and shows exactly
  which communities the next pass anchored on.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import polars as pl

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

log = logging.getLogger("select_anomaly_seeds")


def select(
    anomalies: pl.DataFrame,
    communities: pl.DataFrame,
    *,
    top_n: int = 10,
    min_anomaly_score: float = 0.5,
    threshold: float = 0.9,
) -> pl.DataFrame:
    """Return the UIDs in the top-N anomaly-ranked communities.

    Args:
        anomalies: ``confidence_community_anomalies.parquet`` payload.
            Must carry ``community_id`` and ``anomaly_score``.
        communities: ``confidence_communities.parquet`` payload. Must
            carry ``node_uid``, ``community_id``, and ``threshold``.
        top_n: how many top-scoring communities to pull seeds from.
        min_anomaly_score: floor; communities below this are dropped
            even if they're in the top N. Default 0.5 so we never
            seed on indistinct clusters.
        threshold: the community-partition threshold to read from.
            Default 0.9 to match the anomaly table's strict threshold.

    Returns a DataFrame with columns: uid, community_id, anomaly_score.
    """

    if anomalies.is_empty():
        return _empty()

    top = (
        anomalies.filter(pl.col("anomaly_score") >= min_anomaly_score)
        .sort("anomaly_score", descending=True)
        .head(top_n)
        .select("community_id", "anomaly_score")
    )
    if top.is_empty():
        return _empty()

    members = (
        communities.filter(pl.col("threshold") == threshold)
        .select(
            pl.col("node_uid").alias("uid"),
            "community_id",
        )
        .join(top, on="community_id", how="inner")
        .unique(subset=["uid"])
    )
    return members


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "uid": pl.String,
            "community_id": pl.Int64,
            "anomaly_score": pl.Float64,
        }
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--anomalies",
        type=Path,
        default=Path("/data/processed/confidence_community_anomalies.parquet"),
    )
    p.add_argument(
        "--communities",
        type=Path,
        default=Path("/data/processed/confidence_communities.parquet"),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/anomaly_seed_uids.parquet"),
    )
    p.add_argument("--top-n", type=int, default=10)
    p.add_argument("--min-anomaly-score", type=float, default=0.5)
    p.add_argument(
        "--threshold",
        type=float,
        default=0.9,
        help="Community-partition threshold to read membership from.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.anomalies.exists():
        raise SystemExit(f"[fatal] {args.anomalies} missing (run a recluster first)")
    if not args.communities.exists():
        raise SystemExit(f"[fatal] {args.communities} missing (run a recluster first)")

    anomalies = pl.read_parquet(args.anomalies)
    communities = pl.read_parquet(args.communities)
    log.info(
        "loaded %d anomaly rows, %d community-membership rows",
        anomalies.height,
        communities.height,
    )

    seeds = select(
        anomalies,
        communities,
        top_n=args.top_n,
        min_anomaly_score=args.min_anomaly_score,
        threshold=args.threshold,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    seeds.write_parquet(args.out)
    log.info(
        "wrote %d unique anomaly-seed UIDs to %s (top_n=%d, min_score=%.2f, threshold=%.2f)",
        seeds.height,
        args.out,
        args.top_n,
        args.min_anomaly_score,
        args.threshold,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
