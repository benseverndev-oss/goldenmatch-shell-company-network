"""Sample ~300 marginal pairs to label by hand.

Stratification (intent: validate the v1 -> v2 config tighten):

  * ``v1_dropped`` (n=100): pairs from the v1 list-match run that score
    0.85 <= s < 0.92. v2's threshold raise removed these — labelling
    them tells us whether the drop was a precision gain (most labelled
    `no_match`) or a precision loss (many labelled `match`).
  * ``v2_marginal`` (n=100): pairs from the v2 list-match run with
    0.92 <= s < 0.97. These are the still-marginal v2 keeps. Labelling
    them estimates v2's residual precision.
  * ``perfect_sanity`` (n=50): random pairs from v1 with s >= 0.99.
    Sanity-check the perfect band has near-100% precision.
  * ``v2_borderline_class`` (n=50): pairs from v2 in heuristic classes
    jur_close + jur_loose (not low_overlap) — pairs the heuristic
    review left as "needs human eyes."

Output: ``data/labels/marginal_v1.csv`` with these columns:

  pair_id, bucket, source_run, target_uid, target_source, target_name,
  target_jurisdiction, ref_uid, ref_source, ref_name, ref_jurisdiction,
  ref_lei, score, score_band, heuristic_class, label, rationale

``label`` should be filled with one of {match, no_match, unsure}.
``rationale`` is free-form (one sentence is enough for most).
"""

from __future__ import annotations

import csv
import logging
import os
import random
from pathlib import Path

import psycopg
import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg.connect(url)


def _fetch(cur, where_sql: str, params: tuple, limit: int) -> list[dict]:
    cur.execute(
        f"""
        SELECT target_entity_uid, target_source, target_name, target_jurisdiction,
               ref_entity_uid, ref_source, ref_name, ref_jurisdiction, ref_lei,
               score, score_band
        FROM shellnet.list_matches
        WHERE {where_sql}
        ORDER BY random()
        LIMIT %s
        """,
        params + (limit,),
    )
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def _token_set(name: str | None) -> set[str]:
    return {t for t in (name or "").lower().split() if t}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _classify(target_name, ref_name, target_jur, ref_jur) -> str:
    t = (target_name or "").strip()
    r = (ref_name or "").strip()
    if not t or not r:
        return "missing_name"
    if t.casefold() == r.casefold():
        return "identical"
    tj = (target_jur or "").strip().lower()
    rj = (ref_jur or "").strip().lower()
    same_jur = bool(tj) and tj == rj
    sim = _jaccard(_token_set(t), _token_set(r))
    if same_jur and sim >= 0.85:
        return "jur_close"
    if same_jur and sim >= 0.70:
        return "jur_loose"
    if not same_jur:
        return "jur_mismatch"
    return "low_overlap"


@app.command()
def main(
    out_csv: Path = typer.Option(Path("data/labels/marginal_v1.csv"), "--out"),
    seed: int = typer.Option(7, "--seed"),
    v1_dropped: int = typer.Option(100, "--v1-dropped"),
    v2_marginal: int = typer.Option(100, "--v2-marginal"),
    perfect_sanity: int = typer.Option(50, "--perfect-sanity"),
    v2_borderline: int = typer.Option(50, "--v2-borderline"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    random.seed(seed)

    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT run_id, what FROM shellnet.runs "
            "WHERE what LIKE 'list_match:%' ORDER BY created_at DESC"
        )
        runs = cur.fetchall()
        if not runs:
            raise RuntimeError("no list_match runs found")
        # Identify v1 (no _v2 suffix) and v2 (has _v2).
        v1_run = next((r[0] for r in runs if "_v2" not in r[1]), None)
        v2_run = next((r[0] for r in runs if "_v2" in r[1]), None)
        log.info("v1 run %s; v2 run %s", v1_run, v2_run)
        if not v1_run or not v2_run:
            raise RuntimeError("need both v1 and v2 list_match runs in Postgres")

        log.info("sampling v1_dropped (0.85 <= score < 0.92, in v1)")
        v1_dropped_rows = _fetch(
            cur,
            "run_id = %s AND score >= 0.85 AND score < 0.92",
            (str(v1_run),),
            v1_dropped,
        )

        log.info("sampling v2_marginal (0.92 <= score < 0.97, in v2)")
        v2_marginal_rows = _fetch(
            cur,
            "run_id = %s AND score >= 0.92 AND score < 0.97",
            (str(v2_run),),
            v2_marginal,
        )

        log.info("sampling perfect_sanity (score >= 0.99, in v1)")
        perfect_rows = _fetch(
            cur,
            "run_id = %s AND score >= 0.99",
            (str(v1_run),),
            perfect_sanity,
        )

        log.info("sampling v2_borderline (in v2)")
        # heuristic-class filter happens after fetch; jur_close+jur_loose are
        # ~6% of the v2 distribution so we need a generous oversample.
        v2_borderline_rows = _fetch(
            cur,
            "run_id = %s AND score >= 0.85",
            (str(v2_run),),
            5630,  # entire v2 distribution; randomized order
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # Pre-classify everything, filter v2_borderline by class.
    def annotate(rows, bucket: str, run_tag: str) -> list[dict]:
        for r in rows:
            r["heuristic_class"] = _classify(
                r.get("target_name"),
                r.get("ref_name"),
                r.get("target_jurisdiction"),
                r.get("ref_jurisdiction"),
            )
            r["bucket"] = bucket
            r["source_run"] = run_tag
        return rows

    v1_dropped_rows = annotate(v1_dropped_rows, "v1_dropped", "v1")
    v2_marginal_rows = annotate(v2_marginal_rows, "v2_marginal", "v2")
    perfect_rows = annotate(perfect_rows, "perfect_sanity", "v1")
    v2_borderline_rows = annotate(v2_borderline_rows, "v2_borderline_class", "v2")
    v2_borderline_rows = [
        r for r in v2_borderline_rows if r["heuristic_class"] in {"jur_close", "jur_loose"}
    ][:v2_borderline]

    all_rows = v1_dropped_rows + v2_marginal_rows + perfect_rows + v2_borderline_rows
    log.info(
        "totals: v1_dropped=%d, v2_marginal=%d, perfect_sanity=%d, "
        "v2_borderline_class=%d -> %d rows",
        len(v1_dropped_rows),
        len(v2_marginal_rows),
        len(perfect_rows),
        len(v2_borderline_rows),
        len(all_rows),
    )

    fieldnames = [
        "pair_id",
        "bucket",
        "source_run",
        "target_entity_uid",
        "target_source",
        "target_name",
        "target_jurisdiction",
        "ref_entity_uid",
        "ref_source",
        "ref_name",
        "ref_jurisdiction",
        "ref_lei",
        "score",
        "score_band",
        "heuristic_class",
        "label",
        "rationale",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for i, r in enumerate(all_rows, start=1):
            r["pair_id"] = f"P{i:04d}"
            r["label"] = ""
            r["rationale"] = ""
            r["score"] = round(float(r["score"]), 4)
            w.writerow({k: r.get(k, "") for k in fieldnames})
    log.info("wrote %s (%d rows)", out_csv, len(all_rows))
    print(str(out_csv))


if __name__ == "__main__":
    app()
