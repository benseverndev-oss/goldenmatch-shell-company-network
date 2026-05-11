from pathlib import Path

import networkx as nx
import polars as pl

from shellnet.graph.build import add_same_as_edges, summarize
from shellnet.matching.runs import cluster_pairs, load_clusters, run_paths


def _stage_run(tmp_path: Path) -> Path:
    """Create a fake GoldenMatch run output directory with two clusters."""
    out = tmp_path / "run"
    out.mkdir()
    pl.DataFrame({
        "entity_uid": ["icij:1", "gleif:2", "opencorporates:3", "opencorporates:99"],
        "cluster_id": [1, 1, 1, 2],
        "name": ["Acme Ltd", "Acme Limited", "ACME", "Solo Co"],
    }).write_csv(out / "company_clusters.csv")
    (out / "company_lineage.json").write_text(
        '{"pairs": [{"left": "icij:1", "right": "gleif:2", "score": 0.95, "cluster_id": 1}]}'
    )
    return out


def test_load_clusters(tmp_path: Path) -> None:
    out = _stage_run(tmp_path)
    paths = run_paths(out, "company")
    df = load_clusters(paths)
    assert df.height == 4
    assert "cluster_id" in df.columns


def test_cluster_pairs_only_multi_member(tmp_path: Path) -> None:
    out = _stage_run(tmp_path)
    paths = run_paths(out, "company")
    pairs = cluster_pairs(paths)
    # Cluster 1 has 3 members → C(3,2) = 3 pairs. Cluster 2 is singleton → 0.
    assert len(pairs) == 3
    members = {a for a, _, _ in pairs} | {b for _, b, _ in pairs}
    assert members == {"icij:1", "gleif:2", "opencorporates:3"}
    for _, _, cid in pairs:
        assert cid == 1


def test_add_same_as_edges_to_graph(tmp_path: Path) -> None:
    out = _stage_run(tmp_path)
    g: nx.MultiDiGraph = nx.MultiDiGraph()
    # Pre-populate two nodes; the third should be added on the fly.
    g.add_node("icij:1", kind="company", source="icij")
    g.add_node("gleif:2", kind="company", source="gleif")
    added = add_same_as_edges(g, output_dir=out, run_name="company")
    assert added == 6  # 3 undirected pairs × 2 directions
    same_as = [
        (u, v) for u, v, a in g.edges(data=True) if a.get("kind") == "same_as"
    ]
    assert len(same_as) == 6
    # The previously-missing node was added with kind=unknown.
    assert g.nodes["opencorporates:3"]["kind"] == "unknown"


def test_add_same_as_no_run(tmp_path: Path) -> None:
    g: nx.MultiDiGraph = nx.MultiDiGraph()
    added = add_same_as_edges(g, output_dir=tmp_path / "nope", run_name="company")
    assert added == 0


def test_summarize_includes_edges_by_kind(tmp_path: Path) -> None:
    out = _stage_run(tmp_path)
    g: nx.MultiDiGraph = nx.MultiDiGraph()
    g.add_node("icij:1", kind="company", source="icij")
    g.add_node("gleif:2", kind="company", source="gleif")
    g.add_edge("icij:1", "gleif:2", kind="officer_of", source="icij")
    add_same_as_edges(g, output_dir=out, run_name="company")
    s = summarize(g)
    assert s["edges_by_kind"].get("same_as", 0) > 0
    assert s["edges_by_kind"].get("officer_of", 0) == 1
