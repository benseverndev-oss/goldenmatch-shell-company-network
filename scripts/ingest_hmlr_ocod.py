"""Ingest HM Land Registry OCOD (Overseas Companies Ownership Data)
CSV into a parquet.

Usage:
    uv run python scripts/ingest_hmlr_ocod.py \\
        --input /data/raw/hmlr/OCOD_FULL_2025_05.csv \\
        --snapshot-date 2025-05 \\
        --out /data/processed/hmlr_ocod.parquet
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1] / "src"))

from shellnet.sources import hmlr_ocod  # noqa: E402

log = logging.getLogger("ingest_hmlr_ocod")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input",
        type=Path,
        default=Path("/data/raw/hmlr/OCOD_FULL.csv"),
        help="OCOD CSV from HM Land Registry use-land-property-data service.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/hmlr_ocod.parquet"),
    )
    p.add_argument(
        "--snapshot-date",
        type=str,
        default="",
        help="The OCOD release identifier (e.g. '2025-05'). Stored alongside each row.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.input.exists():
        raise SystemExit(
            f"[fatal] OCOD CSV missing: {args.input}\n"
            "Download manually from "
            "https://use-land-property-data.service.gov.uk/datasets/ocod (free "
            "but requires email signup + licence acceptance), then upload "
            "to Railway via /upload-zip or similar."
        )

    hmlr_ocod.ingest(args.input, out=args.out, snapshot_date=args.snapshot_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
