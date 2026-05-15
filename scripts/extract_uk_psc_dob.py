"""Extract UK PSC DOBs from the cached BODS ZIP on Railway.

    uv run python scripts/extract_uk_psc_dob.py \\
        --input data/raw/openownership/uk_bods.zip

Emits ``data/processed/uk_psc_dob.parquet`` keyed by ``statementId``
with ``recordDetails_birthDate``. Used by `enrich_match_with_dob.py` to
add target_dob to matched.csv rows.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import polars as pl
import typer

from shellnet.paths import DATA_DIR, PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


@app.command()
def main(
    zip_path: Path = typer.Option(
        DATA_DIR / "raw" / "openownership" / "uk_bods.zip",
        "--input",
        "-i",
        help="Path to the OpenOwnership UK BODS zip bundle.",
    ),
    out_path: Path = typer.Option(
        PROCESSED_DIR / "uk_psc_dob.parquet",
        "--out",
        help="Where to write the (statementId, dob) parquet.",
    ),
) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    ensure_dirs()
    member = "person_statement.parquet"
    tmp = out_path.parent / "_uk_bods_spine_tmp.parquet"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    log.info("extracting %s from %s", member, zip_path)
    with zipfile.ZipFile(zip_path) as zf, zf.open(member) as src, tmp.open("wb") as fh:
        while True:
            chunk = src.read(8 * 1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)
    log.info("reading + projecting")
    df = (
        pl.read_parquet(tmp)
        .select(["statementId", "recordDetails_birthDate"])
        .rename({"recordDetails_birthDate": "dob"})
        .filter(pl.col("dob").is_not_null() & (pl.col("dob") != ""))
    )
    df.write_parquet(out_path)
    log.info("wrote %d UK PSC DOB rows -> %s", df.height, out_path)
    tmp.unlink(missing_ok=True)
    print(str(out_path))


if __name__ == "__main__":
    app()
