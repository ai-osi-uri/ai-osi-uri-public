---
name: app-smoke-test
description: デプロイ済みのアプリ URL に対して、最低限の HTTP レベル動作確認を curl で実施するatomic スキル。指定したパス・メソッド・期待ステータス・任意の本文一致条件で検証し、結果をサマリ JSON で返す。Stripe Webhook の 400 期待、ヘルスチェックの 200 期待、Supabase PostgREST relationship probe（`PGRST200` 検出）など、チェック内容は呼び出し側がカスタム可能（決済ありなしで変わる）。実カードでの完全 E2E は対象外。「デプロイ後の動作確認」「スモークテストして」「公開した URL を叩いて確認」「ヘルスチェック走らせて」「Webhook が 400 返すか確認」「Supabase の結合が壊れていないか確認」など、デプロイ直後の HTTP 検証リクエスト全般で発動する。E2E 自動化・実決済テストには使わない（人間にお願いする）。
version: 0.1.1
---

# デプロイ後スモークテスト（atomic）

公開された URL に対して **HTTP レベルの最低限の動作確認**を curl で実施する。
Stripe Webhook の署名検証で 400 が返ること、認証必要 API で 401 が返ることなど、
**期待値とのズレを早期検出**する。

このスキルは **HTTP の reachability と status code チェック**に特化する。決済の
完全 E2E、データの整合性チェック、UI のビジュアル確認は対象外。

---

## 入力契約

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `APP_URL` | ✅ | 対象の base URL（`https://<project>.vercel.app` など） |
| `CHECKS_JSON` | 任意 | カスタムチェック配列（後述）。未指定時はトップページ 200 のみ |
| `WORK_DIR` | 任意 | state.json の場所。デフォルト `/tmp` |

### CHECKS_JSON の例

```json
[
  {"name": "homepage", "method": "GET", "path": "/", "expected": 200},
  {"name": "stripe_webhook_signed", "method": "POST", "path": "/api/stripe/webhook", "expected": 400},
  {"name": "auth_required_api", "method": "POST", "path": "/api/contracts/analyze", "expected": 401},
  {
    "name": "postgrest_relationship_tasks_creator",
    "base_url": "https://<ref>.supabase.co/rest/v1",
    "method": "GET",
    "path": "/tasks?select=id,creator:staff_profiles!tasks_created_by_fkey(display_name)&limit=0",
    "headers": {"apikey": "<anon>", "Authorization": "Bearer <anon>"},
    "expected": 200,
    "body_must_not_contain": "PGRST200"
  }
]
```

### チェック項目のフィールド

| フィールド | 必須 | 説明 |
| --- | --- | --- |
| `name` | ✅ | チェック名（state.json と printf に出る） |
| `method` | ✅ | GET / POST / PATCH など |
| `path` | ✅ | base_url からの相対パス |
| `expected` | ✅ | 期待ステータス。単一値 / 配列 / "2xx" などを許容 |
| `base_url` | 任意 | 既定は `APP_URL`。Supabase REST など別ホストを叩く時のみ指定 |
| `headers` | 任意 | `{"apikey": "...", "Authorization": "Bearer ..."}` の辞書 |
| `body_must_contain` | 任意 | レスポンス本文に含まれるべき部分文字列 |
| `body_must_not_contain` | 任意 | レスポンス本文に含まれてはいけない部分文字列（PGRST エラー検出など） |

---

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| `APP_URL` がデプロイ完了で reachable | DNS 解決可能・名前解決後の TLS ハンドシェイク成功 | 数秒待ってリトライ |
| `curl` と `jq` が利用可能 | `command -v` | エラー |

---

## ワークフロー

```
1. CHECKS_JSON のデフォルト適用
2. 各チェックを順に curl で叩いてステータスコードを取得
3. 期待値との一致判定
4. サマリを state.json に追記、stdout に集計を出す
5. 全件 PASS なら exit 0、1 件でも FAIL なら exit 1
```

---

