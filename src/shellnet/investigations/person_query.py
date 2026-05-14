"""Person-side seed-query workflow.

Given a person name (e.g. ``"Jeffrey Epstein"``), rank rows in the
unified person table by RapidFuzz token-sort score, then for each
matched ICIJ person walk officer-of / intermediary-of edges back to the
company table to surface every entity the person is attached to.

Shares the same normalize / md-escape / report-rendering style as
``seed_query.py`` but keeps the dataclasses separate because persons
don't have LEIs / company numbers / addresses on the row itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from shellnet.investigations.seed_query import _md_escape, _score_row, _slugify
from shellnet.normalize import normalize_company_name, normalize_jurisdiction


@dataclass(frozen=True)
class PersonSeed:
    name: str
    country: str | None
    normalized_name: str
    normalized_country: str | None


@dataclass
class PersonCandidate:
    entity_uid: str
    source: str
    kind: str  # "officer", "intermediary", "person"
    name: str
    normalized_name: str
    country: str | None
    topics: list[str]
    datasets: list[str]
    score: float
    exact_normalized: bool
    in_country: bool


@dataclass
class CompanyEdge:
    """One officer-of / intermediary-of edge from an ICIJ person to a company."""

    person_uid: str
    company_uid: str
    kind_raw: str | None
    role: str | None
    start_date: str | None
    end_date: str | None
    leak: str | None
    company_name: str | None
    company_jurisdiction: str | None
    company_source: str | None


def make_person_seed(name: str, country: str | None) -> PersonSeed:
    return PersonSeed(
        name=name,
        country=country,
        normalized_name=normalize_company_name(name),
        normalized_country=normalize_jurisdiction(country) if country else None,
    )


def rank_person_candidates(
    person_df: pl.DataFrame,
    seed: PersonSeed,
    *,
    top_n: int = 25,
    min_score: float = 90.0,
    include_outside_country: bool = True,
) -> tuple[list[PersonCandidate], list[PersonCandidate]]:
    """Score every row in ``person_df`` against the seed.

    Returns ``(in_country, outside_country)``. Person matching defaults
    to a higher floor than company matching (90 not 85) because personal
    names collide much more aggressively in the offshore-leaks corpus.
    """
    if person_df.height == 0 or not seed.normalized_name:
        return [], []

    norm = person_df.get_column("normalized_name").to_list()
    scores = [_score_row(seed.normalized_name, n) for n in norm]
    sdf = person_df.with_columns(pl.Series("_score", scores))
    sdf = sdf.filter(pl.col("_score") >= min_score)
    if sdf.height == 0:
        return [], []

    have_country = seed.normalized_country is not None

    def _to_candidates(df: pl.DataFrame, in_country: bool) -> list[PersonCandidate]:
        out: list[PersonCandidate] = []
        for r in df.to_dicts():
            nname = r.get("normalized_name") or ""
            out.append(
                PersonCandidate(
                    entity_uid=r["entity_uid"],
                    source=r.get("source") or "?",
                    kind=r.get("kind") or "?",
                    name=r.get("name") or "",
                    normalized_name=nname,
                    country=r.get("country"),
                    topics=list(r.get("topics") or []),
                    datasets=list(r.get("datasets") or []),
                    score=float(r["_score"]),
                    exact_normalized=(nname == seed.normalized_name),
                    in_country=in_country,
                )
            )
        out.sort(
            key=lambda c: (
                not c.exact_normalized,
                -c.score,
                c.source != "opensanctions",  # OFAC/PEP-tagged people first
                c.kind != "officer",  # officers before intermediaries
            )
        )
        return out[:top_n]

    if not have_country:
        return _to_candidates(sdf, in_country=True), []

    in_df = sdf.filter(pl.col("country") == seed.normalized_country)
    out_df = sdf.filter(
        (pl.col("country") != seed.normalized_country) | pl.col("country").is_null()
    )
    in_results = _to_candidates(in_df, in_country=True)
    out_results = _to_candidates(out_df, in_country=False) if include_outside_country else []
    return in_results, out_results


def collect_company_edges(
    person_uids: list[str],
    *,
    edges_df: pl.DataFrame | None,
    company_df: pl.DataFrame | None,
    per_person_limit: int = 50,
) -> dict[str, list[CompanyEdge]]:
    """For each ICIJ person uid, return all edges that point at a company.

    Edges are filtered to ``kind_raw`` containing 'officer', 'intermediary',
    'shareholder', or 'beneficial' — the relations that actually attach a
    natural person to a company.
    """
    if not person_uids or edges_df is None or edges_df.height == 0:
        return {}

    company_by_uid: dict[str, dict[str, Any]] = {}
    if company_df is not None and company_df.height:
        for r in company_df.to_dicts():
            uid = r.get("entity_uid")
            if isinstance(uid, str):
                company_by_uid[uid] = r

    relevant = edges_df.filter(
        pl.col("kind_raw")
        .str.to_lowercase()
        .str.contains("officer|intermediary|shareholder|beneficial", literal=False)
    )
    out: dict[str, list[CompanyEdge]] = {}
    for uid in person_uids:
        sub = relevant.filter((pl.col("src_node") == uid) | (pl.col("dst_node") == uid))
        if sub.height == 0:
            continue
        rows: list[CompanyEdge] = []
        for e in sub.head(per_person_limit).to_dicts():
            other = e["dst_node"] if e["src_node"] == uid else e["src_node"]
            co = company_by_uid.get(other) or {}
            rows.append(
                CompanyEdge(
                    person_uid=uid,
                    company_uid=other,
                    kind_raw=e.get("kind_raw"),
                    role=e.get("role"),
                    start_date=e.get("start_date") or None,
                    end_date=e.get("end_date") or None,
                    leak=e.get("source_label"),
                    company_name=co.get("name"),
                    company_jurisdiction=co.get("jurisdiction"),
                    company_source=co.get("source"),
                )
            )
        out[uid] = rows
    return out


def render_person_report(
    seed: PersonSeed,
    *,
    in_country: list[PersonCandidate],
    outside_country: list[PersonCandidate],
    edges_by_person: dict[str, list[CompanyEdge]],
    inputs_meta: dict[str, Any],
    source_note: str | None = None,
    generated_at: datetime | None = None,
    batch_id: str | None = None,
) -> str:
    """Build the person-investigation markdown report."""
    generated_at = generated_at or datetime.now(UTC)
    lines: list[str] = []
    country_label = seed.normalized_country or "(unspecified)"
    lines.append(f"# Person investigation: `{_md_escape(seed.name)}` / {country_label}")
    lines.append("")
    lines.append(
        f"Generated `{generated_at.isoformat(timespec='seconds')}`"
        + (f" as part of batch `{batch_id}`" if batch_id else "")
        + ". Person-side seed-query workflow over the unified person table."
    )
    lines.append("")
    if source_note:
        lines.append(f"**Seed source:** {_md_escape(source_note)}")
        lines.append("")
    lines.append(
        "> **Hypothesis, not proof.** Personal names collide aggressively in "
        "the offshore-leaks corpus. A name match is a lead to verify, not a "
        "claim that the named officer is the same individual as the seed. "
        "Confirm with DOB, address, or independent filings before relying on "
        "any row below."
    )
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    if in_country:
        top = in_country[0]
        lines.append(
            f"- Best in-country candidate: `{top.entity_uid}` "
            f"(`{_md_escape(top.name)}`, {top.country or '?'}, "
            f"score {top.score:.1f}, kind={top.kind})"
        )
    else:
        lines.append("- No same-country candidates above the score threshold.")
    if outside_country:
        lines.append(f"- {len(outside_country)} candidate(s) in a different / unknown country.")
    total_edges = sum(len(v) for v in edges_by_person.values())
    lines.append(
        f"- {total_edges} person→company edge(s) across {len(edges_by_person)} matched person(s)."
    )
    lines.append("")

    def _person_table(rows: list[PersonCandidate], header: str) -> None:
        lines.append(header)
        lines.append("")
        if not rows:
            lines.append("_None._")
            lines.append("")
            return
        lines.append("| # | score | exact | entity_uid | source | kind | name | country | topics |")
        lines.append("| ---: | ---: | :-: | --- | --- | --- | --- | --- | --- |")
        for i, c in enumerate(rows, start=1):
            lines.append(
                "| {i} | {sc:.1f} | {ex} | `{uid}` | {src} | {k} | `{nm}` | {co} | {tp} |".format(
                    i=i,
                    sc=c.score,
                    ex="✓" if c.exact_normalized else "",
                    uid=c.entity_uid,
                    src=c.source,
                    k=c.kind,
                    nm=_md_escape(c.name)[:50],
                    co=c.country or "?",
                    tp=", ".join(c.topics) if c.topics else "",
                )
            )
        lines.append("")

    _person_table(in_country, "## Candidate persons (same country)")
    if outside_country:
        _person_table(
            outside_country,
            "## Candidate persons (different / unknown country)",
        )

    lines.append("## Companies attached to matched persons")
    lines.append("")
    if not edges_by_person:
        lines.append("_No officer-of / intermediary-of / shareholder edges found._")
    else:
        for person_uid, edges in edges_by_person.items():
            lines.append(f"### `{person_uid}` — {len(edges)} edge(s)")
            lines.append("")
            lines.append(
                "| company_uid | name | jur | source | kind_raw | role | start | end | leak |"
            )
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
            for e in edges:
                lines.append(
                    "| `{cu}` | `{nm}` | {jur} | {src} | {k} | {r} | {s} | {ed} | {lk} |".format(
                        cu=e.company_uid,
                        nm=_md_escape(e.company_name)[:60],
                        jur=e.company_jurisdiction or "?",
                        src=e.company_source or "?",
                        k=_md_escape(e.kind_raw)[:25],
                        r=_md_escape(e.role)[:30],
                        s=e.start_date or "",
                        ed=e.end_date or "",
                        lk=_md_escape(e.leak)[:25],
                    )
                )
            lines.append("")

    lines.append("## Review notes")
    lines.append("")
    if in_country and in_country[0].exact_normalized:
        lines.append(
            "- Top candidate is an exact normalized-name match. Strong lead, "
            "but still confirm identity via DOB / address / known filings."
        )
    else:
        lines.append(
            "- No exact normalized-name match in the seed country. Treat all "
            "rows as fuzzy hypotheses."
        )
    pep_or_sanction = [c for c in in_country + outside_country if c.topics]
    if pep_or_sanction:
        lines.append(
            f"- {len(pep_or_sanction)} candidate(s) carry OpenSanctions topics "
            "(PEP / sanction / other). Review those first."
        )
    lines.append("")

    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Seed: `{_md_escape(seed.name)}` / `{seed.country or '?'}`")
    lines.append(
        f"- Seed normalized: `{seed.normalized_name}` / `{seed.normalized_country or '?'}`"
    )
    for k, v in inputs_meta.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    return "\n".join(lines)


def default_person_report_path(reports_root: Path, seed: PersonSeed) -> Path:
    country_part = (seed.normalized_country or "global").lower()
    slug = _slugify(seed.normalized_name or seed.name)
    return reports_root / "investigations" / "persons" / f"{slug}_{country_part}.md"
