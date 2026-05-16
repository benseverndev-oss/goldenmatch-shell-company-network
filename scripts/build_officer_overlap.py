"""Find officer names appearing in 2+ source datasets.

The investigative move: if "Pavel Maslovsky" appears as an ICIJ leak
officer AND as a UK PSC company director AND as an OS-sanctioned
person, that's the same person sitting in three datasets. The
overlap-by-normalized-name is the cheap first-pass version of
"who's in N sources?" — much faster than running goldenmatch dedupe
across the full unified person table.

Defensive against common-name explosions:

- Group by ``(source, normalized_name)`` first; the per-source
  cardinality is bounded.
- Drop names where any single source has > ``--drop-above`` rows
  (default 50). "Anthony" / "Mr Muhammad" buckets in UK PSC blow
  this up to 100k+; they carry near-zero investigative signal.
- Drop normalized names with < ``--min-tokens`` tokens (default 2).
  Single-token surnames are too ambiguous to anchor a join.

Output: ``processed/officer_overlap.parquet`` keyed by
``normalized_name`` with one column per source carrying the entity
count, ``n_sources``, and ``total_entities``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


@app.command()
def main(
    person_table: Path = typer.Option(
        PROCESSED_DIR / "person_entities.parquet",
        "--person-table",
    ),
    out: Path = typer.Option(
        PROCESSED_DIR / "officer_overlap.parquet",
        "--out",
    ),
    min_tokens: int = typer.Option(
        2,
        "--min-tokens",
        help="Drop names with fewer than N whitespace-separated tokens.",
    ),
    drop_above: int = typer.Option(
        50,
        "--drop-above",
        help="Drop names where any source has > N rows (common-name buckets).",
    ),
    min_sources: int = typer.Option(
        2,
        "--min-sources",
        help="Require name to appear in at least this many distinct sources.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out.parent.mkdir(parents=True, exist_ok=True)

    log.info("scanning %s ...", person_table)
    base = (
        pl.scan_parquet(person_table)
        .filter(pl.col("normalized_name").is_not_null())
        .filter(pl.col("normalized_name").str.len_chars() > 0)
    )
    # Group by (source, name) first → small in memory regardless of corpus size.
    per_source = (
        base.group_by(["source", "normalized_name"])
        .agg(pl.len().alias("n_entities"))
        .collect()
    )
    log.info("per-source-name pairs: %d", per_source.height)

    # Pivot wide so each name carries one count per source.
    wide = per_source.pivot(values="n_entities", index="normalized_name", on="source").fill_null(0)
    source_cols = [c for c in wide.columns if c != "normalized_name"]
    log.info("pivot wide: %d names across %d sources (%s)", wide.height, len(source_cols), source_cols)

    # n_sources = how many source columns are > 0.
    n_sources = pl.sum_horizontal(
        [(pl.col(c) > 0).cast(pl.Int32) for c in source_cols]
    ).alias("n_sources")
    total = pl.sum_horizontal([pl.col(c) for c in source_cols]).alias("total_entities")
    max_per_source = (
        pl.max_horizontal([pl.col(c) for c in source_cols]).alias("max_per_source")
    )
    n_tokens = (
        pl.col("normalized_name").str.split(" ").list.len().alias("n_tokens")
    )

    enriched = wide.with_columns(n_sources, total, max_per_source, n_tokens)

    filtered = enriched.filter(
        (pl.col("n_sources") >= min_sources)
        & (pl.col("max_per_source") <= drop_above)
        & (pl.col("n_tokens") >= min_tokens)
    ).sort(
        by=["n_sources", "total_entities"],
        descending=[True, True],
    )
    log.info(
        "after filter (n_sources >= %d, max_per_source <= %d, n_tokens >= %d): %d names",
        min_sources,
        drop_above,
        min_tokens,
        filtered.height,
    )

    filtered.write_parquet(out)
    typer.echo(f"Wrote: {out}")
    typer.echo(f"  {filtered.height} multi-source officer names")
    if filtered.height:
        typer.echo("  top 10:")
        for r in filtered.head(10).to_dicts():
            typer.echo(
                f"    {r['normalized_name']!r}: n_sources={r['n_sources']}, total={r['total_entities']}"
            )


if __name__ == "__main__":
    app()
