"""Look up arbitrary ICIJ address-node UIDs.

Sajid Bashir's officer record has a registered_address edge to
icij:14090036. That address node's full content (street + city +
country) lives in the ICIJ entities table (yes, addresses are
modeled as entities in the ICIJ schema). Pull it.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_icij_address_lookup")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--source-id", action="append", required=True, help="Bare source_id. Repeatable."
    )
    p.add_argument("--slug", required=True)
    p.add_argument("--out-dir", type=Path, default=Path("/data/processed/probes"))
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # ICIJ entities table covers companies but NOT plain addresses.
    # Addresses live in a separate ICIJ table. Try both ways.
    ent = (
        pl.scan_parquet(Path("/data/interim/icij_entities.parquet"))
        .filter(pl.col("source_id").is_in(args.source_id))
        .collect()
    )
    log.info("entities match: %d", ent.height)

    # Officers table (in case it's misclassified)
    off = (
        pl.scan_parquet(Path("/data/interim/icij_officers.parquet"))
        .filter(pl.col("source_id").is_in(args.source_id))
        .collect()
    )
    log.info("officers match: %d", off.height)

    # Edges where this UID is mentioned
    uids = ["icij:" + s for s in args.source_id]
    edges = (
        pl.scan_parquet(Path("/data/interim/icij_edges.parquet"))
        .filter(pl.col("src_node").is_in(uids) | pl.col("dst_node").is_in(uids))
        .collect()
    )
    log.info("edges: %d", edges.height)

    result = {
        "asked_for": args.source_id,
        "entities": ent.to_dicts(),
        "officers": off.to_dicts(),
        "edges": edges.to_dicts(),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"{args.slug}.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log.info("wrote %s", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
