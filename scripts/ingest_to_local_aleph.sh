#!/usr/bin/env bash
# Convenience wrapper: unzip a GoldenMatch validation bundle and ingest it
# into the local OpenAleph stack (see docker-compose.openaleph.yml).
#
# Usage:
#   ./scripts/ingest_to_local_aleph.sh <community-id>
#
# Requires:
#   - docker-compose.openaleph.yml stack already up (`docker compose -f ... up -d`)
#   - ALEPHCLIENT_HOST + ALEPHCLIENT_API_KEY env vars set
#   - alephclient: `pip install alephclient`

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <community-id>" >&2
    exit 1
fi

CID="$1"
BUNDLE="docs/validation/data/cluster_${CID}_aleph_bundle.zip"
WORK="/tmp/gm-aleph-cluster-${CID}"
FOREIGN_ID="gm-cluster-${CID}-bundle"

if [ ! -f "$BUNDLE" ]; then
    echo "::error::bundle not found: $BUNDLE" >&2
    echo "Build it first with:" >&2
    echo "  uv run python scripts/build_openaleph_bundle.py --community-id $CID --person \"...\"" >&2
    exit 1
fi

if [ -z "${ALEPHCLIENT_HOST:-}" ] || [ -z "${ALEPHCLIENT_API_KEY:-}" ]; then
    echo "::error::set ALEPHCLIENT_HOST and ALEPHCLIENT_API_KEY (see docs/openaleph/README.md)" >&2
    exit 1
fi

if ! command -v alephclient >/dev/null 2>&1; then
    echo "::error::alephclient not installed. Run: pip install alephclient" >&2
    exit 1
fi

echo "Unzipping $BUNDLE -> $WORK ..."
rm -rf "$WORK"
mkdir -p "$WORK"
unzip -q "$BUNDLE" -d "$WORK"

echo "Ingesting to $ALEPHCLIENT_HOST (foreign-id: $FOREIGN_ID) ..."
alephclient crawldir \
    --foreign-id "$FOREIGN_ID" \
    --language en \
    "$WORK"

echo "Done. Visit ${ALEPHCLIENT_HOST}entities to browse."
