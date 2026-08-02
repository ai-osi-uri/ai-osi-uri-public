---
name: switch-to-live-mode
description: |
  デプロイ済みアプリの Stripe を **テストモードから本番（Live）に切り替える**。Live
  で商品・価格・Payment Link・Webhook を再作成し、Vercel の環境変数（または HTML 内の
  Payment Link URL）を更新して再デプロイまで行う。「本番化して」「Live
  モードに切り替えて」「実際にお金を受け取れるようにして」「テストモードを終了したい」
  で発動。**実課金が発生する重大操作**なので複数のチェックポイントで明示確認を取り、
  ロールバック手順も提示する。新規デプロイには使わない（`create-app`）。
version: 0.1.0
---

# Stripe テストモード → 本番モード切替スキル（switch-to-live-mode）

既に `create-app` でデプロイされた Stripe テストモード前提のアプリを、本番
（Live）モードに切り替える。**実際の課金が発生する**操作のため、各ステップでユーザー
の明示的な確認を取ること。

このスキルは「切替」だけを担当する。新規デプロイは `create-app` を、
初期環境構築は `setup-deploy-environment` を使う。

---

## 重大な前置き（必ずユーザーに伝える）

このスキルを実行すると、以下のことが起きる：

1. **公開済みのアプリで、実際の課金が始まる**（テストカードでは決済できなくなる）
2. **新しい Live モードの商品 ID・価格 ID が発行される**（テスト ID とは別物）
3. **既存のテストモードの商品・サブスク・顧客は Stripe 上にそのまま残る**（管理画面で
   切替可能。ただし運用上は Live モードに完全移行する想定）
4. **テストモードに戻すロールバック手順**は完了レポートで提示する

実行前に AskUserQuestion で **「実際にお金が動く状態になることを理解していますか？」**
を確認する。

## 拡張ツールでの実行方針（重要）

Stripe の本番リソース作成は **AI OSI URI Deploy 拡張のツールを `mode:"live"` で**呼ぶ
（生 curl + Live キーは使わない）。各呼び出しに **`confirm_live: true`** を付けないとツール側で
停止する（誤課金ガード）。

- 商品＋価格: `stripe_create_product_and_price({..., mode:"live", confirm_live:true})`
- Payment Link: `stripe_create_payment_link({ price_id, mode:"live", confirm_live:true })`
- Webhook: `stripe_create_webhook({ url, mode:"live", confirm_live:true })`（`whsec_` は作成時のみ全文取得）

> 注: Vercel の **既存プロジェクトの env 更新 / 再デプロイ**は現状の拡張ツールに無い
> （`vercel_create_project_and_deploy` は新規作成用）。本番化での env 差し替えは、当面
> Vercel ダッシュボード / API での手動対応が必要（将来 `vercel_set_env` ツールを追加予定）。
> 以降の手順内の Stripe 部分は上記ツールに読み替えること。

---

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| `AI OSI URI Deploy` 拡張が有効 | `health_check` ツール | `setup-deploy-environment`（拡張導入）を案内 |
| 切替対象のプロジェクトがデプロイ済み | Vercel に該当プロジェクトがある | `create-app` の実行を促す |
| Stripe アカウントが Live 利用可能 | `/v1/account` の `charges_enabled: true` | Stripe Dashboard で本人確認・口座登録の完了を促す |
| Stripe Live キーを拡張に入力済み | `health_check` の `stripe.live.valid: true` | 拡張設定の「Stripe Secret Key（本番/Live）」に `sk_live_` を入力 |
| Live モードの Customer Portal 設定 | Dashboard → Settings → Customer portal（Live） | 未設定なら警告（任意で続行可） |

---

## ワークフロー全体像

```
1. 認証情報・対象プロジェクトの特定
2. 重要な事前確認（AskUserQuestion で 2 回）
3. Stripe Live API Key の取得 → 検証
4. Stripe Live アカウントの利用可能状況確認
5. 既存テストモード商品の確認とユーザーへの提示
6. Live モードで商品・価格を再作成
7. 入力種別ごとの差し替え
   - 静的 HTML: Payment Link URL を置換 → push
   - SaaS: Vercel 環境変数を更新
8. Live モードで Webhook を作成 → secret 反映
9. Customer Portal の Live 設定確認
10. 再デプロイ
11. スモークテスト（HTTP レベルのみ。実決済は user に任せる）
12. 完了レポート + ロールバック手順
```

