"""Emit SEC bridge endpoint UIDs as extra seeds for the next recluster.

Phase 16 of the data-source-utilization roadmap. The previous run
proved that Phase 10's SEC<->ICIJ bridges enter the dossier-anchored
subgraph at hop 3 (the `same_company_as` count went 9 -> 10 on the
30k-cap recluster). But the SEC-to-SEC `beneficial_owner_of` edges
they unlock sit at hop 4 — out of budget.

The fix is to put bridge SEC endpoints into hop 0 alongside the
rare-officer dossier set and the Phase-11 anomaly seeds. Then the
BFS has three full hops to walk the SEC corpus from each bridge
landing site.

Reads:
* ``processed/sec_icij_bridges.parquet`` (Phase 10 output).

Writes:
* ``processed/bridge_endpoint_seeds.parquet`` columns::

    uid       str    sec:CIK pulled from the bridge src_uid
    source    str    constant "sec_bridge" — provenance tag so
                     a future reviewer can see which seed set
                     this row came from.

Why a separate parquet (rather than concatenating into Phase 11's
output): keeps the seed provenance auditable. The recluster reads
both via ``--extra-seeds`` so the BFS treats them identically, but
the source tags survive into downstream reports.
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

log = logging.getLogger("select_bridge_endpoints")


def select(bridges: pl.DataFrame) -> pl.DataFrame:
    """Return DataFrame with columns: uid, source.

    Args:
        bridges: ``sec_icij_bridges.parquet`` payload. Must carry
            ``src_uid`` (the ``sec:CIK`` side).

    Returns: deduped UIDs tagged with ``source = 'sec_bridge'``.
    """

    if bridges.is_empty() or "src_uid" not in bridges.columns:
        return _empty()

    return (
        bridges.select(pl.col("src_uid").alias("uid"))
        .drop_nulls()
        .unique()
        .with_columns(pl.lit("sec_bridge").alias("source"))
    )


def _empty() -> pl.DataFrame:
    return pl.DataFrame(schema={"uid": pl.String, "source": pl.String})


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--bridges",
        type=Path,
        default=Path("/data/processed/sec_icij_bridges.parquet"),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/bridge_endpoint_seeds.parquet"),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.bridges.exists():
        log.warning("%s missing; emitting empty bridge-endpoint seed set", args.bridges)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        _empty().write_parquet(args.out)
        return 0

    bridges = pl.read_parquet(args.bridges)
    log.info("loaded %d bridge rows", bridges.height)
    seeds = select(bridges)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    seeds.write_parquet(args.out)
    log.info("wrote %d unique SEC bridge-endpoint UIDs to %s", seeds.height, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
