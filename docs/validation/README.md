# Validation packs

This directory holds **manual-review workbooks** for clusters surfaced by
the discovery pipeline. The workbook itself is human-authored — it is
where a reviewer records their judgement after working through a
candidate. The supporting **machine-generated evidence pack** that backs
each workbook is produced by `scripts/build_validation_pack.py`.

A validation pack is an **evidence packet for manual review, not a
finding or accusation**. Same-name does not imply same-person.
Recurring infrastructure is a starting point, not an indictment.

## Files

- `template.md` — the blank human-review workbook (copy to
  `cluster_<id>.md` and fill in).
- `cluster_<id>.md` — the machine-generated pack for a specific
  (community, person) pair. Contains a triage summary, overlap table,
  recurring-infrastructure profile, theme classification, search-query
  queue, same-person evidence matrix, and an ordinary-vs-unusual
  indicator table. **The final verdict is always left as
  `Human review required.`**
- `data/cluster_<id>_*.csv` / `.json` / `.md` — structured artefacts
  the reviewer can sort, grep, and reference.

## Generating a pack

**Canonical (Railway-side compute)** — matches `build_validation_queue`.
The workflow is parameterized, so any cluster from the queue can be
profiled without code changes:

```bash
gh workflow run build-validation-pack.yml \
    -f community_id=47 \
    -f person="peter kevin perry"
```

The workflow POSTs to `/run-validation-pack?community_id=...&person=...`
on the Railway job server, polls `/status`, downloads the artefacts to
`docs/validation/cluster_<id>.md` + `docs/validation/data/cluster_<id>_*`,
and auto-commits to `main`. This is the path the project conventions
ask for (`CLAUDE.md`: "all heavy compute runs on Railway").

Inputs:

- `community_id` — required positive integer (e.g. `47`, `38`, `40`).
- `person` — required name, regex `^[A-Za-z][A-Za-z .'-]{1,80}$`.
- `threshold` — optional, defaults to `0.9`.

**Local fallback** — for analyst-machine ad-hoc runs against a small
working copy of the parquets. Heavy on a laptop because `icij_edges`
is 3.3M rows:

```bash
uv run python scripts/build_validation_pack.py \
    --community-id 47 \
    --person "peter kevin perry"
```

Outputs land in `docs/validation/cluster_<id>.md` and
`docs/validation/data/cluster_<id>_*`. The script is deterministic on
the same source parquets and idempotent — re-running overwrites the
prior pack.

Flags:

- `--community-id <int>` — community to profile. Must exist in
  `docs/reports/data/confidence_communities.parquet`.
- `--person "<name>"` — human anchor for the investigation. Normalized
  to lowercase / single-spaced; looked up in
  `data/processed/icij_persons.parquet` and the corresponding dossier
  file under `docs/reports/dossiers/<slug>.md`.
- `--threshold <float>` — confidence_communities threshold to use
  (default `0.9`).
- `--run-external-search` — placeholder for a future safe in-repo
  search abstraction. Currently a no-op (queries are still written to
  CSV for manual execution).
- `--out-dir <path>` — override the output directory; useful for tests.
- `--reports-data-dir`, `--interim-dir`, `--processed-dir`,
  `--dossiers-dir` — override the source-data directories. The Railway
  job-server entry passes `/data/processed/`, `/data/interim/`,
  `/data/processed/`, and `/app/docs/reports/dossiers/` respectively.

The script degrades gracefully when optional source tables are
missing: it writes an empty CSV (with headers) and adds a warning to
the markdown. It only hard-fails when the community or the person
cannot be resolved at all.

## Reuse for other clusters or people

The script is not Cluster-47-specific. To work a different candidate
from the queue:

```bash
uv run python scripts/build_validation_pack.py \
    --community-id 38 \
    --person "darragh o brien"
```

You will get a fresh `cluster_38.md` + `data/cluster_38_*` set without
disturbing the cluster 47 outputs.

## Tests

`tests/test_build_validation_pack.py` covers:

- the script runs end-to-end on cluster 47 / Peter Kevin Perry,
- every output file exists with the expected header row,
- missing optional inputs degrade rather than crash,
- no absolute paths are hardcoded,
- pure helpers (name normalization, dossier parsing, theme
  classification) behave correctly.

```bash
uv run pytest tests/test_build_validation_pack.py
```

The end-to-end tests skip automatically if
`docs/reports/data/confidence_communities.parquet` is not present
(non-analyst CI environment).
