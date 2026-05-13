# Tier D — GLEIF Level 2 corporate-ownership graph

Generated 2026-05-13. Tier D from `docs/ingestion_roadmap.md`.

## What landed

Ingested the OpenOwnership BODS GLEIF Level 2 parquet (1.1 GB) via
the same adapter pattern as Tier A. Output:
`/data/interim/gleif_l2_relationships.parquet` on the Railway volume,
**816,443 corporate parent/child ownership edges**.

The BODS edge schema is leaner than UK PSC:

```
source       gleif_l2
src_lei      XI-LEI-<20-char>    (controlled entity)
dst_lei      XI-LEI-<20-char>    (controller / ultimate parent)
kind         otherInfluenceOrControl   (BODS catch-all for GLEIF L2)
share_min    null   (not exposed by GLEIF L2)
share_max    null   (not exposed by GLEIF L2)
start_date   string (when the relationship started)
end_date     null   (not exposed)
```

GLEIF L2 doesn't carry share percentages or end-dates — that detail
lives in the L1 entity records (which we already ingest separately via
the Golden Copy adapter).

## Structure of the ownership graph

| | Count |
| --- | ---: |
| Total edges | 816,443 |
| Distinct controlled entities (src LEIs) | **284,875** |
| Distinct controllers (dst LEIs) | **74,896** |

Out-degree concentration is real: the top-15 controllers each have
1,400–4,300 declared subsidiaries. These are the holding-company and
financial-conglomerate ultimate parents — Berkshire Hathaway, BlackRock,
state-owned holding firms, etc. The exact names need a join back to
GLEIF entity records to confirm.

In-degree is much flatter: the most-controlled entity in the graph has
22 distinct controllers (presumably a multi-stakeholder joint venture).
Most entities have 1–3 declared parents.

## Why this is data, not yet a finding

The novelty payoff Tier D *could* deliver — "sanctioned individual X
shows up as PSC of UK company Y, which is a 40%-owned subsidiary of Z,
whose ultimate parent is sanctioned entity W" — requires three things
this Tier-D landing doesn't yet wire up:

1. **A bridge between UK PSC company numbers and GLEIF LEIs.** UK PSC
   entities carry Companies House registration numbers; GLEIF entities
   carry LEIs. Companies with both can be matched on
   `(jurisdiction='gb', company_number)`. That's a small adapter
   change in `company_features.py` but not done here.

2. **A company-anchored matching pass.** The current list-match is
   person-anchored (OS sanctions/crime persons → ICIJ / UK PSC
   officers). Walking the GLEIF L2 graph is a different shape: given
   a sanctioned company's LEI, walk parents/children. That's a
   separate analysis script, ~2 hr to write.

3. **LEI coverage on our matched names.** Most of the 43 UK PSC
   sanctioned-individual hits don't directly carry LEIs — LEIs are
   issued to *entities*, not natural persons. To use the ownership
   graph for those people, we'd need to first identify which
   company-entity LEIs are on OS sanctions lists, then walk from
   there.

So the corporate-ownership graph is *staged*; it's not yet *consumed*
by an investigative workflow. That matches the roadmap's honest
flagging of D as "queued, low payoff for current pipeline shape" — the
data is now available for whoever builds the company-anchored matching
pass next.

## What it would look like wired up

Imagine: take Mechel (Igor Zyuzin's company; LEI exists). Search the
GLEIF L2 edges for `src_lei = <Mechel LEI>` → ultimate parents. Search
for `dst_lei = <Mechel LEI>` → subsidiaries. Each link is a registry-
disclosed corporate relationship. Cross-reference each linked LEI back
to OS sanctions → "Mechel is a parent/subsidiary of N other sanctioned
entities, here is the chain."

That's a 2–3 hour follow-up session. The data is already on Railway
and queryable.

## Disk + state

After this ingest, Railway `/data` is at ~27 GB. Within the 30 GB
budget. The relationship parquet is 12 MB — tiny.

## Reproducing

```bash
TOKEN=...; URL=https://shellnet-job-production.up.railway.app
# Fetch the OpenOwnership GLEIF L2 BODS bundle (1.1 GB)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$URL/fetch-url?url=https%3A%2F%2Foo-bodsdata.s3.amazonaws.com%2Fdata%2Fgleif_version_0_4%2Fparquet.zip&dest=raw%2Fopenownership%2Fgleif_bods.zip"

# Ingest (extracts relationship-statement + interests, joins, ~1 min)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$URL/run-script?name=ingest_gleif_l2"

# Download for local analysis
curl -fL -H "Authorization: Bearer $TOKEN" \
  "$URL/download?path=interim/gleif_l2_relationships.parquet" \
  -o gleif_l2.parquet
```

## Status of remaining roadmap items

- **A — UK BODS:** ✅ done; 43 novel UK PSC sanctions matches
- **B — UK Overseas Entities:** ✅ subsumed by A
- **C — FinCEN Files:** queued, blocked on data shape
- **D — GLEIF L2:** ✅ data staged (this doc); company-anchored matching
  pass not yet built
- **E — OCCRP Laundromat:** deferred, multi-session
