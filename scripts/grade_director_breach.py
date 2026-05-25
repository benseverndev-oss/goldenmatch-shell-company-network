"""Grade disqualified-PSC leads: acting director vs passive shareholder (P1-P3).

For each regulatory-breach lead, fetch the company's live Companies House
officers page via Firecrawl and grade whether the disqualified person is a
current director (a real s.11 CDDA candidate) or merely a >25% shareholder.
Emits a ``director_breach.parquet`` signal the Phase-2 ranker consumes via
``--extra-signals`` (column ``acting_director_breach``), plus an
``identity_confidence`` and ``live_confirmed`` flag for human triage.

    uv run python scripts/grade_director_breach.py \\
        --breach        /data/processed/regulatory_breach.parquet \\
        --disqualified  /data/interim/uk_disqualified_directors.parquet \\
        --out           /data/processed/director_breach.parquet

Needs FIRECRAWL_API_KEY in the environment. Results cached to --cache-dir.
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

from shellnet.investigations import director_breach as db
from shellnet.investigations import regulatory_breach as rb

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)

_CH = "https://find-and-update.company-information.service.gov.uk/company/"


def _number(lead_id: str) -> str:
    return str(lead_id).upper().removeprefix("GB-COH-")


def _scrape_officers(number: str, api_key: str, cache_dir: Path) -> str:
    cache = cache_dir / f"{number}.json"
    if cache.exists():
        return json.loads(cache.read_text()).get("markdown", "")
    r = httpx.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"url": f"{_CH}{number}/officers", "formats": ["markdown"]},
        timeout=60.0,
    )
    r.raise_for_status()
    md = (r.json().get("data") or {}).get("markdown", "") or ""
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"markdown": md}))
    return md


@app.command()
def main(
    breach: Path = typer.Option(..., "--breach", help="regulatory_breach.parquet"),
    disqualified: Path = typer.Option(..., "--disqualified", help="for the disq address"),
    out: Path = typer.Option(..., "--out"),
    cache_dir: Path = typer.Option(Path("/data/raw/ch_officers_cache"), "--cache-dir"),
    limit: int = typer.Option(500, "--limit"),
    sleep: float = typer.Option(0.4, "--sleep"),
) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise typer.Exit("FIRECRAWL_API_KEY not set")

    leads = pl.read_parquet(breach)
    # Pull the disqualified person's registered address for identity corroboration.
    disq = pl.read_parquet(disqualified).select(
        pl.col("normalized_person_name").alias("disqualified_name"),
        pl.col("date_of_birth")
        .map_elements(rb.normalize_dob_ym, return_dtype=pl.Utf8)
        .alias("dob_ym"),
        pl.col("normalized_address").alias("disq_address"),
    )
    disq = disq.unique(subset=["disqualified_name", "dob_ym"], keep="first")
    leads = leads.join(disq, on=["disqualified_name", "dob_ym"], how="left")

    rows = []
    for r in leads.head(limit).iter_rows(named=True):
        num = _number(r["lead_id"])
        try:
            md = _scrape_officers(num, api_key, cache_dir)
        except Exception as exc:  # noqa: BLE001
            log.warning("officers scrape failed for %s: %r", num, exc)
            rows.append(
                {
                    "lead_id": r["lead_id"],
                    "breach_grade": "unknown",
                    "acting_director_breach": 0.0,
                    "identity_confidence": 0.0,
                    "live_confirmed": False,
                    "matched_role": None,
                    "matched_officer_name": None,
                }
            )
            continue
        officers = db.parse_ch_officers(md)
        graded = db.grade_company(
            officers, r["disqualified_name"], r.get("dob_ym"), r.get("disq_address")
        )
        graded["lead_id"] = r["lead_id"]
        rows.append(graded)
        time.sleep(sleep)

    df = db.grade_to_frame(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)
    by_grade = df["breach_grade"].value_counts(sort=True).to_dicts() if df.height else []
    log.info("graded %d breach leads -> %s | grades=%s", df.height, out, by_grade)
    typer.echo(f"{df.height} graded -> {out}")


if __name__ == "__main__":
    app()
