# Data sources

Detailed notes on each source: where it comes from, how to obtain it, what
fields the adapter expects, and what to be careful about. Public-source data
is incomplete and noisy by design; treat anything it says as a starting hypothesis.

---

## 1. ICIJ Offshore Leaks Database

- **Home:** https://offshoreleaks.icij.org/
- **Bulk download:** https://offshoreleaks.icij.org/pages/database
- **Licence:** ICIJ permits non-commercial use of the database for journalism
  and research. Re-publication of bulk data requires permission. Read the
  ICIJ terms before redistributing anything derived.
- **Access method:** Manual download. The site distributes a ZIP that contains
  several CSVs (entities, officers, intermediaries, addresses, relationships).
  Filenames have varied across releases (Panama Papers, Pandora Papers,
  Paradise Papers, etc.). The adapter discovers files fuzzily by keyword
  in the stem.

### Drop location

```
data/raw/icij/
  *entit*.csv          → loaded as entities
  *officer*.csv        → loaded as officers (TODO: parser)
  *intermediar*.csv    → loaded as intermediaries (TODO: parser)
  *address*.csv        → loaded as addresses
  *relationship*.csv   → loaded as edges
```

### Fields the adapter reads

Entities CSV:
`node_id, name, jurisdiction, jurisdiction_description, country_codes,
incorporation_date, inactivation_date, struck_off_date, status, company_type,
address, sourceID`

Addresses CSV:
`node_id, address, country_codes, countries, sourceID`

Relationships CSV:
`node_id_start, node_id_end, rel_type, link, start_date, end_date, sourceID`

Missing columns become null — the adapter tolerates schema drift.

### Caveats

- ICIJ entities are sometimes recorded with the *same* shell company under
  multiple leaks; cross-leak deduplication is part of what GoldenMatch is
  meant to address.
- "British Virgin Islands" and similar appear in multiple textual forms;
  `normalize_jurisdiction` maps the common ones.
- Officer / intermediary parsing is on the roadmap; only entities, addresses,
  and edges are emitted today.

---

## 2. OpenCorporates

- **Home:** https://opencorporates.com/
- **API:** https://api.opencorporates.com/
- **Licence:** OpenCorporates' Terms of Use govern API and bulk usage. The
  underlying registry data carries jurisdiction-specific licences. Bulk
  redistribution requires a commercial agreement.
- **Access method:** REST API. The adapter uses the public `v0.4` endpoints
  via `httpx`. With `OPENCORPORATES_API_KEY` set you get higher rate limits
  and more fields per record. **Do not scrape the website.**

### Fields the adapter reads

For each company record:
`name, company_number, jurisdiction_code, incorporation_date, dissolution_date,
company_type, current_status, registered_address_in_full, opencorporates_url`

### Caching

Every paginated response is cached verbatim under
`data/raw/opencorporates/cache/<endpoint>__<params-hash>.json`. Re-runs are
free; you can ship the cache for reproducibility (not the parsed parquet,
which is recomputable).

### Caveats

- Rate limits on the unauthenticated tier are tight. The adapter sleeps
  between pages by default.
- A "search" hit is not necessarily a match — names are common.
- Coverage varies massively by jurisdiction. UK/US registries are deep;
  some offshore jurisdictions are thin or absent.

---

## 3. GLEIF Golden Copy

- **Home:** https://www.gleif.org/en/lei-data
- **Bulk download:** https://www.gleif.org/en/lei-data/gleif-golden-copy
- **Licence:** GLEIF data is released under CC0 (public domain). Attribution
  is appreciated.
- **Access method:** Manual download. The full file is large (~2GB
  compressed) and updated daily. The adapter does **not** auto-download.

### Fields the adapter reads

Per record (v1 API shape, also tolerates a flat top-level shape):

- `attributes.lei`
- `attributes.entity.legalName.name`
- `attributes.entity.jurisdiction`
- `attributes.entity.legalForm.id`
- `attributes.entity.legalAddress.{addressLines,city,region,postalCode,country}`
- `attributes.entity.headquartersAddress.*`
- `attributes.registration.status`
- `relationships.direct-parent.data.id` (or `ultimate-parent`)

### Supported file shapes

| Suffix | Status |
| --- | --- |
| `.json` | Supported (single record, list, or `{"data": [...]}`) |
| `.jsonl` / `.ndjson` | Supported (one record per line) |
| `.xml` / `.xml.zip` | **Not yet implemented** — convert first |

