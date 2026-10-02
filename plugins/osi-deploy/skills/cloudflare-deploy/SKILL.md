---
name: cloudflare-deploy
description: |
  アプリを **Cloudflare にデプロイする** atomic スキル。Workers（静的アセット同梱の
  SPA / SSR / API）を本体に、DB は D1（サーバーレス SQLite）、ストレージは R2、
  セッション/キャッシュは KV を使う「フル Cloudflare 構成」で公開する。
  Git 連携で回したい場合は Pages にも対応。`create-app` の Web-Cloudflare パス
  （Phase 4-W-C）から呼ばれる。単体では「Cloudflare にデプロイして」
  「Workers に上げて」「Cloudflare で公開して」「D1 でアプリ作って」
  「Vercel じゃなく Cloudflare で」「R2 にファイル置きたい」
  「Cloudflare Pages に繋いで」で発動する。
  既存アプリの修正・再デプロイは `update-deploy`、Vercel は
  `vercel-connect-and-deploy`、AWS は `aws-static-deploy` / `tf-state-backend` の役割。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# Cloudflare デプロイ（atomic / 拡張ツール版）

push 済みリポ、またはローカルの scaffold を受け取り、**Cloudflare Workers + D1 + R2 + KV**
で公開する。認証情報は **AI OSI URI Deploy 拡張（v1.20.0 以降）** が保持する
Cloudflare API Token / Account ID を使う。`.env` は読まず、`wrangler login` もしない。
拡張の `cloudflare_*` ツールを呼ぶ。

## Vercel + Supabase 構成との違い（どちらを選ぶか）

| 観点 | Vercel + Supabase | フル Cloudflare（本スキル） |
|---|---|---|
| ホスティング | Vercel（Next.js が最速） | Workers（V8 isolate・コールドスタートほぼ無し） |
| DB | Supabase（Postgres・リレーション強い） | D1（SQLite・軽量。Postgres 機能は無い） |
| 認証 | Supabase Auth が即使える | **自前実装が必要**（下の「認証の扱い」参照） |
| ストレージ | Supabase Storage | R2（**エグレス無料**が最大の利点） |
| 従量課金の当たり | 帯域・関数実行 | リクエスト数・D1 の行読み書き |
| 向く案件 | 認証つき SaaS を早く出す | 静的+API 中心、配信量が多い、コストを抑えたい |

**判断の目安**: 認証つき業務 SaaS を短期で出すなら Vercel + Supabase のままが速い。
LP・メディア・配信量が多いもの・社内ツール・コスト最適化が目的なら Cloudflare。
迷ったら「認証が要るか」で切る。

---

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
|---|---|---|
| 拡張 v1.20.0 以降・Cloudflare Token 入力済み | `cloudflare_health_check` で `token_valid: true` | `setup-deploy-environment` を案内 |
| Account ID が解決できる | 同ツールの `account_id` が 32 桁で返る | 拡張設定「Cloudflare Account ID」を入力 |
| workers.dev サブドメイン登録済み | 同ツールの `workers_dev_subdomain` が値を返す | ダッシュボードの Workers & Pages で一度だけ設定（API 不可） |
| Node 18+ / npm がローカルにある | `wrangler` を npx 経由で使う | Node を入れる |
| GitHub リポ作成済み（推奨） | `gh-create-repo-and-push` の戻り値 | 先に push しておく（Cloudflare 自体は git 不要） |

> **API Token の権限**（足りないと途中で 403 になる）:
> Account 側 — Workers Scripts=Edit / Workers KV Storage=Edit / Workers R2 Storage=Edit /
> D1=Edit / Cloudflare Pages=Edit / Account Settings=Read。
> 独自ドメインを使うなら Zone 側 — Workers Routes=Edit。
> Global API Key は使わない（権限が広すぎる）。

## 実行の絶対ルール

1. **着手前に `cloudflare_health_check`**。`token_valid` と `d1_permission` / `r2_permission` が
   OK になるまで進まない。権限不足を「あとで直す」で進めると Phase 途中で必ず止まる。
2. **操作は拡張ツール経由**。`wrangler login` や対話ログインは絶対に使わない
   （トークンは拡張が env で渡す。ディスクにも残さない）。
3. **`wrangler deploy` を直接叩かない**。`cloudflare_deploy_worker` を使う
   （非同期＋ログ取得＋公開 URL 抽出つき）。
4. **秘密情報は `cloudflare_set_secret`**。`wrangler.jsonc` の `vars` は**平文でリポに入る**
   ので、API キー・トークン類を絶対に書かない。

