# Finding: the UK corporate footprint of sanctioned parties (UK PSC ∩ OpenSanctions)

_Run date: 2026-05-25. First execution of the survivor-pipeline output against the **real** corpus, plus a BODS relationship-layer resolution and live Companies House status checks._

> **Status / framing.** Company-level sanctions and PSC declarations below are
> public-record facts. Individuals named as PSCs are the **registered** controllers —
> that is a public fact, **not** an allegation of personal wrongdoing. Treat as
> investigative leads.

## Honest bottom line (read first)

Cross-source convergence between the **UK PSC register** and **OpenSanctions** —
two sources no single-source search joins — surfaces a coherent, **named** set of
sanctioned parties with UK corporate vehicles: an OFAC/UK-sanctioned cyber-crime
host and five Russian oligarchs. **A recognizable name at the end of the trail:
yes.** An *active, operating* company at the other end: **no** — every resolved
company is now **dissolved or in liquidation**, consistent with post-sanctions
wind-down of UK entities. The value here is a verified, named, cross-source
**corporate-footprint map** of sanctioned parties, not a live operating company.

(An earlier draft of this note called Aeza "active"; that was true only of the
March-2025 PSC snapshot. Live Companies House checks on 2026-05-25 show it
dissolved. Corrected below.)

## 1. The Aeza cyber-crime host

**AEZA INTERNATIONAL LTD** — UK company `GB-COH-15109642`, incorporated 2023-09-01,
**now Dissolved** (Companies House, checked 2026-05-25; was live in the 2025-03 PSC
snapshot, i.e. before sanctions).

- **Sanctioned (company itself):** OpenSanctions `sanctions_overlay` row
  `NK-arBW8i9idYNbpyfj828LxD`, jurisdiction `gb`, topics `corp.disqual; sanction;
  debarment`, datasets **`us_ofac_sdn`, `gb_fcdo_sanctions`**, `ua_war_sanctions`,
  `us_sam_exclusions`, `us_trade_csl`. Sister entities in the overlay: `Aeza Group
  LLC`, `Aeza Logistic LLC`.
- **Registered PSC:** `Mr Marat Timurov` (KZ national, b. 1999) — survivor match
  (name + birth-year, score 1.0) to OpenSanctions' PSC-register mirror
  `gb-coh-psc-`**`15109642`**`-…`, whose embedded company number resolves to AEZA
  INTERNATIONAL LTD. (Timurov is **not** personally on an SDN list in our data.)
- **External corroboration:** OFAC, coordinated with the UK, designated **Aeza
  Group** (Russian "bulletproof hosting", enabling ransomware/cybercrime) on
  **1 July 2025**, naming the UK entity Aeza International Ltd.
  - <https://www.trmlabs.com/resources/blog/treasury-sanctions-global-bulletproof-hosting-service-aeza-group-for-enabling-cybercriminal-activity>
  - <https://www.chainalysis.com/blog/ofac-sanctions-aeza-group-bulletproof-hosting-crypto-payments-july-2025>

## 2. Sanctioned-oligarch UK corporate footprint

Identity-grade (name + DOB-year, score 1.0) matches between the UK PSC register
and OpenSanctions-listed individuals. Each person's UK company was resolved from
the **BODS relationship layer** (see method) and its **current** status checked
live on Companies House (2026-05-25).

| Sanctioned individual | Sanctions regime (OS datasets) | UK company (number) | Current CH status |
|---|---|---|---|
| **Igor Zyuzin** — Mechel chairman | EU asset-freeze `eu_fsf` + EU travel ban + Swiss SECO | **ORIEL RESOURCES LIMITED** (04818143), held via **Mechel PAO** | **In liquidation** |
| **Arkady Volozh** — Yandex co-founder | Ukraine `ua_nsdc` / `ua_war` | **DELI INTERNATIONAL LIMITED** (13371836), held via **Yandex N.V.** | Dissolved |
| **Roman Trotsenko** — AEON Corp | Australia / Belgium / Canada | **SIBERIAN GOLDFIELDS LIMITED** (10695797) | Dissolved |
| **Nikita Mordashov** — Severstal heir | Canada / Japan / Ukraine | **NORD GOLD PLC** (13287342) | Dissolved |
| **Oksana Marchenko** — wife of V. Medvedchuk | **UK `gb_fcdo_sanctions`** + Ukraine | **INTERMAY MANAGEMENT LTD** (04445610) | Dissolved |

The corporate chains are coherent: Mechel acquired Oriel Resources (2008); Nord
Gold is the Mordashov family's gold-mining business; Deli International is held by
Yandex N.V. Register-mirror self-matches (Giner / Isaykin / Viktorov) were excluded
— they match the PSC register *copied into* OpenSanctions, not a sanctions list.

## Method (reproducible)

All inputs pulled from the Railway `/data` volume (`Authorization: Bearer
$SHELLNET_JOB_TOKEN`); analysis run locally on the downloaded parquets.

1. **Leads:** `reports/generated/investigative_grade_survivors.csv` — score-1.0
   matches with name + birth-year agreement.
2. **Sanctions topic + company sanction:** `processed/sanctions_overlay.parquet`
   (filter `caption ~ "aeza"`, inspect `topics`/`datasets`).
3. **Person → company (oligarchs):** the survivor `uk_psc:<uuid>` is the BODS
   **person `statementId`**. In `raw/openownership/uk_bods.zip` →
   `person_statement.parquet`, filter `statementId ∈ {uuids}`; the
   `declarationSubject` column is `GB-COH-<companynumber>`. `entity_statement.parquet`
   gives the company name and any corporate parent (e.g. Mechel PAO, Yandex N.V.).
4. **Names + live status:** Companies House
   `find-and-update.company-information.service.gov.uk/company/<number>`.

## Next steps

- **Enumerate full footprints.** Each person above was resolved from the single PSC
  statement that matched; joining `person_recorddetails_names` (surname + birth-year)
  → all `person_statement`s would list *every* UK company each controlled.
- **Persist the BODS relationship layer.** The `ingest_uk_bods` step drops
  person→company edges; emitting `uk_psc_relationships.parquet` (subject /
  interestedParty / company number) would make every future sanctioned-PSC match
  resolve to a named, status-checked company automatically — without re-parsing the
  3.5 GB zip.
- **Lead, not verdict.** Dissolved/liquidated status means these are historical
  footprints; any external use needs primary-source confirmation of dates and roles.
