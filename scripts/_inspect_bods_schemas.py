"""Peek at column schemas of the BODS parquets inside the UK ZIP.

Parquet footers live at the END of the file, not the start, so we
extract each file fully. Sub-tables are small enough to be cheap.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pyarrow.parquet as pq

zip_path = Path(sys.argv[1])
wanted = {
    "person_statement.parquet",
    "person_recorddetails_names.parquet",
    "person_recorddetails_nationalities.parquet",
    "person_recorddetails_addresses.parquet",
    "entity_statement.parquet",
    "entity_recorddetails_addresses.parquet",
    "entity_recorddetails_identifiers.parquet",
    "relationship_statement.parquet",
    "relationship_recorddetails_interests.parquet",
}
work = Path("/tmp/bods_peek")
work.mkdir(exist_ok=True, parents=True)
with zipfile.ZipFile(zip_path) as zf:
    info_by_name = {m: zf.getinfo(m) for m in zf.namelist() if m in wanted}
    for m in sorted(info_by_name):
        info = info_by_name[m]
        target = work / m
        size = info.file_size
        with zf.open(m) as src, target.open("wb") as fh:
            while True:
                chunk = src.read(8 * 1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        try:
            pf = pq.ParquetFile(target)
            print(f"=== {m}  ({size:,} bytes, rows={pf.metadata.num_rows:,}) ===")
            for field in pf.schema_arrow:
                print(f"  {field.name}: {field.type}")
            print()
        except Exception as exc:
            print(f"=== {m} — could not read: {exc} ===")
            print()
        finally:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
