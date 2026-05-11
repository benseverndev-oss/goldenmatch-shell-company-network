"""One-off: compare schemas of two parquet files."""
import sys
import polars as pl

for path in sys.argv[1:]:
    print(f"=== {path} ===")
    s = pl.scan_parquet(path).collect_schema()
    for k, v in s.items():
        print(f"  {k}: {v}")
