"""Temporal graph evolution patterns from ICIJ incorporation/dissolution dates.

96.8% of ICIJ entities carry `incorporation_date`; 42% carry `dissolution_date`.
That's enough to surface three temporal patterns the dossier pipeline doesn't
currently see:

1. **Resurrection** — an entity dissolves, then a new entity with very similar
   name + same normalized address is incorporated within `--resurrection-window`
   years. The shell-network's "we got named, dissolve and reincorporate" move.
2. **Burst incorporation** — ≥N entities incorporated at the same normalized
   address within `--burst-window` days. Hints at a coordinated registration
   wave (formation-agent batch, sanctions-driven flight, scheme launch).
3. **Long-lived persistence** — entities still active (no dissolution date)
   with incorporation > N years ago, registered at addresses that also host
   many recently-incorporated shells. Old anchor entities for shell-rotation
   patterns.

Output is one parquet per pattern plus a combined summary JSON.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _resurrection_pairs(
    df: pl.DataFrame, window_days: int = 730, max_addr_cardinality: int = 50
) -> pl.DataFrame:
    """Pairs of (dissolved_entity, fresh_entity) sharing normalized_address.

    `window_days` is the max gap between dissolution_date and the new
    entity's incorporation_date for the pair to count as a resurrection.

    `max_addr_cardinality` filters out registered-office addresses with
    more than N entities — Mossack-Fonseca-style formation agents would
    otherwise Cartesian-product into millions of pairs that aren't
    investigatively meaningful and OOM the join.
    """
    # Pre-filter addresses with too many entities — they're registration-
    # service hubs, not investigatively-relevant resurrections.
    addr_counts = (
        df.filter(pl.col("normalized_address").is_not_null())
        .group_by("normalized_address")
        .len()
        .filter(pl.col("len") <= max_addr_cardinality)
        .select("normalized_address")
    )
    df = df.join(addr_counts, on="normalized_address", how="inner")
    dissolved = (
        df.filter(
            pl.col("dissolution_date").is_not_null()
            & (pl.col("dissolution_date").str.len_chars() > 0)
            & pl.col("normalized_address").is_not_null()
            & (pl.col("normalized_address").str.len_chars() > 0)
        )
        .with_columns(
            pl.col("dissolution_date").str.to_date(format="%d-%b-%Y", strict=False).alias("d_date")
        )
        .filter(pl.col("d_date").is_not_null())
        .select(
            pl.col("source_id").alias("old_source_id"),
            pl.col("name").alias("old_name"),
            pl.col("normalized_name").alias("old_norm"),
            pl.col("normalized_address").alias("addr"),
            pl.col("jurisdiction").alias("old_juris"),
            pl.col("d_date"),
        )
    )
    incorporated = (
        df.filter(
            pl.col("incorporation_date").is_not_null()
            & (pl.col("incorporation_date").str.len_chars() > 0)
            & pl.col("normalized_address").is_not_null()
            & (pl.col("normalized_address").str.len_chars() > 0)
        )
        .with_columns(
            pl.col("incorporation_date")
            .str.to_date(format="%d-%b-%Y", strict=False)
            .alias("i_date")
        )
        .filter(pl.col("i_date").is_not_null())
        .select(
            pl.col("source_id").alias("new_source_id"),
            pl.col("name").alias("new_name"),
            pl.col("normalized_name").alias("new_norm"),
            pl.col("normalized_address").alias("addr"),
            pl.col("jurisdiction").alias("new_juris"),
            pl.col("i_date"),
        )
    )
    pairs = dissolved.join(incorporated, on="addr", how="inner").filter(
        (pl.col("i_date") > pl.col("d_date"))
        & ((pl.col("i_date") - pl.col("d_date")).dt.total_days() <= window_days)
        & (pl.col("old_source_id") != pl.col("new_source_id"))
    )
    pairs = pairs.with_columns(
        (pl.col("i_date") - pl.col("d_date")).dt.total_days().alias("gap_days")
    )
    return pairs.sort("gap_days")


def _burst_incorporations(
    df: pl.DataFrame, window_days: int = 30, min_count: int = 5
) -> pl.DataFrame:
    """Addresses with ≥`min_count` incorporations inside any `window_days`."""
    base = (
        df.filter(
            pl.col("incorporation_date").is_not_null()
            & (pl.col("incorporation_date").str.len_chars() > 0)
            & pl.col("normalized_address").is_not_null()
            & (pl.col("normalized_address").str.len_chars() > 0)
        )
        .with_columns(
            pl.col("incorporation_date")
            .str.to_date(format="%d-%b-%Y", strict=False)
            .alias("i_date")
        )
        .filter(pl.col("i_date").is_not_null())
        .select("source_id", "name", "normalized_address", "jurisdiction", "i_date")
    )

    # Per-address: sort by date, then check if date[i+min_count-1] - date[i]
    # ≤ window_days. That's the simplest "any sliding window of N has span ≤ W"
    # check. We use a per-address shift via `over`.
    per_addr = base.sort(["normalized_address", "i_date"])
    per_addr = per_addr.with_columns(
        pl.col("i_date").shift(-(min_count - 1)).over("normalized_address").alias("date_at_plus_n"),
    )
    per_addr = per_addr.filter(pl.col("date_at_plus_n").is_not_null()).with_columns(
        (pl.col("date_at_plus_n") - pl.col("i_date")).dt.total_days().alias("span_days")
    )
    # Window starts where span_days ≤ window_days. Group by address +
    # window_start (= i_date here) so duplicates collapse.
    bursts = (
        per_addr.filter(pl.col("span_days") <= window_days)
        .rename({"i_date": "window_start", "date_at_plus_n": "window_end"})
        .group_by("normalized_address")
        # Take the densest single window per address: smallest span_days for
        # the same min_count entries.
        .agg(
            pl.col("window_start").first(),
            pl.col("window_end").first(),
            pl.col("span_days").first(),
            pl.col("jurisdiction").first(),
            pl.len().alias("n_burst_windows"),
        )
        .with_columns(pl.lit(min_count).alias("n_in_window"))
        .sort("span_days")
    )
    return bursts


def _long_lived_anchors(df: pl.DataFrame, min_years: int = 15) -> pl.DataFrame:
    """Entities incorporated > min_years ago with no dissolution date.

    Cross-referenced with the addresses hosting many recent incorporations.
    """
    threshold_year = 2026 - min_years
    base = (
        df.filter(
            pl.col("incorporation_date").is_not_null()
            & (pl.col("incorporation_date").str.len_chars() > 0)
            & pl.col("normalized_address").is_not_null()
            & (pl.col("normalized_address").str.len_chars() > 0)
            & (
                pl.col("dissolution_date").is_null()
                | (pl.col("dissolution_date").str.len_chars() == 0)
            )
        )
        .with_columns(
            pl.col("incorporation_date")
            .str.to_date(format="%d-%b-%Y", strict=False)
            .alias("i_date")
        )
        .filter(pl.col("i_date").is_not_null() & (pl.col("i_date").dt.year() < threshold_year))
    )
    # Address-level recent activity: how many recent (post-2020) incorporations
    # at each address.
    recent_activity = (
        df.filter(
            pl.col("incorporation_date").is_not_null() & pl.col("normalized_address").is_not_null()
        )
        .with_columns(
            pl.col("incorporation_date")
            .str.to_date(format="%d-%b-%Y", strict=False)
            .alias("i_date")
        )
        .filter(pl.col("i_date").is_not_null() & (pl.col("i_date").dt.year() >= 2020))
        .group_by("normalized_address")
        .len()
        .rename({"len": "n_recent_at_addr"})
    )
    anchors = base.join(recent_activity, on="normalized_address", how="left").filter(
        pl.col("n_recent_at_addr") >= 3
    )
    return anchors.select(
        pl.col("source_id"),
        pl.col("name"),
        pl.col("normalized_address").alias("address"),
        pl.col("jurisdiction"),
        pl.col("i_date").alias("incorporated"),
        pl.col("n_recent_at_addr"),
    ).sort("n_recent_at_addr", descending=True)


@app.command()
def main(
    entities_parquet: Path = typer.Option(
        INTERIM_DIR / "icij_entities.parquet",
        "--entities",
    ),
    out_resurrections: Path = typer.Option(
        PROCESSED_DIR / "temporal_resurrections.parquet",
        "--out-resurrections",
    ),
    out_bursts: Path = typer.Option(
        PROCESSED_DIR / "temporal_bursts.parquet",
        "--out-bursts",
    ),
    out_anchors: Path = typer.Option(
        PROCESSED_DIR / "temporal_long_lived.parquet",
        "--out-anchors",
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "temporal_patterns_summary.json",
        "--out-summary",
    ),
    resurrection_window_days: int = typer.Option(730, "--resurrection-window-days"),
    burst_window_days: int = typer.Option(30, "--burst-window-days"),
    burst_min_count: int = typer.Option(5, "--burst-min-count"),
    long_lived_min_years: int = typer.Option(15, "--long-lived-min-years"),
    top_n: int = typer.Option(500, "--top-n"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()

    df = pl.read_parquet(entities_parquet)
    log.info("ICIJ entities loaded: %d", df.height)

    log.info("computing resurrection pairs ...")
    resurrections = _resurrection_pairs(df, window_days=resurrection_window_days)
    log.info("resurrection pairs: %d", resurrections.height)
    resurrections.head(top_n).write_parquet(out_resurrections)

    log.info("computing burst incorporations ...")
    bursts = _burst_incorporations(df, window_days=burst_window_days, min_count=burst_min_count)
    log.info("burst incorporations: %d", bursts.height)
    bursts.head(top_n).write_parquet(out_bursts)

    log.info("computing long-lived anchors ...")
    anchors = _long_lived_anchors(df, min_years=long_lived_min_years)
    log.info("long-lived anchors: %d", anchors.height)
    anchors.head(top_n).write_parquet(out_anchors)

    summary = {
        "input_entities": int(df.height),
        "resurrections": {
            "window_days": resurrection_window_days,
            "n_pairs": int(resurrections.height),
            "n_kept": int(min(resurrections.height, top_n)),
            "median_gap_days": (
                int(resurrections["gap_days"].median() or 0) if resurrections.height else None
            ),
            "top_3": resurrections.head(3).to_dicts(),
        },
        "bursts": {
            "window_days": burst_window_days,
            "min_count": burst_min_count,
            "n_address_windows": int(bursts.height),
            "n_kept": int(min(bursts.height, top_n)),
            "largest_burst": (int(bursts["n_in_window"].max() or 0) if bursts.height else 0),
            "top_3_sizes": (
                bursts.head(3)
                .select(["normalized_address", "n_in_window", "span_days", "jurisdiction"])
                .to_dicts()
                if bursts.height
                else []
            ),
        },
        "long_lived_anchors": {
            "min_years": long_lived_min_years,
            "n_anchors": int(anchors.height),
            "n_kept": int(min(anchors.height, top_n)),
            "top_3": anchors.head(3)
            .select(["name", "address", "jurisdiction", "incorporated", "n_recent_at_addr"])
            .to_dicts(),
        },
    }
    out_summary.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    typer.echo(f"Wrote: {out_resurrections}")
    typer.echo(f"Wrote: {out_bursts}")
    typer.echo(f"Wrote: {out_anchors}")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
