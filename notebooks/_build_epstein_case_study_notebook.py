"""Build notebooks/02_epstein_case_study.ipynb programmatically.

Source of truth for the executable Epstein-network case study. Same
pattern as ``_build_case_study_notebook.py``: each cell is constructed
with nbformat so the notebook can be regenerated on demand.

Run this script after editing; commit the resulting .ipynb alongside.
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

nb = nbf.v4.new_notebook()
nb["metadata"] = {
    "kernelspec": {
        "display_name": "Python 3 (shellnet)",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "pygments_lexer": "ipython3"},
}
cells: list = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text.lstrip("\n")))


def code(text: str) -> None:
    cells.append(nbf.v4.new_code_cell(text.strip("\n")))


md(
    """
# Epstein corporate-network — investigative case study

Companion to:

- `reports/investigations/batches/epstein_seed_review/findings.md`
- `reports/investigations/epstein_followup_findings.md`

This notebook re-derives every table and chart from the data on disk
(ICIJ Offshore Leaks bundle parsed under `data/processed/`) plus the
published GoldenMatch runs in Railway Postgres. It is the *executable*
version of those two reports.

> **Hypothesis, not proof.** Every match below is a lead the matcher
> produced from public data. Personal-name matches collide aggressively;
> address-text matches reflect string similarity, not verified physical
> identity; shared-officer overlaps are circumstantial. Nothing here
> should be read as a claim that any named individual or company was
> owned or controlled by Jeffrey Epstein unless the sourced documents
> themselves say so.
"""
)

md("## 1. Setup")
code(
    """
from __future__ import annotations
import os
from pathlib import Path
import polars as pl
from dotenv import load_dotenv

