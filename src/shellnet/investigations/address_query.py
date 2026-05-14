"""Address-side seed-query workflow.

Given a free-text address (e.g. ``"9 East 71st Street, New York"``),
find every row in the unified address table whose ``normalized_text``
fuzzily matches, then surface which *entities* are registered at those
addresses via the ``source_id`` join back into the company table.

Shared-address overlap is a classic shell-company-network signal —
multiple entities at the same registered agent address is exactly the
pattern that warrants human review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from shellnet.investigations.seed_query import _md_escape, _score_row, _slugify
from shellnet.normalize import normalize_address_text, normalize_jurisdiction


@dataclass(frozen=True)
class AddressSeed:
    text: str
    country: str | None
    normalized_text: str
    normalized_country: str | None


@dataclass
class AddressCandidate:
    address_uid: str
    source: str
    source_id: str
    raw_text: str
    normalized_text: str
    country: str | None
    score: float
    exact_normalized: bool
    in_country: bool


@dataclass
class EntityAtAddress:
    """One entity whose row in the company table points at this address."""

    entity_uid: str
    name: str
    jurisdiction: str | None
    source: str
    address_uid: str
    address_raw: str | None


def make_address_seed(text: str, country: str | None) -> AddressSeed:
    return AddressSeed(
        text=text,
        country=country,
        normalized_text=normalize_address_text(text),
        normalized_country=normalize_jurisdiction(country) if country else None,
    )


def rank_addresses(
    address_df: pl.DataFrame,
    seed: AddressSeed,
    *,
    top_n: int = 25,
    min_score: float = 85.0,
    include_outside_country: bool = True,
) -> tuple[list[AddressCandidate], list[AddressCandidate]]:
    """Score address rows against the seed text via token_sort_ratio."""
    if address_df.height == 0 or not seed.normalized_text:
        return [], []

    # Pre-filter on first token to keep scoring tractable on ~700k rows.
    first_token = seed.normalized_text.split(" ", 1)[0] if seed.normalized_text else ""
    block = address_df
    if first_token:
        block = block.filter(pl.col("normalized_text").str.contains(first_token, literal=True))
    if block.height == 0:
        # Fall back to the full table if blocking dropped everything (rare).
        block = address_df

    norm = block.get_column("normalized_text").to_list()
    scores = [_score_row(seed.normalized_text, n) for n in norm]
    sdf = block.with_columns(pl.Series("_score", scores))
    sdf = sdf.filter(pl.col("_score") >= min_score)
    if sdf.height == 0:
        return [], []

    have_country = seed.normalized_country is not None

    def _to_candidates(df: pl.DataFrame, in_country: bool) -> list[AddressCandidate]:
        out: list[AddressCandidate] = []
        for r in df.to_dicts():
            nt = r.get("normalized_text") or ""
            out.append(
                AddressCandidate(
                    address_uid=r["address_uid"],
                    source=r.get("source") or "?",
                    source_id=r.get("source_id") or "",
                    raw_text=r.get("raw_text") or "",
                    normalized_text=nt,
                    country=r.get("country"),
                    score=float(r["_score"]),
                    exact_normalized=(nt == seed.normalized_text),
                    in_country=in_country,
                )
            )
        out.sort(
            key=lambda c: (not c.exact_normalized, -c.score),
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


def collect_entities_at_addresses(
    addresses: list[AddressCandidate],
    *,
    company_df: pl.DataFrame | None,
    edges_df: pl.DataFrame | None,
    per_address_limit: int = 100,
) -> dict[str, list[EntityAtAddress]]:
    """For each matched address, return the entities registered there.

    There are two ways an entity attaches to an address:

      1. Its own ``company_entities`` row has ``address_raw`` set — the
         address_table row's ``source_id`` is that entity's source_id.
      2. ICIJ has a ``registered_address``-class edge from the entity to
         a separate ICIJ address node.

    We surface both, deduped by ``entity_uid``.
    """
    out: dict[str, list[EntityAtAddress]] = {}
    if not addresses:
        return out

    # Path 1: direct join — the source_id on the address row is the entity's
    # source_id (per build_address_table semantics).
    if company_df is not None and company_df.height:
        for addr in addresses:
            uid = f"{addr.source}:{addr.source_id}"
            row = company_df.filter(pl.col("entity_uid") == uid)
            if row.height:
                r = row.to_dicts()[0]
                out.setdefault(addr.address_uid, []).append(
                    EntityAtAddress(
                        entity_uid=uid,
                        name=r.get("name") or "",
                        jurisdiction=r.get("jurisdiction"),
                        source=addr.source,
                        address_uid=addr.address_uid,
                        address_raw=addr.raw_text,
                    )
                )

    # Path 2: ICIJ registered_address edges — the address-node uid is the
    # entity_uid of the address itself, and edges point company → address.
    if edges_df is not None and edges_df.height:
        icij_address_uids = [f"icij:{a.source_id}" for a in addresses if a.source == "icij"]
        if icij_address_uids:
            addr_edges = edges_df.filter(
                pl.col("kind_raw").str.to_lowercase().str.contains("address", literal=False)
                & (
                    pl.col("dst_node").is_in(icij_address_uids)
                    | pl.col("src_node").is_in(icij_address_uids)
                )
            )
            uid_to_addr_uid: dict[str, str] = {}
            for a in addresses:
                if a.source == "icij":
                    uid_to_addr_uid[f"icij:{a.source_id}"] = a.address_uid
            seen: set[tuple[str, str]] = set()
            company_by_uid: dict[str, dict[str, Any]] = {}
            if company_df is not None:
                for r in company_df.to_dicts():
                    cu = r.get("entity_uid")
                    if isinstance(cu, str):
                        company_by_uid[cu] = r
            for e in addr_edges.to_dicts():
                a_uid = e["dst_node"] if e["dst_node"] in uid_to_addr_uid else e["src_node"]
                entity_uid = e["src_node"] if a_uid == e["dst_node"] else e["dst_node"]
                addr_uid = uid_to_addr_uid.get(a_uid)
                if addr_uid is None or (entity_uid, addr_uid) in seen:
                    continue
                seen.add((entity_uid, addr_uid))
                co = company_by_uid.get(entity_uid) or {}
                bucket = out.setdefault(addr_uid, [])
                if len(bucket) >= per_address_limit:
                    continue
                bucket.append(
                    EntityAtAddress(
                        entity_uid=entity_uid,
                        name=co.get("name") or "",
                        jurisdiction=co.get("jurisdiction"),
                        source=entity_uid.split(":", 1)[0],
                        address_uid=addr_uid,
                        address_raw=next(
                            (a.raw_text for a in addresses if a.address_uid == addr_uid),
                            None,
                        ),
                    )
                )
    return out


def render_address_report(
    seed: AddressSeed,
    *,
    in_country: list[AddressCandidate],
    outside_country: list[AddressCandidate],
    entities_by_address: dict[str, list[EntityAtAddress]],
    inputs_meta: dict[str, Any],
    source_note: str | None = None,
    generated_at: datetime | None = None,
    batch_id: str | None = None,
) -> str:
    generated_at = generated_at or datetime.now(UTC)
    lines: list[str] = []
    country_label = seed.normalized_country or "(unspecified)"
    lines.append(f"# Address investigation: `{_md_escape(seed.text)[:80]}` / {country_label}")
    lines.append("")
    lines.append(
        f"Generated `{generated_at.isoformat(timespec='seconds')}`"
        + (f" as part of batch `{batch_id}`" if batch_id else "")
        + ". Address-side seed-query workflow over the unified address table."
    )
    lines.append("")
    if source_note:
        lines.append(f"**Seed source:** {_md_escape(source_note)}")
        lines.append("")
    lines.append(
        "> **Hypothesis, not proof.** Addresses are noisy; matches reflect "
        "string similarity, not verified street identity. Shared-address "
        "overlap is a *signal* worth investigating, not a finding."
    )
    lines.append("")

    total_entities = sum(len(v) for v in entities_by_address.values())
    distinct_entities = len(
        {e.entity_uid for bucket in entities_by_address.values() for e in bucket}
    )
    lines.append("## Summary")
    lines.append("")
    if in_country:
        top = in_country[0]
        lines.append(
            f"- Best in-country candidate: `{top.address_uid}` "
            f"(score {top.score:.1f}, country {top.country or '?'})"
        )
    else:
        lines.append("- No same-country candidates above the score threshold.")
    lines.append(
        f"- {len(in_country) + len(outside_country)} matched address row(s) "
        f"→ {distinct_entities} distinct entity registration(s) "
        f"(across {len(entities_by_address)} address group(s), "
        f"{total_entities} edge(s) total)."
    )
    lines.append("")

    def _addr_table(rows: list[AddressCandidate], header: str) -> None:
        lines.append(header)
        lines.append("")
        if not rows:
            lines.append("_None._")
            lines.append("")
            return
        lines.append("| # | score | exact | address_uid | source | country | raw_text |")
        lines.append("| ---: | ---: | :-: | --- | --- | --- | --- |")
        for i, c in enumerate(rows, start=1):
            lines.append(
                "| {i} | {sc:.1f} | {ex} | `{aid}` | {src} | {co} | {rt} |".format(
                    i=i,
                    sc=c.score,
                    ex="✓" if c.exact_normalized else "",
                    aid=c.address_uid,
                    src=c.source,
                    co=c.country or "?",
                    rt=_md_escape(c.raw_text)[:80],
                )
            )
        lines.append("")

    _addr_table(in_country, "## Address rows (same country)")
    if outside_country:
        _addr_table(
            outside_country,
            "## Address rows (different / unknown country)",
        )

    lines.append("## Entities registered at matched addresses")
    lines.append("")
    if not entities_by_address:
        lines.append("_No entities surfaced for any matched address row._")
    else:
        for addr_uid, rows in entities_by_address.items():
            lines.append(f"### `{addr_uid}` — {len(rows)} entity(ies)")
            lines.append("")
            lines.append("| entity_uid | name | jurisdiction | source |")
            lines.append("| --- | --- | --- | --- |")
            for r in rows:
                lines.append(
                    "| `{u}` | `{n}` | {j} | {s} |".format(
                        u=r.entity_uid,
                        n=_md_escape(r.name)[:60],
                        j=r.jurisdiction or "?",
                        s=r.source,
                    )
                )
            lines.append("")

    lines.append("## Review notes")
    lines.append("")
    if distinct_entities == 0:
        lines.append(
            "- No entities surface at any matched address — address strings "
            "exist in the corpus but no company row points to them. Could "
            "indicate an address-only ICIJ node with no registration edges."
        )
    elif distinct_entities >= 5:
        lines.append(
            f"- High shared-address concentration ({distinct_entities} distinct "
            "entities) — classic registered-agent / mass-incorporation pattern. "
            "Filter for jurisdictional overlap with the seed before drawing "
            "conclusions."
        )
    else:
        lines.append(
            f"- {distinct_entities} entity(ies) found. Review each registration "
            "to confirm the address is genuinely the same physical location."
        )
    lines.append("")

    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Seed text: `{_md_escape(seed.text)}`")
    lines.append(f"- Seed country: `{seed.country or '?'}`")
    lines.append(f"- Seed normalized: `{seed.normalized_text}`")
    for k, v in inputs_meta.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    return "\n".join(lines)


def default_address_report_path(reports_root: Path, seed: AddressSeed) -> Path:
    country_part = (seed.normalized_country or "global").lower()
    slug = _slugify(seed.normalized_text or seed.text)
    return reports_root / "investigations" / "addresses" / f"{slug}_{country_part}.md"