## Step 1: チェック配列の決定

`CHECKS_JSON` 未指定時は最低限のヘルスチェックのみ。

```bash
DEFAULT_CHECKS='[{"name":"homepage","method":"GET","path":"/","expected":200}]'
CHECKS="${CHECKS_JSON:-$DEFAULT_CHECKS}"
```

オーケストレータ（`deploy-app`）が **構成に応じて** Stripe Webhook や認証 API
チェックを足す責務を持つ：

| 構成 | 推奨チェック |
| --- | --- |
| 静的 HTML（決済なし） | homepage 200 |
| 静的 HTML + Payment Link | homepage 200、Payment Link href が `buy.stripe.com/...` を含む |
| Next.js + Stripe Webhook | homepage 200、`/api/stripe/webhook` 400（署名なし POST） |
| Next.js + Auth | 上に加え、`/api/<protected>` 401 |
| Next.js + Supabase（joined select あり） | 上に加え、**PostgREST relationship probe** を joined select で使うリレーション 1 つにつき 1 件追加（後述） |

---

## Step 2: 各チェックの実行

各チェックについて、ステータスコード判定に加えて任意の **本文 contains / not-contains**
判定を行う。`base_url` / `headers` で別ホスト・認証ヘッダ送信もサポート。

```bash
RESULTS="[]"
FAIL_COUNT=0
TOTAL=$(echo "$CHECKS" | jq 'length')

for i in $(seq 0 $((TOTAL-1))); do
  NAME=$(echo "$CHECKS" | jq -r ".[$i].name")
  METHOD=$(echo "$CHECKS" | jq -r ".[$i].method")
  PATH_=$(echo "$CHECKS" | jq -r ".[$i].path")
  EXPECTED=$(echo "$CHECKS" | jq -c ".[$i].expected")
  BASE=$(echo "$CHECKS" | jq -r ".[$i].base_url // empty")
  TARGET_URL="${BASE:-$APP_URL}${PATH_}"

  # ヘッダ組み立て（任意）
  HEADER_ARGS=()
  while IFS=$'\t' read -r k v; do
    [ -n "$k" ] && HEADER_ARGS+=(-H "$k: $v")
  done < <(echo "$CHECKS" | jq -r ".[$i].headers // {} | to_entries[] | \"\(.key)\t\(.value)\"")

  # ステータスコード＋本文を 1 回の curl で取得
  BODY_FILE=$(mktemp)
  ACTUAL=$(curl -sS -o "$BODY_FILE" -w "%{http_code}" -X "$METHOD" "${HEADER_ARGS[@]}" "$TARGET_URL")

  # 1) ステータス判定
  PASS="false"
  if [ "$EXPECTED" = "$ACTUAL" ] || \
     echo "$EXPECTED" | grep -q "\"${ACTUAL}\"" || \
     echo "$EXPECTED" | jq -e --arg a "$ACTUAL" '. == ($a|tonumber) or (type=="array" and any(. == ($a|tonumber)))' >/dev/null 2>&1; then
    PASS="true"
  fi

  # 2) 本文 contains / not-contains 判定（指定があれば）
  REASON=""
  MUST_CONTAIN=$(echo "$CHECKS" | jq -r ".[$i].body_must_contain // empty")
  MUST_NOT_CONTAIN=$(echo "$CHECKS" | jq -r ".[$i].body_must_not_contain // empty")
  if [ "$PASS" = "true" ] && [ -n "$MUST_CONTAIN" ]; then
    if ! grep -q -- "$MUST_CONTAIN" "$BODY_FILE"; then
      PASS="false"; REASON=" body missing '$MUST_CONTAIN'"
    fi
  fi
  if [ "$PASS" = "true" ] && [ -n "$MUST_NOT_CONTAIN" ]; then
    if grep -q -- "$MUST_NOT_CONTAIN" "$BODY_FILE"; then
      PASS="false"; REASON=" body contained '$MUST_NOT_CONTAIN'"
    fi
  fi
  rm -f "$BODY_FILE"

  if [ "$PASS" = "false" ]; then
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi

  RESULTS=$(echo "$RESULTS" | jq \
    --arg n "$NAME" --arg m "$METHOD" --arg p "$PATH_" \
    --arg a "$ACTUAL" --argjson e "$EXPECTED" --arg pass "$PASS" --arg r "$REASON" \
    '. + [{name:$n, method:$m, path:$p, expected:$e, actual:($a|tonumber), pass:($pass=="true"), reason:$r}]')

  printf "  [%s] %s %s → %s (expected %s) %s%s\n" \
    "$([ "$PASS" = "true" ] && echo PASS || echo FAIL)" \
    "$METHOD" "$TARGET_URL" "$ACTUAL" "$EXPECTED" "$NAME" "$REASON"
done
```

