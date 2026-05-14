"""Person-side seed-query investigation.

    uv run python scripts/investigate_person.py \
        --name "Jeffrey Epstein" --country us

Reads ``data/processed/person_entities.parquet`` and surfaces every
company the matched person(s) are attached to via ICIJ officer /
intermediary / shareholder edges. Companion to ``investigate_entity.py``;
walks the graph in the opposite direction (person → entities).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer
from dotenv import load_dotenv

from shellnet.investigations.person_query import (
    collect_company_edges,
    default_person_report_path,
    make_person_seed,
    rank_person_candidates,
    render_person_report,
)
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT, relpath_for_report

load_dotenv()

app = typer.Typer(add_completion=False, no_args_is_help=True)
log = logging.getLogger(__name__)


@app.command()
def main(
    name: str = typer.Option(..., "--name", help="Seed person name."),
    country: str | None = typer.Option(
        None, "--country", help="ISO-2/ISO-3/alias country preference."
    ),
    top_n: int = typer.Option(25, "--top-n", help="Max candidates per section."),
    min_score: float = typer.Option(
        90.0,
        "--min-score",
        help="Person matching defaults higher than company matching (names collide harder).",
    ),
    global_fallback: bool = typer.Option(
        True,
        "--global-fallback/--no-global-fallback",
        help="If a country is given, also search outside it and list separately.",
    ),
    processed_dir: Path = typer.Option(
        PROCESSED_DIR, "--processed-dir", help="Override the processed-parquet directory."
    ),
    interim_dir: Path = typer.Option(
        INTERIM_DIR, "--interim-dir", help="Override the interim-parquet directory."
    ),
    out_dir: Path = typer.Option(
        PROJECT_ROOT / "reports",
        "--out-dir",
        help="Reports root. The report lands under `<out-dir>/investigations/persons/`.",
    ),
    out_path: Path | None = typer.Option(
        None, "--out-path", help="Override the auto-generated report path entirely."
    ),
    source_note: str | None = typer.Option(
        None,
        "--source-note",
        help="Free-text seed provenance (URL / citation) embedded in the report.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    seed = make_person_seed(name, country)
    log.info(
        "seed: %r/%r → %r/%r",
        seed.name,
        seed.country,
        seed.normalized_name,
        seed.normalized_country,
    )

    person_path = processed_dir / "person_entities.parquet"
    if not person_path.exists():
        raise typer.BadParameter(
            f"person_entities.parquet not found at {person_path}. "
            "Run scripts/build_person_table.py first."
        )
    person_df = pl.read_parquet(person_path)
    log.info("loaded %d person rows", person_df.height)

    in_country, outside_country = rank_person_candidates(
        person_df,
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

    icij_person_uids = [c.entity_uid for c in (in_country + outside_country) if c.source == "icij"]
    edges_path = interim_dir / "icij_edges.parquet"
    edges_df = pl.read_parquet(edges_path) if edges_path.exists() else None
    company_path = processed_dir / "company_entities.parquet"
    company_df = pl.read_parquet(company_path) if company_path.exists() else None

    edges_by_person = collect_company_edges(
        icij_person_uids, edges_df=edges_df, company_df=company_df
    )
    log.info(
        "%d person→company edge(s) across %d matched person(s)",
        sum(len(v) for v in edges_by_person.values()),
        len(edges_by_person),
    )

    inputs_meta = {
        "person_table": relpath_for_report(person_path),
        "icij_edges": relpath_for_report(edges_path),
        "company_table": relpath_for_report(company_path),
        "top_n": top_n,
        "min_score": min_score,
        "global_fallback": global_fallback,
    }
    md = render_person_report(
        seed,
        in_country=in_country,
        outside_country=outside_country,
        edges_by_person=edges_by_person,
        inputs_meta=inputs_meta,
        source_note=source_note,
        generated_at=datetime.now(UTC),
    )

    target = out_path or default_person_report_path(out_dir, seed)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(md, encoding="utf-8")
    log.info("wrote %s", target)
    print(str(target))


if __name__ == "__main__":
    app()
