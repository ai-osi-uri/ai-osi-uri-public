---
name: vercel-connect-and-deploy
description: 既に GitHub に push 済みのリポジトリを Vercel に接続し、環境変数を設定して初回本番デプロイを実行する atomic スキル。認証は AI OSI URI Deploy 拡張が保持する Vercel Token / GitHub PAT を使い、`.env` は読まない。拡張の MCP ツール `vercel_create_project_and_deploy`（作成+env+デプロイ起動。既定で Deployment Protection を解除し認証なしで公開）、`vercel_get_deployment_status`（polling）、`vercel_get_build_logs`（失敗調査）、`github_push`（修正コミットの再push）を組み合わせ、ビルド失敗の自動修正ループ（最大5回）まで行う。「Vercel にデプロイして」「リポジトリを Vercel に接続」「Next.js を Vercel に上げて」などで発動。Vercel Token の入力は拡張設定の役割。
version: 0.3.0
---

# Vercel 接続 + env + 初回デプロイ（atomic / 拡張ツール版）

push 済みリポを受け取り、Vercel プロジェクト作成・env 流し込み・初回本番デプロイを行う。
**認証情報は AI OSI URI Deploy 拡張**が保持する Vercel Token / GitHub PAT を使う。`.env` は
読まず、拡張の MCP ツールを呼ぶ。

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| 拡張が有効・Vercel Token 入力済み | `health_check` で `vercel.valid: true` | `setup-deploy-environment` を案内 |
| GitHub リポ作成済み | `repo_id` が `gh-create-repo-and-push` から渡る | 先に `github_create_repo_and_push` を実行 |

## 入力契約（= ツール引数）

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `repo_name` | ✅ | GitHub リポジトリ名（owner なし） |
| `repo_id` | ✅ | GitHub 数値リポ ID（`github_create_repo_and_push` の戻り値） |
| `repo_owner` | 任意 | owner（Org slug or username）。未指定は GitHub ユーザー名 |
| `project_name` | 任意 | Vercel プロジェクト名（デフォルト `repo_name`） |
| `framework` | 任意 | `nextjs` / `vite` / `other` / null |
| `env_vars` | 任意 | `[{key,value,target?,type?}]`。アプリ固有の環境変数 |
| `include_anthropic_key` | 任意 | 拡張に保存した `ANTHROPIC_API_KEY` を自動注入（デフォルト true）。不要なら false |
| `disable_protection` | 任意 | 作成直後に Vercel Authentication(Deployment Protection) を解除し認証なしで公開にする（デフォルト true）。社内検証専用に保護を残すなら false |
| `work_dir` | 任意 | ビルド修正の再 push 用（`github_create_repo_and_push` の戻り値） |

## ワークフロー

```
1. vercel_create_project_and_deploy で作成+env+デプロイ起動（既定で保護を解除＝公開）
   - needs_github_app_grant が返ったら許可 URL を提示 → ユーザー許可後に再実行
   - 戻り値 protection_disabled:false / protection_warning が返ったら、保護が残っている旨を
     ユーザーに伝える（Vercel の Settings → Deployment Protection で確認）
2. vercel_get_deployment_status を READY/ERROR になるまで polling
3. ERROR/CANCELED なら vercel_get_build_logs でログ取得
   → work_dir のコードを修正 → github_push で再 push
   → Vercel が自動再デプロイするので新しい deployment_id を取得して再 polling
   → 最大 5 回。超えたら最後のログを提示して中断
4. READY なら app_url を返す。外部から認証なしで開けることを web_fetch で1回検証
   （本文が返れば公開成功。空で返れば保護が残っているので確認）
```

### Step 1: 作成 + デプロイ起動

```
vercel_create_project_and_deploy({
  repo_name, repo_id, repo_owner,
  framework: "nextjs",
  env_vars: [ /* アプリ固有 */ ],
  include_anthropic_key: true,
  disable_protection: true   // 既定 true。認証なしで公開。社内検証専用に守るなら false
})
```

戻り：`project_id` / `deployment_id` / `app_url` / `anthropic_key_injected` / `protection_disabled`。
`needs_github_app_grant: true` が返ったら、出力の URL（`https://github.com/apps/vercel/installations/select_target`）を
ユーザーに提示し、対象リポへのアクセス許可後に同じツールを再実行する。

### Step 2-4: polling と自動修正ループ

