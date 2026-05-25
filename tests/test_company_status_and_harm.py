"""Tests for Phase 3 live-status parsing + harm classification."""

from __future__ import annotations

from shellnet.investigations import company_status as cs
from shellnet.investigations import harm

_CH_MARKDOWN = """# AEZA INTERNATIONAL LTD

Company number 15109642

Company status

Dissolved

Company type

Private limited Company

Incorporated on

1 September 2023

Nature of business (SIC)

63110 - Data processing, hosting and related activities
"""


def test_parse_ch_overview():
    parsed = cs.parse_ch_overview(_CH_MARKDOWN)
    assert parsed["company_name"] == "AEZA INTERNATIONAL LTD"
    assert parsed["company_status"] == "dissolved"
    assert parsed["company_type"] == "Private limited Company"
    assert parsed["incorporated_on"] == "1 September 2023"
    assert "63110" in parsed["sic_codes"]


def test_to_active_flag():
    assert cs.to_active_flag("active") is True
    assert cs.to_active_flag("Liquidation") is True  # ongoing -> still a live target
    assert cs.to_active_flag("Dissolved") is False
    assert cs.to_active_flag(None) is None
    assert cs.to_active_flag("something weird") is None


def test_classify_harm_by_sic():
    assert harm.classify_harm(["87100"], None) == "adult_social_care"
    assert harm.classify_harm(["85310"], "Some Academy Trust") in {"education"}
    assert harm.classify_harm(["63110"], "Acme Hosting") == "crypto_finance"
    assert harm.classify_harm([], "Ordinary Widgets Ltd") == "none"


def test_classify_harm_picks_highest_weight():
    # childrens_care (2.0) should beat education (1.5) when both could match.
    cat = harm.classify_harm(["8891", "85310"], "Little Stars Children's Home")
    assert cat == "childrens_care"
    assert harm.harm_weight(cat) == 2.0
    assert harm.harm_weight("none") == 1.0


def test_crypto_finance_no_longer_fires_on_generic_financial_sic():
    # P4 fix: a PPI/consumer-finance firm must not be mislabelled crypto_finance.
    assert harm.classify_harm(["64999"], "Tax Reclaim PPI Ltd") == "none"
    assert harm.classify_harm([], "Acme Crypto Exchange") == "crypto_finance"


def test_classify_conduct_flags_bounce_back_loan_fraud():
    bbl = "Mr X caused Co to apply for a Bounce Back Loan of GBP50,000 it was not entitled to."
    assert harm.classify_conduct(bbl) == "public_funds_fraud"
    assert harm.conduct_weight("public_funds_fraud") == 1.8
    assert harm.classify_conduct("ordinary trading dispute") == "none"
    assert harm.conduct_weight("none") == 1.0
