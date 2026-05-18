"""Direct list-match between ICIJ officers and UK PSC directors.

Unlike ``list_match_os_sanctions_vs_icij.py``, this routes through no
sanctions pivot — it asks the cleaner question: *which ICIJ leak
officers are currently registered as directors on UK companies?*

That overlap is independent of sanctions status. It's the cross-source
join that ICIJ Offshore Leaks DB doesn't show (no UK PSC integration)
and that Companies House doesn't show (no leak-document integration).

Pattern mirrors the existing list_match script:

- Reference: ICIJ officers + intermediaries from the unified person table.
- Target: UK PSC persons filtered to **foreign-nationality** rows
  (per CLAUDE.md, generic-first-name UK-national blocks like
  "Anthony" / "Mr Muhammad" OOM goldenmatch — and they have near-zero
  investigative payoff for this question).
- Run ``goldenmatch match`` with the person config.
- Output goes to ``reports/generated/list_match_icij_vs_uk_psc_*.csv``.
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


# Foreign-nationality slice that carries actual cross-source signal.
# See list_match_os_sanctions_vs_icij.py for the rationale (Russian /
# Cypriot / Maltese / Kazakh PSCs of UK companies = classic
# leak-overlap pattern).
HIGH_SIGNAL_COUNTRIES = ("ru", "ua", "by", "cy", "kz", "vg", "ky", "bm", "mt", "ae")


@app.command()
def main(
    person_table: Path = typer.Option(
        PROCESSED_DIR / "person_entities.parquet",
        "--person-table",
    ),
    out_dir: Path = typer.Option(
        PROCESSED_DIR,
        "--out-dir",
        help="Where to write the ICIJ-ref and UK_PSC-target parquet slices.",
    ),
    reports_dir: Path = typer.Option(REPORTS_DIR, "--reports-dir"),
    run_name: str = typer.Option(
        "list_match_icij_vs_uk_psc",
        "--run-name",
    ),
    config: Path = typer.Option(
        CONFIGS_DIR / "goldenmatch_person.yml",
        "--config",
    ),
    skip_match: bool = typer.Option(False, "--skip-match"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    keep_cols = ["entity_uid", "source", "name", "normalized_name", "country"]
    df = pl.read_parquet(person_table)
    log.info("loaded %d person rows", df.height)

    icij_ref = df.filter(pl.col("source") == "icij").select(keep_cols)
    ref_path = out_dir / "icij_persons_for_psc_match.parquet"
    icij_ref.write_parquet(ref_path)
    log.info("wrote %d ICIJ ref persons -> %s", icij_ref.height, ref_path)

    psc_target = df.filter(
        (pl.col("source") == "uk_psc") & pl.col("country").is_in(list(HIGH_SIGNAL_COUNTRIES))
    ).select(keep_cols)
    tgt_path = out_dir / "uk_psc_foreign_for_icij_match.parquet"
    psc_target.write_parquet(tgt_path)
    log.info(
        "wrote %d UK PSC foreign-national targets (jurisdictions=%s) -> %s",
        psc_target.height,
        HIGH_SIGNAL_COUNTRIES,
        tgt_path,
    )

    if skip_match:
        log.info("--skip-match set; stopping here")
        return

    cmd = [
        "goldenmatch",
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