---

## Step 1: 認証情報・対象プロジェクトの特定

認証情報は **AI OSI URI Deploy 拡張**が保持する（`.env` は読まない）。まず `health_check`
を呼び、`stripe.live.valid: true`（本番キー入力済み）と `vercel.valid: true` を確認する。
不足していれば拡張設定での入力を案内して中断。

対象プロジェクトは：
- ユーザーから明示的に指定（リポジトリ名 or Vercel プロジェクト名）
- または、Vercel API でプロジェクト一覧を出して AskUserQuestion で選択

```bash
curl -s -H "Authorization: Bearer $VERCEL_TOKEN" \
  https://api.vercel.com/v9/projects | jq '.projects[] | {id, name, link}'
```

選択結果から `PROJECT_ID`、`REPO_NAME` を保持。

---

## Step 2: 重要な事前確認（AskUserQuestion ×2）

### 確認 1：意図の明示

```
AskUserQuestion:
  question: 本番モードに切り替えると、実際にクレジットカード決済が始まります。
            続行しますか？
  options:
    - 「はい、本番モードに切り替えます」
    - 「もう少し検討してからにします」
    - 「キャンセル」
```

「もう少し検討」「キャンセル」が選ばれた場合はスキル中断。

### 確認 2：影響範囲の説明

```
AskUserQuestion:
  question: 切替対象のプロジェクトは「<PROJECT_NAME>」です。
            このアプリで以下の変更が起きます。続行しますか？
            - 新しい Live モードの商品・価格・Webhook が作成されます
            - 既存のテストモードリソースは残ります
            - Vercel 環境変数（または HTML）が Live 用に書き換わります
            - 再デプロイされ、本番運用が始まります
  options:
    - 「OK、進める」
    - 「キャンセル」
```

---

## Step 3: Stripe Live API Key の取得

### 案内メッセージ

```
Stripe Live API key を発行してください。

1. ブラウザで https://dashboard.stripe.com/apikeys を開く
   ⚠️ URL に "test" が入っていないことを確認（本番モード）
2. 「Reveal live key」をクリック
3. sk_live_ で始まる文字列をコピー

⚠️ Live key は本番アカウントへのフルアクセス権を持ちます。漏洩した場合は即 Revoke
してください。

コピーした sk_live_... を次のメッセージで貼り付けてください。
```

### 検証

```bash
curl -s -o /tmp/stripe_live_test.json -w "%{http_code}" \
  -u "$STRIPE_LIVE_KEY:" \
  https://api.stripe.com/v1/account
```

- HTTP 200 → 認証成功
- レスポンスの `livemode: true` を確認
- `charges_enabled: false` の場合は Step 4 で対応

---

## Step 4: Stripe Live 利用可能性の確認

```bash
ACCOUNT=$(curl -s -u "$STRIPE_LIVE_KEY:" https://api.stripe.com/v1/account)
echo "$ACCOUNT" | jq '{
  business_profile: .business_profile.name,
  country: .country,
  currency: .default_currency,
  charges_enabled: .charges_enabled,
  payouts_enabled: .payouts_enabled,
  details_submitted: .details_submitted,
  livemode: .livemode
}'
```

| 状態 | 意味 | 対応 |
| --- | --- | --- |
| `charges_enabled: true` | 決済受付 OK | 進む |
| `charges_enabled: false`、`details_submitted: false` | 本人確認未完了 | Stripe Dashboard で本人確認を促す |
| `payouts_enabled: false` | 銀行口座未登録 | 「お金を受け取る口座が登録されていません。Stripe Dashboard で登録してください」 |

`charges_enabled: false` の場合は **強制中断**。本番化できない状態。

---

## Step 5: 既存テストモード商品の確認

Vercel の現在の env 変数から既存の test product / price を取得し、ユーザーに提示：

```bash
ENV_LIST=$(curl -s -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v9/projects/$PROJECT_ID/env?decrypt=true")
TEST_PRICE_ID=$(echo "$ENV_LIST" | jq -r '.envs[] | select(.key=="NEXT_PUBLIC_STRIPE_PRICE_ID") | .value' | head -1)
TEST_SECRET_KEY=$(echo "$ENV_LIST" | jq -r '.envs[] | select(.key=="STRIPE_SECRET_KEY") | .value' | head -1)
```

