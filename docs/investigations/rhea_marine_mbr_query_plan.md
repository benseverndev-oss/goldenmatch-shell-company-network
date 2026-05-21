# Malta Business Registry query plan: Rhea Marine Ltd + Maistros RoRo Shipholdings Ltd

**Goal:** determine whether the two SEC 13D filers on Heidmar Maritime Holdings Corp (2025) are the same legal entities as the two Malta-registered shipholding companies surfaced in ICIJ Paradise Papers (2017 leak / ~2016 data).

If **yes** → first documented trace from a Paradise Papers Maltese shipping vehicle to a 2025 SEC SCHEDULE 13D filing, with full evidence chain.
If **no** → both are name-coincidences; the labels CSV gets two rows promoted from `uncertain` to `false_positive`; we move to the next candidate.

This document is the executable plan. Anyone with a Malta Business Registry (MBR) account can run it; expected total time ~60-90 minutes plus ~€5-15 in document fees.

## The two questions

### Q1. Rhea Marine Ltd

Is the Malta entity **RHEA MARINE LTD** (incorporated 25 May 2000, director **Plamen Dionissiev**, registered office 125 Mercury House Old Mint Street Valletta) still active, and if so, who is its current director / beneficial owner / registered office as of 2025?

### Q2. Maistros RoRo Shipholdings Ltd

Is the Malta entity **MAISTROS RORO SHIPHOLDINGS LTD** (officers in ICIJ: Aegean Shipholdings Inc, Aegean Investments S.A., Theodora Papadogianni, Spyridon Fokas, Leading Edge (Malta) Limited) still active, and what is its current officer roster and registered office as of 2025?

## Where to look

### Primary — MBR public-facing search (https://registry.mbr.mt/)

| Step | URL pattern | What it returns | Cost |
|---|---|---|---|
| 1. Free search | https://registry.mbr.mt/ROC/ (Search Company) | Company name + status (active / dissolved) + registration number | Free |
| 2. Open company profile | Click the company row | Current registered office, status, latest annual return date | Free (basic) |
| 3. Officers + history | "View officers" tab | Director list with dates of appointment + resignation. **This is the critical query.** | Free to view current; older changes may need a paid document |
| 4. Beneficial owner | "Beneficial Owner Register" — note MBR's BO register has been court-restricted since CJEU C-37/20 ruling; access varies. May need to demonstrate journalistic-investigation interest under MBR Notice 2022/MBR/06. | UBO declared at time of last filing | Restricted; check current access policy |
| 5. Documents | "View documents" — annual returns, Form K (officer change), Form B (registered office change) | PDFs of every filing since incorporation | ~€5 per document |

MBR registration is free for non-Maltese users. The portal accepts a regular email signup. You DO NOT need a Maltese ID card for basic search.

### Secondary — OpenCorporates (https://opencorporates.com/companies/mt)

Free, no signup. OpenCorporates mirrors MBR with a ~12-month lag and exposes a clean API. Useful for:
- Confirming registration number + status before paying for MBR documents
- Cross-checking officer history
- Detecting that an entity has been dissolved without a paid MBR query

URL pattern: `https://opencorporates.com/companies/mt/<registration_number>` — but registration number isn't in our ICIJ data; you'll need to search by name first.

### Tertiary — Manorial / archival snapshots

