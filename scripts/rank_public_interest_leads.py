"""Harm-centred public-interest lead ranking.

Loads existing repo outputs (no broad new external scraping by
default), extracts candidate UK property owners, classifies them
by sector, and scores them on a transparent seven-component
formula.

THE GOAL IS NOT MORE COMPLIANCE ROWS. The goal is to surface leads
where hidden ownership intersects with public harm, public money,
sanctions, court findings, or regulated services, in a way a
normal person can understand in one sentence.

THIS IS NOT AN ACCUSATION. Every candidate is a public-interest
lead requiring manual verification. Every published claim from
this list must carry the caveats surfaced per candidate.

Outputs:
  - docs/reports/public_interest_leads.md
  - docs/reports/data/public_interest_leads.csv
  - docs/reports/data/public_interest_leads.json
  - docs/reports/data/public_interest_leads_evidence.csv

Usage:
  uv run python scripts/rank_public_interest_leads.py
  uv run python scripts/rank_public_interest_leads.py --run-external-search
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger("rank_public_interest_leads")


# ---------------------------------------------------------------------------
# Sector weak-label keywords
# ---------------------------------------------------------------------------

_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "care_health": [
        "care home",
        "nursing home",
        "residential care",
        "children's home",
        "childrens home",
        "health",
        "hospital",
        "clinic",
        "medical",
        "medic",
        "nhs",
        "assisted living",
        "healthcare",
        "medicx",
        "primary care",
    ],
    "asylum_hotels": [
        "hotel",
        "hostel",
        "inn ",
        "lodge",
        "accommodation",
        "asylum",
        "home office",
        "migrant",
        "refugee",
    ],
    "housing_leasehold": [
        "freehold",
        "leasehold",
        " estate",
        "block",
        "flats",
        "apartments",
        "residential",
        "ground rent",
        "social housing",
        "housing association",
        "cladding",
    ],
    "public_procurement": [
        "contract",
        "procurement",
        "tender",
        "council",
        "local authority",
        "nhs",
        "home office",
        "ministry",
        "department",
        "public",
        "pfi",
    ],
    "regulated_infra": [
        "energy",
        "gas",
        "oil",
        "water",
        "utility",
        "telecom",
        "defense",
        "defence",
        "security",
        "prison",
        "transport",
        "rail",
        "port",
        "airport",
        "gambling",
        "casino",
        "pipeline",
    ],
    "financial_secrecy": [
        "trust ",
        "foundation",
        "anstalt",
        "nominee",
        "fiduciary",
        " holdings",
        " investments",
        "capital",
        " services",
        "offshore",
        "jersey",
        "guernsey",
        "isle of man",
        "bvi",
        "british virgin",
        "cayman",
        "liechtenstein",
        "panama",
        "malta",
        "seychelles",
        "luxembourg",
    ],
}

_SECRECY_JURISDICTIONS = {
    "british virgin islands",
    "bvi",
    "vg",
    "jersey",
    "je",
    "guernsey",
    "gg",
    "isle of man",
    "im",
    "liechtenstein",
    "li",
    "panama",
    "pa",
    "seychelles",
    "sc",
    "cayman islands",
    "ky",
    "luxembourg",
    "lu",
    "bahamas",
    "bs",
    "marshall islands",
    "mh",
    "mauritius",
    "mu",
    "nevis",
    "kn",
    "monaco",
    "mc",
    "uae",
    "ae",
}

_OFAC_TOPICS = {
    "sanction",
    "sanction.linked",
    "debarment",
    "crime",
    "crime.fin",
    "crime.fraud",
    "crime.theft",
    "crime.traffick",
    "crime.war",
    "wanted",
    "reg.action",
    "export.control",
    "export.risk",
}


def _norm(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.lower()).strip()


def classify_sector(name: str, addresses: str = "", notes: str = "") -> list[str]:
    """Weak-label sector classification by substring search."""
    blob = " ".join(filter(None, [name, addresses, notes])).lower()
    found: list[str] = []
    for sector, kws in _SECTOR_KEYWORDS.items():
        if any(k in blob for k in kws):
            found.append(sector)
    return found


# ---------------------------------------------------------------------------
# Candidate model
# ---------------------------------------------------------------------------


@dataclass
class Candidate:
    entity_name: str = ""
    normalized_entity_name: str = ""
    one_sentence_story: str = ""
    why_anyone_would_care: str = ""
    asset_type: str = "unknown"
    sector: str = "unknown"
    property_titles_count: int = 0
    property_addresses_or_postcodes: str = ""
    jurisdiction: str = ""
    roe_status: str = "unknown"
    ocod_status: str = "unknown"
    icij_overlap: str = ""
    opensanctions_overlap: str = ""
    companies_house_match: str = "unknown"
    disqualified_director_overlap: str = ""
    public_money_exposure: str = ""
    public_harm_exposure: str = ""
    sanctions_or_enforcement_evidence: str = ""
    court_or_regulatory_evidence: str = ""
    offshore_structure_features: str = ""
    source_files: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    visual_hook: str = ""
    manual_checks_required: list[str] = field(default_factory=list)
    bad_actor_evidence: int = 0
    public_money_or_public_harm: int = 0
    concealment_structure: int = 0
    property_visual_clarity: int = 0
    offshore_complexity: int = 0
    false_positive_risk: int = 0
    legal_risk: int = 0
    public_interest_score: int = 0
    rank: int = 0
    recommendation: str = "needs_manual_review"
    caveats: list[str] = field(default_factory=list)
    safe_sentence: str = ""


# ---------------------------------------------------------------------------
# Loaders — each one degrades gracefully on missing input
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        log.warning("missing: %s", path)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("failed to load %s: %s", path, exc)
        return None


def _candidate_igt(root: Path) -> Candidate | None:
    """IGT Intergestions Trust Reg — the verified hero candidate."""
    src = _load_json(root / "aar_igt_verify.json")
    if not src:
        return None
    igt = next(
        (t for t in src.get("targets", []) if t.get("target_key") == "igt_intergestions"), None
    )
    if not igt:
        return None
    titles = igt.get("ocod_titles", [])
    return Candidate(
        entity_name="IGT Intergestions Trust Reg.",
        normalized_entity_name="igt intergestions trust reg",
        one_sentence_story=(
            "A US-OFAC-sanctioned Liechtenstein trust enterprise is recorded as proprietor "
            "of five UK Land Registry titles on Highgate West Hill, including a building "
            "called Bromwich House at 1 Witanhurst Lane, with no matching filing found "
            "on the UK Register of Overseas Entities."
        ),
        why_anyone_would_care=(
            "The US Treasury sanctioned this entity under its Russia-related Executive Order "
            "14024 programme. The UK created a public Register of Overseas Entities in 2022 "
            "specifically so that overseas owners of UK property would have to disclose who "
            "controls them. This entity has not been found on that register."
        ),
        asset_type="prime central London land + building",
        sector=";".join(classify_sector("IGT Intergestions land Highgate Witanhurst", "")),
        property_titles_count=igt.get("ocod_n_titles", 0),
        property_addresses_or_postcodes=", ".join(
            sorted({(t.get("postcode") or "").strip() or "—" for t in titles if t.get("postcode")})
        )
        or "Highgate West Hill / Witanhurst Lane area, N6",
        jurisdiction="Liechtenstein",
        roe_status="no matching filing found",
        ocod_status="recorded as proprietor since 29 April 2013 per OCOD May 2026",
        icij_overlap="not in ICIJ data",
        opensanctions_overlap=(
            "US OFAC SDN (RUSSIA-EO14024), us_sam_exclusions, ext_us_ofac_press_releases, "
            "ua_war_sanctions, opencorporates, ext_gleif, permid, us_trade_csl; "
            "OFAC remarks: '(Linked To: TRADE INITIATIVE ESTABLISHMENT)'"
        ),
        companies_house_match="no UK Companies House entry under any of 11 tested variants or Liechtenstein company number or LEI (live search 22 May 2026)",
        disqualified_director_overlap="",
        public_money_exposure="",
        public_harm_exposure="prime central London land near major private residence (Witanhurst); ownership opacity",
        sanctions_or_enforcement_evidence=(
            "OFAC SDN entry id=42998, Program RUSSIA-EO14024, Linked To TRADE INITIATIVE "
            "ESTABLISHMENT. Liechtenstein company number FL-0001.513.056-8, LEI 391200PWMHBZMLPKTA05. "
            "Established 20 Aug 1993."
        ),
        court_or_regulatory_evidence="",
        offshore_structure_features=(
            "Liechtenstein Trust Reg (Treuunternehmen); same registered address (Aeulestrasse, "
            "Vaduz) as another OFAC-sanctioned entity TRADE INITIATIVE ESTABLISHMENT for which "
            "IGT acts as corporate-services-of-record"
        ),
        source_files=[
            "aar_igt_verify.json",
            "docs/reports/hero_example_igt_intergestions.md",
            "docs/reports/hero_example_igt_pre_publication_checks.md",
            "docs/reports/hero_example_igt_publication_readiness.md",
            "docs/reports/hero_example_igt_current_ownership.md",
            "docs/reports/hero_example_igt_screenshots.md",
            "docs/reports/screenshots/06_ofac_sdn_search_results_intergestions.png",
            "docs/reports/screenshots/07_ofac_sdn_details_igt.png",
        ],
        source_urls=[
            "https://sanctionssearch.ofac.treas.gov/Details.aspx?id=42998",
            "https://sanctionssearch.ofac.treas.gov/Details.aspx?id=42997",
            "https://www.opensanctions.org/entities/NK-2FYHVi5239jTUiF4iMyFrj/",
        ],
        visual_hook="One Liechtenstein entity, five Highgate land titles, one OFAC sanctions list — fits on a single slide.",
        manual_checks_required=[
            "Buy 5 HMLR title registers (£7 × 5 = £35) for definitive current ownership",
            "Pull the OFAC press release that names TRADE INITIATIVE ESTABLISHMENT for the underlying-control rationale",
            "Pull the Liechtenstein commercial register entry FL-0001.513.056-8 via justizportal.li",
            "Camden planning portal check on Bromwich House to clarify the Witanhurst-estate relationship",
            "Lawyer review with explicit attention to the entity-not-person framing",
        ],
        bad_actor_evidence=5,
        public_money_or_public_harm=2,
        concealment_structure=4,
        property_visual_clarity=5,
        offshore_complexity=4,
        false_positive_risk=0,
        legal_risk=2,
        caveats=[
            "Slide-10 safe sentence uses 'recorded since 2013 as the proprietor' until live title-register purchases confirm current state",
            "OFAC SDN designation is a US listing; UK financial sanctions (OFSI) is a separate regime that should be confirmed",
            "No individual beneficial owner is named in the data — entity-level claim only",
            "Bromwich House at 1 Witanhurst Lane is in the curtilage of the Witanhurst estate but the title-register purchase is required before claiming any relationship to the wider estate",
        ],
        safe_sentence=(
            "A Liechtenstein-registered trust enterprise on the US Treasury OFAC Specially "
            "Designated Nationals list (IGT Intergestions Trust Reg., Liechtenstein company "
            "number FL-0001.513.056-8, designated under the Russia-related Executive Order 14024 "
            "programme as a linked entity of another OFAC-sanctioned entity, TRADE INITIATIVE "
            "ESTABLISHMENT) has been recorded since April 2013 as the proprietor of five UK Land "
            "Registry titles on Highgate West Hill, north London, with no matching filing found "
            "on the UK Register of Overseas Entities."
        ),
    )


def _candidate_trade_initiative(root: Path) -> Candidate | None:
    """TRADE INITIATIVE ESTABLISHMENT — the parent OFAC target (Linked To target of IGT)."""
    src = _load_json(root / "aar_igt_verify.json")
    if not src:
        return None
    return Candidate(
        entity_name="TRADE INITIATIVE ESTABLISHMENT",
        normalized_entity_name="trade initiative establishment",
        one_sentence_story=(
            "A 1968 Liechtenstein establishment on the US OFAC sanctions list is registered "
            "at the same Vaduz address as IGT Intergestions Trust Reg, the sanctioned entity "
            "that owns five Highgate land titles in London."
        ),
        why_anyone_would_care=(
            "It is the primary OFAC target. IGT, the entity actually holding the UK property, "
            "is OFAC-listed as a 'Linked To' entity of Trade Initiative."
        ),
        asset_type="(no direct UK property in OCOD under this name; structurally linked to IGT's 5 Highgate titles)",
        sector="financial_secrecy",
        property_titles_count=0,
        property_addresses_or_postcodes="(c/o IGT Intergestions Trust Reg., Aeulestrasse 30, Vaduz)",
        jurisdiction="Liechtenstein",
        roe_status="not directly an OCOD proprietor; linked via IGT",
        ocod_status="not an OCOD proprietor under its own name",
        icij_overlap="not in ICIJ data",
        opensanctions_overlap="US OFAC SDN (RUSSIA-EO14024); SDN id 42997; LI company number FL-0001.026.862-1; established 27 Nov 1968",
        companies_house_match="not on UK CH",
        disqualified_director_overlap="",
        public_money_exposure="",
        public_harm_exposure="indirect via the IGT-held Highgate titles",
        sanctions_or_enforcement_evidence="OFAC SDN id=42997, Program RUSSIA-EO14024",
        court_or_regulatory_evidence="",
        offshore_structure_features="Older Liechtenstein establishment (1968), with IGT (1993) as its corporate-services-of-record",
        source_files=[
            "aar_igt_verify.json",
            "docs/reports/hero_example_igt_screenshots.md",
            "docs/reports/screenshots/09_ofac_sdn_details_trade_initiative.png",
        ],
        source_urls=[
            "https://sanctionssearch.ofac.treas.gov/Details.aspx?id=42997",
        ],
        visual_hook="Same Vaduz address as IGT; the older 'parent' Liechtenstein entity on the OFAC list.",
        manual_checks_required=[
            "Pull the underlying OFAC press release naming Trade Initiative",
            "Liechtenstein register entry FL-0001.026.862-1",
            "Trace any other Liechtenstein vehicles operating from the same Aeulestrasse address",
        ],
        bad_actor_evidence=5,
        public_money_or_public_harm=1,
        concealment_structure=4,
        property_visual_clarity=2,
        offshore_complexity=4,
        false_positive_risk=0,
        legal_risk=2,
        caveats=[
            "Not a direct UK property owner in OCOD; story angle is the IGT linkage",
            "Use as context for the IGT lead rather than as a separate hero candidate",
        ],
        safe_sentence=(
            "Trade Initiative Establishment, a Liechtenstein company on the US OFAC Specially "
            "Designated Nationals list under the Russia-related Executive Order 14024 programme, "
            "is registered at the same Vaduz correspondence address as IGT Intergestions Trust Reg, "
            "the OFAC-sanctioned entity that is the recorded proprietor of five UK Land Registry "
            "titles in Highgate, London."
        ),
    )


def _candidate_fenland(root: Path) -> Candidate | None:
    src = _load_json(root / "fenland_deepdive.json")
    if not src:
        return None
    totals = src.get("totals", {})
    return Candidate(
        entity_name="FENLAND LIMITED",
        normalized_entity_name="fenland",
        one_sentence_story=(
            "A single Isle-of-Man-administered company is recorded as proprietor of 313 "
            "residential property titles concentrated in prime West London, with no matching "
            "filing found on the UK Register of Overseas Entities."
        ),
        why_anyone_would_care=(
            "313 prime West London residential properties held by one overseas-incorporated "
            "company with no UK Register of Overseas Entities filing is exactly the situation "
            "ECTEA 2022 was designed to make visible."
        ),
        asset_type="prime West London residential portfolio",
        sector=";".join(classify_sector("FENLAND LIMITED residential apartments flats", "")),
        property_titles_count=int(totals.get("fenland_ocod_titles", 313)),
        property_addresses_or_postcodes="W14, SW5, W8, W2, SW7, SW1V, SW10",
        jurisdiction="Isle of Man (OCOD); Malta (ICIJ Paradise Papers record)",
        roe_status="no matching filing found",
        ocod_status="recorded as proprietor since 2011 per OCOD May 2026",
        icij_overlap="FENLAND LIMITED (Malta, Paradise Papers); FENLAND INC. (Panama Papers, bearer)",
        opensanctions_overlap="",
        companies_house_match="no UK CH entry",
        disqualified_director_overlap="",
        public_money_exposure="",
        public_harm_exposure="housing-leasehold extraction risk in prime central London residential market",
        sanctions_or_enforcement_evidence="",
        court_or_regulatory_evidence="",
        offshore_structure_features=(
            "Isle of Man administration via 8 St Georges Street, Douglas IM1 1AH (co-tenant "
            "address with M.H.E. INVESTMENTS LIMITED and ROSSMOOR LIMITED — both also "
            "non-compliant); Paradise Papers names Lilian Fenech and Lawrence Fenech as officers"
        ),
        source_files=[
            "fenland_deepdive.json",
            "named_threads_expand.json",
            "docs/case_study_roe_noncompliance.md",
        ],
        source_urls=[],
        visual_hook="One Isle of Man company, 313 prime West London titles, 85 in W14 alone.",
        manual_checks_required=[
            "IOM Companies Registry entry for FENLAND LIMITED — confirm directors and status",
            "Malta Business Registry entry for FENLAND LIMITED — confirm whether IOM and Malta entities are the same",
            "Spot-check 10 HMLR title registers",
            "Right of reply to FENLAND LIMITED via IOM corp-services address",
        ],
        bad_actor_evidence=2,
        public_money_or_public_harm=3,
        concealment_structure=4,
        property_visual_clarity=5,
        offshore_complexity=3,
        false_positive_risk=1,
        legal_risk=3,
        caveats=[
            "No sanctions or adverse-evidence tag on FENLAND LIMITED or the named Fenech officers",
            "Fenech is a common Maltese surname — Yorgen Fenech name appears in the same Paradise Papers Malta corporate-registry leak but there is NO graph edge linking him to FENLAND LIMITED; do not imply otherwise",
            "Lilian and Lawrence Fenech are private individuals; the story is entity-level",
            "IOM-OCOD vs Malta-Paradise-Papers entity-identity needs separate registry verification",
        ],
        safe_sentence=(
            "FENLAND LIMITED, an Isle-of-Man-administered company, is recorded in HM Land "
            "Registry's Overseas Companies Ownership Data as the proprietor of 313 UK property "
            "titles concentrated in prime West London postcodes. The UK Register of Overseas "
            "Entities at Companies House contains no matching filing under that name. The "
            "Paradise Papers contains a Malta corporate registry record for an entity of the "
            "same name with named officers Lilian Fenech and Lawrence Fenech."
        ),
    )


def _candidate_ledra(root: Path) -> Candidate | None:
    """Ledra Trustee Services - the brand chain to Metalloinvest / Usmanov."""
    metal = _load_json(root / "metalloinvest_verify.json")
    return Candidate(
        entity_name="LEDRA TRUSTEE SERVICES LIMITED",
        normalized_entity_name="ledra trustee services",
        one_sentence_story=(
            "A Cyprus trustee firm is recorded as proprietor of two Mayfair flats, with "
            "no matching UK Register of Overseas Entities filing, and shares a Cyprus brand "
            "with a nominee firm that the Panama Papers documents as registered officer of "
            "a Russian Metalloinvest BVI structure connected to US-sanctioned oligarch Alisher "
            "Usmanov."
        ),
        why_anyone_would_care=(
            "If the Cyprus brand-family link reflects a corporate link, this is a Mayfair "
            "property in the asset-holding chain of a sanctioned Russian oligarch."
        ),
        asset_type="Mayfair flats",
        sector="financial_secrecy",
        property_titles_count=2,
        property_addresses_or_postcodes="45 Green Street, Mayfair, London W1K 7FX (+ one further Mayfair title)",
        jurisdiction="Cyprus",
        roe_status="no matching filing found",
        ocod_status="recorded as proprietor since March 2015 per OCOD May 2026",
        icij_overlap=(
            f"Panama Papers nominee chain for {len(metal.get('icij_metalloinvest_entities', []) if metal else [])} "
            "Metalloinvest-named BVI entities (via the related Cyprus brand 'Ledra Services Limited')"
        ),
        opensanctions_overlap="OS topics debarment + sanction for LEDRA TRUSTEE SERVICES LIMITED",
        companies_house_match="not on UK CH OE register",
        disqualified_director_overlap="",
        public_money_exposure="",
        public_harm_exposure="UK property ownership in the orbit of a US-sanctioned Russian oligarch",
        sanctions_or_enforcement_evidence=(
            "Holdingovaya Kompaniya Metalloinvest AO on us_ofac_sdn + us_sam_exclusions + "
            "ua_war_sanctions; Alisher Usmanov on us_ofac_sdn + us_sam_exclusions; OS topics "
            "for Ledra Trustee Services Limited include debarment + sanction"
        ),
        court_or_regulatory_evidence="",
        offshore_structure_features=(
            "Cyprus 'Ledra' service-provider brand family with multiple related entities "
            "(Ledra Trustee Services Limited, Ledra Services Limited, Ledra Trustees Limited, "
            "Ledra Nominees Limited); appears in Panama Papers as officer of BVI Metalloinvest "
            "entities; Bridgewater Isle of Man nominees co-officered"
        ),
        source_files=[
            "metalloinvest_verify.json",
            "metalloinvest_uk_ch.json",
            "named_threads_expand.json",
            "docs/case_study_roe_noncompliance.md",
        ],
        source_urls=[],
        visual_hook="Mayfair flat → Cyprus brand → Panama Papers nominee → Russia Metalloinvest → Usmanov (caveat-heavy).",
        manual_checks_required=[
            "Cyprus corporate registry: confirm or refute that Ledra Trustee Services Limited and Ledra Services Limited share corporate parent / common control",
            "BVI registry/gazette for the two BVI Metalloinvest entities",
            "OFAC designation paperwork for Usmanov / Metalloinvest control chain",
            "Right of reply to LEDRA TRUSTEE SERVICES LIMITED at Mayfair correspondence and Nicosia Ledra House",
            "Lawyer review of brand-vs-corporate identity framing",
        ],
        bad_actor_evidence=3,
        public_money_or_public_harm=3,
        concealment_structure=5,
        property_visual_clarity=4,
        offshore_complexity=5,
        false_positive_risk=3,
        legal_risk=5,
        caveats=[
            "BRAND identity not CORPORATE identity between LEDRA TRUSTEE SERVICES LIMITED (UK property owner) and Ledra Services Limited (Panama Papers nominee). The Cyprus registry verification is the critical gate.",
            "Zero direct edges in the leak graph from any Usmanov officer node to the BVI Metalloinvest entities; the structure layers nominees between Usmanov and the BVI shells by design",
            "The Metalloinvest BVI entity name 'METALLOINVEST HOLDINGS B.V.I) LIMITED' contains a typo in the leak record",
            "Do NOT publish framing as 'Usmanov-owned Mayfair flat'; the supported framing is brand-family-shared with a documented Metalloinvest nominee",
        ],
        safe_sentence=(
            "LEDRA TRUSTEE SERVICES LIMITED, a Cyprus-registered trustee firm, is recorded as "
            "proprietor of two Mayfair property titles in HMLR's Overseas Companies Ownership "
            "Data, with no matching filing on the UK Register of Overseas Entities. OpenSanctions "
            "applies debarment and sanction topic tags to the entity. The same Cyprus 'Ledra' "
            "service-provider brand appears in the Panama Papers as registered officer of two "
            "BVI entities named for Metalloinvest, the Russian metals holding controlled by "
            "US-OFAC-sanctioned Alisher Usmanov. The brand-identity link is documented; the "
            "corporate-identity link between LEDRA TRUSTEE SERVICES LIMITED and Ledra Services "
            "Limited needs separate Cyprus-registry verification."
        ),
    )


def _candidate_embassy(root: Path) -> Candidate | None:
    return Candidate(
        entity_name="EMBASSY DEVELOPMENT (Lux + Jersey SPV cluster)",
        normalized_entity_name="embassy development",
        one_sentence_story=(
            "A Luxembourg-and-Jersey corporate cluster acquired £44 million of Battersea "
            "regeneration land just before the 2022 UK overseas-ownership-disclosure law "
            "commenced, and has not been found on the UK Register of Overseas Entities."
        ),
        why_anyone_would_care=(
            "Nine Elms Park is part of the wider Battersea / Vauxhall public-realm "
            "regeneration scheme. A £44M single-title acquisition by an offshore SPV "
            "cluster, with no UK BO disclosure, sits in a sector — UK regeneration land "
            "— with material public-money exposure."
        ),
        asset_type="prime regeneration-zone development land",
        sector="public_procurement;housing_leasehold",
        property_titles_count=3,
        property_addresses_or_postcodes="Plot E, Nine Elms Park, Nine Elms Lane, London SW8 5BB",
        jurisdiction="Luxembourg + Jersey",
        roe_status="no matching filing found",
        ocod_status="recorded as proprietor since 15 Feb 2022 per OCOD May 2026 (pre-ECTEA commencement)",
        icij_overlap="no ICIJ leak presence",
        opensanctions_overlap="EMBASSY DEVELOPMENT LIMITED tagged debarment + sanction by OS (source needs lookup)",
        companies_house_match="no UK CH OE register entry",
        disqualified_director_overlap="",
        public_money_exposure="Nine Elms is part of major UK regeneration zone with public-realm spending and TfL Northern Line extension; specific exposure to be confirmed",
        public_harm_exposure="potential public-money / regeneration-asset opacity",
        sanctions_or_enforcement_evidence="OS topic debarment + sanction — primary source lookup pending",
        court_or_regulatory_evidence="",
        offshore_structure_features=(
            "Three related SPVs: EMBASSY DEVELOPMENT E S.A.R.L (Luxembourg), EMBASSY "
            "DEVELOPMENT F S.A R.L (Luxembourg), EMBASSY DEVELOPMENT LIMITED (Jersey); "
            "two SPVs co-located at 14-16 Avenue Pasteur, L-2130 Luxembourg"
        ),
        source_files=[
            "named_threads_deepdive.json",
            "named_threads_expand.json",
            "roe_noncompliance_personalize.json",
        ],
        source_urls=[],
        visual_hook="Plot E, Nine Elms Park, £44M, acquired Feb 2022.",
        manual_checks_required=[
            "Look up the specific OS source for the debarment+sanction tag on EMBASSY DEVELOPMENT LIMITED",
            "Cross-reference Nine Elms development consortium public filings for the project sponsor",
            "Live UK CH OE-register search for all three name variants",
            "Confirm pre-ECTEA acquisition status (acquired Feb 2022, ECTEA commenced Aug 2022; transitional deadline 31 Jan 2023)",
        ],
        bad_actor_evidence=3,
        public_money_or_public_harm=3,
        concealment_structure=4,
        property_visual_clarity=4,
        offshore_complexity=3,
        false_positive_risk=2,
        legal_risk=3,
        caveats=[
            "OS debarment+sanction topic without a named individual is anonymous and needs primary-source lookup",
            "Acquired pre-ECTEA commencement; the breach is the failure to file by 31 Jan 2023 transitional deadline",
            "Zero ICIJ leak presence is unusual for high-stakes concealment; this may be conventional project-financing rather than secrecy",
        ],
        safe_sentence=(
            "Three related SPVs — EMBASSY DEVELOPMENT E S.A.R.L (Luxembourg), EMBASSY "
            "DEVELOPMENT F S.A R.L (Luxembourg), and EMBASSY DEVELOPMENT LIMITED (Jersey) — "
            "are recorded in HM Land Registry's Overseas Companies Ownership Data as "
            "proprietors of three UK titles in Battersea / Nine Elms, including a £44 million "
            "title at Plot E, Nine Elms Park, acquired 15 February 2022. The UK Register of "
            "Overseas Entities contains no matching filing for any of the three names."
        ),
    )


def _candidate_healthcare_property(root: Path) -> Candidate:
    return Candidate(
        entity_name="HEALTHCARE PROPERTY HOLDINGS LIMITED",
        normalized_entity_name="healthcare property holdings",
        one_sentence_story=(
            "A Jersey-incorporated company called Healthcare Property Holdings Limited is "
            "recorded as proprietor of 37 UK property titles, with no matching UK Register "
            "of Overseas Entities filing."
        ),
        why_anyone_would_care=(
            "The company name itself indicates a healthcare-sector portfolio. Beneficial "
            "ownership of healthcare-property landlords is a recognised UK public-interest "
            "concern, particularly where care homes and clinical sites depend on a stable "
            "landlord."
        ),
        asset_type="healthcare-sector property portfolio (per entity name)",
        sector="care_health;housing_leasehold",
        property_titles_count=37,
        property_addresses_or_postcodes="(not extracted in current artefacts — manual lookup required)",
        jurisdiction="Jersey",
        roe_status="no matching filing found in OCOD-vs-OE-registry anti-join",
        ocod_status="recorded as proprietor per OCOD May 2026 anti-join",
        icij_overlap="not surfaced in current artefacts",
        opensanctions_overlap="not surfaced",
        companies_house_match="not on UK CH OE register (per anti-join)",
        disqualified_director_overlap="",
        public_money_exposure="potential — healthcare landlords often receive NHS or local-authority payments via tenants",
        public_harm_exposure="potential — stable beneficial ownership of healthcare landlords matters to service continuity for residents and patients",
        sanctions_or_enforcement_evidence="",
        court_or_regulatory_evidence="",
        offshore_structure_features="Jersey incorporation",
        source_files=["roe_noncompliance.json", "docs/case_study_roe_noncompliance.md"],
        source_urls=[],
        visual_hook="Care landlord with 37 UK titles, Jersey ownership, no UK BO disclosure.",
        manual_checks_required=[
            "Resolve OCOD title-level addresses to confirm the portfolio actually contains healthcare assets (the company name is a weak label only)",
            "Live UK CH OE-register search for name variants",
            "Cross-reference CQC (Care Quality Commission) regulated-locations registry",
            "Identify operating tenants and any NHS / local-authority payments to those tenants",
            "Right of reply",
        ],
        bad_actor_evidence=1,
        public_money_or_public_harm=4,
        concealment_structure=3,
        property_visual_clarity=3,
        offshore_complexity=2,
        false_positive_risk=2,
        legal_risk=2,
        caveats=[
            "Name-based sector classification is a weak label; some 'Healthcare Property Holdings' entities are not in fact healthcare landlords",
            "No adverse evidence on the entity in current artefacts",
            "Title-level addresses must be confirmed before claiming the portfolio is in the care sector",
        ],
        safe_sentence=(
            "HEALTHCARE PROPERTY HOLDINGS LIMITED, a Jersey-incorporated company whose name "
            "indicates healthcare-sector activity, is recorded in HMLR's Overseas Companies "
            "Ownership Data as proprietor of 37 UK property titles, with no matching filing "
            "found on the UK Register of Overseas Entities. The composition of the property "
            "portfolio and any healthcare-tenant relationships have not been independently "
            "verified."
        ),
    )


def _candidate_medicx(root: Path) -> Candidate:
    return Candidate(
        entity_name="MEDICX PROPERTIES V LIMITED",
        normalized_entity_name="medicx properties v",
        one_sentence_story=(
            "MedicX Properties V Limited, a Guernsey-incorporated holder of 41 UK property "
            "titles whose name and corporate group historically operated medical-centre "
            "properties leased to NHS-funded primary care providers, has no matching UK "
            "Register of Overseas Entities filing in our anti-join."
        ),
        why_anyone_would_care=(
            "MedicX as a brand historically owned and leased primary-care medical centres "
            "to NHS-funded GP practices. Beneficial ownership of medical-centre landlords "
            "is a recognised UK public-interest concern given the NHS funding flowing "
            "through them via primary-care rent reimbursements."
        ),
        asset_type="medical-centre / primary-care property",
        sector="care_health;public_procurement",
        property_titles_count=41,
        property_addresses_or_postcodes="(not extracted in current artefacts — title-level address audit required)",
        jurisdiction="Guernsey",
        roe_status="no matching filing found in OCOD-vs-OE-registry anti-join",
        ocod_status="recorded as proprietor per OCOD May 2026 anti-join",
        icij_overlap="not surfaced",
        opensanctions_overlap="not surfaced",
        companies_house_match="not on UK CH OE register (per anti-join)",
        disqualified_director_overlap="",
        public_money_exposure="NHS primary-care rent reimbursement potentially flows to medical-centre landlords",
        public_harm_exposure="medical-centre tenant relationships and any NHS rent-reimbursement exposure",
        sanctions_or_enforcement_evidence="",
        court_or_regulatory_evidence="",
        offshore_structure_features="Guernsey incorporation, numbered SPV (V) suggesting a series of related vehicles",
        source_files=["roe_noncompliance.json", "docs/case_study_roe_noncompliance.md"],
        source_urls=[],
        visual_hook="A medical-centre landlord with 41 UK titles, Guernsey ownership, no UK BO disclosure.",
        manual_checks_required=[
            "Confirm whether MEDICX PROPERTIES V LIMITED is part of the historic Octopus Healthcare / MedicX Fund group (now Octopus AHI / Primary Health Properties or successor)",
            "Resolve OCOD title-level addresses to confirm portfolio composition",
            "Live UK CH OE-register search for all MedicX Properties name variants",
            "NHS primary-care contract / rent-reimbursement disclosure check",
            "Right of reply to the Guernsey address",
        ],
        bad_actor_evidence=1,
        public_money_or_public_harm=4,
        concealment_structure=3,
        property_visual_clarity=3,
        offshore_complexity=2,
        false_positive_risk=2,
        legal_risk=3,
        caveats=[
            "MedicX as a brand has changed hands; the current group successor needs verification before any claim about beneficial ownership",
            "Numbered SPVs (MedicX Properties V) often appear within a wider series; the broader fund structure should be mapped",
            "No adverse evidence in current artefacts",
        ],
        safe_sentence=(
            "MEDICX PROPERTIES V LIMITED, a Guernsey-incorporated company, is recorded as "
            "proprietor of 41 UK property titles in HM Land Registry's Overseas Companies "
            "Ownership Data, with no matching filing found on the UK Register of Overseas "
            "Entities. The MedicX corporate group has historically held medical-centre "
            "properties leased to NHS-funded primary care providers. The current beneficial "
            "ownership of MEDICX PROPERTIES V LIMITED and the composition of its 41-title "
            "portfolio have not been independently verified in this work."
        ),
    )


def _candidate_gas_transport(root: Path) -> Candidate:
    return Candidate(
        entity_name="THE GAS TRANSPORTATION COMPANY LIMITED",
        normalized_entity_name="gas transportation company",
        one_sentence_story=(
            "A Guernsey company called The Gas Transportation Company Limited is recorded as "
            "proprietor of 41 UK property titles, in a sector — gas pipeline / utility "
            "infrastructure — with material public-interest considerations."
        ),
        why_anyone_would_care=(
            "If the company is a UK gas distribution-network or pipeline infrastructure "
            "owner, beneficial ownership disclosure is directly material to UK energy "
            "policy and consumer billing."
        ),
        asset_type="gas / utility infrastructure (per entity name)",
        sector="regulated_infra",
        property_titles_count=41,
        property_addresses_or_postcodes="(not extracted in current artefacts)",
        jurisdiction="Guernsey",
        roe_status="no matching filing found in OCOD-vs-OE-registry anti-join",
        ocod_status="recorded as proprietor per OCOD May 2026 anti-join",
        icij_overlap="not surfaced",
        opensanctions_overlap="not surfaced",
        companies_house_match="not on UK CH OE register (per anti-join)",
        disqualified_director_overlap="",
        public_money_exposure="possible Ofgem-regulated revenue if the entity is a licensed gas-network operator",
        public_harm_exposure="utility-regulated asset class with consumer billing implications",
        sanctions_or_enforcement_evidence="",
        court_or_regulatory_evidence="",
        offshore_structure_features="Guernsey incorporation, name suggesting infrastructure holding vehicle",
        source_files=["roe_noncompliance.json", "docs/case_study_roe_noncompliance.md"],
        source_urls=[],
        visual_hook="A gas-named landlord with 41 UK titles, Guernsey ownership, no UK BO disclosure.",
        manual_checks_required=[
            "Confirm whether THE GAS TRANSPORTATION COMPANY LIMITED is the Ofgem-licensed Independent Gas Transporter (IGT — confusing acronym collision) or an unrelated entity",
            "Ofgem licence registry check",
            "OCOD title-level address audit (gas-pipeline easements are often unusual property records)",
            "Live UK CH OE-register search",
            "Right of reply",
        ],
        bad_actor_evidence=1,
        public_money_or_public_harm=3,
        concealment_structure=3,
        property_visual_clarity=2,
        offshore_complexity=2,
        false_positive_risk=3,
        legal_risk=2,
        caveats=[
            "Name-based sector classification is a weak label — entity might be a non-utility holding vehicle merely named that way",
            "Acronym collision risk: 'IGT' here refers to UK Independent Gas Transporters as a regulatory category, distinct from IGT Intergestions Trust Reg (the OFAC-sanctioned Liechtenstein entity featured in the hero example), and also distinct from International Game Technology",
            "No adverse evidence in current artefacts",
        ],
        safe_sentence=(
            "THE GAS TRANSPORTATION COMPANY LIMITED, a Guernsey-incorporated company, is "
            "recorded as proprietor of 41 UK property titles in HM Land Registry's Overseas "
            "Companies Ownership Data, with no matching filing found on the UK Register of "
            "Overseas Entities. Whether the company is an Ofgem-licensed UK gas-network "
            "operator or an unrelated holding vehicle has not been independently verified."
        ),
    )


def _candidate_profitable_plots(root: Path) -> Candidate:
    return Candidate(
        entity_name="PROFITABLE PLOTS PTE LTD",
        normalized_entity_name="profitable plots pte",
        one_sentence_story=(
            "A Singapore company called Profitable Plots Pte Ltd, whose principals were "
            "convicted in a 2014 UK land-banking fraud case, is recorded in HMLR's Overseas "
            "Companies Ownership Data as proprietor of 1,335 UK property titles with no "
            "matching filing on the UK Register of Overseas Entities."
        ),
        why_anyone_would_care=(
            "1,335 UK property titles attributed to a single Singapore company associated "
            "with a major UK fraud prosecution sit unchanged in HMLR data for more than a "
            "decade after the convictions. The status of those titles — frozen, "
            "compensation-pool, or actively held — is a recognised public-interest question."
        ),
        asset_type="UK land-banking plots (mass small parcels)",
        sector="public_procurement;housing_leasehold",
        property_titles_count=1335,
        property_addresses_or_postcodes="(mass plots across UK — title-level audit required)",
        jurisdiction="Singapore",
        roe_status="no matching filing found in OCOD-vs-OE-registry anti-join",
        ocod_status="recorded as proprietor per OCOD May 2026 anti-join",
        icij_overlap="not surfaced",
        opensanctions_overlap="not directly tagged in current artefacts",
        companies_house_match="not on UK CH OE register (per anti-join)",
        disqualified_director_overlap="The 2014 prosecution of related individuals would put them on the UK CH disqualified-officers register — separate confirmation needed",
        public_money_exposure="UK Serious Fraud Office prosecuted the related individuals (R v Profitable Plots / Land Options International)",
        public_harm_exposure="UK retail investors defrauded in the original 2014 case; current status of the company's 1,335 titles is the public-interest question",
        sanctions_or_enforcement_evidence="The principals were convicted of fraud; the company entity itself is the public-record holder of the residual property titles",
        court_or_regulatory_evidence="2014 UK Serious Fraud Office prosecution and convictions; reportable",
        offshore_structure_features="Singapore Pte Ltd",
        source_files=["roe_noncompliance.json", "docs/case_study_roe_noncompliance.md"],
        source_urls=[
            "https://www.sfo.gov.uk/cases/profitable-plots-and-land-options-international/",
        ],
        visual_hook="1,335 UK titles still in one Singapore company more than a decade after the SFO prosecution of its principals.",
        manual_checks_required=[
            "Confirm the SFO case (R v Profitable Plots / Land Options International) names this exact entity",
            "Confirm the SFO civil-recovery / confiscation status of the 1,335 titles — frozen, compensation-pool, or actively held?",
            "Cross-reference with UK CH disqualified-officers register for the named principals",
            "Title-level audit of a sample of the 1,335 titles to understand the asset class",
            "Right of reply via the Singapore registered office",
        ],
        bad_actor_evidence=5,
        public_money_or_public_harm=4,
        concealment_structure=2,
        property_visual_clarity=2,
        offshore_complexity=1,
        false_positive_risk=1,
        legal_risk=3,
        caveats=[
            "The principals' convictions are court-record fact; the company entity is separate from the convicted individuals",
            "1,335 titles in OCOD does NOT mean active concealment — these may be SFO-frozen / receiver-held assets in a long-running compensation process",
            "The 'no ROE filing' point is genuinely interesting either way: if the company is dormant / under receivership, the question shifts to who is responsible for the filing",
            "The status of the underlying investors / claimants in the 2014 case is reportable; the company-level ROE finding is the news angle",
        ],
        safe_sentence=(
            "PROFITABLE PLOTS PTE LTD, a Singapore company whose principals were convicted "
            "in a 2014 UK Serious Fraud Office land-banking prosecution, is recorded in HM "
            "Land Registry's Overseas Companies Ownership Data as proprietor of 1,335 UK "
            "property titles, with no matching filing on the UK Register of Overseas Entities. "
            "The current operational status of the company and the title pool — including "
            "whether the titles are subject to receivership, confiscation, or compensation "
            "proceedings — has not been independently verified in this work."
        ),
    )


def _candidate_park_plaza(root: Path) -> Candidate:
    return Candidate(
        entity_name="WESTMINSTER BRIDGE LONDON (REAL ESTATE) B.V. + COUNTY HALL HOTEL HOLDINGS B.V.",
        normalized_entity_name="park plaza westminster bridge",
        one_sentence_story=(
            "Two related Dutch companies are recorded as proprietors of 609 UK property "
            "titles — almost all at the Park Plaza Westminster Bridge hotel — with no "
            "matching filings found on the UK Register of Overseas Entities."
        ),
        why_anyone_would_care=(
            "Hotel-condo schemes have been a UK consumer-protection concern. 609 titles "
            "for a single building owned by a Dutch SPV with no UK BO disclosure is at "
            "minimum a regulatory-housekeeping question."
        ),
        asset_type="hotel-condo room titles (1,019-room hotel)",
        sector="asylum_hotels;public_procurement",
        property_titles_count=609,
        property_addresses_or_postcodes="200 Westminster Bridge Road, London SE1 7UT + 1 Addington Street SE1 7RY",
        jurisdiction="Netherlands",
        roe_status="no matching filings found",
        ocod_status="recorded per OCOD May 2026 anti-join",
        icij_overlap="small (≤7 distinct names within SE1)",
        opensanctions_overlap="not surfaced",
        companies_house_match="not on UK CH OE register (per anti-join)",
        disqualified_director_overlap="",
        public_money_exposure="UK Home Office contracts for hotel accommodation are a relevant national policy area; this specific building's contract status is not known",
        public_harm_exposure="hotel-condo investor protection",
        sanctions_or_enforcement_evidence="",
        court_or_regulatory_evidence="",
        offshore_structure_features="Dutch B.V. SPV structure; numbered-SPV pattern; 88% of SE1 cluster",
        source_files=["se1_deepdive.json", "docs/case_study_roe_noncompliance.md"],
        source_urls=[],
        visual_hook="One building, 1,019 hotel rooms, 609 separate UK title records.",
        manual_checks_required=[
            "Live UK CH OE-register search for both Dutch entity names",
            "Confirm whether Park Plaza Westminster Bridge has a Home Office / local authority accommodation contract",
            "Right of reply to the Dutch operator",
            "Decide whether to use as a hero candidate or as a methodology / downgrade example",
        ],
        bad_actor_evidence=0,
        public_money_or_public_harm=3,
        concealment_structure=2,
        property_visual_clarity=3,
        offshore_complexity=2,
        false_positive_risk=1,
        legal_risk=1,
        caveats=[
            "Conventional hotel-condo operator pattern, not offshore-secrecy pattern",
            "No adverse evidence on the Dutch operator",
            "Better used as a 'show your work' downgrade / methodology example than as a hero lead",
        ],
        safe_sentence=(
            "WESTMINSTER BRIDGE LONDON (REAL ESTATE) B.V. and COUNTY HALL HOTEL HOLDINGS B.V., "
            "two Dutch-incorporated companies, are recorded between them as proprietors of "
            "609 UK property titles — the majority at the Park Plaza Westminster Bridge "
            "hotel-condo development at 200 Westminster Bridge Road, London — with no "
            "matching filings on the UK Register of Overseas Entities."
        ),
    )


def _candidate_eko_ire(root: Path) -> Candidate:
    return Candidate(
        entity_name="EKO IRE LIMITED",
        normalized_entity_name="eko ire",
        one_sentence_story=(
            "A British Virgin Islands company set up via the Pandora-Papers-leaked Alcogal "
            "law firm is recorded as proprietor of five UK property titles — including a "
            "room in the Park Plaza Westminster Bridge hotel — with no matching UK Register "
            "of Overseas Entities filing."
        ),
        why_anyone_would_care=(
            "Small scale and no sanctions overlay; use as case-study context rather than "
            "a lead. The Pandora-Papers documentary trail is independently corroborative "
            "of the offshore-secrecy pattern."
        ),
        asset_type="mixed UK property incl. one hotel-condo room",
        sector="financial_secrecy",
        property_titles_count=5,
        property_addresses_or_postcodes="Park Plaza Westminster Bridge SE1 7UT + others",
        jurisdiction="British Virgin Islands",
        roe_status="no matching filing found",
        ocod_status="recorded as proprietor per OCOD May 2026",
        icij_overlap="EKO IRE LIMITED (BVI) named in Pandora Papers via Alemán, Cordero, Galindo & Lee (Alcogal); 3 Edokpolo-named officers",
        opensanctions_overlap="",
        companies_house_match="not on UK CH OE register",
        disqualified_director_overlap="",
        public_money_exposure="",
        public_harm_exposure="",
        sanctions_or_enforcement_evidence="",
        court_or_regulatory_evidence="",
        offshore_structure_features="BVI vehicle set up via Alcogal law firm (Pandora Papers source); Nigerian/Lagos correspondence at 'Edokonsult'",
        source_files=["named_threads_deepdive.json", "named_threads_expand.json"],
        source_urls=[],
        visual_hook="Family-named BVI vehicle owns hotel-condo room + 4 other UK titles, no UK BO disclosure.",
        manual_checks_required=[
            "Sanctions / PEP screening of the three named Edokpolo officers",
            "Live UK CH OE-register search",
            "Title-level audit of the 5 titles",
        ],
        bad_actor_evidence=1,
        public_money_or_public_harm=1,
        concealment_structure=4,
        property_visual_clarity=3,
        offshore_complexity=3,
        false_positive_risk=1,
        legal_risk=4,
        caveats=[
            "The Edokpolos are private individuals with no sanctions, PEP or wrongdoing tag in current data",
            "Naming the family without an independent public-interest hook beyond ROE non-compliance is high defamation risk",
            "Park Plaza Westminster Bridge title is the hotel-condo scheme (see SE1 deepdive)",
            "Use as context only",
        ],
        safe_sentence=(
            "EKO IRE LIMITED, a British Virgin Islands company, is recorded as proprietor "
            "of five UK property titles in HMLR's Overseas Companies Ownership Data, with "
            "no matching filing on the UK Register of Overseas Entities. The Pandora Papers "
            "contains a corresponding Alemán, Cordero, Galindo & Lee record with three "
            "Edokpolo-surname officers."
        ),
    )


def _candidate_harmony_ridge(root: Path) -> Candidate:
    return Candidate(
        entity_name="HARMONY RIDGE LIMITED",
        normalized_entity_name="harmony ridge",
        one_sentence_story=(
            "A single Kensington flat is recorded as owned by a Jersey company that shares "
            "a name with a separately-incorporated BVI entity in the Panama and Paradise "
            "Papers tagged by OpenSanctions as sanction-linked."
        ),
        why_anyone_would_care=("Single-title; useful only as a name-pattern example."),
        asset_type="single Kensington flat",
        sector="housing_leasehold",
        property_titles_count=1,
        property_addresses_or_postcodes="Flat 7, 27 and 29 Hornton Street, London W8 7NR",
        jurisdiction="Jersey (OCOD) / BVI (ICIJ — note jurisdictional mismatch)",
        roe_status="no matching filing found",
        ocod_status="recorded since 2010",
        icij_overlap="Harmony Ridge Holdings Ltd (BVI, Panama); Harmony Ridge Limited (BVI, Paradise/Appleby) — note jurisdictional mismatch with OCOD-Jersey record",
        opensanctions_overlap="corp.offshore + sanction.linked",
        companies_house_match="not on UK CH OE register",
        disqualified_director_overlap="",
        public_money_exposure="",
        public_harm_exposure="",
        sanctions_or_enforcement_evidence="",
        court_or_regulatory_evidence="",
        offshore_structure_features="Single offshore-incorporation pattern; weak sanction.linked OS topic",
        source_files=["named_threads_deepdive.json"],
        source_urls=[],
        visual_hook="Kensington flat, name-only chain to Panama/Paradise Papers entries.",
        manual_checks_required=[
            "Jersey + BVI corporate-registry verification to resolve same-entity-vs-homonym question",
        ],
        bad_actor_evidence=2,
        public_money_or_public_harm=1,
        concealment_structure=3,
        property_visual_clarity=2,
        offshore_complexity=2,
        false_positive_risk=4,
        legal_risk=3,
        caveats=[
            "OCOD Jersey vs ICIJ BVI jurisdictional mismatch unresolved — likely different entities sharing a name",
            "Single title, very small scale",
            "OS topic sanction.linked is the weakest sanctions topic (linked, not direct)",
        ],
        safe_sentence=(
            "HARMONY RIDGE LIMITED, a Jersey-incorporated company, is recorded as proprietor "
            "of a single flat at Hornton Street, London W8 in HMLR's Overseas Companies "
            "Ownership Data. Two BVI-incorporated entities sharing the same name appear in "
            "the Panama and Paradise Papers and carry OpenSanctions topic tags of "
            "corp.offshore + sanction.linked. The Jersey-vs-BVI jurisdictional mismatch is "
            "unresolved and the entities may be distinct."
        ),
    )


def _candidate_aar(root: Path) -> Candidate | None:
    src = _load_json(root / "aar_igt_verify.json")
    if not src:
        return None
    return Candidate(
        entity_name="AAR INTERNATIONAL INC",
        normalized_entity_name="aar international",
        one_sentence_story=(
            "A US aerospace maintenance company subject to historical US arms-export-controls "
            "enforcement is recorded as proprietor of one UK aircraft title parked near "
            "Gatwick airport, with no matching UK Register of Overseas Entities filing."
        ),
        why_anyone_would_care=(
            "False-positive downgrade example. OS tagged AAR International with "
            "crime.traffick, but the topic refers to historical US Directorate of Defense "
            "Trade Controls (ITAR) arms-export enforcement, not human trafficking. The "
            "company is the well-known US aerospace MRO operator AAR Corp."
        ),
        asset_type="one aircraft / aviation parking title",
        sector="regulated_infra",
        property_titles_count=1,
        property_addresses_or_postcodes="Explorer 1, Fleming Way, Crawley RH10 9GT",
        jurisdiction="USA",
        roe_status="no matching filing found",
        ocod_status="recorded since 2019",
        icij_overlap="Panama Papers contains entries for Alfa Group / AAR International / similar names but cross-reference is weak",
        opensanctions_overlap="OS topic crime.traffick — but the source dataset is us_ddtc_enforcements (US arms-export-controls), not human-trafficking",
        companies_house_match="not on UK CH OE register",
        disqualified_director_overlap="",
        public_money_exposure="",
        public_harm_exposure="",
        sanctions_or_enforcement_evidence="historical US DDTC settlement, not active sanctions",
        court_or_regulatory_evidence="historical US DDTC enforcement",
        offshore_structure_features="US public-company headquartered at Wood Dale, Chicago — NOT offshore-secrecy",
        source_files=["aar_igt_verify.json", "docs/case_study_roe_noncompliance.md"],
        source_urls=[],
        visual_hook="(downgrade example) The OS 'crime.traffick' topic is misleading without context.",
        manual_checks_required=[
            "Confirm the AAR Corp public-company identity and the historical DDTC settlement details",
        ],
        bad_actor_evidence=2,
        public_money_or_public_harm=0,
        concealment_structure=0,
        property_visual_clarity=2,
        offshore_complexity=0,
        false_positive_risk=4,
        legal_risk=4,
        caveats=[
            "OS crime.traffick topic here means arms-export-controls (ITAR) enforcement, not human trafficking — easy to misread",
            "The proprietor address (Wood Dale, Chicago) is AAR Corp's actual headquarters, a major US-listed aerospace MRO",
            "The 'UK property' is one aviation-parking title; regulatory housekeeping not concealment",
            "Downgrade example — useful in a methodology section, not as a hero candidate",
        ],
        safe_sentence=(
            "AAR INTERNATIONAL INC, a US-incorporated entity associated with the publicly-listed "
            "aerospace maintenance firm AAR Corp, is recorded as proprietor of one UK title "
            "(an aviation parking title at Fleming Way, Crawley) with no matching filing on "
            "the UK Register of Overseas Entities. OpenSanctions tags the entity with topic "
            "'crime.traffick' which in this case derives from a historical US Directorate of "
            "Defense Trade Controls enforcement record under the arms-export-controls regime, "
            "not human trafficking."
        ),
    )


def _candidate_disqualified_directors(root: Path) -> Candidate | None:
    """Downgrade example — OS gb_coh_disqualified turned out unreliable."""
    return Candidate(
        entity_name="UK CH disqualified-directors x ICIJ matches (multiple)",
        normalized_entity_name="disqualified directors track",
        one_sentence_story=(
            "An earlier attempt to match UK Companies House disqualified directors against "
            "the ICIJ leak corpus surfaced ~219 distinct unique-on-both-sides names including "
            "well-known sanctioned figures, but a live UK CH search confirmed none of these "
            "names is on the current UK CH disqualified-officers register."
        ),
        why_anyone_would_care=(
            "Downgrade / methodology example. Demonstrates why dataset-name (OpenSanctions "
            "'gb_coh_disqualified') vs underlying-source-truth checks matter."
        ),
        asset_type="(none — leads track)",
        sector="financial_secrecy",
        property_titles_count=0,
        property_addresses_or_postcodes="",
        jurisdiction="various",
        roe_status="n/a",
        ocod_status="n/a",
        icij_overlap="219 distinct unique-on-both-sides matches surfaced; most filtered out on live verification",
        opensanctions_overlap="OS gb_coh_disqualified dataset turned out to over-classify sanctioned individuals as 'corp.disqual' beyond the CDDA court register",
        companies_house_match="0 of 219 names on the live UK CH disqualified-officers register (live search confirmed)",
        disqualified_director_overlap="(this IS the disqualified-director track)",
        public_money_exposure="",
        public_harm_exposure="",
        sanctions_or_enforcement_evidence="",
        court_or_regulatory_evidence="",
        offshore_structure_features="",
        source_files=[
            "ch_disqualified_live.json",
            "disqualified_verification_queue.json",
            "disqualified_verification_report.json",
            "docs/case_study_roe_noncompliance.md",
        ],
        source_urls=[],
        visual_hook="0 of 219 names confirmed on live UK CH disqualified-officers register — a clean downgrade.",
        manual_checks_required=[],
        bad_actor_evidence=1,
        public_money_or_public_harm=1,
        concealment_structure=1,
        property_visual_clarity=0,
        offshore_complexity=1,
        false_positive_risk=5,
        legal_risk=4,
        caveats=[
            "Discard the original disqualified-director track for naming purposes",
            "Useful as a methodology / downgrade example for documenting honest reframing",
        ],
        safe_sentence=(
            "An earlier track that cross-referenced ICIJ officer names against the "
            "OpenSanctions 'gb_coh_disqualified' dataset returned ~219 unique-on-both-sides "
            "names. A live UK Companies House search confirmed that none of the 219 names "
            "appears on the current UK CH disqualified-officers register. The OS dataset "
            "appears to classify sanctioned individuals as 'corp.disqual' beyond the strict "
            "UK CDDA court register. The track was downgraded as a result and is documented "
            "here as a methodology example."
        ),
    )


def discover_candidates(root: Path) -> list[Candidate]:
    builders = [
        _candidate_igt,
        _candidate_trade_initiative,
        _candidate_fenland,
        _candidate_ledra,
        _candidate_embassy,
        _candidate_healthcare_property,
        _candidate_medicx,
        _candidate_gas_transport,
        _candidate_profitable_plots,
        _candidate_park_plaza,
        _candidate_eko_ire,
        _candidate_harmony_ridge,
        _candidate_aar,
        _candidate_disqualified_directors,
    ]
    out: list[Candidate] = []
    for fn in builders:
        try:
            c = fn(root)
        except Exception as exc:  # noqa: BLE001
            log.warning("candidate %s failed: %s", fn.__name__, exc)
            c = None
        if c is not None:
            out.append(c)
    return out


def score(c: Candidate) -> int:
    """Apply the public-interest scoring formula."""
    return (
        3 * c.bad_actor_evidence
        + 3 * c.public_money_or_public_harm
        + 2 * c.concealment_structure
        + 2 * c.property_visual_clarity
        + 1 * c.offshore_complexity
        - 3 * c.false_positive_risk
        - 2 * c.legal_risk
    )


def recommend(c: Candidate) -> str:
    s = c.public_interest_score
    if s >= 35:
        return "lead"
    if s >= 25:
        return "strong_backup"
    if s >= 15:
        return "needs_manual_review"
    if s >= 5:
        return "use_as_context"
    if s >= -5:
        return "downgrade"
    return "discard"


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

_MD_HEADER = """# Public-Interest Lead Ranking

