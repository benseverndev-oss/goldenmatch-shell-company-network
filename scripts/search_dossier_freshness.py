"""Run firecrawl queries per rare-name in a dossier parquet.

Spec: docs/superpowers/specs/2026-05-16-expose-candidates-design.md (Web search section)

Reads rare_officer_dossiers.parquet, runs 2-3 firecrawl queries per
distinct rare_name (general, offshore, optionally localized), writes
the hits as a sidecar JSON. Per-name failures are isolated; the batch
keeps going.

Auth: FIRECRAWL_API_KEY env var (provisioned as a GH Actions secret).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


_FIRECRAWL_URL = "https://api.firecrawl.dev/v1/search"


def _dominant_jurisdiction(df: pl.DataFrame, rare_name: str) -> str | None:
    """Plurality jurisdiction across the rare-name's linked companies.

    Returns None on ties (margin < 2 over runner-up).
    """
    js = (
        df.filter(pl.col("rare_name") == rare_name)
        .filter(pl.col("company_jurisdiction").is_not_null())
        .group_by("company_jurisdiction")
        .len()
        .sort("len", descending=True)
    )
    if js.height == 0:
        return None
    if js.height == 1:
        return js[0, "company_jurisdiction"]
    top, runner = js[0, "len"], js[1, "len"]
    if (top - runner) < 2:
        return None
    return js[0, "company_jurisdiction"]


def _firecrawl_search(
    client: httpx.Client, api_key: str, query: str, limit: int
) -> list[dict[str, Any]]:
    """Single firecrawl query. Returns hit dicts or [] on failure."""
    try:
        resp = client.post(
            _FIRECRAWL_URL,
            json={"query": query, "limit": limit},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        if resp.status_code == 429:
            log.warning("firecrawl rate-limited for %r", query)
            return []
        if resp.status_code >= 500:
            log.warning("firecrawl 5xx for %r: %s", query, resp.status_code)
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", []) or data.get("results", []) or []
    except (httpx.HTTPError, httpx.ReadTimeout, ValueError) as exc:
        log.warning("firecrawl exception for %r: %s", query, exc)
        return []


@app.command()
def main(
    parquet: Path = typer.Option(..., "--parquet", help="rare_officer_dossiers.parquet"),
    out: Path = typer.Option(..., "--out", help="search_results.json output path"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        log.error("FIRECRAWL_API_KEY env var not set")
        sys.exit(2)

    df = pl.read_parquet(parquet)
    rare_names = df.select("rare_name").unique().to_series().to_list()
    log.info("running firecrawl for %d rare names", len(rare_names))

    results: dict[str, dict[str, list[dict[str, Any]] | str]] = {}
    with httpx.Client() as client:
        for i, name in enumerate(rare_names, start=1):
            log.info("[%d/%d] %s", i, len(rare_names), name)
            top_juris = _dominant_jurisdiction(df, name)
            row: dict[str, list[dict[str, Any]] | str] = {
                "general": _firecrawl_search(client, api_key, f'"{name}"', 5),
                "offshore": _firecrawl_search(
                    client,
                    api_key,
                    f'"{name}" (shell OR offshore OR director OR PSC)',
                    5,
                ),
                "localized": (
                    _firecrawl_search(client, api_key, f'"{name}" {top_juris}', 3)
                    if top_juris
                    else []
                ),
                "dominant_jurisdiction": top_juris or "",
            }
            results[name] = row

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    typer.echo(f"Wrote: {out}")


if __name__ == "__main__":
    app()
