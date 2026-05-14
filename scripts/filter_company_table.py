"""Filter the unified company table to keep only matchable rows.

The full 4.1M-row table from ICIJ + GLEIF + OpenSanctions has long-tail
placeholder names ("STICHTING", "THE TRUSTEE", "BEARER", etc.) and very
short names that produce mega-blocks during GoldenMatch dedupe (e.g.
9k+ records in the 'stichtin||nl' block, blowing past max_block_size=5000
and OOMing the run).

This script drops rows that contribute disproportionately to block
explosion without losing real-entity coverage:

  * normalized_name is null/empty
  * normalized_name has < 4 characters
  * normalized_name is in a hand-coded placeholder list
  * name starts with a numeric prefix and is < 8 chars (e.g. 'NO. 123')

Writes back to data/processed/company_entities.parquet (overwriting).
The pre-filter copy is preserved at company_entities.unfiltered.parquet.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)

PLACEHOLDER_NAMES: set[str] = {
    "bearer",
    "the bearer",
    "el portador",
    "stichting",
    "the trustee",
    "trustee",
    "the trust",
    "trust",
    "limited",
    "ltd",
    "co",
    "corp",
    "inc",
    "sa",
    "ag",
    "gmbh",
    "bv",
    "nv",
    "spa",
    "srl",
    "kg",
    "ohg",
    "the company",
    "company",
    "n/a",
    "unknown",
    "to be appointed",
    "no name",
}


@app.command()
def main(
    in_path: Path = typer.Option(PROCESSED_DIR / "company_entities.parquet", "--in", "-i"),
    out_path: Path = typer.Option(PROCESSED_DIR / "company_entities.parquet", "--out", "-o"),
    keep_unfiltered: bool = typer.Option(True, "--keep-unfiltered/--no-keep-unfiltered"),
    min_name_chars: int = typer.Option(4, "--min-name-chars"),
    drop_sources: str = typer.Option(
        "",
        "--drop-sources",
        help="Comma-separated list of source labels to drop (e.g. 'gleif').",
    ),
    keep_only_sources: str = typer.Option(
        "",
        "--keep-only-sources",
        help="If set, keep ONLY these sources (comma-separated). Mutually exclusive with --drop-sources.",
    ),
    skip_megablock_filter: bool = typer.Option(
        False,
        "--skip-megablock-filter",
        help="Skip the mega-block size filter (useful when source itself is the filter).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()

    # Prefer the pre-filter backup as input if it exists, so re-runs always
    # start from the original 4.1M rows rather than the previous filter
    # output.
    backup = in_path.with_name(in_path.stem + ".unfiltered.parquet")
    source = backup if backup.exists() else in_path
    log.info("reading %s", source)
    df = pl.read_parquet(source)
    before = df.height
    log.info("loaded %d rows", before)

    if keep_unfiltered and not backup.exists() and source == in_path:
        log.info("saving pre-filter backup -> %s", backup)
        df.write_parquet(backup)

    drop_set = {s.strip().lower() for s in drop_sources.split(",") if s.strip()}
    keep_set = {s.strip().lower() for s in keep_only_sources.split(",") if s.strip()}
    if drop_set and keep_set:
        raise typer.BadParameter("Cannot use --drop-sources and --keep-only-sources together")
    if drop_set:
        before_drop = df.height
        df = df.filter(~pl.col("source").str.to_lowercase().is_in(list(drop_set)))
        log.info(
            "dropped sources %s: %d rows -> %d rows",
            sorted(drop_set),
            before_drop,
            df.height,
        )
    if keep_set:
        before_keep = df.height
        df = df.filter(pl.col("source").str.to_lowercase().is_in(list(keep_set)))
        log.info(
            "kept only sources %s: %d rows -> %d rows",
            sorted(keep_set),
            before_keep,
            df.height,
        )

    placeholders = pl.lit(list(PLACEHOLDER_NAMES))
    name_col = pl.col("normalized_name").fill_null("").str.strip_chars()
    df = df.filter(
        (name_col.str.len_chars() >= min_name_chars)
        & (~name_col.str.to_lowercase().is_in(placeholders))
        & (~name_col.str.contains(r"^\d+$"))
    )
    after_placeholders = df.height
    log.info(
        "after placeholder filter: %d rows (dropped %d)",
        after_placeholders,
        before - after_placeholders,
    )

    if skip_megablock_filter:
        log.info("--skip-megablock-filter set; writing %s without block-size filter", out_path)
        df.write_parquet(out_path)
        return

    # Drop rows whose (substring:0:8, jurisdiction) blocking key has > 4000
    # members. These mega-blocks produce O(N^2) pair candidates and OOM the
    # dedupe — see the 'stichtin||nl' and 'the trus||au' blocks in the
    # earlier failed run.
    blk = (
        pl.col("normalized_name").fill_null("").str.slice(0, 8).str.to_lowercase()
        + pl.lit("||")
        + pl.col("jurisdiction").fill_null("")
    )
    df = df.with_columns(blk.alias("_blk"))
    block_counts = df.group_by("_blk").len().rename({"len": "_blk_size"})
    big_blocks = block_counts.filter(pl.col("_blk_size") > 4000)
    log.info(
        "%d mega-blocks (>4000 members), covering %d rows",
        big_blocks.height,
        big_blocks["_blk_size"].sum() or 0,
    )
    for row in big_blocks.iter_rows(named=True):
        log.info("  %s -> %d rows", row["_blk"], row["_blk_size"])
    df = df.join(block_counts, on="_blk", how="left")
    df = df.filter(pl.col("_blk_size") <= 4000).drop(["_blk", "_blk_size"])

    after = df.height
    dropped = before - after
    log.info("kept %d rows (dropped %d, %.1f%%)", after, dropped, 100.0 * dropped / before)

    df.write_parquet(out_path)
    log.info("wrote %s", out_path)


if __name__ == "__main__":
    app()
