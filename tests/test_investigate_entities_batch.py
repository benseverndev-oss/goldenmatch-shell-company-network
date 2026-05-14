"""Tests for the batch seed-query workflow."""

from __future__ import annotations

import csv
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from shellnet.investigations.seed_query import (
    BatchRow,
    make_seed,
    rank_candidates,
    render_batch_index,
    render_report,
)
from shellnet.matching.company_features import build_unified_table
from shellnet.sources import gleif, icij, opencorporates, opensanctions


def _stage_full_fixtures(tmp_path: Path, fixtures_dir: Path) -> tuple[Path, Path]:
    raw_icij = tmp_path / "raw" / "icij"
    raw_icij.mkdir(parents=True)
    for src, dst in [
        ("icij_entities_sample.csv", "nodes-entities.csv"),
        ("icij_addresses_sample.csv", "nodes-addresses.csv"),
        ("icij_officers_sample.csv", "nodes-officers.csv"),
        ("icij_intermediaries_sample.csv", "nodes-intermediaries.csv"),
        ("icij_relationships_sample.csv", "relationships.csv"),
    ]:
        (raw_icij / dst).write_text((fixtures_dir / src).read_text("utf-8"))
    interim = tmp_path / "interim"
    icij.ingest(raw_dir=raw_icij, out_dir=interim)
    oc_df = opencorporates.parse_local_file(fixtures_dir / "opencorporates_company_sample.json")
    oc_df.write_parquet(interim / "opencorporates_companies.parquet")
    gleif.ingest(input_path=fixtures_dir / "gleif_lei_sample.json", out_dir=interim)
    opensanctions.ingest(
        input_path=fixtures_dir / "opensanctions_entities_sample.json",
        out_dir=interim,
    )
    processed = tmp_path / "processed"
    build_unified_table(interim_dir=interim, out_dir=processed)
    return interim, processed


def test_source_note_appears_in_rendered_report(tmp_path: Path, fixtures_dir: Path) -> None:
    _, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    df = pl.read_parquet(processed / "company_entities.parquet")
    seed = make_seed("ACME HOLDINGS LIMITED", "bvi")
    in_juris, outside = rank_candidates(df, seed, top_n=10, min_score=80.0)
    md = render_report(
        seed,
        in_juris=in_juris,
        outside_juris=outside,
        neighbourhoods=[],
        gm_context=None,
        sources_seen=["icij"],
        inputs_meta={},
        source_note="https://example.com/foo — analyst note",
        batch_id="test_batch",
    )
    assert "**Seed source:**" in md
    assert "example.com/foo" in md
    assert "Hypothesis, not proof" in md
    assert "batch `test_batch`" in md


def test_render_batch_index_summary_and_links(tmp_path: Path) -> None:
    seed_ok = make_seed("ACME HOLDINGS LIMITED", "bvi")
    seed_err = make_seed("BROKEN ENTITY", "us")
    rows = [
        BatchRow(
            seed=seed_ok,
            source_note="https://example.com/ok",
            report_path=tmp_path / "acme_holdings_vg.md",
            top_in_juris=None,  # exercised separately; None is also valid
            n_in_juris=1,
            n_outside_juris=2,
        ),
        BatchRow(
            seed=seed_err,
            source_note="https://example.com/err",
            report_path=tmp_path / "(none).md",
            top_in_juris=None,
            n_in_juris=0,
            n_outside_juris=0,
            error="RuntimeError: synthetic failure",
        ),
    ]
    md = render_batch_index(
        rows,
        batch_id="example",
        seeds_path=tmp_path / "seeds.csv",
        generated_at=datetime(2026, 5, 12, tzinfo=UTC),
    )
    assert "# Investigation batch: `example`" in md
    assert "1 error(s)" in md
    assert "## Errors" in md
    assert "synthetic failure" in md
    # Per-seed links are by filename, so the index can live next to them.
    assert "[acme_holdings_vg.md](acme_holdings_vg.md)" in md


def test_batch_script_end_to_end(tmp_path: Path, fixtures_dir: Path) -> None:
    interim, processed = _stage_full_fixtures(tmp_path, fixtures_dir)
    seeds_path = tmp_path / "seeds.csv"
    with seeds_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["name", "jurisdiction", "source_note"])
        writer.writeheader()
        writer.writerow(
            {
                "name": "ACME HOLDINGS LIMITED",
                "jurisdiction": "bvi",
                "source_note": "https://example.com/acme",
            }
        )
        writer.writerow(
            {
                "name": "SUNRISE TRADING",
                "jurisdiction": "pa",
                "source_note": "https://example.com/sunrise",
            }
        )

    out_dir = tmp_path / "reports"
    repo = Path(__file__).resolve().parents[1]
    rc = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "investigate_entities.py"),
            str(seeds_path),
            "--processed-dir",
            str(processed),
            "--interim-dir",
            str(interim),
            "--out-dir",
            str(out_dir),
            "--no-postgres",
            "--min-score",
            "80",
        ],
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr
    index_path = Path(rc.stdout.strip().splitlines()[-1])
    assert index_path.exists()
    index_md = index_path.read_text(encoding="utf-8")
    assert "# Investigation batch: `seeds`" in index_md
    assert "https://example.com/acme" in index_md
    assert "https://example.com/sunrise" in index_md

    # Per-seed reports exist alongside the index and carry the source note.
    batch_dir = index_path.parent
    seed_reports = sorted(batch_dir.glob("*.md"))
    seed_reports = [p for p in seed_reports if p.name != "index.md"]
    assert len(seed_reports) == 2
    for p in seed_reports:
        body = p.read_text(encoding="utf-8")
        assert "**Seed source:**" in body
        assert "Hypothesis, not proof" in body
