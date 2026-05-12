"""OpenSanctions adapter (enrichment, not ground truth).

OpenSanctions distributes datasets as line-delimited JSON ("FtM" entities)
plus aggregated CSVs. We support the LDJSON / NDJSON form because it
preserves nested properties cleanly. Drop a file like ``entities.ftm.json``
into ``data/raw/opensanctions/`` and point the ingest at it.

We never call the website at import time. If you want to wire up a remote
download, set ``OPENSANCTIONS_DATASET_URL`` in your env and use the
``download`` helper explicitly.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
import polars as pl

from shellnet.normalize import (
    normalize_address_text,
    normalize_company_name,
    normalize_identifier,
    normalize_jurisdiction,
)
from shellnet.paths import INTERIM_DIR, OPENSANCTIONS_RAW

log = logging.getLogger(__name__)

USER_AGENT = "shellnet/0.1 (+https://github.com/) GoldenMatch case study"


_PARQUET_SCHEMA: dict[str, type[pl.DataType]] = {
    "source": pl.Utf8,
    "source_id": pl.Utf8,
    "entity_schema": pl.Utf8,           # OpenSanctions FtM schema name (Company, Person, ...)
    "name": pl.Utf8,
    "normalized_name": pl.Utf8,
    "aliases": pl.List(pl.Utf8),
    "jurisdictions": pl.List(pl.Utf8),
    "identifiers": pl.List(pl.Utf8),
    "addresses_raw": pl.List(pl.Utf8),
    "normalized_addresses": pl.List(pl.Utf8),
    "topics": pl.List(pl.Utf8),         # sanctions, pep, crime, ...
    "datasets": pl.List(pl.Utf8),
    "first_seen": pl.Utf8,
    "last_seen": pl.Utf8,
    "raw_json": pl.Utf8,
}


def _as_list(value: Any) -> list[str]:
    """Normalise FtM properties (lists of strings or scalars) into list[str]."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def parse_entity(record: dict[str, Any]) -> dict[str, Any]:
    """Map an FtM-style OpenSanctions entity record to the row shape."""
    props = record.get("properties") or {}
    names = _as_list(props.get("name"))
    primary_name = names[0] if names else (record.get("caption") or "")
    aliases = _as_list(props.get("alias")) + names[1:]
    jurisdictions_raw = _as_list(props.get("jurisdiction")) + _as_list(props.get("country"))
    jurisdictions = sorted({
        j for j in (normalize_jurisdiction(x) for x in jurisdictions_raw) if j
    })

    identifiers = []
    for key in ("registrationNumber", "leiCode", "ogrnCode", "innCode", "okpoCode", "swiftBic", "taxNumber"):
        identifiers.extend(normalize_identifier(v) for v in _as_list(props.get(key)))
    identifiers = [i for i in identifiers if i]

    addresses_raw = _as_list(props.get("address"))
    normalized_addresses = [normalize_address_text(a) for a in addresses_raw]

    topics = _as_list(props.get("topics"))
    datasets = _as_list(record.get("datasets"))

    return {
        "source": "opensanctions",
        "source_id": str(record.get("id") or ""),
        "entity_schema": str(record.get("schema") or ""),
        "name": primary_name,
        "normalized_name": normalize_company_name(primary_name),
        "aliases": aliases,
        "jurisdictions": jurisdictions,
        "identifiers": identifiers,
        "addresses_raw": addresses_raw,
        "normalized_addresses": normalized_addresses,
        "topics": topics,
        "datasets": datasets,
        "first_seen": record.get("first_seen"),
        "last_seen": record.get("last_seen"),
        "raw_json": json.dumps(record, default=str),
    }


def _iter_entities(path: Path) -> list[dict[str, Any]]:
    """Read entities from a JSON, NDJSON, or wrapped-JSON file.

    For NDJSON (one JSON object per line) we stream line-by-line so
    multi-GB OpenSanctions exports don't OOM the read step.
    """
    # NDJSON detection: peek the first non-empty line.
    with path.open("r", encoding="utf-8") as fh:
        first = ""
        while not first:
            line = fh.readline()
            if not line:
                return []
            first = line.strip()
        if first.startswith("{"):
            # Stream NDJSON. Reopen so we restart at line 1.
            out: list[dict[str, Any]] = []
            try:
                out.append(json.loads(first))
            except json.JSONDecodeError:
                pass
            else:
                for ln in fh:
                    s = ln.strip()
                    if not s:
                        continue
                    try:
                        out.append(json.loads(s))
                    except json.JSONDecodeError:
                        continue
                return out
    # Fall back to whole-file load for small JSON / wrapped-JSON.
    text = path.read_text("utf-8").strip()
    blob = json.loads(text)
    if isinstance(blob, list):
        return blob
    if isinstance(blob, dict):
        if "entities" in blob and isinstance(blob["entities"], list):
            return blob["entities"]
        if "results" in blob and isinstance(blob["results"], list):
            return blob["results"]
        return [blob]
    return []


def ingest(
    input_path: Path | None = None,
    *,
    out_dir: Path = INTERIM_DIR,
) -> Path | None:
    """Parse a local OpenSanctions export and write a parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)

    if input_path is None:
        log.warning(
            "No OpenSanctions input path provided. Download a dataset export "
            "(see https://www.opensanctions.org/datasets/) into %s and re-run.",
            OPENSANCTIONS_RAW,
        )
        return None

    input_path = Path(input_path)
    if not input_path.exists():
        log.error("OpenSanctions input %s does not exist.", input_path)
        return None

    records = _iter_entities(input_path)
    rows = [parse_entity(r) for r in records if isinstance(r, dict)]
    if not rows:
        log.warning("No OpenSanctions records parsed from %s", input_path)
        df = pl.DataFrame(schema=_PARQUET_SCHEMA)
    else:
        df = pl.DataFrame(rows, schema=_PARQUET_SCHEMA)

    out = out_dir / "opensanctions_entities.parquet"
    df.write_parquet(out)
    log.info("Wrote %d OpenSanctions rows to %s", df.height, out)
    return out


def download(
    url: str | None = None,
    *,
    out_path: Path | None = None,
    chunk_size: int = 1 << 16,
) -> Path:
    """Download a stable OpenSanctions export to disk.

    The URL is read from the ``url`` argument or, if not given, from the
    ``OPENSANCTIONS_DATASET_URL`` env var. We refuse to guess so we don't
    accidentally hammer their CDN.
    """
    src_url = url or os.environ.get("OPENSANCTIONS_DATASET_URL")
    if not src_url:
        raise ValueError(
            "No OpenSanctions URL provided. Pass url= or set OPENSANCTIONS_DATASET_URL."
        )
    OPENSANCTIONS_RAW.mkdir(parents=True, exist_ok=True)
    target = out_path or (OPENSANCTIONS_RAW / Path(src_url).name)
    target = Path(target)

    log.info("Downloading OpenSanctions export to %s", target)
    with httpx.stream("GET", src_url, headers={"User-Agent": USER_AGENT}, timeout=120.0) as r:
        r.raise_for_status()
        with target.open("wb") as fh:
            for chunk in r.iter_bytes(chunk_size):
                fh.write(chunk)
    return target