load_dotenv()
PROCESSED = Path(\"../data/processed\")
INTERIM = Path(\"../data/interim\")
print('Postgres configured:', bool(os.environ.get('DATABASE_URL')))
"""
)

md("## 2. The sourced seed list")
md(
    """
The 28 entities below are from public records (USVI Second Amended
Complaint ST-20-CV-14, NYDFS Consent Order, Senate Finance 2025 list,
USVI/JPMorgan litigation cash-flow tables). Each row in
`seeds/epstein_entities.csv` carries its own `source_note` citing
where the name came from.

Note: this is a **seed list**, not a list of conclusions. Inclusion
here does not imply wrongdoing or even confirmed Epstein control —
just that public reporting named the entity in an Epstein-adjacent
context worth verifying.
"""
)
code(
    """
seeds = pl.read_csv(\"../seeds/epstein_entities.csv\")
print(f\"{seeds.height} seeds across {seeds.get_column('seed_group').n_unique()} groups\")
seeds.group_by('seed_group').agg(pl.len().alias('n')).sort('n', descending=True)
"""
)

md("## 3. Candidate-pool coverage")
md(
    """
The unified company table is ICIJ-only for this run (GLEIF /
OpenCorporates / OpenSanctions interims not staged). That matters: ICIJ
covers offshore-provider registries, not USVI / US-Delaware records.
The Epstein seed list is heavily USVI/US.
"""
)
code(
    """
co = pl.read_parquet(PROCESSED / 'company_entities.parquet')
print(f\"{co.height:,} unified company rows\")
top_juris = co.group_by('jurisdiction').agg(pl.len().alias('n')).sort('n', descending=True).head(10)
top_juris
"""
)
md(
    """
**Read:** ICIJ has 2 rows tagged `vi` (US Virgin Islands) and 482 tagged
`us`. The candidate pool for the Epstein seed list is structurally
narrow — any USVI-registered entity is essentially impossible to find
here without OpenCorporates. The Bermuda / BVI / Cayman seeds, by
contrast, are well-covered.
"""
)

md("## 4. Entity-side batch — single in-jurisdiction hit")
code(
    """
import csv
batch_dir = Path('../reports/investigations/batches/epstein_seed_review')
with (batch_dir / 'index.md').open(encoding='utf-8') as f:
    lines = f.readlines()
n_in_juris_hit = sum(1 for ln in lines if ln.startswith('| ') and '| 100.0 |' in ln and '| ✓ |' in ln)
print(f'Reports with exact in-jurisdiction match: {n_in_juris_hit}')
print()
print('The one in-jurisdiction match:')
for ln in lines:
    if 'Liquid Funding' in ln and ln.startswith('| '):
        print(ln.strip())
        break
"""
)
md(
    """
Of 28 sourced seeds, exactly one returned an exact in-jurisdiction match
in the ICIJ corpus: **`Liquid Funding, Ltd.`** (Bermuda).

Read the full per-seed reports in
`reports/investigations/batches/epstein_seed_review/`. The findings doc
there summarises which other seeds returned only weak outside-jurisdiction
collisions, and which returned nothing at all (mostly the USVI-registry
entities — predictable given the coverage gap above).
"""
)

md("## 5. Person-side query — confirm single Epstein record")
code(
    """
persons = pl.read_parquet(PROCESSED / 'person_entities.parquet')
from rapidfuzz import fuzz
norm = persons.get_column('normalized_name').to_list()
seed_norm = 'jeffrey epstein'
scores = [fuzz.token_sort_ratio(seed_norm, n or '') for n in norm]
df = persons.with_columns(pl.Series('score', scores)).filter(pl.col('score') >= 90)
print(f'Persons matching \"Jeffrey Epstein\" at score>=90: {df.height}')
df.select(['entity_uid', 'source', 'kind', 'name', 'country', 'score']).sort('score', descending=True)
"""
)
md(
    """
**Confirmed:** ICIJ contains exactly one record with a strong score
against `Jeffrey Epstein`: `icij:80063035` `Epstein - Jeffrey E`. The
lower-scored matches (Bleustein, Goldstein, Greenstein, etc.) are
clearly different individuals.

This is a useful *negative* result. It tells us the absence of other
Epstein entities elsewhere in the corpus isn't a false negative due to
name normalization — it's that ICIJ simply doesn't carry more records
about him.
"""
)
code(
    """
edges = pl.read_parquet(INTERIM / 'icij_edges.parquet')
attached = edges.filter(
    (pl.col('src_node') == 'icij:80063035') | (pl.col('dst_node') == 'icij:80063035')
)
print(f'Edges incident to Jeffrey Epstein record: {attached.height}')
attached.select(['src_node', 'dst_node', 'kind_raw', 'role', 'start_date', 'end_date', 'source_label'])
"""
)
md(
    """
Two edges, both `officer_of`, both pointing at the same target
(`icij:82004676` `Liquid Funding, Ltd.`):

- `director of`, **2001-11-09 → 2007-03-30** (~5.4 years)
- `chairman of`, **2001-11-09 → 2007-03-19** (~5.4 years, ending 11 days earlier)

Both edges are from the Paradise Papers — Appleby leak. That's the only
direct corporate-officer attachment to Jeffrey Epstein in this corpus.
"""
)

md("## 6. 2-hop expansion — separating provider noise from signal")
md(
    """
The raw 2-hop walk from Liquid Funding surfaces ~3,800 other companies
sharing an officer with the seed. Most of that volume is *provider
noise*: Appleby Services (Bermuda) Ltd. is the registered-agent for
thousands of Bermuda entities, and audit firms (PwC, Deloitte) show up
similarly. The `--named-individuals-only` filter on `expand_2hop.py`
drops officers whose name carries a corporate legal suffix (Ltd, LLC,
…) or matches a known provider firm.
"""
)
code(
    """
# Read both versions and compare.
def grep_marker(path, marker):
    return [ln.strip() for ln in path.read_text(encoding='utf-8').splitlines() if marker in ln]

unfiltered = Path('../reports/investigations/expansions/liquid_funding_2hop.md')
filtered = Path('../reports/investigations/expansions/liquid_funding_named_2hop.md')
print('Unfiltered:', len(grep_marker(unfiltered, '`icij:')), 'rows')
print('Filtered:  ', len(grep_marker(filtered, '`icij:')), 'rows')
"""
)
code(
    """
# Find the Bear Stearns row in the filtered output — it shares only
# named-individual Lipman with Liquid Funding (Appleby was the other
# shared link in the unfiltered version).
for ln in filtered.read_text(encoding='utf-8').splitlines():
    if 'Bear Stearns' in ln:
        print(ln)
"""
)
md(
    """
**Noteworthy lead:** `Bear Stearns International Funding (Bermuda)
Limited` shares co-director `Lipman - Jeffrey M` with Liquid Funding.
Lipman is on Liquid Funding's board alongside Epstein.

Context (not something the matcher can verify): Epstein started his
career at Bear Stearns. The Bear Stearns ↔ Liquid Funding ↔ Epstein
triangle here is consistent with that biographical detail, but the
matcher only knows that the same *string* `Lipman - Jeffrey M`
appears on both Bermuda entities. A human reviewer would want
DOB / address / professional record confirmation before relying on
the Lipman ↔ Lipman link.
"""
)

md("## 7. Address probes — confirming the coverage gap")
code(
    """
import subprocess, sys
# (Don't actually shell out — just summarize the existing address-report files.)
addr_dir = Path('../reports/investigations/addresses')
summaries = []
for p in sorted(addr_dir.glob('*.md')):
    text = p.read_text(encoding='utf-8')
    for ln in text.splitlines():
        if 'matched address row' in ln and 'distinct entity registration' in ln:
            summaries.append((p.name, ln.strip()))
            break
for name, line in summaries:
    print(f'• {name}'); print(f'    {line}'); print()
"""
)
md(
    """
Pattern: addresses with offshore-provider associations (`Ugland House`
Cayman, `Canon's Court` Bermuda) light up with dozens of registrations —
classic mass-incorporation hubs. Epstein's personal addresses (`Little
St James`, `El Brillo Way`) return zero hits — they're not in ICIJ at
all, confirming the structural coverage gap. This is *uninformative*
about Epstein's actual address footprint; it just tells us ICIJ isn't
the right source for USVI / US-residential records.
"""
)

md("## 8. Published GoldenMatch context")
md(
    """
The dedupe + list-match runs published in Railway Postgres add a layer
the per-source records don't carry: which entities the matcher believes
are the same legal entity (cluster membership), and which ICIJ records
were anchored to GLEIF LEIs by the list-match pass.
"""
)
code(
    """
import psycopg
if not os.environ.get('DATABASE_URL'):
    print('DATABASE_URL not set — skipping live Postgres query.')
else:
    with psycopg.connect(os.environ['DATABASE_URL']) as conn, conn.cursor() as cur:
        cur.execute(\"SELECT run_id, what, created_at FROM shellnet.runs ORDER BY created_at\")
        for r in cur.fetchall():
            print(r)
"""
)
code(
    """
if os.environ.get('DATABASE_URL'):
    with psycopg.connect(os.environ['DATABASE_URL']) as conn, conn.cursor() as cur:
        cur.execute(
            \"\"\"
            SELECT c.cluster_id, count(*) AS members
            FROM shellnet.clusters c
            WHERE c.run_id = 'ba237a6c-8a29-43a5-8d07-f0eb81473bce'
              AND c.entity_uid IN ('icij:82004676')
            GROUP BY c.cluster_id
            \"\"\"
        )
        print('Liquid Funding cluster(s):', cur.fetchall())
"""
)
md(
    """
Liquid Funding lands in a singleton cluster — the dedupe pass found
no other entities the matcher believes are the same legal company.
That's expected: there's no GLEIF / OpenSanctions cross-source row to
fuse with. The published-context layer is still informative as a
*sanity check* (the entity passed the matcher's threshold cleanly and
sits in a cluster of its own, not silently merged into something else).
"""
)

md("## 9. Findings summary")
md(
    """
- **Confirmed (high confidence):** `Liquid Funding, Ltd.` (Bermuda) is
  in ICIJ Paradise Papers (Appleby) with Jeffrey E Epstein listed as
  both **director** (2001-11-09 → 2007-03-30) and **chairman**
  (2001-11-09 → 2007-03-19). The seed source (public reporting) and
  the ICIJ record corroborate each other on this point.
- **Hypothesis (medium confidence, needs verification):** `Bear Stearns
  International Funding (Bermuda) Limited` shares co-director
  `Lipman - Jeffrey M` with Liquid Funding. The Lipman ↔ Lipman link
  is a name-string match in ICIJ, not a verified identity.
- **Lead (low confidence, candidate parent):** `Liquid Funding
  Holdings, LLC` (US) appears as an officer of Liquid Funding Ltd. —
  the apparent US parent / holding-company shape. Not currently in
  the company table as a row (only as a person-shaped officer link).
- **Uninformative absence:** the other 27 seeds returned no
  in-jurisdiction matches. That's a coverage artefact: ICIJ has 2 `vi`
  rows and 482 `us` rows in 814k total. The absence here is not
  evidence that the named entities don't exist or aren't
  Epstein-linked — it's evidence that ICIJ is the wrong corpus for
  USVI-registered material.

**What would extend this:**

1. OpenCorporates ingest for the USVI registry — biggest gap.
2. GLEIF LEI cross-check for the financial entities (`Financial Trust
   Company, Inc.`, `Southern Trust Company, Inc.`).
3. OpenSanctions for any sanctions / PEP overlap.
4. Verifying the `Lipman - Jeffrey M` ICIJ record against public
   filings to confirm or refute the Bear Stearns ↔ Liquid Funding
   person link.

## 10. Ethical posture

Unchanged from the README. Matches are hypotheses; ICIJ membership
does not imply wrongdoing; manual review is required before
publishing any identity-linked claim. The single Epstein ↔ Liquid
Funding link is sufficiently corroborated by public reporting + ICIJ
to be discussed as fact in this notebook; everything else is framed
as a lead.
"""
)

nb["cells"] = cells

out = Path(__file__).parent / "02_epstein_case_study.ipynb"
out.write_text(nbf.writes(nb) + "\n", encoding="utf-8")
print(f"wrote {out}")