---

## Step 3: state.json に追記

```bash
STATE_FILE="${WORK_DIR:-/tmp}/state.json"
if [ -f "$STATE_FILE" ]; then
  TMP=$(mktemp)
  jq --argjson r "$RESULTS" --argjson f "$FAIL_COUNT" \
     '. + {smoke_test_results:$r, smoke_test_fail_count:$f, smoke_test_at:(now|todate)}' \
     "$STATE_FILE" > "$TMP" && mv "$TMP" "$STATE_FILE"
fi

echo "Total: $TOTAL, Pass: $((TOTAL-FAIL_COUNT)), Fail: $FAIL_COUNT"
[ "$FAIL_COUNT" -eq 0 ]
```

---

## 戻り値

| 変数 | 用途 |
| --- | --- |
| `RESULTS` | 各チェックの詳細（state.json 内 `smoke_test_results`） |
| `FAIL_COUNT` | 失敗件数。0 で全件 PASS |
| exit code | 0=全 PASS、1=1 件以上 FAIL |

---

## エラー時の挙動

| ケース | 対応 |
| --- | --- |
| 全件 PASS | 進む |
| 一部 FAIL（軽微） | 警告表示してオーケストレータに判断委譲。デプロイ自体は成功扱いも可 |
| 全件 FAIL（reachability ない） | デプロイ反映待ちの可能性 → 30 秒待って 1 回だけ自動リトライ |
| timeout | エラーで返す。手動確認を案内 |

スモークテストの FAIL は **デプロイの自動ロールバックを引き起こさない**。
判断はオーケストレータ＆ユーザーに任せる。

---

## Supabase PostgREST relationship probe

**なぜ必要か**：Supabase + Next.js で `select("*, author:staff_profiles!fk_name(...)")`
のような joined select を使うと、PostgREST は外部キー定義から関係を引く。FK が
`auth.users` を指していて `staff_profiles` を指していない、といった設計ミスがあると
PostgREST は `PGRST200 "Could not find a relationship between ..."` を返す。
supabase-js はこれを `data: null, error: {...}` で返すが、Next.js ページの多くは
`data ?? []` で空配列フォールバックするため、**画面が常に空＝INSERT は通るのに
表示されない** という、デバッグしにくいバグになる（2026-05 案件で実際に踏んだ罠）。

このスキルが本文一致条件（`body_must_not_contain`）をサポートしている主な理由が
これ。joined select に使うリレーション 1 つにつき 1 件、次のチェックを追加すれば
公開前に弾ける：

```bash
# deploy-app オーケストレータが構成して渡す例
SUPABASE_REST="https://${SUPABASE_REF}.supabase.co/rest/v1"
ANON_KEY="<anon_key>"
RELATIONSHIPS=(
  "tasks|creator|staff_profiles|tasks_created_by_fkey"
  "handover_notes|author|staff_profiles|handover_notes_author_id_fkey"
  "customer_notes|creator|staff_profiles|customer_notes_created_by_fkey"
)
for r in "${RELATIONSHIPS[@]}"; do
  IFS='|' read -r T ALIAS J FK <<< "$r"
  CHECKS_JSON=$(echo "$CHECKS_JSON" | jq \
    --arg url "$SUPABASE_REST" --arg key "$ANON_KEY" \
    --arg name "pgrst_${T}_${ALIAS}" \
    --arg path "/${T}?select=id,${ALIAS}:${J}!${FK}(*)&limit=0" '. + [{
      name: $name,
      base_url: $url,
      method: "GET",
      path: $path,
      headers: {apikey: $key, Authorization: ("Bearer "+$key)},
      expected: 200,
      body_must_not_contain: "PGRST200"
    }]')
done
```

