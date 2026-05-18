"""Adversarial-robustness benchmark for the ER pipeline.

For each rare-anchor name, generate synthetic perturbations that
model what an adversary trying to defeat cross-source matching would
do:

- **suffix_mutation**: swap legal suffix (ltd↔limited↔llc↔inc↔holdings)
- **honorific_insertion**: prepend mr/ms/dr/sheikh
- **transliteration**: char-level substitutions modelling slavic /
  arabic transliteration variance (i↔y, kh↔h, sh↔sch, ts↔z, ee↔ie)
- **token_reorder_drop**: shuffle middle tokens, drop one if ≥4 tokens

Then measure two baselines' recovery:

- **B2 recovery** = `normalize_company_name(perturbed) == anchor.normalized_name`.
  The normalize layer should defeat suffix + honorific by design; should
  fail on transliteration + token reorder.
- **B6 recovery** = `token_set_ratio(perturbed, anchor.normalized_name) ≥ 85`.
  Fuzzy is more permissive — should recover suffix + honorific + some
  token-reorder, fail on transliteration when chars actually change.

Output: per-perturbation recovery rates + per-anchor detail. The
honest reading the paper needs: where DOES the pipeline fail
against a determined adversary, and which adversary moves does it
defeat?
"""

from __future__ import annotations

import json
import logging
import random
import re
from collections.abc import Callable
from pathlib import Path

import polars as pl
import typer
from rapidfuzz import fuzz

from shellnet.normalize import normalize_company_name
from shellnet.paths import PROCESSED_DIR, ensure_dirs

app = typer.Typer(add_completion=False, no_args_is_help=False)
log = logging.getLogger(__name__)


# --- perturbation primitives ------------------------------------------------

_SUFFIXES = [
    "ltd",
    "limited",
    "llc",
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "plc",
    "holdings",
    "group",
    "co",
]
_HONORIFICS = ["mr", "ms", "mrs", "dr", "sheikh", "sir", "prof"]

# Character-level substitutions modelling transliteration variance.
# Apply at most 2 substitutions per name to avoid mangling beyond recognition.
_TRANSLIT_SUBS: list[tuple[str, str]] = [
    ("kh", "h"),
    ("ts", "z"),
    ("sh", "sch"),
    ("ee", "ie"),
    ("y", "i"),
    ("v", "w"),
    ("ph", "f"),
    ("ck", "k"),
    ("oo", "u"),
]


def _suffix_mutation(rng: random.Random, name: str) -> str:
    """Append or swap a legal suffix not already present."""
    tokens = name.split()
    # If a suffix is already at the end, swap to a different one.
    if tokens and tokens[-1] in _SUFFIXES:
        new_suffix = rng.choice([s for s in _SUFFIXES if s != tokens[-1]])
        tokens[-1] = new_suffix
    else:
        tokens.append(rng.choice(_SUFFIXES))
    return " ".join(tokens)


def _honorific_insertion(rng: random.Random, name: str) -> str:
    """Prepend a random honorific."""
    tokens = name.split()
    # If already honorific-prefixed, replace.
    if tokens and tokens[0] in _HONORIFICS:
        tokens[0] = rng.choice([h for h in _HONORIFICS if h != tokens[0]])
        return " ".join(tokens)
    return rng.choice(_HONORIFICS) + " " + name


def _transliteration(rng: random.Random, name: str) -> str:
    """Apply 1-2 random character-level substitutions."""
    candidates = [(old, new) for old, new in _TRANSLIT_SUBS if old in name]
    if not candidates:
        # Fall back to a single-char vowel swap.
        vowel_swaps = [("a", "e"), ("e", "a"), ("o", "u"), ("i", "y")]
        candidates = [(o, n) for o, n in vowel_swaps if o in name]
    if not candidates:
        return name  # no applicable substitution
    n_subs = rng.randint(1, min(2, len(candidates)))
    chosen = rng.sample(candidates, n_subs)
    out = name
    for old, new in chosen:
        # Replace only the first occurrence to avoid over-mangling.
        out = re.sub(re.escape(old), new, out, count=1)
    return out


def _token_reorder_drop(rng: random.Random, name: str) -> str:
    """Shuffle middle tokens; drop one if ≥4 tokens."""
    tokens = name.split()
    if len(tokens) < 3:
        return name  # not enough room to shuffle middles
    first, middles, last = tokens[0], tokens[1:-1], tokens[-1]
    if len(tokens) >= 4 and rng.random() < 0.5:
        # Drop a random middle token.
        drop_idx = rng.randrange(len(middles))
        middles = middles[:drop_idx] + middles[drop_idx + 1 :]
    if len(middles) > 1:
        rng.shuffle(middles)
    return " ".join([first, *middles, last])


