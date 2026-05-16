"""Render per-lead exposé dossiers + the ranked candidate index.

Spec: docs/superpowers/specs/2026-05-16-expose-candidates-design.md
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import polars as pl
import typer

from shellnet.novelty_ranking import auto_pin, novelty_score

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(name: str) -> str:
    s = _SLUG_RE.sub("-", name.lower()).strip("-")
    if s:
        return s
    # Non-ASCII names collapse to empty. Use a short hash of the original
    # name so two non-ASCII names don't both land on "unnamed.md".
    return "x-" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:10]


def _hits_section(query: str, hits: list[dict[str, Any]]) -> str:
    if not hits:
        return f"### `{query}` — 0 hits\n_No hits._\n"
    lines = [f"### `{query}` — {len(hits)} hits"]
    for h in hits:
        title = (h.get("title") or "(no title)").replace("|", "\\|")
        url = h.get("url") or h.get("link") or ""
        snippet = (h.get("description") or h.get("snippet") or "").replace("\n", " ")
        lines.append(f"- [{title}]({url}) — _{snippet[:200]}_")
    return "\n".join(lines) + "\n"


def _render_one(
    rare_name: str,
    rows: pl.DataFrame,
    hits: dict[str, list[dict[str, Any]] | str],
    score: float,
    pinned: bool,
    now: str,
) -> str:
    expanded = rows.filter(pl.col("company_entity_uid").is_not_null())
    n_companies = expanded.select("company_entity_uid").unique().height
    jurisdictions = (
        expanded.filter(pl.col("company_jurisdiction").is_not_null())
        .select("company_jurisdiction")
        .unique()
        .to_series()
        .to_list()
    )
    sources = rows.select("person_source").unique().to_series().to_list()
    degree_capped = bool(rows.select(pl.col("degree_capped").any()).item())

    h_general = cast(list[dict[str, Any]], hits.get("general") or [])
    h_offshore = cast(list[dict[str, Any]], hits.get("offshore") or [])
    h_localized = cast(list[dict[str, Any]], hits.get("localized") or [])
    top_juris = cast(str, hits.get("dominant_jurisdiction") or "")

    body = [
        f"# {rare_name}",
        "",
        (
            f"**Sources:** {len(sources)} ({', '.join(sources)})  •  "
            f"**Linked companies:** {n_companies}  •  "
            f"**Jurisdictions:** {', '.join(jurisdictions) or '—'}  •  "
            f"**Novelty score:** {score:.2f}"
            f"{'  •  📌 **auto-pinned (no web mentions + multi-shell)**' if pinned else ''}"
            f"{'  •  ⚠️ degree-capped (partial picture)' if degree_capped else ''}"
        ),
        "",
        "## Linked entities by source",
    ]
    for src in sorted(sources):
        sub = rows.filter(pl.col("person_source") == src)
        n_ents = sub.select("person_entity_uid").unique().height
        body.append(f"### {src} ({n_ents} {'entity' if n_ents == 1 else 'entities'})")
        for r in sub.select(["person_name", "person_entity_uid", "person_country"]).unique().to_dicts():
            body.append(
                f"- {r['person_name']} — `{r['person_entity_uid']}` — country: {r['person_country'] or '—'}"
            )
        if src == "icij" and expanded.height > 0:
            body.append("")
            body.append("**Linked companies (ICIJ 2-hop walk):**")
            for c in expanded.select(
                ["company_name", "company_jurisdiction", "sanction_datasets", "company_normalized_address"]
            ).unique().to_dicts():
                sanc = c["sanction_datasets"] or "—"
                body.append(
                    f"- {c['company_name']} ({c['company_jurisdiction'] or '—'}) — "
                    f"address: `{(c['company_normalized_address'] or '—')[:80]}` — "
                    f"sanctions: {sanc}"
                )
        elif src in ("uk_psc", "opensanctions"):
            body.append(
                f"  _(stub only — no person→company relations parquet for {src} in v1)_"
            )
        body.append("")

    body.extend(
        [
            "## Web search (firecrawl, " + now.split(" ")[0] + ")",
            "",
            _hits_section(f'"{rare_name}" (shell OR offshore OR director OR PSC)', h_offshore),
            _hits_section(f'"{rare_name}"', h_general),
        ]
    )
    if top_juris:
        body.append(_hits_section(f'"{rare_name}" {top_juris}', h_localized))

    body.extend(
        [
            "## Reproduce",
            "",
            f"- `processed/rare_officer_dossiers.parquet`, filter `rare_name == \"{rare_name}\"`",
            "- Search ran via `scripts/search_dossier_freshness.py` on " + now.split(" ")[0],
        ]
    )
    return "\n".join(body) + "\n"


@app.command()
def main(
    parquet: Path = typer.Option(..., "--parquet", help="rare_officer_dossiers.parquet"),
    search_results: Path = typer.Option(..., "--search-results", help="search_results.json"),
    out_dir: Path = typer.Option(Path("docs/reports"), "--out-dir"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    df = pl.read_parquet(parquet)
    searches: dict[str, dict[str, Any]] = json.loads(search_results.read_text(encoding="utf-8"))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    dossiers_dir = out_dir / "dossiers"
    dossiers_dir.mkdir(parents=True, exist_ok=True)

    # Score each rare name + render its dossier.
    index_rows: list[dict[str, Any]] = []
    rare_names = df.select("rare_name").unique().to_series().to_list()
    written_slugs: set[str] = set()
    for rare_name in rare_names:
        rows = df.filter(pl.col("rare_name") == rare_name)
        expanded = rows.filter(pl.col("company_entity_uid").is_not_null())
        n_companies = expanded.select("company_entity_uid").unique().height
        n_juris = (
            expanded.filter(pl.col("company_jurisdiction").is_not_null())
            .select("company_jurisdiction")
            .unique()
            .height
        )
        hits = searches.get(rare_name, {"general": [], "offshore": [], "localized": [], "dominant_jurisdiction": ""})
        n_general = len(hits.get("general") or [])
        n_offshore = len(hits.get("offshore") or [])
        n_localized = len(hits.get("localized") or [])
        # localized_ran == True only when the localized query was emitted:
        # the search step writes a non-empty dominant_jurisdiction iff it
        # passed the plurality-with-margin test in search_dossier_freshness.
        localized_ran = bool(hits.get("dominant_jurisdiction"))
        n_sanc_adj = expanded.filter(pl.col("sanction_datasets").is_not_null()).height

        score = novelty_score(
            hits_general=n_general,
            hits_offshore=n_offshore,
            hits_localized=n_localized,
            localized_ran=localized_ran,
            n_linked_companies=n_companies,
            n_jurisdictions=n_juris,
        )
        pinned = auto_pin(
            hits_general=n_general,
            hits_offshore=n_offshore,
            n_linked_companies=n_companies,
        )

        slug = _slug(rare_name)
        written_slugs.add(slug)
        (dossiers_dir / f"{slug}.md").write_text(
            _render_one(rare_name, rows, hits, score, pinned, now),
            encoding="utf-8",
        )
        index_rows.append(
            {
                "name": rare_name,
                "slug": slug,
                "sources": rows.select("person_source").unique().height,
                "companies": n_companies,
                "jurisdictions": n_juris,
                "sanc_adj": n_sanc_adj,
                "hits_offshore": n_offshore,
                "score": score,
                "pinned": pinned,
            }
        )

    # Sort: pinned first, then score DESC.
    index_rows.sort(key=lambda r: (-int(r["pinned"]), -r["score"], r["name"]))

    # Render the index.
    idx = [
        "# Exposé candidates — rare cross-source officer overlaps",
        "",
        f"_Generated {now} from `processed/rare_officer_dossiers.parquet` + `search_results.json`._",
        "",
        "Score is a triage signal, not a verdict — open each dossier and judge.",
        "📌 = auto-pinned (zero web mentions + ≥3 linked companies).",
        "",
        "| Rank | Name | Sources | Companies | Juris | Sanctions adj | Web hits (offshore) | Score | Dossier |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(index_rows, start=1):
        pin = "📌 " if r["pinned"] else ""
        safe_name = r["name"].replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")
        idx.append(
            f"| {i} | {pin}{safe_name} | {r['sources']} | {r['companies']} | "
            f"{r['jurisdictions']} | {r['sanc_adj']} | {r['hits_offshore']} | "
            f"{r['score']:.2f} | [→](dossiers/{r['slug']}.md) |"
        )

    # Orphaned dossiers footer.
    existing = {p.stem for p in dossiers_dir.glob("*.md")}
    orphans = sorted(existing - written_slugs)
    if orphans:
        idx.append("")
        idx.append("## Orphaned dossiers")
        idx.append("")
        idx.append("_These dossiers were rendered by a previous run but fell out of the current top-N._")
        idx.append("")
        for slug in orphans:
            idx.append(f"- [`{slug}`](dossiers/{slug}.md)")

    (out_dir / "exposes_candidates.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    typer.echo(f"Wrote: {out_dir}/exposes_candidates.md")
    typer.echo(f"  + {len(written_slugs)} dossier .md files in {dossiers_dir}")


if __name__ == "__main__":
    app()
