"""Filter a DOB-enriched + coverage-scored match CSV down to the
investigative-grade survivor set.

Survivor criteria:
- target_normalized_name == ref_normalized_name (exact-name match)
- target_country != cn (drop common-Chinese-name collisions)
- dob_match in {both_present_year_match, ref_only, target_only}
  (DOB confirms identity, or is at least non-contradictory on one side)
- prior_coverage_mainstream == 0
  (no mainstream investigative outlet has already covered this name)

Emits a small CSV with one row per (target_normalized_name,
target_country) — the publication-grade candidate list.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import REPORTS_DIR

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


@app.command()
def main(
    scored_csv: Path = typer.Argument(...),
    out_csv: Path = typer.Option(REPORTS_DIR / "investigative_grade_survivors.csv", "--out"),
) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    df = pl.read_csv(scored_csv)
    log.info("input rows: %d", df.height)
    filt = df.filter(
        (pl.col("target_normalized_name") == pl.col("ref_normalized_name"))
        & (pl.col("target_country") != "cn")
        & pl.col("dob_match").is_in(["both_present_year_match", "ref_only", "target_only"])
    )
    log.info("after exact+non-cn+dob filters: %d", filt.height)
    novel = (
        filt.filter(pl.col("prior_coverage_mainstream") == 0)
        .unique(subset=["target_normalized_name", "target_country"])
        .sort(["dob_match", "prior_coverage_n"], nulls_last=True)
    )
    log.info("zero-mainstream-coverage unique survivors: %d", novel.height)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    novel.write_csv(out_csv)
    log.info("wrote %s", out_csv)
    print(f"survivors: {novel.height} unique candidates -> {out_csv}")


if __name__ == "__main__":
    app()
