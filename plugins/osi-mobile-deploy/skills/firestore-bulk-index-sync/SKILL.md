---
name: firestore-bulk-index-sync
description: |
  Firestore の composite index が 50 個・100 個と大量にある案件で、`firebase deploy
  --only firestore:indexes` が「index limit」「操作進行中」「409 already exists」で
  詰まる問題を、Firestore Admin REST API `collectionGroups/{cg}/indexes` を直叩きして
  1 本ずつ冪等に create する形で解決する atomic skill。`firestore.indexes.json` を jq で
  舐めて各 index を POST、HTTP 200 = created、409 = already exists、400 "not necessary"
  = built-in index として skip、を全部「成功」に丸めることで、再 deploy が壊れない
  ようにする。「firebase deploy indexes が落ちる」「firestore index limit」「409 で index
  作れない」「大量の複合インデックスを一括作成」「MCP から firestore index を作る」
  「index を CI で自動作成」「REST で firestore index を貼る」で発動する。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# firestore-bulk-index-sync — 大量 composite index を REST で冪等に貼る

## 問題

`firebase deploy --only firestore:indexes` は:

- 1 回の deploy で同時作成できる index の上限がある（実測 10 前後で throttle）
- 既存 index と衝突する（409 conflict）と処理全体が止まる
- 「index 作成が進行中」状態で追加 create を出すとエラーで CI が真っ赤に

50 以上の composite index を持つ MustPost 級のプロジェクトでは、これで deploy が
毎回不安定になる。

## 解決

Firestore Admin REST API を直叩きし、`firestore.indexes.json` を 1 行ずつ POST。
**409 と 400 (not necessary) を成功に丸める**ことで冪等化する。

---

## 実装（CI workflow の step）

```yaml
- name: Install jq
  run: sudo apt-get install -y jq

- name: Sync Firestore composite indexes (idempotent, REST)
  run: |
    set -e
    TOKEN=$(gcloud auth print-access-token)
    PROJECT="mustpost-dev"
    COUNT=$(jq '.indexes | length' firestore.indexes.json)
    echo "→ syncing ${COUNT} composite indexes"
    OK=0; SKIP=0; FAIL=0
    for i in $(seq 0 $((COUNT-1))); do
      CG=$(jq -r ".indexes[$i].collectionGroup" firestore.indexes.json)
      BODY=$(jq -c ".indexes[$i] | {queryScope, fields}" firestore.indexes.json)
      URL="https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/collectionGroups/${CG}/indexes"
      STATUS=$(curl -s -o /tmp/idx.json -w "%{http_code}" -X POST \
        -H "Authorization: Bearer $TOKEN" \
        -H "X-Goog-User-Project: ${PROJECT}" \
        -H "Content-Type: application/json" \
        -d "$BODY" "$URL")
      case "$STATUS" in
        200) OK=$((OK+1)) ;;
        409) SKIP=$((SKIP+1)) ;;                # already exists — treat as success
        400)
          # Firestore returns 400 for "index not necessary"
          # (single-field index already covered by built-in single-field indexes).
          if grep -q "not necessary" /tmp/idx.json; then
            SKIP=$((SKIP+1))
          else
            FAIL=$((FAIL+1))
            echo "::warning::index #$i (${CG}) HTTP 400"
            head -c 500 /tmp/idx.json
          fi
          ;;
        *)
          FAIL=$((FAIL+1))
          echo "::warning::index #$i (${CG}) HTTP ${STATUS}"
          head -c 500 /tmp/idx.json
          ;;
      esac
    done
    echo "→ index sync: ${OK} created, ${SKIP} already existed, ${FAIL} failed"
    if [ "$FAIL" -gt 0 ]; then exit 1; fi
```

`references/bulk-index-sync.sh` にスタンドアロン版もある（ローカル手動実行用）。

---

## ローカルから叩く（MCP 経由）

```
mcp__AI_OSI_URI_Deploy__mac_shell({
  cmd: "gcloud",
  args: ["auth", "print-access-token"],
  cwd: "/Users/…/mustpost-native/backend"
})
→ TOKEN
```