テストキーで Stripe API を叩いて、既存の商品の名前・価格・課金形態を取得し、
**Live で再作成する内容の確認**としてユーザーに提示：

```
現在のテストモード商品：
- 商品名: <name>
- 価格: ¥<amount>（<one_time | monthly | yearly>）
- 商品説明: <description>

これと同じ内容で Live モードに作成します。よろしいですか？
（変更したい場合は具体的に教えてください）
```

ユーザーから修正があれば反映。

---

## Step 6: Live モードで商品・価格を再作成

Stripe MCP は接続時のモード（test/live）に固定されることが多いので、**curl で直接 Live
キーを使う**のが安全。

### 6-1. Product 作成

```bash
curl -s -u "$STRIPE_LIVE_KEY:" \
  -d "name=$PRODUCT_NAME" \
  -d "description=$PRODUCT_DESC" \
  https://api.stripe.com/v1/products \
  | jq -r '.id' > /tmp/live_product_id.txt
```

### 6-2. Price 作成

単発商品：
```bash
curl -s -u "$STRIPE_LIVE_KEY:" \
  -d "product=$LIVE_PRODUCT_ID" \
  -d "unit_amount=$AMOUNT" \
  -d "currency=$CURRENCY" \
  https://api.stripe.com/v1/prices \
  | jq -r '.id' > /tmp/live_price_id.txt
```

サブスク商品：
```bash
curl -s -u "$STRIPE_LIVE_KEY:" \
  -d "product=$LIVE_PRODUCT_ID" \
  -d "unit_amount=$AMOUNT" \
  -d "currency=$CURRENCY" \
  -d "recurring[interval]=month" \
  https://api.stripe.com/v1/prices \
  | jq -r '.id' > /tmp/live_price_id.txt
```

### 6-3. Payment Link（静的 HTML の場合のみ）

```bash
curl -s -u "$STRIPE_LIVE_KEY:" \
  -d "line_items[0][price]=$LIVE_PRICE_ID" \
  -d "line_items[0][quantity]=1" \
  https://api.stripe.com/v1/payment_links \
  | jq -r '.url' > /tmp/live_payment_link_url.txt
```

注：`buy.stripe.com/test_xxx` の `test_` プレフィックスが取れた URL になる。

---

## Step 7: 差し替え

### 7-A. 静的 HTML の場合

リポジトリをローカルに clone して `index.html` の Payment Link URL を置換：

```bash
WORK_DIR="/tmp/<repo-name>-live"
rm -rf "$WORK_DIR"
git clone "https://${GITHUB_USERNAME}:${GITHUB_PAT}@github.com/${GITHUB_USERNAME}/${REPO_NAME}.git" "$WORK_DIR"
cd "$WORK_DIR"

# test_ プレフィックス付きの URL を Live URL に置換
TEST_URL_PATTERN="https://buy.stripe.com/test_[A-Za-z0-9]\+"
sed -i.bak "s|$TEST_URL_PATTERN|$LIVE_PAYMENT_LINK_URL|g" index.html

# 変更を確認
git diff index.html | head -30

# コミット & push
git -c user.email="cd@a" -c user.name="cd" add index.html
git -c user.email="cd@a" -c user.name="cd" commit -q -m "feat: switch to live mode (production payment link)"
git push -q origin main
```

### 7-B. SaaS の場合

Vercel 環境変数を 3 つ PATCH（または 2 つ + 1 つ追加）：

```bash
# 既存の env id を取得
ENV_LIST=$(curl -s -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v9/projects/$PROJECT_ID/env")

update_env() {
  local KEY=$1; local VALUE=$2
  local ENV_ID=$(echo "$ENV_LIST" | jq -r ".envs[] | select(.key==\"$KEY\") | .id" | head -1)
  if [ -n "$ENV_ID" ] && [ "$ENV_ID" != "null" ]; then
    curl -s -X PATCH \
      -H "Authorization: Bearer $VERCEL_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"value\":\"$VALUE\"}" \
      "https://api.vercel.com/v9/projects/$PROJECT_ID/env/$ENV_ID"
  fi
}

update_env "STRIPE_SECRET_KEY" "$STRIPE_LIVE_KEY"
update_env "NEXT_PUBLIC_STRIPE_PRICE_ID" "$LIVE_PRICE_ID"
# STRIPE_WEBHOOK_SECRET は Step 8 で更新
```

