"""One-off: inspect icij edge ID format vs entity_uid format."""
import polars as pl
df = pl.scan_parquet("/data/interim/icij_edges.parquet")
print("schema:", df.collect_schema())
print("sample:")
print(df.head(5).collect())
print()
print("src_node distinct len 1k sample:")
samp = df.head(1000).collect()
import collections
sl = collections.Counter(len(str(x)) for x in samp["src_node"].to_list())
print("src_node string-len distribution:", sl)
print()
print("Comparing to a known entity_uid like icij:172123 (Oriental Century)")
hits = df.filter((pl.col("src_node") == "172123") | (pl.col("dst_node") == "172123")).head(5).collect()
print("hits filter=str '172123':", hits.height)
print(hits)
