"""Pure normalization helpers used everywhere in the pipeline.

All functions here must be deterministic and side-effect-free so they're
safe to use inside Polars expressions and inside tests as fixtures.
"""

from __future__ import annotations

import re
import unicodedata

# Common legal-entity suffixes. Order matters where one is a prefix of
# another: longer multi-token forms first so the substring strip doesn't
# leave stray fragments behind. Each entry is a sequence of normalized
# tokens (lowercased, punctuation already stripped).
_LEGAL_SUFFIX_TOKENS: tuple[tuple[str, ...], ...] = (
    ("societe", "anonyme"),
    ("limited", "liability", "company"),
    ("limited", "partnership"),
    ("public", "limited", "company"),
    ("private", "limited"),
    ("incorporated",),
    ("corporation",),
    ("company",),
    ("limited",),
    ("ltd",),
    ("llc",),
    ("inc",),
    ("corp",),
    ("plc",),
    ("lp",),
    ("llp",),
    ("gmbh",),
    ("ag",),
    ("sa",),
    ("bv",),
    ("nv",),
    ("oy",),
    ("ab",),
    ("trust",),
    ("foundation",),
    ("holdings",),
    ("holding",),
)

_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_WS_RE = re.compile(r"\s+")
# Collapse dotted single-letter sequences ("S.A.", "S.A.R.L.", "U.S.A.") into
# a single token before we strip punctuation, so suffix detection works.
_DOTTED_INITIALS_RE = re.compile(r"(?:\b[a-z]\.){2,}")


def _ascii_fold(s: str) -> str:
    """Strip diacritics via NFKD decomposition, keep ASCII text only."""
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def tokenize_name(name: str) -> list[str]:
    """Lowercase, ASCII-fold, collapse dotted initials, drop punctuation, split."""
    if not name:
        return []
    folded = _ascii_fold(name).lower()
    folded = _DOTTED_INITIALS_RE.sub(lambda m: m.group(0).replace(".", ""), folded)
    cleaned = _PUNCT_RE.sub(" ", folded)
    return [t for t in _WS_RE.split(cleaned) if t]


def normalize_company_name(name: str | None) -> str:
    """Return a normalized form suitable for blocking and string scoring.

    The original is *not* destroyed; callers are expected to keep `name`
    alongside `normalized_name` (see :class:`shellnet.schemas.CompanyEntity`).

    Steps:
      1. Unicode NFKD + ASCII fold + lowercase
      2. Strip punctuation, collapse whitespace
      3. Strip a single trailing run of legal-suffix tokens (cautious:
         only strip from the end, never from the middle, never the only token).
    """
    if not name:
        return ""
    tokens = tokenize_name(name)
    if not tokens:
        return ""
    tokens = _strip_trailing_legal_suffix(tokens)
    return " ".join(tokens)


def _strip_trailing_legal_suffix(tokens: list[str]) -> list[str]:
    """Strip one trailing legal-suffix token sequence if present.

    Never reduces the name to the empty string — if all tokens are
    suffixes ("Trust Foundation"), we return the original tokens untouched.
    """
    for suffix in _LEGAL_SUFFIX_TOKENS:
        n = len(suffix)
        if len(tokens) > n and tuple(tokens[-n:]) == suffix:
            return tokens[:-n]
    return tokens


_ALPHA3_TO_ALPHA2: dict[str, str] = {
    # Just the codes that show up in the public datasets we touch. Extend as
    # needed; we deliberately don't pull in a full ISO library for one column.
    "gbr": "gb", "usa": "us", "vgb": "vg", "kym": "ky", "pan": "pa",
    "bhs": "bs", "bmu": "bm", "che": "ch", "lux": "lu", "deu": "de",
    "fra": "fr", "nld": "nl", "rus": "ru", "hkg": "hk", "sgp": "sg",
    "lie": "li", "irl": "ie", "isl": "is", "ita": "it", "esp": "es",
    "prt": "pt", "dnk": "dk", "swe": "se", "nor": "no", "fin": "fi",
    "cyp": "cy", "mlt": "mt", "are": "ae", "sau": "sa", "isr": "il",
    "jpn": "jp", "chn": "cn", "kor": "kr", "ind": "in", "bra": "br",
    "mex": "mx", "can": "ca", "aus": "au", "nzl": "nz", "zaf": "za",
    "mco": "mc", "and": "ad", "smr": "sm", "vat": "va", "jey": "je",
    "ggy": "gg", "imn": "im", "gib": "gi",
}

_JURISDICTION_ALIASES: dict[str, str] = {
    "united kingdom": "gb",
    "great britain": "gb",
    "england": "gb",
    "uk": "gb",
    "u.k.": "gb",
    "scotland": "gb",
    "wales": "gb",
    "united states": "us",
    "united states of america": "us",
    "usa": "us",
    "u.s.": "us",
    "u.s.a.": "us",
    "british virgin islands": "vg",
    "bvi": "vg",
    "cayman islands": "ky",
    "panama": "pa",
    "bahamas": "bs",
    "bermuda": "bm",
    "switzerland": "ch",
    "luxembourg": "lu",
    "germany": "de",
    "france": "fr",
    "netherlands": "nl",
    "the netherlands": "nl",
    "russia": "ru",
    "russian federation": "ru",
    "hong kong": "hk",
    "singapore": "sg",
}


def normalize_jurisdiction(value: str | None) -> str | None:
    """Coerce a country/jurisdiction string to a lowercase ISO-3166-1 alpha-2.

    Returns ``None`` if we can't confidently map. Callers should preserve the
    raw value separately for audit.
    """
    if not value:
        return None
    s = _ascii_fold(value).strip().lower()
    if not s:
        return None
    # Already a 2-letter code?
    if len(s) == 2 and s.isalpha():
        return s
    # 3-letter ISO code? (ICIJ uses these)
    if len(s) == 3 and s.isalpha() and s in _ALPHA3_TO_ALPHA2:
        return _ALPHA3_TO_ALPHA2[s]
    # OpenCorporates uses forms like "us_de" (state-qualified) — keep country part
    if "_" in s and len(s.split("_", 1)[0]) == 2:
        return s.split("_", 1)[0]
    return _JURISDICTION_ALIASES.get(s)


def normalize_address_text(value: str | None) -> str:
    """Loose normalization for an address line.

    We deliberately don't try to parse structure here — that's a separate
    problem and there are dedicated libraries for it. This is just enough
    to make string comparison and blocking less noisy.
    """
    if not value:
        return ""
    folded = _ascii_fold(value).lower()
    cleaned = _PUNCT_RE.sub(" ", folded)
    return _WS_RE.sub(" ", cleaned).strip()


_IDENTIFIER_KEEP_RE = re.compile(r"[A-Za-z0-9]+")


def normalize_identifier(value: str | None) -> str:
    """Uppercase, strip everything that isn't alphanumeric.

    Good enough for LEIs (20 alphanumerics), most company numbers, and
    OpenCorporates-style identifiers. Returns ``""`` for empty input.
    """
    if not value:
        return ""
    parts = _IDENTIFIER_KEEP_RE.findall(value)
    return "".join(parts).upper()
