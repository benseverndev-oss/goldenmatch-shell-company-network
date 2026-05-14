"""Single source of truth for filesystem layout.

Everything that reads or writes data should go through these helpers so
the project root, raw/interim/processed split, and per-source subdirectories
stay consistent across ingestion scripts, library code, and tests.
"""

from __future__ import annotations

import os
from pathlib import Path

# Project root is two parents up from this file: src/shellnet/paths.py -> src -> project root.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]


def _data_root() -> Path:
    """Allow overriding the data directory via env (useful for large mounts)."""
    override = os.environ.get("SHELLNET_DATA_DIR")
    return Path(override).resolve() if override else PROJECT_ROOT / "data"


DATA_DIR: Path = _data_root()
RAW_DIR: Path = DATA_DIR / "raw"
INTERIM_DIR: Path = DATA_DIR / "interim"
PROCESSED_DIR: Path = DATA_DIR / "processed"
SAMPLES_DIR: Path = DATA_DIR / "samples"

CONFIGS_DIR: Path = PROJECT_ROOT / "configs"
REPORTS_DIR: Path = PROJECT_ROOT / "reports" / "generated"

# Per-source raw subdirectories
ICIJ_RAW: Path = RAW_DIR / "icij"
OPENCORPORATES_RAW: Path = RAW_DIR / "opencorporates"
OPENCORPORATES_CACHE: Path = OPENCORPORATES_RAW / "cache"
GLEIF_RAW: Path = RAW_DIR / "gleif"
OPENSANCTIONS_RAW: Path = RAW_DIR / "opensanctions"


def relpath_for_report(p: Path | str) -> str:
    """Format a path for inclusion in a generated report.

    Resolves to a project-root-relative POSIX string when possible, so reports
    are reproducible across operators and OSes. Falls back to the basename if
    the path lives outside the project (e.g. ``/data/...`` on Railway).
    """
    path = Path(p).resolve()
    try:
        rel = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return path.name
    return rel.as_posix()


def ensure_dirs() -> None:
    """Create the standard directory layout if it isn't already there.

    Safe to call repeatedly; only creates what's missing.
    """
    for p in (
        RAW_DIR,
        INTERIM_DIR,
        PROCESSED_DIR,
        SAMPLES_DIR,
        REPORTS_DIR,
        ICIJ_RAW,
        OPENCORPORATES_RAW,
        OPENCORPORATES_CACHE,
        GLEIF_RAW,
        OPENSANCTIONS_RAW,
    ):
        p.mkdir(parents=True, exist_ok=True)
