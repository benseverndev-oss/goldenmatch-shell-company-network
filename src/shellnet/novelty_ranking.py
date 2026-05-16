"""Novelty scoring for the exposé-candidates pipeline.

Pure function — no I/O, no parquet reads. Imported by render_dossiers.py.
Spec: docs/superpowers/specs/2026-05-16-expose-candidates-design.md
"""

from __future__ import annotations


def novelty_score(
    *,
    hits_general: int,
    hits_offshore: int,
    hits_localized: int,
    localized_ran: bool,
    n_linked_companies: int,
    n_jurisdictions: int,
) -> float:
    """Weighted novelty score in [0, 1].

    Weights are constants locked by unit tests. The spec's earlier draft
    spoke of "operator-tunable via CLI flags"; we reject that as YAGNI —
    changing weights requires touching this function AND updating the
    tests, which is the review gate. Spec amended to match.

    ``localized_ran`` must be True only when the localized firecrawl query
    was actually emitted (the dominant-jurisdiction plurality test passed).
    Skipped-query runs MUST pass False, otherwise every name without a
    dominant jurisdiction gets a free 0.15 bonus — the bug spotted in
    review pass 2.
    """
    offshore_term = 0.40 * (1 - min(hits_offshore / 5, 1.0))
    general_term = 0.25 * (1 - min(hits_general / 10, 1.0))
    localized_term = 0.15 if (localized_ran and hits_localized == 0) else 0.0
    company_density = 0.10 * min(n_linked_companies / 5, 1.0)
    jurisdiction_density = 0.10 * min(n_jurisdictions / 3, 1.0)
    return offshore_term + general_term + localized_term + company_density + jurisdiction_density


def auto_pin(
    *,
    hits_general: int,
    hits_offshore: int,
    n_linked_companies: int,
) -> bool:
    """Whether a candidate gets pinned to the top of the index regardless of score.

    The cleanest 'found-X-first' shape: zero web mentions anywhere AND
    a non-trivial shell-network footprint.
    """
    return hits_general == 0 and hits_offshore == 0 and n_linked_companies >= 3