### Caveats

- Entities can have multiple parent relationships (direct vs. ultimate); we
  prefer `direct-parent`, falling back to `ultimate-parent`.
- Jurisdictions are typically already ISO-3166-1; we still re-normalise to
  lowercase for consistency.

---

## 4. OpenSanctions

- **Home:** https://www.opensanctions.org/
- **Datasets:** https://www.opensanctions.org/datasets/
- **Licence:** Per-dataset; many are CC-BY 4.0. Read the dataset page.
- **Access method:** Manual export download (FtM JSON / NDJSON preferred).
  Optional automatic download via `OPENSANCTIONS_DATASET_URL` if you've
  pinned a stable URL.

### Fields the adapter reads

From each FollowTheMoney entity:

- `id`, `schema`, `caption`, `datasets`
- `properties.name`, `properties.alias`
- `properties.jurisdiction`, `properties.country`
- `properties.address`
- `properties.registrationNumber`, `properties.leiCode`,
  `properties.ogrnCode`, `properties.innCode`, `properties.okpoCode`,
  `properties.swiftBic`, `properties.taxNumber`
- `properties.topics`
- `first_seen`, `last_seen`

Only entities with schema `Company` / `Organization` / `LegalEntity` flow
into the unified company table; persons go to a separate sink (TODO).

### Caveats

- OpenSanctions is **enrichment**, not ground truth. A topic of `sanction`
  or `pep` is a strong signal but the underlying source may be wrong or
  out of date — always check the linked source.

---

## 5. Sanctions multi-list overlay

- **Source repo:** https://github.com/benseverndev-oss/goldenmatch-sanctions-reconciliation
- **What it adds:** a per-entity rollup of which government sanctions
  lists each OS entity appears on. Captures the typical evasion pattern
  where an entity is on EU/UK lists but not OFAC SDN — `n_datasets == 1`
  with `us_ofac_sdn` absent is a high-value investigative signal.
- **Mode 1 (local):** recompute the overlay from our existing
  `interim/opensanctions_entities.parquet`. No external download.
- **Mode 2 (external):** drop a `records.parquet` from the source repo
  into `data/raw/sanctions_reconciliation/` and pass `--external` to
  prefer its aggregation (which uses upstream OS entity resolution).

### Run

```bash
uv run python scripts/build_sanctions_overlay.py
# or, with the external curated parquet:
uv run python scripts/build_sanctions_overlay.py \
    --external data/raw/sanctions_reconciliation/records.parquet
```

Railway: `POST /run-script?name=sanctions_overlay` (or
`sanctions_overlay_external`).

### Output

`processed/sanctions_overlay.parquet` with columns
`os_id, schema, caption, names, n_names, datasets, n_datasets, topics, jurisdictions`.
Join to the rest of the pipeline via `os_id == source_id`.

### Caveats

- Curated to ~17 government asset-freeze dataset prefixes (see
  `SANCTION_DATASET_PREFIXES` in `src/shellnet/sources/sanctions_overlay.py`).
  PEP / `sanction.linked` / `reg.action` / `crime` topics are deliberately
  excluded — they are not asset-freezes.
- Mode 1 mirrors the upstream methodology but is bounded by whatever
  datasets are present in our local OS export.

---

## 6. Reconcile (Max Harlow) — Equasis, Russian FTS/ITSoft, SEC EDGAR

- **Source repo:** https://github.com/maxharlow/reconcile
- **What it adds:** CSV fan-out enrichment against online services we
  don't already ingest in bulk. Three reconcilers are scaffolded:
  - **Equasis** (`ship-imo-numbers-to-ship-details`) — vessel ownership
    + flag history. Hard-capped at ~500 lookups/day; feed it
    investigative shortlists only.
  - **Russian FTS + ITSoft** (`ru-company-names-to-ru-company-numbers`
    → `ru-company-numbers-to-company-details`) — public Russian business
    register lookups, no auth.
  - **SEC EDGAR** (`names-to-sec-ciks` → `sec-ciks-to-sec-filings`) — US
    public-company filings, no auth.

### Install

Bundled into the Railway image (Dockerfile installs Node 20 +
`npm install -g reconcile`). Locally, either `npm install -g reconcile`
or set `RECONCILE_CMD="npx reconcile"`.

