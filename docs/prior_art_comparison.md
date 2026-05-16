# Prior-art comparison

What does this project do that the two canonical investigative tools —
**ICIJ Offshore Leaks DB** and **OCCRP Aleph** — don't already? This
doc states the comparison plainly so the
[`join_novelty.md` report](reports/join_novelty.md) can lean on it.

## The two systems we're positioning against

### ICIJ Offshore Leaks Database (`offshoreleaks.icij.org`)
- **Corpus**: four leak document sets (Panama 2016, Paradise 2017,
  Pandora 2021, FinCEN files 2020) totalling ~830k entities, ~750k
  officers, ~410k addresses.
- **Schema**: Officer, Entity, Address, Intermediary, and edges between
  them. Provenance is the leak file the row came from.
- **UI**: per-entity / per-officer pages, neighbourhood graph view, free
  text search. No filter by jurisdiction risk, no overlay against
  sanctions, no cross-leak deduplication beyond what was in the source
  records.
- **Updates**: cadence is "when a new leak drops" (years apart). Not
  live.

### OCCRP Aleph (`aleph.occrp.org`)
- **Corpus**: superset — incorporates ICIJ's leaks plus government
  registries (UK Companies House, Latvia, Slovenia, Romania, USA OFAC,
  PEP lists), document dumps, and OCCRP's own investigative archive.
  Tens of millions of records.
- **Schema**: [FollowTheMoney](https://followthemoney.tech/) — the same
  schema OpenSanctions uses (Person, Company, LegalEntity, Vessel,
  Asset, …). Each row has a `dataset` tag indicating origin.
- **UI**: full-text search across documents *and* structured records,
  per-entity pages with cross-references, a "mentions" view (who else
  appears in the same document), notebook-style export.
- **Updates**: rolling — new datasets land continuously.

### What both tools share
- Both are **read-mostly investigative platforms**. They surface what
  exists; they do not run their own cross-source matching beyond
  same-name lookup.
- Both **trust the source's own identifiers**. If Panama Papers row
  `42` and FinCEN row `99` are the same legal entity, neither tool will
  tell you that unless the leaks themselves used the same identifier.
- Neither **rates novelty** — they show you the records that exist,
  not the records that are "newly surfaced because of a join you
  couldn't make yourself".

### What this project does differently

| Capability | ICIJ DB | Aleph | This project |
|---|:---:|:---:|:---:|
| ICIJ Offshore Leaks ingest | ✓ | ✓ | ✓ |
| OpenSanctions ingest (FtM) | ✗ | ✓ (named datasets) | ✓ (full + filtered) |
| GLEIF LEI registry ingest | ✗ | partial | ✓ (Level 1 + L2 relationships) |
| UK PSC (Companies House BODS) ingest | ✗ | ✓ | ✓ (+ DOB extraction) |
| UK disqualified-directors register | ✗ | ✗ | ✓ |
| Sanctions multi-list overlay (single-list-non-OFAC signal) | ✗ | ✗ | ✓ |
| **Explicit cross-source dedupe with confidence scoring** | ✗ | ✗ | ✓ (goldenmatch + DOB scoring) |
| **Ranked "newly surfaced" cross-source join report** | ✗ | ✗ | ✓ (`join_novelty.md`) |
| Live document UI for journalists | ✓ | ✓ | ✗ (not the target user) |
| Hosted, free, public | ✓ | ✓ | ✗ (it's a research showcase) |

### Concretely: things this surfaces that neither tool would

1. **Same legal entity in ICIJ + OS + GLEIF** — e.g. the
   `2138006Z57H3EJHYY303` "Altitude X*" Bermuda family from PR #51's
   first run. Aleph would show the leak record OR the sanctions record;
   nothing connects them to the same LEI.
2. **Sanctioned-but-not-OFAC officer with a UK PSC seat** — e.g.
   Pavel Maslovsky (b. 1956-12, RU). Sanctioned by UA NSDC, never by
   OFAC SDN, but listed as an officer on UK companies via PSC. The
   join (`matched_dob_scored` + `sanctions_overlay`) is what surfaces
   the lead; neither raw dataset's UI would highlight it.
3. **Cluster ranking with cross-list coverage** — entities sanctioned
   on N independent government lists are ranked higher than entities
   on 1 list. The overlay (`processed/sanctions_overlay.parquet`)
   makes this trivial; Aleph carries the same OS data but doesn't
   compute the aggregate.

### Things this project does *worse*

Honest list:

- **No document-level retrieval.** Aleph stores the actual leak PDFs
  and lets you full-text search them; we store only structured
  extractions.
- **No public UI.** Everything is parquet files, scripts, and reports.
  Not usable by non-engineer journalists today.
- **Smaller corpus than Aleph.** We don't ingest OCCRP's own document
  archive, Latvia/Slovenia/Romania registers, or court filings.
- **Single-author research project** vs. ICIJ/OCCRP's investigative
  newsroom resources.

### Where the comparison ends

This isn't a replacement for either tool. It's a different layer:
**explicit cross-source dedupe + novelty ranking on top of the public
data the two of them already aggregate**. The join_novelty report is
intended to be the kind of thing a journalist could feed *back into*
Aleph or the ICIJ DB as a starting shortlist — "here are 16 LEIs and
38 PSC officer DOBs that look multi-sourced; now go read the
underlying documents".

## How to verify this comparison

Both tools have public APIs:

- ICIJ DB: search at `offshoreleaks.icij.org/search?q=ALTITUDE+X` and
  observe that no LEI / OS-sanction column is shown.
- Aleph: `aleph.occrp.org/search?q=Pavel+Maslovsky` and observe that
  while sanction records exist, they are surfaced as separate dataset
  entries — there is no "this person is on N sanctions lists, lives in
  RU, and holds K UK PSC officer seats" rollup.

The 16 + 38 numbers above come from
[`docs/reports/join_novelty.md`](reports/join_novelty.md), refreshed by
the [`render-novelty-report.yml`](../.github/workflows/render-novelty-report.yml)
workflow.
