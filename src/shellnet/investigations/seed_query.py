"""Seed-query workflow: rank candidates in the unified company table for a
single (name, jurisdiction) input, then attach 1-hop ICIJ neighbourhood
context and (optionally) published GoldenMatch results from Postgres.

The logic here is import-safe: no I/O at module import time, no Typer.
``scripts/investigate_entity.py`` is the thin CLI wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
from rapidfuzz import fuzz

from shellnet.normalize import normalize_company_name, normalize_jurisdiction


@dataclass(frozen=True)
class Seed:
    name: str
    jurisdiction: str | None
    normalized_name: str
    normalized_jurisdiction: str | None


@dataclass
class Candidate:
    entity_uid: str
    source: str
    name: str
    normalized_name: str
    jurisdiction: str | None
    company_number: str | None
    lei: str | None
    address_raw: str | None
    score: float
    exact_normalized: bool
    in_jurisdiction: bool


@dataclass
class Neighbourhood:
    """1-hop ICIJ context for a single ICIJ entity_uid."""

    entity_uid: str
    n_edges: int
    addresses: list[dict[str, Any]] = field(default_factory=list)
    officers: list[dict[str, Any]] = field(default_factory=list)
    intermediaries: list[dict[str, Any]] = field(default_factory=list)
    connected_entities: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GoldenmatchContext:
    """Published GoldenMatch context for a set of entity_uids, if a
    DATABASE_URL is reachable. Each list element is one row from the
    relevant table."""

    dedupe_run_id: str | None = None
    list_match_run_id: str | None = None
    cluster_memberships: list[dict[str, Any]] = field(default_factory=list)
    list_match_anchors: list[dict[str, Any]] = field(default_factory=list)
    same_as_pairs: list[dict[str, Any]] = field(default_factory=list)


def make_seed(name: str, jurisdiction: str | None) -> Seed:
    norm_name = normalize_company_name(name)
    norm_juris = normalize_jurisdiction(jurisdiction) if jurisdiction else None
    return Seed(
        name=name,
        jurisdiction=jurisdiction,
        normalized_name=norm_name,
        normalized_jurisdiction=norm_juris,
    )


def _score_row(seed_norm: str, candidate_norm: str | None) -> float:
    if not candidate_norm:
        return 0.0
    return float(fuzz.token_sort_ratio(seed_norm, candidate_norm))


def rank_candidates(
    company_df: pl.DataFrame,
    seed: Seed,
    *,
    top_n: int = 25,
    min_score: float = 85.0,
    include_outside_jurisdiction: bool = True,
) -> tuple[list[Candidate], list[Candidate]]:
    """Score every row in ``company_df`` against the seed.

    Returns ``(in_jurisdiction, outside_jurisdiction)`` lists, each already
    sorted and truncated to ``top_n``. If ``seed.normalized_jurisdiction``
    is ``None``, everything goes in the first list.
    """
    if company_df.height == 0 or not seed.normalized_name:
        return [], []

    norm = company_df.get_column("normalized_name").to_list()
    scores = [_score_row(seed.normalized_name, n) for n in norm]
    sdf = company_df.with_columns(pl.Series("_score", scores))
    sdf = sdf.filter(pl.col("_score") >= min_score)
    if sdf.height == 0:
        return [], []

    have_juris = seed.normalized_jurisdiction is not None

    def _to_candidates(df: pl.DataFrame, in_juris: bool) -> list[Candidate]:
        rows = df.to_dicts()
        out: list[Candidate] = []
        for r in rows:
            nname = r.get("normalized_name") or ""
            out.append(
                Candidate(
                    entity_uid=r["entity_uid"],
                    source=r.get("source") or "?",
                    name=r.get("name") or "",
                    normalized_name=nname,
                    jurisdiction=r.get("jurisdiction"),
                    company_number=r.get("company_number"),
                    lei=r.get("lei"),
                    address_raw=r.get("address_raw"),
                    score=float(r["_score"]),
                    exact_normalized=(nname == seed.normalized_name),
                    in_jurisdiction=in_juris,
                )
            )
        # Sort: exact-normalized first, then score desc, then has-LEI, then has-cn.
        out.sort(
            key=lambda c: (
                not c.exact_normalized,
                -c.score,
                not bool(c.lei),
                not bool(c.company_number),
            )
        )
        return out[:top_n]

    if not have_juris:
        return _to_candidates(sdf, in_juris=True), []

    in_df = sdf.filter(pl.col("jurisdiction") == seed.normalized_jurisdiction)
    out_df = sdf.filter(
        (pl.col("jurisdiction") != seed.normalized_jurisdiction)
        | pl.col("jurisdiction").is_null()
    )
    in_results = _to_candidates(in_df, in_juris=True)
    out_results = (
        _to_candidates(out_df, in_juris=False) if include_outside_jurisdiction else []
    )
    return in_results, out_results


def collect_icij_neighbourhood(
    icij_uids: list[str],
    *,
    edges_df: pl.DataFrame | None,
    addresses_df: pl.DataFrame | None,
    officers_df: pl.DataFrame | None,
    intermediaries_df: pl.DataFrame | None,
    company_df: pl.DataFrame | None,
    per_kind_limit: int = 15,
) -> list[Neighbourhood]:
    """For each ICIJ entity_uid, walk edges 1 hop and partition by kind.

    All inputs are optional; if a table isn't available we skip that slice.
    """
    if not icij_uids or edges_df is None or edges_df.height == 0:
        return []

    addr_by_sid = {}
    if addresses_df is not None and addresses_df.height:
        for r in addresses_df.to_dicts():
            addr_by_sid[r.get("source_id")] = r

    off_by_sid = {}
    if officers_df is not None and officers_df.height:
        for r in officers_df.to_dicts():
            off_by_sid[r.get("source_id")] = r

    inter_by_sid = {}
    if intermediaries_df is not None and intermediaries_df.height:
        for r in intermediaries_df.to_dicts():
            inter_by_sid[r.get("source_id")] = r

    company_by_uid = {}
    if company_df is not None and company_df.height:
        for r in company_df.to_dicts():
            company_by_uid[r.get("entity_uid")] = r

    out: list[Neighbourhood] = []
    for uid in icij_uids:
        sub = edges_df.filter(
            (pl.col("src_node") == uid) | (pl.col("dst_node") == uid)
        )
        if sub.height == 0:
            continue
        nbh = Neighbourhood(entity_uid=uid, n_edges=sub.height)
        for e in sub.to_dicts():
            other = e["dst_node"] if e["src_node"] == uid else e["src_node"]
            kind = (e.get("kind_raw") or "").lower()
            # ICIJ node-id types: 1xx = entity, 2xx = address, 3xx = officer,
            # 4xx = intermediary. But "kind_raw" carries the relationship
            # label so route off that primarily.
            other_sid = other.split(":", 1)[1] if ":" in other else other
            label = e.get("source_label") or ""
            start = e.get("start_date") or ""
            end = e.get("end_date") or ""
            if "address" in kind:
                addr = addr_by_sid.get(other_sid) or {}
                if len(nbh.addresses) < per_kind_limit:
                    nbh.addresses.append(
                        {
                            "node": other,
                            "text": addr.get("raw_text"),
                            "country": addr.get("country"),
                            "leak": label,
                            "start": start,
                            "end": end,
                        }
                    )
            elif "officer" in kind:
                off = off_by_sid.get(other_sid) or {}
                if len(nbh.officers) < per_kind_limit:
                    nbh.officers.append(
                        {
                            "node": other,
                            "name": off.get("name"),
                            "role": e.get("role"),
                            "country": off.get("country"),
                            "leak": label,
                            "start": start,
                            "end": end,
                        }
                    )
            elif "intermediary" in kind:
                inter = inter_by_sid.get(other_sid) or {}
                if len(nbh.intermediaries) < per_kind_limit:
                    nbh.intermediaries.append(
                        {
                            "node": other,
                            "name": inter.get("name"),
                            "country": inter.get("country"),
                            "leak": label,
                            "start": start,
                            "end": end,
                        }
                    )
            else:
                # Treat anything else (parent/child, associated_with, …) as
                # an entity-to-entity link if both ends look like companies.
                co = company_by_uid.get(other) or {}
                if len(nbh.connected_entities) < per_kind_limit:
                    nbh.connected_entities.append(
                        {
                            "node": other,
                            "name": co.get("name"),
                            "kind_raw": e.get("kind_raw"),
                            "role": e.get("role"),
                            "leak": label,
                            "start": start,
                            "end": end,
                        }
                    )
        out.append(nbh)
    return out


def fetch_goldenmatch_context(
    entity_uids: list[str], *, conn: Any
) -> GoldenmatchContext:
    """Query the Postgres tables ``provenance_report.py`` already uses.

    ``conn`` is a live ``psycopg`` connection. Caller decides whether to
    open one — we never reach for the network on our own.
    """
    ctx = GoldenmatchContext()
    if not entity_uids:
        return ctx

    with conn.cursor() as cur:
        cur.execute(
            "SELECT run_id FROM shellnet.runs "
            "WHERE what='company' ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if row:
            ctx.dedupe_run_id = str(row[0])
            cur.execute(
                "SELECT entity_uid, cluster_id FROM shellnet.clusters "
                "WHERE run_id=%s AND entity_uid = ANY(%s)",
                (ctx.dedupe_run_id, entity_uids),
            )
            ctx.cluster_memberships = [
                {"entity_uid": uid, "cluster_id": cid} for uid, cid in cur.fetchall()
            ]
            cluster_ids = sorted({m["cluster_id"] for m in ctx.cluster_memberships})
            if cluster_ids:
                cur.execute(
                    "SELECT left_uid, right_uid, cluster_id FROM shellnet.same_as_pairs "
                    "WHERE run_id=%s AND cluster_id = ANY(%s)",
                    (ctx.dedupe_run_id, cluster_ids),
                )
                ctx.same_as_pairs = [
                    {"left": left, "right": right, "cluster_id": cid}
                    for (left, right, cid) in cur.fetchall()
                ]

        cur.execute(
            "SELECT run_id FROM shellnet.runs "
            "WHERE what LIKE 'list_match:%%v2%%' "
            "ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if row:
            ctx.list_match_run_id = str(row[0])
            cur.execute(
                """
                SELECT target_entity_uid, ref_entity_uid, ref_name,
                       ref_jurisdiction, ref_lei, score, score_band
                FROM shellnet.list_matches
                WHERE run_id=%s AND target_entity_uid = ANY(%s)
                """,
                (ctx.list_match_run_id, entity_uids),
            )
            for t, r, rn, rj, lei, sc, band in cur.fetchall():
                ctx.list_match_anchors.append(
                    {
                        "target_entity_uid": t,
                        "ref_entity_uid": r,
                        "ref_name": rn,
                        "ref_jurisdiction": rj,
                        "ref_lei": lei,
                        "score": float(sc),
                        "band": band,
                    }
                )
    return ctx


def _md_escape(s: Any) -> str:
    if s is None:
        return ""
    return str(s).replace("|", "/").replace("\n", " ").strip()


def _slugify(s: str) -> str:
    import re

    s = re.sub(r"[^A-Za-z0-9]+", "_", s.lower()).strip("_")
    return s[:60] or "seed"


def render_report(
    seed: Seed,
    *,
    in_juris: list[Candidate],
    outside_juris: list[Candidate],
    neighbourhoods: list[Neighbourhood],
    gm_context: GoldenmatchContext | None,
    sources_seen: list[str],
    inputs_meta: dict[str, Any],
    generated_at: datetime | None = None,
    source_note: str | None = None,
    batch_id: str | None = None,
) -> str:
    """Build the markdown report. Pure string-in, string-out.

    ``source_note`` is rendered verbatim near the top — used by batch mode
    to thread per-seed provenance (URL, citation, who suggested the seed)
    from the input CSV into the generated report.
    """
    generated_at = generated_at or datetime.now(UTC)
    lines: list[str] = []

    juris_label = seed.normalized_jurisdiction or "(unspecified)"
    lines.append(
        f"# Investigation seed: `{_md_escape(seed.name)}` / {juris_label}"
    )
    lines.append("")
    lines.append(
        f"Generated `{generated_at.isoformat(timespec='seconds')}`"
        + (f" as part of batch `{batch_id}`" if batch_id else "")
        + ". Seed-query workflow over local processed parquets"
        + (" + published GoldenMatch context." if gm_context else ".")
    )
    lines.append("")
    if source_note:
        lines.append(f"**Seed source:** {_md_escape(source_note)}")
        lines.append("")
    lines.append(
        "> **Hypothesis, not proof.** Every candidate below is a guess the "
        "matcher produced from public data. Names collide. Public data is "
        "incomplete. Treat each row as a lead to review, not a finding to "
        "publish. Do not derive identity-linked claims without human review."
    )
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    if in_juris:
        top = in_juris[0]
        lines.append(
            f"- Best local candidate: `{top.entity_uid}` "
            f"(`{_md_escape(top.name)}`, {top.jurisdiction or '?'}, "
            f"score {top.score:.1f})"
        )
    else:
        lines.append("- No same-jurisdiction candidates above the score threshold.")
    if outside_juris:
        lines.append(
            f"- {len(outside_juris)} possible outside-jurisdiction match(es) "
            "— see separate section."
        )
    if gm_context and gm_context.list_match_anchors:
        n_lei = sum(1 for a in gm_context.list_match_anchors if a.get("ref_lei"))
        lines.append(
            f"- Published GoldenMatch: {len(gm_context.list_match_anchors)} "
            f"list-match anchor(s) ({n_lei} with LEI)."
        )
    if gm_context and gm_context.cluster_memberships:
        clusters = sorted({m["cluster_id"] for m in gm_context.cluster_memberships})
        lines.append(
            f"- Cluster membership: {clusters} "
            f"(from dedupe run `{gm_context.dedupe_run_id}`)."
        )
    if neighbourhoods:
        n_addr = sum(len(n.addresses) for n in neighbourhoods)
        n_off = sum(len(n.officers) for n in neighbourhoods)
        n_int = sum(len(n.intermediaries) for n in neighbourhoods)
        lines.append(
            f"- ICIJ 1-hop neighbourhood: {n_addr} address(es), {n_off} "
            f"officer-edge(s), {n_int} intermediary-edge(s)."
        )
    lines.append("")

    lines.append("## Candidate records (same jurisdiction)")
    lines.append("")
    if in_juris:
        lines.append(
            "| # | score | exact | entity_uid | source | name | jurisdiction | lei | company_number |"
        )
        lines.append("| ---: | ---: | :-: | --- | --- | --- | --- | --- | --- |")
        for i, c in enumerate(in_juris, start=1):
            lines.append(
                "| {i} | {sc:.1f} | {ex} | `{uid}` | {src} | `{name}` | {jur} | {lei} | {cn} |".format(
                    i=i,
                    sc=c.score,
                    ex="✓" if c.exact_normalized else "",
                    uid=c.entity_uid,
                    src=c.source,
                    name=_md_escape(c.name)[:60],
                    jur=c.jurisdiction or "?",
                    lei=c.lei or "",
                    cn=c.company_number or "",
                )
            )
    else:
        lines.append("_No candidates passed the score threshold._")
    lines.append("")

    if outside_juris:
        lines.append("## Possible outside-jurisdiction matches")
        lines.append("")
        lines.append(
            "_These score well but their jurisdiction does not match the "
            "seed. Treat as lower-confidence hypotheses — jurisdiction may "
            "be missing, abbreviated differently, or genuinely distinct._"
        )
        lines.append("")
        lines.append(
            "| # | score | entity_uid | source | name | jurisdiction | lei |"
        )
        lines.append("| ---: | ---: | --- | --- | --- | --- | --- |")
        for i, c in enumerate(outside_juris, start=1):
            lines.append(
                "| {i} | {sc:.1f} | `{uid}` | {src} | `{name}` | {jur} | {lei} |".format(
                    i=i,
                    sc=c.score,
                    uid=c.entity_uid,
                    src=c.source,
                    name=_md_escape(c.name)[:60],
                    jur=c.jurisdiction or "?",
                    lei=c.lei or "",
                )
            )
        lines.append("")

    lines.append("## Published GoldenMatch context")
    lines.append("")
    if gm_context is None:
        lines.append(
            "_Skipped — no `DATABASE_URL` set. Set the env var to enrich "
            "with published list-match anchors, cluster memberships, and "
            "same-as pairs._"
        )
    elif not (
        gm_context.list_match_anchors
        or gm_context.cluster_memberships
        or gm_context.same_as_pairs
    ):
        lines.append("_No published context for these candidates._")
    else:
        if gm_context.list_match_anchors:
            lines.append("### GLEIF list-match anchors")
            lines.append("")
            lines.append(
                f"From list-match run `{gm_context.list_match_run_id}`."
            )
            lines.append("")
            lines.append(
                "| target_uid | gleif_lei | gleif_name | jur | score | band |"
            )
            lines.append("| --- | --- | --- | --- | ---: | --- |")
            for a in gm_context.list_match_anchors:
                lines.append(
                    "| `{t}` | `{lei}` | `{n}` | {j} | {s:.3f} | {b} |".format(
                        t=a["target_entity_uid"],
                        lei=_md_escape(a.get("ref_lei")),
                        n=_md_escape(a.get("ref_name"))[:60],
                        j=a.get("ref_jurisdiction") or "?",
                        s=a["score"],
                        b=a.get("band") or "",
                    )
                )
            lines.append("")
        if gm_context.cluster_memberships:
            lines.append("### Cluster membership")
            lines.append("")
            lines.append(f"From dedupe run `{gm_context.dedupe_run_id}`.")
            lines.append("")
            lines.append("| entity_uid | cluster_id |")
            lines.append("| --- | ---: |")
            for m in gm_context.cluster_memberships:
                lines.append(f"| `{m['entity_uid']}` | {m['cluster_id']} |")
            lines.append("")
        if gm_context.same_as_pairs:
            lines.append("### Same-as pairs (within shared clusters)")
            lines.append("")
            lines.append("| left | right | cluster |")
            lines.append("| --- | --- | ---: |")
            for p in gm_context.same_as_pairs[:40]:
                lines.append(
                    f"| `{p['left']}` | `{p['right']}` | {p['cluster_id']} |"
                )
            if len(gm_context.same_as_pairs) > 40:
                lines.append(
                    f"| _… {len(gm_context.same_as_pairs)-40} more_ | | |"
                )
            lines.append("")

    lines.append("## 1-hop ICIJ neighbourhood")
    lines.append("")
    if not neighbourhoods:
        lines.append(
            "_No ICIJ-sided candidates, or no edges incident to those candidates._"
        )
    else:
        for n in neighbourhoods:
            lines.append(f"### `{n.entity_uid}` — {n.n_edges} edges")
            lines.append("")
            if n.addresses:
                lines.append("**Registered addresses**")
                lines.append("")
                lines.append("| node | address | country | leak | start | end |")
                lines.append("| --- | --- | --- | --- | --- | --- |")
                for a in n.addresses:
                    lines.append(
                        "| `{nd}` | {t} | {c} | {l} | {s} | {e} |".format(
                            nd=a["node"],
                            t=_md_escape(a.get("text"))[:80],
                            c=a.get("country") or "?",
                            l=_md_escape(a.get("leak")),
                            s=a.get("start") or "",
                            e=a.get("end") or "",
                        )
                    )
                lines.append("")
            if n.officers:
                lines.append("**Officers**")
                lines.append("")
                lines.append("| node | name | role | country | leak |")
                lines.append("| --- | --- | --- | --- | --- |")
                for o in n.officers:
                    lines.append(
                        "| `{nd}` | {nm} | {r} | {c} | {l} |".format(
                            nd=o["node"],
                            nm=_md_escape(o.get("name"))[:60],
                            r=_md_escape(o.get("role")),
                            c=o.get("country") or "?",
                            l=_md_escape(o.get("leak")),
                        )
                    )
                lines.append("")
            if n.intermediaries:
                lines.append("**Intermediaries**")
                lines.append("")
                lines.append("| node | name | country | leak |")
                lines.append("| --- | --- | --- | --- |")
                for it in n.intermediaries:
                    lines.append(
                        "| `{nd}` | {nm} | {c} | {l} |".format(
                            nd=it["node"],
                            nm=_md_escape(it.get("name"))[:60],
                            c=it.get("country") or "?",
                            l=_md_escape(it.get("leak")),
                        )
                    )
                lines.append("")
            if n.connected_entities:
                lines.append("**Connected entities**")
                lines.append("")
                lines.append("| node | name | kind_raw | role | leak |")
                lines.append("| --- | --- | --- | --- | --- |")
                for ce in n.connected_entities:
                    lines.append(
                        "| `{nd}` | {nm} | {k} | {r} | {l} |".format(
                            nd=ce["node"],
                            nm=_md_escape(ce.get("name"))[:60],
                            k=_md_escape(ce.get("kind_raw")),
                            r=_md_escape(ce.get("role")),
                            l=_md_escape(ce.get("leak")),
                        )
                    )
                lines.append("")

    # Shared-address / shared-officer summary across all candidates.
    all_addrs: dict[str, list[str]] = {}
    all_offs: dict[str, list[str]] = {}
    for n in neighbourhoods:
        for a in n.addresses:
            key = _md_escape(a.get("text")) or "(unknown)"
            all_addrs.setdefault(key, []).append(n.entity_uid)
        for o in n.officers:
            key = _md_escape(o.get("name")) or "(unknown)"
            all_offs.setdefault(key, []).append(n.entity_uid)
    shared_addrs = {k: v for k, v in all_addrs.items() if len(set(v)) > 1}
    shared_offs = {k: v for k, v in all_offs.items() if len(set(v)) > 1}
    if shared_addrs or shared_offs:
        lines.append("## Cross-candidate overlap")
        lines.append("")
        if shared_addrs:
            lines.append("**Addresses shared across candidates**")
            lines.append("")
            lines.append("| address | shared by |")
            lines.append("| --- | --- |")
            for addr, uids in sorted(
                shared_addrs.items(), key=lambda kv: -len(set(kv[1]))
            ):
                lines.append(
                    f"| {addr[:80]} | {', '.join(sorted(set(uids)))} |"
                )
            lines.append("")
        if shared_offs:
            lines.append("**Officers shared across candidates**")
            lines.append("")
            lines.append("| name | shared by |")
            lines.append("| --- | --- |")
            for name, uids in sorted(
                shared_offs.items(), key=lambda kv: -len(set(kv[1]))
            ):
                lines.append(f"| {name[:60]} | {', '.join(sorted(set(uids)))} |")
            lines.append("")

    lines.append("## Review notes")
    lines.append("")
    notes: list[str] = []
    if in_juris and in_juris[0].exact_normalized:
        notes.append(
            "- Top candidate is an exact normalized-name match in the seed "
            "jurisdiction — strong signal."
        )
    if in_juris and not in_juris[0].exact_normalized:
        notes.append(
            "- No exact normalized-name match; treat all candidates as "
            "fuzzy hypotheses pending review."
        )
    if outside_juris and not in_juris:
        notes.append(
            "- All hits are outside the seed jurisdiction. Consider whether "
            "the seed jurisdiction code itself is right."
        )
    if seed.normalized_jurisdiction is None and seed.jurisdiction:
        notes.append(
            f"- Seed jurisdiction `{seed.jurisdiction}` did not normalize "
            "to an ISO code — searched globally."
        )
    if not notes:
        notes.append("- No automatic notes generated. Review the tables above.")
    lines.extend(notes)
    lines.append("")

    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Seed: `{_md_escape(seed.name)}` / `{seed.jurisdiction or '?'}`")
    lines.append(
        f"- Seed normalized: `{seed.normalized_name}` / "
        f"`{seed.normalized_jurisdiction or '?'}`"
    )
    lines.append(f"- Sources present in candidate pool: {', '.join(sources_seen) or '(none)'}")
    for k, v in inputs_meta.items():
        lines.append(f"- {k}: `{v}`")
    if gm_context is not None:
        lines.append(
            f"- GoldenMatch dedupe run: `{gm_context.dedupe_run_id or '(none)'}`"
        )
        lines.append(
            f"- GoldenMatch list-match run: `{gm_context.list_match_run_id or '(none)'}`"
        )
    lines.append("")

    return "\n".join(lines)


def default_report_path(reports_root: Path, seed: Seed) -> Path:
    juris_part = (seed.normalized_jurisdiction or "global").lower()
    slug = _slugify(seed.normalized_name or seed.name)
    return reports_root / "investigations" / f"{slug}_{juris_part}.md"


@dataclass
class BatchRow:
    """One row's worth of state from a batch run, used for the index file."""

    seed: Seed
    source_note: str | None
    report_path: Path
    top_in_juris: Candidate | None
    n_in_juris: int
    n_outside_juris: int
    error: str | None = None


