# Methodology (planned)

This document describes the *target* entity-resolution strategy. The first
pass of the repo only scaffolds the inputs to it; the matching itself is
incremental.

## Goal

Given fragmented public-source records about legal entities, produce two
artefacts:

1. **Identity clusters** — sets of records (across ICIJ, OpenCorporates,
   GLEIF, OpenSanctions) that we believe describe the same legal entity.
2. **An identity graph** — nodes for entities/officers/addresses and edges
   for relationships, with cross-source `same_as` edges layered on from the
   matcher.

We are explicit about uncertainty: every cluster and every edge carries a
provenance trail back to the source rows that created it.

## Approach

### Phase 1 — Conservative, identifier-anchored

Where two records share a strong identifier (LEI, jurisdiction-qualified
company number) and the names are compatible, link them. Precision should be
near-perfect; recall is whatever it is. This is what the shipped
`configs/goldenmatch_company.yml` does today.

### Phase 2 — Name + jurisdiction + address

Weighted matchkey on `(normalized_name, jurisdiction, normalized_address)`.
Already configured; threshold deliberately set high (0.85) so the first
investigations don't drown in marginal pairs.

### Phase 3 — Probabilistic with negative evidence

Once we have a small **labelled set** (call it 200–500 manually reviewed
pairs), switch the name+address matchkey to `probabilistic` so GoldenMatch
learns the agree/disagree weights via Fellegi-Sunter EM. Add negative
evidence for divergent jurisdictions and identifiers — two records with the
same name but different LEIs are very unlikely to be the same entity.

### Phase 4 — Address clusters

Run a separate GoldenMatch config (`goldenmatch_address.yml`) over the
deduplicated address pool to detect **shared registered-agent addresses** —
buildings hosting hundreds of unrelated shells. These are not
incriminating on their own but they are *signals*.

### Phase 5 — Officer/person resolution

Persons are harder (initials, transliteration, name order). Defer until
the entity side is stable. Feature ideas: nationality, DOB year if
present, shared company associations.

## Ingredients we already have

- **Normalization** (`shellnet.normalize`): suffix-stripping, ASCII-fold,
  jurisdiction aliasing, identifier cleanup.
- **Canonical schemas** (`shellnet.schemas`): typed Pydantic models for
  CompanyEntity, AddressRecord, IdentifierRecord, PersonOrOfficer,
  RelationshipEdge.
- **Per-source adapters** that all emit the same shape.
- **A unified company table** (`data/processed/company_entities.parquet`)
  that the matcher consumes.
- **A NetworkX builder** that turns the table + ICIJ edges into a
  `MultiDiGraph` with a JSON summary.

## Ingredients we still need

- A small labelled evaluation set.
- An "address only" parquet to drive `goldenmatch_address.yml`.
- A persons table from ICIJ officers + OpenSanctions `Person` rows.
- Cluster-level review tooling. GoldenMatch's `gm review` can probably
  cover this; we'll wire it up once we have real candidate pairs.

## Anti-goals

- **No automatic accusations.** No exported "X is suspicious" claims.
  Every output is structural ("these records cluster", "this address
  hosts N entities") not evaluative.
- **No commercial data.** Only public sources, with their own licences.
- **No scraping.** We use APIs and bulk downloads, not HTML scraping.
