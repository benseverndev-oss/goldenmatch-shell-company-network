"""Sanctions-evasion timing detector (roadmap Phase 1).

The signal: control of a UK company changing hands around the moment its
controller (or the company itself) is sanctioned — a divestment to a relative
or thin-identity nominee. This is a *wrongdoing signal* (the act), not a status
lookup, and it is what makes a lead worth chasing.

Inputs (all polars frames, so the core is unit-testable without I/O):

  survivors      sanctioned-person <-> UK PSC matches (the existing
                 ``investigative_grade_survivors.csv`` shape). Columns used:
                 ``target_entity_uid`` (``uk_psc:<statementId>``),
                 ``ref_entity_uid`` (``opensanctions:<os_id>``), ``target_name``.
  relationships  ``uk_psc_relationships.parquet`` (bods ingest). Columns used:
                 ``person_source_id``, ``company_id``, ``company_number``,
                 ``start_date``, ``end_date``.
  designations   ``os_id``, ``designation_date``, ``date_quality`` — built by
                 :func:`build_designation_dates`.
  persons        unified UK PSC persons (``source_id``, ``name``) — used to
                 name the incoming nominee/successor.

Output: one row per (sanctioned principal, company, successor-PSC) where a new
controller's stake began within ``window_days`` of the designation.
"""

from __future__ import annotations

import polars as pl

__all__ = [
    "EVASION_COLUMNS",
    "build_designation_dates",
    "detect_evasion_timing",
]

EVASION_COLUMNS: tuple[str, ...] = (
    "principal_name",
    "principal_os_id",
    "designation_date",
    "date_quality",
    "company_id",
    "company_number",
    "principal_control_end",
    "successor_source_id",
    "successor_name",
    "successor_control_start",
    "delta_days",
    "same_surname",
)


def _to_date(col: str) -> pl.Expr:
    """Parse a lenient ISO date/datetime string to ``Date`` (first 10 chars)."""
    return (
        pl.col(col)
        .cast(pl.Utf8)
        .str.slice(0, 10)
        .str.strptime(pl.Date, format="%Y-%m-%d", strict=False)
    )


def _surname_root(name_col: str) -> pl.Expr:
    """Surname root for same-family comparison.

    Last whitespace-delimited token, lowercased, with a single trailing ``a``
    stripped so Russian gendered pairs collapse (``Ivanov``/``Ivanova`` ->
    ``ivanov``) — the wife/daughter-nominee pattern this detector targets. A
    coarse heuristic feeding a ranking *flag*, not a filter.
    """
    return (
        pl.col(name_col)
        .cast(pl.Utf8)
        .str.to_lowercase()
        .str.replace_all(r"[^a-z\s]", "")
        .str.strip_chars()
        .str.split(" ")
        .list.last()
        .str.replace(r"a$", "")
    )


def build_designation_dates(os_entities: pl.DataFrame) -> pl.DataFrame:
    """Project OpenSanctions entities to (os_id, designation_date, date_quality).

    ``first_seen`` is the designation date for entities that entered
    OpenSanctions *via* a sanctions dataset (e.g. AEZA INTERNATIONAL LTD's
    first_seen is exactly the 2025-07-01 OFAC date). For entities that were
    tracked as PEPs/Wikidata before being listed, ``first_seen`` is a
    placeholder (commonly midnight on Jan 1) — flagged ``placeholder`` so the
    detector and downstream review can discount it.
    """
    if "topics" in os_entities.columns:
        df = os_entities.filter(pl.col("topics").list.contains("sanction"))
    else:
        df = os_entities
    raw = pl.col("first_seen").cast(pl.Utf8)
    placeholder = raw.str.contains(r"-01-01T00:00:00") | raw.is_null()
    return df.select(
        pl.col("source_id").alias("os_id"),
        pl.col("name"),
        _to_date("first_seen").alias("designation_date"),
        pl.when(placeholder)
        .then(pl.lit("placeholder"))
        .otherwise(pl.lit("dataset_first_seen"))
        .alias("date_quality"),
    ).unique(subset=["os_id"], keep="first")


def _strip_prefix(col: str, prefix: str) -> pl.Expr:
    return (
        pl.when(pl.col(col).str.starts_with(prefix))
        .then(pl.col(col).str.slice(len(prefix)))
        .otherwise(pl.col(col))
    )


def detect_evasion_timing(
    survivors: pl.DataFrame,
    relationships: pl.DataFrame,
    designations: pl.DataFrame,
    persons: pl.DataFrame,
    *,
    window_days: int = 730,
    drop_placeholder: bool = False,
) -> pl.DataFrame:
    """Flag PSC control transfers that cluster around a designation date.

    For each sanctioned principal matched to a UK PSC record, find the
    company(ies) they controlled, then surface any *other* PSC whose stake
    started within ``window_days`` of the designation — the candidate
    nominee/successor the control was handed to.

    With ``drop_placeholder`` the detector discards designations whose date is a
    placeholder (PEPs tracked before listing, dated midnight on Jan 1): the delta
    against such a date is meaningless, so they are noise, not leads (precision
    roadmap P5).
    """
    # Sanctioned principal -> their UK PSC statementId + the company they hold.
    # Keep only uk_psc-target rows (the others are ICIJ matches with no PSC edge).
    surv = survivors.filter(pl.col("target_entity_uid").str.starts_with("uk_psc:")).select(
        _strip_prefix("target_entity_uid", "uk_psc:").alias("person_source_id"),
        _strip_prefix("ref_entity_uid", "opensanctions:").alias("os_id"),
        pl.col("target_name").alias("principal_name"),
    )

    surv = surv.join(designations, on="os_id", how="inner")
    if drop_placeholder:
        surv = surv.filter(pl.col("date_quality") != "placeholder")

    principal_edges = relationships.select(
        "person_source_id",
        "company_id",
        "company_number",
        pl.col("end_date").alias("principal_control_end"),
    )
    principal = surv.join(principal_edges, on="person_source_id", how="inner")

    # All PSC stakes on those companies, to find who came in around the date.
    successors = relationships.select(
        "company_id",
        pl.col("person_source_id").alias("successor_source_id"),
        pl.col("start_date").alias("successor_control_start"),
    )
    joined = principal.join(successors, on="company_id", how="inner").filter(
        pl.col("successor_source_id") != pl.col("person_source_id")
    )

    person_names = persons.select(
        pl.col("source_id").alias("successor_source_id"),
        pl.col("name").alias("successor_name"),
    )
    joined = joined.join(person_names, on="successor_source_id", how="left")

    # Drop the principal reappearing as their own successor under a different
    # company-scoped statement id (same human, not a transfer).
    def _norm(c: str) -> pl.Expr:
        return pl.col(c).cast(pl.Utf8).str.to_lowercase().str.replace_all(r"[^a-z]", "")

    joined = joined.filter(_norm("successor_name") != _norm("principal_name"))

    joined = joined.with_columns(
        (_to_date("successor_control_start") - pl.col("designation_date"))
        .dt.total_days()
        .alias("delta_days"),
        (
            (_surname_root("principal_name") == _surname_root("successor_name"))
            & (_surname_root("successor_name") != "")
        ).alias("same_surname"),
    )

    out = joined.rename({"os_id": "principal_os_id"}).filter(
        pl.col("delta_days").is_not_null() & (pl.col("delta_days").abs() <= window_days)
    )
    return (
        out.select(list(EVASION_COLUMNS))
        .unique()
        .sort(["same_surname", "delta_days"], descending=[True, False])
    )