```
ループ（最大5回）:
  status = vercel_get_deployment_status({ deployment_id })
  READY → 完了
  ERROR/CANCELED →
    logs = vercel_get_build_logs({ deployment_id })
    （よくある型エラー等を work_dir で修正）
    github_push({ work_dir, repo_name, repo_owner, commit_message: "fix: build error" })
    sleep 後、新 deployment_id を vercel_get_deployment_status / 一覧で取得して再 polling
```

## よくあるビルドエラーと自動修正

`vercel_get_build_logs` が返したログから次のパターンを検出して `work_dir` を修正、
`github_push` で再 push する。

| エラー | 原因 | 自動修正 |
|---|---|---|
| `Type error: Parameter 'cookiesToSet' implicitly has an 'any' type` | `@supabase/ssr` の `setAll` 型注釈なし | `import { CookieOptions } from '@supabase/ssr'`、`(cookiesToSet: { name: string; value: string; options?: CookieOptions }[])` に明示 |
| `npm error ERESOLVE` / `peer dependency` | `react-konva@19` 等が React 19+ 要求、本体は React 18 | `vercel.json` に `"installCommand": "npm install --legacy-peer-deps"`、または `package.json` で v18 系（`react-konva@^18.2.10`）にピン |
| `Module not found: assets/...` / `public/fonts/...` | `prebuild` フックは Vercel の `next build` 直叩きで走らない | `vercel.json` の `"buildCommand": "node scripts/fetch-asset.mjs && next build"` を置く |
| `Function exceeded the maximum execution time` / 30s 前後で 504 | サーバレス関数の既定タイムアウト | 該当 `route.ts` に `export const maxDuration = 60`。重い処理はビルド時に前倒し |
| `Embedded font file may be invalid`（PDF が Chrome で空白） | OTF (CFF) を埋め込み／variable TTF を `subset:true` | variable TTF を `subset:false` で。詳細は `nextjs-pdf-export` スキル |
| `Failed to compile` で詳細不明 | 個別調査 | ログを subagent に渡して修正 |

## アプリ特性に応じた追加設定

`env_vars` だけでは足りないケース：

| 機能 | 必要な追加 | 詳細 |
|---|---|---|
| **PDF 出力**（pdf-lib + 日本語） | `vercel.json` の `buildCommand`、`next.config.mjs` の `outputFileTracingIncludes`、route に `maxDuration = 60` | 詳細テンプレ：`nextjs-pdf-export` スキル |
| **重いライブラリ依存**（pdfjs-dist, react-konva 等） | `vercel.json` に `installCommand: "npm install --legacy-peer-deps"` | peer dep 衝突を吸収 |
| **長時間 AI 推論**（Claude/OpenAI） | route に `maxDuration = 60` | env_vars の `ANTHROPIC_API_KEY` は `include_anthropic_key: true` で自動注入 |
| **マルチテナント SaaS の RLS** | アプリ実装側で `getMyTenantId()` ヘルパ統一、Supabase は `current_tenant_id()` を SECURITY DEFINER | 詳細：`supabase-multitenant-rls` スキル |

## ビルド時の静的資産バンドル（簡易版）

PDF フォント・OCR モデル・辞書ファイル等を関数バンドルに含めたいときの最小構成：

1. `scripts/fetch-font.mjs` 等の取得スクリプトをリポに置く
2. `vercel.json` で `buildCommand` を `node scripts/fetch-font.mjs && next build` に上書き
3. `next.config.mjs` に `experimental.outputFileTracingIncludes: { '/api/<route>': ['./assets/**'] }`
4. route.ts で `fs.readFile(path.join(process.cwd(), 'assets', '...'))` で読込

詳細は `nextjs-pdf-export` スキル参照。

---

## 戻り値

`project_id` / `deployment_id` / `app_url`。`app_url` は `supabase_set_auth_url` や
スモークテスト、Stripe Webhook の url 設定で使う。

## 注意事項

- `gitSource.repoId` は数値（ツールが処理）。
- Hobby プランは商用制限あり。本番販売段階では Pro へ。
- env を後から足す場合は再デプロイが必要（現状は作成時 env 同梱）。
- `disable_protection`（既定 true）で本番・プレビュー両方が公開になる。社内検証だけ守りたい
  場合は `disable_protection: false` にして、Protection Bypass for Automation トークン運用にする。
- ユーザーに Vercel ダッシュボードを触らせない運用前提（当社課金・管理画面のみ提供）のため、
  保護解除はこのツール内で自動化する（手動トグルは不要）。
