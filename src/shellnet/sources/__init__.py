"""Per-source adapters.

Each adapter is responsible for:

  * locating its raw inputs (downloaded by the user or by an ingest script),
  * mapping them onto the canonical schemas in :mod:`shellnet.schemas`,
  * writing source-specific interim parquet files under ``data/interim/``.

Adapters never reach into other adapters. Cross-source linking happens later
in :mod:`shellnet.matching` and :mod:`shellnet.graph`.
"""
