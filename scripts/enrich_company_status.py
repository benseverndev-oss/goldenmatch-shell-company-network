"""Enrich leads with live Companies House status + harm category (Phase 3, #158).

Snapshots lag (the Aeza finding flipped active->dissolved on a live check), so
this fetches the *current* CH overview page per company via Firecrawl (CH isn't
in the network allowlist; Firecrawl is), parses status + SIC codes, and assigns
a public-harm category. Output keyed by ``lead_id`` (``GB-COH-<n>``) for the
Phase-2 ranker's gates.

    uv run python scripts/enrich_company_status.py \\
        --leads /data/processed/wrongdoing_leads.parquet \\
        --out   /data/processed/company_status.parquet

Needs FIRECRAWL_API_KEY in the environment. Results are cached to --cache-dir.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import httpx
import polars as pl
import typer

from shellnet.investigations import company_status as cs
from shellnet.investigations import harm

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)

_CH = "https://find-and-update.company-information.service.gov.uk/company/"


def _number(lead_id: str) -> str:
    return lead_id.upper().removeprefix("GB-COH-")


def _scrape(number: str, api_key: str, cache_dir: Path) -> str:
    cache = cache_dir / f"{number}.json"
    if cache.exists():
        return json.loads(cache.read_text()).get("markdown", "")
    r = httpx.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"url": f"{_CH}{number}", "formats": ["markdown"]},
        timeout=60.0,
    )
    r.raise_for_status()
    md = (r.json().get("data") or {}).get("markdown", "") or ""
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"markdown": md}))
    return md


@app.command()
def main(
    leads: Path = typer.Option(..., "--leads", help="parquet with a lead_id (GB-COH-<n>) column"),
    out: Path = typer.Option(..., "--out"),
    cache_dir: Path = typer.Option(Path("/data/raw/companies_house_cache"), "--cache-dir"),
    limit: int = typer.Option(500, "--limit", help="max companies to fetch"),
    sleep: float = typer.Option(0.4, "--sleep", help="seconds between fetches"),
) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise typer.Exit("FIRECRAWL_API_KEY not set")

    ids = pl.read_parquet(leads)["lead_id"].unique().to_list()[:limit]
    rows = []
    for lead_id in ids:
        num = _number(str(lead_id))
        try:
            md = _scrape(num, api_key, cache_dir)
        except Exception as exc:  # noqa: BLE001
            log.warning("scrape failed for %s: %r", num, exc)
            rows.append({"lead_id": lead_id, "active": None, "harm_category": "none"})
            continue
        parsed = cs.parse_ch_overview(md)
        name_m = md.splitlines()[0].lstrip("# ").strip() if md else None
        cat = harm.classify_harm(parsed["sic_codes"], name_m)  # type: ignore[arg-type]
        rows.append(
            {
                "lead_id": lead_id,
                "company_name": name_m,
                "active_status": parsed["company_status"],
                "active": cs.to_active_flag(parsed["company_status"]),  # type: ignore[arg-type]
                "incorporated_on": parsed["incorporated_on"],
                "sic_codes": ",".join(parsed["sic_codes"]),  # type: ignore[arg-type]
                "harm_category": cat,
                "harm_weight": harm.harm_weight(cat),
            }
        )
        time.sleep(sleep)

    df = pl.DataFrame(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)
    log.info("wrote status+harm for %d companies -> %s", df.height, out)
    typer.echo(f"{df.height} companies -> {out}")


if __name__ == "__main__":
    app()
