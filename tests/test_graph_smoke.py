import json
from pathlib import Path

import polars as pl

from shellnet.graph.build import build_graph, summarize, write_summary
from shellnet.matching.company_features import build_unified_table
from shellnet.sources import icij


def test_graph_smoke_on_fixtures(tmp_path: Path, fixtures_dir: Path) -> None:
    # Stage ICIJ fixtures so we have both companies and edges.
    raw = tmp_path / "raw" / "icij"
    raw.mkdir(parents=True)
    for src, dst in [
        ("icij_entities_sample.csv", "nodes-entities.csv"),
        ("icij_addresses_sample.csv", "nodes-addresses.csv"),
        ("icij_relationships_sample.csv", "relationships.csv"),
    ]:
        (raw / dst).write_text((fixtures_dir / src).read_text("utf-8"))

    interim = tmp_path / "interim"
    icij.ingest(raw_dir=raw, out_dir=interim)

    processed = tmp_path / "processed"
    build_unified_table(interim_dir=interim, out_dir=processed)

    g = build_graph(processed_dir=processed, interim_dir=interim)
    assert g.number_of_nodes() > 0
    assert g.number_of_edges() > 0

    summary = summarize(g)
    assert summary["node_count"] == g.number_of_nodes()
    assert summary["edge_count"] == g.number_of_edges()
    assert summary["component_count"] >= 1

    out_path = tmp_path / "graph_summary.json"
    written = write_summary(g, out_path=out_path)
    assert written.exists()
    blob = json.loads(written.read_text("utf-8"))
    assert blob["edge_count"] == g.number_of_edges()


def test_graph_handles_empty_inputs(tmp_path: Path) -> None:
    # Empty company table → graph still builds with zero nodes.
    processed = tmp_path / "processed"
    processed.mkdir()
    interim = tmp_path / "interim"
    interim.mkdir()
    pl.DataFrame(
        schema={
            "entity_uid": pl.Utf8,
            "source": pl.Utf8,
            "source_id": pl.Utf8,
            "name": pl.Utf8,
            "normalized_name": pl.Utf8,
            "jurisdiction": pl.Utf8,
        }
    ).write_parquet(processed / "company_entities.parquet")
    g = build_graph(processed_dir=processed, interim_dir=interim)
    assert g.number_of_nodes() == 0
    assert g.number_of_edges() == 0
