"""2-hop expansion from a single seed entity.

    uv run python scripts/expand_2hop.py --entity-uid icij:82004676 \
        --label "liquid_funding"

For a seed company entity_uid:

    seed_co --officer/intermediary_of--> persons
    persons --officer/intermediary_of--> other_companies

Surfaces every *other* company that shares an officer / intermediary
with the seed. The classic "co-director graph" walk — useful for
expanding a single confirmed lead into its first-degree corporate
neighbourhood without re-investigating every officer individually.

Emits a markdown report at
``reports/investigations/expansions/<label>_2hop.md``.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import typer

from shellnet.investigations.seed_query import _md_escape
from shellnet.paths import INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT

app = typer.Typer(add_completion=False, no_args_is_help=True)
log = logging.getLogger(__name__)

# Officer names that are themselves entities, not natural persons. The
# patterns are intentionally conservative — we'd rather keep an ambiguous
# row than silently drop a lead.
_COMPANY_SHAPED_SUFFIXES = re.compile(
    r"\b(ltd|limited|inc|incorporated|llc|llp|lp|plc|corp|corporation|"
    r"company|gmbh|ag|sa|bv|nv|trust|foundation|holdings|holding|"
    r"services|llc\.|ltd\.|inc\.|sarl|s\.a\.|associates)\b",
    re.IGNORECASE,
)
_PROVIDER_HINTS = re.compile(
    r"\b(appleby|mossfon|mossack|trident|maples|alemán|aleman|ocra|"
    r"pricewaterhousecoopers|pwc|deloitte|kpmg|ernst\s*&?\s*young|"
    r"bdo|grant\s*thornton)\b",
    re.IGNORECASE,
)


def _is_named_individual(person_name: str | None, kind: str | None) -> bool:
    """Heuristic: keep officers whose name doesn't look like a corporate entity.

    We drop rows where the person's name has a legal suffix (Ltd, LLC, …)
    or matches a known provider firm. Conservative — anything we can't
    classify confidently is kept.
    """
    if (kind or "").lower() == "intermediary":
        return False
    if not person_name:
        return True  # Can't classify; keep.
    if _COMPANY_SHAPED_SUFFIXES.search(person_name):
        return False
    return not _PROVIDER_HINTS.search(person_name)


@app.command()
def main(
    entity_uid: str = typer.Option(..., "--entity-uid"),
    label: str = typer.Option(..., "--label", help="Short slug for the output filename."),
    processed_dir: Path = typer.Option(PROCESSED_DIR, "--processed-dir"),
    interim_dir: Path = typer.Option(INTERIM_DIR, "--interim-dir"),
    out_dir: Path = typer.Option(
        PROJECT_ROOT / "reports" / "investigations" / "expansions",
        "--out-dir",
    ),
    person_limit: int = typer.Option(50, "--person-limit"),
    company_limit_per_person: int = typer.Option(25, "--company-limit-per-person"),
    named_individuals_only: bool = typer.Option(
        False,
        "--named-individuals-only",
        help="Drop officers that look like corporate providers (Appleby, "
        "PwC, etc.) or carry corporate legal suffixes (Ltd, LLC). Big "
        "noise reducer when the seed is anchored at an offshore provider.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    edges_path = interim_dir / "icij_edges.parquet"
    if not edges_path.exists():
        raise typer.BadParameter(f"missing {edges_path}")
    edges = pl.read_parquet(edges_path)
    companies = pl.read_parquet(processed_dir / "company_entities.parquet")
    persons = pl.read_parquet(processed_dir / "person_entities.parquet")

    person_kinds = "officer|intermediary|shareholder|beneficial"

    # Hop 1: seed → persons.
    hop1 = edges.filter(
        ((pl.col("src_node") == entity_uid) | (pl.col("dst_node") == entity_uid))
        & pl.col("kind_raw").str.to_lowercase().str.contains(person_kinds, literal=False)
    )
    log.info("hop 1: %d edge(s) from seed to person-shaped nodes", hop1.height)

    seed_row = companies.filter(pl.col("entity_uid") == entity_uid)
    seed_name = (
        seed_row.to_dicts()[0].get("name") if seed_row.height else entity_uid
    )

    person_uids: list[str] = []
    for e in hop1.to_dicts():
        other = e["dst_node"] if e["src_node"] == entity_uid else e["src_node"]
        if other not in person_uids:
            person_uids.append(other)
    person_uids = person_uids[:person_limit]
    log.info("walking %d distinct person uids", len(person_uids))

    person_by_uid = {
        r["entity_uid"]: r
        for r in persons.filter(pl.col("entity_uid").is_in(person_uids)).to_dicts()
    }
    if named_individuals_only:
        before = len(person_uids)
        person_uids = [
            uid
            for uid in person_uids
            if _is_named_individual(
                (person_by_uid.get(uid) or {}).get("name"),
                (person_by_uid.get(uid) or {}).get("kind"),
            )
        ]
        log.info(
            "named-individuals-only: kept %d / %d officers", len(person_uids), before
        )
    company_by_uid: dict[str, dict] = {}

    # Hop 2: persons → other companies (excluding the seed itself).
    hop2 = edges.filter(
        (pl.col("src_node").is_in(person_uids) | pl.col("dst_node").is_in(person_uids))
        & pl.col("kind_raw").str.to_lowercase().str.contains(person_kinds, literal=False)
    )
    log.info("hop 2: %d total person→entity edge(s)", hop2.height)

    # (other_company_uid) → list of (person_uid, role, kind, leak, start, end)
    co_shared: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()  # (person, other_co) — count one edge per pair max
    for e in hop2.to_dicts():
        src = e["src_node"]
        dst = e["dst_node"]
        person = src if src in person_by_uid else dst
        other = dst if person == src else src
        if other == entity_uid:
            continue
        if (person, other) in seen and len(co_shared[other]) >= company_limit_per_person:
            continue
        seen.add((person, other))
        co_shared[other].append(
            {
                "person_uid": person,
                "person_name": (person_by_uid.get(person) or {}).get("name", ""),
                "kind_raw": e.get("kind_raw"),
                "role": e.get("role"),
                "start": e.get("start_date") or "",
                "end": e.get("end_date") or "",
                "leak": e.get("source_label") or "",
            }
        )

    # Resolve other-company names in bulk.
    other_uids = list(co_shared.keys())
    if other_uids:
        for r in companies.filter(pl.col("entity_uid").is_in(other_uids)).to_dicts():
            company_by_uid[r["entity_uid"]] = r

    # Sort other companies by shared-officer count (desc).
    ranked = sorted(
        co_shared.items(), key=lambda kv: (-len({s["person_uid"] for s in kv[1]}), kv[0])
    )

    # Build markdown.
    lines: list[str] = []
    lines.append(f"# 2-hop expansion: `{label}`")
    lines.append("")
    lines.append(
        f"Seed entity: `{entity_uid}` (`{_md_escape(seed_name)}`)"
    )
    lines.append("")
    lines.append(
        "Walks: seed → persons (officer / intermediary / shareholder / "
        "beneficial-owner edges) → other companies those persons are "
        "attached to. Surfaces every entity that shares at least one "
        "officer-class link with the seed."
    )
    lines.append("")
    lines.append(
        "> **Hypothesis, not proof.** A shared director is a lead. "
        "It does not imply common control, shared beneficial ownership, "
        "or wrongdoing. Confirm identity (DOB, address, multiple "
        "filings) before drawing conclusions."
    )
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- {len(person_uids)} person(s) attached to seed.")
    lines.append(
        f"- {len(co_shared)} *other* company(ies) share at least one of those persons."
    )
    distinct_persons_used = len({s["person_uid"] for v in co_shared.values() for s in v})
    lines.append(f"- {distinct_persons_used} of seed's persons appear elsewhere in ICIJ.")
    lines.append("")

    lines.append("## Seed's officer-class neighbours")
    lines.append("")
    if not person_uids:
        lines.append("_None._")
    else:
        lines.append("| person_uid | name | country | kind |")
        lines.append("| --- | --- | --- | --- |")
        for pu in person_uids:
            p = person_by_uid.get(pu) or {}
            lines.append(
                "| `{u}` | `{n}` | {c} | {k} |".format(
                    u=pu,
                    n=_md_escape(p.get("name"))[:60],
                    c=p.get("country") or "?",
                    k=p.get("kind") or "?",
                )
            )
    lines.append("")

    lines.append("## Other companies sharing officer-class links")
    lines.append("")
    if not ranked:
        lines.append("_No other ICIJ companies share an officer with the seed._")
    else:
        lines.append(
            "Ranked by number of distinct shared persons (desc). Showing all rows."
        )
        lines.append("")
        lines.append(
            "| other_company_uid | name | jur | shared_persons | shared_with |"
        )
        lines.append("| --- | --- | --- | ---: | --- |")
        for other_uid, shares in ranked:
            co = company_by_uid.get(other_uid) or {}
            persons_set = sorted(
                {(s["person_uid"], s["person_name"]) for s in shares}
            )
            persons_label = ", ".join(
                f"`{u}`" for u, _ in persons_set[:4]
            ) + ("…" if len(persons_set) > 4 else "")
            lines.append(
                "| `{u}` | `{n}` | {j} | {k} | {p} |".format(
                    u=other_uid,
                    n=_md_escape(co.get("name"))[:60],
                    j=co.get("jurisdiction") or "?",
                    k=len(persons_set),
                    p=persons_label,
                )
            )
    lines.append("")

    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Seed entity_uid: `{entity_uid}`")
    lines.append(f"- Edges read from: `{edges_path}`")
    lines.append(
        f"- Generated: `{datetime.now(UTC).isoformat(timespec='seconds')}`"
    )
    lines.append("")

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{label}_2hop.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s", target)
    print(str(target))


if __name__ == "__main__":
    app()
