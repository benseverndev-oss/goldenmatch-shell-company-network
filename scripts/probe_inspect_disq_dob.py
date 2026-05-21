"""One-shot diagnostic: dump 10 sample DOBs from the disqualified
register + full record for Sajid Bashir + Santokh Singh."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("inspect_disq_dob")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--disqualified",
        type=Path,
        default=Path("/data/interim/uk_disqualified_directors.parquet"),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/disq_dob_sample.json"),
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    d = pl.read_parquet(args.disqualified)
    log.info("columns: %s", d.columns)

    # Sample DOBs (raw)
    sample_dobs = (
        d.filter(pl.col("date_of_birth").is_not_null())
        .select("date_of_birth")
        .head(15)
        .to_series()
        .to_list()
    )

    # Pull the two candidates' full records
    candidates = []
    for needle in ("sajid bashir", "santokh singh"):
        rows = d.filter(pl.col("normalized_person_name").str.contains(needle))
        for r in rows.iter_rows(named=True):
            candidates.append(r)

    result = {
        "n_rows": int(d.height),
        "schema": d.columns,
        "sample_dobs": sample_dobs,
        "candidates": candidates,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
