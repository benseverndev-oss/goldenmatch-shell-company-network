#!/usr/bin/env bash
# Thin operator helper for the Railway shellnet-job service.
#
# Subcommands:
#   run <script-name>            POST /run-script?name=<n>, poll until done.
#   fetch <relpath> [local-out]  GET  /download?path=<relpath>.
#   status [stage]               GET  /status, optionally filter to a stage.
#
# Reads SHELLNET_JOB_URL and SHELLNET_JOB_TOKEN from env (set them once in
# your shell). See `just job-run` and `just job-fetch` for the recipes
# that wrap this.

set -euo pipefail

: "${SHELLNET_JOB_URL:?SHELLNET_JOB_URL not set}"
: "${SHELLNET_JOB_TOKEN:?SHELLNET_JOB_TOKEN not set}"

auth=(-H "Authorization: Bearer ${SHELLNET_JOB_TOKEN}")

_status_field() {
    # _status_field STAGE FIELD — read state.json[stages][STAGE][FIELD] via /status.
    local stage="$1" field="$2"
    curl -fsS "${auth[@]}" "${SHELLNET_JOB_URL}/status" \
        | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('stages', {}).get('${stage}', {}).get('${field}', '?'))
"
}

cmd_run() {
    local name="${1:?usage: $0 run <script-name>}"
    local stage="script_${name}"
    echo ">> POST /run-script?name=${name}"
    curl -fsS -X POST "${auth[@]}" "${SHELLNET_JOB_URL}/run-script?name=${name}"
    echo
    echo ">> polling ${stage}"
    local s
    for _ in $(seq 1 720); do
        sleep 5
        s="$(_status_field "${stage}" status)"
        printf '  %s: %s\n' "${stage}" "${s}"
        case "${s}" in
            completed) break ;;
            failed)
                echo "::error::${stage} failed; tailing log:"
                curl -fsS "${auth[@]}" "${SHELLNET_JOB_URL}/logs/${stage}?tail=80" || true
                exit 1 ;;
        esac
    done
    if [[ "${s:-}" != "completed" ]]; then
        echo "::error::${stage} did not complete within timeout"
        exit 1
    fi
    echo ">> ${stage} OK"
}

cmd_fetch() {
    local relpath="${1:?usage: $0 fetch <relpath> [local-out]}"
    local out="${2:-$(basename "${relpath}")}"
    echo ">> GET /download?path=${relpath} -> ${out}"
    curl -fsS "${auth[@]}" "${SHELLNET_JOB_URL}/download?path=${relpath}" -o "${out}"
    ls -lh "${out}"
}

cmd_status() {
    local stage="${1:-}"
    if [[ -z "${stage}" ]]; then
        curl -fsS "${auth[@]}" "${SHELLNET_JOB_URL}/status" | python3 -m json.tool
    else
        curl -fsS "${auth[@]}" "${SHELLNET_JOB_URL}/status" \
            | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(json.dumps(d.get('stages', {}).get('${stage}', {}), indent=2))
"
    fi
}

case "${1:-}" in
    run)    shift; cmd_run "$@" ;;
    fetch)  shift; cmd_fetch "$@" ;;
    status) shift; cmd_status "$@" ;;
    *)
        echo "usage: $0 {run|fetch|status} ..." >&2
        exit 2 ;;
esac
