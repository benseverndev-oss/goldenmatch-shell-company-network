"""Streaming adapter for the GLEIF Golden Copy CDF JSON format.

The Golden Copy "concatenated entities" file is ~13 GB unzipped and uses an
XML-derived JSON shape where every leaf is wrapped in ``{"$": "<value>"}``.
The v1 API adapter in ``shellnet.sources.gleif`` reads the whole file into
memory and assumes the API record shape, so it can't handle this format.

This adapter streams the file with ``ijson``, maps each record to the same
parquet schema the v1 adapter produces, and writes the result in row-group
chunks via PyArrow so peak memory stays bounded.

Reference structure (abbreviated):

```
{"records": [
  {
    "LEI": {"$": "..."},
    "Entity": {
        "LegalName": {"@xml:lang": "en", "$": "..."},
        "LegalAddress": {"FirstAddressLine": {"$": "..."}, "City": {"$": "..."}, ...},
        "LegalJurisdiction": {"$": "US-DE"},
        "LegalForm": {"EntityLegalFormCode": {"$": "..."}}
    },
    "Registration": {"RegistrationStatus": {"$": "ISSUED"}}
  },
  ...
]}
```

Parent relationships live in a separate RR (Relationship Record) file, so
``parent_lei`` is always null when ingesting only the LEI2 concatenated
entities file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterator

import ijson
import polars as pl

from shellnet.normalize import (
    normalize_address_text,
    normalize_company_name,
    normalize_identifier,
    normalize_jurisdiction,
)
from shellnet.paths import INTERIM_DIR
from shellnet.sources.gleif import _PARQUET_SCHEMA

log = logging.getLogger(__name__)

_BATCH_SIZE = 100_000


def _leaf(node: Any) -> Any:
    """GLEIF CDF wraps leaves in ``{"$": "value"}``; unwrap one level."""
    if isinstance(node, dict):
        if "$" in node:
            return node["$"]
    return node


def _format_cdf_address(addr: dict[str, Any] | None) -> str:
    if not addr:
        return ""
    keys = ("FirstAddressLine", "AdditionalAddressLine", "City", "Region", "PostalCode", "Country")
    parts: list[str] = []
    for k in keys:
        val = addr.get(k)
        if isinstance(val, list):
            for v in val:
                v = _leaf(v)
                if v:
                    parts.append(str(v))
        else:
            v = _leaf(val)
            if v:
                parts.append(str(v))
    return ", ".join(parts)


def parse_cdf_record(record: dict[str, Any]) -> dict[str, Any]:
    entity = record.get("Entity") or {}
    registration = record.get("Registration") or {}

    lei = _leaf(record.get("LEI")) or ""
    legal_name = _leaf(entity.get("LegalName")) or ""
    juris_raw = _leaf(entity.get("LegalJurisdiction"))
    legal_addr = _format_cdf_address(entity.get("LegalAddress"))
    hq_addr = _format_cdf_address(entity.get("HeadquartersAddress"))

    legal_form_block = entity.get("LegalForm") or {}
    legal_form = _leaf(legal_form_block.get("EntityLegalFormCode"))

    status = _leaf(registration.get("RegistrationStatus"))

    return {
        "source": "gleif",
        "source_id": normalize_identifier(lei),
        "lei": normalize_identifier(lei),
        "name": legal_name,
        "normalized_name": normalize_company_name(legal_name),
        "jurisdiction": normalize_jurisdiction(juris_raw),
        "jurisdiction_raw": juris_raw,
        "registration_status": status,
        "legal_form": legal_form,
        "legal_address_raw": legal_addr,
        "normalized_legal_address": normalize_address_text(legal_addr),
        "headquarters_address_raw": hq_addr,
        "normalized_headquarters_address": normalize_address_text(hq_addr),
        "parent_lei": None,  # comes from the RR file, not this one
        "raw_json": json.dumps(record, default=str)[:2000],  # truncate for size
    }


def _iter_cdf(path: Path) -> Iterator[dict[str, Any]]:
    """Yield each record under ``records.item`` without loading the whole file."""
    with path.open("rb") as fh:
        for rec in ijson.items(fh, "records.item"):
            if isinstance(rec, dict):
                yield rec


def ingest_streaming(
    input_path: Path,
    *,
    sample: int = 0,
    out_dir: Path = INTERIM_DIR,
    batch_size: int = _BATCH_SIZE,
) -> Path:
    """Stream-parse a Golden Copy CDF JSON file into ``gleif_entities.parquet``.

    Writes one row-group per batch via PyArrow so peak memory tracks
    batch_size, not file size. Concatenates chunk parquets at the end.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "gleif_entities.parquet"
    tmp_dir = out_dir / "_gleif_chunks"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    # Wipe any prior chunks from a failed run.
    for p in tmp_dir.glob("chunk_*.parquet"):
        p.unlink()

    buf: list[dict[str, Any]] = []
    total = 0
    chunk_index = 0
    for rec in _iter_cdf(input_path):
        buf.append(parse_cdf_record(rec))
        if sample and total + len(buf) >= sample:
            buf = buf[: sample - total]
            total += len(buf)
            chunk_path = tmp_dir / f"chunk_{chunk_index:06d}.parquet"
            pl.DataFrame(buf, schema=_PARQUET_SCHEMA).write_parquet(chunk_path)
            log.info("wrote chunk %s (%d rows, sample cap reached)", chunk_path.name, len(buf))
            buf = []
            chunk_index += 1
            break
        if len(buf) >= batch_size:
            chunk_path = tmp_dir / f"chunk_{chunk_index:06d}.parquet"
            pl.DataFrame(buf, schema=_PARQUET_SCHEMA).write_parquet(chunk_path)
            total += len(buf)
            log.info("wrote chunk %s (%d rows, total %d)", chunk_path.name, len(buf), total)
            buf = []
            chunk_index += 1

    if buf:
        chunk_path = tmp_dir / f"chunk_{chunk_index:06d}.parquet"
        pl.DataFrame(buf, schema=_PARQUET_SCHEMA).write_parquet(chunk_path)
        total += len(buf)
        log.info("wrote final chunk %s (%d rows, total %d)", chunk_path.name, len(buf), total)

    # Concatenate all chunks into one parquet for downstream code.
    chunks = sorted(tmp_dir.glob("chunk_*.parquet"))
    if chunks:
        log.info("concatenating %d chunks into %s", len(chunks), out)
        lf = pl.concat([pl.scan_parquet(p) for p in chunks], how="vertical")
        try:
            lf.sink_parquet(out)
        except Exception:
            # Older polars may not support sink_parquet; fall back.
            lf.collect(streaming=True).write_parquet(out)
        for p in chunks:
            p.unlink()
        tmp_dir.rmdir()
    else:
        log.warning("no GLEIF records parsed from %s", input_path)
        pl.DataFrame(schema=_PARQUET_SCHEMA).write_parquet(out)

    log.info("Wrote %d GLEIF rows to %s", total, out)
    return out
