"""GLEIF LEI adapter.

The GLEIF Golden Copy is large (~2GB compressed) and updated daily. We
deliberately do **not** download it automatically. Instead the operator is
expected to fetch a snapshot from https://www.gleif.org/en/lei-data/gleif-golden-copy
into ``data/raw/gleif/`` and then point the ingest at it with ``--input``.

This adapter parses two shapes today:

  * the per-record JSON used by the GLEIF v1 API
    (``{"data": [...]}`` or single ``{"data": {...}}``),
  * a JSON-Lines file where each line is one LEI record.

Full XML / multi-GB parquet handling is left as a TODO — the placeholder
function raises a clear NotImplementedError so behaviour is honest.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import polars as pl

from shellnet.normalize import (
    normalize_address_text,
    normalize_company_name,
    normalize_identifier,
    normalize_jurisdiction,
)
from shellnet.paths import GLEIF_RAW, INTERIM_DIR

log = logging.getLogger(__name__)


_PARQUET_SCHEMA: dict[str, type[pl.DataType]] = {
    "source": pl.Utf8,
    "source_id": pl.Utf8,            # the LEI itself
    "lei": pl.Utf8,
    "name": pl.Utf8,
    "normalized_name": pl.Utf8,
    "jurisdiction": pl.Utf8,
    "jurisdiction_raw": pl.Utf8,
    "registration_status": pl.Utf8,
    "legal_form": pl.Utf8,
    "legal_address_raw": pl.Utf8,
    "normalized_legal_address": pl.Utf8,
    "headquarters_address_raw": pl.Utf8,
    "normalized_headquarters_address": pl.Utf8,
    "parent_lei": pl.Utf8,
    "raw_json": pl.Utf8,
}


def _format_address(addr: dict[str, Any] | None) -> str:
    """Flatten a GLEIF address block into a single comparable line."""
    if not addr:
        return ""
    parts = [
        addr.get("addressLines"),
        addr.get("city"),
        addr.get("region"),
        addr.get("postalCode"),
        addr.get("country"),
    ]
    flat: list[str] = []
    for p in parts:
        if isinstance(p, list):
            flat.extend(str(x) for x in p if x)
        elif p:
            flat.append(str(p))
    return ", ".join(flat)


def parse_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map a GLEIF v1 record (the ``data`` payload) to our row shape.

    Tolerant of two shapes the wild produces:
      * the API form: ``{"id": "...", "attributes": {...}, "relationships": {...}}``
      * the Golden Copy "concatenated entities" form which puts everything
        flat under top-level keys.
    """
    attrs = record.get("attributes") or record
    entity = attrs.get("entity") or {}
    registration = attrs.get("registration") or {}

    lei = attrs.get("lei") or record.get("id") or ""
    legal_name = (entity.get("legalName") or {}).get("name") if isinstance(entity.get("legalName"), dict) else entity.get("legalName")
    legal_name = legal_name or ""
    juris_raw = entity.get("jurisdiction")
    legal_addr = _format_address(entity.get("legalAddress"))
    hq_addr = _format_address(entity.get("headquartersAddress"))

    parent_lei = None
    rels = record.get("relationships") or {}
    parent = rels.get("direct-parent") or rels.get("ultimate-parent") or {}
    parent_data = parent.get("data") if isinstance(parent, dict) else None
    if isinstance(parent_data, dict):
        parent_lei = parent_data.get("id")

    return {
        "source": "gleif",
        "source_id": normalize_identifier(lei),
        "lei": normalize_identifier(lei),
        "name": legal_name,
        "normalized_name": normalize_company_name(legal_name),
        "jurisdiction": normalize_jurisdiction(juris_raw),
        "jurisdiction_raw": juris_raw,
        "registration_status": registration.get("status"),
        "legal_form": (entity.get("legalForm") or {}).get("id") if isinstance(entity.get("legalForm"), dict) else entity.get("legalForm"),
        "legal_address_raw": legal_addr,
        "normalized_legal_address": normalize_address_text(legal_addr),
        "headquarters_address_raw": hq_addr,
        "normalized_headquarters_address": normalize_address_text(hq_addr),
        "parent_lei": normalize_identifier(parent_lei) if parent_lei else None,
        "raw_json": json.dumps(record, default=str),
    }


def _iter_records_from_file(path: Path) -> list[dict[str, Any]]:
    """Yield raw record dicts from a JSON or JSON-Lines file."""
    text = path.read_text("utf-8").strip()
    if not text:
        return []
    # Try plain JSON first.
    try:
        blob = json.loads(text)
    except json.JSONDecodeError:
        # Fall back to JSON Lines.
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(blob, list):
        return blob
    data = blob.get("data") if isinstance(blob, dict) else None
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def ingest(
    input_path: Path | None = None,
    *,
    sample: int = 0,
    out_dir: Path = INTERIM_DIR,
) -> Path | None:
    """Parse a GLEIF JSON/JSONL snapshot and write parquet output.

    ``sample`` > 0 truncates to that many records for smoke testing.
    Returns the output path, or ``None`` if no input was provided.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if input_path is None:
        log.warning(
            "No GLEIF input path provided. Download a Golden Copy snapshot from "
            "https://www.gleif.org/en/lei-data/gleif-golden-copy and pass --input."
        )
        return None

    input_path = Path(input_path)
    if not input_path.exists():
        log.error("GLEIF input %s does not exist.", input_path)
        return None

    if input_path.suffix.lower() in {".xml", ".gz", ".zip"}:
        # Be honest about what we don't yet handle.
        raise NotImplementedError(
            f"GLEIF {input_path.suffix} parsing isn't implemented yet. "
            "Convert to JSON/JSONL or use a small JSON sample for now."
        )

    records = _iter_records_from_file(input_path)
    if sample > 0:
        records = records[:sample]

    rows = [parse_record(r) for r in records if isinstance(r, dict)]
    if not rows:
        log.warning("No GLEIF records parsed from %s", input_path)
        df = pl.DataFrame(schema=_PARQUET_SCHEMA)
    else:
        df = pl.DataFrame(rows, schema=_PARQUET_SCHEMA)

    out = out_dir / "gleif_entities.parquet"
    df.write_parquet(out)
    log.info("Wrote %d GLEIF rows to %s", df.height, out)
    return out


def discover_local_files(raw_dir: Path = GLEIF_RAW) -> list[Path]:
    """List candidate GLEIF inputs in the standard raw dir."""
    if not raw_dir.exists():
        return []
    return sorted(p for p in raw_dir.iterdir() if p.is_file() and p.suffix.lower() in {".json", ".jsonl"})
