"""Generate a per-cluster provenance report.

    uv run python scripts/provenance_report.py 503264

Pulls every piece of evidence for the named cluster — the ICIJ source rows,
the GLEIF list-match anchors, the v2 match scores, the ICIJ relationships
touching the cluster (officers, intermediaries, addresses, parent/child) —
and writes a markdown report under reports/case_studies/<cluster_id>_<slug>.md.

Designed to be runnable both locally (with the Postgres public proxy)
and on the Railway shellnet-job container. Postgres connection uses
``DATABASE_URL`` env var.
"""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from pathlib import Path

import polars as pl
import psycopg
import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)
log = logging.getLogger(__name__)


def _slugify(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s.lower()).strip("_")
    return s[:40] or "cluster"


def _conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg.connect(url)


@app.command()
def main(
    cluster_id: int = typer.Argument(..., help="cluster_id from shellnet.clusters"),
    processed_dir: Path = typer.Option(
        Path("/data/processed"),
        "--processed-dir",
        help="Override the processed-parquet directory.",
    ),
    interim_dir: Path = typer.Option(
        Path("/data/interim"),
        "--interim-dir",
        help="Override the interim-parquet directory.",
    ),
    out_dir: Path = typer.Option(
        Path("/data/reports/generated/case_studies"),
        "--out-dir",
        help="Where the `<cluster_id>_<slug>.md` report lands.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Emit DEBUG-level logs."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    log.info("loading cluster %d", cluster_id)
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT run_id, created_at FROM shellnet.runs "
            "WHERE what='company' ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("no company run in shellnet.runs")
        dedupe_run_id, dedupe_created = row[0], row[1]

        cur.execute(
            "SELECT entity_uid FROM shellnet.clusters WHERE run_id=%s AND cluster_id=%s",
            (str(dedupe_run_id), cluster_id),
        )
        member_uids = [r[0] for r in cur.fetchall()]
        if not member_uids:
            raise RuntimeError(f"cluster {cluster_id} has no members in run {dedupe_run_id}")
        log.info("%d members", len(member_uids))

        cur.execute(
            "SELECT run_id, what FROM shellnet.runs "
            "WHERE what LIKE 'list_match:%%v2%%' "
            "ORDER BY created_at DESC LIMIT 1"
        )
        lm = cur.fetchone()
        lm_run_id, lm_run_name = (lm[0], lm[1]) if lm else (None, None)

        anchors: dict[str, list[dict]] = defaultdict(list)
        if lm_run_id:
            cur.execute(
                """
                SELECT target_entity_uid, ref_entity_uid, ref_name,
                       ref_jurisdiction, ref_lei, score, score_band
                FROM shellnet.list_matches
                WHERE run_id=%s AND target_entity_uid = ANY(%s)
                """,
                (str(lm_run_id), member_uids),
            )
            for t, r, rn, rj, lei, sc, band in cur.fetchall():
                anchors[t].append(
                    {
                        "ref_uid": r,
                        "ref_name": rn,
                        "ref_jurisdiction": rj,
                        "ref_lei": lei,
                        "score": float(sc),
                        "band": band,
                    }
                )

        # Same-as pairs within this cluster (sanity-check intra-cluster matches).
        cur.execute(
            "SELECT left_uid, right_uid, cluster_id FROM shellnet.same_as_pairs "
            "WHERE run_id=%s AND cluster_id=%s",
            (str(dedupe_run_id), cluster_id),
        )
        same_as = cur.fetchall()

    # Attribute lookup from the processed parquet.
    log.info("reading company_entities parquet")
    member_attrs = (
        pl.read_parquet(processed_dir / "company_entities.parquet")
        .filter(pl.col("entity_uid").is_in(member_uids))
        .to_dicts()
    )
    attr_by_uid = {r["entity_uid"]: r for r in member_attrs}

    # Edges store node IDs in entity_uid form ('icij:<source_id>'), not the
    # raw numeric node_id, so we filter on member_uids directly.
    icij_member_uids = [u for u in member_uids if u.startswith("icij:")]
    rels_summary: list[dict] = []
    if icij_member_uids:
        log.info("reading icij_edges parquet")
        edges = pl.read_parquet(interim_dir / "icij_edges.parquet").select(
            ["src_node", "dst_node", "kind_raw", "role", "start_date", "end_date", "source_label"]
        )
        for uid in icij_member_uids:
            sub = edges.filter((pl.col("src_node") == uid) | (pl.col("dst_node") == uid))
            if sub.height:
                rels_summary.append(
                    {
                        "uid": uid,
                        "n_edges": sub.height,
                        "sample": sub.head(15).to_dicts(),
                    }
                )

    # Pick a slug from the longest common normalized_name prefix.
    norm_names = [(attr_by_uid.get(u, {}).get("normalized_name") or "") for u in member_uids]
    name_for_slug = ""
    if norm_names:
        # Longest common prefix across normalized names.
        cand = norm_names[0]
        for n in norm_names[1:]:
            i = 0
            while i < min(len(cand), len(n)) and cand[i] == n[i]:
                i += 1
            cand = cand[:i]
        name_for_slug = cand.strip() or norm_names[0]
    slug = _slugify(name_for_slug)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / f"{cluster_id}_{slug}.md"

    # Build markdown.
    lines: list[str] = []
    lines.append(f"# Cluster {cluster_id} — {name_for_slug or '(unnamed)'}")
    lines.append("")
    lines.append(
        "Provenance report for a multi-member cluster produced by the v2 GoldenMatch dedupe pass."
    )
    lines.append("")
    lines.append(f"- **Dedupe run**: `{dedupe_run_id}` (created `{dedupe_created}`)")
    if lm_run_id:
        lines.append(f"- **List-match run**: `{lm_run_id}` (`{lm_run_name}`)")
    lines.append(f"- **Members**: {len(member_uids)}")
    sources = sorted({(attr_by_uid.get(u) or {}).get("source") for u in member_uids} - {None})
    lines.append(f"- **Source datasets**: {', '.join(sources)}")
    jurs = sorted({(attr_by_uid.get(u) or {}).get("jurisdiction") for u in member_uids} - {None})
    lines.append(f"- **Jurisdictions**: {', '.join(jurs)}")
    anchored = sum(1 for u in member_uids if anchors.get(u))
    lines.append(
        f"- **GLEIF anchors**: {anchored} / {len(member_uids)} "
        f"({100 * anchored / len(member_uids):.0f}%)"
    )
    lines.append("")
    lines.append(
        "> **Disclaimer.** Each row below is a hypothesis the matcher "
        "produced from public data. Membership in the ICIJ Offshore Leaks "
        "Database does **not** imply wrongdoing. Many entities listed are "
        "legitimate corporate structures. Do not derive identity-linked "
        "claims from this report without independent review."
    )
    lines.append("")

    lines.append("## Members (side-by-side)")
    lines.append("")
    lines.append("| # | entity_uid | source | name | jurisdiction | source_id |")
    lines.append("| ---: | --- | --- | --- | --- | --- |")
    for i, uid in enumerate(sorted(member_uids), start=1):
        a = attr_by_uid.get(uid, {})
        lines.append(
            "| {i} | `{uid}` | {src} | `{name}` | {jur} | {sid} |".format(
                i=i,
                uid=uid,
                src=a.get("source") or "?",
                name=(a.get("name") or "").replace("|", "/")[:70],
                jur=a.get("jurisdiction") or "?",
                sid=a.get("source_id") or "?",
            )
        )
    lines.append("")

    if anchors:
        lines.append("## GLEIF cross-source anchors")
        lines.append("")
        lines.append(
            "Each ICIJ/OS member that the list-match step linked to a GLEIF "
            "LEI record, with the v2 match score and heuristic band."
        )
        lines.append("")
        lines.append("| icij/os uid | gleif lei | gleif name | score | band |")
        lines.append("| --- | --- | --- | ---: | --- |")
        for uid in sorted(member_uids):
            for a in anchors.get(uid, []):
                lei = (a.get("ref_lei") or "").replace("|", "/")
                rn = (a.get("ref_name") or "").replace("|", "/")[:60]
                lines.append(
                    "| `{u}` | `{lei}` | `{n}` | {s:.3f} | {b} |".format(
                        u=uid, lei=lei, n=rn, s=a["score"], b=a.get("band") or ""
                    )
                )
        lines.append("")

    lines.append("## Intra-cluster `same_as` pairs")
    lines.append("")
    if same_as:
        lines.append("| left | right | cluster |")
        lines.append("| --- | --- | ---: |")
        for left, right, cid in same_as[:40]:
            lines.append(f"| `{left}` | `{right}` | {cid} |")
        if len(same_as) > 40:
            lines.append(f"| _… {len(same_as) - 40} more pairs_ | | |")
    else:
        lines.append("_No explicit same-as pairs recorded for this cluster._")
    lines.append("")

    if rels_summary:
        lines.append("## ICIJ relationships incident to cluster members")
        lines.append("")
        total = sum(r["n_edges"] for r in rels_summary)
        lines.append(
            f"{total} edges total across {len(rels_summary)} ICIJ-sided "
            "members. Showing up to 15 per member; address-type relationships "
            "and officer-type relationships are the structural backbone."
        )
        lines.append("")
        for r in rels_summary:
            lines.append(f"### `{r['uid']}` — {r['n_edges']} edges")
            lines.append("")
            lines.append("| kind_raw | role | other | start | end | leak |")
            lines.append("| --- | --- | --- | --- | --- | --- |")
            for e in r["sample"]:
                other = e["dst_node"] if e["src_node"] == r["uid"] else e["src_node"]
                lines.append(
                    "| {k} | {role} | `{o}` | {s} | {ed} | {lab} |".format(
                        k=(e.get("kind_raw") or "")[:30],
                        role=(e.get("role") or "")[:30],
                        o=other,
                        s=e.get("start_date") or "",
                        ed=e.get("end_date") or "",
                        lab=(e.get("source_label") or "")[:25],
                    )
                )
            lines.append("")
    else:
        lines.append("## ICIJ relationships incident to cluster members")
        lines.append("")
        lines.append("_None — either no ICIJ members in cluster, or relationship lookup empty._")
        lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append(
        "- The cluster groups records that the matcher *believes* refer to "
        "the same legal entity. Membership and similarity are evidence, not "
        "proof."
    )
    lines.append(
        "- GLEIF LEIs are authoritative only for the entity they were issued "
        "to. A high-score match between an ICIJ entity and a GLEIF LEI is a "
        "strong corroborating signal, but a human reviewer should compare "
        "incorporation date, registered address, and any officer overlap "
        "before treating them as the same entity."
    )
    lines.append(
        "- This snapshot is built from the ICIJ bundle dated 2025-03-31, the "
        "GLEIF Golden Copy dated 2026-05-11, and the US OFAC SDN dataset "
        "fetched 2026-05-11. Names, statuses, and addresses change over time."
    )
    lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s", out_md)
    print(str(out_md))


if __name__ == "__main__":
    app()