---

## Step 8: Live モードで Webhook 作成

```bash
curl -s -u "$STRIPE_LIVE_KEY:" \
  -d "url=${APP_URL}/api/stripe/webhook" \
  -d "enabled_events[]=checkout.session.completed" \
  -d "enabled_events[]=customer.subscription.created" \
  -d "enabled_events[]=customer.subscription.updated" \
  -d "enabled_events[]=customer.subscription.deleted" \
  -d "enabled_events[]=invoice.payment_succeeded" \
  -d "enabled_events[]=invoice.payment_failed" \
  -d "description=<アプリ名> LIVE subscription lifecycle (cowork-deploy)" \
  https://api.stripe.com/v1/webhook_endpoints \
  > /tmp/live_webhook.json

LIVE_WEBHOOK_SECRET=$(jq -r '.secret' /tmp/live_webhook.json)
```

Vercel env の `STRIPE_WEBHOOK_SECRET` を新しい Live secret に更新：

```bash
update_env "STRIPE_WEBHOOK_SECRET" "$LIVE_WEBHOOK_SECRET"
```

---

## Step 9: Customer Portal の Live 設定確認（任意）

サブスク販売の場合、Customer Portal が Live モードで設定済みかチェック。
未設定だと「Manage Subscription」ボタンを押した時にエラーになる。

```bash
curl -s -u "$STRIPE_LIVE_KEY:" \
  https://api.stripe.com/v1/billing_portal/configurations \
  | jq '.data[] | {id, is_default, business_profile: .business_profile.headline}'
```

設定がない場合、ユーザーに以下を案内（強制中断はしない、警告のみ）：

```
⚠️ Live モードの Customer Portal が未設定です。
購読中ユーザーがプラン変更・解約しようとするとエラーになります。

https://dashboard.stripe.com/settings/billing/portal で設定してください。
（テストモードの設定からインポートできる場合があります）
```

---

## Step 10: 再デプロイ

環境変数の変更を反映するため再デプロイをトリガー（静的 HTML の場合は push 時点で
自動デプロイされるが、SaaS は明示的に再デプロイが必要）：

```bash
REPO_ID=$(curl -s -H "Authorization: token $GITHUB_PAT" \
  "https://api.github.com/repos/${GITHUB_USERNAME}/${REPO_NAME}" | jq -r '.id')
DEPLOYMENT_ID=$(curl -s -X POST \
  -H "Authorization: Bearer $VERCEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$REPO_NAME\",\"project\":\"$PROJECT_ID\",\"target\":\"production\",\"gitSource\":{\"type\":\"github\",\"repoId\":$REPO_ID,\"ref\":\"main\"}}" \
  https://api.vercel.com/v13/deployments | jq -r '.id')
```

完了まで polling。

---

## Step 11: スモークテスト

**Live モードでは実カードでの決済テストは行わない**（実課金が発生するため）。
以下の HTTP レベルチェックのみ：

```bash
# トップページ 200
curl -s -o /dev/null -w "%{http_code}\n" "$APP_URL/"

# 静的 HTML の場合: Payment Link が live になっているか確認
curl -s "$APP_URL/" | grep -oE 'https://buy\.stripe\.com/[a-zA-Z0-9_]+' | head -3
# test_ が含まれていないこと

# Webhook エンドポイント 400（署名なし）
curl -s -X POST -w "%{http_code}\n" "$APP_URL/api/stripe/webhook"
```

実決済テストはユーザーの判断で実施してもらう（実カードを使うため）。

---

## Step 12: 完了レポート + ロールバック手順

