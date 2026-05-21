"""Pull every ICIJ record naming 'Sajid Bashir' plus all entities + addresses they touch.

Investigative drill-down. The disqualified UK director Sajid Bashir
(DOB 1993-01-26, Huddersfield) name-matches at least one Panama
Papers officer. We need every officer record by that name + all
their connected entities + addresses to see if the Panama Papers
Sajid Bashir is the same UK-disqualified Sajid Bashir.

Outputs ``/data/processed/probes/sajid_bashir_icij.json``."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_sajid_bashir_icij")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out", type=Path, default=Path("/data/processed/probes/sajid_bashir_icij.json")
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    off = (
        pl.scan_parquet(Path("/data/interim/icij_officers.parquet"))
        .filter(pl.col("normalized_name") == "sajid bashir")
        .collect()
    )
    log.info("officer records: %d", off.height)

    uids = ["icij:" + s for s in off["source_id"].to_list()]
    edges = (
        pl.scan_parquet(Path("/data/interim/icij_edges.parquet"))
        .filter(pl.col("src_node").is_in(uids) | pl.col("dst_node").is_in(uids))
        .collect()
    )
    log.info("edges: %d", edges.height)

    connected = sorted(
        {n.replace("icij:", "") for n in edges["src_node"].to_list() + edges["dst_node"].to_list()}
    )
    ent = (
        pl.scan_parquet(Path("/data/interim/icij_entities.parquet"))
        .filter(pl.col("source_id").is_in(connected))
        .collect()
    )
    log.info("connected entities: %d", ent.height)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "officers": off.to_dicts(),
                "edges": edges.to_dicts(),
                "entities": ent.to_dicts(),
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
