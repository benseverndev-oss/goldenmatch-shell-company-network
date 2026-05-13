"""Aggregate the address table to surface shared registered-agent addresses.

Shared addresses (one address hosting many otherwise unrelated entities)
are a classic shell-company tell. This is descriptive, not accusatory —
many large law firms and registered-agent services legitimately host
thousands of entities.

Outputs both a JSON-friendly Polars parquet and a Markdown summary.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.matching.address_features import shared_address_report
from shellnet.paths import PROCESSED_DIR, REPORTS_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)


def _markdown(df: pl.DataFrame, top_n: int) -> str:
    lines = [
        f"# Shared addresses (top {top_n})",
        "",
        "Each row is one normalized address line that hosts multiple entities.",
        "Sorted by hosted-entity count, descending. This is structural —",
        "**not** evidence of wrongdoing on its own.",
        "",
        "| # | Country | Hosted | Sources | Sample address |",
        "| ---: | --- | ---: | --- | --- |",
    ]
    for i, row in enumerate(df.iter_rows(named=True), start=1):
        country = row.get("country") or "?"
        sources = ", ".join(sorted(row.get("contributing_sources") or []))
        sample = (row.get("sample_raw_text") or "").replace("|", "\\|")
        lines.append(f"| {i} | {country} | {row['hosted_count']} | {sources} | {sample[:120]} |")
    return "\n".join(lines) + "\n"


@app.command()
def main(
    address_path: Path = typer.Option(PROCESSED_DIR / "address_entities.parquet"),
    top_n: int = typer.Option(20, "--top-n", "-n"),
    min_count: int = typer.Option(3, "--min-count"),
    out_parquet: Path = typer.Option(REPORTS_DIR / "shared_addresses.parquet"),
    out_md: Path = typer.Option(REPORTS_DIR / "shared_addresses.md"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    if not address_path.exists():
        typer.echo(
            f"Address table {address_path} not found. Run scripts/build_address_table.py first."
        )
        raise typer.Exit(code=1)
    df = shared_address_report(address_path, top_n=top_n, min_count=min_count)
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out_parquet)
    out_md.write_text(_markdown(df, top_n), encoding="utf-8")
    typer.echo(f"Wrote {df.height} rows to {out_parquet} and {out_md}")


if __name__ == "__main__":
    app()
