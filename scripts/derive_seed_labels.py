"""Write auto-derived seed labels from the unified company table.

These are NOT a substitute for human labels. They're the cheap, very
high-confidence labels (same LEI → match; same name + different LEI →
no_match) that we can extract without judgement. They seed the labels
table so the eval script has *something* to score against before a
human starts labelling the marginal band.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from shellnet.matching.labels import derive_seed_labels, load_labels, save_labels
from shellnet.paths import PROCESSED_DIR, REPORTS_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    company_table: Path = typer.Option(PROCESSED_DIR / "company_entities.parquet"),
    out_path: Path = typer.Option(REPORTS_DIR / "labels.csv"),
    merge: bool = typer.Option(
        True, "--merge/--overwrite", help="Merge into existing labels (keep human labels)."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    if not company_table.exists():
        typer.echo(f"Company table {company_table} not found.")
        raise typer.Exit(code=1)

    derived = derive_seed_labels(company_table)
    typer.echo(f"Derived {derived.height} seed labels.")
    if merge and out_path.exists():
        import polars as pl

        existing = load_labels(out_path)
        # Human labels win on conflict — drop any derived row whose pair is
        # already labelled by a human, then concat the rest.
        human_pairs = set()
        for r in existing.filter(pl.col("source").str.starts_with("human:")).iter_rows(named=True):
            human_pairs.add((r["left_uid"], r["right_uid"]))
        derived = derived.filter(
            ~pl.struct(["left_uid", "right_uid"]).map_elements(
                lambda row: (row["left_uid"], row["right_uid"]) in human_pairs,
                return_dtype=pl.Boolean,
            )
        )
        combined = pl.concat([existing, derived], how="vertical_relaxed")
        save_labels(combined, out_path)
        typer.echo(f"Merged into {out_path}; total rows now {load_labels(out_path).height}.")
    else:
        save_labels(derived, out_path)
        typer.echo(f"Wrote {derived.height} labels to {out_path}")


if __name__ == "__main__":
    app()
