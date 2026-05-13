"""Enrich a list-match CSV with DOBs from both sides.

OS side: parse `properties.birthDate` from the raw_json column of
opensanctions_entities.parquet. UK PSC side: lookup statementId in
uk_psc_dob.parquet (produced by extract_uk_psc_dob.py).

Adds columns: target_dob, ref_dob, dob_match
  - dob_match values:
    - 'both_present_year_match' — both have DOB, year matches
    - 'both_present_year_mismatch' — both have DOB, year doesn't match
    - 'ref_only' / 'target_only' / 'neither' — partial information

Use it to filter score-1.00 matches down to the ones where the DOB
either confirms or doesn't contradict the identity hypothesis.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import INTERIM_DIR, PROCESSED_DIR

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)

_YEAR = re.compile(r"\b(19|20)\d{2}\b")


def _year(dob: str | None) -> int | None:
    if not dob:
        return None
    m = _YEAR.search(dob)
    return int(m.group(0)) if m else None


@app.command()
def main(
    matched_csv: Path = typer.Argument(...),
    os_parquet: Path = typer.Option(
        INTERIM_DIR / "opensanctions_entities.parquet", "--os-parquet"
    ),
    uk_dob_parquet: Path = typer.Option(
        PROCESSED_DIR / "uk_psc_dob.parquet", "--uk-dob"
    ),
    out_csv: Path | None = typer.Option(None, "--out"),
) -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    matched = pl.read_csv(matched_csv)
    log.info("matched rows: %d", matched.height)

    log.info("building UK PSC DOB lookup")
    uk_dob = pl.read_parquet(uk_dob_parquet) if uk_dob_parquet.exists() else None
    uk_dob_map: dict[str, str] = {}
    if uk_dob is not None and uk_dob.height:
        uk_dob_map = {r["statementId"]: r["dob"] for r in uk_dob.to_dicts()}
    log.info("UK PSC DOB rows: %d", len(uk_dob_map))

    # OS side: extract DOB from raw_json. The matched CSV has
    # ref_entity_uid like `opensanctions:<id>`. We need to look up the
    # corresponding OS row's raw_json.
    log.info("loading OS persons (for raw_json -> dob lookup)")
    os_e = pl.read_parquet(os_parquet).filter(pl.col("entity_schema") == "Person")
    os_dob: dict[str, str] = {}
    for r in os_e.iter_rows(named=True):
        try:
            rj = json.loads(r["raw_json"]) if r["raw_json"] else {}
        except json.JSONDecodeError:
            continue
        bd = (rj.get("properties") or {}).get("birthDate")
        if bd:
            # birthDate is a list in FtM
            dob = bd[0] if isinstance(bd, list) else bd
            os_dob[f"opensanctions:{r['source_id']}"] = dob
    log.info("OS DOB rows: %d", len(os_dob))

    # target_entity_uid is like uk_psc:<statementId>; strip the prefix.
    def lookup_target_dob(uid: str) -> str | None:
        if uid.startswith("uk_psc:"):
            return uk_dob_map.get(uid[len("uk_psc:"):])
        return None

    enriched = matched.with_columns(
        pl.col("target_entity_uid")
        .map_elements(lookup_target_dob, return_dtype=pl.Utf8)
        .alias("target_dob"),
        pl.col("ref_entity_uid")
        .map_elements(lambda u: os_dob.get(u), return_dtype=pl.Utf8)
        .alias("ref_dob"),
    )
    enriched = enriched.with_columns(
        pl.struct(["target_dob", "ref_dob"])
        .map_elements(
            lambda d: _classify(d["target_dob"], d["ref_dob"]),
            return_dtype=pl.Utf8,
        )
        .alias("dob_match")
    )

    summary = enriched.group_by("dob_match").agg(pl.len().alias("n")).sort(
        "n", descending=True
    )
    log.info("dob_match distribution:")
    for r in summary.iter_rows(named=True):
        log.info("  %s: %d", r["dob_match"], r["n"])

    out = out_csv or matched_csv.with_name(matched_csv.stem + "_dob.csv")
    enriched.write_csv(out)
    log.info("wrote %s", out)
    print(str(out))


def _classify(t: str | None, r: str | None) -> str:
    ty = _year(t)
    ry = _year(r)
    if ty and ry:
        return "both_present_year_match" if ty == ry else "both_present_year_mismatch"
    if ty:
        return "target_only"
    if ry:
        return "ref_only"
    return "neither"


if __name__ == "__main__":
    app()