_PERTURBATIONS: dict[str, Callable[[random.Random, str], str]] = {
    "suffix_mutation": _suffix_mutation,
    "honorific_insertion": _honorific_insertion,
    "transliteration": _transliteration,
    "token_reorder_drop": _token_reorder_drop,
}


# --- benchmark --------------------------------------------------------------


@app.command()
def main(
    discovery_parquet: Path = typer.Option(
        PROCESSED_DIR / "discovery_lift.parquet",
        "--discovery-parquet",
    ),
    out_parquet: Path = typer.Option(
        PROCESSED_DIR / "adversarial_benchmark.parquet",
        "--out-parquet",
    ),
    out_summary: Path = typer.Option(
        PROCESSED_DIR / "adversarial_benchmark_summary.json",
        "--out-summary",
    ),
    sample_size: int = typer.Option(
        500,
        "--sample-size",
        help="B3 anchors to perturb. 500 yields ~2000 perturbed evaluations.",
    ),
    fuzzy_threshold: int = typer.Option(85, "--fuzzy-threshold"),
    seed: int = typer.Option(42, "--seed"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_dirs()
    out_parquet.parent.mkdir(parents=True, exist_ok=True)

    disc = pl.read_parquet(discovery_parquet)
    b3 = disc.filter(pl.col("reachable_b3"))
    log.info("B3 anchor set: %d", b3.height)

    b3_sample = b3.sample(n=sample_size, seed=seed) if b3.height > sample_size else b3
    log.info("perturbing %d anchors", b3_sample.height)

    rng = random.Random(seed)
    rows: list[dict] = []
    for r in b3_sample.iter_rows(named=True):
        anchor = r["name_b2"]
        for ptype, fn in _PERTURBATIONS.items():
            perturbed = fn(rng, anchor)
            perturbed_normalized = normalize_company_name(perturbed)
            b2_recovers = perturbed_normalized == anchor
            b6_score = fuzz.token_set_ratio(perturbed_normalized, anchor)
            b6_recovers = b6_score >= fuzzy_threshold
            rows.append(
                {
                    "anchor": anchor,
                    "perturbation": ptype,
                    "perturbed": perturbed,
                    "perturbed_normalized": perturbed_normalized,
                    "b2_recovers": b2_recovers,
                    "b6_score": int(b6_score),
                    "b6_recovers": b6_recovers,
                }
            )

    df = pl.DataFrame(rows)
    log.info("total perturbed pairs: %d", df.height)

    by_pert = (
        df.group_by("perturbation")
        .agg(
            pl.len().alias("n"),
            pl.col("b2_recovers").sum().alias("b2_hits"),
            pl.col("b6_recovers").sum().alias("b6_hits"),
            pl.col("b6_score").mean().alias("b6_mean_score"),
        )
        .with_columns(
            (pl.col("b2_hits") / pl.col("n")).alias("b2_recovery_rate"),
            (pl.col("b6_hits") / pl.col("n")).alias("b6_recovery_rate"),
        )
        .sort("perturbation")
    )
    log.info("per-perturbation recovery:")
    for r in by_pert.iter_rows(named=True):
        log.info(
            "  %s: B2 %.1f%% (%d/%d), B6 %.1f%% (%d/%d, mean score %.1f)",
            r["perturbation"],
            r["b2_recovery_rate"] * 100,
            int(r["b2_hits"]),
            int(r["n"]),
            r["b6_recovery_rate"] * 100,
            int(r["b6_hits"]),
            int(r["n"]),
            r["b6_mean_score"],
        )

    df.write_parquet(out_parquet)

    summary = {
        "sample_size": int(b3_sample.height),
        "b3_population": int(b3.height),
        "fuzzy_threshold": fuzzy_threshold,
        "perturbation_types": list(_PERTURBATIONS.keys()),
        "by_perturbation": by_pert.to_dicts(),
        "overall": {
            "n_perturbed_pairs": int(df.height),
            "b2_recovery_rate": (int(df["b2_recovers"].sum()) / df.height if df.height else 0.0),
            "b6_recovery_rate": (int(df["b6_recovers"].sum()) / df.height if df.height else 0.0),
        },
        "adversary_model_notes": (
            "Perturbations model what an adversary controls in the threat model "
            "documented in docs/paper/methodology.md §1.5. Each perturbation "
            "represents one of: legal-form jurisdiction shopping (suffix_mutation), "
            "salutation inflation (honorific_insertion), transliteration variance "
            "across registries (transliteration), or name-form variants used to "
            "evade exact-match dedupe (token_reorder_drop)."
        ),
    }
    out_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    typer.echo(f"Wrote: {out_parquet}")
    typer.echo(f"Wrote: {out_summary}")


if __name__ == "__main__":
    app()
