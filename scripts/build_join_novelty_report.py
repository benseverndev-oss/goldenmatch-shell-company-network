"""Rank cross-source joins that surface entities present in 3+ datasets.

The thesis of this project (see ``docs/prior_art_comparison.md``) is that
sitting inside any single source UI — ICIJ Offshore Leaks DB,
OpenSanctions, GLEIF, Aleph — you can't ask "which entities appear in
*all three* with name + jurisdiction agreement?" This script answers
that for the joins we have:

- **Company triples** — same GLEIF LEI matched from both an ICIJ row
  AND an OpenSanctions row in ``icij_os_vs_gleif_matched.csv``. 3
  sources: ICIJ + OS + GLEIF.
- **DOB-confirmed sanctioned-person pairs** — OS-sanctioned person
  matched to a UK PSC officer with a confirming DOB
  (``matched_dob_scored.csv``, ``dob_match`` ∈ {match, year_match,
  full_match}). 2 sources but high-confidence, listed for context.

Both are then enriched with the *new* data layers shipped in PRs #51-#53
of this repo:

- ``processed/sanctions_overlay.parquet`` — multi-list sanction
  coverage. The high-value signal is single-list-non-OFAC (the
  evasion pattern).
- ``interim/uk_disqualified_directors.parquet`` — UK-struck-off
  directors. Joinable on (normalized_person_name, dob).

Output:
- ``processed/join_novelty.parquet`` — top-N ranked triples with the
  enrichment columns. Small (~50 KB), git-mergeable.
- ``processed/join_novelty_summary.json`` — counts, distributions, top
  patterns. Tiny.

Both files are intended to be pulled by a GH Actions workflow that
renders the markdown report (``.github/workflows/render-novelty-report.yml``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import DATA_DIR, INTERIM_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


_HIGH_CONF_DOB = ("match", "both_present_year_match", "both_present_full_match")
_REPORTS_DIR = DATA_DIR / "reports" / "generated"


def _icij_psc_pairs(matched_csv: Path) -> pl.DataFrame:
    """ICIJ ↔ UK PSC pairs from list_match_icij_vs_uk_psc.

    Filtered to high-signal subset:

    - **Exact** normalized-name equality (not fuzzy). Without DOB on
      the ICIJ side, fuzzy matches are dominated by first-name +
      honorific collisions ("Mr Sergey ... vs Mr Sergey ...").
    - Same country tag on both sides (RU↔RU, CY↔CY, etc.).
    - ≥ 3-token name (drops single-surname matches).
    - Score = 1.0 (exact-string after normalization).

    Acknowledged limitation: even exact-string matches can be different
    people with the same name in different datasets. Section 4 (rare
    multi-source officer names) is the same-evidence-base view of who
    actually appears in N sources.
    """
    if not matched_csv.exists():
        return pl.DataFrame()
    raw = pl.read_csv(matched_csv, ignore_errors=True, infer_schema_length=500)
    n_tokens = pl.col("target_normalized_name").str.split(" ").list.len()
    pairs = raw.filter(
        (pl.col("target_country") == pl.col("ref_country"))
        & (pl.col("target_country").is_not_null())
        & (pl.col("target_country") != "")
        & (n_tokens >= 3)
        & (pl.col("target_normalized_name") == pl.col("ref_normalized_name"))
        & (pl.col("__match_score__") >= 0.99)
    ).select(
        pl.col("target_entity_uid").alias("psc_uid"),
        pl.col("target_name").alias("psc_name"),
        pl.col("target_country").alias("country"),
        pl.col("ref_entity_uid").alias("icij_uid"),
        pl.col("ref_name").alias("icij_name"),
        pl.col("__match_score__").alias("name_score"),
    )
    return pairs.with_columns(
        pl.lit("icij_psc_pair").alias("kind"),
        pl.lit(2).alias("n_sources"),
    )


def _rare_officer_overlaps(officer_overlap_parquet: Path) -> pl.DataFrame:
    """Officer names appearing across 2+ sources with bounded cardinality.

    Selects only names that look investigative:
      - n_sources >= 2 (already enforced upstream)
      - max_per_source <= 2 (rare in EVERY source — not a common-name explosion)
      - n_tokens >= 3 (single-token surnames are too ambiguous)
    """
    if not officer_overlap_parquet.exists():
        return pl.DataFrame()
    raw = pl.read_parquet(officer_overlap_parquet)
    return (
        raw.filter((pl.col("max_per_source") <= 2) & (pl.col("n_tokens") >= 3))
        .with_columns(
            pl.lit("officer_overlap").alias("kind"),
        )
        .rename({"n_sources": "_n_sources"})
        .with_columns(pl.col("_n_sources").alias("n_sources"))
        .drop("_n_sources")
    )


def _disqualified_overlaps(disq_overlap_parquet: Path) -> pl.DataFrame:
    """Disqualified UK directors who appear in cross-source datasets.

    Filters to ICIJ + GLEIF matches (the rare ones) — UK PSC matches
    are dominated by common UK names (Singh, Smith) and aren't useful
    signal.
    """
    if not disq_overlap_parquet.exists():
        return pl.DataFrame()
    raw = pl.read_parquet(disq_overlap_parquet)
    return (
        raw.filter(pl.col("source").is_in(["icij", "gleif"]))
        .with_columns(
            pl.lit("disqualified_overlap").alias("kind"),
            pl.lit(2).alias("n_sources"),
        )
    )


def _company_triples(
    icij_os_vs_gleif: Path,
) -> pl.DataFrame:
    """ICIJ + OS + GLEIF triples — same LEI matched from both ICIJ and OS sides."""
    raw = pl.read_csv(icij_os_vs_gleif, ignore_errors=True, infer_schema_length=500)
    icij_side = raw.filter(pl.col("target_source") == "icij").select(
        pl.col("target_entity_uid").alias("icij_uid"),
        pl.col("target_name").alias("icij_name"),
        pl.col("target_jurisdiction").alias("icij_jurisdiction"),
        pl.col("ref_entity_uid").alias("gleif_uid"),
        pl.col("ref_lei").alias("lei"),
        pl.col("ref_name").alias("gleif_name"),
        pl.col("__match_score__").alias("icij_gleif_score"),
    )
    os_side = raw.filter(pl.col("target_source") == "opensanctions").select(
        pl.col("target_entity_uid").alias("os_uid"),
        pl.col("target_name").alias("os_name"),
        pl.col("ref_entity_uid").alias("gleif_uid"),
        pl.col("__match_score__").alias("os_gleif_score"),
    )
    return icij_side.join(os_side, on="gleif_uid", how="inner").with_columns(
        pl.lit("company_triple").alias("kind"),
        pl.lit(3).alias("n_sources"),
    )


def _person_dob_pairs(
    matched_dob_scored: Path,
) -> pl.DataFrame:
    """OS sanctioned person ↔ UK PSC officer with DOB-confirming match."""
    raw = pl.read_csv(matched_dob_scored, ignore_errors=True, infer_schema_length=500)
    pairs = raw.filter(
        (pl.col("dob_match").is_in(_HIGH_CONF_DOB)) & (pl.col("target_source") == "uk_psc")
    ).select(
        pl.col("target_entity_uid").alias("psc_uid"),
        pl.col("target_name").alias("psc_name"),
        pl.col("target_dob").alias("psc_dob"),
        pl.col("target_country").alias("psc_country"),
        pl.col("ref_entity_uid").alias("os_uid"),
        pl.col("ref_name").alias("os_name"),
        pl.col("ref_dob").alias("os_dob"),
        pl.col("__match_score__").alias("name_score"),
        pl.col("dob_match"),
        pl.col("prior_coverage_n"),
        pl.col("prior_coverage_mainstream"),
    )
    return pairs.with_columns(
        pl.lit("dob_confirmed_pair").alias("kind"),
        pl.lit(2).alias("n_sources"),
    )


def _enrich_with_sanctions_overlay(
    triples: pl.DataFrame,
    overlay: pl.DataFrame,
    *,
    os_uid_col: str = "os_uid",
) -> pl.DataFrame:
    """Left-join the sanctions overlay so each row carries n_datasets + non_ofac."""
    if triples.height == 0:
        return triples
    # OS source_id format on our side is e.g. "opensanctions:Q12345"; overlay's
    # os_id is the bare OS UID. Strip the "opensanctions:" prefix if present.
    keyed = triples.with_columns(
        pl.col(os_uid_col).str.replace("^opensanctions:", "").alias("_os_key")
    )
    ov = overlay.select(
        pl.col("os_id").alias("_os_key"),
        pl.col("n_datasets").alias("sanction_list_count"),
        pl.col("datasets").alias("sanction_datasets"),
    )
    joined = keyed.join(ov, on="_os_key", how="left").drop("_os_key")
    return joined.with_columns(
        (
            (pl.col("sanction_list_count") == 1)
            & ~pl.col("sanction_datasets").fill_null("").str.contains("us_ofac_sdn")
        ).alias("evasion_signal_single_list_non_ofac")
    )


def _enrich_with_disqualified_directors(
    triples: pl.DataFrame,
    disq: pl.DataFrame,
    *,
    name_col: str,
) -> pl.DataFrame:
    """Left-join uk_disqualified_directors on (lowered name [+ dob if present])."""
    if triples.height == 0 or disq.height == 0:
        return triples.with_columns(pl.lit(False).alias("uk_disqualified_match"))
    disq_keyed = disq.select(
        pl.col("normalized_person_name").alias("_d_name"),
        pl.col("date_of_birth").alias("_d_dob"),
        pl.col("disqualification_length").alias("disq_length"),
    ).unique(subset=["_d_name"])
    name_norm = pl.col(name_col).str.to_lowercase().str.strip_chars()
    keyed = triples.with_columns(name_norm.alias("_t_name"))
    joined = keyed.join(disq_keyed, left_on="_t_name", right_on="_d_name", how="left").drop(
        "_t_name"
    )
    return joined.with_columns(pl.col("disq_length").is_not_null().alias("uk_disqualified_match"))


def _summary_for_extras(
    icij_psc: pl.DataFrame, rare_officers: pl.DataFrame, disq_xref: pl.DataFrame
) -> dict[str, object]:
    return {
        "icij_psc_pairs": {
            "n_rows": int(icij_psc.height),
            "distinct_psc_uids": (
                int(icij_psc.select("psc_uid").unique().height) if icij_psc.height else 0
            ),
            "distinct_icij_uids": (
                int(icij_psc.select("icij_uid").unique().height) if icij_psc.height else 0
            ),
            "country_distribution": (
                icij_psc.group_by("country").len().sort("len", descending=True).to_dicts()
                if icij_psc.height
                else []
            ),
        },
        "rare_officer_overlaps": {
            "n_rows": int(rare_officers.height),
            "by_n_sources": (
                rare_officers.group_by("n_sources")
                .len()
                .sort("n_sources", descending=True)
                .to_dicts()
                if rare_officers.height
                else []
            ),
        },
        "disqualified_overlaps": {
            "n_rows": int(disq_xref.height),
            "by_source": (
                disq_xref.group_by("source").len().sort("len", descending=True).to_dicts()
                if disq_xref.height
                else []
            ),
        },
    }


def _summary(company: pl.DataFrame, persons: pl.DataFrame) -> dict[str, object]:
    return {
        "company_triples": {
            "n_rows": int(company.height),
            "distinct_leis": (
                int(company.select("lei").unique().height) if company.height else 0
            ),
            "distinct_icij_uids": (
                int(company.select("icij_uid").unique().height) if company.height else 0
            ),
            "distinct_os_uids": (
                int(company.select("os_uid").unique().height) if company.height else 0
            ),
            "with_evasion_signal": (
                int(company.filter(pl.col("evasion_signal_single_list_non_ofac")).height)
                if company.height
                else 0
            ),
            "with_disqualified_director_overlap": (
                int(company.filter(pl.col("uk_disqualified_match")).height)
                if company.height
                else 0
            ),
            "jurisdiction_distribution": (
                company.group_by("icij_jurisdiction").len().sort("len", descending=True).to_dicts()
                if company.height
                else []
            ),
        },
        "dob_confirmed_pairs": {
            "n_rows": int(persons.height),
            "distinct_os_uids": (
                int(persons.select("os_uid").unique().height) if persons.height else 0
            ),
            "with_evasion_signal": (
                int(persons.filter(pl.col("evasion_signal_single_list_non_ofac")).height)
                if persons.height
                else 0
            ),
            "with_disqualified_director_overlap": (
                int(persons.filter(pl.col("uk_disqualified_match")).height)
                if persons.height
                else 0
            ),
        },
    }


@app.command()
def main(
    icij_os_vs_gleif: Path = typer.Option(
        _REPORTS_DIR / "icij_os_vs_gleif_matched.csv",
        "--icij-os-vs-gleif",
        help="Pair match CSV from list_match_os_vs_gleif (target=ICIJ or OS, ref=GLEIF).",
    ),
    matched_dob: Path = typer.Option(
        _REPORTS_DIR / "matched_dob_scored.csv",
        "--matched-dob",
        help="OS↔(ICIJ+UK_PSC) match CSV with DOB scoring.",
    ),
    overlay: Path = typer.Option(
        PROCESSED_DIR / "sanctions_overlay.parquet",
        "--overlay",
    ),
    disqualified: Path = typer.Option(
        INTERIM_DIR / "uk_disqualified_directors.parquet",
        "--disqualified",
    ),
    icij_psc_matched: Path = typer.Option(
        _REPORTS_DIR / "list_match_icij_vs_uk_psc_matched.csv",
        "--icij-psc-matched",
        help="ICIJ↔UK_PSC direct match CSV.",
    ),
    officer_overlap: Path = typer.Option(
        PROCESSED_DIR / "officer_overlap.parquet",
        "--officer-overlap",
    ),
    disqualified_overlaps: Path = typer.Option(
        PROCESSED_DIR / "disqualified_overlaps.parquet",
        "--disqualified-overlaps",
    ),
    out_parquet: Path = typer.Option(
        PROCESSED_DIR / "join_novelty.parquet",
        "--out-parquet",
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "join_novelty_summary.json",
        "--out-summary",
    ),
    top_n: int = typer.Option(
        200, "--top-n", help="Per-kind cap. Each kind is sorted before truncation."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_parquet.parent.mkdir(parents=True, exist_ok=True)

    ov_df = (
        pl.read_parquet(overlay)
        if overlay.exists()
        else pl.DataFrame(schema={"os_id": pl.Utf8, "n_datasets": pl.Int32, "datasets": pl.Utf8})
    )
    disq_df = (
        pl.read_parquet(disqualified)
        if disqualified.exists()
        else pl.DataFrame(
            schema={
                "normalized_person_name": pl.Utf8,
                "date_of_birth": pl.Utf8,
                "disqualification_length": pl.Utf8,
            }
        )
    )

    company = _company_triples(icij_os_vs_gleif)
    company = _enrich_with_sanctions_overlay(company, ov_df, os_uid_col="os_uid")
    company = _enrich_with_disqualified_directors(company, disq_df, name_col="icij_name")
    company = company.sort(
        by=["evasion_signal_single_list_non_ofac", "icij_gleif_score"],
        descending=[True, True],
    ).head(top_n)
    log.info("company triples kept: %d", company.height)

    persons = _person_dob_pairs(matched_dob)
    persons = _enrich_with_sanctions_overlay(persons, ov_df, os_uid_col="os_uid")
    persons = _enrich_with_disqualified_directors(persons, disq_df, name_col="psc_name")
    persons = persons.sort(
        by=["evasion_signal_single_list_non_ofac", "name_score"],
        descending=[True, True],
    ).head(top_n)
    log.info("dob-confirmed person pairs kept: %d", persons.height)

    icij_psc = _icij_psc_pairs(icij_psc_matched).head(top_n)
    log.info("icij↔psc filtered pairs kept: %d", icij_psc.height)

    rare_officers = _rare_officer_overlaps(officer_overlap).head(top_n)
    log.info("rare multi-source officer names kept: %d", rare_officers.height)

    disq_xref = _disqualified_overlaps(disqualified_overlaps).head(top_n)
    log.info("disqualified-director cross-refs kept: %d", disq_xref.height)

    all_rows = pl.concat(
        [company, persons, icij_psc, rare_officers, disq_xref],
        how="diagonal_relaxed",
    )
    log.info(
        "writing %d rows across %d kinds to %s",
        all_rows.height,
        all_rows.select("kind").unique().height,
        out_parquet,
    )
    all_rows.write_parquet(out_parquet)

    summary = _summary(company, persons)
    summary.update(_summary_for_extras(icij_psc, rare_officers, disq_xref))
    out_summary.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log.info("summary written to %s", out_summary)
    typer.echo(f"Wrote: {out_parquet}")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
