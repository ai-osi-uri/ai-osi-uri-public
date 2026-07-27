# Vercel デプロイパス (Phase 4-W-V)

> `create-app` オーケストレータが Web アプリ／LP を Vercel にデプロイする際の詳細手順。
> 本ファイルはリファレンスであり、スキル実行時に毎回参照される。

---

## 1. 実行手順

### Step 1: フロントエンド scaffold

| アプリ種別 | scaffold 内容 |
|---|---|
| Web アプリ（Next.js） | `npx create-next-app@latest` のデフォルト構成（App Router, TypeScript, Tailwind） |
| LP / 静的サイト | HTML + CSS + JS の最小構成。フレームワーク不要 |

- scaffold 後、ユーザー要件に応じてページ・コンポーネントを実装する。
- `package.json` の `name` はリポジトリ名と一致させる。

### Step 2: GitHub リポジトリ作成 & push

`gh-create-repo-and-push` スキルを呼び出す。

- `USE_ORG` 設定に従い `owner_override` を渡す（個人アカウント or 組織）。
- リポジトリ名はアプリのスラッグ（例: `acme-booking-app`）。
- visibility は原則 `private`。顧客が public を希望した場合のみ変更。

### Step 2.5: Supabase プロビジョニング

**静的サイト／LP の場合はこのステップをスキップする。**

DB・認証が必要なアプリのみ実行する。

```
1. supabase_list_projects  → 既存プロジェクトの重複確認
2. supabase_create_project  → 新規作成（リージョン: ap-northeast-1 既定）
3. ポーリング（10-15秒間隔）で provision 完了を待つ
   - supabase_get_project でステータスを確認
   - ACTIVE_HEALTHY になるまで繰り返す（最大5分）
4. get_api_keys → anon_key, service_role_key を取得
5. get_project_url → supabase_url を取得
6. ENV_VARS_JSON 用に値を保持
```

> **注意**: provision 完了前に env を渡して Vercel デプロイすると、初回ビルドで接続エラーになる。必ず完了を待つ。

### Step 3: Vercel 接続 & デプロイ

`vercel-connect-and-deploy` スキルを呼び出す。

- `ENV_VARS_JSON` を渡す（構築ルールは後述）。
- Framework Preset は自動検出に任せる（Next.js は自動認識される）。
- ビルド成功を確認し、production URL を取得する。

### Step 4: マイグレーション適用

`supabase_execute_sql` で DDL を実行する。

- テーブル作成、RLS ポリシー、インデックス、初期データを順に適用。
- 各 SQL 文は冪等に書く（`CREATE TABLE IF NOT EXISTS` / `DO $$ ... $$`）。
- 実行順序に依存関係がある場合は明示的に順番を守る。

### Step 5: Auth URL 設定

`supabase-set-auth-url` スキルを呼び出す。

- Vercel の production URL を Supabase Auth の Site URL / Redirect URLs に設定する。
- これを忘れると OAuth コールバックやメールリンクが機能しない。

### Step 6: Stripe 設定

Deploy 拡張の Stripe ツールを使用する（詳細は後述）。

```
1. stripe_create_product_and_price → Product + Price を作成
2. stripe_create_payment_link    → Payment Link を生成
3. stripe_create_webhook         → Webhook endpoint を登録
   - endpoint URL: {production_url}/api/webhook/stripe
   - events: checkout.session.completed, invoice.paid 等
```

- **mode は `"test"` が既定**。本番切替は別途 `switch-to-live-mode` で行う。
- Price ID / Webhook Secret を env に追加して Vercel を再デプロイする。

### Step 7: スモークテスト

`app-smoke-test` スキルを呼び出す。

- Production URL に対して HTTP レベルの動作確認を実施。
- チェック項目例:

| パス | メソッド | 期待ステータス | 備考 |
|---|---|---|---|
| `/` | GET | 200 | トップページ表示 |
| `/api/health` | GET | 200 | ヘルスチェック（実装時） |
| `/api/webhook/stripe` | POST | 400 | Stripe Webhook の署名検証エラー（正常） |

---

## 2. 冪等デプロイ原則

| 原則 | 説明 |
|---|---|
| **正本は GitHub リモート** | ローカルの outputs/ は作業領域。デプロイ後のコード正本は GitHub リポジトリ |
| **Vercel プロジェクトは 1 リポにつき 1 つ** | `vercel_create_project_and_deploy` は 1 リポに対して一度だけ呼ぶ。二度目以降は git push による自動デプロイ |
| **provision → env 収集 → 単一 create** | Supabase / Stripe 等の外部サービスを先にプロビジョニングし、全ての env を揃えてから Vercel プロジェクトを作成する。env 不足での再作成を防ぐ |
| **本番 URL は production alias** | Vercel の production deployment に自動付与される URL（カスタムドメイン設定前は `*.vercel.app`）を本番 URL として扱う |
| **ローカルクローン確立** | デプロイ完了後、`~/projects/<repo-name>` にクローンを配置する。以後の修正は `update-deploy` スキルでこのクローンを起点に行う |

---

## 3. ENV_VARS_JSON 構築ルール

