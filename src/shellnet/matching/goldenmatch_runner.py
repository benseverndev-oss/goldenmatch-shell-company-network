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
        raise FileNotFoundError(f"{path} not found. Run scripts/build_candidate_tables.py first.")
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
    log.info(
        "Loaded GoldenMatch config %s with %d matchkeys", config_path, summary["matchkey_count"]
    )
    return summary


def match_names(
    target: pl.DataFrame,
    reference: pl.DataFrame,
    *,
    name_col: str = "normalized",
    fuzzy_threshold: float = 0.90,
    blocking_cols: list[str] | None = None,
) -> pl.DataFrame:
    """Match two name-bearing tables with GoldenMatch's calibrated
    fuzzy scorer.

    Phase 15a entry point. Replaces the bespoke exact-name match used by
    ``scripts/bridge_sec_icij_by_name.py`` with GoldenMatch's
    Jaro-Winkler-plus-blocking pipeline. Output preserves the input
    column set plus a ``prob`` column carrying the calibrated match
    probability.

    Args:
        target: Polars DataFrame to match (e.g. SEC filer names).
        reference: Polars DataFrame to match against (e.g. ICIJ entities).
        name_col: Column to fuzzy-match on. Must exist on both sides.
        fuzzy_threshold: Minimum similarity for the matcher to emit a row.
            0.90 corresponds to "very strong" matches under GoldenMatch's
            default scoring; 0.95+ for "near-identical".
        blocking_cols: Optional columns to block on (jurisdiction, etc.)
            to cut candidate set before fuzzy scoring. None = no blocking.

    Returns: a Polars DataFrame with target + reference columns and a
    ``prob`` score column. May be empty if no pairs cross the threshold.
    """

    from goldenmatch import match_df  # type: ignore

    if name_col not in target.columns or name_col not in reference.columns:
        raise ValueError(
            f"name_col={name_col!r} must exist on both target ({target.columns}) "
            f"and reference ({reference.columns})"
        )

    result = match_df(
        target,
        reference,
        fuzzy={name_col: fuzzy_threshold},
        blocking=blocking_cols,
    )
    matched = result.matched
    if matched is None or matched.is_empty():
        # Empty result with at least the columns the caller expects.
        empty_schema: dict[str, Any] = {c: pl.String for c in target.columns}
        empty_schema.update({f"{c}_ref": pl.String for c in reference.columns})
        empty_schema["prob"] = pl.Float64
        return pl.DataFrame(schema=empty_schema)

    # Surface the score column under a stable name. GoldenMatch's
    # version on disk emits ``__match_score__`` (the literal column
    # name in the matched frame); older versions used ``__score__`` /
    # ``score`` / ``__prob__``. Pick whatever's present.
    score_aliases = ("__match_score__", "__score__", "score", "__prob__", "prob")
    for alias in score_aliases:
        if alias in matched.columns and alias != "prob":
            matched = matched.rename({alias: "prob"})
            break
    if "prob" not in matched.columns:
        # Fall back to fuzzy_threshold as a constant — calibration is
        # then a downstream concern. Logged loudly so a future SDK
        # bump can be caught.
        log.warning(
            "GoldenMatch match_df did not surface a score column; "
            "filling prob=%.2f. Columns were: %s",
            fuzzy_threshold,
            matched.columns,
        )
        matched = matched.with_columns(pl.lit(fuzzy_threshold).alias("prob"))
    return matched
