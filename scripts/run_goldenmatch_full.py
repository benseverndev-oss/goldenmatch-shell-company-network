"""Invoke the GoldenMatch CLI for real and persist its output.

    uv run python scripts/run_goldenmatch_full.py --what company

We shell out to ``goldenmatch dedupe`` (instead of importing GoldenMatch's
internal API) because the CLI is the documented, stable surface and
because shell-out keeps our wrapper honest about which env vars and
configs it relies on.

Outputs land in ``reports/generated/``:

  * ``<run_name>_clusters.csv``  — one row per record with a cluster_id
  * ``<run_name>_lineage.json``  — per-pair scores
  * ``<run_name>_summary.json``  — small summary we add on top

Use ``--what company`` or ``--what address`` or ``--what person`` to pick
the source table + config combination.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import typer

from shellnet.matching.runs import cluster_pairs, load_clusters, run_paths
from shellnet.paths import CONFIGS_DIR, PROCESSED_DIR, REPORTS_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Target:
    config: Path
    table: Path
    run_name: str


def _resolve(what: str) -> _Target:
    if what == "company":
        return _Target(
            config=CONFIGS_DIR / "goldenmatch_company.yml",
            table=PROCESSED_DIR / "company_entities.parquet",
            run_name="company",
        )
    if what == "address":
        return _Target(
            config=CONFIGS_DIR / "goldenmatch_address.yml",
            table=PROCESSED_DIR / "address_entities.parquet",
            run_name="address",
        )
    if what == "person":
        return _Target(
            config=CONFIGS_DIR / "goldenmatch_person.yml",
            table=PROCESSED_DIR / "person_entities.parquet",
            run_name="person",
        )
    raise typer.BadParameter(f"--what must be company|address|person, got {what!r}")


@app.command()
def main(
    what: str = typer.Option(
        "company",
        "--what",
        "-w",
        help="Which unified table to dedupe: `company`, `address`, or `person`.",
    ),
    output_dir: Path = typer.Option(
        REPORTS_DIR, "--output-dir", help="Where GoldenMatch writes cluster + lineage files."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the command we would invoke and exit."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    target = _resolve(what)

    if not target.config.exists():
        typer.echo(f"Config not found: {target.config}")
        raise typer.Exit(code=1)
    if not target.table.exists():
        typer.echo(
            f"Source table {target.table} not found. "
            "Run the matching build script for this target first."
        )
        raise typer.Exit(code=1)

    gm = shutil.which("goldenmatch") or "goldenmatch"
    cmd = [
        gm,
        "dedupe",
        str(target.table),
        "--config",
        str(target.config),
        "--output-dir",
        str(output_dir),
        "--run-name",
        target.run_name,
        "--output-clusters",
        "--format",
        "csv",
        "--no-tui",
    ]
    typer.echo("$ " + " ".join(cmd))
    if dry_run:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        typer.echo(f"goldenmatch dedupe exited with code {result.returncode}")
        raise typer.Exit(code=result.returncode)

    paths = run_paths(output_dir, target.run_name)
    summary = {
        "what": what,
        "config": str(target.config),
        "table": str(target.table),
        "clusters_csv": str(paths.clusters_csv),
        "lineage_json": str(paths.lineage_json),
        "exists": paths.exists(),
    }
    if paths.clusters_csv.exists():
        df = load_clusters(paths, source_table=target.table)
        summary["records"] = df.height
        summary["clusters"] = int(df["cluster_id"].n_unique())
        summary["multi_member_clusters"] = sum(
            1 for _, g in df.group_by("cluster_id") if g.height > 1
        )
        summary["same_as_pairs"] = len(cluster_pairs(paths, source_table=target.table))
    out = output_dir / f"{target.run_name}_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    typer.echo(json.dumps(summary, indent=2))
    typer.echo(f"\nWrote: {out}")


if __name__ == "__main__":
    app()
