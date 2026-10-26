#!/usr/bin/env bash
# End-to-end Docker smoke test. Run from the repository root.
set -euo pipefail

command -v docker >/dev/null || { echo "Docker is required" >&2; exit 2; }
command -v python3 >/dev/null || { echo "Python 3 is required" >&2; exit 2; }
command -v curl >/dev/null || { echo "curl is required" >&2; exit 2; }

compose=(docker compose -f docker/docker-compose.yml)
cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    "${compose[@]}" ps >&2 || true
    "${compose[@]}" logs --tail=100 gateway nulld >&2 || true
  fi
  "${compose[@]}" down || true
  exit "$status"
}
trap cleanup EXIT

"${compose[@]}" config --quiet
"${compose[@]}" up --build -d
python3 scripts/check_gateway_health.py --wait-seconds 300

thread_id="smoke_$(date +%s)_$$"
curl --fail --silent --show-error --max-time 30 \
  -H 'Content-Type: application/json' \
  --data '{"text":"Docker smoke probe","salience":1.0}' \
  "http://127.0.0.1:8000/inject?thread_id=${thread_id}" >/dev/null
curl --fail --silent --show-error --max-time 30 \
  "http://127.0.0.1:8000/recall?thread_id=${thread_id}" \
  | python3 -c 'import json,sys; result=json.load(sys.stdin); assert isinstance(result,dict), result'
echo "Docker gateway smoke checks passed (health, inject, recall JSON)"
