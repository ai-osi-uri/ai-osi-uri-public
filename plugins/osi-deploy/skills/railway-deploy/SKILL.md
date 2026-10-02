---
name: railway-deploy
description: |
  アプリを **Railway にデプロイする** atomic スキル。GitHub リポジトリ（または Docker
  イメージ）からサービスを作り、Railway 側の自動ビルドで公開する。常駐サーバー
  （Express / FastAPI / Rails / Go など）、WebSocket、バックグラウンドワーカー、cron、
  Dockerfile のあるアプリ、Postgres / MySQL / Redis / Mongo を同じプロジェクトで
  まとめて動かしたいときに使う。`create-app` の Web-Railway パス（Phase 4-W-R）から
  呼ばれる。単体では「Railway にデプロイして」「Railway で公開して」「Railway に上げて」
  「Railway に Postgres を足して」「バックエンドを Railway で動かして」
  「Docker のまま動かしたい」「常駐サーバーを置きたい」で発動する。
  既存アプリの修正・再デプロイは `update-deploy`、Vercel は `vercel-connect-and-deploy`、
  Cloudflare は `cloudflare-deploy`、AWS は `aws-static-deploy` / `tf-state-backend` の役割。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# Railway デプロイ（atomic / 拡張ツール版）

push 済みの GitHub リポジトリ（または Docker イメージ）を受け取り、**Railway** で公開する。
認証情報は **AI OSI URI Deploy 拡張（v1.35.0 以降）** が保持する Railway API Token を使う。
`.env` は読まず、`railway login` も CLI もしない。拡張の `railway_*` ツールだけで完結する。

## どんなときに Railway を選ぶか

| 観点 | Vercel + Supabase | Cloudflare | Railway（本スキル） |
|---|---|---|---|
| 実行モデル | サーバーレス関数 | V8 isolate | **常駐コンテナ**（プロセスが動き続ける） |
| 向く言語 | Next.js / Node | JS / TS（Workers 互換） | **何でも**（Node / Python / Go / Ruby / Java / Dockerfile） |
| DB | Supabase（Postgres + Auth + RLS） | D1（SQLite） | Postgres / MySQL / Redis / Mongo をワンクリック |
| 得意 | 認証つき SaaS を早く出す | 静的 + 軽い API・配信量 | WebSocket・ジョブ・cron・重い処理・既存のサーバーアプリ |
| 注意 | 長時間処理・常時接続に弱い | Node API 互換に制約 | **常駐のぶん使った分だけ課金**。スリープ設定で抑える |

**判断の目安**: 「関数で書けない（常時接続・キュー処理・長い処理・Python サーバー・
Dockerfile 前提）」なら Railway。フロントは Vercel に置き、バックエンドだけ Railway に
置く併用も普通にある。**認証は Railway に無い**ので、ログインが要るなら Supabase Auth を
併用するか、アプリで実装する（Phase 3 で必ず合意を取る）。

## 前提（着手前に必ず）

1. `health_check` の `railway.valid: true`（拡張 v1.35.0 以降が必要）
2. `railway_health_check` で `valid: true`、作成先にするワークスペースが一覧に出ることを確認
   - アカウントトークンなら全ワークスペースが出る。ワークスペーストークンならそのワークスペースだけ
   - 未設定・無効 → `setup-deploy-environment` を案内して中断。**推測で進めない**
3. GitHub リポジトリからデプロイするなら、**Railway の GitHub App** がそのリポジトリに
   アクセスできること（https://github.com/apps/railway-app/installations/new）。
   org リポなら org 側でインストール・許可が要る。`railway_create_service` が
   権限エラーを返したらこれを案内する

## 手順

### Step 1: プロジェクト

既存を使うなら `railway_list_projects` で ID を取る。新規なら:

```
railway_create_project { name: "<app-name>", workspace_id: "<ws>" }
```

返る `project.id` と `environments`（既定は production）を控える。

### Step 2: データベース（要るときだけ）

```
railway_add_database { project_id, kind: "postgres" }   # mysql / redis / mongo も可
```

起動まで 1〜2 分。サービス名（例: `Postgres`）と `connect_hint` を控える。

### Step 3: アプリのサービス

