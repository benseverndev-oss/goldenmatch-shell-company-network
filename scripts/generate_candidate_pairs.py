"""Emit a CSV of marginal-band candidate pairs from the company table.

We block on the normalized-name prefix + jurisdiction (the same loose
block used in the conservative GoldenMatch config) and emit every
within-block pair that isn't trivially same-LEI or same-(company_number,
jurisdiction). A human can then open the CSV and add a label.

Output columns: ``left_uid, right_uid, label, source, reason, left_name,
right_name, left_jurisdiction, right_jurisdiction``.

The labelling columns (``label``, ``source``, ``reason``) are left blank
so a human can fill them. ``scripts/derive_seed_labels.py`` does the
auto-derivation pass.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import PROCESSED_DIR, REPORTS_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)


def _block_key(name: str | None, juris: str | None, prefix_len: int) -> str:
    return f"{(juris or '').lower()}|{(name or '')[:prefix_len]}"


@app.command()
def main(
    company_table: Path = typer.Option(PROCESSED_DIR / "company_entities.parquet"),
    out_path: Path = typer.Option(REPORTS_DIR / "candidate_pairs.csv"),
    prefix_len: int = typer.Option(8, "--prefix-len", help="Name-prefix length for blocking."),
    max_pairs: int = typer.Option(500, "--max-pairs", "-n"),
    max_block_size: int = typer.Option(
        40, "--max-block-size", help="Skip blocks bigger than this (cartesian explosion)."
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
    df = pl.read_parquet(company_table)
    if df.height < 2:
        typer.echo("Not enough rows to form pairs.")
        raise typer.Exit(code=0)

    df = df.with_columns(
        pl.struct(["normalized_name", "jurisdiction"])
        .map_elements(
            lambda row: _block_key(row["normalized_name"], row["jurisdiction"], prefix_len),
            return_dtype=pl.Utf8,
        )
        .alias("_block")
    )

    rows: list[dict[str, str | None]] = []
    for _, group in df.group_by("_block"):
        if group.height < 2 or group.height > max_block_size:
            continue
        records = group.to_dicts()
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                a, b = records[i], records[j]
                # Skip pairs we'd auto-label anyway.
                if a.get("lei") and a.get("lei") == b.get("lei"):
                    continue
                if (
                    a.get("company_number")
                    and a.get("company_number") == b.get("company_number")
                    and a.get("jurisdiction") == b.get("jurisdiction")
                ):
                    continue
                left, right = sorted((a["entity_uid"], b["entity_uid"]))
                rows.append(
                    {
                        "left_uid": left,
                        "right_uid": right,
                        "label": "",
                        "source": "",
                        "reason": "",
                        "left_name": a["name"] if left == a["entity_uid"] else b["name"],
                        "right_name": b["name"] if left == a["entity_uid"] else a["name"],
                        "left_jurisdiction": a["jurisdiction"]
                        if left == a["entity_uid"]
                        else b["jurisdiction"],
                        "right_jurisdiction": b["jurisdiction"]
                        if left == a["entity_uid"]
                        else a["jurisdiction"],
                    }
                )
                if len(rows) >= max_pairs:
                    break
            if len(rows) >= max_pairs:
                break
        if len(rows) >= max_pairs:
            break

    if not rows:
        typer.echo("No candidate pairs emitted.")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(
            schema={
                "left_uid": pl.Utf8,
                "right_uid": pl.Utf8,
                "label": pl.Utf8,
                "source": pl.Utf8,
                "reason": pl.Utf8,
                "left_name": pl.Utf8,
                "right_name": pl.Utf8,
                "left_jurisdiction": pl.Utf8,
                "right_jurisdiction": pl.Utf8,
            }
        ).write_csv(out_path)
        return

    out_df = pl.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.write_csv(out_path)
    typer.echo(f"Wrote {out_df.height} candidate pairs to {out_path}")


if __name__ == "__main__":
    app()
