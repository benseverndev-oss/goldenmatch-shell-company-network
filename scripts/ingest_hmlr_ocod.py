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

    # HMLR ships the CSV with a dated filename (e.g. OCOD_FULL_2026_05.csv)
    # inside the zip. If the exact --input path doesn't exist, fall back
    # to the first OCOD_FULL*.csv in the same directory.
    input_path = args.input
    if not input_path.exists():
        parent = input_path.parent
        candidates = sorted(parent.glob("OCOD_FULL*.csv"))
        if candidates:
            input_path = candidates[-1]
            log.info("--input not found; falling back to %s", input_path)
        else:
            raise SystemExit(
                f"[fatal] OCOD CSV missing: {args.input}\n"
                "Download manually from "
                "https://use-land-property-data.service.gov.uk/datasets/ocod "
                "(free but requires email signup + licence acceptance), then "
                "upload to Railway via /upload-file?slot=hmlr_ocod_zip + "
                "/unzip-file."
            )

    # Derive snapshot_date from filename if not provided. HMLR uses
    # OCOD_FULL_YYYY_MM.csv — extract YYYY-MM as a stable identifier.
    snapshot_date = args.snapshot_date
    if not snapshot_date:
        import re

        m = re.search(r"(\d{4})_(\d{2})", input_path.name)
        if m:
            snapshot_date = f"{m.group(1)}-{m.group(2)}"
            log.info("snapshot_date inferred from filename: %s", snapshot_date)

    hmlr_ocod.ingest(input_path, out=args.out, snapshot_date=snapshot_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
