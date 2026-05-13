"""Labelled-pair store + evaluator for GoldenMatch outputs.

A *label* is a row of the form ``(left_uid, right_uid, label, source, reason)``
where ``label`` is ``"match"``, ``"no_match"``, or ``"unsure"``. We store
labels as CSV — easy to hand-edit, easy to diff in PRs, easy to import
into GoldenMatch's own ``label`` command later.

We make a careful distinction:

  * **derived** labels are produced automatically by cheap, conservative
    rules — e.g. "same LEI → match", "different LEI on both sides → no_match".
    These are good seed data but they aren't ground truth.
  * **human** labels are the real currency for evaluation. Every label
    carries a ``source`` column so we can filter to humans-only at eval
    time.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import polars as pl

log = logging.getLogger(__name__)

Label = Literal["match", "no_match", "unsure"]
LABEL_VALUES: tuple[Label, ...] = ("match", "no_match", "unsure")

LABEL_COLUMNS: tuple[str, ...] = (
    "left_uid",
    "right_uid",
    "label",
    "source",  # "human:<name>" or "derived:<rule_id>"
    "reason",
)


@dataclass(frozen=True)
class PrecisionRecall:
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int

    @property
    def precision(self) -> float:
        denom = self.true_positive + self.false_positive
        return 0.0 if denom == 0 else self.true_positive / denom

    @property
    def recall(self) -> float:
        denom = self.true_positive + self.false_negative
        return 0.0 if denom == 0 else self.true_positive / denom

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 0.0 if (p + r) == 0 else 2 * p * r / (p + r)

    def as_dict(self) -> dict[str, float | int]:
        return {
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "true_negative": self.true_negative,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
        }


def _empty() -> pl.DataFrame:
    return pl.DataFrame(schema={c: pl.Utf8 for c in LABEL_COLUMNS})


def load_labels(path: Path) -> pl.DataFrame:
    """Load a labels CSV, normalising orientation so ``left_uid < right_uid``."""
    if not path.exists():
        return _empty()
    df = pl.read_csv(path)
    missing = [c for c in LABEL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Labels CSV {path} is missing columns: {missing}")
    df = df.select(list(LABEL_COLUMNS))
    return _canonicalise(df)


def save_labels(df: pl.DataFrame, path: Path) -> Path:
    df = _canonicalise(df.select([c for c in LABEL_COLUMNS if c in df.columns]))
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(path)
    return path


def _canonicalise(df: pl.DataFrame) -> pl.DataFrame:
    """Ensure ``left_uid <= right_uid`` and pairs are unique."""
    if df.height == 0:
        return df
    swapped = df.with_columns(
        pl.when(pl.col("left_uid") <= pl.col("right_uid"))
        .then(pl.col("left_uid"))
        .otherwise(pl.col("right_uid"))
        .alias("_a"),
        pl.when(pl.col("left_uid") <= pl.col("right_uid"))
        .then(pl.col("right_uid"))
        .otherwise(pl.col("left_uid"))
        .alias("_b"),
    )
    return (
        swapped.with_columns(pl.col("_a").alias("left_uid"), pl.col("_b").alias("right_uid"))
        .drop("_a", "_b")
        .unique(subset=["left_uid", "right_uid"], keep="last")
    )


def derive_seed_labels(company_table: Path) -> pl.DataFrame:
    """Produce cheap, conservative labels from the unified company table.

    Rules (all very high-confidence):
      * Two rows share a non-empty LEI → ``match``.
      * Two rows share a non-empty (company_number, jurisdiction) tuple → ``match``.
      * Two rows have non-empty LEIs that differ AND a normalized_name in
        common → ``no_match``. (Same name + different LEI is a strong signal
        of distinct entities; the LEI is a registry-authoritative ID.)

    These are *derived*, not human-labelled. They're fine to use as seeds
    and as a sanity check on the matcher; they shouldn't be the only
    ground-truth source.
    """
    df = pl.read_parquet(company_table)
    seeds: list[dict[str, str]] = []

    seeds.extend(_pairs_sharing(df, key="lei", reason="shared_lei", label="match"))
    seeds.extend(
        _pairs_sharing(
            df.with_columns((pl.col("company_number") + "|" + pl.col("jurisdiction")).alias("_cn")),
            key="_cn",
            reason="shared_company_number_jurisdiction",
            label="match",
        )
    )
    seeds.extend(_pairs_diverging_lei(df))

    if not seeds:
        return _empty()
    return _canonicalise(pl.DataFrame(seeds))


def _pairs_sharing(
    df: pl.DataFrame, *, key: str, reason: str, label: Label
) -> list[dict[str, str]]:
    """Emit pairs from rows that share a non-empty ``key`` value."""
    if key not in df.columns:
        return []
    work = df.filter(pl.col(key).is_not_null() & (pl.col(key) != "") & (pl.col(key) != "|"))
    if work.height < 2:
        return []
    out: list[dict[str, str]] = []
    for value, group in work.group_by(key):
        uids = sorted(group["entity_uid"].to_list())
        if len(uids) < 2:
            continue
        # Polars returns group keys as 1-tuples; unwrap so the audit string
        # reads "key=actual_value" instead of "key=('actual_value',)".
        value_str = value[0] if isinstance(value, tuple) else value
        for i in range(len(uids)):
            for j in range(i + 1, len(uids)):
                out.append(
                    {
                        "left_uid": uids[i],
                        "right_uid": uids[j],
                        "label": label,
                        "source": f"derived:{reason}",
                        "reason": f"{key}={value_str}",
                    }
                )
    return out


def _pairs_diverging_lei(df: pl.DataFrame) -> list[dict[str, str]]:
    """Same normalized_name, different non-empty LEIs → ``no_match``."""
    if "lei" not in df.columns or "normalized_name" not in df.columns:
        return []
    work = df.filter(
        pl.col("lei").is_not_null()
        & (pl.col("lei") != "")
        & pl.col("normalized_name").is_not_null()
        & (pl.col("normalized_name") != "")
    )
    if work.height < 2:
        return []
    out: list[dict[str, str]] = []
    for name, group in work.group_by("normalized_name"):
        name_str = name[0] if isinstance(name, tuple) else name
        uids_leis = sorted(zip(group["entity_uid"].to_list(), group["lei"].to_list(), strict=True))
        for i in range(len(uids_leis)):
            for j in range(i + 1, len(uids_leis)):
                if uids_leis[i][1] != uids_leis[j][1]:
                    out.append(
                        {
                            "left_uid": uids_leis[i][0],
                            "right_uid": uids_leis[j][0],
                            "label": "no_match",
                            "source": "derived:divergent_lei_same_name",
                            "reason": f"name={name_str} leis={uids_leis[i][1]}!={uids_leis[j][1]}",
                        }
                    )
    return out


def evaluate(
    predicted_pairs: Iterable[tuple[str, str]],
    labels: pl.DataFrame,
    *,
    sources: tuple[str, ...] | None = None,
) -> PrecisionRecall:
    """Compute precision/recall/F1 over a labelled set.

    ``predicted_pairs`` is the set the matcher *says* are the same entity.
    ``labels`` is the ground-truth table; rows with ``label == "unsure"``
    are excluded.

    ``sources`` filters labels (e.g. only `("human:*",)`); pass ``None`` to
    use all labels regardless of provenance.
    """
    labels = _canonicalise(labels).filter(pl.col("label") != "unsure")
    if sources is not None:
        # Treat sources as prefixes — "human:" matches "human:alice".
        mask = None
        for prefix in sources:
            m = pl.col("source").str.starts_with(prefix)
            mask = m if mask is None else (mask | m)
        labels = labels.filter(mask if mask is not None else pl.lit(False))

    def _key(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a <= b else (b, a)

    pred = {_key(a, b) for a, b in predicted_pairs}
    truth_match = {
        _key(r["left_uid"], r["right_uid"])
        for r in labels.filter(pl.col("label") == "match").iter_rows(named=True)
    }
    truth_no = {
        _key(r["left_uid"], r["right_uid"])
        for r in labels.filter(pl.col("label") == "no_match").iter_rows(named=True)
    }
    tp = len(pred & truth_match)
    fp = len(pred & truth_no)
    fn = len(truth_match - pred)
    tn = len(truth_no - pred)
    return PrecisionRecall(true_positive=tp, false_positive=fp, false_negative=fn, true_negative=tn)
