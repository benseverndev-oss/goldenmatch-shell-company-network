"""Apply Claude's research-assistant labels to the remaining 200 pairs.

Same methodology as scripts/_apply_v1_dropped_labels.py — see
data/labels/marginal_v1_methodology.md.
"""

from __future__ import annotations

import csv
from pathlib import Path

# v2_marginal (P0101-P0200, n=100): still-marginal v2 keeps in 0.92-0.97
V2_MARGINAL: dict[str, tuple[str, str]] = {
    "P0101": ("no_match", "Colchester Beta Two vs Beta Three — different sub-funds in series."),
    "P0102": ("match", "Service Immobiliere/Immobilier et Gestion SAS — French SAS, spelling variant of one entity."),
    "P0103": ("no_match", "Golden State Re vs Golden State Re II — different reinsurance vehicles."),
    "P0104": ("match", "Team Force Renewable Energies Limited — identical."),
    "P0105": ("no_match", "West CLO 2012-1 vs West CLO 2014-1 — different vintages."),
    "P0106": ("unsure", "Certares GBT Holdings vs Certares Holdings LLC — possibly related Certares group entities, but different legal forms."),
    "P0107": ("match", "Aplus Assets Worldwide Ltd — identical."),
    "P0108": ("match", "MALTA UNIVERSITY HOLDING COMPANY LIMITED vs Malta University Holding Co Ltd — same entity, suffix expansion only."),
    "P0109": ("match", "The Hankey No 1 Settlement vs THE HANKEY NO1 SETTLEMENT — same trust, only spacing differs."),
    "P0110": ("unsure", "Atlas Senior Loan Fund III, Ltd. Trust vs Ltd — Trust label may mean a separate trust vehicle for the same CLO."),
    "P0111": ("no_match", "Loeb Offshore B Fund vs Loeb Offshore Fund — distinct sub-funds."),
    "P0112": ("match", "Lokesh Machines Limited/LTD — identical."),
    "P0113": ("match", "INDISOL MARKETING PRIVATE LIMITED — identical."),
    "P0114": ("match", "SUPERSONIC VENTURES LIMITED — identical."),
    "P0115": ("unsure", "ALF. MIZZI & SONS (HR) LTD vs ALF. MIZZI & SONS LTD — (HR) suggests an HR-services subsidiary distinct from the parent."),
    "P0116": ("match", "PERSISTENT PETROCHEM PRIVATE LIMITED — identical."),
    "P0117": ("no_match", "IVM 041 vs IVM 047 PURPOSE TRUST — different sub-trusts in the IVM series."),
    "P0118": ("unsure", "Shipstern Global Opportunities Fund vs Master Fund — master/feeder vehicles can be distinct legal entities or share LEIs depending on structure."),
    "P0119": ("no_match", "PA Grand Opportunity VI Limited vs main — different sub-fund."),
    "P0120": ("unsure", "Brookside Mill CLO Ltd. Trust vs Ltd — Trust label may indicate distinct trust vehicle."),
    "P0121": ("match", "IRON WILL INVESTMENT LTD — identical."),
    "P0122": ("match", "First Crockford Advisors/Advisers Ltd — same entity, US/UK spelling variant."),
    "P0123": ("no_match", "Elementum NatCat Offshore Fund vs Fund II — different vintages."),
    "P0124": ("match", "HIGH WORLD MANAGEMENT LIMITED — identical."),
    "P0125": ("no_match", "ALM VII(R) vs ALM VII(R)-2 — distinct CLO vintages."),
    "P0126": ("match", "Starline Circle Limited — identical."),
    "P0127": ("no_match", "Morgan Stanley Reinsurance Alpha Ltd vs main MS Reinsurance Ltd — distinct sub-vehicle."),
    "P0128": ("no_match", "MEDSEA INVESTMENTS LIMITED vs Medsea Investments Two Limited — distinct."),
    "P0129": ("match", "PICOTIN HOLDINGS LIMITED — identical."),
    "P0130": ("no_match", "Mediterranean Trade vs Mediterranean Travel Services — different industries."),
    "P0131": ("unsure", "Bridge Electronic Trading Ltd vs Bridge Electronic Trading (BVI) Ltd — (BVI) suffix may denote BVI subsidiary distinct from parent."),
    "P0132": ("match", "SUEX OTC s.r.o. — identical Czech sro (note: SUEX was sanctioned by US Treasury in 2021 for crypto-money-laundering)."),
    "P0133": ("match", "ASIA FORTUNE GROUP LIMITED — identical."),
    "P0134": ("unsure", "Investcorp Aerwulf Credit Opportunities Fund vs Master Fund — master/feeder pair, may share or have distinct LEIs."),
    "P0135": ("unsure", "KB HOLDING LIMITED vs KB HOLDINGS LTD — Holding/Holdings could be same entity or separate."),
    "P0136": ("no_match", "INTERTRUST TRUSTEES II vs Intertrust Trustees — distinct."),
    "P0137": ("no_match", "ADVANTECH HOLDINGS LIMITED vs Advantec Holding S.A. — distinct (different spelling, different legal form)."),
    "P0138": ("unsure", "Atlas Senior Loan Fund IV, Ltd. Trust vs Ltd — Trust label may indicate separate trust vehicle."),
    "P0139": ("no_match", "CLO Repackaging 2014-2 vs 2014-1 — different vintages."),
    "P0140": ("match", "Red Win Enterprise Ltd — identical."),
    "P0141": ("no_match", "CVP Cascade CLO -1 vs -3 — different vintages."),
    "P0142": ("no_match", "Altitude X3 vs X2 — different sub-vehicles."),
    "P0143": ("match", "GPB-DI HOLDINGS LIMITED — identical."),
    "P0144": ("match", "MCC Group Ltd — identical."),
    "P0145": ("unsure", "GY AVIATION LEASE (MALTA) LIMITED vs GY Aviation Lease (Malta) Co. Limited — Co. suffix variant; could be same entity or sister."),
    "P0146": ("no_match", "CORPORACION CIMEX, S.A. vs CORPORACION COEX, INC. — distinct entities (note: CIMEX is a sanctioned Cuban entity)."),
    "P0147": ("no_match", "PSAM WorldArb SRI Fund vs PSAM WorldArb Fund — SRI is a distinct ESG sub-fund."),
    "P0148": ("no_match", "Golden Heritage vs Golden Hedge Investments — distinct."),
    "P0149": ("no_match", "CVP Cascade CLO-2 vs -3 — different vintages."),
    "P0150": ("no_match", "INFINITY INTERNATIONAL CORP vs Infinity Grow International — distinct."),
    "P0151": ("match", "OCEAN LEONID INVESTMENTS AG — identical Swiss AG."),
    "P0152": ("match", "Azla Advisors Ltd. — identical."),
    "P0153": ("unsure", "Golub Capital Partners CLO 16 vs 16(M)-R — (M)-R indicates a refinanced master tranche; may be the same underlying CLO or a distinct refinanced vehicle."),
    "P0154": ("no_match", "NATURA DEVELOPMENT II N.V. vs NATURA DEVELOPMENT N.V. — distinct."),
    "P0155": ("no_match", "Global Asia Opportunity IV vs V — distinct sub-funds."),
    "P0156": ("match", "Bronze Pacific Corporation — identical."),
    "P0157": ("no_match", "AVANTRADER vs AVANTRADE — distinct."),
    "P0158": ("match", "SHARPLINE AUTOMATION PRIVATE LIMITED — identical."),
    "P0159": ("no_match", "TICP CLO II vs IX — different vintages."),
    "P0160": ("no_match", "Windsor Properties (6) Limited vs Windsor Properties Limited — distinct sub-vehicles in series."),
    "P0161": ("match", "DISNEY GARDEN LIMITED — identical."),
    "P0162": ("match", "CHEMOVICK PRIVATE LIMITED — identical."),
    "P0163": ("match", "VH Antibes SAS — identical French SAS."),
    "P0164": ("no_match", "PAMPLONA CREDIT OPPORTUNITIES INVESTMENTS HOLDING LIMITED vs INVESTMENTS LIMITED — holdco vs underlying portfolio entity."),
    "P0165": ("unsure", "ASSIKURA INSURANCE BROKERS LTD vs PCC LTD — PCC (Protected Cell Company) is a distinct legal form for Malta; could be same entity restructured or two distinct entities."),
    "P0166": ("match", "Knightsbridge International Ventures Ltd — identical."),
    "P0167": ("match", "Highland Gold Mining Limited — identical."),
    "P0168": ("unsure", "Golub Capital Partners CLO 11, Ltd. Trust vs Ltd — Trust label."),
    "P0169": ("match", "ASEAN CAPITAL HOLDINGS S.A — identical (case differs only)."),
    "P0170": ("no_match", "Windsor Properties (2) vs main — distinct sub-vehicle."),
    "P0171": ("match", "Actionwheels Inc. — identical."),
    "P0172": ("match", "Attica Offshore Limited — identical."),
    "P0173": ("no_match", "Windsor Properties (14) vs main — distinct sub-vehicle."),
    "P0174": ("no_match", "GREAT EAGLE vs Great Ease Investments — distinct."),
    "P0175": ("no_match", "SILVERIN vs Silverine Investment — distinct (different name root)."),
    "P0176": ("match", "SHREEJI GEMS LTD — identical."),
    "P0177": ("match", "Bickley Hill Inc. — identical."),
    "P0178": ("unsure", "Phoenix Real Estate Fund GP vs Fund (T) L.P. — GP and Fund are distinct legal vehicles in same fund structure."),
    "P0179": ("match", "TAIWIN INTERNATIONAL LTD — identical."),
    "P0180": ("no_match", "Orion Co-Investments I vs III — distinct vintages."),
    "P0181": ("no_match", "Aeolus Property Catastrophe Spire Fund LP vs Sphaera Fund Ltd — distinct sub-funds (different name + different legal form)."),
    "P0182": ("no_match", "PA Grand Opportunity X vs main — distinct sub-vehicle."),
    "P0183": ("match", "Hirondelle Holdings Group Ltd — identical."),
    "P0184": ("match", "ELEGANT SOURCE HOLDINGS LIMITED — identical."),
    "P0185": ("match", "Brookfield Renewable Energy Partners L.P. vs Brookfield Renewable Partners L.P. — same entity; renamed in 2016 (publicly documented BEP rebrand)."),
    "P0186": ("no_match", "JMP CLO II vs III (R) — different vintages."),
    "P0187": ("match", "PowerFinance International Ltd — identical."),
    "P0188": ("unsure", "Invesco Active Multi-Sector Credit Fund (Cayman) vs main — (Cayman) is a regional flag; likely same fund but parent group runs multi-jurisdictional vehicles."),
    "P0189": ("no_match", "PA Grand Opportunity II vs main — distinct sub-vehicle."),
    "P0190": ("match", "VIRTUOSITY INVESTMENT CO., LTD — identical."),
    "P0191": ("no_match", "JMP FINANCE B vs JMP FINANCE A — distinct sub-vehicles."),
    "P0192": ("no_match", "GL Finance III vs I — distinct vintages."),
    "P0193": ("no_match", "INCLINE B MALTACO ONE vs TWO — distinct."),
    "P0194": ("unsure", "AEROSPACE INSPECTION TRAINING MALTA LIMITED vs HOLDING LTD — operating co vs holdco in same group."),
    "P0195": ("match", "PACIFIC WINNERS SERVICES LIMITED — identical."),
    "P0196": ("no_match", "Free Spirit vs FREE SPIRIT - A — distinct sub-vehicle."),
    "P0197": ("no_match", "The Star Trust vs The Staro Trust — distinct."),
    "P0198": ("no_match", "AUDENTIA CAPITAL SICAV PLC vs SICAV II PLC — distinct."),
    "P0199": ("no_match", "Manulife (International) P & C Limited vs MANULIFE (INTERNATIONAL) LIMITED — P&C is a distinct property-and-casualty subsidiary."),
    "P0200": ("match", "Amazing Opportunity Ltd — identical."),
}

