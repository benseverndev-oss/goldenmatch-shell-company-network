"""Address-side seed-query investigation.

    uv run python scripts/investigate_address.py \
        --text "9 East 71st Street, New York" --country us

Reads ``data/processed/address_entities.parquet`` and surfaces every
entity registered at fuzzily-matching addresses. Shared-address overlap
is the classic shell-company-network signal.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

from shellnet.investigations.address_query import (
    collect_entities_at_addresses,
    default_address_report_path,
    make_address_seed,
    rank_addresses,
    render_address_report,
)
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT, relpath_for_report

app = typer.Typer(add_completion=False, no_args_is_help=True)
log = logging.getLogger(__name__)


@app.command()
def main(
    text: str = typer.Option(..., "--text", help="Free-text address string."),
    country: str | None = typer.Option(None, "--country"),
    top_n: int = typer.Option(25, "--top-n"),
    min_score: float = typer.Option(85.0, "--min-score"),
    global_fallback: bool = typer.Option(True, "--global-fallback/--no-global-fallback"),
    processed_dir: Path = typer.Option(PROCESSED_DIR, "--processed-dir"),
    interim_dir: Path = typer.Option(INTERIM_DIR, "--interim-dir"),
    out_dir: Path = typer.Option(PROJECT_ROOT / "reports", "--out-dir"),
    out_path: Path | None = typer.Option(None, "--out-path"),
    source_note: str | None = typer.Option(None, "--source-note"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    seed = make_address_seed(text, country)
    log.info(
        "seed: %r/%r → %r/%r",
        seed.text,
        seed.country,
        seed.normalized_text,
        seed.normalized_country,
    )

    addr_path = processed_dir / "address_entities.parquet"
    if not addr_path.exists():
        raise typer.BadParameter(
            f"address_entities.parquet not found at {addr_path}. "
            "Run scripts/build_address_table.py first."
        )
    addr_df = pl.read_parquet(addr_path)
    log.info("loaded %d address rows", addr_df.height)

    in_country, outside_country = rank_addresses(
        addr_df,
        seed,
        top_n=top_n,
        min_score=min_score,
        include_outside_country=global_fallback,
    )
    log.info(
        "ranked: %d in-country, %d outside-country",
        len(in_country),
        len(outside_country),
    )

    company_path = processed_dir / "company_entities.parquet"
    company_df = pl.read_parquet(company_path) if company_path.exists() else None
    edges_path = interim_dir / "icij_edges.parquet"
    edges_df = pl.read_parquet(edges_path) if edges_path.exists() else None

    entities_by_address = collect_entities_at_addresses(
        in_country + outside_country,
        company_df=company_df,
        edges_df=edges_df,
    )
    log.info(
        "%d address group(s) surfacing %d distinct entity(ies)",
        len(entities_by_address),
        len({e.entity_uid for bucket in entities_by_address.values() for e in bucket}),
    )

    inputs_meta = {
        "address_table": relpath_for_report(addr_path),
        "icij_edges": relpath_for_report(edges_path),
        "company_table": relpath_for_report(company_path),
        "top_n": top_n,
        "min_score": min_score,
        "global_fallback": global_fallback,
    }
    md = render_address_report(
        seed,
        in_country=in_country,
        outside_country=outside_country,
        entities_by_address=entities_by_address,
        inputs_meta=inputs_meta,
        source_note=source_note,
        generated_at=datetime.now(UTC),
    )

    target = out_path or default_address_report_path(out_dir, seed)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(md, encoding="utf-8")
    log.info("wrote %s", target)
    print(str(target))


if __name__ == "__main__":
    app()
