#!/usr/bin/env bash
# bulk-index-sync.sh — Firestore composite index を REST で冪等に貼るスタンドアロン版。
#
# 使い方:
#   PROJECT=mustpost-dev ./bulk-index-sync.sh path/to/firestore.indexes.json
#
# 前提:
#   - gcloud auth 済み（Application Default Credentials または gcloud auth login）
#   - 実行 SA/user が roles/datastore.indexAdmin を持つ
#   - jq が入っている（macOS: brew install jq）
#
# 挙動:
#   - HTTP 200 = created           → OK
#   - HTTP 409 = already exists    → SKIP (成功扱い)
#   - HTTP 400 "not necessary"     → SKIP (built-in で足りる)
#   - それ以外                      → FAIL カウント
#   - 最後に集計を出す。1 個でも FAIL があれば exit 1

set -euo pipefail

PROJECT="${PROJECT:?PROJECT env var required (e.g. PROJECT=mustpost-dev)}"
INDEXES_JSON="${1:?usage: $0 <firestore.indexes.json>}"

if ! command -v jq >/dev/null; then
  echo "jq not found. brew install jq (or apt-get install jq)."
  exit 1
fi

TOKEN="$(gcloud auth print-access-token)"
COUNT="$(jq '.indexes | length' "$INDEXES_JSON")"
echo "→ syncing ${COUNT} composite indexes to project=${PROJECT}"

OK=0; SKIP=0; FAIL=0
for i in $(seq 0 $((COUNT-1))); do
  CG="$(jq -r ".indexes[$i].collectionGroup" "$INDEXES_JSON")"
  BODY="$(jq -c ".indexes[$i] | {queryScope, fields}" "$INDEXES_JSON")"
  URL="https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/collectionGroups/${CG}/indexes"

  STATUS="$(curl -s -o /tmp/idx-$i.json -w "%{http_code}" -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-Goog-User-Project: ${PROJECT}" \
    -H "Content-Type: application/json" \
    -d "$BODY" "$URL")"

  case "$STATUS" in
    200) OK=$((OK+1)) ;;
    409) SKIP=$((SKIP+1)) ;;
    400)
      if grep -q "not necessary" /tmp/idx-$i.json; then
        SKIP=$((SKIP+1))
      else
        FAIL=$((FAIL+1))
        echo "  ✗ index #$i (${CG}) HTTP 400"
        head -c 400 /tmp/idx-$i.json; echo
      fi
      ;;
    *)
      FAIL=$((FAIL+1))
      echo "  ✗ index #$i (${CG}) HTTP ${STATUS}"
      head -c 400 /tmp/idx-$i.json; echo
      ;;
  esac
done

echo "→ result: ${OK} created, ${SKIP} existed/skipped, ${FAIL} failed"
if [ "$FAIL" -gt 0 ]; then exit 1; fi
