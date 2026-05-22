"""Ingest NYC ACRIS (real-property records) into parquet on Railway.

Downloads three NYC Open Data CSVs (Master, Parties, Legals), projects
each to the columns we care about, writes one parquet per source to
``/data/processed/`` for the probe layer.

NYC Open Data serves these as direct CSV downloads. We stream them
to disk (a few GB each), then read with polars. Total Railway-side
runtime: ~10-20 minutes depending on egress speed.

Allowlist entry in ``src/shellnet/job_server.py:_ALLOWED_SCRIPTS``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import httpx

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from shellnet.sources.nyc_acris import (  # noqa: E402
    ACRIS_LEGALS_URL,
    ACRIS_MASTER_URL,
    ACRIS_PARTIES_URL,
    project_legals,
    project_master,
    project_parties,
)

log = logging.getLogger("ingest_nyc_acris")


def _download(url: str, dest: Path, ua: str) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        log.info("  cache hit: %s (%d bytes)", dest, dest.stat().st_size)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s -> %s", url, dest)
    with httpx.stream(
        "GET", url, follow_redirects=True, headers={"User-Agent": ua}, timeout=None
    ) as r:
        r.raise_for_status()
        total = 0
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
                total += len(chunk)
        log.info("  wrote %d bytes", total)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-dir", type=Path, default=Path("/data/raw/nyc_acris"))
    p.add_argument("--processed-dir", type=Path, default=Path("/data/processed"))
    p.add_argument(
        "--user-agent",
        default="GoldenMatch case study bsevern@mjhlifesciences.com",
    )
    p.add_argument("--skip-download", action="store_true", help="Use cached CSVs only.")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.processed_dir.mkdir(parents=True, exist_ok=True)

    master_csv = args.raw_dir / "acris_master.csv"
    parties_csv = args.raw_dir / "acris_parties.csv"
    legals_csv = args.raw_dir / "acris_legals.csv"

    if not args.skip_download:
        _download(ACRIS_MASTER_URL, master_csv, args.user_agent)
        _download(ACRIS_PARTIES_URL, parties_csv, args.user_agent)
        _download(ACRIS_LEGALS_URL, legals_csv, args.user_agent)

    n_master = project_master(master_csv, args.processed_dir / "nyc_acris_master.parquet")
    n_parties = project_parties(parties_csv, args.processed_dir / "nyc_acris_parties.parquet")
    n_legals = project_legals(legals_csv, args.processed_dir / "nyc_acris_legals.parquet")

    log.info("ingest complete: master=%d parties=%d legals=%d", n_master, n_parties, n_legals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
