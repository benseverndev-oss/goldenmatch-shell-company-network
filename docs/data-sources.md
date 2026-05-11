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