`limit=0` にしているのは「結合が解決できるかだけを知りたい」「RLS で実データは
返らなくても良い」「コストを最小化したい」の 3 拍子のため。匿名キーでもこの probe は
通る（リレーション解決は schema cache の話なので RLS とは独立）。

---

## PDF / Excel 出力エンドポイントの probe

PDF・Excel ダウンロード系は次の罠で「公開後に気付く」ことが多い。スモークに必ず追加：

| 罠 | 症状 | チェック |
|---|---|---|
| 日本語フォント未バンドル | PDF に日本語が空白で出る／`Syntax Error: Embedded font file may be invalid` | `body_size_min` を 50_000 以上に設定（Noto Sans JP variable TTF を埋め込めば最低でも数十KB） |
| サーバレス関数のタイムアウト | コールドスタートで 30s 前後に 504 / 切断 | `max_duration_ms` を 8_000 程度の警告閾値に。それ以上ならフォントをビルド時同梱 |
| RLS で空の結果 | 200 だが PDF 内容が空 / 行ゼロ | RLS 経由でデータが取れる JWT を渡して probe する |

```bash
CHECKS_JSON=$(echo "$CHECKS_JSON" | jq \
  --arg url "$APP_URL" \
  '. + [{
    name: "pdf_export",
    base_url: $url,
    method: "GET",
    path: "/api/estimates/<seed-id>/pdf",
    expected: 200,
    content_type_starts_with: "application/pdf",
    body_size_min: 50000,
    max_duration_ms: 8000
  }]')
```

### RLS 再帰の検出

Supabase で users テーブル等の SELECT が `stack depth limit exceeded` で 500 を返す
ケースがある。原因はポリシー内から呼ぶ `current_tenant_id()` 等の関数が users を
SELECT し、再びポリシーが発火する循環。authenticated JWT で `/users?select=id` を
1 回叩いて 200 を確認するチェックを入れる：

```bash
CHECKS_JSON=$(echo "$CHECKS_JSON" | jq \
  --arg url "$SUPABASE_REST" --arg key "$SEED_JWT" \
  '. + [{
    name: "rls_users_select",
    base_url: $url,
    method: "GET",
    path: "/users?select=id&limit=1",
    headers: {apikey: $key, Authorization: ("Bearer "+$key)},
    expected: 200,
    body_must_not_contain: "stack depth"
  }]')
```

500 が出たら関数を `SECURITY DEFINER` に変更する（詳細は `supabase-multitenant-rls` 参照）。

---

## 注意事項

- 実カードでの決済テストは **絶対にこのスキルでやらない**。完了レポートで人間に
  依頼する旨を必ず明示する
- `expected` を `"2xx"` のようなパターンで指定したい場合は別途 jq マッチャを拡張
  すること（現状は数値マッチのみ）
- 公開直後は CDN キャッシュやデプロイ反映遅延で 404 が出ることがある。30 秒程度の
  バックオフを 1 回だけ入れる実装が現実的
- 認証 API の 401 期待は **保護ミドルウェアが正しく走っているか**の検証になる。
  500 が返ったらサーバ実装側のバグの兆候
- `body_must_not_contain` で `PGRST200` を弾く relationship probe は、Supabase
  joined select を使うプロジェクトでは **デプロイのたびに走らせる価値が大きい**。
  スキーマ変更で FK の向きを間違えると即時バグになるため