# perfect_sanity (P0201-P0250, n=50): random v1 score=1.0 pairs
PERFECT_SANITY: dict[str, tuple[str, str]] = {
    pid: ("match", "Identical legal name (case/punctuation only); perfect-band sanity-check passes.")
    for pid in [f"P{i:04d}" for i in range(201, 251)]
}

# v2_borderline_class (P0251-P0300, n=50): jur_close + jur_loose v2 keeps
V2_BORDERLINE: dict[str, tuple[str, str]] = {
    "P0251": ("match", "NOVA RENEWABLE ENERGY (NOVARE) FUND SICAV P.L.C. vs PLC — same entity, dot variant."),
    "P0252": ("no_match", "PA Grand Opportunity III vs main — distinct sub-vehicle."),
    "P0253": ("no_match", "STAMFORD MANAGEMENT vs Stamford Land Management — distinct (Stamford Land is a publicly-listed Singapore real-estate co)."),
    "P0254": ("no_match", "IKOS Currency Limited vs IKOS CURRENCY D LIMITED — distinct sub-funds."),
    "P0255": ("no_match", "Windsor Properties (5) vs main — distinct sub-vehicle."),
    "P0256": ("no_match", "Lilly Asia Ventures Fund I vs II — distinct vintages."),
    "P0257": ("unsure", "Birchwood Park CLO, Ltd. Trust vs Ltd — Trust label."),
    "P0258": ("match", "Cailon Capital Global Opportunities Master Fund Ltd — identical."),
    "P0259": ("match", "Golub Capital Partners CLO Holdings Ltd. — identical (comma variant only)."),
    "P0260": ("unsure", "Zen Shipping & Port India vs ZEN SHIPPING & PORTS INDIA — Port/Ports may be a typo or distinct registration."),
    "P0261": ("unsure", "Golub Capital Partners CLO 22(B) vs 22(B)-R — refinanced version may share or have distinct LEIs."),
    "P0262": ("no_match", "JMP CLO II vs III — distinct vintages."),
    "P0263": ("no_match", "AUDENTIA SICAV PLC vs SICAV II PLC — distinct."),
    "P0264": ("no_match", "PA Grand Opportunity IV vs main — distinct sub-vehicle."),
    "P0265": ("no_match", "PAMPLONA PE INVESTMENTS HOLDING vs HOLDING II — distinct."),
    "P0266": ("no_match", "Golub Capital Partners CLO 17 vs 15 — different vintages."),
    "P0267": ("no_match", "Morningside China TMT Fund I vs IV — distinct vintages."),
    "P0268": ("unsure", "Scopia LB International Master Fund vs Scopia Long International Master Fund — LB may abbreviate Long Bias=Long; could be renamed same entity."),
    "P0269": ("unsure", "Madison Park Funding VIII Trust vs Ltd — Trust label."),
    "P0270": ("unsure", "VistaJet Malta Aircraft Eleven Limited vs Eleven MAPCC Limited — MAPCC suffix changes legal form."),
    "P0271": ("no_match", "NATURA DEVELOPMENT II vs NATURA DEVELOPMENT N.V. — distinct (same as P0154 — appears twice)."),
    "P0272": ("match", "Patricia Jane Roberts Zagal Settlement vs DE Zagal Settlement — same person trust, missing 'de' particle."),
    "P0273": ("no_match", "White Peak Investments 2 vs main — distinct sub-vehicle."),
    "P0274": ("unsure", "Denali Capital CLO X, Ltd. Trust vs Ltd — Trust label."),
    "P0275": ("unsure", "Golub Capital Partners CLO 23(B) vs 23(B)-R — refinanced version."),
    "P0276": ("match", "AEROSPACE INSPECTION TRAINING MALTA HOLDING LIMITED — identical."),
    "P0277": ("no_match", "Windsor Properties (7) vs main — distinct sub-vehicle."),
    "P0278": ("match", "Kompas Kimyevi Maddeler Pazarlama Ticaret ve Sanayi A.S. — identical Turkish name (case differs only; the ?'s are encoding artifacts of Turkish characters)."),
    "P0279": ("unsure", "Golub Capital Partners CLO 11, Ltd. Trust vs Ltd — Trust label."),
    "P0280": ("unsure", "Octagon Investment Partners XVII Trust vs LTD — Trust label."),
    "P0281": ("no_match", "Mapeley Beta Acquisition Co (5) vs (1) — distinct sub-vehicles in series."),
    "P0282": ("match", "Mapeley Beta Acquistion Co (1) vs ACQUISITION CO (1) — same entity, typo in one source."),
    "P0283": ("match", "SM Managed Futures Ltd vs SM Managed Futures — same, one missing the Ltd suffix."),
    "P0284": ("match", "New Ocean Market Value Cat Fund Ltd. — identical."),
    "P0285": ("unsure", "DELTA MARITIME CO LTD vs DELTA MARITIME LTD — Co. suffix variant."),
    "P0286": ("match", "Invesco Senior Secured Bank Loan Fund Japan (JPY-Hedged) — same fund, hyphen variant in name."),
    "P0287": ("no_match", "Warburg Pincus (Bermuda) Private Equity VIII vs X — distinct vintages."),
    "P0288": ("unsure", "Commonwealth Opportunity Master Fund II Ltd Trust vs Ltd — Trust label."),
    "P0289": ("no_match", "Mapeley Beta Acquisition Co (4) vs (1) — distinct sub-vehicles in series."),
    "P0290": ("no_match", "BURREN GLOBAL ARBITRAGE II MASTER FUND vs main — distinct."),
    "P0291": ("no_match", "Windsor Properties (16) vs main — distinct sub-vehicle."),
    "P0292": ("no_match", "HANSON APPLIED SCIENCES vs HANSON APPLIED SCIENCES II — distinct."),
    "P0293": ("no_match", "Globeways Holdings II vs main — distinct."),
    "P0294": ("unsure", "Golub Capital Partners CLO 21(M) vs 21(M)-R — refinanced version."),
    "P0295": ("match", "Credit Suisse Long/Short Equity Strategy Fund Ltd. — identical (one missing trailing dot)."),
    "P0296": ("no_match", "PA Grand Opportunity IX vs main — distinct sub-vehicle."),
    "P0297": ("unsure", "S3 Global Multi-Strategy Fund Ltd vs S3 Global Multi-Strategy Master Fund Ltd — feeder/master pair."),
    "P0298": ("unsure", "Cedar Funding II CLO Trust vs Ltd — Trust label."),
    "P0299": ("no_match", "Windsor Properties (6) vs main — distinct sub-vehicle."),
    "P0300": ("no_match", "Mapeley Beta Acquisition Co (6) vs (1) — distinct sub-vehicles in series."),
}


def main() -> None:
    src = Path("data/labels/marginal_v1.csv")
    rows = list(csv.DictReader(src.open(encoding="utf-8")))

    all_labels: dict[str, tuple[str, str]] = {}
    all_labels.update(V2_MARGINAL)
    all_labels.update(PERFECT_SANITY)
    all_labels.update(V2_BORDERLINE)

    written = 0
    for r in rows:
        if r["pair_id"] in all_labels and not r["label"]:
            label, rationale = all_labels[r["pair_id"]]
            r["label"] = label
            r["rationale"] = rationale
            written += 1

    fieldnames = list(rows[0].keys())
    with src.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"applied {written} labels (expected 200)")
    from collections import Counter
    by_bucket = {}
    for r in rows:
        by_bucket.setdefault(r["bucket"], Counter())[r["label"]] += 1
    for b, c in by_bucket.items():
        print(f"  {b}: {dict(c)}")


if __name__ == "__main__":
    main()
