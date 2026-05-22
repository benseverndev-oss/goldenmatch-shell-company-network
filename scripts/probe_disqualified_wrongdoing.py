"""Disqualified UK directors — surface concrete wrongdoing leads.

Pivot from infrastructure stories to surfacing specific legal
violations. The UK Companies House publishes a register of court-
*disqualified directors* (CDDA 1986 + 2015 reforms). It is a
**criminal offence** under section 11 CDDA 1986 for a disqualified
person to be involved (directly or indirectly) in the management
of any company without leave of the court — including as a
'shadow director' or via nominee.

This probe takes the UK disqualified-directors list and cross-
references three datasets to surface specific leads:

  1. ICIJ officers — disqualified UK director listed as officer
     of an offshore company in Panama/Paradise/Pandora Papers.
     If the offshore company is currently active, that's a
     potential s.11 CDDA breach.
  2. HMLR OCOD proprietor names — disqualified person appearing
     as the (named-individual) proprietor on a UK property held
     via overseas company.
  3. Their ICIJ-controlled entities -> OCOD UK property holdings.
     Three-step join: disqualified person -> ICIJ entity ->
     OCOD title.

Output: ``/data/processed/probes/disqualified_wrongdoing.json``.

NO accusation of wrongdoing in this script's output. The output is
a **lead list** — each row is a name-match that warrants
verification (DOB, address, manual reconciliation). Defamation
guard: Person schema, normalised-name ≥2 tokens AND ≥8 chars.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_disqualified_wrongdoing")


_DISQ = Path("/data/interim/uk_disqualified_directors.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")
_OCOD = Path("/data/processed/hmlr_ocod.parquet")


def _norm_expr(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/disqualified_wrongdoing.json"),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # ------------------------------------------------------------
    # Load disqualified directors
    # ------------------------------------------------------------
    log.info("loading disqualified directors...")
    disq = pl.read_parquet(_DISQ)
    log.info("  rows: %d  cols: %s", disq.height, disq.columns)

    # Find the name + DOB columns by best-effort
    name_col = next(
        (c for c in ("name", "full_name", "officer_name", "person_name") if c in disq.columns),
        None,
    )
    if name_col is None:
        log.error("no name column found in disqualified directors; columns=%s", disq.columns)
        return 1
    disq = disq.with_columns(_norm_expr(name_col).alias("_norm"))
    # Defamation guard
    guarded = disq.filter(
        (pl.col("_norm").str.len_chars() >= 8) & (pl.col("_norm").str.count_matches(r"\s") >= 1)
    )
    log.info("  guarded (>=2 tokens, >=8 chars): %d", guarded.height)
    disq_norms = guarded["_norm"].unique().to_list()
    log.info("  unique guarded names: %d", len(disq_norms))

    # ------------------------------------------------------------
    # 1. ICIJ officers name-match
    # ------------------------------------------------------------
    log.info("=== 1. disqualified vs ICIJ officers ===")
    icij_officers = pl.read_parquet(_ICIJ_OFFICERS)
    matched_officers = icij_officers.filter(pl.col("normalized_name").is_in(disq_norms))
    log.info(
        "  matched officers: %d (%d distinct names)",
        matched_officers.height,
        matched_officers["normalized_name"].n_unique(),
    )

    # ------------------------------------------------------------
    # 2. OCOD proprietor name match (where proprietor is a named
    #    individual, not a company — rare in OCOD but possible)
    # ------------------------------------------------------------
    log.info("=== 2. disqualified vs OCOD proprietors ===")
    ocod = pl.read_parquet(_OCOD)
    ocod_hits = ocod.filter(pl.col("normalized_name").is_in(disq_norms))
    log.info("  matched OCOD proprietors: %d", ocod_hits.height)

    # ------------------------------------------------------------
    # 3. disqualified -> ICIJ officer -> controlled entity -> OCOD
    # ------------------------------------------------------------
    log.info("=== 3. disqualified -> ICIJ entity -> OCOD UK property ===")
    matched_uids = ["icij:" + s for s in matched_officers["source_id"].to_list()]
    chain_hits: list[dict] = []
    if matched_uids:
        edges = pl.read_parquet(_ICIJ_EDGES)
        out_edges = edges.filter(
            pl.col("src_node").is_in(matched_uids) & (pl.col("kind_raw") == "officer_of")
        )
        controlled_uids = sorted(
            {r["dst_node"].replace("icij:", "") for r in out_edges.iter_rows(named=True)}
        )
        log.info("  ICIJ entities controlled by matched disq officers: %d", len(controlled_uids))
        if controlled_uids:
            icij_entities = (
                pl.scan_parquet(_ICIJ_ENTITIES)
                .filter(pl.col("source_id").is_in(controlled_uids))
                .with_columns(_norm_expr("name").alias("_norm"))
                .collect()
            )
            entity_norms = icij_entities["_norm"].to_list()
            chain_ocod = ocod.filter(pl.col("normalized_name").is_in(entity_norms))
            log.info("  OCOD properties held by those ICIJ entities: %d", chain_ocod.height)
            # Build per-officer breakdown
            edges_by_src: dict[str, list[str]] = {}
            for r in out_edges.iter_rows(named=True):
                edges_by_src.setdefault(r["src_node"], []).append(
                    r["dst_node"].replace("icij:", "")
                )
            ent_by_uid = {e["source_id"]: e for e in icij_entities.iter_rows(named=True)}
            ocod_by_norm: dict[str, list[dict]] = {}
            for r in chain_ocod.iter_rows(named=True):
                ocod_by_norm.setdefault(r["normalized_name"], []).append(r)
            for o in matched_officers.iter_rows(named=True):
                uid = "icij:" + o["source_id"]
                ents = []
                for euid in edges_by_src.get(uid, []):
                    e = ent_by_uid.get(euid)
                    if not e:
                        continue
                    props = ocod_by_norm.get(e["_norm"], [])
                    if props:
                        ents.append(
                            {
                                "entity_name": e.get("name"),
                                "entity_jurisdiction": e.get("jurisdiction"),
                                "entity_source": e.get("source_label"),
                                "ocod_properties": [
                                    {
                                        "title": p.get("title_number"),
                                        "address": p.get("property_address"),
                                        "postcode": p.get("postcode"),
                                        "country_incorporated": p.get("country_incorporated"),
                                    }
                                    for p in props[:5]
                                ],
                                "n_ocod_properties": len(props),
                            }
                        )
                if ents:
                    chain_hits.append(
                        {
                            "officer_name": o.get("name"),
                            "officer_normalized": o.get("normalized_name"),
                            "officer_country": o.get("country"),
                            "officer_icij_source": o.get("source_id_label"),
                            "controlling_entities_with_uk_property": ents,
                        }
                    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "totals": {
                    "disqualified_directors_total": int(disq.height),
                    "disqualified_directors_guarded": int(guarded.height),
                    "icij_officer_matches": int(matched_officers.height),
                    "ocod_proprietor_matches": int(ocod_hits.height),
                    "chain_matches_disq_to_icij_to_ocod": len(chain_hits),
                },
                "icij_officer_matches": matched_officers.head(50).to_dicts(),
                "ocod_proprietor_matches": ocod_hits.head(50).to_dicts(),
                "chain_matches": chain_hits,
                "disqualified_directors_schema": {
                    "name_col_used": name_col,
                    "columns": disq.columns,
                },
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
