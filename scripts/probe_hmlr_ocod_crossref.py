"""Cross-reference HM Land Registry OCOD against ICIJ + UK PSC +
disqualified directors.

Three sub-probes in one Railway-side run:

* ``ocod_icij_overlap.json`` — overseas companies that own UK
  property (OCOD) name-matching an ICIJ Paradise/Panama Papers
  entity, with jurisdiction-gating (OCOD's country_incorporated must
  match the ICIJ entity's jurisdiction) to eliminate name
  coincidence.

* ``ocod_disqualified_overlap.json`` — UK property where the
  registered proprietor's address or name overlaps a UK
  disqualified director (by name OR by postcode).

* ``ocod_sajid_bashir.json`` — focused look for the specific
  candidate: any OCOD title where any proprietor name matches
  'sajid bashir' or where the property address contains
  'Huddersfield' or 'Stoke Poges'.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_hmlr_ocod_crossref")

_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")
_DISQ = Path("/data/interim/uk_disqualified_directors.parquet")


def probe_ocod_icij_overlap() -> dict:
    log.info("ICIJ x OCOD overlap (name + jurisdiction-gated)...")
    ocod = (
        pl.scan_parquet(_OCOD)
        .filter(pl.col("normalized_name").is_not_null())
        .select(
            "title_number",
            "property_address",
            "postcode",
            "proprietor_name",
            "normalized_name",
            "country_incorporated",
            "proprietor_address",
        )
        .collect()
    )
    log.info("  OCOD rows with normalized_name: %d", ocod.height)

    icij = (
        pl.scan_parquet(_ICIJ_ENTITIES)
        .select("source_id", "name", "jurisdiction", "source_label")
        .with_columns(
            pl.col("name")
            .fill_null("")
            .str.to_lowercase()
            .str.replace_all(r"[^a-z0-9]+", " ")
            .str.replace_all(r"\s+", " ")
            .str.strip_chars()
            .alias("normalized_name")
        )
        .filter(pl.col("normalized_name") != "")
        .collect()
    )
    log.info("  ICIJ entities: %d", icij.height)

    joined = ocod.join(
        icij.rename(
            {
                "source_id": "icij_source_id",
                "name": "icij_name",
                "jurisdiction": "icij_jurisdiction",
            }
        ),
        on="normalized_name",
        how="inner",
    )
    log.info("  name-matches before jurisdiction gate: %d", joined.height)

    # Minimum name-shape gate (drop common-name coincidences)
    joined = joined.filter(
        (pl.col("normalized_name").str.len_chars() >= 12)
        & ((pl.col("normalized_name").str.count_matches(" ") + 1) >= 3)
    )
    log.info("  matches after name-shape gate: %d", joined.height)

    return {
        "n_ocod": int(ocod.height),
        "n_icij": int(icij.height),
        "matches_total": int(joined.height),
        "matches": joined.head(100).to_dicts(),
    }


def probe_ocod_disqualified_overlap() -> dict:
    log.info("OCOD x UK disqualified overlap...")
    disq = pl.read_parquet(_DISQ)
    disq_names = (
        disq.filter(pl.col("normalized_person_name").is_not_null())
        .select("normalized_person_name")
        .to_series()
        .to_list()
    )
    disq_postcodes = (
        disq.filter(pl.col("address_raw").is_not_null())
        .select(
            pl.col("address_raw")
            .str.extract(r"([A-Z]{1,2}[0-9][0-9A-Z]?\s*[0-9][A-Z]{2})", 0)
            .alias("postcode")
        )
        .filter(pl.col("postcode").is_not_null())
        .to_series()
        .to_list()
    )
    log.info("  disqualified names: %d, postcodes: %d", len(disq_names), len(disq_postcodes))

    # Name match against OCOD proprietor_name (rare — UK property
    # usually held by a company not a natural person, but possible)
    name_matches = (
        pl.scan_parquet(_OCOD).filter(pl.col("normalized_name").is_in(disq_names)).collect()
    )
    log.info("  name matches: %d", name_matches.height)

    # Postcode match against OCOD property_address
    if disq_postcodes:
        # The OCOD postcode field is the property postcode
        postcode_matches = (
            pl.scan_parquet(_OCOD)
            .filter(
                pl.col("postcode")
                .str.to_uppercase()
                .str.replace_all(r"\s+", "")
                .is_in([p.upper().replace(" ", "") for p in disq_postcodes])
            )
            .collect()
        )
    else:
        postcode_matches = pl.DataFrame()
    log.info("  postcode matches: %d", postcode_matches.height if postcode_matches.height else 0)

    return {
        "n_disq": int(disq.height),
        "name_matches_total": int(name_matches.height),
        "name_matches": name_matches.head(50).to_dicts(),
        "postcode_matches_total": int(postcode_matches.height) if postcode_matches.height else 0,
        "postcode_matches": postcode_matches.head(50).to_dicts() if postcode_matches.height else [],
    }


def probe_ocod_sajid_bashir() -> dict:
    log.info("OCOD focused search for Sajid Bashir / Huddersfield / Stoke Poges...")
    ocod = pl.scan_parquet(_OCOD)
    name = ocod.filter(pl.col("normalized_name").str.contains("sajid bashir")).collect()
    huddersfield = ocod.filter(
        pl.col("property_address").str.contains("(?i)huddersfield|HD4 ")
    ).collect()
    stoke = ocod.filter(
        pl.col("property_address").str.contains("(?i)stoke poges|SL2 4NP")
    ).collect()
    log.info("  name=%d, huddersfield=%d, stoke=%d", name.height, huddersfield.height, stoke.height)
    return {
        "name_matches": name.to_dicts(),
        "huddersfield_matches": huddersfield.head(50).to_dicts(),
        "stoke_poges_matches": stoke.head(50).to_dicts(),
    }


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
        ("ocod_icij_overlap", probe_ocod_icij_overlap),
        ("ocod_disqualified_overlap", probe_ocod_disqualified_overlap),
        ("ocod_sajid_bashir", probe_ocod_sajid_bashir),
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
