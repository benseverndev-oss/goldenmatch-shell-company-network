# Finding: an OFAC- & UK-sanctioned cyber-crime host is an active UK company with a named PSC

_Run date: 2026-05-25. Source: first execution of the survivor pipeline output against the **real** corpus (not the test fixture)._

> **Status:** the company-level sanction is an established public fact (OFAC SDN,
> 1 July 2025). The person named below is the **registered Person with Significant
> Control** per the UK PSC register — that is a public-record fact, **not** an
> allegation of personal wrongdoing. Treat as an investigative lead.

## The trail (one hop, three independent sources)

```
Marat Timurov  ──registered PSC of──▶  AEZA INTERNATIONAL LTD  ◀──sanctioned by──  OFAC SDN + UK FCDO
(KZ national, b.1999)                  UK company 15109642                          (+ Ukraine, Canada, NZ)
                                       incorporated 2023-09-01
                                       active in the register*
```

This is the "wow" the engine was built to surface: not a dense-but-nameless graph
blob, but a **recognizable, current, real-world sanctioned target** (the July 2025
OFAC/NCA "Aeza" bulletproof-hosting takedown) sitting **one hop** from an **active
UK-incorporated company** with a **named human at the Companies House helm** — and
it falls out of cross-source convergence between the **UK PSC register** and
**OpenSanctions**, two sources no single-source search joins.

## Evidence, entirely from our own corpus

**1. The company is sanctioned** — `processed/sanctions_overlay.parquet`:

| os_id | caption | topics | datasets | juris |
|---|---|---|---|---|
| `NK-arBW8i9idYNbpyfj828LxD` | **AEZA INTERNATIONAL LTD** | corp.disqual; **sanction**; debarment | **us_ofac_sdn**, **gb_fcdo_sanctions**, ua_war_sanctions, us_sam_exclusions, us_trade_csl | **gb** |

(Sister entities in the same overlay: `Aeza Group LLC`, `Aeza Logistic LLC` — the
Russian parent network.)

**2. The company is a live UK registration** — `processed/oo_uk_psc_entities.parquet`:

| bods_subject | name | incorporated | dissolved | juris |
|---|---|---|---|---|
| `GB-COH-15109642` | **AEZA INTERNATIONAL LTD** | 2023-09-01 | _null_ | GB |

Exactly one company of this name in the register; the number is unambiguous.

**3. The PSC link** — `reports/generated/investigative_grade_survivors.csv` row +
`os_sanctioned_persons` (OpenSanctions `gb_coh_psc` mirror of the UK PSC register):

- Survivor match (score 1.0, name **and** birth-year match): UK PSC `Mr Marat Timurov`
  (kz, DOB 1999-12) ⇄ OpenSanctions `gb-coh-psc-`**`15109642`**`-vc-bcdihogzslzit5zc-…`.
- The company number `15109642` embedded in that PSC id resolves (source 2) to
  AEZA INTERNATIONAL LTD. So the PSC linkage and the company identity come from two
  independent ingests that agree.

## External corroboration

On **1 July 2025** the US Treasury's OFAC, coordinated with the UK, designated
**Aeza Group** — a Russian "bulletproof hosting" provider — for enabling ransomware
and other cyber-criminal activity; the action named the UK entity **Aeza
International Ltd** among the designated parties.

- US Treasury / TRM Labs: <https://www.trmlabs.com/resources/blog/treasury-sanctions-global-bulletproof-hosting-service-aeza-group-for-enabling-cybercriminal-activity>
- Chainalysis: <https://www.chainalysis.com/blog/ofac-sanctions-aeza-group-bulletproof-hosting-crypto-payments-july-2025>
- Elliptic: <https://www.elliptic.co/blog/ofac-sanctions-four-russian-affiliated-bulletproof-hosting-bph-entities>

## Confidence & caveats (read before repeating this)

- **Identity (company): high.** Name + GB jurisdiction + single register match +
  the documented OFAC action all converge on company `15109642`.
- **\*"Active" is as-of the PSC snapshot (2025-03-11), which predates the July 2025
  sanctions.** The company was live in the register then; its **current** status
  (it may since be in liquidation / struck off) must be checked on Companies House
  before publication.
- **The PSC is not personally on an SDN list** in our data — `Mr Marat Timurov`
  appears only via the PSC-register mirror. A 1999-born Kazakhstan national listed
  as PSC of a Russian-controlled sanctioned host is *consistent with* a nominee/
  front pattern, but that is a hypothesis to verify, not a claim.
- This is the UK PSC register ∩ OpenSanctions — **not** an ICIJ leak. It is novel
  precisely because it isn't in the picked-over Panama/Pandora corpus.

## Secondary cohort: sanctioned individuals with UK PSC declarations

The same survivor file carries a cluster of **identity-grade (name + DOB-year)**
matches between the UK PSC register and OpenSanctions-listed individuals. These are
the inverse pattern (sanctioned *person* → UK company). Companies were **not**
resolved here — the BODS person→company relationship layer isn't in the current
processed artifacts (it lives in the raw `uk_bods.zip`), so this is the documented
next step.

| Person | Sanctions regime (OS datasets) | Public identity |
|---|---|---|
| **Igor Zyuzin** | EU asset-freeze `eu_fsf` + EU travel ban + Swiss SECO | Mechel chairman |
| **Oksana Marchenko** | **UK `gb_fcdo_sanctions`** + Ukraine | wife of Viktor Medvedchuk |
| **Roman Trotsenko** | Australia / Belgium / Canada | AEON Corp billionaire |
| **Nikita Mordashov** | Canada / Japan / Ukraine | Severstal heir |
| **Arkady Volozh** | Ukraine (NSDC / war) | Yandex co-founder |
| **Igor Yusufov** (ICIJ-side) | Canada / Ukraine | ex-Russian energy minister |

(Register-mirror self-matches — Giner / Isaykin / Viktorov — were excluded: they
match the PSC register *copied into* OpenSanctions, not a sanctions list.)

## Reproduce

```bash
# from the Railway job volume (auth: Authorization: Bearer $SHELLNET_JOB_TOKEN)
GET /download?path=reports/generated/investigative_grade_survivors.csv
GET /download?path=processed/sanctions_overlay.parquet
GET /download?path=processed/oo_uk_psc_entities.parquet
GET /download?path=processed/os_sanctioned_persons.parquet
```

1. In `sanctions_overlay`, filter `caption ~ "aeza"` → AEZA INTERNATIONAL LTD,
   `topics` contains `sanction`, datasets include `us_ofac_sdn` + `gb_fcdo_sanctions`.
2. In `survivors.csv`, find `Mr Marat Timurov` → OS id embeds company `15109642`.
3. In `oo_uk_psc_entities`, `bods_subject == "GB-COH-15109642"` → AEZA INTERNATIONAL
   LTD, `dissolution_date` null (as of snapshot).

## Honest bottom line

A recognizable name at the end of the trail: **yes.** The headline lead — an
OFAC/UK-sanctioned bulletproof-hosting front that is a live UK company with a named
PSC — is concrete, current, and cross-source-verified from the corpus. The
oligarch-PSC cohort is a strong secondary seam but is one resolution step short
(needs the BODS relationship layer to name each company). The next compounding move
is to ingest the UK BODS person→company relationships so every sanctioned-PSC match
resolves to a named, status-checked company automatically.
