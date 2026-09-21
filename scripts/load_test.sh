#!/usr/bin/env bash
# load_test.sh — Simple load testing for LedgerDesk API
# Usage: ./scripts/load_test.sh [BASE_URL]

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
TMPDIR_LT=$(mktemp -d)
trap 'rm -rf "$TMPDIR_LT"' EXIT

run_requests() {
  local url="$1" count="$2" label="$3"
  local timings="$TMPDIR_LT/${label}.txt" errors=0

  echo ""
  echo "=== $label ==="
  echo "URL: $url | Requests: $count"

  for i in $(seq 1 "$count"); do
    out=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" "$url" 2>/dev/null || echo "000 0.000")
    code=$(echo "$out" | awk '{print $1}')
    time_s=$(echo "$out" | awk '{print $2}')
    echo "$time_s" >> "$timings"
    [ "$code" -lt 200 ] || [ "$code" -ge 400 ] && errors=$((errors + 1))
  done

  local total
  total=$(wc -l < "$timings" | tr -d ' ')
  sort -n "$timings" > "$TMPDIR_LT/${label}_s.txt"

  local p50_i=$(( (total * 50 + 99) / 100 ))
  local p95_i=$(( (total * 95 + 99) / 100 ))
  local p99_i=$(( (total * 99 + 99) / 100 ))
  [ "$p50_i" -gt "$total" ] && p50_i=$total
  [ "$p95_i" -gt "$total" ] && p95_i=$total
  [ "$p99_i" -gt "$total" ] && p99_i=$total

  local p50 p95 p99
  p50=$(sed -n "${p50_i}p" "$TMPDIR_LT/${label}_s.txt")
  p95=$(sed -n "${p95_i}p" "$TMPDIR_LT/${label}_s.txt")
  p99=$(sed -n "${p99_i}p" "$TMPDIR_LT/${label}_s.txt")

  local err_pct
  err_pct=$(awk "BEGIN {printf \"%.1f\", ($errors / $total) * 100}")

  echo "  p50: ${p50}s | p95: ${p95}s | p99: ${p99}s"
  echo "  Errors: ${errors}/${total} (${err_pct}%)"
}

echo "============================================"
echo " LedgerDesk Load Test"
echo " Base URL: $BASE_URL"
echo " Started:  $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "============================================"

run_requests "$BASE_URL/health" 100 "GET_health"
run_requests "$BASE_URL/api/v1/cases" 50 "GET_cases"

# Get a real case ID for single-case test
CASE_ID=$(curl -s "$BASE_URL/api/v1/cases" 2>/dev/null | python3 -c "import sys,json; cs=json.load(sys.stdin).get('cases',[]); print(cs[0]['id'] if cs else '')" 2>/dev/null || echo "")
if [ -n "$CASE_ID" ]; then
  run_requests "$BASE_URL/api/v1/cases/$CASE_ID" 50 "GET_case_by_id"
else
  echo ""
  echo "=== GET_case_by_id ==="
  echo "  Skipped (no cases found)"
fi

echo ""
echo "============================================"
echo " Load Test Complete"
echo " Finished: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "============================================"