アプリの構成要素に応じて、段階的に env を積み上げる。

### 基本パターン

| 構成 | 環境変数 |
|---|---|
| 静的 HTML | (空 `{}`) |
| Next.js のみ | `NEXT_PUBLIC_APP_URL` |
| + Supabase | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` |
| + Anthropic (Claude API) | `ANTHROPIC_API_KEY` |
| + Stripe | `STRIPE_SECRET_KEY`, `NEXT_PUBLIC_STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET` |

### 組み立て例

```json
{
  "NEXT_PUBLIC_APP_URL": "https://acme-app.vercel.app",
  "NEXT_PUBLIC_SUPABASE_URL": "https://xxxx.supabase.co",
  "NEXT_PUBLIC_SUPABASE_ANON_KEY": "eyJ...",
  "SUPABASE_SERVICE_ROLE_KEY": "eyJ...",
  "STRIPE_SECRET_KEY": "sk_test_...",
  "NEXT_PUBLIC_STRIPE_PRICE_ID": "price_...",
  "STRIPE_WEBHOOK_SECRET": "whsec_..."
}
```

> **注意**: `NEXT_PUBLIC_` プレフィックスの変数はクライアントに露出する。シークレットキーには絶対に付けない。

---

## 4. アプリ特性に応じた追加設定判定表

| 特性 | 追加設定 | 詳細 |
|---|---|---|
| **PDF / Excel 出力** | `vercel.json` に `outputFileTracingIncludes` + `maxDuration` | Serverless Function のファイルトレーシングに `node_modules/**/*.wasm` 等を含め、タイムアウトを延長（30-60秒） |
| **Claude / OpenAI API 呼び出し** | env_vars に API キー追加 + `maxDuration` 延長 | LLM 応答は遅延しやすいため `maxDuration: 60` 以上を推奨 |
| **マルチテナント SaaS** | `supabase-multitenant-rls` スキルを呼び出す | organization_id ベースの RLS ポリシーを全テーブルに適用 |
| **ファイルアップロード** | Supabase Storage バケット作成 + RLS | `supabase_execute_sql` でバケット作成 & アップロード/ダウンロードの RLS ポリシーを設定 |
| **react-konva 等 peer 制約あり** | `installCommand` に `--legacy-peer-deps` | `vercel.json` の `installCommand` を `npm install --legacy-peer-deps` に設定 |

### vercel.json 設定例（PDF 出力 + タイムアウト延長）

```json
{
  "functions": {
    "app/api/**/*.ts": {
      "maxDuration": 60
    }
  },
  "outputFileTracing": true
}
```

### vercel.json 設定例（legacy-peer-deps）

```json
{
  "installCommand": "npm install --legacy-peer-deps"
}
```

---

## 5. Stripe は Deploy 拡張経由

| ルール | 説明 |
|---|---|
| **Deploy 拡張のツールを使う** | `stripe_create_product_and_price`, `stripe_create_payment_link`, `stripe_create_webhook` は全て AI OSI URI Deploy コネクタ経由で呼ぶ |
| **mode:"test" が既定** | 初回デプロイ時は常にテストモードで作成する |
| **Live 切替は明示的** | 本番切替は `switch-to-live-mode` スキルで `confirm_live: true` を渡して実行する。誤切替を防止するため、ユーザーの明示的な確認を必須とする |
| **旧 standalone Stripe MCP は使わない** | 別途接続された Stripe MCP サーバがあっても、デプロイフローでは Deploy 拡張内蔵のツールを使用する。二重管理を避けるため |

---

## 6. 完了レポートテンプレ

デプロイ完了時に以下のフォーマットで報告する。

```
## デプロイ完了レポート

### 基本情報
- アプリ名: {app_name}
- リポジトリ: https://github.com/{owner}/{repo}
- 本番 URL: {production_url}
- ローカルクローン: ~/projects/{repo}

### 外部サービス
- Supabase: {supabase_project_url} ({status})
- Stripe: {mode} モード ({product_name} / {price})

### 環境変数
| 変数名 | 設定済み |
|---|---|
| NEXT_PUBLIC_APP_URL | Yes |
| NEXT_PUBLIC_SUPABASE_URL | Yes |
| NEXT_PUBLIC_SUPABASE_ANON_KEY | Yes |
| SUPABASE_SERVICE_ROLE_KEY | Yes |
| STRIPE_SECRET_KEY | Yes |
| NEXT_PUBLIC_STRIPE_PRICE_ID | Yes |
| STRIPE_WEBHOOK_SECRET | Yes |

### スモークテスト結果
| パス | ステータス | 結果 |
|---|---|---|
| / | 200 | OK |
| /api/health | 200 | OK |
| /api/webhook/stripe | 400 | OK (署名検証) |

### 次のステップ
- [ ] カスタムドメイン設定（必要な場合）
- [ ] Stripe Live モード切替（本番運用開始時）
- [ ] 初期データ投入（必要な場合）
```

> **注意**: レポートにシークレットキーの値そのものを含めない。設定済みかどうか（Yes/No）のみ記載する。
