"""Personalize the ROE non-compliance story.

Three drills, all bolted to the same 5,324 non-compliant proprietor
set from probe_roe_noncompliance:

  1. ICIJ officer enrichment — for each of the 622 entities that
     name-match against ICIJ, walk the ICIJ edge table to surface
     the *people* (officers, intermediaries, beneficial owners)
     listed alongside that entity in the leaked corpus. Turns
     "FENLAND LIMITED is in Panama Papers" into "...and the
     officers named in that record are A, B, C."

  2. OS sanctions/PEP overlap — filter OS to entities tagged with
     topics in {sanction, sanction.linked, role.pep, crime,
     reg.action, wanted} BEFORE the name-match, to avoid loading
     the full 2.7 GB consolidated file. Surfaces sanctioned,
     politically-exposed, or wanted persons/entities that hold
     UK property without ROE filing.

  3. Date-aware non-compliance — auto-detect OCOD's acquisition-
     date column (the v1 probe missed it), and split non-compliant
     titles into pre/post-Aug-2022. Post-Aug-2022 titles are
     unambiguously in breach (no transitional defence) and are
     the highest-quality lead subset.

Output: ``/data/processed/probes/roe_noncompliance_personalize.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_roe_noncompliance_personalize")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_OE = Path("/data/processed/uk_ch_overseas_entities.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")
_OS_ENTITIES = Path("/data/interim/opensanctions_entities.parquet")

_OS_FLAG_TOPICS = (
    "sanction",
    "sanction.linked",
    "role.pep",
    "crime",
    "crime.fin",
    "crime.fraud",
    "crime.theft",
    "reg.action",
    "wanted",
)


def _norm_expr(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(
            r"\b(ltd|limited|llc|inc|corp|corporation|sa|spa|gmbh|bv|ag|plc|llp|lp)\b", ""
        )
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/roe_noncompliance_personalize.json"),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # ---------------- Set up the non-compliant set ----------------
    oe = pl.read_parquet(_OE).with_columns(_norm_expr("name").alias("match_key"))
    oe_keys = set(oe["match_key"].to_list())
    log.info("OE entities: %d", oe.height)

    ocod = pl.read_parquet(_OCOD)
    log.info("OCOD columns: %s", ocod.columns)
    name_col = next(
        c for c in ("proprietor_name", "normalized_name", "proprietor", "name") if c in ocod.columns
    )
    ocod = ocod.with_columns(_norm_expr(name_col).alias("match_key"))
    nc_titles = ocod.filter(
        ~pl.col("match_key").is_in(list(oe_keys)) & (pl.col("match_key").str.len_chars() > 3)
    )
    log.info("non-compliant titles: %d", nc_titles.height)
    nc_keys = set(nc_titles["match_key"].unique().to_list())
    log.info("non-compliant distinct names: %d", len(nc_keys))

    # ---------------- 1. ICIJ officer enrichment ----------------
    log.info("=== 1. ICIJ officer enrichment ===")
    icij_ent = pl.read_parquet(_ICIJ_ENTITIES).with_columns(_norm_expr("name").alias("match_key"))
    icij_nc = icij_ent.filter(pl.col("match_key").is_in(list(nc_keys)))
    log.info("  ICIJ entities matching non-compliant: %d", icij_nc.height)
    nc_entity_uids = ["icij:" + s for s in icij_nc["source_id"].to_list()]

    officer_links: list[dict] = []
    if nc_entity_uids:
        edges = pl.read_parquet(_ICIJ_EDGES)
        # Edges where the entity is on the destination side and an officer
        # is on the source side ("X officer_of Y")
        in_edges = edges.filter(
            pl.col("dst_node").is_in(nc_entity_uids)
            & pl.col("kind_raw").is_in(["officer_of", "intermediary_of", "beneficiary_of"])
        )
        log.info("  inbound officer edges: %d", in_edges.height)

        # Collect officer UIDs and look up names
        off_uids = sorted(
            {r["src_node"].replace("icij:", "") for r in in_edges.iter_rows(named=True)}
        )
        officers = (
            pl.scan_parquet(_ICIJ_OFFICERS).filter(pl.col("source_id").is_in(off_uids)).collect()
        )
        log.info("  matched officer rows: %d", officers.height)
        officer_by_uid = {o["source_id"]: o for o in officers.iter_rows(named=True)}
        entity_by_uid = {e["source_id"]: e for e in icij_nc.iter_rows(named=True)}

        # Build per-entity officer list
        ent_to_off: dict[str, list[dict]] = {}
        for r in in_edges.iter_rows(named=True):
            ent_uid = r["dst_node"].replace("icij:", "")
            off_uid = r["src_node"].replace("icij:", "")
            off = officer_by_uid.get(off_uid)
            if not off:
                continue
            ent_to_off.setdefault(ent_uid, []).append(
                {
                    "name": off.get("name"),
                    "country": off.get("country"),
                    "kind": r["kind_raw"],
                }
            )

        # Stitch back with OCOD title count
        ocod_count_by_key = nc_titles.group_by("match_key").len().sort("len", descending=True)
        cbk = {r["match_key"]: r["len"] for r in ocod_count_by_key.iter_rows(named=True)}

        for ent_uid, offs in ent_to_off.items():
            e = entity_by_uid.get(ent_uid)
            if not e:
                continue
            officer_links.append(
                {
                    "entity_name": e.get("name"),
                    "entity_jurisdiction": e.get("jurisdiction"),
                    "entity_source": e.get("source_label"),
                    "n_uk_titles": cbk.get(e["match_key"], 0),
                    "named_officers": offs[:12],
                }
            )
        officer_links.sort(key=lambda x: -x["n_uk_titles"])

    # ---------------- 2. OS sanctions/PEP overlap ----------------
    log.info("=== 2. OS sanctions/PEP overlap ===")
    os_flagged_hits: list[dict] = []
    os_diag: dict = {}
    if _OS_ENTITIES.exists():
        try:
            lazy = pl.scan_parquet(_OS_ENTITIES)
            schema = lazy.collect_schema()
            cols = schema.names()
            log.info("  OS columns: %s", cols)
            log.info("  OS topics dtype: %s", schema.get("topics"))
            os_diag["columns"] = cols
            os_diag["topics_dtype"] = str(schema.get("topics"))
            if "topics" in cols:
                topics_dtype = schema.get("topics")
                # Handle both list-of-string and plain-string topics
                if str(topics_dtype).startswith("List"):
                    topic_expr = pl.col("topics").list.join(",").alias("_topics_s")
                else:
                    topic_expr = pl.col("topics").cast(pl.Utf8).alias("_topics_s")
                topic_strs = "|".join(_OS_FLAG_TOPICS)
                # Pre-normalize name key on OS side
                hits = (
                    lazy.with_columns([topic_expr, _norm_expr("name").alias("match_key")])
                    .filter(
                        pl.col("_topics_s").fill_null("").str.contains(topic_strs)
                        & pl.col("match_key").is_in(list(nc_keys))
                    )
                    .collect()
                )
                log.info("  OS sanction/PEP/crime hits in non-compliant: %d", hits.height)
                os_flagged_hits = hits.head(100).to_dicts()
                # Sample of topics-string to confirm format
                sample_topics = (
                    lazy.with_columns(topic_expr).select("_topics_s").head(5).collect().to_dicts()
                )
                os_diag["topics_sample"] = [r["_topics_s"] for r in sample_topics]
            else:
                log.warning("  OS topics column missing")
        except Exception as exc:  # noqa: BLE001
            log.warning("  OS load failed: %s", exc)
            os_diag["error"] = str(exc)
    else:
        log.warning("  OS file missing at %s", _OS_ENTITIES)
        os_diag["error"] = f"file missing: {_OS_ENTITIES}"

    # ---------------- 3. Date-aware non-compliance ----------------
    log.info("=== 3. Date-aware non-compliance ===")
    date_col = next(
        (
            c
            for c in (
                "date_proprietor_added",
                "date_proprietor_registered",
                "date_added",
                "registration_date",
                "proprietor_date",
                "added_date",
            )
            if c in ocod.columns
        ),
        None,
    )
    pre_2022: int | None = None
    post_2022: int | None = None
    post_2022_by_country: list[dict] = []
    date_diag: dict = {}
    if date_col:
        log.info("  using date column: %s", date_col)
        dtype = nc_titles.schema.get(date_col)
        date_diag["dtype"] = str(dtype)
        # Sample raw values to confirm format before parsing
        date_diag["sample_raw"] = nc_titles.select(date_col).head(8).to_series().to_list()
        log.info("  date_col dtype=%s sample=%s", dtype, date_diag["sample_raw"])

        if str(dtype).startswith("Date") or str(dtype).startswith("Datetime"):
            with_date = nc_titles.with_columns(pl.col(date_col).alias("_d"))
        else:
            # String — try multiple UK CH date formats
            with_date = nc_titles.with_columns(
                pl.coalesce(
                    [
                        pl.col(date_col).str.to_date("%d-%m-%Y", strict=False),
                        pl.col(date_col).str.to_date("%d/%m/%Y", strict=False),
                        pl.col(date_col).str.to_date("%Y-%m-%d", strict=False),
                        pl.col(date_col).str.to_date("%d %B %Y", strict=False),
                        pl.col(date_col).str.to_date("%d-%b-%Y", strict=False),
                    ]
                ).alias("_d")
            )
        cutover = pl.date(2022, 8, 1)
        pre_2022 = int(with_date.filter(pl.col("_d") < cutover).height)
        post_2022 = int(with_date.filter(pl.col("_d") >= cutover).height)
        date_diag["pre_2022"] = pre_2022
        date_diag["post_2022"] = post_2022
        if "country_incorporated" in ocod.columns:
            post_2022_by_country = (
                with_date.filter(pl.col("_d") >= cutover)
                .group_by("country_incorporated")
                .len()
                .sort("len", descending=True)
                .head(20)
                .to_dicts()
            )
    else:
        log.warning("  no date column detected; OCOD cols: %s", ocod.columns)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "noncompliant_titles": int(nc_titles.height),
                    "noncompliant_distinct_names": len(nc_keys),
                    "icij_entity_matches": int(icij_nc.height),
                    "icij_officer_links_built": len(officer_links),
                    "os_sanction_pep_hits": len(os_flagged_hits),
                    "titles_pre_aug_2022": pre_2022,
                    "titles_post_aug_2022": post_2022,
                    "date_col_used": date_col,
                },
                "top_officer_links": officer_links[:75],
                "os_sanction_pep_hits": os_flagged_hits,
                "os_diag": os_diag,
                "post_2022_by_country": post_2022_by_country,
                "date_diag": date_diag,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