### Credentials

Equasis is the only one needing auth:
`EQUASIS_CREDENTIALS=email:password` in `.env`.

### Run

```bash
uv run python scripts/reconcile_equasis.py \
    --input data/reports/generated/shortlist_imos.csv \
    --imo-field IMO \
    --out data/reports/generated/shortlist_imos_enriched.csv

uv run python scripts/reconcile_ru_companies.py \
    --input data/reports/generated/ru_shortlist.csv \
    --name-field CompanyName \
    --out data/reports/generated/ru_shortlist_enriched.csv

uv run python scripts/reconcile_sec_filings.py \
    --input data/reports/generated/us_shortlist.csv \
    --name-field name \
    --filing-type 10-K \
    --out data/reports/generated/us_shortlist_sec.csv
```

Railway: `POST /run-script?name=reconcile_equasis`
(or `reconcile_ru_companies`, `reconcile_sec_filings`).

### Caveats

- `reconcile` is rate-limited per-source. The shared wrapper passes
  `-c <cache_dir>` (under `data/interim/reconcile_cache/<source>/`) so
  re-runs don't re-hit upstream APIs.
- Feed only deduped shortlists (e.g. from `rank_clusters.py` or
  list-match output). Bulk-feeding the corpus will get you banned,
  especially on Equasis.
- The thin wrapper at `src/shellnet/sources/reconcile.py` is shared by
  all three scripts; add new reconcilers by mirroring the existing
  script files.

---

## 7. UK disqualified directors (Insolvency Service)

- **Source repo:** https://github.com/maxharlow/scrape-disqualified-directors
- **Upstream:** `insolvencydirect.bis.gov.uk` (UK Insolvency Service
  register of disqualified directors).
- **What it adds:** a list of named individuals barred from acting as
  UK company directors, with date of birth, disqualification length,
  last-known address, and the company / conduct that triggered the
  disqualification. An exact `(normalized_person_name, date_of_birth)`
  match against our person table is a strong investigative signal —
  this person is in our shell-network *and* has been struck off in the
  UK for company-officer misconduct.

### Run

```bash
# Scrape (sequential, ~hours; cached by the upstream scraper).
uv run python scripts/scrape_disqualified_directors.py
# Project the CSV into the join-ready parquet.
uv run python scripts/ingest_uk_disqualified_directors.py
```

Railway: `POST /run-script?name=scrape_uk_disqualified_directors` then
`POST /run-script?name=ingest_uk_disqualified_directors`.

### Output

- Raw: `data/raw/scrapers/disqualified-directors/disqualified-directors.csv`
- Projected: `data/interim/uk_disqualified_directors.parquet` with
  columns `source_id, person_name, normalized_person_name,
  date_of_birth, company_name, normalized_company_name, address_raw,
  normalized_address, date_order_starts, disqualification_length,
  conduct, information_correct_as_of`.

### Caveats

- The upstream site is unauthenticated but sequential
  (`maxParallel: 1`); a full crawl is slow. Run it on Railway and let
  the resulting CSV sit on the data volume.
- The Insolvency Service publishes only *recent* disqualifications;
  historic strike-offs may not appear. A non-match here does not
  exonerate.

---

## 8. UK MPs' Register of Members' Financial Interests

- **Source repo:** https://github.com/maxharlow/scrape-members-financial-interests
- **Upstream:** `publications.parliament.uk` (Register of Members'
  Financial Interests).
- **What it adds:** a PEP / political-exposure overlay against
  shortlists. Useful for spotting cases where an investigative
  shortlist intersects with declared MP interests — historically a
  fertile area for shell-company conflicts.

### Run

```bash
uv run python scripts/scrape_mp_interests.py
```

Railway: `POST /run-script?name=scrape_mp_interests`. The scraper
caches per-URL responses under `data/raw/scrapers/members-financial-interests/cache/`
so re-runs are mostly free.

### Output

`data/raw/scrapers/members-financial-interests/members-financial-interests.csv`.
We don't (yet) ingest this into the unified person table — schema is
loose ("structural inconsistencies may occur" per the upstream
README); use it as a spot-check overlay against ranked shortlists.

### Caveats

- Upstream README warns: "It's probably not wise to use this as your
  sole source for anything important." Treat as enrichment.
