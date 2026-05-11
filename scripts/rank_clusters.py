"""Rank multi-member dedupe clusters by a composite 'defensibility' score.

Pulls the latest v2 company-dedupe run from Postgres (``shellnet.clusters``),
joins with the unified company-entities parquet for names + jurisdictions,
the ICIJ edges parquet for officer / address counts, and the latest
list-match run (``shellnet.list_matches``) for GLEIF cross-source anchors.

Scoring components (each in [0,1], summed equally):

  * cross_source     — 1.0 if cluster spans icij + opensanctions or anchors to GLEIF
  * single_jur       — 1.0 if all members share a single jurisdiction (easier story)
  * tight_size       — 1.0 if 3 <= size <= 15 (writeable), 0.5 if 2 or 16-30, else 0
  * name_agreement   — share of pairs in the cluster whose normalized_name
                       has overlap_ratio >= 0.6 (token-set jaccard)
  * has_provenance   — 1.0 if cluster has any officer or address edges in
                       the raw ICIJ data (real provenance trail)
  * gleif_anchor     — share of members that have a list-match into GLEIF

Output: a markdown table sorted by defensibility, top 50.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from pathlib import Path

import polars as pl
import psycopg
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg.connect(url)


def _token_set(name: str) -> set[str]:
    if not name:
        return set()
    return {t for t in name.lower().split() if t}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@app.command()
def main(
    processed_dir: Path = typer.Option(Path("/data/processed"), "--processed-dir"),
    interim_dir: Path = typer.Option(Path("/data/interim"), "--interim-dir"),
    out_md: Path = typer.Option(
        Path("/data/reports/generated/cluster_ranking.md"), "--out-md"
    ),
    top_n: int = typer.Option(50, "--top-n"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    log.info("loading clusters + list-matches from Postgres")
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT run_id FROM shellnet.runs "
            "WHERE what='company' ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("no company run in shellnet.runs")
        dedupe_run_id = row[0]
        log.info("dedupe run_id = %s", dedupe_run_id)

        # Pull multi-member clusters only (cheaper than scanning 800K rows).
        cur.execute(
            """
            WITH cnt AS (
                SELECT cluster_id, COUNT(*) AS n
                FROM shellnet.clusters
                WHERE run_id = %s
                GROUP BY cluster_id
                HAVING COUNT(*) >= 2
            )
            SELECT c.cluster_id, c.entity_uid
            FROM shellnet.clusters c
            JOIN cnt USING (cluster_id)
            WHERE c.run_id = %s
            """,
            (str(dedupe_run_id), str(dedupe_run_id)),
        )
        rows = cur.fetchall()

        cur.execute(
            "SELECT run_id FROM shellnet.runs "
            "WHERE what LIKE 'list_match:%%v2%%' "
            "ORDER BY created_at DESC LIMIT 1"
        )
        lm_row = cur.fetchone()
        lm_run_id = lm_row[0] if lm_row else None
        anchors_by_uid: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
        if lm_run_id:
            log.info("list-match run_id = %s", lm_run_id)
            cur.execute(
                """
                SELECT target_entity_uid, ref_entity_uid, ref_name, score
                FROM shellnet.list_matches
                WHERE run_id = %s
                """,
                (str(lm_run_id),),
            )
            for t, r, rn, sc in cur.fetchall():
                anchors_by_uid[t].append((r, rn or "", float(sc)))
        else:
            log.warning("no v2 list_match run found")

    log.info("loaded %d (cluster_id, entity_uid) pairs", len(rows))
    members_by_cluster: dict[int, list[str]] = defaultdict(list)
    for cid, uid in rows:
        members_by_cluster[int(cid)].append(uid)
    log.info("%d multi-member clusters", len(members_by_cluster))

    log.info("reading company_entities parquet")
    company_df = pl.read_parquet(processed_dir / "company_entities.parquet").select(
        ["entity_uid", "source", "name", "normalized_name", "jurisdiction"]
    )
    company_lookup = {
        r["entity_uid"]: r
        for r in company_df.filter(
            pl.col("entity_uid").is_in(
                list({u for uids in members_by_cluster.values() for u in uids})
            )
        ).iter_rows(named=True)
    }
    log.info("attribute lookup built for %d entities", len(company_lookup))

    log.info("reading icij_edges parquet")
    edges = pl.read_parquet(interim_dir / "icij_edges.parquet").select(
        ["src_node", "dst_node", "kind_raw"]
    )
    # Officer/address provenance: count edges incident to each ICIJ source_id
    # (entity_uid for ICIJ rows is 'icij:<source_id>').
    icij_uids = {u for u in company_lookup if u.startswith("icij:")}
    icij_ids = {u.split(":", 1)[1] for u in icij_uids}
    edge_subset = edges.filter(
        pl.col("src_node").is_in(list(icij_ids))
        | pl.col("dst_node").is_in(list(icij_ids))
    )
    log.info("filtered edges to %d incident to clustered ICIJ entities", edge_subset.height)

    addr_per_uid: dict[str, int] = defaultdict(int)
    off_per_uid: dict[str, int] = defaultdict(int)
    for r in edge_subset.iter_rows(named=True):
        kind = (r["kind_raw"] or "").lower()
        if "address" in kind:
            for nid in (r["src_node"], r["dst_node"]):
                if nid in icij_ids:
                    addr_per_uid[f"icij:{nid}"] += 1
        elif "officer" in kind or "intermediar" in kind:
            for nid in (r["src_node"], r["dst_node"]):
                if nid in icij_ids:
                    off_per_uid[f"icij:{nid}"] += 1

    log.info("scoring clusters")
    scored = []
    for cid, uids in members_by_cluster.items():
        size = len(uids)
        sources = {company_lookup.get(u, {}).get("source") for u in uids} - {None}
        jurs = {company_lookup.get(u, {}).get("jurisdiction") for u in uids} - {None}
        names = [company_lookup.get(u, {}).get("normalized_name") or "" for u in uids]

        anchor_uids = [u for u in uids if anchors_by_uid.get(u)]
        anchor_share = len(anchor_uids) / size if size else 0.0
        cross_source = 1.0 if (len(sources) >= 2 or anchor_share > 0) else 0.0
        single_jur = 1.0 if len(jurs) == 1 else 0.0
        if 3 <= size <= 15:
            tight_size = 1.0
        elif size == 2 or 16 <= size <= 30:
            tight_size = 0.5
        else:
            tight_size = 0.0

        token_sets = [_token_set(n) for n in names]
        agreement_pairs: list[float] = []
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                agreement_pairs.append(_jaccard(token_sets[i], token_sets[j]))
        if agreement_pairs:
            high_share = sum(1 for x in agreement_pairs if x >= 0.6) / len(
                agreement_pairs
            )
        else:
            high_share = 0.0

        total_addr = sum(addr_per_uid.get(u, 0) for u in uids)
        total_off = sum(off_per_uid.get(u, 0) for u in uids)
        has_provenance = 1.0 if (total_addr + total_off) > 0 else 0.0

        score = (
            cross_source
            + single_jur
            + tight_size
            + high_share
            + has_provenance
            + min(1.0, anchor_share * 2)  # weight gleif anchor 2x but cap at 1.0
        )

        scored.append(
            {
                "cluster_id": cid,
                "score": score,
                "size": size,
                "sources": "|".join(sorted(s or "?" for s in sources)),
                "jurisdictions": "|".join(sorted(j or "?" for j in jurs)),
                "anchor_share": anchor_share,
                "name_agreement": high_share,
                "addresses": total_addr,
                "officers": total_off,
                "sample_names": " · ".join(
                    n[:30] for n in (
                        company_lookup.get(u, {}).get("name") or "" for u in uids
                    ) if n
                )[:120],
                "sample_anchor": (
                    anchors_by_uid[anchor_uids[0]][0][1][:60]
                    if anchor_uids else ""
                ),
            }
        )

    scored.sort(key=lambda r: (-r["score"], -r["anchor_share"], -r["size"]))

    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Cluster ranking by defensibility",
        "",
        f"From v2 dedupe run `{dedupe_run_id}` ({len(members_by_cluster)} multi-member clusters).",
        f"Cross-source signal from list-match run `{lm_run_id}`.",
        "",
        "Score is a sum of six components in [0,1]: cross_source, single_jur, "
        "tight_size, name_agreement, has_provenance, 2× anchor_share (capped at 1).",
        "",
        f"## Top {top_n}",
        "",
        "| cluster_id | score | size | src | jur | anchor% | name_agree | addrs | officers | sample names | sample gleif anchor |",
        "| ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for r in scored[:top_n]:
        lines.append(
            "| {cluster_id} | {score:.2f} | {size} | {sources} | {jurisdictions} | "
            "{anchor_share:.0%} | {name_agreement:.0%} | {addresses} | {officers} | "
            "{sample_names} | {sample_anchor} |".format(**r)
        )

    out_md.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s (%d top clusters)", out_md, min(top_n, len(scored)))

    # Also drop the raw scored table as parquet for downstream tooling.
    out_parquet = out_md.with_suffix(".parquet")
    pl.DataFrame(scored).write_parquet(out_parquet)
    log.info("wrote %s (%d rows)", out_parquet, len(scored))


if __name__ == "__main__":
    app()
