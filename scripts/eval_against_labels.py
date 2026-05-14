"""Score a GoldenMatch run against the labels CSV.

Reads:
  * the GoldenMatch cluster CSV (default: reports/generated/company_clusters.csv)
  * the labels CSV (default: reports/generated/labels.csv)

Emits precision / recall / F1 broken out by label source (humans vs.
derived). The split matters: precision against derived labels is a sanity
check; precision against human labels is the number you'd actually report.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from shellnet.matching.labels import evaluate, load_labels
from shellnet.matching.runs import cluster_pairs, run_paths
from shellnet.paths import REPORTS_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    run_name: str = typer.Option("company", "--run-name", "-r"),
    output_dir: Path = typer.Option(REPORTS_DIR, "--output-dir"),
    labels_path: Path = typer.Option(REPORTS_DIR / "labels.csv", "--labels"),
    out_path: Path = typer.Option(REPORTS_DIR / "evaluation.json", "--out"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    paths = run_paths(output_dir, run_name)
    if not paths.clusters_csv.exists():
        typer.echo(f"GoldenMatch cluster file not found: {paths.clusters_csv}")
        raise typer.Exit(code=1)
    if not labels_path.exists():
        typer.echo(f"Labels file not found: {labels_path}")
        raise typer.Exit(code=1)

    # Best-effort: if the cluster CSV uses GoldenMatch's opaque row ids we
    # need the source parquet alongside to recover entity_uid.
    from shellnet.paths import PROCESSED_DIR

    source_table = PROCESSED_DIR / f"{run_name}_entities.parquet"
    predicted = [
        (a, b)
        for a, b, _cid in cluster_pairs(
            paths,
            source_table=source_table if source_table.exists() else None,
        )
    ]
    labels = load_labels(labels_path)

    overall = evaluate(predicted, labels).as_dict()
    human = evaluate(predicted, labels, sources=("human:",)).as_dict()
    derived = evaluate(predicted, labels, sources=("derived:",)).as_dict()

    report = {
        "run_name": run_name,
        "labels_path": str(labels_path),
        "predicted_pairs": len(predicted),
        "label_rows": labels.height,
        "overall": overall,
        "human_only": human,
        "derived_only": derived,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    typer.echo(json.dumps(report, indent=2))
    typer.echo(f"\nWrote: {out_path}")


if __name__ == "__main__":
    app()
