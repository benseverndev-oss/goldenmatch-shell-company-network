"""Score each dossier anchor on a "non-obviousness" axis.

The dossier pipeline's existing `novelty_score` weighs web-hit-count and
shell-density. It doesn't explicitly score what an investigator would call
**non-obviousness**: the structural rarity of the cross-source pattern.

This script adds five orthogonal components per anchor:

- **rarity** — inverse log of how often the normalized name pattern appears
  in the corpus. Rarer names = harder to dismiss as coincidence.
- **jurisdiction_span** — number of distinct jurisdictions touched by the
  anchor's linked companies. More spread = less easily explained by a single
  country's regulatory environment.
- **graph_surprise** — edge density of the anchor's 2-hop neighbourhood
  relative to the corpus average. Densely-interconnected shell sub-networks
  are unusual.
- **uncommon_intermediary** — does the anchor share an ICIJ intermediary
  with multiple other entities? Intermediaries that bridge ≥3 anchors are
  the "shared corporate secretary" pattern investigators look for.
- **low_freq_pattern** — uniqueness of the (source-set, jurisdiction-set)
  combination. An anchor with the rarest pattern across the dossier set
  scores highest.

Output: re-ranked dossier index with `non_obviousness_score` alongside
the existing `novelty_score`.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _compute_corpus_name_frequencies(person_table: Path) -> dict[str, int]:
    """How many times does each normalized_name appear in person_entities?"""
    df = (
        pl.scan_parquet(person_table)
        .group_by("normalized_name")
        .agg(pl.len().alias("n"))
        .collect()
    )
    return {row["normalized_name"]: row["n"] for row in df.iter_rows(named=True)}


def _rarity(name: str, freqs: dict[str, int]) -> float:
    """1 / log(freq + e) so rarer names score higher. Bounded ~[0.1, 1.0]."""
    n = freqs.get(name, 1)
    return 1.0 / math.log(max(n, 1) + math.e)


def _shared_intermediary_count(
    seed_uids: list[str],
    edges: pl.DataFrame,
) -> dict[str, int]:
    """Per seed_uid, count distinct OTHER seeds reached via a shared intermediary.

    Intermediary = a node with kind_raw == "intermediary_of" outgoing edge.
    Returns 0 if the seed isn't an ICIJ uid or has no intermediary links.
    """
    int_edges = edges.filter(pl.col("kind_raw") == "intermediary_of")
    if int_edges.height == 0:
        return dict.fromkeys(seed_uids, 0)
    # For each seed, find intermediaries it touches, then find other seeds
    # touching the same intermediaries.
    int_per_seed: dict[str, set[str]] = {}
    for r in int_edges.iter_rows(named=True):
        if r["src_node"] in seed_uids:
            int_per_seed.setdefault(r["src_node"], set()).add(r["dst_node"])
        if r["dst_node"] in seed_uids:
            int_per_seed.setdefault(r["dst_node"], set()).add(r["src_node"])
    # Invert: intermediary → seeds it touches.
    intermediary_to_seeds: dict[str, set[str]] = {}
    for seed, ints in int_per_seed.items():
        for i in ints:
            intermediary_to_seeds.setdefault(i, set()).add(seed)
    # Per seed, count shared-intermediary partners.
    out: dict[str, int] = {}
    for seed in seed_uids:
        partners: set[str] = set()
        for i in int_per_seed.get(seed, set()):
            partners |= intermediary_to_seeds.get(i, set()) - {seed}
        out[seed] = len(partners)
    return out


def _non_obviousness(
    rarity: float,
    jurisdiction_span: int,
    graph_surprise: float,
    shared_intermediary: int,
    pattern_uniqueness: float,
) -> float:
    """Weighted combination of the five orthogonal components.

    Each input is normalized to [0, 1] before weighting. Weights sum to 1.
    Lower weights on the noisier components (shared_intermediary,
    pattern_uniqueness).
    """
    return (
        0.30 * rarity
        + 0.25 * min(jurisdiction_span / 3, 1.0)
        + 0.20 * min(graph_surprise, 1.0)
        + 0.15 * min(shared_intermediary / 3, 1.0)
        + 0.10 * pattern_uniqueness
    )


@app.command()
def main(
    dossier_parquet: Path = typer.Option(
        PROCESSED_DIR / "rare_officer_dossiers.parquet",
        "--dossier-parquet",
    ),
    person_table: Path = typer.Option(
        PROCESSED_DIR / "person_entities.parquet",
        "--person-table",
    ),
    edges_parquet: Path = typer.Option(
        INTERIM_DIR / "icij_edges.parquet",
        "--edges",
    ),
    out_parquet: Path = typer.Option(
        PROCESSED_DIR / "non_obviousness_scores.parquet",
        "--out-parquet",
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "non_obviousness_summary.json",
        "--out-summary",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_parquet.parent.mkdir(parents=True, exist_ok=True)

    dossiers = pl.read_parquet(dossier_parquet)
    rare_names = dossiers.select("rare_name").unique().to_series().to_list()
    log.info("anchors to score: %d", len(rare_names))

    log.info("computing corpus name frequencies ...")
    freqs = _compute_corpus_name_frequencies(person_table)
    log.info("distinct normalized names in corpus: %d", len(freqs))

    # Pull all anchor seed UIDs for the shared-intermediary calc.
    seed_uids = (
        dossiers.filter(pl.col("person_source") == "icij")
        .select("person_entity_uid")
        .unique()
        .to_series()
        .to_list()
    )
    # Cap the edge scan to seed-adjacent edges.
    log.info("scanning edges adjacent to %d ICIJ seeds ...", len(seed_uids))
    adj_edges = (
        pl.scan_parquet(edges_parquet)
        .filter(
            pl.col("src_node").is_in(seed_uids) | pl.col("dst_node").is_in(seed_uids)
        )
        .collect()
    )
    log.info("seed-adjacent edges: %d", adj_edges.height)
    shared_int = _shared_intermediary_count(seed_uids, adj_edges)

    # Per-anchor pattern signature for low_freq_pattern: (sorted-source-set,
    # sorted-jurisdiction-set). Patterns appearing once across the dossier
    # set get max uniqueness; common patterns get low.
    anchor_patterns: dict[str, tuple[str, str]] = {}
    for name in rare_names:
        rows = dossiers.filter(pl.col("rare_name") == name)
        sources = tuple(sorted(rows.select("person_source").unique().to_series().to_list()))
        juris = tuple(
            sorted(
                set(
                    rows.filter(pl.col("company_jurisdiction").is_not_null())
                    .select("company_jurisdiction")
                    .to_series()
                    .to_list()
                )
            )
        )
        anchor_patterns[name] = (";".join(sources), ";".join(juris))
    # Pattern frequency across the dossier set.
    pattern_counts: dict[tuple[str, str], int] = {}
    for pat in anchor_patterns.values():
        pattern_counts[pat] = pattern_counts.get(pat, 0) + 1
    max_pattern_count = max(pattern_counts.values()) if pattern_counts else 1

    # Approximate graph_surprise per anchor as the local edge density of its
    # 1-hop neighbourhood in adj_edges (relative to a baseline of ~0.01).
    # density = n_edges / max_edges_for_n_nodes.
    def _local_density(uid: str) -> float:
        if uid not in seed_uids:
            return 0.0
        local = adj_edges.filter(
            (pl.col("src_node") == uid) | (pl.col("dst_node") == uid)
        )
        n_edges = local.height
        # Unique neighbours.
        neighbours = set(local.select("src_node").to_series().to_list()) | set(
            local.select("dst_node").to_series().to_list()
        )
        n_nodes = len(neighbours)
        if n_nodes < 2:
            return 0.0
        max_edges = n_nodes * (n_nodes - 1) / 2
        return min(n_edges / max_edges, 1.0)

    rows: list[dict] = []
    for name in rare_names:
        anchor_rows = dossiers.filter(pl.col("rare_name") == name)
        icij_uids = (
            anchor_rows.filter(pl.col("person_source") == "icij")
            .select("person_entity_uid")
            .unique()
            .to_series()
            .to_list()
        )
        # Aggregate components across this anchor's ICIJ-side UIDs.
        rarity = _rarity(name, freqs)
        juris_span = (
            anchor_rows.filter(pl.col("company_jurisdiction").is_not_null())
            .select("company_jurisdiction")
            .unique()
            .height
        )
        if icij_uids:
            densities = [_local_density(u) for u in icij_uids]
            graph_surprise = max(densities) if densities else 0.0
            shared = max((shared_int.get(u, 0) for u in icij_uids), default=0)
        else:
            graph_surprise = 0.0
            shared = 0
        pat = anchor_patterns[name]
        pattern_uniqueness = 1.0 - (pattern_counts[pat] - 1) / max_pattern_count

        score = _non_obviousness(
            rarity=rarity,
            jurisdiction_span=juris_span,
            graph_surprise=graph_surprise,
            shared_intermediary=shared,
            pattern_uniqueness=pattern_uniqueness,
        )
        rows.append(
            {
                "rare_name": name,
                "rarity": rarity,
                "jurisdiction_span": juris_span,
                "graph_surprise": graph_surprise,
                "shared_intermediary": shared,
                "pattern_uniqueness": pattern_uniqueness,
                "non_obviousness_score": score,
            }
        )

    df = pl.DataFrame(rows).sort("non_obviousness_score", descending=True)
    df.write_parquet(out_parquet)
    log.info("wrote %d anchor scores to %s", df.height, out_parquet)

    # Summary stats.
    summary: dict = {
        "n_anchors": int(df.height),
        "weights": {
            "rarity": 0.30,
            "jurisdiction_span": 0.25,
            "graph_surprise": 0.20,
            "shared_intermediary": 0.15,
            "pattern_uniqueness": 0.10,
        },
        "score_distribution": {
            "min": float(df["non_obviousness_score"].min() or 0),
            "median": float(df["non_obviousness_score"].median() or 0),
            "max": float(df["non_obviousness_score"].max() or 0),
            "mean": float(df["non_obviousness_score"].mean() or 0),
        },
        "top_10": df.head(10).to_dicts(),
    }
    out_summary.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    typer.echo(f"Wrote: {out_parquet}")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