---

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `repo_dir` | ✅ | `wrangler.jsonc` を置く（置いた）ディレクトリの絶対パス |
| `app_name` | ✅ | Worker 名。`https://<app_name>.<subdomain>.workers.dev` になる |
| `needs_db` | 任意 | D1 を作るか（既定: アプリ定義から判断） |
| `needs_storage` | 任意 | R2 を作るか（画像・PDF・添付があるなら true） |
| `needs_kv` | 任意 | KV を作るか（セッション・レート制限・フラグ） |
| `secrets` | 任意 | `{NAME: value}`。デプロイ後に `cloudflare_set_secret` で投入 |
| `custom_domain` | 任意 | 独自ドメイン。Cloudflare 管理ゾーンであることが前提 |
| `use_pages` | 任意 | Workers ではなく Pages（Git 連携）で運用する場合 true |

---

## ワークフロー

```
0. cloudflare_health_check（token / account_id / subdomain / D1・R2 権限）
1. リソース先出し（順序が重要）
   needs_db      → cloudflare_d1_create      → database_id を得る
   needs_storage → cloudflare_r2_create_bucket
   needs_kv      → cloudflare_kv_create_namespace → id を得る
2. wrangler.jsonc を書く（1 で得た id を埋める。まだ deploy しない）
   → references/wrangler-config.md のテンプレをベースにする
3. cloudflare_deploy_worker({ repo_dir })            ← npm install → build → deploy
4. cloudflare_deploy_status({ repo_dir }) を succeeded/failed まで polling
   failed → log_tail を読んで repo_dir を修正 → 3 に戻る（最大 5 回）
5. cloudflare_enable_workers_dev({ script_name }) → 公開 URL を得る
6. secrets があれば cloudflare_set_secret（値は出力しない・再デプロイ不要）
7. D1 のスキーマ投入
   migrations/ 方式 → cloudflare_wrangler(["d1","migrations","apply",<db>,"--remote"])
   単発 DDL        → cloudflare_d1_query({ database, sql, allow_write: true })
8. custom_domain があれば cloudflare_add_custom_domain
9. app-smoke-test で公開 URL を外部から検証（200 が返るまで完了と言わない）
```

### なぜこの順序か

D1 / KV は **作成してから ID を `wrangler.jsonc` に書く**必要がある。先に deploy すると
バインディング未定義で起動時エラーになり、直して再 deploy する二度手間になる。
Vercel パスの「env を全部揃えてから 1 回だけ create」と同じ思想。

---

## Step 1: リソース先出し

```
cloudflare_d1_create({ name: "<app>-db", primary_location_hint: "apac" })
  → { name, database_id, wrangler_snippet }

cloudflare_r2_create_bucket({ name: "<app>-assets", location_hint: "apac" })
cloudflare_kv_create_namespace({ title: "<app>-sessions" })
```

`primary_location_hint: "apac"` を必ず付ける（日本のユーザー向け。省略すると
最初にアクセスした地域が主リージョンになり、日本から遠くなることがある）。
各ツールは `wrangler_snippet` を返すので、そのまま `wrangler.jsonc` に貼る。

## Step 2: wrangler.jsonc

> テンプレ全文とパターン別の書き方: [references/wrangler-config.md](references/wrangler-config.md)

最小の形（SPA + API + D1）:

```jsonc
{
  "name": "<app-name>",
  "main": "./src/worker.ts",
  "compatibility_date": "<今日の日付 YYYY-MM-DD>",
  "compatibility_flags": ["nodejs_compat"],
  "assets": {
    "directory": "./dist",
    "binding": "ASSETS",
    "not_found_handling": "single-page-application"
  },
  "observability": { "enabled": true },
  "d1_databases": [
    { "binding": "DB", "database_name": "<app>-db", "database_id": "<Step 1 の database_id>" }
  ]
}
```

- `compatibility_date` は**実行時点の日付**を入れる。古い日付のままにしない。
- `vars` に秘密を書かない（リポに平文で入る）。秘密は Step 6。
- `not_found_handling` を `single-page-application` にしないと、SPA のクライアント
  ルーティング（`/dashboard` に直アクセス等）が 404 になる。

## Step 3-4: デプロイと polling

```
cloudflare_deploy_worker({ repo_dir })          // 非同期。すぐ返る
→ cloudflare_deploy_status({ repo_dir })        // state: running / succeeded / failed
```

`state: failed` のときは `step`（install / build / deploy）と `log_tail` を読む。
よくある失敗は下の表。修正したら `cloudflare_deploy_worker` を再実行する（冪等）。

## Step 5-6: 公開と Secret

```
cloudflare_enable_workers_dev({ script_name: "<app-name>" })
  → { url: "https://<app>.<subdomain>.workers.dev" }

cloudflare_set_secret({ script_name, name: "ANTHROPIC_API_KEY", value: "..." })
```

Secret はコード側で `env.ANTHROPIC_API_KEY` として読める。**反映に再デプロイは不要**。
ツールは値を出力に出さない。

## Step 7: D1 スキーマ

migrations 方式（推奨・冪等）:

```
repo_dir/migrations/0001_init.sql を置く
cloudflare_wrangler({ repo_dir, args: ["d1","migrations","apply","<app>-db","--remote"] })
```

`--remote` を忘れるとローカルの SQLite にだけ当たって本番が空のまま、という
「デプロイは成功したのにデータが無い」事故になる。**必ず `--remote`**。

