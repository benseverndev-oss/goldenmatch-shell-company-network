"""Helpers for reading GoldenMatch run output.

GoldenMatch's CLI emits two files per run under the configured output dir:

  * ``<run_name>_clusters.csv`` — one row per *input record*, with a
    ``cluster_id`` column grouping records into clusters.
  * ``<run_name>_lineage.json`` — per-pair scores and metadata.

This module hides those naming details so other code can ask for clusters
or pairs by run name and not care about the layout.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import polars as pl


@dataclass(frozen=True)
class RunPaths:
    run_name: str
    clusters_csv: Path
    lineage_json: Path

    def exists(self) -> bool:
        return self.clusters_csv.exists() and self.lineage_json.exists()


def run_paths(output_dir: Path, run_name: str) -> RunPaths:
    return RunPaths(
        run_name=run_name,
        clusters_csv=output_dir / f"{run_name}_clusters.csv",
        lineage_json=output_dir / f"{run_name}_lineage.json",
    )


def load_clusters(
    paths: RunPaths,
    *,
    id_column: str = "entity_uid",
    source_table: Path | None = None,
) -> pl.DataFrame:
    """Return a frame with ``id_column`` and ``cluster_id``.

    Real GoldenMatch output uses ``__cluster_id__`` + ``__row_id__`` and
    doesn't propagate the input id column. If we see those, we join with
    ``source_table`` on row order to recover ``id_column``. Older / hand-
    written cluster files that already carry both columns natively are
    returned as-is.
    """
    if not paths.clusters_csv.exists():
        raise FileNotFoundError(paths.clusters_csv)
    df = pl.read_csv(paths.clusters_csv)

    if id_column in df.columns and "cluster_id" in df.columns:
        return df

    # GoldenMatch format. We need the source table to recover the id.
    if "__cluster_id__" in df.columns and "__row_id__" in df.columns:
        if source_table is None or not Path(source_table).exists():
            raise ValueError(
                "GoldenMatch cluster output uses opaque row ids; pass source_table= "
                "so we can join back to the input id column."
            )
        src = pl.read_parquet(source_table).with_row_index(name="__row_id__")
        # Polars row_index is u32; the cluster CSV has it as int. Cast both.
        df = df.with_columns(pl.col("__row_id__").cast(pl.UInt32))
        src = src.with_columns(pl.col("__row_id__").cast(pl.UInt32))
        joined = df.join(src.select(["__row_id__", id_column]), on="__row_id__", how="left")
        joined = joined.rename({"__cluster_id__": "cluster_id"})
        return joined.select(id_column, "cluster_id")

    raise ValueError(
        f"Cluster output has neither ({id_column!r}, 'cluster_id') nor "
        f"('__row_id__', '__cluster_id__'); found {df.columns}"
    )


def load_pairs(paths: RunPaths) -> list[dict]:
    """Return the pair-level lineage records (each has src/dst ids + score)."""
    if not paths.lineage_json.exists():
        return []
    blob = json.loads(paths.lineage_json.read_text("utf-8"))
    pairs = blob.get("pairs") or []
    return list(pairs) if isinstance(pairs, list) else []


def cluster_pairs(
    paths: RunPaths,
    *,
    id_column: str = "entity_uid",
    min_cluster_size: int = 2,
    source_table: Path | None = None,
) -> list[tuple[str, str, int]]:
    """Return ``(left_uid, right_uid, cluster_id)`` tuples for all multi-member clusters.

    Useful when the runner doesn't emit explicit pair scores (single-pass
    runs do) but the cluster file is still there.
    """
    df = load_clusters(paths, id_column=id_column, source_table=source_table)
    out: list[tuple[str, str, int]] = []
    for cid, group in df.group_by("cluster_id"):
        ids = sorted(str(x) for x in group[id_column].to_list() if x is not None)
        if len(ids) < min_cluster_size:
            continue
        cid_int = int(cid[0]) if isinstance(cid, tuple) else int(cid)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                out.append((ids[i], ids[j], cid_int))
    return out
