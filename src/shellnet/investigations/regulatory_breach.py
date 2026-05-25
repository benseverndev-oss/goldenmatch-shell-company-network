"""Disqualified-director-still-acting detector (roadmap Phase 4, issue #159).

A new wrongdoing-grade *join* the pre-existing pipeline couldn't make: cross
the UK disqualified-directors register against the new ``uk_psc_relationships``
layer to find a disqualified person who is *currently* a PSC of a UK company —
a candidate breach of s.11 Company Directors Disqualification Act 1986.

The earlier disqualified-overlap probes matched names but had no way to resolve
to the *controlled company*; the relationship layer is what makes that join
possible. Identity-grade match on name + birth year-month; lead, not verdict.
"""

from __future__ import annotations

import re

import polars as pl

__all__ = ["BREACH_COLUMNS", "normalize_dob_ym", "detect_disqualified_psc"]

BREACH_COLUMNS: tuple[str, ...] = (
    "lead_id",
    "regulatory_breach",
    "disqualified_name",
    "dob_ym",
    "conduct",
    "person_source_id",
)

_DDMMYYYY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_YYYYMM = re.compile(r"^(\d{4})-(\d{2})")


def normalize_dob_ym(value: str | None) -> str | None:
    """Normalize a DOB to ``YYYY-MM`` (the resolution both sides share).

    Handles ``DD/MM/YYYY`` (disqualified register) and ``YYYY-MM[-DD]``
    (PSC DOB). Returns ``None`` if unparseable.
    """
    if not value:
        return None
    s = value.strip()
    m = _DDMMYYYY.match(s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}"
    m = _YYYYMM.match(s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def detect_disqualified_psc(
    disqualified: pl.DataFrame,
    psc_identity: pl.DataFrame,
    relationships: pl.DataFrame,
    *,
    require_current: bool = True,
) -> pl.DataFrame:
    """Join disqualified people to currently-controlled UK companies.

    Inputs (pre-normalized):
      disqualified   ``norm_name``, ``dob_ym``, ``conduct``
      psc_identity   ``person_source_id``, ``norm_name``, ``dob_ym``
      relationships  ``person_source_id``, ``company_id``, ``end_date``

    Match is exact on (``norm_name``, ``dob_ym``) — identity-grade. With
    ``require_current``, only PSC stakes with no end date count (still acting).
    """
    d = disqualified.select("norm_name", "dob_ym", "conduct").filter(
        pl.col("norm_name").is_not_null()
        & (pl.col("norm_name") != "")
        & pl.col("dob_ym").is_not_null()
    )
    matched = d.join(psc_identity, on=["norm_name", "dob_ym"], how="inner")

    rel = relationships
    if require_current:
        rel = rel.filter(pl.col("end_date").is_null() | (pl.col("end_date") == ""))
    rel = rel.select("person_source_id", "company_id")

    joined = matched.join(rel, on="person_source_id", how="inner")
    if joined.height == 0:
        return pl.DataFrame(schema={c: pl.Utf8 for c in BREACH_COLUMNS}).with_columns(
            pl.col("regulatory_breach").cast(pl.Float64)
        )
    return (
        joined.with_columns(
            pl.col("company_id").alias("lead_id"),
            pl.lit(1.0).alias("regulatory_breach"),
            pl.col("norm_name").alias("disqualified_name"),
        )
        .group_by("lead_id")
        .agg(
            pl.col("regulatory_breach").max(),
            pl.col("disqualified_name").first(),
            pl.col("dob_ym").first(),
            pl.col("conduct").first(),
            pl.col("person_source_id").first(),
        )
        .select(list(BREACH_COLUMNS))
    )
