"""Promote the committed UK CH overseas-entities parquet to /data.

The full UK Companies House Basic Company Data bulk CSV (2.8 GB
uncompressed) was stream-filtered locally to extract just the
``OE``-prefixed rows — the UK Register of Overseas Entities — and
the result (~30k rows, ~1 MB) is committed at
``data/uk_ch_overseas_entities.parquet``.

This script just copies that file to the Railway volume at
``/data/processed/uk_ch_overseas_entities.parquet`` so downstream
probes can read it from the canonical location.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

log = logging.getLogger("ingest_uk_ch_overseas_entities")

_SRC_CANDIDATES = [
    Path("/data/raw/icij/uk_ch_overseas_entities.parquet"),
    Path("/app/data/uk_ch_overseas_entities.parquet"),
    Path("data/uk_ch_overseas_entities.parquet"),
]
_DST = Path("/data/processed/uk_ch_overseas_entities.parquet")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    src = next((p for p in _SRC_CANDIDATES if p.exists()), None)
    if src is None:
        log.error("source not found in any of: %s", [str(p) for p in _SRC_CANDIDATES])
        return 1
    _DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, _DST)
    size = _DST.stat().st_size
    log.info("copied %s -> %s (%d bytes)", src, _DST, size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