```
🎉 本番モードへの切替完了

【公開 URL】
  $APP_URL（Live モード稼働中）

【作成した Live リソース】
  - 商品 ID: prod_xxxxx
  - 価格 ID: price_xxxxx
  - Webhook ID: we_xxxxx
  - Payment Link: https://buy.stripe.com/xxxxx（静的 HTML の場合）

【更新した Vercel 環境変数】
  - STRIPE_SECRET_KEY: sk_test_*** → sk_live_***
  - NEXT_PUBLIC_STRIPE_PRICE_ID: <test> → <live>
  - STRIPE_WEBHOOK_SECRET: <test> → <live>

【今すぐ確認すべきこと】
  1. <APP_URL> を開いて表示確認
  2. CTA ボタンの URL が `buy.stripe.com/xxxxx`（test_ プレフィックスなし）になっているか
  3. 少額の実カード決済テストを 1 度実施（推奨：自分のカードで最小額）

【⚠️ ロールバック手順】
  もし問題があってテストモードに戻したい場合：
  1. Vercel Dashboard で以下の env を元のテスト値に戻す
     - STRIPE_SECRET_KEY → sk_test_*** （前の値）
     - NEXT_PUBLIC_STRIPE_PRICE_ID → <元のテスト price_id>
     - STRIPE_WEBHOOK_SECRET → <元のテスト webhook secret>
  2. 静的 HTML の場合は git revert <last commit>
  3. 再デプロイ

  テスト用の元の値は、このスキル実行前に以下に保存しています：
  - /tmp/<project>-rollback.env
```

ロールバック用の値は事前に **Step 5** で取得した時点で
`/tmp/<project>-rollback.env` に保存しておくこと。

---

## ロールバック準備（重要）

Step 5 の終わりで、必ずロールバック用の値を保存する：

```bash
ROLLBACK_FILE="/tmp/${REPO_NAME}-rollback.env"
cat > "$ROLLBACK_FILE" <<EOF
# 切替前のテストモード値（ロールバック時に使用）
# 切替日時: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

ROLLBACK_STRIPE_SECRET_KEY=$TEST_SECRET_KEY
ROLLBACK_STRIPE_PRICE_ID=$TEST_PRICE_ID
ROLLBACK_WEBHOOK_SECRET=$TEST_WEBHOOK_SECRET
ROLLBACK_PAYMENT_LINK=$TEST_PAYMENT_LINK_URL
ROLLBACK_GIT_COMMIT=$(cd /tmp/<work> && git rev-parse HEAD)
EOF
chmod 600 "$ROLLBACK_FILE"
```

完了レポートでこのファイルパスを案内する。

---

## エラー時の挙動

| 失敗箇所 | 対応 |
| --- | --- |
| Step 3 で Live key 無効 | 再発行依頼 |
| Step 4 で `charges_enabled: false` | 強制中断、Stripe Dashboard でアカウント完成を促す |
| Step 6 で商品作成失敗 | ロールバック不要（まだ何も切り替えていない）、エラー報告 |
| Step 7-A で git push 失敗 | リポジトリ権限・ブランチ保護を確認 |
| Step 7-B で env 更新失敗 | 一部の env だけ更新済みの可能性あり、状態を確認しユーザーに共有 |
| Step 8 で Webhook 作成失敗 | env を一部 Live 化したが webhook が test のまま、という不整合状態。ユーザーに即座に共有し、ロールバックを推奨 |
| Step 10 でデプロイ失敗 | 環境変数は Live 化済み、コードは古い、という危険な状態。ロールバックを強く推奨 |
| Step 11 で表示異常 | デプロイは成功しているがコード/データが正しくない可能性。デバッグ |

特に Step 8 以降の失敗は **不整合状態**を生む可能性があるので、ロールバックの判断を
ユーザーに早めに仰ぐこと。

---

## 注意事項

- Stripe Live モードの **商品・Webhook は削除できない**（無効化のみ可）。間違って作った
  ものは Disable する
- このスキルは **テスト → 本番の一方向**を想定。本番 → テストへの「逆方向」は
  ロールバック手順として完了レポートに含める（自動化はしない）
- Live モードの Customer Portal は **テストモードの設定とは独立**。両方で個別に設定が必要
- 本番化後は **Stripe の不正利用検知（Radar）** が有効になる。テストでは通っていた
  パターンが本番では弾かれることがある
- **税金・インボイス・領収書** の設定（Stripe Tax、Customer Tax IDs 等）も Live モードで
  別途必要。このスキルでは扱わない（運用前に Stripe Dashboard で要設定）
- 既存のテストモード顧客・サブスクは Live モードに自動移行されない。テスト顧客は
  そのまま破棄するのが普通
- このスキルは **重大な操作**なので、subagent ではなくメインスレッドで実行することを推奨
