"""Deep-dive on a parameterised list of OCOD proprietor-address hubs.

The ocod_address_hubs probe surfaced 596 hubs above the 20-title
threshold. The top 10 alone account for 14,000+ UK property titles.
This probe drills into each named hub and returns the full picture:

  1. All OCOD titles administered through the hub (not just samples)
     — including price_paid + date_proprietor_added + tenure.
  2. All ICIJ Panama / Paradise Papers companies that name-match
     the hub's proprietors (with ICIJ source_label + jurisdiction).
  3. Country-incorporated breakdown (full, not top-5 sample).
  4. UK postcode-district distribution of the underlying properties.
  5. Acquisition timeline (titles per year).
  6. Portfolio value (sum of recorded price_paid).

Hubs are specified by their (first_line, postcode) tuple — same
format as the address-hubs probe's hub_key. We pass them in as JSON
via the --hubs argument so the same script generalises to any list.

Output: ``/data/processed/probes/hub_deepdive.json`` — one block per
hub.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections import Counter
from pathlib import Path

import polars as pl

log = logging.getLogger("probe_hub_deepdive")


_OCOD = Path("/data/processed/hmlr_ocod.parquet")
_ICIJ_ENTITIES = Path("/data/interim/icij_entities.parquet")

_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2})\b", re.IGNORECASE)


def _norm_name(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _hub_key(address: str | None) -> str | None:
    if not address:
        return None
    a = address.strip().rstrip(", ").strip()
    m = _POSTCODE_RE.search(a)
    postcode = m.group(1).upper().replace(" ", "") if m else ""
    first = a.split(",")[0].strip()
    first = re.sub(r"\s+", " ", first)[:80].strip().upper()
    if not first:
        return None
    return f"{first}||{postcode}" if postcode else first


def _postcode_district(postcode: str | None) -> str:
    if not postcode:
        return "(none)"
    m = re.match(r"^([A-Z]{1,2}\d{1,2}[A-Z]?)", postcode.upper().strip())
    return m.group(1) if m else "(none)"


def _year_from_date(s: str | None) -> str | None:
    if not s:
        return None
    m = re.search(r"(\d{4})", s)
    return m.group(1) if m else None


# Top-10 hubs from the previous address-hubs probe. The user can
# override via --hubs (JSON list of [first_line, postcode] pairs).
_DEFAULT_HUBS = [
    ["1 ROYAL PLAZA", "GY12HL"],
    ["22 GRENVILLE STREET", "JE48PX"],
    ["44 ESPLANADE", "JE49WG"],
    ["IFC 5", "JE11ST"],
    ["11B STANLEY STREET", ""],
    ["PO BOX 781", "JE40SG"],
    ["26 NEW STREET", "JE23RA"],
    ["47 ESPLANADE", "JE10BD"],
    ["28 ESPLANADE", "JE23QA"],
    ["10 BRICKET ROAD", "AL13JX"],
]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--hubs",
        type=str,
        default="",
        help=("JSON list of [first_line, postcode] pairs. If empty, uses the top-10 default."),
    )
    p.add_argument("--out", type=Path, default=Path("/data/processed/probes/hub_deepdive.json"))
    p.add_argument(
        "--per-hub-cap",
        type=int,
        default=500,
        help="Max OCOD title rows per hub in the output (to keep JSON small).",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    targets = json.loads(args.hubs) if args.hubs else _DEFAULT_HUBS
    target_keys = [_hub_key(f"{f}, {pc}") if pc else _hub_key(f) for f, pc in targets]
    log.info("targets: %d hubs", len(target_keys))

    log.info("loading OCOD...")
    ocod = pl.read_parquet(_OCOD)
    log.info("  rows: %d", ocod.height)

    log.info("indexing OCOD by hub_key...")
    by_hub: dict[str, list[dict]] = {}
    for r in ocod.iter_rows(named=True):
        k = _hub_key(r.get("proprietor_address"))
        if not k or k not in target_keys:
            continue
        by_hub.setdefault(k, []).append(r)

    log.info("loading ICIJ entities for cross-reference...")
    icij = (
        pl.scan_parquet(_ICIJ_ENTITIES)
        .select("source_id", "name", "jurisdiction", "source_label")
        .collect()
    )
    icij_by_norm: dict[str, list[dict]] = {}
    for row in icij.iter_rows(named=True):
        nm = _norm_name(row.get("name"))
        if nm:
            icij_by_norm.setdefault(nm, []).append(row)
    log.info("  icij entries: %d", icij.height)

    hubs_out: list[dict] = []
    for (first, pc), key in zip(targets, target_keys):
        rows = by_hub.get(key, [])
        log.info("=== %s (%s) — %d titles ===", first, pc, len(rows))

        proprietors = sorted(
            {(r.get("proprietor_name") or "").strip() for r in rows if r.get("proprietor_name")}
        )
        # Country mix (full)
        country_counts = Counter(
            (r.get("country_incorporated") or "(blank)").strip() or "(blank)" for r in rows
        )
        # Postcode district hotspots of the underlying UK properties
        prop_postcodes = Counter()
        for r in rows:
            pcc = r.get("postcode") or ""
            district = _postcode_district(pcc)
            prop_postcodes[district] += 1
        # Acquisition years
        years = Counter()
        for r in rows:
            y = _year_from_date(r.get("date_proprietor_added"))
            if y:
                years[y] += 1
        # Portfolio value
        prices: list[int] = []
        for r in rows:
            pp = (r.get("price_paid") or "").strip()
            if pp.isdigit():
                prices.append(int(pp))
        total = sum(prices)

        # ICIJ matches by normalized proprietor name
        icij_matches: list[dict] = []
        for nm in proprietors:
            n = _norm_name(nm)
            if not n:
                continue
            for entry in icij_by_norm.get(n, []):
                icij_matches.append(
                    {
                        "ocod_proprietor": nm,
                        "icij_source_id": entry["source_id"],
                        "icij_name": entry["name"],
                        "icij_jurisdiction": entry.get("jurisdiction"),
                        "icij_source_label": entry.get("source_label"),
                    }
                )

        hubs_out.append(
            {
                "hub_first_line": first,
                "hub_postcode": pc,
                "n_titles": len(rows),
                "n_distinct_proprietors": len(proprietors),
                "country_mix": country_counts.most_common(),
                "property_postcode_hotspots": prop_postcodes.most_common(15),
                "acquisition_years": dict(sorted(years.items())),
                "portfolio_value_recorded_gbp": total,
                "n_titles_with_price": len(prices),
                "max_price_gbp": max(prices) if prices else 0,
                "proprietors": proprietors,
                "icij_matches": icij_matches,
                "sample_titles": [
                    {
                        "title": r.get("title_number"),
                        "address": r.get("property_address"),
                        "postcode": r.get("postcode"),
                        "proprietor": r.get("proprietor_name"),
                        "country": r.get("country_incorporated"),
                        "price_gbp": r.get("price_paid"),
                        "added": r.get("date_proprietor_added"),
                    }
                    for r in rows[: args.per_hub_cap]
                ],
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"hubs": hubs_out}, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