上の bash step と同じロジックを bash で回す。または以下の python:

```python
import json, subprocess, urllib.request

project = "mustpost-dev"
token = subprocess.check_output(["gcloud", "auth", "print-access-token"]).decode().strip()
indexes = json.load(open("backend/firestore.indexes.json"))["indexes"]

ok = skip = fail = 0
for i, idx in enumerate(indexes):
    cg = idx["collectionGroup"]
    body = json.dumps({"queryScope": idx["queryScope"], "fields": idx["fields"]}).encode()
    url = f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/collectionGroups/{cg}/indexes"
    req = urllib.request.Request(url, method="POST", data=body, headers={
        "Authorization": f"Bearer {token}",
        "X-Goog-User-Project": project,
        "Content-Type": "application/json",
    })
    try:
        urllib.request.urlopen(req).read()
        ok += 1
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="ignore")
        if e.code == 409:
            skip += 1
        elif e.code == 400 and "not necessary" in body_text:
            skip += 1
        else:
            fail += 1
            print(f"idx#{i} ({cg}) HTTP {e.code}: {body_text[:300]}")

print(f"→ {ok} created / {skip} existed / {fail} failed")
```

---

## 前提

- `gcloud` が deploy 実行 SA で認証済み（Application Default Credentials または
  `--credential-file-override`）
- 実行 SA が以下の IAM を持つ:
  - `roles/datastore.indexAdmin`（推奨。index の CRUD 全部）
  - もしくは `roles/datastore.owner`
- Firestore が Native mode で作成済み（Datastore mode だと index の形が違うので流用不可）
- `firestore.indexes.json` が `{"indexes":[...], "fieldOverrides":[...]}` 形式

---

## `firestore.indexes.json` 形式チェック

`firebase deploy` は fieldOverrides もサポートするが、本 skill は composite indexes
（複数フィールド）のみ扱う。単一 field override が必要な場合は別途:

```
POST /v1/projects/{p}/databases/(default)/collectionGroups/{cg}/fields/{f}
Body: { "indexConfig": { "indexes": [...] } }
```

`references/field-override-sync.sh` にサンプル。

---

## エラーハンドリング

| 症状 | 対処 |
|---|---|
| HTTP 403 `Permission denied on resource project` | 実行 SA に `roles/datastore.indexAdmin` を付与。gcloud project も対象 project と一致させる |
| HTTP 429 quota exceeded | Firestore の index 作成は QPS 制限あり。sleep 1 を各 index の後に入れる。全部作り終わったら数分は index build が非同期で走る |
| HTTP 400 「fields duplicated」 | `firestore.indexes.json` に同じ field 定義の index が 2 個ある。jq で dedupe |
| HTTP 400 「project X not found」 | `X-Goog-User-Project` header を必ずつける（quota project 指定） |
| CI で `jq: command not found` | ubuntu-latest でも sudo apt-get install jq が必要 |
| index build が終わらない | POST 成功 = create request 受理、まで。実際の build は数分〜数十分かかる。`gcloud firestore indexes composite list --database=(default)` で state=READY を待つ |
| ローカルの Firebase Emulator では動かない | Emulator は index API を持たない。emulator は index を要求しない仕様なので、そもそも同期不要 |

---

## Firebase CLI と併用する場合

REST 直叩き step は `firebase deploy --only functions` の**前**に置く。順番:

1. jq install
2. **REST で firestore indexes を同期（本 skill）**
3. firebase-tools install
4. `firebase deploy --only functions --project X --force`
5. post-deploy: allUsers invoker 付与（`apiv2-callable-iam-gotchas` skill）

順番を守ることで、functions 側が新しい index に依存していても deploy 時に「index missing」で
落ちない。

---

## 関連スキル

- `apiv2-callable-iam-gotchas` — 同じ deploy workflow に組み込む post-deploy step
- `mobile-firebase-setup` — 初期セットアップ（本 skill は継続運用中の index 追加時）
- `mobile-update-deploy` — client の新機能追加で index が増えたときの deploy 呼び出し元
