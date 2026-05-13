"""List-match OpenSanctions sanctioned/crime-tagged Persons against ICIJ
officers + intermediaries.

The full-corpus person dedupe (1.86M rows) is infrastructure-bound at the
configured blocking — pathological for Russian-patronymic / sanctions data.
This script narrows the cross-source question to the one that's actually
investigatively interesting: *do any ICIJ officers match a sanctioned or
crime-tagged OpenSanctions Person?*

Outputs:
- ``data/processed/os_sanctioned_persons.parquet`` (reference set)
- ``data/processed/icij_persons.parquet`` (target set)
- ``reports/generated/list_match_os_sanctions_vs_icij/...`` via
  ``goldenmatch match``.

Run locally first; Railway-side run is a follow-up if needed.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import CONFIGS_DIR, PROCESSED_DIR, REPORTS_DIR

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


@app.command()
def main(
    person_table: Path = typer.Option(
        PROCESSED_DIR / "person_entities.parquet", "--person-table"
    ),
    out_dir: Path = typer.Option(PROCESSED_DIR, "--out-dir"),
    reports_dir: Path = typer.Option(REPORTS_DIR, "--reports-dir"),
    run_name: str = typer.Option(
        "list_match_os_sanctions_vs_icij", "--run-name"
    ),
    config: Path = typer.Option(
        CONFIGS_DIR / "goldenmatch_person.yml", "--config"
    ),
    skip_match: bool = typer.Option(
        False,
        "--skip-match",
        help="Only build the two parquet subsets; don't shell out to goldenmatch.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = pl.read_parquet(person_table)
    log.info("loaded %d person rows", df.height)

    # Reference: OS Persons tagged with 'sanction' or 'crime'.
    # Project to the columns goldenmatch actually reads from the config —
    # the topics / datasets list columns trip goldenmatch's strict_cast.
    keep_cols = ["entity_uid", "source", "name", "normalized_name", "country"]
    topics = pl.col("topics").list.join(",")
    os_ref = df.filter(
        (pl.col("kind") == "person")
        & (topics.str.contains("sanction") | topics.str.contains("crime"))
    ).select(keep_cols)
    ref_path = out_dir / "os_sanctioned_persons.parquet"
    os_ref.write_parquet(ref_path)
    log.info("wrote %d OS sanctioned/crime persons -> %s", os_ref.height, ref_path)

    # Target: every non-OS person.
    #
    # For UK PSC specifically, restrict to *foreign-nationality* PSCs.
    # UK-national PSCs of UK companies are mostly real British people
    # running real British businesses — generic first names like
    # "Anthony" (168k records) create unsplittable blocks that OOM the
    # matcher and contribute near-zero cross-sanctions signal. The
    # interesting UK PSC slice is the foreign-national one: Russian /
    # Cypriot / Maltese / etc. beneficial owners of UK companies —
    # exactly the "sanctioned principal -> UK Ltd" pattern we want.
    icij = df.filter(pl.col("source") == "icij")
    # Narrow to the high-signal jurisdiction set for cross-sanctions
    # surfacing. Russian/Ukrainian/Belarusian PSCs of UK Ltds = classic
    # sanctioned-oligarch pattern; Cyprus/Malta = enabler jurisdictions;
    # Kazakhstan = post-Soviet wealth + several PEP cases; Pakistan/India
    # / China captured for completeness against current OS lists.
    # Excluding generic Western-EU first-name blocks (alexander/michael/
    # anthony) that swamp the matcher with no investigative payoff.
    high_signal = {
        "ru", "ua", "by", "kz", "cy", "mt", "pk", "in", "cn", "kg",
        "uz", "az", "am", "ge", "md", "ir", "sy", "ve", "tm", "tj",
    }
    uk_psc = df.filter(
        (pl.col("source") == "uk_psc")
        & pl.col("country").is_in(list(high_signal))
    )
    target = pl.concat([icij, uk_psc], how="vertical_relaxed").select(keep_cols)
    tgt_path = out_dir / "icij_persons.parquet"
    target.write_parquet(tgt_path)
    log.info(
        "wrote %d target persons (icij=%d, uk_psc-foreign=%d) -> %s",
        target.height,
        icij.height,
        uk_psc.height,
        tgt_path,
    )

    if skip_match:
        log.info("--skip-match set; stopping here")
        return

    gm = "goldenmatch"
    cmd = [
        gm,
        "match",
        str(tgt_path),
        "--against",
        str(ref_path),
        "--config",
        str(config),
        "--output-dir",
        str(reports_dir),
        "--run-name",
        run_name,
        "--output-matched",
        "--output-scores",
        "--format",
        "csv",
        "--quiet",
    ]
    log.info("$ %s", " ".join(cmd))
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        log.error("goldenmatch match exited with code %d", rc)
        sys.exit(rc)
    log.info("done -> %s/%s_*", reports_dir, run_name)


if __name__ == "__main__":
    app()
