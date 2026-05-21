# HM Land Registry OCOD — Overseas Companies Ownership Data

OCOD lists every UK property (England + Wales) owned by an
overseas-incorporated company. Quarterly release, ~80 MB CSV,
~50k-100k titles. Free but gated behind a one-time email signup +
licence acceptance.

## What it gives the pipeline

The disambiguator we were missing for the natural-person / offshore-
shell-company bridges. OCOD's `country_incorporated` field lets us
jurisdiction-gate ICIJ name matches; OCOD's `property_address` +
`postcode` let us cross-check UK-disqualified-director address
overlaps.

Concrete example: ICIJ Paradise Papers has a Maltese company
"Apeiron Investment Group Ltd". OCOD will tell us whether that
specific Maltese company owns any UK property — and if yes, at what
address.

## Manual download (one-time, ~5 minutes)

1. Visit `https://use-land-property-data.service.gov.uk/datasets/ocod`.
2. Sign in (free GOV.UK account; no card).
3. Accept the dataset licence (Open Government Licence v3.0 with
   attribution conditions).
4. Download the latest **OCOD_FULL_YYYY_MM.csv** file.

5. Upload to Railway under `/data/raw/hmlr/OCOD_FULL.csv` either:
   - via the existing `/upload-zip` endpoint (zip it first), OR
   - via `railway run --service shellnet-job` + manual `cp` from a
     pre-uploaded artifact, OR
   - via your preferred SCP / SFTP method.

The same applies for CCOD (UK companies that own UK property) if
needed — same gov.uk service, separate dataset.

## Ingest

After the CSV is on Railway:

```bash
# Allowlist entry: ingest_hmlr_ocod
# Dispatch via /run-script?name=ingest_hmlr_ocod
# Reads /data/raw/hmlr/OCOD_FULL.csv, writes /data/processed/hmlr_ocod.parquet
```

Output schema is one row per (title, proprietor) — OCOD's source
CSV has up to 4 co-proprietors per title; we unpivot for downstream
join simplicity. See `src/shellnet/sources/hmlr_ocod.py` for the
exact column projection.

## Cross-reference probe

`scripts/probe_hmlr_ocod_crossref.py` (allowlist:
`probe_hmlr_ocod_crossref`) does three things in one run:

1. **OCOD × ICIJ** — match overseas-property owners by normalised
   name (3+ tokens, 12+ chars defamation guard).
2. **OCOD × UK disqualified** — match property addresses or
   proprietor names against the 222-row disqualified-directors
   register.
3. **OCOD focused Sajid Bashir** — surface any title held under
   that name OR any property at Huddersfield / Stoke Poges
   postcodes from the existing identity-verification question.

Outputs `ocod_icij_overlap.json`, `ocod_disqualified_overlap.json`,
`ocod_sajid_bashir.json` under `/data/processed/probes/`.

## Licence + attribution

OCOD is licensed under the **Open Government Licence v3.0** with an
explicit HM Land Registry attribution requirement. Any derived
publication (Aleph bundles, blog posts, video) must credit:

> Contains HM Land Registry data © Crown copyright and database
> right [year]. This data is licensed under the Open Government
> Licence v3.0.

The bundle generator should fold this into the per-cluster
`README.md` once OCOD data is folded in.

## What this does NOT do

- Does not give us beneficial owners — OCOD names the *registered
  proprietor* (the company that holds title), not the natural
  person behind it. To bridge to beneficial owners you still need
  Companies House PSC (which we have) or the new Register of
  Overseas Entities (separate dataset, partially gated).
- Does not cover Scotland or Northern Ireland — those have their
  own land registries (Registers of Scotland; Land Registry of
  Northern Ireland) with separate ownership datasets.
- Quarterly snapshot, not real-time — transactions in the current
  quarter aren't visible until the next release.