## Status

Machine-generated triage. **Not an allegation of wrongdoing.** Every candidate is a public-interest *lead* requiring human review before any publication. Sector and harm labels are weak (substring matches against entity names and addresses) and may be wrong.

## Executive verdict

The top three leads as ranked by `public_interest_score` are:

{top3_summary}

## Why this exists

Generic compliance gaps (a missing register filing here, an ICIJ overlap there) are hard for the public to care about. This report ranks leads where hidden ownership intersects with public harm, public money, sanctions, court findings, or regulated services, in a way a normal person can understand in one sentence.

## Scoring model

```
public_interest_score =
  3 * bad_actor_evidence
+ 3 * public_money_or_public_harm
+ 2 * concealment_structure
+ 2 * property_visual_clarity
+ 1 * offshore_complexity
- 3 * false_positive_risk
- 2 * legal_risk
```

Each component is scored 0-5. The formula is transparent on purpose: anyone can recompute any candidate's score from the per-component values.

Recommendation buckets (based on the score alone — manual override is expected):

| Score | Recommendation |
|---:|---|
| ≥ 35 | **lead** |
| 25-34 | strong_backup |
| 15-24 | needs_manual_review |
| 5-14 | use_as_context |
| −5 to 4 | downgrade |
| < −5 | discard |