```
railway_create_service {
  project_id, repo: "<owner>/<repo>", branch: "main",
  variables: { DATABASE_URL: "${{Postgres.DATABASE_URL}}", NODE_ENV: "production" },
  start_command: "npm start",          # 自動検出で足りるなら省略
  healthcheck_path: "/health"          # あれば。デプロイ切替の安全性が上がる
}
```

- ソースが繋がった時点で Railway がビルド・デプロイを始める（ビルダーは既定の Railpack が
  言語を自動判定。Dockerfile があればそれを使う）
- **アプリは `PORT` 環境変数で待ち受ける**こと（Railway が注入する）。固定ポートで
  listen していると公開 URL に繋がらない
- モノレポは `root_directory: "/apps/api"`
- DB の参照は `${{<DBサービス名>.<変数名>}}`。同じプロジェクト内は private network
  （`<サービス名>.railway.internal`）で繋がるので、DB を公開する必要はない
- マイグレーションは `pre_deploy_command`（例: `npx prisma migrate deploy`）で毎回流す
  （`railway_update_service`）
- 設定を作成後に入れた場合は `railway_deploy` を1回呼んで確実に反映させる

### Step 4: 公開 URL

Railway は**既定では外部公開しない**。

```
railway_create_domain { service_id }                              # *.up.railway.app を発行
railway_create_domain { service_id, custom_domain: "app.example.com" }   # 独自ドメイン
```

独自ドメインは返ってきた `dns_records` を DNS に設定する（Route53 なら `aws-route53`）。
証明書は Railway が自動発行する。

### Step 5: 確認

```
railway_deployment_status { service_id }
```

- `QUEUED / BUILDING / DEPLOYING` → 数十秒おいて再確認（ビルドは通常 1〜5 分）
- `SUCCESS` → URL を `app-smoke-test` に渡す
- `FAILED / CRASHED` → ログ末尾が自動で付く。典型原因:

| 症状 | 原因 | 直し方 |
|---|---|---|
| ビルドは通るが CRASHED | 起動コマンド違い / 必須の環境変数が無い | `start_command` を直す、`railway_list_variables` で名前を確認 |
| SUCCESS なのに 502 | `PORT` で listen していない / ポート違い | アプリを `process.env.PORT` に、または `target_port` を指定してドメインを作り直す |
| ヘルスチェックで失敗 | `healthcheck_path` が 200 を返さない | パスを直すか外す |
| DB に繋がらない | 参照名の大文字小文字違い / DB 起動前 | `${{Postgres.DATABASE_URL}}` の表記を確認、DB の起動後に `railway_deploy` |
| リポジトリにアクセスできない | Railway GitHub App 未許可 | 前提 3 を案内 |

詳細ログは `railway_get_logs { deployment_id, kind: "build" | "deploy", filter: "@level:error" }`。

## 運用操作

| やりたいこと | ツール |
|---|---|
| 再デプロイ（同じソース） | `railway_deployment_action { action: "redeploy" }` |
| 再起動のみ | `railway_deployment_action { action: "restart" }` |
| 前のデプロイに戻す | `railway_list_deployments` → `railway_deployment_action { action: "rollback", confirm: true }` |
| 環境変数の変更 | `railway_set_variables`（変更で自動再デプロイ。止めるなら `skip_deploys: true`） |
| コストを抑える | `railway_update_service { sleep_application: true }`（アクセスが無いと停止） |
| ここに無い操作 | `railway_graphql`（ボリューム・環境の複製・PR 環境など） |

## 安全ルール

- 削除（`railway_delete_service` / `railway_delete_project`）、`rollback` / `stop` / `cancel`、
  変数の `replace: true` は **ユーザーの明示の指示があるときだけ** `confirm: true` で実行する
- 環境変数の値はチャットに出さない。`railway_list_variables` は既定で名前のみ。
  値の確認が本当に必要なときだけ `show_values: true`
- シークレットの値はユーザーにチャットへ貼らせない。Railway ダッシュボードで直接
  入れてもらうか、DB の参照（`${{Postgres.DATABASE_URL}}`）のように値を書かずに済む形で渡す

## 完了時に返すもの

- 公開 URL（Railway ドメイン / 独自ドメイン）
- プロジェクトのダッシュボード URL（`https://railway.com/project/<project_id>`）
- 作ったサービスと DB の一覧、設定した環境変数の**名前**
- 未完了があれば（DNS 反映待ち・GitHub App 未許可など）その旨と次の手順
