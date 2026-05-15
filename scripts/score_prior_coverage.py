"""Score each unique candidate-novel match by prior published coverage.

    uv run python scripts/score_prior_coverage.py \\
        reports/generated/matched_dob.csv

For every distinct (target_name, target_country) tuple in an enriched
match CSV, run a Firecrawl search for the name + relevant keywords
and produce a prior-coverage score:

  - 0 = no results (zero published coverage)
  - 1-2 = sparse / non-mainstream only
  - 3+ = multiple mainstream investigative outlets

Output: the input CSV with two added columns — `prior_coverage_n`
(raw result count) and `prior_coverage_score` (a heuristic
bucketing). Rows are then sorted ascending by coverage so the lowest-
coverage candidates surface first.

This is what gets us from "the matcher rediscovers 43 sanctioned
names" to "here are the 3 sanctioned-individual ↔ UK Ltd pairs no
mainstream outlet has published."

Requires the `firecrawl` CLI on PATH and an authenticated session.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import httpx
import polars as pl
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)

MAINSTREAM_HOSTS = (
    "icij.org",
    "occrp.org",
    "reuters.com",
    "ft.com",
    "bloomberg.com",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "wsj.com",
    "lemonde.fr",
    "spiegel.de",
    "elpais.com",
    "corriere.it",
    "tass.com",
    "interfax.com",
    "kommersant.ru",
    "vedomosti.ru",
    "rbc.ru",
    "rferl.org",
    "bbc.com",
    "bbc.co.uk",
    "novaya.ru",
    "novayagazeta.eu",
    "balkaninsight.com",
    "kyivindependent.com",
)


_FIRECRAWL_BASE = "https://api.firecrawl.dev"


def _firecrawl_search(query: str, limit: int = 8) -> list[dict]:
    """Call Firecrawl's HTTP search endpoint directly.

    The CLI wraps this same API; calling the HTTP endpoint avoids
    needing the Node CLI on the Railway container.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        log.error("FIRECRAWL_API_KEY not set")
        return []
    try:
        r = httpx.post(
            f"{_FIRECRAWL_BASE}/v1/search",
            json={"query": query, "limit": limit},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPError as exc:
        log.warning("firecrawl HTTP error for %r: %s", query, exc)
        return []
    # The v1 API returns either {"data": [...]} or {"data": {"web": [...]}}.
    body = data.get("data") or {}
    if isinstance(body, list):
        return body
    return body.get("web") or []


def _score(results: list[dict]) -> tuple[int, int]:
    """Return (raw_count, mainstream_count)."""
    mainstream = 0
    for r in results:
        url = (r.get("url") or "").lower()
        if any(h in url for h in MAINSTREAM_HOSTS):
            mainstream += 1
    return len(results), mainstream


@app.command()
def main(
    enriched_csv: Path = typer.Argument(
        ..., help="Input CSV (output of `enrich_match_with_dob.py`)."
    ),
    out_csv: Path | None = typer.Option(
        None,
        "--out",
        help="Destination CSV. Defaults to `<input-stem>_scored.csv`.",
    ),
    exact_only: bool = typer.Option(
        True,
        "--exact-only/--all",
        help="Score only exact-normalized-name matches (default; the high-confidence slice).",
    ),
    dob_ok_only: bool = typer.Option(
        False,
        "--dob-ok-only",
        help="Only score rows where DOB confirms identity (both_present_year_match or ref/target_only).",
    ),
    delay: float = typer.Option(
        0.5, "--delay", help="Pause between Firecrawl requests, in seconds."
    ),
) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    df = pl.read_csv(enriched_csv)
    log.info("rows: %d", df.height)

    df_filt = df
    if exact_only:
        df_filt = df_filt.filter(pl.col("target_normalized_name") == pl.col("ref_normalized_name"))
    if dob_ok_only and "dob_match" in df.columns:
        df_filt = df_filt.filter(
            pl.col("dob_match").is_in(["both_present_year_match", "ref_only", "target_only"])
        )
    log.info("after filters: %d candidate rows", df_filt.height)

    # Dedupe to (name, country) tuples to minimise Firecrawl credits.
    uniq = df_filt.unique(subset=["target_normalized_name", "target_country"]).select(
        ["target_name", "target_country"]
    )
    log.info("unique candidates to score: %d", uniq.height)

    coverage: dict[tuple[str, str | None], tuple[int, int]] = {}
    for i, r in enumerate(uniq.iter_rows(named=True)):
        nm = r["target_name"]
        country = r["target_country"]
        query = f'"{nm}" sanctions OR offshore OR investigation'
        log.info("[%d/%d] %s (%s)", i + 1, uniq.height, nm, country or "?")
        results = _firecrawl_search(query)
        coverage[(nm, country)] = _score(results)
        if delay > 0:
            time.sleep(delay)

    cov_n = {k: v[0] for k, v in coverage.items()}
    cov_m = {k: v[1] for k, v in coverage.items()}

    def cov_lookup(nm: str, country: str | None, dim: int) -> int | None:
        key = (nm, country)
        d = cov_n if dim == 0 else cov_m
        return d.get(key)

    enriched = df.with_columns(
        pl.struct(["target_name", "target_country"])
        .map_elements(
            lambda d: cov_lookup(d["target_name"], d["target_country"], 0),
            return_dtype=pl.Int64,
        )
        .alias("prior_coverage_n"),
        pl.struct(["target_name", "target_country"])
        .map_elements(
            lambda d: cov_lookup(d["target_name"], d["target_country"], 1),
            return_dtype=pl.Int64,
        )
        .alias("prior_coverage_mainstream"),
    )

    out = out_csv or enriched_csv.with_name(enriched_csv.stem + "_scored.csv")
    enriched.sort(
        ["prior_coverage_mainstream", "prior_coverage_n"], descending=False, nulls_last=True
    ).write_csv(out)
    log.info("wrote %s", out)
    print(str(out))


if __name__ == "__main__":
    app()