## Top ranked leads

| Rank | Entity | One-sentence story | Why anyone would care | Sector / asset type | Evidence strength | Public-interest score | FP risk | Legal risk | Recommendation |
|---:|---|---|---|---|---|---:|---:|---:|---|
"""

_MD_PROFILE = """
### {rank}. {entity_name}

#### One-sentence story

{one_sentence_story}

#### Why anyone would care

{why_anyone_would_care}

#### Evidence chain

OCOD / property → overseas entity → ROE register status → ICIJ/OpenSanctions/court/regulator/public-money evidence → caveat.

- **OCOD / property**: {property_titles_count} title(s); {property_addresses_or_postcodes}; sector tags `{sector}`
- **Overseas entity**: {entity_name} ({jurisdiction})
- **UK ROE filing**: {roe_status}
- **ICIJ leak overlap**: {icij_overlap}
- **OpenSanctions overlap**: {opensanctions_overlap}
- **Companies House live check**: {companies_house_match}
- **Court / regulatory evidence**: {court_or_regulatory_evidence}
- **Sanctions / enforcement evidence**: {sanctions_or_enforcement_evidence}

#### What the repo supports

Source files referenced:

{source_files_md}

#### What is still missing

{manual_checks_md}

#### Safe sentence

> {safe_sentence}

