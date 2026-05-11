"""One-off: summarize the icij_os_vs_gleif match output."""
from __future__ import annotations
import csv
import sys
from collections import Counter
from pathlib import Path

PATH = Path("/data/reports/generated/icij_os_vs_gleif_matched.csv")

def main() -> None:
    with PATH.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    print(f"Total matched rows: {len(rows)}")
    targets = {r["target_entity_uid"] for r in rows}
    refs = {r["ref_entity_uid"] for r in rows}
    print(f"Unique target_entity_uid (ICIJ+OS matched): {len(targets)}")
    print(f"Unique ref_entity_uid (GLEIF hits):         {len(refs)}")

    buckets: Counter[float] = Counter()
    for r in rows:
        s = float(r["__match_score__"])
        buckets[round(s, 1)] += 1
    print("\nScore distribution (rounded to 0.1):")
    for b in sorted(buckets.keys(), reverse=True):
        print(f"  {b:.1f}: {buckets[b]}")

    print("\nBy source breakdown of target:")
    src = Counter(r["target_source"] for r in rows)
    for s, n in src.most_common():
        print(f"  {s}: {n}")

    print("\nTop 10 matches by score:")
    top = sorted(rows, key=lambda x: -float(x["__match_score__"]))[:10]
    for r in top:
        t_name = (r["target_name"] or "")[:40]
        r_name = (r["ref_name"] or "")[:40]
        t_jur = r.get("target_jurisdiction") or ""
        r_jur = r.get("ref_jurisdiction") or ""
        print(f"  {r['__match_score__']:>5}  [{r['target_source'][:4]}|{t_jur}] {t_name!r:42s}  vs  [{r['ref_source'][:4]}|{r_jur}] {r_name!r}")

    print("\nSample 5 ICIJ-side matches (not opensanctions):")
    icij_matches = [r for r in rows if r["target_source"] == "icij"][:200]
    if icij_matches:
        # show 5 sorted by score
        sample = sorted(icij_matches, key=lambda x: -float(x["__match_score__"]))[:5]
        for r in sample:
            print(f"  {r['__match_score__']:>5}  [icij|{r.get('target_jurisdiction','')}] {(r['target_name'] or '')[:45]!r}  ->  [gleif|{r.get('ref_jurisdiction','')}] {(r['ref_name'] or '')[:45]!r}")


if __name__ == "__main__":
    sys.exit(main() or 0)
