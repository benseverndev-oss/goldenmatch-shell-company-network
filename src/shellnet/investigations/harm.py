"""Public-harm classification (roadmap Phase 3, issue #158).

Turns a company's SIC codes / name into a coarse ``harm_category`` +
``harm_weight`` prior — the "would people care?" axis. Public money, regulated
services, and vulnerable-people sectors weigh highest. This is a *prior for
ranking*, not proof of harm.
"""

from __future__ import annotations

__all__ = [
    "HARM_RULES",
    "CONDUCT_RULES",
    "classify_harm",
    "harm_weight",
    "classify_conduct",
    "conduct_weight",
]

# (category, weight, sic-prefixes, name-keywords). First match by weight wins.
HARM_RULES: list[tuple[str, float, tuple[str, ...], tuple[str, ...]]] = [
    ("childrens_care", 2.0, ("8891", "8790"), ("children's home", "childrens home", "fostering")),
    (
        "adult_social_care",
        1.9,
        ("8710", "8730", "8810", "8899"),
        ("care home", "nursing home", "domiciliary", "home care", "care support", "supported living"),
    ),
    ("health", 1.7, ("86",), ("nhs", "clinic", "hospital", "ambulance", "pharmacy")),
    (
        "social_housing",
        1.6,
        ("6820", "6810"),
        ("housing association", "social housing"),
    ),
    ("education", 1.5, ("85",), ("academy", "school", "college", "nursery")),
    ("public_supplier", 1.5, (), ("council", "ministry", "government", "public sector")),
    ("gambling", 1.3, ("9200",), ("casino", "betting", "gambling", "gaming")),
    # Cyber-hosting / crypto. Keep the data-processing/hosting SICs (6311/6312 —
    # the Aeza bulletproof-host pattern) but drop the *generic financial* prefixes
    # (6419/6499/6630) that mislabelled ordinary consumer-finance firms (e.g. PPI
    # claims) as "crypto_finance".
    (
        "crypto_finance",
        1.3,
        ("6311", "6312"),
        ("crypto", "bitcoin", "blockchain", "digital asset", "virtual currency", "hosting"),
    ),
    ("defence", 1.4, ("2540", "3030"), ("defence", "munitions", "arms")),
    ("energy_utility", 1.2, ("35", "36"), ("energy", "utility", "water", "electricity")),
]

# Conduct severity mined from the disqualification narrative — the "what did they
# actually do" axis, independent of the company's sector. (category, weight,
# substrings). First match by weight wins.
CONDUCT_RULES: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "public_funds_fraud",
        1.8,
        ("bounce back loan", "bbl", "cbils", "coronavirus", "covid", "furlough",
         "government-backed", "government backed", "grant fund", "ppe"),
    ),
    ("tax_fraud", 1.5, ("vat", "hmrc", " paye", "tax loss", "evaded tax", "duty")),
    (
        "investor_harm",
        1.5,
        ("investor", "investment scheme", "ponzi", "client money", "deposits", "pension"),
    ),
    (
        "creditor_harm",
        1.2,
        ("creditor", "detriment of creditor", "preference", "misappropriat", "trading while insolvent"),
    ),
]


def classify_harm(sic_codes: list[str] | None, name: str | None) -> str:
    """Return the highest-weight matching harm category, or ``"none"``."""
    sics = [s.strip() for s in (sic_codes or []) if s and s.strip()]
    nm = (name or "").lower()
    best_cat, best_w = "none", 0.0
    for cat, w, prefixes, keywords in HARM_RULES:
        hit = any(s.startswith(prefixes) for s in sics) if prefixes else False
        hit = hit or any(k in nm for k in keywords)
        if hit and w > best_w:
            best_cat, best_w = cat, w
    return best_cat


def harm_weight(category: str) -> float:
    """Multiplier for a harm category; ``1.0`` for none/unknown."""
    for cat, w, _p, _k in HARM_RULES:
        if cat == category:
            return w
    return 1.0


def classify_conduct(text: str | None) -> str:
    """Return the highest-weight conduct category from a disqualification narrative."""
    t = (text or "").lower()
    best_cat, best_w = "none", 0.0
    for cat, w, subs in CONDUCT_RULES:
        if any(s in t for s in subs) and w > best_w:
            best_cat, best_w = cat, w
    return best_cat


def conduct_weight(category: str) -> float:
    """Multiplier for a conduct category; ``1.0`` for none/unknown."""
    for cat, w, _s in CONDUCT_RULES:
        if cat == category:
            return w
    return 1.0
