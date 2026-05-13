# GLEIF L2 walk — verification round and filter recalibration

Generated 2026-05-13. Follow-on to `gleif_ownership_findings.md`.

## Why this exists

The previous walk's 10 highlighted "candidate secondary-sanctions
leads" turned out to include at least three entities (Azoria Shipping
Company, PURPOSEFUL CORPORATION, GLOBAL CHALLENGE SHIPPING) that are
*already directly sanctioned* — under OS datasets I didn't include in
the filter. The methodology was right; the dataset filter was wrong.

This doc records the recalibration and what survived.

## Filter expansion

Original filter (too narrow): `us_ofac,eu_fsf,gb_hmt`. Caught only
`us_ofac_sdn` (17 k OS rows) and `eu_fsf` (5.9 k). Missed everything
under `us_sam_exclusions` (16 k — Azoria et al.), `gb_fcdo_sanctions`
(5.6 k — actual UK source, not the legacy `gb_hmt` name),
`ch_seco_sanctions`, `ua_nsdc_sanctions`, `ua_war_sanctions`, etc.

Expanded filter — 20 dataset substrings covering every internationally-
recognised sanctions / asset-freeze regime in OS:

```
us_ofac, us_sam_exclusions, us_trade_csl,
eu_fsf, eu_travel_bans, eu_journal_sanctions,
gb_fcdo_sanctions, ch_seco_sanctions,
ua_nsdc_sanctions, ua_war_sanctions,
ca_dfatd_sema_sanctions, au_dfat_sanctions, jp_mof_sanctions,
fr_tresor_gels_avoir, be_fod_sanctions, mc_fund_freezes,
nz_russia_sanctions, tw_shtc, iq_aml_list, kg_fiu_national
```

## Result deltas

| | Original | Wider filter |
| --- | ---: | ---: |
| Directly-sanctioned LEIs in seed | 533 | **702** (+169) |
| Both-ends-sanctioned chains (validation) | 127 | **202** (+75) |
| Exactly-one-end-sanctioned (candidate-novel) | 390 | **470** |

The +75 reclassified-as-both-sanctioned includes Azoria Shipping ↔
Sovcomflot — the matcher's join was always right; it was just the
*classification* that was wrong.

The candidate-novel count went up (390 → 470) because expanding the
seed set widens the cone of edges with at least one sanctioned end.
The actually-novel-looking subset is much narrower (see below).

## Re-verified candidate-novel categories (after wider filter)

The remaining 470-edge slice splits roughly into:

### Well-documented secondary subsidiaries (most of the volume)

- **Lukoil European chain** — LITASCO SA (Geneva), LUKOIL
  International Finance B.V. (NL), PETROTEL-LUKOIL SA (Romania),
  LUKOIL Neftohim Burgas AD (Bulgaria). Under active US-OFAC
  wind-down per October 2025 designation; Swissinfo / Balkan Insight
  / ECFR / Reuters covered each.
- **CNOOC finance + marketing vehicles** — CNOOC Finance (2013),
  (2014) ULC, Petroleum North America, UK Marketing, Marketing
  Canada. Documented in CNOOC's own annual reports + multiple
  law-firm CCMC sanctions advisories.
- **MegaFon Investments (Cyprus)** — In MegaFon's own annual reports.
- **Sibur Securities DAC (Ireland)** — Eurobond SPV; rated by Fitch;
  on IRS FFI list.
- **NORILSK NICKEL → METAL TRADE OVERSEAS SA (CH)** — Global Witness
  + Nornickel annual reports + OECD critical-raw-materials report.

### Already-sanctioned (validation chains, reclassified correctly)

- Sovcomflot → Azoria Shipping (now properly in both-sanctioned table)
- VTB → Banco VTB Africa, Bank VTB Kazakhstan
- Vnesheconombank → Belvnesheconombank (Belarus)
- Gazprombank → GPB Switzerland
- Polyus PJSC → Polyus Service LLC
- Otkritie Capital ↔ Otkritie Financial Corp ↔ Central Bank of Russia
- Several MICEX, Alfa-Bank, Alfa-Forex chains

### Probable GLEIF data-quality issue

