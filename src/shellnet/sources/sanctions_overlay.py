"""Sanctions multi-list overlay.

Layers cross-list coverage information on top of our existing OpenSanctions
ingest. Each sanctioned entity in OpenSanctions appears in one or more
``datasets`` (e.g. ``us_ofac_sdn``, ``gb_fcdo_sanctions``, ``eu_fsf``). The
overlay projects that array into a per-entity row counting how many
*government sanction* lists the entity appears on, and which ones.

Why bother: the typical evasion pattern is being on a regional list but
absent from OFAC SDN. ``n_datasets == 1`` plus ``"us_ofac_sdn" not in
datasets`` is a strong investigative signal.

Two modes:

1. **Local** (default). Recompute the overlay from
   ``interim/opensanctions_entities.parquet`` using our curated set of
   government-sanction-list dataset prefixes. This mirrors what the
   ``goldenmatch-sanctions-reconciliation`` repo computes upstream.

2. **External**. If a ``records.parquet`` from that repo is supplied
   via ``external_parquet``, we left-join on ``os_id`` and prefer the
   external aggregation. Useful when you want their canonical
   cross-list counts (or future schema additions) without rebuilding
   the FtM corpus locally.

Output columns mirror the upstream schema so downstream readers don't
care which mode produced the parquet:

    os_id, schema, caption, names, n_names, datasets, n_datasets,
    topics, jurisdictions

Join key against the rest of the pipeline: ``os_id`` == ``source_id`` on
our OpenSanctions parquet.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR

log = logging.getLogger(__name__)

# Curated government asset-freeze sanction datasets. Substring match against
# the OS ``datasets`` array. Keep in sync with
# scripts/walk_gleif_ownership.py — that's the canonical list, this is the
# duplicate to avoid a cross-module import in a leaf source adapter.
SANCTION_DATASET_PREFIXES: tuple[str, ...] = (
    "us_ofac",
    "us_sam_exclusions",
    "us_trade_csl",
    "eu_fsf",
    "eu_travel_bans",
    "eu_journal_sanctions",
    "gb_fcdo_sanctions",
    "ch_seco_sanctions",
    "ua_nsdc_sanctions",
    "ua_war_sanctions",
    "ca_dfatd_sema_sanctions",
    "au_dfat_sanctions",
    "jp_mof_sanctions",
    "fr_tresor_gels_avoir",
    "be_fod_sanctions",
    "mc_fund_freezes",
    "nz_russia_sanctions",
)


def _is_sanction_dataset(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(p in name for p in prefixes)


def build_local_overlay(
    os_parquet: Path,
    *,
    dataset_prefixes: tuple[str, ...] = SANCTION_DATASET_PREFIXES,
) -> pl.DataFrame:
    """Compute the overlay from our existing OpenSanctions parquet.

    Filters to rows tagged with the ``sanction`` topic AND present on at
    least one curated government-sanction dataset (avoids polluting the
    overlay with ``sanction.linked``, ``reg.action``, or ``crime`` topics
    per the OS taxonomy notes in CLAUDE.md).
    """
    df = pl.scan_parquet(os_parquet).filter(pl.col("topics").list.contains("sanction"))

    df = df.with_columns(
        pl.col("datasets")
        .list.eval(
            pl.element().filter(
                pl.element().map_elements(
                    lambda s: _is_sanction_dataset(s or "", dataset_prefixes),
                    return_dtype=pl.Boolean,
                )
            )
        )
        .alias("sanction_datasets"),
    ).filter(pl.col("sanction_datasets").list.len() > 0)

    df = df.with_columns(
        pl.col("aliases")
        .list.concat(pl.concat_list(pl.col("name")))
        .list.unique()
        .alias("_all_names"),
    )

    df = df.select(
        pl.col("source_id").alias("os_id"),
        pl.col("entity_schema").alias("schema"),
        pl.col("name").alias("caption"),
        pl.col("_all_names").list.eval(pl.element().fill_null("")).list.join("; ").alias("names"),
        pl.col("_all_names").list.len().cast(pl.Int32).alias("n_names"),
        pl.col("sanction_datasets").list.unique().list.sort().list.join("; ").alias("datasets"),
        pl.col("sanction_datasets").list.unique().list.len().cast(pl.Int32).alias("n_datasets"),
        pl.col("topics").list.join("; ").alias("topics"),
        pl.col("jurisdictions").list.join("; ").alias("jurisdictions"),
    )

    return df.collect()


def merge_external(
    local: pl.DataFrame,
    external_parquet: Path,
) -> pl.DataFrame:
    """Left-join an external ``records.parquet`` from sanctions-reconciliation.

    Prefers the external aggregation for ``datasets`` / ``n_datasets`` /
    ``names`` / ``n_names`` when present (upstream may include extra
    lists or canonical cleanup we don't replicate here). Rows present
    only locally fall back to local values.
    """
    ext = pl.read_parquet(external_parquet)
    join = local.join(ext, on="os_id", how="left", suffix="_ext")
    for col in ("schema", "caption", "names", "n_names", "datasets", "n_datasets"):
        ext_col = f"{col}_ext"
        if ext_col in join.columns:
            join = join.with_columns(pl.coalesce([pl.col(ext_col), pl.col(col)]).alias(col)).drop(
                ext_col
            )
    return join


def build(
    *,
    os_parquet: Path = INTERIM_DIR / "opensanctions_entities.parquet",
    external_parquet: Path | None = None,
    out_path: Path = PROCESSED_DIR / "sanctions_overlay.parquet",
    dataset_prefixes: tuple[str, ...] = SANCTION_DATASET_PREFIXES,
) -> Path:
    """Build the overlay parquet. Returns the path written."""
    if not os_parquet.exists():
        raise FileNotFoundError(
            f"OpenSanctions interim parquet missing: {os_parquet}. "
            "Run scripts/ingest_opensanctions.py first."
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = build_local_overlay(os_parquet, dataset_prefixes=dataset_prefixes)
    log.info("sanctions overlay: %d entities from local ingest", df.height)
    if external_parquet is not None:
        if not external_parquet.exists():
            raise FileNotFoundError(f"external parquet missing: {external_parquet}")
        df = merge_external(df, external_parquet)
        log.info("sanctions overlay: merged external records from %s", external_parquet)
    df.write_parquet(out_path)
    log.info("Wrote %d rows to %s", df.height, out_path)
    return out_path
