"""Build a verification queue for the disqualified-directors x ICIJ matches.

The wrongdoing probe surfaced ~797 name-matches between the UK
Companies House disqualified-directors register (via OpenSanctions
gb_coh_disqualified) and ICIJ Offshore Leaks officers. Many are
common-name false positives. This probe produces a *ranked
verification queue* by joining each match to both sides'
disambiguators:

  - From the OS gb_coh_disqualified side:
      DOB, nationality, addresses, disqualification dates, source URL
      (back to the UK CH register page).
  - From the ICIJ officers side:
      country code, source-label (Panama / Paradise / Pandora / etc),
      ICIJ node URL (offshoreleaks.icij.org/nodes/<id>).

Ranking heuristic — confidence ~= 1 / name_rarity:

  - Count how many disqualified persons share the normalized name
    (within the gb_coh_disqualified register).
  - Count how many ICIJ officers share the normalized name.
  - Score = 1 / (n_disq_share * n_icij_share). Unique-on-both = 1.0;
    "JOHN SMITH" on both sides = very low.

Top-K of that score is the highest-confidence verification queue.

Output: ``/data/processed/probes/disqualified_verification_queue.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_disqualified_verification_queue")


_DISQ = Path("/data/processed/uk_coh_disqualified_full.parquet")
_ICIJ_OFFICERS = Path("/data/interim/icij_officers.parquet")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/probes/disqualified_verification_queue.json"),
    )
    p.add_argument("--top-k", type=int, default=100, help="Top-K rows to include in the queue.")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    log.info("loading disqualified-directors register...")
    disq = pl.read_parquet(_DISQ)
    log.info("  rows: %d", disq.height)

    log.info("loading ICIJ officers...")
    icij = pl.read_parquet(_ICIJ_OFFICERS)
    log.info("  rows: %d", icij.height)

    # Defamation guard on disq side (2+ tokens, 8+ chars).
    disq_guarded = disq.filter(
        (pl.col("normalized_name").str.len_chars() >= 8)
        & (pl.col("normalized_name").str.count_matches(r"\s") >= 1)
    )
    log.info("  disq guarded: %d", disq_guarded.height)

    # Match
    disq_norms = set(disq_guarded["normalized_name"].to_list())
    icij_matches = icij.filter(pl.col("normalized_name").is_in(list(disq_norms)))
    log.info("  ICIJ name-match rows: %d", icij_matches.height)
    matched_norms = set(icij_matches["normalized_name"].to_list())
    log.info("  matched distinct names: %d", len(matched_norms))

    # Count rarity per name on each side
    disq_count: Counter[str] = Counter(disq_guarded["normalized_name"].to_list())
    icij_count: Counter[str] = Counter(icij["normalized_name"].to_list())

    # Group disq and ICIJ rows by name for the joined view
    disq_by_name: dict[str, list[dict]] = {}
    for r in disq_guarded.iter_rows(named=True):
        if r["normalized_name"] in matched_norms:
            disq_by_name.setdefault(r["normalized_name"], []).append(r)
    icij_by_name: dict[str, list[dict]] = {}
    for r in icij_matches.iter_rows(named=True):
        icij_by_name.setdefault(r["normalized_name"], []).append(r)

    queue: list[dict] = []
    for nm in matched_norms:
        disq_rows = disq_by_name.get(nm, [])
        icij_rows = icij_by_name.get(nm, [])
        n_disq = disq_count[nm]
        n_icij = icij_count[nm]
        # Score: 1 / (count product). Unique-on-both = 1.0
        score = 1.0 / max(1, n_disq * n_icij)
        # Pick the first disq row (canonical) + collapse ICIJ rows
        d = disq_rows[0] if disq_rows else {}
        icij_summary = [
            {
                "icij_name": i.get("name"),
                "country": i.get("country"),
                "source_label": i.get("source_id_label"),
                "source_id": i.get("source_id"),
                "icij_url": f"https://offshoreleaks.icij.org/nodes/{i.get('source_id')}",
            }
            for i in icij_rows[:5]
        ]
        queue.append(
            {
                "normalized_name": nm,
                "score": round(score, 4),
                "n_disq_records_same_name": n_disq,
                "n_icij_records_same_name": n_icij,
                "disq_canonical_name": d.get("name"),
                "disq_birth_date": d.get("birth_date"),
                "disq_nationality": d.get("nationality"),
                "disq_addresses": d.get("addresses"),
                "disq_topics": d.get("topics"),
                "disq_source_url": d.get("source_url"),
                "disq_notes": (d.get("notes") or "")[:300],
                "icij_records": icij_summary,
            }
        )

    queue.sort(key=lambda x: (-x["score"], x["normalized_name"]))
    top = queue[: args.top_k]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "total_distinct_name_matches": len(matched_norms),
                "icij_name_match_rows": int(icij_matches.height),
                "top_k": args.top_k,
                "queue": top,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    log.info("wrote %s (top %d of %d)", args.out, len(top), len(queue))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