**PJSC Motovilikhinskiye Zavody → Sistema subsidiaries.** The walk
surfaces Dega Retail, Sistema Asia Fund, Steppe Trading SA, etc. as
subsidiaries of Motovilikhinskiye — but Motovilikhinskiye is a Rostec-
managed weapons manufacturer; Sistema is a separate Moscow-listed
conglomerate. These shouldn't be in the same ownership tree. Two
likely explanations:

1. Stale GLEIF L2 records — Motovilikhinskiye was historically owned
   by Sistema via JSFC Sistema, divested years ago; the L2 record
   may not reflect the divestiture.
2. Match collision on a shared parent LEI.

Worth pulling the underlying GLEIF L2 RR file for the specific
relationship records to confirm. Flagged as a known caveat.

### Genuinely under-reported (the actually-novel residual)

**ABH Holdings S.A. (Luxembourg parent of Alfa Bank Russia) upstream
holding chain.** The matcher surfaces, as siblings under ABH Holdings:

- `549300SY4W3W7L5WZE53` **SIFUM GROUP LIMITED** (Cyprus)
- `549300QUS7ZQXD8GVG76` **Countryisle Assets Limited** (Cyprus)
- `549300RFJCRPC8219D49` **RINGBELL LIMITED** (Cyprus)
- `213800JV1ZCAGAL5BK67` **GREATFORD LIMITED** (Cyprus)
- `549300BJKVXI3YIYYW60` **ABHU FINANCE PLC**

These appear in OS's adjacency record for ABH Holdings (no separate
asset-freeze designation), are documented in Cyprus Companies House,
LEI Lookup, and Kazakh-exchange Alfa Bank financial filings — but
have minimal Anglophone press coverage.

They are the *named registered owners* in ABH Holdings's PSC chain.
Each represents one step removed from Alfa Bank (sanctioned),
specifically in the Cyprus-Luxembourg holding-company structure that
Russian banking groups have used to interpose between Russian
operating banks and Western financial systems.

This is the closest thing to "uncovered structure" in the GLEIF L2
walk output. Verifying who actually controls these Cyprus entities
— and whether the disclosed addresses overlap with other
sanctions-relevant structures — is a follow-up investigative
question.

### Modest-coverage but documented

- **DRIADUS INVESTMENTS LIMITED** — Cyprus-incorporated; re-registered
  as "West Asia LLC" in Russia 2015. Documented as a Gazprom
  subsidiary in OS, MarketScreener, North Data. Modest press.
- **Various Lukoil Russian-domiciled subsidiaries** (ЛУКОЙЛ-Резерв-
  нефтепродукт-Трейдинг, Lukoil International GmbH, AC Management
  Company Limited) — Russian-language coverage exists; English-
  language coverage is thin.

## Methodological takeaways for future runs

1. **Trust OS's `sanction` topic, but expand the dataset filter
   broadly.** OS's topic taxonomy is accurate (`sanction` =
   asset-freeze, `sanction.linked` = adjacent, `reg.action` =
   regulatory enforcement, `crime` = AML/criminal), but its dataset
   names are an enormous list that grows monthly. Substring filter
   against the ~25 known internationally-recognised sanctions sources
   is the right shape.

2. **Verify both endpoints before publication.** The matcher's
   classification is only as good as the source-list completeness on
   *both* sides. An entity in the candidate-novel slice may already
   be sanctioned via a list OS hasn't aggregated yet, or via an
   OS dataset the local filter missed.

3. **GLEIF L2 has staleness.** Some L2 relationships reflect
   historical ownership that has since changed. The Motovilikhinskiye
   ↔ Sistema artifact is a concrete instance. Cross-checking against
   recent corporate filings is necessary before treating any single
   L2 edge as currently-valid.

## What this re-classification didn't change

The structural conclusion holds:

- The matcher mechanically joins OS sanctions against GLEIF L2's
  816 k ownership edges correctly.
- The combined pipeline now exercises three different join shapes
  (OS × ICIJ persons, OS × UK PSC persons, OS × GLEIF L2 entities).
- For any given investigative question, the script is now a
  10-second one-liner instead of a manual document-mining
  exercise.

What the re-classification *did* change is the honest framing of the
candidate-novel set: the actually-under-reported residual is smaller
than the original 390-edge number suggested, with the **ABH Holdings
Cypriot upstream owners** as the strongest single under-reported
cluster.
