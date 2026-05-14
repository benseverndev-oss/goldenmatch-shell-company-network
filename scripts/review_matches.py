"""Heuristic precision review of a GoldenMatch list-match output.

We don't have human labels, so this classifies each ``target -> ref`` pair
by a set of cheap heuristics and reports the distribution. The intent is
to estimate where the false-positive risk lives, not to ground-truth the
matches.

Classifications, in order of trust:

1. ``identical``      — target_name == ref_name (after casefold + strip)
2. ``normalized_eq``  — same canonical token sequence after legal-suffix strip
3. ``jur_close``      — jurisdiction matches AND token-sort ratio >= 0.85
4. ``jur_loose``      — jurisdiction matches AND token-sort ratio >= 0.70
5. ``jur_mismatch``   — different jurisdictions (high FP risk)
6. ``low_overlap``    — same jurisdiction but token-sort ratio < 0.70

For each bucket we report counts + a small random sample so the user can
eyeball quality. Suspect buckets (5 + 6) get a bigger sample.
"""

from __future__ import annotations

import csv
import logging
import random
from collections import Counter, defaultdict
from pathlib import Path

import typer

from shellnet.normalize import normalize_company_name, tokenize_name

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


def _token_sort_ratio(a: str, b: str) -> float:
    """Cheap token-sort similarity in [0,1]. No external deps."""
    ta = sorted(tokenize_name(a))
    tb = sorted(tokenize_name(b))
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    sa = " ".join(ta)
    sb = " ".join(tb)
    # Levenshtein ratio via difflib (no rapidfuzz import needed; this is
    # script-only and ~20k rows so speed is fine).
    import difflib

    return difflib.SequenceMatcher(None, sa, sb).ratio()


def _classify(row: dict[str, str]) -> str:
    t = (row.get("target_name") or "").strip()
    r = (row.get("ref_name") or "").strip()
    if not t or not r:
        return "missing_name"
    if t.casefold() == r.casefold():
        return "identical"
    if normalize_company_name(t) == normalize_company_name(r):
        return "normalized_eq"

    tj = (row.get("target_jurisdiction") or "").strip().lower()
    rj = (row.get("ref_jurisdiction") or "").strip().lower()
    same_jur = bool(tj) and tj == rj
    sim = _token_sort_ratio(t, r)

    if same_jur and sim >= 0.85:
        return "jur_close"
    if same_jur and sim >= 0.70:
        return "jur_loose"
    if not same_jur:
        return "jur_mismatch"
    return "low_overlap"


@app.command()
def main(
    matched_csv: Path = typer.Option(
        Path("/data/reports/generated/icij_os_vs_gleif_matched.csv"),
        "--matched-csv",
    ),
    sample_size: int = typer.Option(8, "--sample-size"),
    suspect_sample_size: int = typer.Option(20, "--suspect-sample-size"),
    out_md: Path = typer.Option(
        Path("/data/reports/generated/icij_os_vs_gleif_review.md"),
        "--out-md",
    ),
    seed: int = typer.Option(0, "--seed"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    random.seed(seed)

    log.info("reading %s", matched_csv)
    rows: list[dict[str, str]] = []
    with matched_csv.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    log.info("loaded %d rows", len(rows))

    by_band: Counter[str] = Counter()
    by_class: Counter[str] = Counter()
    by_band_class: dict[tuple[str, str], int] = defaultdict(int)
    samples: dict[str, list[dict[str, str]]] = defaultdict(list)

    for r in rows:
        score = float(r["__match_score__"])
        band = (
            "perfect"
            if score >= 0.99
            else "high"
            if score >= 0.95
            else "borderline"
            if score >= 0.85
            else "low"
        )
        cls = _classify(r)
        by_band[band] += 1
        by_class[cls] += 1
        by_band_class[(band, cls)] += 1
        samples[cls].append(r)

    lines: list[str] = []
    lines.append("# icij_os_vs_gleif — heuristic precision review")
    lines.append("")
    lines.append(f"Source: `{matched_csv}` — {len(rows)} matched rows")
    lines.append("")
    lines.append("## Counts by score band")
    lines.append("")
    lines.append("| Band | Count |")
    lines.append("| --- | ---: |")
    for b in ("perfect", "high", "borderline", "low"):
        lines.append(f"| {b} | {by_band.get(b, 0)} |")
    lines.append("")
    lines.append("## Counts by heuristic class")
    lines.append("")
    lines.append(
        "Heuristic-only — no human labels. Higher rows = more trust; suspect rows at the bottom."
    )
    lines.append("")
    lines.append("| Class | Count | Share |")
    lines.append("| --- | ---: | ---: |")
    order = [
        "identical",
        "normalized_eq",
        "jur_close",
        "jur_loose",
        "low_overlap",
        "jur_mismatch",
        "missing_name",
    ]
    total = len(rows) or 1
    for cls in order:
        n = by_class.get(cls, 0)
        lines.append(f"| {cls} | {n} | {100 * n / total:.1f}% |")
    lines.append("")
    lines.append("## Crosstab: score band x class")
    lines.append("")
    lines.append("| | " + " | ".join(order) + " |")
    lines.append("| --- " + "| ---: " * len(order) + "|")
    for band in ("perfect", "high", "borderline", "low"):
        row_cells = [band]
        for cls in order:
            row_cells.append(str(by_band_class.get((band, cls), 0)))
        lines.append("| " + " | ".join(row_cells) + " |")
    lines.append("")
    lines.append("## Samples by class")
    lines.append("")
    for cls in order:
        bucket = samples[cls]
        if not bucket:
            continue
        n = suspect_sample_size if cls in {"jur_mismatch", "low_overlap"} else sample_size
        sample = random.sample(bucket, min(n, len(bucket)))
        lines.append(f"### {cls} (n={by_class[cls]}, sample {len(sample)})")
        lines.append("")
        lines.append("| score | target ([src|jur]) | ref ([src|jur]) |")
        lines.append("| ---: | --- | --- |")
        for r in sample:
            tn = (r.get("target_name") or "")[:60].replace("|", "/")
            rn = (r.get("ref_name") or "")[:60].replace("|", "/")
            tj = r.get("target_jurisdiction") or ""
            rj = r.get("ref_jurisdiction") or ""
            ts = r.get("target_source") or ""
            rs = r.get("ref_source") or ""
            lines.append(f"| {r['__match_score__']} | `{tn}` [{ts}|{tj}] | `{rn}` [{rs}|{rj}] |")
        lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote review to %s (%d lines)", out_md, len(lines))

    # Brief stdout summary too.
    print("\n=== HEURISTIC PRECISION SUMMARY ===")
    for cls in order:
        n = by_class.get(cls, 0)
        print(f"  {cls:>15s}: {n:>6d}  ({100 * n / total:.1f}%)")
    high_trust = sum(by_class.get(c, 0) for c in ("identical", "normalized_eq", "jur_close"))
    suspect = sum(by_class.get(c, 0) for c in ("jur_mismatch", "low_overlap"))
    print(
        f"\n  high_trust (identical+normalized_eq+jur_close): {high_trust}  ({100 * high_trust / total:.1f}%)"
    )
    print(
        f"  suspect (jur_mismatch+low_overlap):              {suspect}  ({100 * suspect / total:.1f}%)"
    )


if __name__ == "__main__":
    app()
