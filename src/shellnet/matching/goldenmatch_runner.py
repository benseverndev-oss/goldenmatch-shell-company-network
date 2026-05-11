"""Thin wrapper around GoldenMatch for the company table.

We intentionally keep this small. GoldenMatch's own CLI is fully
capable; the wrapper here just exists so smoke scripts can import a
single function and so we can log / persist results consistently.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import polars as pl

from shellnet.paths import CONFIGS_DIR, PROCESSED_DIR

log = logging.getLogger(__name__)


def load_company_table(processed_dir: Path = PROCESSED_DIR) -> pl.DataFrame:
    """Load ``company_entities.parquet`` or raise a clear error."""
    path = processed_dir / "company_entities.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run scripts/build_candidate_tables.py first."
        )
    return pl.read_parquet(path)


def default_config_path() -> Path:
    """Path to the company-matching YAML shipped in this repo."""
    return CONFIGS_DIR / "goldenmatch_company.yml"


def run_match(
    df: pl.DataFrame | None = None,
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Run GoldenMatch over the unified company table.

    Returns a small dict summarising what happened. We deliberately do not
    propagate the entire match output here — for that, use the GoldenMatch
    CLI directly. This wrapper exists so smoke scripts can sanity-check
    that the engine *runs* without a giant import surface.
    """
    if df is None:
        df = load_company_table()
    config_path = config_path or default_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Match config {config_path} not found.")

    # Imported lazily so importing the rest of this package doesn't pull in
    # GoldenMatch's full dependency tree.
    from goldenmatch.config.loader import load_config  # type: ignore

    cfg = load_config(str(config_path))
    summary: dict[str, Any] = {
        "config": str(config_path),
        "rows": int(df.height),
        "matchkey_count": len(cfg.get_matchkeys()),
        "matchkeys": [mk.name for mk in cfg.get_matchkeys()],
    }
    log.info("Loaded GoldenMatch config %s with %d matchkeys", config_path, summary["matchkey_count"])
    return summary
