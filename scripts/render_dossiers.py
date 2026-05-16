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

# Honorifics dropped at display time. Source `normalized_name` doesn't strip
# these, so the rare-name set ends up with "mr foo bar" and "foo bar" as
# separate entries. We display the stripped form and merge index rows that
# collide on it, taking the higher-scoring row's dossier link as the survivor.
_HONORIFICS = frozenset(
    {"mr", "mrs", "ms", "miss", "dr", "sir", "lord", "lady", "sheikh", "prof", "hon", "rev"}
)


def _display_name(rare_name: str) -> str:
    """Strip leading honorific tokens. Display-time only — slug uses raw input."""
    tokens = rare_name.split()
    while tokens and tokens[0].lower().rstrip(".") in _HONORIFICS:
        tokens.pop(0)
    return " ".join(tokens) if tokens else rare_name


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

    display = _display_name(rare_name)
    body = [
        f"# {display}",
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
    ]
    if display != rare_name:
        body.append(
            f"_Normalized name in source data: `{rare_name}` — honorifics stripped for display._"
        )
        body.append("")

    # Address overlap rollup — surface shared-address shell clusters explicitly
    # before listing companies individually. Spec promised this; renderer
    # didn't do it in v1.
    if expanded.height > 0:
        addr_groups = (
            expanded.filter(
                pl.col("company_normalized_address").is_not_null()
                & (pl.col("company_normalized_address").str.len_chars() > 0)
            )
            .group_by("company_normalized_address")
            .agg(
                pl.col("company_name").unique().alias("companies"),
                pl.col("company_jurisdiction").unique().alias("jurisdictions"),
            )
            .filter(pl.col("companies").list.len() >= 2)
            .sort(by=pl.col("companies").list.len(), descending=True)
        )
        if addr_groups.height > 0:
            body.append("## Shared-address shell clusters")
            body.append("")
            body.append(
                "_Multiple ICIJ-linked companies registered at the same address — the "
                "shell-network shape the spec was designed to surface._"
            )
            body.append("")
            for grp in addr_groups.to_dicts():
                addr = grp["company_normalized_address"][:100]
                companies = "; ".join(grp["companies"])
                juris = ", ".join(j for j in grp["jurisdictions"] if j) or "—"
                body.append(
                    f"- `{addr}` ({juris}) — {len(grp['companies'])} companies: {companies}"
                )
            body.append("")

    body.append("## Linked entities by source")
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
                ["company_name", "company_jurisdiction", "company_normalized_address"]
            ).unique().to_dicts():
                body.append(
                    f"- {c['company_name']} ({c['company_jurisdiction'] or '—'}) — "
                    f"address: `{(c['company_normalized_address'] or '—')[:80]}`"
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
        degree_capped = bool(rows.select(pl.col("degree_capped").any()).item())

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
                "display": _display_name(rare_name),
                "slug": slug,
                "sources": rows.select("person_source").unique().height,
                "companies": n_companies,
                "jurisdictions": n_juris,
                "hits_offshore": n_offshore,
                "score": score,
                "pinned": pinned,
                "degree_capped": degree_capped,
            }
        )

    # Merge index rows that collapse to the same display name (e.g. "mr foo bar"
    # and "foo bar"). Keep the highest-scoring row's dossier link as the
    # canonical one; orphan the other dossier file (it stays on disk and
    # surfaces in the orphaned-dossier footer).
    by_display: dict[str, dict[str, Any]] = {}
    for r in index_rows:
        existing = by_display.get(r["display"])
        if existing is None or r["score"] > existing["score"]:
            by_display[r["display"]] = r
    index_rows = list(by_display.values())

    # Sort: pinned first, then score DESC, then display name for stable diffs.
    index_rows.sort(key=lambda r: (-int(r["pinned"]), -r["score"], r["display"]))

    n_degree_capped = sum(1 for r in index_rows if r["degree_capped"])

    # Render the index.
    idx = [
        "# Exposé candidates — rare cross-source officer overlaps",
        "",
        f"_Generated {now} from `processed/rare_officer_dossiers.parquet` + `search_results.json`._",
        "",
        "Score is a triage signal, not a verdict — open each dossier and judge.",
        "📌 = auto-pinned (zero web mentions + ≥3 linked companies).",
        "⚠️ = ICIJ edge fan-out truncated by `--max-degree`; dossier is partial.",
        "",
        f"**Run notes:** {n_degree_capped} of {len(index_rows)} dossiers degree-capped. "
        "Sanctions-adjacency column dropped from the index — the current join only "
        "resolves for OS-sourced linked companies, which never overlap with the ICIJ-"
        "walked set; column was zero across the board (see follow-up phase 2).",
        "",
        "| Rank | Name | Sources | Companies | Juris | Web hits (offshore) | Score | Dossier |",
        "|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(index_rows, start=1):
        pin = "📌 " if r["pinned"] else ""
        cap = " ⚠️" if r["degree_capped"] else ""
        safe_name = r["display"].replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")
        idx.append(
            f"| {i} | {pin}{safe_name}{cap} | {r['sources']} | {r['companies']} | "
            f"{r['jurisdictions']} | {r['hits_offshore']} | "
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