def render_batch_index(
    rows: list[BatchRow],
    *,
    batch_id: str,
    seeds_path: Path,
    generated_at: datetime | None = None,
) -> str:
    """Top-level summary across a batch run."""
    generated_at = generated_at or datetime.now(UTC)
    lines: list[str] = []
    lines.append(f"# Investigation batch: `{batch_id}`")
    lines.append("")
    lines.append(
        f"Generated `{generated_at.isoformat(timespec='seconds')}` from "
        f"`{seeds_path}` ({len(rows)} seed(s))."
    )
    lines.append("")
    lines.append(
        "> **Hypothesis, not proof.** Every linked report contains *candidate* "
        "matches the matcher produced from public data. Treat each row as a "
        "lead requiring human review, not a finding."
    )
    lines.append("")

    n_ok = sum(1 for r in rows if r.error is None)
    n_err = len(rows) - n_ok
    n_top = sum(1 for r in rows if r.top_in_juris is not None)
    n_exact = sum(
        1
        for r in rows
        if r.top_in_juris is not None and r.top_in_juris.exact_normalized
    )
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- {n_ok} seed(s) processed successfully, {n_err} error(s).")
    lines.append(
        f"- {n_top} seed(s) found at least one same-jurisdiction candidate."
    )
    lines.append(
        f"- {n_exact} of those had an exact normalized-name match in the seed jurisdiction."
    )
    lines.append("")

    lines.append("## Results")
    lines.append("")
    lines.append(
        "| # | seed | jur | top match | score | exact | in-juris | outside | source note | report |"
    )
    lines.append("| ---: | --- | --- | --- | ---: | :-: | ---: | ---: | --- | --- |")
    for i, r in enumerate(rows, start=1):
        if r.error:
            lines.append(
                f"| {i} | `{_md_escape(r.seed.name)}` | {r.seed.normalized_jurisdiction or '?'} "
                f"| _error_ |  |  |  |  | {_md_escape(r.source_note)} | _{_md_escape(r.error)}_ |"
            )
            continue
        top = r.top_in_juris
        rel = r.report_path.name  # link by filename — index lives in same dir
        top_name = _md_escape(top.name)[:50] if top else ""
        top_score = f"{top.score:.1f}" if top else ""
        top_exact = "✓" if (top and top.exact_normalized) else ""
        lines.append(
            "| {i} | `{seed}` | {jur} | `{tn}` | {ts} | {ex} | {ni} | {no} | {sn} | [{rel}]({rel}) |".format(
                i=i,
                seed=_md_escape(r.seed.name),
                jur=r.seed.normalized_jurisdiction or "?",
                tn=top_name,
                ts=top_score,
                ex=top_exact,
                ni=r.n_in_juris,
                no=r.n_outside_juris,
                sn=_md_escape(r.source_note),
                rel=rel,
            )
        )
    lines.append("")

    if n_err:
        lines.append("## Errors")
        lines.append("")
        for r in rows:
            if r.error:
                lines.append(
                    f"- `{_md_escape(r.seed.name)}` ({r.seed.jurisdiction or '?'}): {r.error}"
                )
        lines.append("")

    lines.append("## Source CSV format")
    lines.append("")
    lines.append("Expected columns:")
    lines.append("")
    lines.append("- `name` — seed company name (required).")
    lines.append(
        "- `jurisdiction` — ISO-2, ISO-3, or recognised alias (e.g. `bvi`, "
        "`cayman islands`). Optional but strongly recommended."
    )
    lines.append(
        "- `source_note` — free-text provenance for this seed (URL, citation, "
        "who suggested it). Echoed verbatim into each generated report."
    )
    lines.append("")
    return "\n".join(lines)
