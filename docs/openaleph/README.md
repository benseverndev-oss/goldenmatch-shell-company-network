# Local OpenAleph for reviewing GoldenMatch bundles

The first three PRs in this thread shipped:

1. **FTM export** (`scripts/export_validation_pack_ftm.py`) — pack → FollowTheMoney ndjson
2. **OpenAleph bundle** (`scripts/build_openaleph_bundle.py`) — pack + corroboration → zip
3. **Local OpenAleph** — this doc — bring the stack up, ingest a bundle, click around

OpenAleph is the maintained fork of the ICIJ Aleph investigative platform. You
use it to **search, cross-reference, and review** the structured entities + raw
documents we packaged.

## Prerequisites

- Docker Desktop with at least 8 GB RAM allocated (Elasticsearch is the
  hungry one)
- `alephclient` Python package for ingesting bundles:
  `pip install alephclient`
- A built bundle: `docs/validation/data/cluster_<id>_aleph_bundle.zip`

## Bring up the stack

```bash
# from repo root
docker compose -f docker-compose.openaleph.yml up -d

# wait ~60 sec for elasticsearch to come up, then initialise schema
docker compose -f docker-compose.openaleph.yml exec api aleph upgrade

# create your admin user
docker compose -f docker-compose.openaleph.yml exec api aleph createuser \
    --admin --email you@example.com --name "You"

# tail the API container to see ingest progress
docker compose -f docker-compose.openaleph.yml logs -f api worker
```

Open <http://localhost:8080/>, log in with the email you just used. Grab an
API key from **Profile → Settings** (top-right avatar).

## Ingest a bundle

```bash
# 1. unzip the bundle
unzip docs/validation/data/cluster_47_aleph_bundle.zip -d /tmp/c47/

# 2. point alephclient at your local instance
export ALEPHCLIENT_HOST=http://localhost:8080/
export ALEPHCLIENT_API_KEY=<paste from web UI>

# 3. crawl the unzipped directory
alephclient crawldir \
    --foreign-id gm-cluster-47-bundle \
    --language en \
    /tmp/c47/
```

The `foreign-id` matches the `manifest.json` inside the bundle, so re-ingesting
overwrites in-place rather than creating duplicates. The FTM entities are
loaded first (Persons, Companies, Addresses, Directorships, Ownerships); the
markdown + CSV files come in as Documents.

Or use the convenience wrapper:

```bash
./scripts/ingest_to_local_aleph.sh 47
./scripts/ingest_to_local_aleph.sh 37
```

## What to do once it's loaded

- **Search "AGS HOUSE"** — see every cluster-37 company hanging off the
  shared registered address.
- **Open the Calvin Edward Ayre Person entity** — Aleph cross-references his
  Directorships and Ownerships; expand them to walk the graph.
- **Cross-reference** — Aleph's `xref` feature compares your bundle against
  any other dataset in the instance (e.g. OpenSanctions if you import it).
- **Documents → `research_brief.md`** — the one-page narrative summary.

## Tear-down

```bash
docker compose -f docker-compose.openaleph.yml down -v
```

The `-v` flag drops the named volumes. Without it, your data survives the
next `up -d`.

## Production caveats

This compose file is sized for **one analyst on one laptop**. For a team
deployment:

- Bump Elasticsearch heap (`ES_JAVA_OPTS`) and provision external storage.
- Replace `ALEPH_SECRET_KEY: change-me-for-prod` with a real secret.
- Put the API behind a reverse proxy with TLS.
- Add the `worker` service replicas if you ingest large document collections.
- See <https://docs.openaleph.org/deployment> for the upstream guidance.

## Going further

- **ftm-lakehouse** — once a bundle is reviewed, archive it via
  `ftm-lakehouse` for reproducibility. The `entities.ftm.json` inside each
  bundle is the canonical artefact; everything else can be regenerated from
  the validation pack.
- **OpenSanctions xref** — import OpenSanctions consolidated dataset into
  the same Aleph instance, then run `xref` against the cluster bundle to
  surface any sanctioned-entity matches automatically.
- **ICIJ Datashare** — the bundle format is also Datashare-compatible.
  Drop the unzipped folder into a Datashare data dir; the FTM file is
  auto-recognized.
