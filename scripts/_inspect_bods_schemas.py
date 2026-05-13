"""Peek at column schemas of the BODS parquets inside the UK ZIP.

One-off diagnostic to plan the join layout.
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
    members = [m for m in zf.namelist() if m in wanted]
    for m in members:
        target = work / m.replace("/", "_")
        # Extract only the file footer to read schema.
        # Easier: extract first 4 MB which is enough for parquet metadata.
        with zf.open(m) as src, target.open("wb") as fh:
            fh.write(src.read(4 * 1024 * 1024))
        try:
            schema = pq.read_schema(target)
            print(f"=== {m} ===")
            for field in schema:
                print(f"  {field.name}: {field.type}")
            print()
        except Exception as exc:
            print(f"=== {m} — could not read partial: {exc} ===")
            print()
