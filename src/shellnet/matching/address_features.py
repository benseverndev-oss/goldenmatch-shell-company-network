"""Address-side helpers used during candidate generation.

We do not try to do real address parsing here (libpostal etc.). Instead we
emit a coarse "country + first-token + postal-code" blocking key which is
good enough to narrow the candidate space without hiding genuine matches.
"""

from __future__ import annotations

import re

import polars as pl

from shellnet.normalize import normalize_address_text

_POSTAL_RE = re.compile(r"\b[A-Z0-9]{3,10}(?:[-\s][A-Z0-9]{2,5})?\b")


def address_blocking_key(addr: str | None, country: str | None) -> str:
    """Return a coarse blocking key for an address line.

    Format: ``"<country>|<first-token>|<postal>"``. Empty parts are kept as
    empty strings so the column shape is stable.
    """
    if not addr:
        return f"{country or ''}||"
    norm = normalize_address_text(addr)
    if not norm:
        return f"{country or ''}||"
    first_token = norm.split(" ", 1)[0]
    upper = addr.upper()
    postal_match = _POSTAL_RE.search(upper)
    postal = postal_match.group(0) if postal_match else ""
    return f"{(country or '').lower()}|{first_token}|{postal}"


def add_address_blocking(df: pl.DataFrame) -> pl.DataFrame:
    """Add an ``address_block`` column to a unified company table."""
    return df.with_columns(
        pl.struct(["normalized_address", "jurisdiction"])
        .map_elements(
            lambda row: address_blocking_key(row["normalized_address"], row["jurisdiction"]),
            return_dtype=pl.Utf8,
        )
        .alias("address_block")
    )
