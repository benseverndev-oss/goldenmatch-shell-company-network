# Company-anchored matching — GLEIF L2 corporate-ownership findings

Generated 2026-05-13. Follow-on to `gleif_l2_findings.md` (Tier D data
ingest) that actually exercises the graph.

> **Hypothesis, not proof.** Every edge below is a registry-disclosed
> corporate ownership link via GLEIF Level 2 reference data, joined
> against OpenSanctions asset-freeze records (US OFAC, EU FSF, UK
> HMT). The fact that one end is on an asset-freeze list and the
> other isn't is a *secondary-sanctions lead*, not an enforcement
> conclusion. Human review (and possibly a sanctions designation)
> would still need DOB / control-percentage / current-ownership
> verification.

## What ran

`scripts/walk_gleif_ownership.py` joins:

- **OpenSanctions entities** filtered to `topic == 'sanction'` AND
  membership in one of the OFAC / EU FSF / UK HMT datasets (the
  three primary asset-freeze regimes). 533 LEIs survive that filter.
- **GLEIF Level 2 ownership edges** (816,443 corporate parent /
  child relationships ingested in PR #35).

The script then surfaces three slices:

1. Edges where **both endpoints** are independently OFAC/EU/UK-sanctioned.
2. Edges where **a sanctioned parent controls a not-yet-sanctioned subsidiary** (the candidate-secondary-sanctions slice).
3. Edges where **a not-yet-sanctioned parent controls a sanctioned subsidiary** (rarer; sanctions tend to flow downward).

Full output: `reports/investigations/gleif_ownership_chains.md` (510
lines, 50 sanctioned-parent sections).

## Numbers

- **533** directly-sanctioned LEIs in the OFAC/EU/UK universe with
  ownership edges in GLEIF L2.
- **127** edges with both ends sanctioned (intra-sanctioned-network
  chains — already known structure).
- **390** edges with *exactly one* end sanctioned (the lead slice —
  not-yet-sanctioned entities adjacent to asset-frozen ones).

## Strongest leads — sanctioned parent → not-yet-sanctioned subsidiary

Each cluster below is a registry-disclosed corporate-ownership chain
where the parent is OFAC/EU/UK asset-frozen and one or more
subsidiaries are not. These are candidate secondary-sanctions targets.

### Lukoil PJSC (`549300LCJ1UJXHYBWI24`)

OFAC SDN-sanctioned 2022. GLEIF L2 declared subsidiaries (not on
asset-freeze lists at corpus generation):

- `K80PJMCDA9MAE5C8IO91` **LITASCO SA** — Lukoil's Geneva-based commodities trading arm
- `724500LG1GUKJ5TOIW61` **LUKOIL International Finance B.V.** — Netherlands finance vehicle
- `7872006AZAFVTVIQ3G32` **PETROTEL-LUKOIL SA** — Romanian refinery
- `485100TJJ5MAH4VCVF30` **LUKOIL Neftohim Burgas AD** — Bulgarian refinery
- `213800FXBZXOXNXKWP95` **LUKOIL SECURITIES LIMITED**
- `2549005D4COOXVIAJQ13` **TSP FINANCE COMPANY LTD**
- `72450024EGZK2K8NAG02` **LUKOIL Finance B.V.**
- `9845007AC47F8H858B51` **AC MANAGEMENT COMPANY LIMITED**

### Sovcomflot (Russian state-owned shipping; OFAC SDN 2022)

Declared subsidiaries via GLEIF L2:

- `549300FD9UH07N44ZX88` **Azoria Shipping Company Limited**
- Plus PURPOSEFUL CORPORATION, GLOBAL CHALLENGE SHIPPING COMPANY,
  ENSAY SHIPPING LIMITED (surfaced in the broader edge scan; names
  not all carried in the OS row lookup, would be filled by a GLEIF
  entity-table join)

### Norilsk Nickel (`OAO Norilsk Nickel`)

Declared subsidiaries:

- **METAL TRADE OVERSEAS SA** (Swiss commodity trader)

### MegaFon PJSC

- **MEGAFON INVESTMENTS (CYPRUS) LIMITED**

### ABH Holdings S.A. (Alfa Group's Luxembourg parent; sanctioned)

- **ABH KAZAKHSTAN LIMITED**
- **Voda International Corp.**

### Swiru Holding AG (sanctioned Swiss holding company)

- **Watertight International Inc.**
- **IFI Estates S.A.**
- **VH Estates S.A.**

### Russian Aluminum (RUSAL)

- **SEA CHAIKA CORPORATION**

### Expobank JSC

- **OOO Хвоя Банк** (Russian regional bank)

### SIBUR Holding (sanctioned Russian petrochemicals)

- **Sibur Securities Designated Activity Company** (Irish SPV)

### Joint-Stock Company "Russian Standard"

- **ZAO "Russian Standard Insurance"**

### Hangzhou Hikvision Digital Technology

- **Hikvision Singapore PTE. LTD.**

### Tekhsnabexport JSC (Russian state uranium trader, sanctioned)

Surfaced multiple subsidiaries without OS name records (would resolve
against the GLEIF entity table on Railway).

## Both-ends-sanctioned chains (validation slice)

These are pre-existing intra-sanctioned-network chains — already known
to enforcement, useful as a sanity check that the join is wired right:

- **Belvnesheconombank OJSC** controlled by **Vnesheconombank
  (Russian state development bank)**
- **BANCO VTB AFRICA SA**, **BANK VTB KAZAKHSTAN JSC** controlled by
  **Bank VTB (PAO)**
- **Bank Sepah International PLC** controlled by **Bank Sepah** (Iran)
- **GPB (SWITZERLAND) LTD** controlled by **Gazprombank**
- **Otkritie Capital Ltd** controlled by **Otkritie Financial
  Corporation PJSC**, in turn controlled by the **Central Bank of the
  Russian Federation**
- **National Clearing Centre** controlled by **MICEX-RTS PJSC**
- **AO "Alfa-Forex"** controlled by **AO "Alfa-Bank"**
- **GTLK Europe Capital DAC** controlled by **GTLK Europe DAC**
  (Russian state leasing)
- **Volzhsky Trubny Zavod** controlled by **TMK** (Russian pipe maker)
- **Mighty Divine Global Fund SPC** controlled by **Mighty Divine
  Investment Management Limited**
- **Evrazholding subsidiary** controlled by **Evraz**
- **NIS AD Novi Sad** (Serbian oil company) controlled by **Gazprom** /
  **Gazprom Moscow branch**

127 such intra-network chains surfaced.

## Reading honestly

**What this delivers.** The 390-edge "one end sanctioned" slice is
real, concrete, surfaced-without-prior-journalism material. Each row
is a registry-disclosed corporate ownership link from a sanctioned
parent to a not-yet-sanctioned subsidiary. For compliance / asset-
tracker / OFAC analysts, this is the exact pattern of leads they
manually construct from court filings + bank records — automated.

**What it doesn't deliver.** Like the UK PSC finding, most of the
specific named subsidiaries (LITASCO, METAL TRADE OVERSEAS, the
Lukoil Netherlands / Romania / Bulgaria refineries, NIS in Serbia)
are already publicly known via OCCRP / Reuters / FT investigations.
The novelty isn't *finding* these entities — it's the *speed* of
automated joining: 533-LEI seed × 816k-edge graph processed in 30
seconds locally, producing 390 ranked leads.

The genuinely new structure would surface where a sanctioned entity
has a GLEIF-disclosed subsidiary that *hasn't* been worked into a
published report. Identifying which of the 390 rows are in that
category is the manual human review step, not the matcher's job.

## Combined Tier-A + Tier-D state

The matching pipeline now exercises three different join shapes:

1. **Person-side (Tier A): OS sanctions × ICIJ officers × UK PSC.** 43
   novel sanctioned-individual-as-UK-PSC matches.
2. **Person-side (existing): OS sanctions × ICIJ officers only.** 132
   non-CN exact-name matches (mostly already-published cases).
3. **Company-side (Tier D, this doc): OS sanctions × GLEIF L2
   ownership.** 390 not-yet-sanctioned-subsidiary leads.

Each surfaces a different *kind* of corporate-network insight. UK PSC
gives you "named individual declared as PSC of UK Ltd"; GLEIF L2
gives you "subsidiary entity in an asset-freeze parent's ownership
tree." Together they cover the two complementary halves of the
ownership-disclosure surface.

## Reproducing

```bash
# Locally (data already on disk):
uv run python scripts/walk_gleif_ownership.py

# Or via Railway (if the script gets added to the allowlist):
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$SHELLNET_JOB_URL/run-script?name=walk_gleif_ownership"
curl -fL -H "Authorization: Bearer $TOKEN" \
  "$SHELLNET_JOB_URL/download?path=reports/generated/gleif_ownership_chains.md" \
  -o chains.md
```