確認は read-only で:

```
cloudflare_d1_query({ database: "<app>-db", sql: "SELECT name FROM sqlite_master WHERE type='table'" })
```

---

## 認証の扱い（Supabase Auth の代替・正直な話）

D1 には Supabase Auth 相当の組み込み認証が無い。案件に応じて選ぶ：

| 案件 | 推奨 | 理由 |
|---|---|---|
| 社内ツール・限定公開 | **Cloudflare Access**（Zero Trust） | アプリ側の実装ゼロ。Google/メールOTP で前段認証。最も速く安全 |
| 一般公開 SaaS | ライブラリでセッション自前実装（D1 + KV） | パスワードハッシュ・セッション・メール送信まで自分の責任範囲になる |
| 認証が主要要件 | **Vercel + Supabase を選ぶ** | Cloudflare に寄せる利点より、認証を自作するコストの方が大きい |

**「フル Cloudflare にしたいが認証も要る」ときは、この表をユーザーに見せて選ばせる。**
黙って自前認証を実装しない（セキュリティ責任の所在が変わるため、必ず合意を取る）。

Cloudflare Access を使う場合はダッシュボード側の設定が主で、本スキルの範囲外。
`cloudflare_api` で Access アプリの作成まで到達できる。

---

## よくある失敗と対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `cloudflare_health_check` で `workers_dev_subdomain: "(未登録)"` | アカウントの workers.dev 名が未設定 | ダッシュボード Workers & Pages で一度だけ登録。**API では設定できない** |
| deploy で `Authentication error [code: 10000]` | Token の権限不足 | Workers Scripts=Edit を確認。D1/R2 も個別に Edit が必要 |
| `binding DB not found` / `env.DB is undefined` | `wrangler.jsonc` の `database_id` 未記入 or typo | Step 1 の `wrangler_snippet` を貼り直して再 deploy |
| 公開 URL が 404 | `assets.directory` がビルド出力と不一致 | `dist` / `build` / `.output/public` のどれかを実物で確認 |
| SPA の直リンクが 404 | `not_found_handling` 未設定 | `"single-page-application"` を入れる |
| デプロイ成功なのにデータが空 | `d1 migrations apply` に `--remote` が無い | `--remote` を付けて再実行 |
| `nodejs_compat` 関連の import エラー | Node 組込み API を使うライブラリ | `compatibility_flags: ["nodejs_compat"]`。それでも駄目ならブラウザ互換の代替に置換 |
| Next.js が動かない | Workers は Node ランタイムではない | `@opennextjs/cloudflare` を使う（references 参照）。無理なら Vercel パスに戻す判断も可 |
| `npm install` で ERESOLVE | peer dep 衝突 | `build_command` に `npm install --legacy-peer-deps && npm run build` を明示 |

---

## Pages（Git 連携）で運用する場合

`use_pages: true` のとき。push で自動デプロイさせたい・ビルドを Cloudflare 側で
回したいケース向け。

```
cloudflare_pages_create_project({
  name, github_owner, repo_name,
  production_branch: "main",
  build_command: "npm run build",
  destination_dir: "dist"
})
→ cloudflare_pages_deploy({ project_name: name })
→ cloudflare_pages_deployment_status({ project_name: name })  // stage/status を polling
```

初回は GitHub App の許可が必要な場合がある。`cloudflare_pages_create_project` は冪等
（同名があれば再利用）なので、許可後に同じ引数で再実行してよい。

> **Workers と Pages のどちらか**: 新規なら **Workers を既定**にする（Cloudflare 自身が
> Workers への集約を進めており、静的アセットも Workers で扱えるため）。Pages は
> 「ビルドを Cloudflare に任せたい」「既存 Pages 案件」のときだけ。

---

## 完了の定義（DoD）

以下すべてに実際の出力を貼れて初めて「完了」と言う。1 つでも欠けたら
`未検証: ◯◯` と正直に書く。

- [ ] `cloudflare_deploy_status` が `state: succeeded`
- [ ] `cloudflare_enable_workers_dev` が返した URL に外部から HTTP 200（`app-smoke-test`）
- [ ] D1 を使う場合、`cloudflare_d1_query` でテーブルが見えている
- [ ] Secret を使う場合、アプリの該当機能が実際に動いた（キー未設定エラーが出ない）
- [ ] 独自ドメインを設定した場合、そのドメインで 200

`git push` 成功や `wrangler deploy` の完了だけを根拠に「動いています」と報告しない。

---

## 関連スキル

- `create-app` — 新規アプリの入口。Web-Cloudflare パスから本スキルを呼ぶ
- `update-deploy` — デプロイ済みアプリの修正・再デプロイ
- `app-smoke-test` — 公開 URL の外部検証
- `gh-create-repo-and-push` — リポ作成
- `vercel-connect-and-deploy` / `aws-static-deploy` — 別プラットフォームの同等スキル
