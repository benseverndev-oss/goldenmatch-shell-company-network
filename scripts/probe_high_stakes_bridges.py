"""Railway-side scan for the three high-stakes story directions.

Loads SEC 13D filers, ICIJ entities + officers, and OpenSanctions
once, then emits three JSON results under /data/processed/probes/:

* ``sanctions_overlap.json`` — SEC 13D filers whose name matches an
  OpenSanctions entity with topic=sanction OR a known sanctions
  dataset (us_ofac_sdn, us_sam_exclusions, eu_fsf, gb_fcdo_sanctions,
  ...).

* ``marinakis_expanded.json`` — all ICIJ entities + officers + edges
  linked to any Marinakis-surnamed officer, plus a check against
  OpenSanctions for any matched name.

* ``pep_sec_overlap.json`` — SEC 13D filers whose name matches an
  OpenSanctions entity tagged topic=pep (politically-exposed person).

Output JSONs are small (top matches + counts), suitable for local
inspection. The heavy compute stays on Railway via
``pl.scan_parquet`` + filter pushdown.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_high_stakes_bridges")

_SEC_EDGES = Path("/data/processed/sec_13dg_edges.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")
_ICIJ_EDGES = Path("/data/interim/icij_edges.parquet")
_OS_ENTITIES = Path("/data/interim/opensanctions_entities.parquet")

# Sanctions-emitting datasets — substring matched against OS `datasets`
# column. CLAUDE.md notes ``us_sam_exclusions`` is where the
# Sovcomflot Cyprus shells live; the broader ``sanction`` topic catches
# the rest. Substring matching keeps us robust to naming-convention
# drift (us_ofac_sdn vs us_ofac etc).
_SANCTION_DATASETS = (
    "ofac_sdn",
    "ofac_consol",
    "sam_exclusions",
    "fcdo_sanctions",
    "fsf",
    "eu_fsf",
    "ca_sema",
    "ch_seco",
    "au_dfat",
)


def _normalize_name(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _norm_expr(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


# ---------------------------------------------------------------------------
# Probe 1 — sanctioned actors in SEC 13D filers
# ---------------------------------------------------------------------------


def probe_sanctions_overlap() -> dict:
    log.info("loading SEC filers + OpenSanctions...")
    sec = (
        pl.scan_parquet(_SEC_EDGES)
        .select(
            pl.col("filer_cik").alias("cik"),
            pl.col("filer_name").alias("name"),
        )
        .unique(subset=["cik"])
        .with_columns(_norm_expr("name").alias("normalized"))
        .collect()
    )
    log.info("  %d unique SEC filers", sec.height)

    os_ent = (
        pl.scan_parquet(_OS_ENTITIES)
        .select("id", "name", "schema", "topics", "datasets")
        .collect()
        .with_columns(_norm_expr("name").alias("normalized"))
    )
    log.info("  %d OpenSanctions entities", os_ent.height)

    # Sanctioned subset: topic=sanction OR datasets contains a known
    # sanctions list.
    sanction_pat = "|".join(re.escape(s) for s in _SANCTION_DATASETS)
    sanctioned = os_ent.filter(
        pl.col("topics").list.contains("sanction")
        | pl.col("datasets").cast(pl.List(pl.String)).list.join(",").str.contains(sanction_pat)
    )
    log.info("  %d sanctioned-flagged OS entities", sanctioned.height)

    # Name-equality join on normalized
    joined = sec.join(
        sanctioned.select("id", "name", "topics", "datasets", "normalized").rename(
            {"name": "os_name", "id": "os_id"}
        ),
        on="normalized",
        how="inner",
    ).filter(
        # Drop one-word or very-short matches (defamation guard).
        (pl.col("normalized").str.len_chars() >= 12)
        & ((pl.col("normalized").str.count_matches(" ") + 1) >= 3)
    )
    log.info("  %d SEC<->sanctions matches after defamation guard", joined.height)

    return {
        "n_sec_filers": int(sec.height),
        "n_sanctioned_os_entities": int(sanctioned.height),
        "matches": joined.head(200).to_dicts(),
        "matches_total": int(joined.height),
    }


# ---------------------------------------------------------------------------
# Probe 2 — Marinakis family expansion in ICIJ
# ---------------------------------------------------------------------------


def probe_marinakis_expanded() -> dict:
    log.info("loading ICIJ officers/entities/edges for Marinakis expansion...")
    off = (
        pl.scan_parquet(_ICIJ_OFFICERS)
        .filter(pl.col("normalized_name").str.contains("marinakis"))
        .collect()
    )
    log.info("  %d Marinakis officers", off.height)
    if off.is_empty():
        return {"officers": [], "entities": [], "edges": []}

    marinakis_uids = ["icij:" + s for s in off["source_id"].to_list()]

    edges = (
        pl.scan_parquet(_ICIJ_EDGES)
        .filter(pl.col("src_node").is_in(marinakis_uids) | pl.col("dst_node").is_in(marinakis_uids))
        .collect()
    )
    log.info("  %d edges touching Marinakis officers", edges.height)

    connected = sorted(set(edges["src_node"].to_list()) | set(edges["dst_node"].to_list()))
    connected_bare = [u.replace("icij:", "") for u in connected]

    ent = (
        pl.scan_parquet(_ICIJ_ENTITIES).filter(pl.col("source_id").is_in(connected_bare)).collect()
    )
    log.info("  %d entities linked to Marinakis officers", ent.height)

    # Cross-check: do any of the names match a sanctioned/PEP OS entity?
    if ent.height:
        ent_normalized = ent.with_columns(_norm_expr("name").alias("normalized"))
        os_ent = (
            pl.scan_parquet(_OS_ENTITIES)
            .select("id", "name", "topics", "datasets")
            .collect()
            .with_columns(_norm_expr("name").alias("normalized"))
        )
        os_match = ent_normalized.join(
            os_ent.rename({"name": "os_name", "id": "os_id"}),
            on="normalized",
            how="inner",
        )
    else:
        os_match = pl.DataFrame()

    return {
        "n_officers": int(off.height),
        "n_edges": int(edges.height),
        "n_entities": int(ent.height),
        "n_os_matches": int(os_match.height) if os_match.height else 0,
        "officers": off.head(20).to_dicts(),
        "entities": ent.head(50).to_dicts(),
        "os_matches": os_match.head(20).to_dicts() if os_match.height else [],
    }


# ---------------------------------------------------------------------------
# Probe 3 — PEP overlap with SEC 13D filers
# ---------------------------------------------------------------------------


def probe_pep_overlap() -> dict:
    log.info("loading SEC filers + OpenSanctions PEPs...")
    sec = (
        pl.scan_parquet(_SEC_EDGES)
        .select(
            pl.col("filer_cik").alias("cik"),
            pl.col("filer_name").alias("name"),
        )
        .unique(subset=["cik"])
        .with_columns(_norm_expr("name").alias("normalized"))
        .collect()
    )

    peps = (
        pl.scan_parquet(_OS_ENTITIES)
        .filter(pl.col("topics").list.contains("pep"))
        .select("id", "name", "schema", "topics", "datasets")
        .collect()
        .with_columns(_norm_expr("name").alias("normalized"))
    )
    log.info("  %d PEP-flagged OS entities", peps.height)

    joined = sec.join(
        peps.select("id", "name", "topics", "datasets", "normalized").rename(
            {"name": "os_name", "id": "os_id"}
        ),
        on="normalized",
        how="inner",
    ).filter(
        (pl.col("normalized").str.len_chars() >= 12)
        & ((pl.col("normalized").str.count_matches(" ") + 1) >= 3)
    )
    log.info("  %d SEC<->PEP matches after defamation guard", joined.height)

    return {
        "n_sec_filers": int(sec.height),
        "n_peps_in_os": int(peps.height),
        "matches": joined.head(200).to_dicts(),
        "matches_total": int(joined.height),
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=Path("/data/processed/probes"))
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    for slug, fn in [
        ("sanctions_overlap", probe_sanctions_overlap),
        ("marinakis_expanded", probe_marinakis_expanded),
        ("pep_sec_overlap", probe_pep_overlap),
    ]:
        log.info("=== %s ===", slug)
        result = fn()
        out_path = args.out_dir / f"{slug}.json"
        out_path.write_text(
            json.dumps(result, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        log.info("wrote %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
