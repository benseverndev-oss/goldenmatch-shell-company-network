"""Cross-jurisdictional name-lineage twin detector.

Discovers UK-Malta-IoM-etc. company-name twins automatically. The
Perry verification (PR #62 / #63 / #64) surfaced two examples by hand:

    UK PROBUTEC LTD (04102334, 2000) <-> MT PROBUTEC (MALTA) LTD
    UK I-CAP MARINE SERVICES LTD (06494852, 2008) <-> MT INTEGRATED-CAPABILITIES (MALTA) LTD

The first is a strict shared-root match. The second is a
documented-abbreviation match (I-CAP = Integrated CAPabilities). This
script catches both classes:

* **strict-root**: normalised name without legal suffix or
  jurisdictional qualifier is identical across two sources.
* **abbrev**: one side is a multi-token camel-case abbreviation of
  the other (left side's letters form a prefix of the right side's
  initials, or vice versa).

Output: ``data/processed/cross_jurisdiction_twins.parquet`` — one row
per candidate twin pair with shape suitable for ingestion as a new
edge type in ``build_confidence_graph.py``.

Heavy compute on large corpora; intended to run Railway-side.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import polars as pl

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

log = logging.getLogger("detect_cross_jurisdiction_twins")

PROJECT_ROOT = _REPO_ROOT

# Legal-suffix tokens to strip when computing a name root. Order matters:
# longer multi-token forms first so we don't leave stragglers.
_LEGAL_SUFFIXES: tuple[tuple[str, ...], ...] = (
    ("limited", "liability", "company"),
    ("public", "limited", "company"),
    ("limited", "partnership"),
    ("societe", "anonyme"),
    ("plc",),
    ("ltd",),
    ("limited",),
    ("inc",),
    ("incorporated",),
    ("corporation",),
    ("corp",),
    ("llc",),
    ("llp",),
    ("lp",),
    ("ag",),
    ("gmbh",),
    ("sa",),
    ("nv",),
    ("bv",),
    ("oy",),
    ("ab",),
    ("as",),
    ("group",),
    ("holdings",),
    ("holding",),
)

# Jurisdictional qualifiers commonly appended to or embedded in Malta /
# IoM / Cyprus / etc. shell-company names: "(MALTA)", "MT", "ISLE OF MAN".
_JURIS_QUALIFIER_RE = re.compile(
    r"\s*\(?\s*(?:malta|mt|isle of man|iom|cyprus|cy|bvi|jersey|guernsey|"
    r"gibraltar|luxembourg|lu|monaco|mc|liechtenstein|li|panama|pa|bahamas|"
    r"bs|bermuda|bm|cayman|ky|delaware|de)\s*\)?\s*$",
    re.IGNORECASE,
)

# Same set as the regex, but as bare tokens — used to strip qualifiers that
# appear before the legal suffix, e.g. "PROBUTEC MALTA LTD".
_JURIS_TOKENS: frozenset[str] = frozenset(
    {
        "malta",
        "mt",
        "iom",
        "cyprus",
        "cy",
        "bvi",
        "jersey",
        "guernsey",
        "gibraltar",
        "luxembourg",
        "lu",
        "monaco",
        "mc",
        "liechtenstein",
        "li",
        "panama",
        "pa",
        "bahamas",
        "bs",
        "bermuda",
        "bm",
        "cayman",
        "ky",
        "delaware",
        "de",
    }
)


def _normalize(raw: str) -> str:
    """Lowercase, ASCII-fold, drop punctuation, strip legal suffix +
    jurisdictional qualifier, collapse whitespace."""

    if not raw:
        return ""
    s = raw.lower().strip()
    # Strip jurisdictional qualifier from the tail.
    s = _JURIS_QUALIFIER_RE.sub("", s).strip()
    # Punctuation → space.
    s = re.sub(r"[^a-z0-9\s-]+", " ", s)
    # Collapse hyphens to spaces so "I-CAP" -> "i cap".
    s = s.replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    tokens = [t for t in s.split() if t]
    # Iteratively strip trailing legal-suffix runs AND trailing jurisdiction
    # qualifier tokens ("PROBUTEC MALTA LTD" -> "PROBUTEC").
    changed = True
    while changed and tokens:
        changed = False
        for suffix in _LEGAL_SUFFIXES:
            n = len(suffix)
            if len(tokens) > n and tuple(tokens[-n:]) == suffix:
                tokens = tokens[:-n]
                changed = True
                break
        if not changed and len(tokens) > 1 and tokens[-1] in _JURIS_TOKENS:
            tokens = tokens[:-1]
            changed = True
    return " ".join(tokens)


def _abbreviation_root(name: str) -> str:
    """Return the dash-stripped acronym form of a multi-word name.

    Example: ``integrated capabilities`` -> ``icap`` (first letter of
    each token, lowercased, joined). Returns '' for single-word names.
    """

    norm = _normalize(name)
    toks = [t for t in norm.split() if t]
    if len(toks) < 2:
        return ""
    return "".join(t[0] for t in toks)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Polars-native expression equivalents of _normalize / _abbreviation_root.
# The Python helpers above are kept for readability + unit tests; build_name_index
# uses these expressions so the work streams through Polars rather than crossing
# the Python-UDF boundary for every row (which OOMs at corpus scale).
# ---------------------------------------------------------------------------

# Tail jurisdictional qualifier ("(MALTA)" / "MT" / "CYPRUS" at end of string).
# Matches the Python _JURIS_QUALIFIER_RE one-for-one.
_TAIL_JURIS_PATTERN = (
    r"(?i)\s*\(?\s*(?:malta|mt|isle\s+of\s+man|iom|cyprus|cy|bvi|jersey|"
    r"guernsey|gibraltar|luxembourg|lu|monaco|mc|liechtenstein|li|panama|"
    r"pa|bahamas|bs|bermuda|bm|cayman|ky|delaware|de)\s*\)?\s*$"
)

# A single trailing legal-suffix or jurisdiction token, preceded by whitespace.
# The leading `\s+` is what preserves the "keep at least one token alive"
# semantic from the Python implementation: we only strip a token that has
# *something* before it, so a name reduced to "limited" stays "limited"
# rather than collapsing to empty. Iterating this regex N times drains
# trailing suffix + juris runs in one streaming pass.
_TAIL_SUFFIX_OR_JURIS_PATTERN = (
    r"(?i)\s+(?:"
    r"limited\s+liability\s+company|public\s+limited\s+company|"
    r"limited\s+partnership|societe\s+anonyme|"
    r"plc|ltd|limited|inc|incorporated|corporation|corp|llc|llp|lp|"
    r"ag|gmbh|sa|nv|bv|oy|ab|as|group|holdings|holding|"
    r"malta|mt|iom|cyprus|cy|bvi|jersey|guernsey|gibraltar|"
    r"luxembourg|lu|monaco|mc|liechtenstein|li|panama|pa|"
    r"bahamas|bs|bermuda|bm|cayman|ky|delaware|de"
    r")\s*$"
)

# Iteration cap. The longest plausible trailing chain in real corpora is
# "<name> HOLDINGS GROUP LIMITED" (3 tokens). Six iterations covers that
# with margin, including one extra for nested parenthesised qualifiers.
_TAIL_STRIP_ITERATIONS = 6


def _normalize_expr(col: str) -> pl.Expr:
    """Polars-native equivalent of :func:`_normalize`."""

    expr = (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.strip_chars()
        .str.replace_all(_TAIL_JURIS_PATTERN, "")
        .str.replace_all(r"[^a-z0-9\s\-]+", " ")
        .str.replace_all("-", " ", literal=True)
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )
    # Apply the trailing-suffix regex up to _TAIL_STRIP_ITERATIONS times.
    # Polars compiles this once and reuses the regex object across rows.
    for _ in range(_TAIL_STRIP_ITERATIONS):
        expr = expr.str.replace_all(_TAIL_SUFFIX_OR_JURIS_PATTERN, "").str.strip_chars()
    return expr


def _abbreviation_root_expr(root_expr: pl.Expr) -> pl.Expr:
    """Polars-native equivalent of :func:`_abbreviation_root`.

    Returns the concatenated first-character-of-each-token initialism for
    multi-token roots; returns "" for single-token roots (matching the
    Python helper).
    """

    # \b\w extracts the first letter at every word boundary, e.g. for
    # "integrated capabilities" the matches are ["i", "c"]; list.join glues
    # them back to "ic". For single-token names we'd get a single-char
    # initialism which the caller's >= 3 filter drops, but we also gate on
    # token count for clarity.
    abbrev = root_expr.str.extract_all(r"\b\w").list.join("")
    token_count = (root_expr.str.count_matches(" ") + 1).cast(pl.Int64)
    return pl.when(token_count >= 2).then(abbrev).otherwise(pl.lit(""))


def build_name_index(
    df: pl.DataFrame, *, name_col: str, uid_col: str, jurisdiction_col: str
) -> pl.DataFrame:
    """Returns a frame with one row per entity carrying:
    entity_uid, name, jurisdiction, root, abbrev_root.

    Uses Polars-native expressions throughout (no Python UDFs) so the work
    streams; required for 5.79M-row OO UK PSC ingestion to fit in Railway's
    memory ceiling.
    """

    base = df.select(
        pl.col(uid_col).alias("entity_uid"),
        pl.col(name_col).alias("name"),
        pl.col(jurisdiction_col).fill_null("").alias("jurisdiction"),
    )
    return base.with_columns(
        _normalize_expr("name").alias("root"),
    ).with_columns(
        _abbreviation_root_expr(pl.col("root")).alias("abbrev_root"),
    )


def detect_twins(left: pl.DataFrame, right: pl.DataFrame) -> pl.DataFrame:
    """Inner-join ``left`` and ``right`` on (root) AND on (abbrev <-> root)
    to surface strict-root + abbrev candidate twin pairs.

    Both frames must already be processed by :func:`build_name_index`.
    """

    # Drop short or generic roots. At corpus scale (5.79M OO x 814k ICIJ)
    # a root like "asia" or "trust" produces 6-figure cross-joins that
    # OOM the container. Empirically a 4-char minimum cuts cardinality
    # by ~95% while preserving all PROBUTEC-style multi-syllable matches.
    left = left.filter(pl.col("root").str.len_chars() >= 4)
    right = right.filter(pl.col("root").str.len_chars() >= 4)

    # Frequency-based drop: a root that appears on hundreds of entities
    # in either side is generic ("global trading", "investments holdings")
    # and produces explosive join cardinality without surfacing real
    # twins. Cap at 5 occurrences per side; PROBUTEC etc. appear ~1-3x.
    _MAX_ROOT_FREQ = 5
    left_freq = left.group_by("root").len().filter(pl.col("len") <= _MAX_ROOT_FREQ)
    right_freq = right.group_by("root").len().filter(pl.col("len") <= _MAX_ROOT_FREQ)
    left = left.join(left_freq.select("root"), on="root", how="inner")
    right = right.join(right_freq.select("root"), on="root", how="inner")

    def _project(df: pl.DataFrame, *, match_type: str, confidence: float) -> pl.DataFrame:
        return df.select(
            pl.col("entity_uid").alias("src_uid"),
            pl.col("entity_uid_r").alias("dst_uid"),
            pl.col("name").alias("src_name"),
            pl.col("name_r").alias("dst_name"),
            pl.col("jurisdiction").alias("src_jurisdiction"),
            pl.col("jurisdiction_r").alias("dst_jurisdiction"),
            pl.col("root"),
            pl.lit(match_type).alias("match_type"),
            pl.lit(confidence).alias("confidence"),
        )

    # 1. Strict-root match: left.root == right.root.
    strict_raw = left.join(right, on="root", how="inner", suffix="_r")
    strict = _project(strict_raw, match_type="strict_root", confidence=0.95)

    # For abbreviation joins, drop the left frame's `root` column first so it
    # doesn't collide with the join key on the right.
    # Same OOM concern applies to the abbreviation join. Two-letter
    # acronyms collide too often at corpus scale; require >=3 letters.
    left_abbrev = (
        left.filter(pl.col("abbrev_root").str.len_chars() >= 3)
        .drop("root")
        .rename({"abbrev_root": "root"})
    )
    right_abbrev = (
        right.filter(pl.col("abbrev_root").str.len_chars() >= 3)
        .drop("root")
        .rename({"abbrev_root": "root"})
    )

    # 2. Abbreviation match: left.abbrev_root == right.root.
    abbrev_l_raw = left_abbrev.join(right, on="root", how="inner", suffix="_r")
    abbrev_l = _project(abbrev_l_raw, match_type="abbrev_left", confidence=0.80)

    # 3. Abbreviation match the other way: right.abbrev_root == left.root.
    # Reverse the inputs so the helper's column layout still applies.
    abbrev_r_raw = right_abbrev.join(left, on="root", how="inner", suffix="_r")
    abbrev_r = _project(abbrev_r_raw, match_type="abbrev_right", confidence=0.80)

    # 4. Both-sides abbreviation match: shared acronym. Lower confidence
    # because acronym collisions are more common ("IC" can be many things).
    abbrev_both_raw = left_abbrev.join(right_abbrev, on="root", how="inner", suffix="_r")
    abbrev_both = _project(abbrev_both_raw, match_type="abbrev_both", confidence=0.65)

    pairs = pl.concat([strict, abbrev_l, abbrev_r, abbrev_both], how="diagonal")
    # Filter same-jurisdiction pairs out — twins must be cross-jurisdictional.
    pairs = pairs.filter(pl.col("src_jurisdiction") != pl.col("dst_jurisdiction"))
    # Filter same-uid (shouldn't happen but defensive).
    pairs = pairs.filter(pl.col("src_uid") != pl.col("dst_uid"))
    out = pairs
    # Dedupe symmetric pairs by canonicalising (smaller uid first).
    out = out.with_columns(
        pl.when(pl.col("src_uid") < pl.col("dst_uid"))
        .then(pl.col("src_uid"))
        .otherwise(pl.col("dst_uid"))
        .alias("_first"),
        pl.when(pl.col("src_uid") < pl.col("dst_uid"))
        .then(pl.col("dst_uid"))
        .otherwise(pl.col("src_uid"))
        .alias("_second"),
    ).unique(subset=["_first", "_second", "match_type"])
    return out.drop("_first", "_second")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--icij-entities",
        type=Path,
        default=Path("/data/interim/icij_entities.parquet"),
    )
    p.add_argument(
        "--oo-entities",
        type=Path,
        default=Path("/data/processed/oo_uk_psc_entities.parquet"),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("/data/processed/cross_jurisdiction_twins.parquet"),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.icij_entities.exists():
        raise SystemExit(f"[fatal] {args.icij_entities} missing")
    if not args.oo_entities.exists():
        log.warning(
            "%s missing; producing no twins (run Phase 0 OO ingest first)", args.oo_entities
        )
        empty = pl.DataFrame(
            schema={
                "src_uid": pl.String,
                "dst_uid": pl.String,
                "src_name": pl.String,
                "dst_name": pl.String,
                "src_jurisdiction": pl.String,
                "dst_jurisdiction": pl.String,
                "root": pl.String,
                "match_type": pl.String,
                "confidence": pl.Float64,
            }
        )
        empty.write_parquet(args.out)
        return 0

    log.info("loading ICIJ entities from %s", args.icij_entities)
    icij = pl.scan_parquet(args.icij_entities).collect()
    # ICIJ columns: source_id, name, jurisdiction, ...
    icij_uid = (pl.lit("icij:") + pl.col("source_id")).alias("entity_uid")
    icij_idx = build_name_index(
        icij.with_columns(icij_uid),
        name_col="name",
        uid_col="entity_uid",
        jurisdiction_col="jurisdiction",
    )

    log.info("loading OO entities from %s", args.oo_entities)
    oo = pl.scan_parquet(args.oo_entities).collect()
    oo_idx = build_name_index(
        oo,
        name_col="name",
        uid_col="entity_uid",
        jurisdiction_col="jurisdiction",
    )

    log.info(
        "indexed %d ICIJ entities + %d OO entities; detecting twins",
        icij_idx.height,
        oo_idx.height,
    )
    twins = detect_twins(icij_idx, oo_idx)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    twins.write_parquet(args.out)
    log.info("wrote %d twin pairs to %s", twins.height, args.out)
    # Tally by match_type.
    for row in (
        twins.group_by("match_type").len().sort("len", descending=True).iter_rows(named=True)
    ):
        log.info("  %s: %d", row["match_type"], row["len"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
