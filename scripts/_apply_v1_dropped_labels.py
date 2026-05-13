"""Apply Claude's research-assistant labels to the v1_dropped bucket.

Each label is a deliberate assertion. Rationale notes the basis: name
inspection, public-source knowledge, or marked unsure when the call
genuinely could go either way without independent records.

Methodology + caveats are documented in
``data/labels/marginal_v1.labelled_v1dropped_methodology.md``.
"""

from __future__ import annotations

import csv
from pathlib import Path

LABELS: dict[str, tuple[str, str]] = {
    # 6 likely matches: identical names + same jurisdiction; score below
    # 0.92 only because the address component diverged (different leaks
    # captured different address rows for the same legal entity).
    "P0016": (
        "match",
        "Identical name + same BVI jurisdiction; score depressed by diverging address rows across two leak captures of one company.",
    ),
    "P0041": (
        "match",
        "Identical name 'EAGLE SECURITIES LIMITED' + same BVI jurisdiction; address-only divergence.",
    ),
    "P0049": (
        "match",
        "Identical name 'Gold Medallion Investments Corporation' + same BVI jurisdiction; address-only divergence.",
    ),
    "P0066": (
        "match",
        "Identical name 'SMART ADVISORS INVESTMENT LIMITED' + same BVI jurisdiction (case differs only); address-only divergence.",
    ),
    "P0071": (
        "match",
        "Identical name 'FADUL INVESTMENTS LIMITED' + same BVI jurisdiction; address-only divergence.",
    ),
    "P0093": (
        "match",
        "Identical name 'Silver Melody Capital Ltd' + same BVI jurisdiction (case differs only); address-only divergence.",
    ),
    # ~14 unsure: name structure suggests possibly-related entities (parent /
    # subsidiary / sister fund / family business) but they are at minimum
    # legally distinct and could plausibly be either same legal entity or
    # related-but-separate.
    "P0004": (
        "unsure",
        "Both 'OASIS INTERNATIONAL INVEST...' / BVI; could be same group with two registrations or distinct sub-entities. No public coverage.",
    ),
    "P0027": (
        "unsure",
        "GLOBAL STRATEGIC CAPITAL PTE / GLOBAL STRATEGIC FUND, both Singapore. Plausibly manager+fund pair; need registry confirmation.",
    ),
    "P0030": (
        "unsure",
        "Intrepid Africa (BVI) / Intrepid International, both BVI. 'Africa' subsidiary of 'International' is plausible.",
    ),
    "P0031": (
        "unsure",
        "CRYSTAL ASSET GROUP / Crystal Group, both BVI. Possibly parent/subsidiary of same Crystal corporate group.",
    ),
    "P0034": (
        "unsure",
        "East Africa Investment Managers / EAST AFRICAN HOLDINGS, both Bermuda. Possibly related East Africa-focused vehicles.",
    ),
    "P0035": (
        "unsure",
        "SCHEMBRI BARBROS / SCHEMBRI FINANCE p.l.c., both Malta. Schembri is a common Maltese family/business name; possibly related family business.",
    ),
    "P0045": (
        "unsure",
        "VinaCapital Group / VINACAPITAL INVESTMENT MANAGEMENT, both BVI. Both real VinaCapital-branded entities — likely sister entities of one Vietnam-focused investment group.",
    ),
    "P0056": (
        "unsure",
        "BONELLO VRTS / BONELLO SERVICE STATION, both Malta. Possibly related Bonello-family entities.",
    ),
    "P0068": (
        "unsure",
        "BELLSHILL INVESTMENTS / Bellshill Holdings, both BVI. Possibly related Bellshill-themed entities.",
    ),
    "P0069": (
        "unsure",
        "STAFFCO MALTA HOLDING / STAFFCO MALTA TREASURY, both Malta. Naming pattern strongly suggests sister entities in one StaffCo Malta corporate group.",
    ),
    "P0074": (
        "unsure",
        "NOBLESSE UNIVERSAL / Noblesse Real Estate, both BVI. Possibly related Noblesse-themed entities.",
    ),
    "P0080": (
        "unsure",
        "Artemis UK Properties Holdco / ARTEMIS INVESTMENT HOLDINGS, both Jersey. Artemis Investment Management is a known UK fund manager; possibly related vehicle.",
    ),
    "P0081": (
        "unsure",
        "BELGRAVE HOLDINGS / Belgrave Investments, both Malta. Naming overlap strong but distinct legal-form suffixes.",
    ),
    # ~80 clear no-matches — different legal entities sharing only a leading
    # token. Same-jurisdiction collisions on common words like Pacific,
    # Newport, Evolution, European, Global, International, Atlantic, Bermuda,
    # Cayman, etc. — and the Aruba 'STICHTING <X>' family that all matched
    # to a single pension-fund stichting via leading-prefix blocking.
    "P0001": (
        "no_match",
        "Pacific Crossing Holdings (defunct trans-Pacific fiber JV) vs Pacific Basin Shipping (LSE/HK-listed dry bulk operator). Distinct businesses.",
    ),
    "P0002": (
        "no_match",
        "Newport Energy (Caribbean utility) vs Newport Waves CDO (2004-vintage CDO vehicle). Distinct entities.",
    ),
    "P0003": (
        "no_match",
        "Evolution DMC Limited (destination management) vs Evolution Travel Ltd. Distinct legal entities even if both travel-sector.",
    ),
    "P0005": (
        "no_match",
        "Addison Management vs Addison Estates — different second-token, different business descriptors.",
    ),
    "P0006": (
        "no_match",
        "Will trusts of two different individuals (Frances Irene Ashworth vs Frank Sharples).",
    ),
    "P0007": (
        "no_match",
        "Nordic-Link Shipping vs Nordic Light Limited — different second token, distinct entities.",
    ),
    "P0008": (
        "no_match",
        "Splendid Oasis Holdings vs Splendid Heights International — different entities sharing only 'Splendid'.",
    ),
    "P0009": (
        "no_match",
        "STICHTING SAVE OUR IGUANAS (an Aruban environmental foundation) vs STICHTING PENSIOENFONDS META BEDRIJVEN ARUBA (a pension fund). Distinct.",
    ),
    "P0010": (
        "no_match",
        "European Pilot Academy vs European Lotto and Betting — distinct industries.",
    ),
    "P0011": ("no_match", "Fortune Star vs Fortune Marshall — different second-token."),
    "P0012": (
        "no_match",
        "Capital Advisory Services One vs Capital Di Limited — different entities.",
    ),
    "P0013": (
        "no_match",
        "Universal Transfer vs Universal Distribution Worldwide — different entities.",
    ),
    "P0014": (
        "no_match",
        "Global Step International vs Global Solid International — different entities.",
    ),
    "P0015": (
        "no_match",
        "Forward Freight Logistics vs Forward Media Limited — different industries.",
    ),
    "P0017": (
        "no_match",
        "STICHTING CENTRO DEPORTIVO TANKI LENDER vs STICHTING PENSIOENFONDS META BEDRIJVEN ARUBA — distinct stichting types (sports vs pension).",
    ),
    "P0018": ("no_match", "Eastern Sky Investments 6A vs Eastern Elm Company — distinct."),
    "P0019": (
        "no_match",
        "Serendipity Shipping vs Serendipity Maritime — distinct legal entities even if both maritime.",
    ),
    "P0020": (
        "no_match",
        "STICHTING PRO TEATRO ARUBA vs STICHTING PENSIOENFONDS — distinct stichtings (theatre vs pension).",
    ),
    "P0021": (
        "no_match",
        "Sequoia Systematic Fund vs Sequoia Capital Global Growth Fund II — distinct fund vehicles, different fund families.",
    ),
    "P0022": ("no_match", "Galileo Property vs Galileo Space — distinct industries."),
    "P0023": (
        "no_match",
        "General Electrical and Mechanical vs General Cleaners — distinct industries.",
    ),
    "P0024": (
        "no_match",
        "Union Express Investment vs Union Express Technology — distinct entities.",
    ),
    "P0025": (
        "no_match",
        "Financial Investment Trust vs Financial Planning Services — distinct entities.",
    ),
    "P0026": (
        "no_match",
        "Golden Concord Energy Investment Holdings vs Golden Cone Inc. — distinct entities.",
    ),
    "P0028": ("no_match", "Strategic Link Services vs Strategic Alliana Group — distinct."),
    "P0029": ("no_match", "Seashells Capital vs Seashell Group — distinct entities."),
    "P0032": ("no_match", "Target Group vs Target Global Advisors — distinct."),
    "P0033": (
        "no_match",
        "International Link Company vs International Bond Fund — distinct industries.",
    ),
    "P0036": (
        "no_match",
        "Bonello and Ciantar (accountancy) vs Bonello Service Station — distinct businesses.",
    ),
    "P0037": ("no_match", "Harvard Group vs Harvard International Finance — distinct entities."),
    "P0038": ("no_match", "Jupiter Maritime vs Jupiter Capital Fund — distinct industries."),
    "P0039": (
        "no_match",
        "STICHTING AMICUS BEHEER vs STICHTING PENSIOENFONDS — distinct stichtings.",
    ),
    "P0040": (
        "no_match",
        "China Pro Asset Management vs China Privilege International — distinct entities.",
    ),
    "P0042": ("no_match", "General Maintenance vs General Plastics — distinct industries."),
    "P0043": (
        "no_match",
        "Valletta Light Clothing vs Valletta Credit Finance — distinct industries.",
    ),
    "P0044": ("no_match", "Classico Mobile vs Classico Investments — distinct entities."),
    "P0046": (
        "no_match",
        "Renaissance Russia Distressed Assets vs Renaissance Reinsurance — distinct (Renaissance Capital vs RenRe).",
    ),
    "P0047": ("no_match", "Atlantic Concord vs Atlantic Services — distinct."),
    "P0048": (
        "no_match",
        "St Julian's Heights vs St Julian's Maritime Finance — distinct (Maltese locality + different industries).",
    ),
    "P0050": ("no_match", "International Oil Group vs International Alliance Group — distinct."),
    "P0051": ("no_match", "Champion Eagle vs Champion Merry — distinct."),
    "P0052": (
        "no_match",
        "Lifetime Limited vs Lifetime Occupational Pension Scheme — distinct (corporate vs pension scheme).",
    ),
    "P0053": ("no_match", "Global Prize vs Global Profit Assets — distinct."),
    "P0054": (
        "no_match",
        "Independent Mobile Productions vs Independent Holding Company — distinct industries.",
    ),
    "P0055": (
        "no_match",
        "International Fashion Company vs International Hotel Investments PLC — distinct industries.",
    ),
    "P0057": (
        "no_match",
        "Genesis International Consultancy vs Genesis Research Financial — distinct.",
    ),
    "P0058": (
        "no_match",
        "Valletta Consulting Services vs Valletta Bunkers (marine fuel) — distinct industries.",
    ),
    "P0059": ("no_match", "Major International vs Major Investment Holdings — distinct."),
    "P0060": ("no_match", "Amazing Venture vs Amazing Opportunity — distinct."),
    "P0061": ("no_match", "Brothers Twelve Shipping vs Brothers Holding — distinct."),
    "P0062": ("no_match", "STICHTING JET vs STICHTING PENSIOENFONDS — distinct stichtings."),
    "P0063": (
        "no_match",
        "Meridian Maritime vs Meridian Global Opportunities Fund — distinct industries.",
    ),
    "P0064": (
        "no_match",
        "African Iron Ore Investments vs African Lion 3 — distinct mining vehicles.",
    ),
    "P0065": ("no_match", "Blue Sea Leasing vs Blue Seas Yacht — distinct."),
    "P0067": (
        "no_match",
        "Global Marketing vs Global Multi-Asset Sub-Fund — distinct (corporate vs investment fund).",
    ),
    "P0070": ("no_match", "Seminole Enterprise vs Seminole Dedicated Investor Fund — distinct."),
    "P0072": (
        "no_match",
        "International Isotopes Consulting vs International Seaways Operating Corp — distinct industries.",
    ),
    "P0073": (
        "no_match",
        "Building Internal Restructuring vs Building Block Insurance PCC — distinct.",
    ),
    "P0075": (
        "no_match",
        "Transatlantic Management vs TransAtlantic Petroleum (a real listed E&P company) — distinct.",
    ),
    "P0076": ("no_match", "Pacific Chimes vs Pacific Winners — distinct."),
    "P0077": ("no_match", "Financial Junction vs Financial Planning Services — distinct."),
    "P0078": (
        "no_match",
        "Franciscus Limited (corporate) vs Franciscan Province of St Paul (religious order) — distinct.",
    ),
    "P0079": (
        "no_match",
        "Bermuda Capital Company vs Bermuda Life Insurance — distinct industries.",
    ),
    "P0082": (
        "no_match",
        "Valletta Freight Services vs Valletta Benefit Trust — distinct industries.",
    ),
    "P0083": (
        "no_match",
        "Partners Segregated Portfolio vs Partners Global Opportunities Fund — different sub-funds even if same fund family.",
    ),
    "P0084": ("no_match", "Horizon Group vs Horizon Plus Fund — distinct industries."),
    "P0085": ("no_match", "Montana Global Corp vs Montana Advisors — distinct."),
    "P0086": ("no_match", "Central Holdings vs Central Flats Trust — distinct industries."),
    "P0087": (
        "no_match",
        "Educational Services and Testing vs Education Capital Investments Fund — distinct industries.",
    ),
    "P0088": ("no_match", "Andover Finance vs Andover Ventures — distinct."),
    "P0089": (
        "no_match",
        "Bermuda National Trust Endowment (heritage NGO) vs Bermuda First Investment — distinct industries.",
    ),
    "P0090": (
        "no_match",
        "Cayman Angel Investors Network vs Cayman Aggregator 2 LP — distinct vehicles.",
    ),
    "P0091": (
        "no_match",
        "T T Grime Will Trust vs T T Grime 1989 Settlement — same individual T T Grime, but distinct legal vehicles (will trust vs settlement).",
    ),
    "P0092": ("no_match", "General Promotions vs General Plastics — distinct industries."),
    "P0094": ("no_match", "Kingdom Entertainment vs Kingdom Generation Lithamal NV — distinct."),
    "P0095": (
        "no_match",
        "Global Marine Ships vs Global Media Distribution Fund SICAV — distinct industries (shipping vs media fund).",
    ),
    "P0096": (
        "no_match",
        "Oakwood Investments vs Oakwood Holdings — distinct entities sharing only 'Oakwood'.",
    ),
    "P0097": ("no_match", "Accurate Limited vs Accurate Management — distinct."),
    "P0098": ("no_match", "Orion Construction vs Orion Co-VI — distinct."),
    "P0099": (
        "no_match",
        "Permanent Holdings (Cayman) vs Permanence Cayman Portfolio — distinct vehicles.",
    ),
    "P0100": (
        "no_match",
        "Mermaid International Ventures vs Mermaid Nordic Cayman Master Fund — distinct.",
    ),
}


def main() -> None:
    src = Path("data/labels/marginal_v1.csv")
    dst = Path("data/labels/marginal_v1.csv")  # in-place

    rows = list(csv.DictReader(src.open(encoding="utf-8")))
    written = 0
    for r in rows:
        if r["pair_id"] in LABELS and r["bucket"] == "v1_dropped":
            label, rationale = LABELS[r["pair_id"]]
            r["label"] = label
            r["rationale"] = rationale
            written += 1

    fieldnames = list(rows[0].keys())
    with dst.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"applied {written} v1_dropped labels to {dst}")
    print(f"expected 100 rows in v1_dropped bucket; matched {written}")


if __name__ == "__main__":
    main()