#### Caveats

{caveats_md}

#### Score breakdown

bad_actor_evidence: {bad_actor_evidence}, public_money_or_public_harm: {public_money_or_public_harm}, concealment_structure: {concealment_structure}, property_visual_clarity: {property_visual_clarity}, offshore_complexity: {offshore_complexity}, false_positive_risk: {false_positive_risk}, legal_risk: {legal_risk} → **public_interest_score = {public_interest_score}** → recommendation: **{recommendation}**

"""

_MD_DOWNGRADES = """
## Downgrades and false positives

This section makes the ranker's downgrades explicit. Each is an example of something that *looks* like a story but, on inspection, is weaker or misleading than the headline implies.

{downgrades}
"""


def _bullets(items: list[str]) -> str:
    if not items:
        return "(none)"
    return "\n".join(f"- {i}" for i in items)


def write_markdown(scored: list[Candidate], out_path: Path) -> None:
    top3 = scored[:3]
    top3_summary = "\n".join(
        f"{i + 1}. **{c.entity_name}** (score {c.public_interest_score}). {c.one_sentence_story}"
        for i, c in enumerate(top3)
    )
    header = _MD_HEADER.format(top3_summary=top3_summary)
    rows = "\n".join(
        "| {rank} | {entity_name} | {one_sentence_story} | {why_anyone_would_care} | {sector} / {asset_type} | {evidence_summary} | {public_interest_score} | {false_positive_risk} | {legal_risk} | {recommendation} |".format(
            rank=c.rank,
            entity_name=c.entity_name.replace("|", "/"),
            one_sentence_story=(c.one_sentence_story or "")
            .replace("\n", " ")
            .replace("|", "/")[:180],
            why_anyone_would_care=(c.why_anyone_would_care or "")
            .replace("\n", " ")
            .replace("|", "/")[:180],
            sector=c.sector or "",
            asset_type=c.asset_type or "",
            evidence_summary=f"BA={c.bad_actor_evidence}/PM={c.public_money_or_public_harm}/CS={c.concealment_structure}/PVC={c.property_visual_clarity}/OC={c.offshore_complexity}",
            public_interest_score=c.public_interest_score,
            false_positive_risk=c.false_positive_risk,
            legal_risk=c.legal_risk,
            recommendation=c.recommendation,
        )
        for c in scored
    )

    profiles_md = ""
    for c in scored[:10]:
        profiles_md += _MD_PROFILE.format(
            rank=c.rank,
            entity_name=c.entity_name,
            one_sentence_story=c.one_sentence_story,
            why_anyone_would_care=c.why_anyone_would_care,
            property_titles_count=c.property_titles_count,
            property_addresses_or_postcodes=c.property_addresses_or_postcodes or "(not extracted)",
            sector=c.sector or "(unclassified)",
            jurisdiction=c.jurisdiction or "(unknown)",
            roe_status=c.roe_status,
            icij_overlap=c.icij_overlap or "(none in current artefacts)",
            opensanctions_overlap=c.opensanctions_overlap or "(none in current artefacts)",
            companies_house_match=c.companies_house_match,
            court_or_regulatory_evidence=c.court_or_regulatory_evidence
            or "(none in current artefacts)",
            sanctions_or_enforcement_evidence=c.sanctions_or_enforcement_evidence
            or "(none in current artefacts)",
            source_files_md=_bullets(c.source_files),
            manual_checks_md=_bullets(c.manual_checks_required),
            safe_sentence=c.safe_sentence,
            caveats_md=_bullets(c.caveats),
            bad_actor_evidence=c.bad_actor_evidence,
            public_money_or_public_harm=c.public_money_or_public_harm,
            concealment_structure=c.concealment_structure,
            property_visual_clarity=c.property_visual_clarity,
            offshore_complexity=c.offshore_complexity,
            false_positive_risk=c.false_positive_risk,
            legal_risk=c.legal_risk,
            public_interest_score=c.public_interest_score,
            recommendation=c.recommendation,
        )

    downgrades = [c for c in scored if c.recommendation in ("downgrade", "discard")]
    if len(downgrades) < 3:
        # also include high-fp-risk items
        downgrades += [c for c in scored if c.false_positive_risk >= 3 and c not in downgrades][
            : 3 - len(downgrades)
        ]
    downgrades_md = "\n".join(
        f"### Downgrade — {c.entity_name}\n\n{c.one_sentence_story}\n\n**Why it ranked low**: false_positive_risk={c.false_positive_risk}, legal_risk={c.legal_risk}, score={c.public_interest_score}. {c.caveats[0] if c.caveats else ''}\n"
        for c in downgrades[:5]
    )

    next_actions_md = ""
    for c in scored[:3]:
        next_actions_md += (
            f"### Next actions for #{c.rank} — {c.entity_name}\n\n"
            + _bullets(c.manual_checks_required)
            + "\n\n"
        )

    md = (
        header
        + rows
        + "\n"
        + "\n## Lead profiles\n"
        + profiles_md
        + _MD_DOWNGRADES.format(downgrades=downgrades_md)
        + "\n## Next actions\n\n"
        + next_actions_md
    )
    out_path.write_text(md, encoding="utf-8")
    log.info("wrote %s", out_path)


def write_csv(scored: list[Candidate], out_path: Path) -> None:
    fields = list(asdict(scored[0]).keys()) if scored else []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in scored:
            row = asdict(c)
            # Flatten lists
            for k, v in row.items():
                if isinstance(v, list):
                    row[k] = " | ".join(str(x) for x in v)
            w.writerow(row)
    log.info("wrote %s", out_path)


def write_evidence_csv(scored: list[Candidate], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "entity_name", "evidence_class", "evidence_value"])
        for c in scored:
            for ec, ev in [
                ("ocod_status", c.ocod_status),
                ("roe_status", c.roe_status),
                ("icij_overlap", c.icij_overlap),
                ("opensanctions_overlap", c.opensanctions_overlap),
                ("companies_house_match", c.companies_house_match),
                ("disqualified_director_overlap", c.disqualified_director_overlap),
                ("sanctions_or_enforcement_evidence", c.sanctions_or_enforcement_evidence),
                ("court_or_regulatory_evidence", c.court_or_regulatory_evidence),
                ("public_money_exposure", c.public_money_exposure),
                ("public_harm_exposure", c.public_harm_exposure),
                ("offshore_structure_features", c.offshore_structure_features),
                ("visual_hook", c.visual_hook),
                ("safe_sentence", c.safe_sentence),
            ]:
                if ev:
                    w.writerow([c.rank, c.entity_name, ec, ev])
    log.info("wrote %s", out_path)


def write_json(scored: list[Candidate], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(c) for c in scored]
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log.info("wrote %s", out_path)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--md-out", type=Path, default=Path("docs/reports/public_interest_leads.md"))
    p.add_argument(
        "--csv-out", type=Path, default=Path("docs/reports/data/public_interest_leads.csv")
    )
    p.add_argument(
        "--json-out", type=Path, default=Path("docs/reports/data/public_interest_leads.json")
    )
    p.add_argument(
        "--evidence-csv-out",
        type=Path,
        default=Path("docs/reports/data/public_interest_leads_evidence.csv"),
    )
    p.add_argument(
        "--run-external-search",
        action="store_true",
        help="Reserved for future external lookups; not used by default.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    candidates = discover_candidates(args.root)
    log.info("discovered %d candidates", len(candidates))

    for c in candidates:
        c.public_interest_score = score(c)
        c.recommendation = recommend(c)

    candidates.sort(key=lambda c: -c.public_interest_score)
    for i, c in enumerate(candidates, start=1):
        c.rank = i

    write_markdown(candidates, args.md_out)
    write_csv(candidates, args.csv_out)
    write_json(candidates, args.json_out)
    write_evidence_csv(candidates, args.evidence_csv_out)

    log.info("top 5:")
    for c in candidates[:5]:
        log.info(
            "  %d. %s (score %d, %s)",
            c.rank,
            c.entity_name,
            c.public_interest_score,
            c.recommendation,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
