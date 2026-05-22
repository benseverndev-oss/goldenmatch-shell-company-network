"""Find the offshore-property administration hubs in HMLR OCOD.

128 Ebury Street administers 119 UK properties owned by overseas
companies (with 52 in Panama Papers per ICIJ). This probe asks the
generalised question: how many other UK addresses appear as the
proprietor correspondence point for a comparable concentration of
overseas-company-held titles?

For each candidate hub address:

  1. Count OCOD titles whose proprietor_address contains the hub
     address substring.
  2. Distinct overseas companies using the hub.
  3. Country-incorporated mix of those companies.
  4. ICIJ Panama Papers / Paradise Papers overlap by company name.

Threshold: include any address with >=20 OCOD titles to keep the
output bounded (12,000 OCOD titles total means the long tail is
small).

Output: ``/data/processed/probes/ocod_address_hubs.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections import Counter
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_ocod_address_hubs")


_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")

_HUB_THRESHOLD = 20

# Normalise proprietor_address into a hub key.
# OCOD's proprietor_address concatenates up to 3 lines + the UK
# correspondence postcode, so the same physical address sometimes
# differs by trailing whitespace, comma usage, or which line carries
# the postcode. Reduce each address to (first_line, postcode_only)
# so minor variations don't fragment hub counts.
_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2})\b", re.IGNORECASE)


def _hub_key(address: str | None) -> str | None:
    if not address:
        return None
    a = address.strip().rstrip(", ").strip()
    # Extract the postcode where present
    m = _POSTCODE_RE.search(a)
    postcode = m.group(1).upper().replace(" ", "") if m else ""
    # First "line" up to a comma or the first 60 chars
    first = a.split(",")[0].strip()
    first = re.sub(r"\s+", " ", first)[:80].strip().upper()
    if not first:
        return None
    return f"{first}||{postcode}" if postcode else first


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--threshold",
        type=int,
        default=_HUB_THRESHOLD,
        help="Minimum OCOD title count to qualify as a hub.",
    )
    p.add_argument(
        "--out", type=Path, default=Path("/data/processed/probes/ocod_address_hubs.json")
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    log.info("loading OCOD...")
    ocod = pl.read_parquet(_OCOD)
    log.info("  ocod rows: %d", ocod.height)

    # Build hub_key per row
    hubs: Counter[str] = Counter()
    rows_by_hub: dict[str, list[dict]] = {}
    for r in ocod.iter_rows(named=True):
        k = _hub_key(r.get("proprietor_address"))
        if not k:
            continue
        hubs[k] += 1
        rows_by_hub.setdefault(k, []).append(r)

    log.info("  distinct hub keys: %d", len(hubs))
    top_hubs = [(k, c) for k, c in hubs.most_common() if c >= args.threshold]
    log.info("  hubs >= %d titles: %d", args.threshold, len(top_hubs))

    log.info("loading ICIJ entities for cross-reference...")
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
            .alias("_norm")
        )
        .collect()
    )
    icij_names: set[str] = set(icij["_norm"].to_list())
    log.info("  icij entities: %d", icij.height)

    out_hubs: list[dict] = []
    for hub_key, n_titles in top_hubs:
        rows = rows_by_hub[hub_key]
        first, _, postcode = hub_key.partition("||")
        # Distinct proprietor names
        proprietors = sorted(
            {(r.get("proprietor_name") or "").strip() for r in rows if r.get("proprietor_name")}
        )
        # Country mix
        countries: Counter[str] = Counter()
        for r in rows:
            c = (r.get("country_incorporated") or "").strip()
            countries[c or "(blank)"] += 1
        # ICIJ overlap on normalized proprietor names
        icij_matches = 0
        for nm in proprietors:
            n = re.sub(r"[^a-z0-9]+", " ", nm.lower())
            n = re.sub(r"\s+", " ", n).strip()
            if n in icij_names:
                icij_matches += 1
        # Sample 5 proprietor names + 5 property addresses
        sample_props = proprietors[:5]
        sample_addrs = list({(r.get("property_address") or "")[:120] for r in rows[:20]})[:5]
        out_hubs.append(
            {
                "hub_address_first_line": first,
                "hub_postcode": postcode,
                "n_titles": n_titles,
                "n_distinct_proprietors": len(proprietors),
                "icij_matched_proprietors": icij_matches,
                "country_mix_top5": countries.most_common(5),
                "sample_proprietors": sample_props,
                "sample_properties": sample_addrs,
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "threshold": args.threshold,
                "ocod_rows_total": int(ocod.height),
                "distinct_hub_keys_total": len(hubs),
                "hubs_above_threshold": len(top_hubs),
                "hubs": out_hubs,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