If MBR shows the entity is dissolved or has no current filings:
- **archive.org Wayback Machine** for prior MBR profile snapshots (the original directors / addresses)
- **MBR press releases** for any merger / re-domicile announcements
- **Greek shipping press** (Lloyd's List, TradeWinds) for any reporting on Rhea Marine or Maistros as Marinakis / Dionissiev / Aegean-family vehicles

## The specific queries to run

### Run order: query 1 first (cheapest, most informative)

```
1. MBR free search → "RHEA MARINE LTD"
   - Note the registration number (Maltese "C" code, e.g. "C12345")
   - Note the company status
   - Note the registered office as of last filing
   - Note the date of last filing (a stale company has not filed in >2 years)

2. MBR free search → "MAISTROS RORO SHIPHOLDINGS LTD"
   - Same fields.

3. For each, click "View officers" — record:
   - Current director(s) and date of appointment
   - Most recent resignation, if any (look for Plamen Dionissiev resignation date on Rhea, Aegean Shipholdings resignation on Maistros)

4. If officer history shows a transfer matching the 2025 SEC filing:
   - Pay for the Form K (officer change) PDF that documents the transfer
   - Note the date, the incoming director, and any reference to a beneficial owner

5. If officer history shows the same officers as ICIJ (Dionissiev / Aegean still in place):
   - Bridge is a false positive at the legal-entity level
   - The 2025 SEC filers used the same name but are different legal entities
   - Stop and re-label

6. If the Malta entity is dissolved:
   - Note the dissolution date
   - Bridge is a false positive at the legal-entity level (the 2025 SEC entity cannot be a dissolved Maltese company)
   - Stop and re-label
```

### Decision table

| Outcome | Verdict | Next step |
|---|---|---|
| Active, current director = Michalis Mastris (Rhea) OR Miltiadis Marinakis / Kokoretsi (Maistros) | **Confirmed same entity** | Pay for Form K + B PDFs; draft the lede; ship as the discovery moment |
| Active, current director still Dionissiev (Rhea) / Aegean (Maistros) | **Different legal entity** | Label both bridges `false_positive`; investigate next candidate |
| Active, current director is unrelated third party | **Ambiguous (possible nominee)** | Pull Form K for last 5 years to trace ownership chain; may need Companies House CY for Mastris's Cypriot history |
| Dissolved before 2025 | **Different legal entity** | Same as row 2 |
| No company found with that name | **MBR record may have moved** | Search MFSA financial-services-licence holders; try Greek Government Gazette (FEK) for re-domicile filings |

## What to write down (evidence template)

For each entity, the bundle should ultimately contain:

```yaml
entity: RHEA MARINE LTD
mbr_registration_number: C-?????   # filled from MBR search
mbr_status: active | dissolved | unknown
mbr_status_as_of: 2025-MM-DD
icij_data_vintage: ~2016 (Paradise Papers - Malta corporate registry)
sec_filing_date: 2025-02-26
sec_filing_accession: 0000919574-25-001673
officers_in_icij:
  - PLAMEN DIONISSIEV (Cypriot, director)
officers_in_mbr_2025:
  - <name>, appointed <date>, role <director|secretary>
registered_office_icij: 125 Mercury House Old Mint Street Valletta MT
registered_office_mbr_2025: <address>
sec_principal_2025: Michalis Mastris (Cypriot)
sec_address_2025: 89 Akti Miaouli Piraeus 18538 Greece
verdict: confirmed_same | different_entity | ambiguous
verdict_rationale: <one-sentence>
evidence:
  - <local file path to MBR Form K PDF>
  - <local file path to MBR Form B PDF>
  - <local file path to MBR profile screenshot>
  - <local file path to archived ICIJ HTML — already in cluster_47_aleph_bundle.zip>
  - <local file path to SEC EDGAR primary_doc.xml — already in bundle>
```

Place under `data/investigations/rhea_marine/` and `data/investigations/maistros_roro/`. Drop the captured Form PDFs + screenshots there as well; they become the new bundle artefacts.

## What this proves vs doesn't prove

### Confirmed-same outcome lets us publish

> "Rhea Marine Ltd, a Malta-registered shipping vehicle that surfaced in the 2017 ICIJ Paradise Papers leak with Cypriot director Plamen Dionissiev, filed a SCHEDULE 13D with the SEC in February 2025 disclosing 5%+ beneficial ownership of NASDAQ-listed Heidmar Maritime Holdings Corp. The 2025 SEC filing names Michalis Mastris (Cypriot) as principal, with a Piraeus business address. Malta Business Registry records [date] confirm that Rhea Marine Ltd remained the same legal entity throughout this period, with director succession from Dionissiev to Mastris on [date] and registered-office relocation from Valletta to Piraeus on [date]."

That's the publishable claim. It does NOT allege any wrongdoing. It does NOT say Mastris and Dionissiev are connected personally. It establishes a documented legal-entity continuity that single-source search would not surface.

### Confirmed-different outcome

Just as valuable for the methodology paper. It demonstrates:
- Phase 17a's filter catches the loudest false positives (large public co's with tickers)
- Name-coincidence at the offshore tail (Rhea Marine / Maistros) requires registry-level verification
- Phase 17b (officer overlap) is the next disambiguator we need

Both outcomes ship as bundle artefacts. Neither is a wasted run.

## Cost + time

| Item | Cost | Time |
|---|---|---|
| MBR account signup | €0 | 5 min |
| MBR free search × 2 | €0 | 15 min |
| MBR Form K + B documents (worst case 4 docs × 2 entities) | ~€40 | 10 min |
| Reading + transcribing | €0 | 30 min |
| Draft the lede + bundle artefacts | €0 | 20 min |
| **Total** | **~€40** | **~80 min** |

## If the user can't run this themselves

I can produce:
1. A scrape-friendly `scripts/probe_mbr_public_search.py` that hits the public MBR ROC endpoint with a polite UA and dumps the basic free-tier response per company name.
2. An OpenCorporates API integration (`shellnet.registries.opencorporates_mt`) that pulls the same data via JSON. Free tier is 200 requests/day; trivial for two queries.
3. A Wayback Machine probe for prior MBR snapshots if the live search is blocked.

None of these substitute for the paid Form K / B documents that conclusively prove succession, but they get us to the verdict on Q1 + Q2 without any user interaction.

## After verdict

Whichever way it lands, write the result back into `docs/labels/sec_icij_bridge_labels.csv`:

- promote `Rhea Marine Ltd <-> RHEA MARINE LTD` from `uncertain` to either `real` or `false_positive`
- add a new row for `Maistros Shipinvest Corp <-> MAISTROS RORO SHIPHOLDINGS LTD` (this match isn't in the current labels file; add it from this investigation)
- both with rationale rows pointing at the MBR document paths

That's how this single investigation tightens the calibration of every future Phase-17 filter.
