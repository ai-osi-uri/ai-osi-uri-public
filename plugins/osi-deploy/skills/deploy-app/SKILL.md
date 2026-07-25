---
name: deploy-app
description: >
  ⚠️ 非推奨 — `create-app` に統合されました。「アプリ作って」等の発話は create-app が処理します。
  Desktop（Electron）・Mobile・ローカル出力は create-app にのみ対応。
  互換性のため残していますが、新しい機能は create-app に追加されます。
version: 0.6.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
  - server: aws-api
    provision: user-install
  - server: slack
    provision: user-install
---

> ⚠️ **このスキルは非推奨です。`create-app` に統合されました。**
> Desktop（Electron）・Mobile（iOS/Android）・ローカル出力パスは `create-app` にのみ対応しています。
> このスキルが発動した場合は `create-app` の手順に従ってください。
>
> Web パス（Vercel / AWS）の既存手順は下記にそのまま残しています。

---


# deploy-app v4.0 — 汎用アプリ作成エントリポイント（Web / AWS / Desktop）

「アプリ作って」と言われたら、業種・規模に関わらず要件を聞き出して、Vercel・AWS・Desktop（Electron）で公開するところまで 1 つの対話で完結させる。

> **AWS パスで着手する前に必ず参照**：[references/aws-app-gotchas.md](references/aws-app-gotchas.md)
> — 最小構成テンプレ（S3+CloudFront+Lambda+API Gateway+DynamoDB+Bedrock）と、
> このアカウント固有の罠（公開 Function URL は SCP 禁止 → API Gateway、`$default` の
> CORS は Lambda 側で処理、source_arn はアカウント ID 込み、terraform は arm64、
> Bedrock は use case フォーム提出が前提、format はマジックバイト判定）。
> コロワイド 2 アプリで確立。同じ罠で時間を溶かさない。

---

## 作成先の決定ルール（最優先・all-or-personal）

アプリ作成前に必ず「org 利用可否」をプリフライト判定し、その結果を全リソースへ一貫適用する。
**org と個人を混在させない**（例: git だけ org・Supabase は個人、は禁止）。

- 判定 `USE_ORG = (github_org_ok && vercel_team_ok && supabase_org_ok)`
  - `github_org_ok`: PAT が Org `ai-osi-uri` にリポ作成できる（403 / org 未所属なら false）
  - `vercel_team_ok`: Vercel の `ai-osi-uri` スコープ/Team がトークンで使える
  - `supabase_org_ok`: `supabase_list_organizations` に会社 org `zsarvxuigtcmrmoewarw`
    （"shared@ai-osi-uri.com's Org"）がある
- **USE_ORG が真（3つ全部OK）** → 全リソースを org 配下に作る
  - GitHub owner=`ai-osi-uri` ／ Vercel scope=`ai-osi-uri` ／ Supabase org=`zsarvxuigtcmrmoewarw`
- **USE_ORG が偽（1つでも欠ける）** → 全リソースを個人アカウント配下に作る
  - GitHub owner=`personal` ／ Vercel=個人スコープ ／ Supabase=個人 org
- 判定結果（USE_ORG と各 slug）を atomic に明示的に渡す。作成・更新は deploy-app /
  update-deploy 経由のみ（手作業で個人配下に作らない）。

---

## 実行の絶対ルール（コネクタ必須・拡張ロード確認）★フレッシュ環境の詰まり防止

1. **着手前に拡張のロードを確認する。** `health_check` を呼び、AI OSI URI Deploy の
   ツール（`github_*` / `vercel_*` / `supabase_*`）が**実際に呼べる**かを見る。
   - ツールが見つからない／呼べない → 拡張が未ロード。**次の2点をユーザーにそのまま提示**して
     いったん停止する（ループしない・見切り発車しない）:
     1. **再起動していない（最有力）** — mcpb 拡張はインストール／key 入力だけでは有効化されず、
        Claude を完全終了→再起動して初めてサーバが起動する。今のウィンドウのままだとずっと
        「起動できない／ツールが無い」状態。**×で閉じるのは再起動ではない**。画面左上の
        「Claude」→「Claude を終了」→もう一度起動が必要。
     2. **拡張がまだ「無効」** — インストール済みでもトグルが OFF のことがある。
        設定 → 拡張機能 で該当拡張が**有効(オン)**か確認する。
     案内後の手順：①拡張を有効化 → ②Claude を完全終了して再起動 → ③新しいチャットで
     もう一度お願いします、で再確認する。
   - トークンが `valid:false` → `setup-deploy-environment`（該当トークン入力）へ案内して停止。
   - この確認が通るまで実ビルドに進まない（**ループしない・見切り発車しない**）。
2. **コネクタが使えるなら、git / Vercel / Supabase の操作は必ず AI OSI URI Deploy の
   ツールで行う。手動の `npm` / `gh` / `vercel` / `supabase` CLI にフォールバックしない。**
   コネクタ経由で失敗したら、手で作り直さず**失敗の原因（ツールの戻り値）を提示して止まる**。
   （手動フォールバックが「コネクター経由で実行できません」の無限ループと二重作成の元凶。）

---

## 設計原則

1. **Single entry point**: ユーザーは「アプリ作って」と言うだけ。Tier / Phase /
   atomic を意識させない
2. **業種非依存**: 花屋・飲食店・学習塾・医療・不動産・EC・社内 DX — どんな業種
   でも同じフローが動く
3. **入力の粒度に頑健**: 詳細な仕様が来ても、「○○屋向け××」だけの一言依頼が来ても、
   両方に対応する
4. **明確な順序 (AWS パス)**: アプリ定義 → インフラ判断 → インフラ → アプリ+CI。
   `/bootstrap-project` のアプリ先・インフラ後とは異なる
5. **責務分離**: 本スキルは判定・順序制御・引き渡し・監視に専念。実ビルドは
   atomic / `/setup-infra` / `/create-app` に委譲
6. **既存資産活用**: 軽量パスは `gh-create-repo-and-push` / `vercel-connect-and-deploy`
   / `supabase-set-auth-url` / `aws-static-deploy` を使う

---

## 冪等デプロイとローカルクローン正本（最重要・必須）

> 経緯: 実デプロイで Vercel プロジェクトが重複作成された（env 無しで初回 create → 後から
> env を足そうと再 create → 名前衝突で `-002` が自動採番）。**同じ事故を二度と起こさない**ため、
> 以下を体裁・速度より優先する。設計の詳細は
> [docs/deploy-app-local-clone-and-idempotency.md](../../../../docs/deploy-app-local-clone-and-idempotency.md)。

### 原則
1. **正本は GitHub リモート。ローカルクローンは"そのマシンの作業コピー"**。誰でも clone し直せる。
2. **Vercel プロジェクトは 1 リポにつき 1 つ。create は一度きり**。以降の更新は git push＝CI 自動デプロイ。
3. **provision → env 収集 → 単一 create**。Supabase/Stripe を先に作り env を全部そろえてから Vercel を 1 回だけ作る。
4. **本番URLは production alias（`<project>-<team>.vercel.app`）**。per-deploy 固定URLを正本にしない。

### 冪等ガード（Vercel パスで create する前に必ず）
- 「この repo に紐づく既存 Vercel プロジェクトが在るか」を確認する。**在れば `vercel_create_project_and_deploy` を絶対に再実行しない**（名前衝突で別プロジェクトが増殖する）。
- 既存があるのに env を変えたい場合は、create ではなく「git push（CI 自動デプロイ）＋ env はダッシュボード/CLI/将来の `vercel_set_env`」で対応する。
- ⚠️ 現状、拡張に「既存プロジェクトへ env 後付け」「プロジェクト削除」ツールは無い。よって **初回 create に env を全部入れる**ことが唯一の安全策。env が未確定なうちは create しない。

### ローカルクローン確立（repo 作成直後）
- 既定の配置は `~/projects/<repo-name>`。以下のガードを必ず通す:
  - (a) 正本は GitHub リモートと明記。クローンは作業コピー（壊れても再 clone で復旧）。
  - (b) Cowork では `~/projects` が**接続（マウント）済み＆書込可能**かを確認。未接続なら接続を促すか接続済みフォルダを選ばせる。
  - (c) 配置は上書き可能（`OSI_PROJECTS_DIR` 等）。既定は `~/projects`。
  - (d) 同名ディレクトリ衝突をチェックして確認。
- scaffold に `CLAUDE.md` / `DEPLOY.md` を必ず同梱し、「更新は clone→push→CI／再 create 禁止／本番は alias／旧プロジェクトは削除」をリポ自身に自己記述させる。

### 初回デプロイ後の更新
- **全更新は `update-deploy`（clone→編集→github_push→CI 監視→smoke）を既定入口にする**。本スキル（deploy-app）を同じ案件で再実行しない。

---

## ハーネス: 状態ログと「完了の定義」（必須）

deploy-app は複数フェーズ・複数セッションにまたがる長時間タスク（特に AWS パスは
Claude Code への引き渡し → ポーリング → 復帰）。途中でセッションが切れても再開でき、
かつ「実際は動いていないのに完了宣言する（early victory declaration）」事故を防ぐため、
以下を必ず守る。これはこのスキルの最重要ルールであり、体裁や速度より優先する。

### 1. 状態ログ `deploy-progress.md`（フェーズ境界ごとに更新）

最初の実作業（Phase 4 着手）に入る前に `{OUTPUTS}/deploy-progress.md` を作成し、
各フェーズの完了時に更新する。AWS パスで Drive 案件フォルダがある場合は、同ファイルを
`03.PJT資料/{ID}.{企業名}/03_制作・成果物/` にもミラーする。

```markdown
# Deploy Progress — {PROJECT_NAME}
更新: {YYYY-MM-DD HH:MM}

## 確定事項
- ホスティング: {Vercel|AWS}
- リポジトリ: {REPO_URL or 未作成}
- 構成: {Supabase/Stripe/Anthropic 有無}

## 完了（evidence 付き）
- [x] Phase 0 認証確認 — evidence: health_check の valid 一覧
- [x] Phase 1 アプリ定義

## 進行中
- [ ] Phase 4-V デプロイ（現在: vercel build 監視中）

## ブロック中 / 要確認
- （なし / 例: Stripe live 切替はユーザー承認待ち）

## 次セッションでの再開手順
- {具体的な次の1手}
```

**セッション開始時にこのファイルが既にあれば必ず先に読み**、途中から再開する。
記憶ではなくこのファイルを唯一の進捗の正典（system of record）とする。

### 2. 完了の定義（DoD）— 証拠なしに「完了」と言わない

Phase 5-V / Phase 7-A の完了レポートを出してよいのは、**下の検証チェックリストの
全項目に実際の出力（evidence）を貼れたときだけ**。未検証の項目が1つでも残るなら
「完了」と書かず、`未検証: ◯◯` と正直に明記する。READY 状態や `git push` 成功だけを
根拠に「直りました／動いています」と顧客に伝えない。

### 3. 検証コマンド（このスキルの正典チェック）

| 対象 | コマンド / 確認 | 合格条件 |
|---|---|---|
| Vercel: コミット一致 | Vercel API の `meta.githubCommitSha` と `git rev-parse HEAD` | 一致 |
| Vercel: 公開URL実体 | `curl -sf {APP_URL}` の中身を grep | 期待文字列が出る（旧キャッシュでない） |
| Supabase 結合 | `app-smoke-test` の PostgREST probe | `PGRST200` が出ない |
| Stripe webhook | `app-smoke-test` で webhook に無署名 POST | 400 が返る |
| AWS API | `curl -i https://{ALB_DNS}/health` | 200 |
| マルチテナント | 2人目ユーザーで他テナント不可視 | 他テナントデータ 0 件 |
| **Drive 記録** | `{案件}/{アプリ名}/アプリ情報_README.md` 生成 + `_アプリ台帳.md` 追記 | 両ファイルがドライブに存在し公開URLが記載 |
| Desktop: GH Actions 成功 | GitHub API で workflow run の `conclusion` | `success`（全 matrix job） |
| Desktop: Release asset 存在 | GitHub API で release の `assets` 配列 | 対象 OS 分の asset が存在 |

検証の実行は `app-smoke-test` に委譲してよいが、**結果（evidence）は必ず
`deploy-progress.md` の「完了」欄に貼る**。検証していない項目を完了扱いにしない。

---

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| `AI OSI URI Deploy` 拡張が有効 | `health_check` ツールで各トークン `valid` | `setup-deploy-environment`（拡張導入）を案内 |
| Vercel パス: Vercel Token 入力済み | `health_check` の `vercel.valid` | 拡張設定で Vercel Token 入力 |
| AWS パス: `AWS_PROFILE` + ローカルに `claude` CLI | MCP or 環境変数 + `which claude` | 案内して中断 |
| Stripe ありの場合 | Stripe MCP 接続済み | レジストリ案内 |
| Supabase ありの場合 | `health_check` の `supabase.valid: true`（PAT入力済み） | `setup-deploy-environment` を案内。プロジェクト・キーはユーザーに聞かず、下記「Supabase プロビジョニング」節の手順でClaudeが用意する（既存プロジェクト再利用の判定精度は #27 参照） |
| Desktop パス: GitHub PAT に `workflow` スコープ | `health_check` の `github.valid` + PAT スコープ確認 | `setup-deploy-environment` を案内。Classic PAT なら `repo` + `workflow` が必要 |
| Desktop パス（署名あり）: Apple Developer ID | ユーザーに確認 | Apple Developer Program ($99/年) の登録を案内 |
| Desktop パス（署名あり）: Windows コード署名証明書 | ユーザーに確認 | Azure Trusted Signing または EV/OV 証明書の取得を案内 |

---

## ワークフロー全体像

```
Phase 0: 認証情報・接続状況の確認
Phase 1: アプリ定義
  Step 1-A: 入力解析 (詳細あり / 一言依頼 / 既存コードあり)
  Step 1-B: ギャップ埋め (一言依頼の場合のみ、targeted 質問 2-3 個)
Phase 2: インフラ判断 (内部判定マトリクス → AWS or Vercel 推奨)
Phase 3: ホスティング選択 + プラン承認

[Vercel パス] (軽量案件)
  Phase 4-V: scaffold 生成 → atomic 連鎖 (gh push → Vercel → Supabase → smoke)
  Phase 4.9-V: ドライブへ接続情報を記録（アプリ情報README + 台帳追記）★必須ゲート
  Phase 5-V: 完了レポート

[AWS パス] (エンタープライズ)
  Phase 4-A: インフラ構築 (spec.md+infra-decision.md 生成 → Claude Code 引き渡し
             → /initialize-project → /setup-infra → 完了監視)
  Phase 5-A: アプリ + CI 構築 (/create-app → docker push → ECS 更新 → 監視)
  Phase 6-A: 動作確認 (smoke test + migration)
  Phase 6.9-A: ドライブへ接続情報を記録（アプリ情報README + 台帳追記）★必須ゲート
  Phase 7-A: 完了レポート

[Desktop パス] (デスクトップアプリ)
  Phase 4-D: Electron scaffold 生成 → GH Actions workflow 同梱 → push → CI ビルド監視
  Phase 4.9-D: ドライブへ接続情報を記録（アプリ情報README + 台帳追記）★必須ゲート
  Phase 5-D: 完了レポート（DL リンク付き）
```

---

## Phase 0: 認証情報・接続状況の確認

### Step 0-1: 認証情報は「AI OSI URI Deploy」拡張から取得

本スキルは `.deploy-credentials/.env` を読まない。GitHub / Vercel / Stripe / Supabase /
Anthropic の各トークンは **AI OSI URI Deploy 拡張**（`mcp/ai-osi-uri-deploy`、設定欄に入力 →
OS キーチェーン保存）が保持し、デプロイ操作は拡張の MCP ツール経由で行う。

確認手順：
1. `health_check` ツールを呼ぶ。
2. 使うパスに必要なトークンが揃っているか確認：
   - 全パス: `github.valid: true`
   - Vercel パス: `vercel.valid: true`
   - Stripe 利用時: `stripe.test` / `stripe.live`（使う方）
   - Supabase 利用時: `supabase.valid: true`
   - AI 機能つき: `anthropic.valid: true`
3. 不足していれば `setup-deploy-environment`（拡張インストール＋トークン入力）を案内して中断。

### Step 0-2: 使用する拡張ツール

| ツール（AI OSI URI Deploy 拡張が提供） | 用途 |
|---|---|
| `github_create_repo_and_push` / `github_push` | 新規リポ作成＋push / 既存リポ再push（ビルド修正） |
| `vercel_create_project_and_deploy` / `vercel_get_deployment_status` / `vercel_get_build_logs` | Vercel 作成・本番デプロイ・監視 |
| `supabase_list_organizations` | Organization 一覧取得（`organization_id` 特定） |
| `supabase_create_project` | 新規 Supabase プロジェクト作成（`db_pass` は自動生成） |
| `supabase_get_api_keys` | URL・anon key・service_role key 取得 → `ENV_VARS_JSON` に反映 |
| `supabase_execute_sql` | migration SQL 適用 |
| `supabase_list_projects` / `supabase_set_auth_url` | 既存プロジェクトの確認 / Auth URL 本番反映 |
| `stripe_create_product_and_price` / `stripe_create_payment_link` / `stripe_create_webhook` | Stripe（`mode:"test"` 既定 / `"live"` は `confirm_live:true` 必須） |

- 作成先は「作成先の決定ルール」の `USE_ORG` に従う。真なら `github_create_repo_and_push` に
  `owner_override:"ai-osi-uri"`、偽なら `"personal"` を渡す（3点セットで揃わなければ personal に倒す
  ＝org と個人を混在させない）。403（org 権限なし）は「欠け」として personal 扱いにし、必要なら
  Classic PAT(repo+workflow+read:org) 差し替えを案内。
- Supabase を新規作成する場合、`USE_ORG` が真なら `organization_id:"zsarvxuigtcmrmoewarw"`、
  偽なら個人 org に作る。
- AI 機能つきアプリは `vercel_create_project_and_deploy` が拡張保存の `ANTHROPIC_API_KEY` を
  デプロイ env に自動注入する（`include_anthropic_key:false` で抑止）。

### Step 0-3: AWS 利用判定 (MCP or .env)

AWS パスは AWS_PROFILE in .env でも MCP 経由でも OK。優先順位は MCP > .env:

```
1. 利用可能ツール一覧に mcp__awslabs_aws-api-mcp-server__call_aws があるか確認:
   - あり → AWS パス利用可能、MCP 経由で apply
   - なし → .env の AWS_PROFILE を確認
     - あり → AWS CLI 経由で apply
     - なし → AWS パスは「setup-deploy-environment 再実行で AWS_PROFILE 登録を案内」

2. ユーザーが Phase 3 で AWS パスを選んだとき、上記のいずれの経路もない場合のみ中断
```

### Step 0-4: Phase 1 に進む

ここでは**全クレデンシャルの存在チェックだけ**。実際に使うのは Phase 4 以降なので、
細かいエラーは後でハンドリングする。`health_check` で必要なトークンが揃っていれば
速やかに Phase 1 へ進む。

### 認証情報の扱い（拡張方式）

非 AWS パス（Vercel / Stripe / Supabase / GitHub）では `.env` を一切読まない。トークンは
拡張がキーチェーンに保持し、各 MCP ツールが内部で使う。AWS パスのみ `AWS_PROFILE`（MCP or
環境変数）を従来どおり参照する。

---

## Phase 1: アプリ定義

### Step 1-A: 入力解析

ユーザーの**初発入力**を読んで、以下の 3 つに分類:

| 分類 | 判定基準 | 次のステップ |
|------|---------|-------------|
| **detailed** | 業種 + エンティティ + ロール + 規模 + 機能 のうち 3 つ以上読み取れる | Step 2 (確認のみ) |
| **sparse** | 業種だけ・ジャンルだけ・「○○屋向け××」程度 | Step 1-B (ギャップ埋め) |
| **既存コードあり** | 「~/Desktop/xxx に HTML がある」「フォルダがある」 | Phase 3 (Vercel/AWS-static で軽量パス) |
| **desktop** | 「デスクトップアプリ」「Windows/Mac で動くアプリ」「オフラインで使えるアプリ」等の明示 | Step 1-B (ギャップ埋め) + Desktop パス確定 |
| **わからない** | 何も読み取れない | AskUserQuestion で「どの種別？」を確認 |

### Step 1-B: ギャップ埋め (sparse の場合のみ)

**業種から推測した候補を提示してユーザーに選ばせる**のがコツ。LLM が業種から
妥当な「ロール候補」「エンティティ候補」「規模候補」を生成して、AskUserQuestion で 1-2 個に絞って質問する。

#### sparse 入力の例とギャップ埋めのパターン

##### 例 1: 「花屋の在庫管理アプリ作って」

```
LLM 推測:
  業種: 小売 (花屋)
  推測される利用者: 店員 / 店長 (本部があれば本部管理者も)
  推測される主要エンティティ: 商品(花) / 仕入先 / 入庫履歴 / 出庫履歴 / 廃棄記録
  推測される機能: 在庫数表示 / 入出庫登録 / 賞味期限/品質管理 / 仕入発注

AskUserQuestion (1-2 個に絞る):
  Q: 店舗構成はどの規模ですか?
    - 単店舗 (1 つの店だけ)
    - 数店舗チェーン (3-10 店)
    - 多店舗展開 (10 店以上、本部もある)

  Q: 利用者は何種類ですか?
    - 店員のみ (シンプル)
    - 店員 + 店長 (2 ロール、店長は売上分析が見られる)
    - 店員 + 店長 + 本部管理者 (3 ロール、店舗横断分析あり)
```

##### 例 2: 「飲食店の予約システム作って」

```
LLM 推測:
  業種: 飲食
  推測される利用者: お客さん (予約する人) / 店舗スタッフ
  推測される主要エンティティ: 予約 / 顧客 / 席 / 営業時間 / メニュー
  推測される機能: 予約フォーム / カレンダー / リマインダーメール / キャンセル管理

AskUserQuestion:
  Q: 課金はどうしますか?
    - お客さんは無料 (予約のみ)
    - 事前決済あり (デポジット、コース料金等)

  Q: 店舗側でやることは何ですか?
    - 予約確認のみ (シンプル)
    - 予約管理 + 顧客 CRM (常連管理、メモ等)
    - 予約 + 顧客 + メニュー管理 (フル機能)
```

##### 例 3: 「学習塾の生徒管理アプリ作って」

```
LLM 推測:
  業種: 教育
  推測される利用者: 生徒 / 保護者 / 講師 / 塾長
  推測される主要エンティティ: 生徒 / 保護者 / クラス / 出欠 / 成績 / 連絡

AskUserQuestion:
  Q: 利用者は何種類ですか?
    - 講師のみ (内部利用、シンプル)
    - 講師 + 塾長 (運営側 2 ロール)
    - 講師 + 塾長 + 保護者 (保護者ポータルあり、3 ロール)
    - フル (講師 + 塾長 + 保護者 + 生徒、4 ロール)

  Q: 課金は?
    - 無料 (内部利用のみ)
    - 月謝管理あり (オンライン決済)
```

##### ギャップ埋めの一般原則

- **業種から推測されるエンティティ・ロール候補を最初に LLM が生成**
- **質問は 2-3 個まで**、それ以上聞かず、残りはデフォルト値で進める
- **推測値をユーザーに見せた上で確認**、聞き方は「これですか？修正は？」
- 推測の根拠を 1 行でも書くと精度の体感が上がる

### Step 2: アプリ定義シートを内部で作る

詳細あり / ギャップ埋め後 のどちらも、最終的に以下の項目を確定する:

| 項目 | 抽出例 |
|------|--------|
| PROJECT_NAME | PascalCase (例: FlowerInventory) |
| PROJECT_NAME_LOWER | kebab-case (例: flower-inventory) |
| PROJECT_DESCRIPTION | 1 行説明 (例: 花屋向けの在庫管理アプリ) |
| 業種 | 小売 / 飲食 / 教育 / 医療 / 不動産 / etc. |
| エンティティ | 主要な名詞 3-7 個 |
| ユーザー種別 | 1-4 ロール |
| 主要機能 | 5-10 個 |
| 機密性レベル | 公開可 (LP) / 個人情報あり / 機微情報あり (医療・金融) |
| 想定規模 | 〜50 / 〜500 / 5000+ 人 |
| 課金 | 無料 / 月額 / 一回購入 / 内部利用のみ |
| 配布形態 | Web / Desktop / 両方 |

ユーザーに最終確認:
```
「以下の構成で進めて OK ですか?
- アプリ名: FlowerInventory
- エンティティ: Product (花), Supplier, StockIn, StockOut, DisposalRecord
- 利用者: 店員 / 店長 (2 ロール)
- 機能: 在庫表示、入出庫登録、賞味期限管理、仕入発注
- 規模: PoC (同時 ~50)
- 課金: 内部利用 (なし)

修正したい点があれば言ってください。」
```

---

## Phase 2: インフラ判断 (業種非依存)

Phase 1 で確定したアプリ定義シートから、**インフラ構成**を内部判定する。
ユーザーには「Tier」を見せない。

### 内部判定マトリクス

| 機密性 | 規模 | 課金 | 推奨インフラ |
|--------|------|------|--------------|
| 公開可 (LP/コーポサイト) | 任意 | 任意 | **Vercel** (or AWS 静的) |
| 個人情報あり | 〜50 (PoC) | なし or サブスク | **Vercel + Supabase** |
| 個人情報あり | 〜50 (PoC) | Stripe 課金あり | **Vercel + Supabase + Stripe** |
| 個人情報あり | 〜500 (中規模) | 任意 | **Vercel + Supabase** (まだ十分) |
| 個人情報あり | 5000+ (大規模) | 任意 | **AWS** (project-template) |
| 業務系・在庫等 (内部) | 〜500 | 任意 | **AWS** (project-template) |
| 機微情報 (医療/金融) | 任意 | 任意 | **AWS + 3 省ガイドライン強化** |
| マルチテナント SaaS | 中規模以上 | 課金あり | **AWS** (本格運用) |
| ローカルファイル操作・オフライン必須 | 任意 | 任意 | **Desktop（Electron）** |
| OS ネイティブ連携（トレイ・通知・ショートカット） | 任意 | 任意 | **Desktop（Electron）** |
| ハードウェア連携（USB・シリアル・BLE） | 任意 | 任意 | **Desktop（Electron）** |

### AWS パス判定時のみ詳細確認

AWS パスを判定した場合、以下を確認 (AskUserQuestion):

```
Q1: 規模感
  - PoC (同時 50 / データ 100GB)
  - 中規模 (同時 500 / データ 1TB)
  - 本番 (同時 5000+ / スケール想定)

Q2: ロール構成 (Phase 1 で推測済みなら確認のみ)
  - 1 ロール / 2 ロール / 3 ロール

Q3: コンプライアンス
  - 通常 (個人情報保護法レベル)
  - 機微情報強化 (医療: 3 省ガイドライン / 金融: FISC 安対基準)

Q4: ドメイン (任せる / 指定)

Q5: 通知メール (CloudWatch アラート用、任意)
```

### Desktop パス判定時の詳細確認

Desktop パスを判定した場合、以下を確認 (AskUserQuestion):

```
Q1: 対象 OS
  - Windows のみ
  - Mac のみ
  - Windows + Mac（推奨）
  - Windows + Mac + Linux

Q2: コード署名
  - 社内ツール / PoC（署名なし = SmartScreen / Gatekeeper 警告あり、無料）
  - 顧客配布 / 製品（署名あり = Apple Developer ID + Windows 証明書が必要）
  - わからない（署名なしで先に進め、後で追加可能）

Q3: 自動更新
  - あり（electron-updater + GitHub Releases、推奨）
  - なし（手動で新バージョンを DL してもらう）
```

---

## Phase 3: ホスティング選択 + プラン承認

Phase 1 (アプリ定義) と Phase 2 (インフラ判断) の結果をプランとして提示。

### プラン提示テンプレ

```
=== 構築プラン ===

【アプリ定義】
  名前: FlowerInventory
  業種: 小売 (花屋)
  概要: 花屋向けの在庫管理アプリ
  エンティティ: Product / Supplier / StockIn / StockOut / DisposalRecord
  利用者: 2 ロール (店員 / 店長)
  機密性: 個人情報あり (顧客情報なし、社内利用主)

【インフラ構成 (推奨)】
  → Vercel + Supabase

  - フロントエンド: Next.js (React + MUI 想定)
  - 認証: Supabase Auth (2 ロール: staff / manager)
  - DB: Supabase PostgreSQL
  - デプロイ: Vercel (Hobby or Pro)

【月額見積もり】
  - 開発初期: 無料 (Vercel Hobby + Supabase Free)
  - 本番運用: USD 20-30 (Vercel Pro + Supabase Pro)

【ホスティング先選択】
  - [推奨] Vercel
  - AWS で立てたい (将来のスケールや業務系を見据えて)
  - LP のみ静的サイトとして AWS S3+CloudFront に置く
  - デスクトップアプリ (Electron, GitHub Actions でビルド → GitHub Releases で配布)

このプランで進めますか?
  [はい、Vercel で進める]
  [AWS に変更]
  [Desktop で進める]
  [プランを修正したい]
```

### 軽量パスの 3 択 (Phase 1 で「既存コード」or「LP」)

既存コードあり / LP の場合は Phase 2 をスキップして以下を直接提示:

```
Q: どこにデプロイしますか?
  - Vercel (推奨、Hobby なら無料)
  - AWS S3 + CloudFront (静的サイト、カスタムドメイン重視)
  - 任せる (内容から判定)
```

---

## Phase 4-V: Vercel パスの実行

```
Step 1: フロントエンドの scaffold 確認
  - 既存コードあり: そのまま使う
  - 新規: Next.js (default) で生成
    npm create next-app@latest (or pnpm create) でテンプレート展開
    Phase 1 のエンティティに沿った API routes / pages を仮実装
  - LP: HTML 1 枚ならそのまま、複数なら index.html + pages/

Step 2: gh-create-repo-and-push を呼ぶ（owner_override は USE_ORG に従い "ai-osi-uri" / "personal"）
Step 2.5: (Supabase あり) Supabase をプロビジョニング（下の「Supabase プロビジョニング」参照）。
          既存 project を使うか、無ければ作成→provision 完了まで待って URL/anon/service_role を取得。
          idempotency 原則で、env が揃ってから Vercel を作る。
Step 3: vercel-connect-and-deploy を呼ぶ（repo_owner は USE_ORG に従い "ai-osi-uri" / 個人、ENV_VARS_JSON 込み）
Step 4: (Supabase あり) migration を supabase_execute_sql で適用（手動 SQL editor に頼らない）
Step 5: (Supabase あり) supabase-set-auth-url（app_url を Auth に反映）
Step 6: (Stripe あり、Phase 2 以降) stripe-create-product → vercel-set-env → vercel-redeploy
Step 7: app-smoke-test
Step 8: (任意) slack-notify
```

### Supabase プロビジョニング（新規ユーザーで必ず通す手順）

「Supabase プロジェクト設定できない」の恒久対応。**個人ダッシュボードでの手作業に頼らず、
AI OSI URI Deploy のツールで完結**させる。空の Supabase を持つ新規ユーザーでも詰まらない。

> **静的サイト / LP はこの手順を丸ごとスキップ**（GitHub + Vercel のみで一発完結・Supabase PAT 不要）。
> DB・ログイン・保存・会員・予約など**データを保存する必要があるアプリのときだけ**本手順を通す。

1. `supabase_list_projects` で使える既存 project（`status=ACTIVE_HEALTHY`）を確認。あれば
   その `ref` を再利用（重複作成しない）。
2. 無ければ作成：
   - `supabase_list_organizations` で org を取得。`USE_ORG` が真なら会社 org
     `zsarvxuigtcmrmoewarw`、偽なら本人の org。**org が取れない（PATなし）なら
     `setup-deploy-environment` の Supabase PAT 入力へ案内して停止**（手作業に逃げない）。
   - `supabase_create_project({ name: "<repo>-db", organization_id, db_pass: <強力な乱数>, region: "ap-northeast-1" })`。
     `db_pass` はチャットに出さず生成して控える。
3. **provision 完了待ち（最重要）**：作成直後は使えない。`supabase_list_projects` を
   10〜15 秒間隔でポーリングし、`status` が `ACTIVE_HEALTHY` になるまで待つ（目安 1〜2 分）。
   ここを飛ばして次に進むと接続に失敗する（フレッシュ環境の典型的な詰まり）。
4. `supabase_get_api_keys({ project_ref })` で `URL` / `anon` / `service_role` を取得。
5. これらを **Vercel を作る前に** ENV へ：`NEXT_PUBLIC_SUPABASE_URL` /
   `NEXT_PUBLIC_SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY`。
6. スキーマ（テーブル）は `supabase_execute_sql` で適用（Dashboard の SQL editor 手作業に頼らない）。
   マルチテナントの RLS が要るなら `supabase-multitenant-rls` を参照。
7. デプロイ後、`supabase-set-auth-url` で本番 `app_url` を Auth の Site/Redirect に反映。

### ENV_VARS_JSON 構築ルール

| 構成 | env キー |
|------|----------|
| 静的 HTML | (空) |
| Next.js のみ | `NEXT_PUBLIC_APP_URL` |
| + Supabase | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` |
| + Anthropic | + `ANTHROPIC_API_KEY` |
| + Stripe | + `STRIPE_SECRET_KEY`, `NEXT_PUBLIC_STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET` |

### ロールバック

失敗時は GitHub repo を残し、手動修正手順を案内。

---

### Step 1.5: アプリ特性に応じた追加設定の判定

Phase 1 で確定したエンティティ・機能から、次の表に該当するアプリは追加設定を入れる。
具体的なコードテンプレは `Phase 4-V 補足` および参照スキルにある：

| 機能 | 追加設定 | 詳細 |
|---|---|---|
| **PDF/Excel 出力**（pdf-lib, exceljs, react-pdf） | `vercel.json` + `outputFileTracingIncludes` + `maxDuration` | (a) フォントを `scripts/fetch-font.mjs` でビルド時 DL、`vercel.json` の `buildCommand` で実行 (b) `next.config.mjs` の `experimental.outputFileTracingIncludes` で関数バンドルに含める (c) route.ts に `export const maxDuration = 60` (d) 日本語 PDF は variable TTF を `subset:false` で埋め込む（OTF は不可）。詳細テンプレ：`nextjs-pdf-export` スキル |
| **Claude/OpenAI API での画像解析** | env_vars 追加 + maxDuration | `ANTHROPIC_API_KEY` を env_vars に追加。route に `maxDuration = 60`。bbox は **0–1000 正規化座標**で会話（実 px は Claude の内部レンダリングスケールとズレる） |
| **PDF ビューア**（pdfjs-dist + react-konva） | バージョンピン + worker CDN | `react-konva` は `^18.2.10` でピン（v19 は React 19 要求）。`pdfjs-dist` は `legacy/build/pdf.mjs` を使い、worker は `GlobalWorkerOptions.workerSrc = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@<ver>/build/pdf.worker.min.mjs'` を直指定（`?url` import は Next で解決不可） |
| **マルチテナント SaaS** | RLS テンプレ適用 | `current_tenant_id()` は SECURITY DEFINER、INSERT 時 tenant_id 必須、auto-create trigger は app_metadata を尊重。詳細テンプレ：`supabase-multitenant-rls` スキル |
| **ファイルアップロード（Storage）** | バケット作成 + RLS | バケット private + authenticated read/upload ポリシー、Server Action での `bodySizeLimit: '50mb'` 等 |
| **多めの依存（react-konva 等 peer 制約）** | `vercel.json` の installCommand | `"installCommand": "npm install --legacy-peer-deps"` |

これらは `vercel-connect-and-deploy` の Step 5-X / 5-2 で詳述。

---

## Phase 4-V 補足: 過去に踏んだ落とし穴 (必須対策)

過去案件で実際にハマった具体的な落とし穴。Vercel パスでは**最初から**以下を仕込む。
後から直すと顧客の前で「なぜか動かない」状態を見せることになる。

### Stripe は AI OSI URI Deploy 拡張経由（test がデフォルト）

- Stripe 操作は拡張ツール `mcp__AI_OSI_URI_Deploy__stripe_create_product_and_price` /
  `stripe_create_payment_link` / `stripe_create_webhook` を使う。**`mode:"test"` が既定**で、
  Live で作成するには `confirm_live:true` を明示的に渡す必要がある（誤爆防止）。
- **対策**:
  - デモ・検証は既定の `mode:"test"` のまま使う。`confirm_live` は付けない。
  - Live で商品を作る前に必ず「これは本番アカウントに残ります」と顧客に確認し、
    その上で `confirm_live:true` を渡す。
  - 旧 standalone Stripe MCP（単独 `stripe_*` サーバ / `get_stripe_account_info`）は**使わない**。
    AI OSI URI では Stripe は Deploy 拡張に一本化済み。
- 本番化 (test→live) は `switch-to-live-mode` を使う。dev/demo段階では使わない。

### Next.js Server Component キャッシュは最初から無効化

- `revalidate: 60` でキャッシュさせると、初回エラーや初期データ不整合のとき**60秒間
  404 や旧データが固着**する。顧客にデモ中に固まる事故の原因。
- **対策**: 動的データを扱う page では迷ったら最初から:
  ```ts
  export const dynamic = "force-dynamic";
  // fetch 側も:
  fetch(url, { cache: "no-store" })
  ```
- 安定して動き始めた後で `revalidate` に戻す。最初から `revalidate` を貼らない。

### Next.js dynamic route × 日本語 / マルチバイト handle

- 日本語の handle (例: `名刺入れ-楓デザイン`) を URL に使うと、ホスティング/CDN の
  デコード段数の差で `params.handle` が**期待と違う形**で渡ることがある。`product not found`
  の謎404を引き起こす。
- **対策** (handle ベースで取得する全 dynamic page に入れる):
  ```ts
  const { handle: raw } = await params;
  const candidates: string[] = [raw];
  try { const d = decodeURIComponent(raw); if (d !== raw) candidates.push(d); } catch {}
  try { const d2 = decodeURIComponent(decodeURIComponent(raw)); if (!candidates.includes(d2)) candidates.push(d2); } catch {}
  let item = null;
  for (const c of candidates) { item = await fetchByHandle(c); if (item) break; }
  if (!item) {
    // 最後のフォールバック: 一覧から find
    const all = await fetchAll();
    item = all.find(x => candidates.includes(x.handle)) || null;
  }
  ```
- 完全 ASCII の slug 設計で逃げるのも一手だが、商品名そのものをハンドルにする
  日本案件では上記の保険が必須。

### localStorage はスキーマ変更時に LS_KEY のバージョンを上げる

- カートや会員データを localStorage に持つ場合、データスキーマを変えると**ユーザーの
  ブラウザに残っている旧データ**でアプリが落ちる。`undefined.gid`系の致命的エラー。
- **対策**:
  ```ts
  const LS_KEY = "myapp_cart_v3"; // スキーマ変更ごとに v2 → v3
  if (typeof window !== "undefined") {
    ["myapp_cart", "myapp_cart_v2"].forEach(k => localStorage.removeItem(k));
  }
  ```
- 読み込み時に**必ず validate** し、不正項目は破棄する:
  ```ts
  const valid = parsed.filter(i => VALID_IDS.has(i.id));
  ```

### Vercel デプロイは「Push 成功」と「Build 成功」を分けて確認

- `git push` が成功しても、ローカル/CI の PAT 期限切れで「実は push されていない」
  「Vercel は古い main から build した」ということが起きる。デプロイの READY 状態
  だけ見て「直ったはず」と顧客に伝えると赤恥。
- **対策** (デプロイ完了後の確認順):
  1. `git push` の出力末尾に `main -> main` のコミット移動が出ているか
  2. Vercel API で `meta.githubCommitSha` を取得し、ローカル `git rev-parse HEAD` と一致
  3. その上で `readyState=READY`
  4. さらに本物の URL を curl してレスポンスの中身を grep（古いキャッシュを掴んでないか）

### GitHub PAT 期限切れの突然死対策

- `.env` の `GITHUB_PAT=ghp_...` は寿命がある（90日や1年）。期限が来た瞬間に
  `git push` が `Bad credentials` で全滅する。デプロイ中に発覚すると最悪のタイミング。
- **対策**:
  - `.env` に発行日と期限を `# GITHUB_PAT (issued 2026-05-30, expires 2026-08-28)`
    と注記。
  - デプロイ実行直前に必ず `curl -sf -H "Authorization: token $GITHUB_PAT" https://api.github.com/user`
    で 200 を確認してから git 操作に入る。401 なら setup-deploy-environment へ案内。

### 顧客サイトと管理画面は**最初から完全分離**

EC・予約・SaaSなど「お客さん向けUI」と「事務局向けUI」が同居するアプリで、
中途半端に統合して始めると後で剥がす作業が発生する。

- **構造原則** (Next.js App Router の場合):
  ```
  src/app/
    layout.tsx          ← html/body のみ、何も入れない
    (shop)/             ← お客さん向け
      layout.tsx        ← Header/Footer/Providers
      page.tsx
      products/...
    admin/              ← 事務局向け
      layout.tsx        ← サイドバー、独自CSS
      admin.css
      page.tsx
      orders/page.tsx
      inventory/page.tsx
  ```
- **絶対やらないこと**:
  - 顧客サイト → 管理画面 への遷移リンクを置く（逆も）
  - 同じ Header/Footer/カラーパレット/書体 を使い回す
  - 共通の AuthProvider で両方を包む（権限が混乱する）
- **配色・書体・ナビゲーション構造を別物に**することで、顧客に説明するときも
  「これはお客さんの顔」「これは事務局の裏側」と一言で分かるようになる。
- 一度同居させてから分離すると、ルートを `(shop)` route group に動かすため
  `git mv` × 全頁、provider 配置の見直し、CSS 競合の整理 と痛い手戻りになる。
  「**最初から分けて作る**」が結局一番速い。

### Vercel: route group `(shop)` の括弧はシェルで quote する

- ディレクトリ名 `(shop)` の括弧はシェルが解釈しようとして `syntax error` や
  予期せぬ展開を起こす。
- **対策**:
  ```bash
  # NG
  cp -r src/app/(shop)/page.tsx ...
  # OK
  cp -r "src/app/(shop)/page.tsx" ...
  ```
- mv/cp/find 系を組むスクリプトでは route group ディレクトリを必ず `"..."` で囲う。

### 構成選定: 「説明のシンプルさ」を最初に評価

- Headless Shopify 等の多サービス連携構成は技術的には美しいが、**顧客に説明する
  工数**が膨大で、最終的に「やっぱり1サービスにして」と差し戻されやすい（実例: 
  楓美会EC で Headless Shopify → Stripe一本化に大手戻り）。
- **チェックリスト (Phase 1〜2 で全部聞く):**
  - 商品/エンティティ点数は何点規模？
  - 運営人数は？ボランティア？専任スタッフ？
  - 月額固定費に出せる予算は？(Shopify 3,650円 vs Stripe 0円 など差が大きい)
  - 顧客が「これは○○です」と一言で説明できる構成か？
  - サイトは**1つ**に保てるか？（顧客向け）
- 複雑な構成を選ぶときは**理由を明文化**して spec.md に残す。後で「シンプルな方が
  良かった」となったときに、判断の経緯を見直せる。

### 顧客向けご案内資料に必ず含める項目

- アクセス URL と認証情報（テーブル形式、1ページ目）
- ご確認いただきたいポイント（3〜5個に絞る）
- デモ版の制約 × 本番で解消される項目（1対1で対応させる）
- 連絡先（最後、統一フォーマット）

---

## Phase 4.9-V: ドライブへ接続情報を記録（必須・アプリ台帳）

> **DoD ゲート（必須）**：この記録を完了するまで Phase 5-V 完了レポートを出さない。
> 目的は「**ドライブを見れば全アプリの公開URL・リポ・再デプロイ手順に必ず辿り着ける**」
> 状態を保つこと。アプリが増えても行方不明にしない、全社の単一情報源。
> Vercel パス（本フェーズ）/ AWS パス（Phase 6.9-A）の両方で必須。

### Step 1: 保存先フォルダを決める

- Drive 案件フォルダがある場合：`03.PJT資料/{ID}.{企業名}/` 配下に `{アプリ名}/` を作る。
- 案件が紐づかない場合：ユーザーに保存先フォルダを確認（既定は作業中の案件フォルダ直下）。
- 全社横断台帳のパスが指定/既知ならそれも控える（Step 3）。

### Step 2: `アプリ情報_README.md` を生成（このフォルダに置く）

```markdown
# {アプリ名} — アプリ接続情報

> このファイルを見れば、アプリの場所・接続先・更新方法がすべて分かります。

## 概要
| 項目 | 内容 |
| --- | --- |
| アプリ名 | {アプリ名} |
| 用途 | {1行} |
| ステータス | 🟡 モック / 🟢 本番 / ⚪️ 停止 |
| 作成日 | {YYYY-MM-DD} |
| 作成者 | {名前}／Cowork |
| 案件 | {案件名} |

## 接続先（ここから開ける）
| 種別 | URL / ID |
| --- | --- |
| 🌐 公開URL | {APP_URL} |
| 📦 GitHub | {REPO_URL} |
| ▲ Vercel / AWS | {project名 / Team or ALB/CloudFront} |
| project_id 等 | {prj_... / ECS cluster 等} |
| 💾 オフライン版 | {あれば相対パス／無ければ「なし」} |

## 構成
- {静的 / Next.js+Supabase / AWS 等}・{DB/課金の有無}

## 更新・再デプロイ手順
1. コードは {REPO_URL} の {主要パス}。
2. main に push すると {Vercel 自動再デプロイ / CI でECS更新}。
3. Cowork からは「{アプリ名}を更新して」で再デプロイ。

## 注意
- {モックならダミーデータ等の注意 / 本番なら取り扱い注意}
```

### Step 3: 台帳 `_アプリ台帳.md` に1行追記（無ければ新規作成）

- 置き場所：案件フォルダ直下（全社横断台帳が指定されていればそちらにも追記）。
- 既存ならアプリ行を追記/更新し、`最終更新` を更新する。

```markdown
# アプリ台帳（{案件名}）

> 新しくアプリを作ったら必ず1行追加する。詳細は各フォルダの `アプリ情報_README.md`。

最終更新: {YYYY-MM-DD}

| アプリ名 | ステータス | 公開URL | GitHub | ホスティング | フォルダ | 作成日 |
| --- | --- | --- | --- | --- | --- | --- |
| {アプリ名} | 🟡 モック | {APP_URL} | [repo]({REPO_URL}) | {Vercel/AWS} | `{アプリ名}/` | {YYYY-MM-DD} |

## ステータス凡例
- 🟡 モック … 商談デモ用（ダミーデータ）／🟢 本番 … 実運用／⚪️ 停止 … アーカイブ
```

### Step 4: オフライン版・成果物の同梱（あれば）

- 静的HTML等は同フォルダにコピーしておく（ネット不要で開ける保険）。

### Step 5: evidence を残す

- `deploy-progress.md` の「完了」欄に
  `Drive 記録 ✅: {README 絶対パス} ／ 台帳追記済み` を貼る。
- これが無いと DoD 未達のため Phase 5-V に進まない。

---

## Phase 5-V: Vercel 完了レポート

> **DoD ゲート（必須）**：この完了レポートを出す前に「ハーネス §3 検証コマンド」と
> 「Phase 4.9-V（Drive 記録）」を完了し、各 evidence を `deploy-progress.md` に貼ること。
> 未検証項目が残るなら `🎉` ではなく「未検証: ◯◯」を明記して正直に出す。

```
🎉 デプロイ完了 (Vercel パス)

【公開 URL】 {APP_URL}
【リポジトリ】 {REPO_URL}
【構成】 Vercel + {Supabase/Stripe/Anthropic 有無}

【次にやること】
  1. {APP_URL} を開いて動作確認
  2. (Supabase あり) Magic Link テスト
  3. (Stripe あり) テスト決済 (4242 4242 4242 4242)
  4. 本番化 (test → live) は switch-to-live-mode
  4. **PDF/Excel 出力がある場合**：書き出して中身が日本語で出ているか確認。
     日本語が空白なら font 未バンドル（`vercel.json` の buildCommand 確認）
  5. **マルチテナント SaaS の場合**：Supabase Dashboard でテスト用 2 人目のユーザーを
     作り、それぞれが他テナントのデータを見えないことを確認
  6. **AI 機能がある場合**：1 回テストして response time が 30 秒以内であることを確認
     （超えるなら CDN フェッチをビルド時に前倒し）
```

---

## Phase 4-D: Desktop パスの実行（Electron + GitHub Actions）

> Desktop パスは Cowork で Electron scaffold を生成し、GitHub Actions の matrix ビルドで
> Windows/Mac/Linux 向けのインストーラーを自動生成する。Cowork のサンドボックス（Linux）では
> macOS の署名・Notarization ができないため、**ビルド・署名・配布は GitHub Actions に委譲**する。

### Step 1: Electron scaffold 生成

`electron-scaffold-and-build` atomic スキルを呼ぶ。以下の構成を生成:

```
{project}/
├── package.json              # electron-builder config 込み
├── electron-builder.yml      # ビルド詳細設定（ターゲット OS・インストーラー形式）
├── src/
│   ├── main/
│   │   ├── index.ts          # Electron main process
│   │   ├── preload.ts        # contextBridge（セキュリティ境界）
│   │   └── ipc-handlers.ts   # IPC ハンドラ（ファイル操作等）
│   └── renderer/
│       ├── index.html
│       ├── App.tsx            # React（Phase 1 のエンティティに沿った画面）
│       └── ...
├── .github/
│   └── workflows/
│       └── build-and-release.yml   # GitHub Actions matrix ビルド
├── CLAUDE.md
└── DEPLOY.md
```

Phase 1 のエンティティ・ロール・機能に沿った画面を `renderer/` に仮実装する。
Web（Next.js）との違い: ルーティングは `react-router-dom`、API は IPC 経由（HTTP ではない）。

### Step 2: GitHub Actions workflow 同梱

`build-and-release.yml` を scaffold に含める。タグ push (`v*`) で自動トリガー:

```yaml
name: Build & Release
on:
  push:
    tags: ['v*']
  workflow_dispatch:

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: macos-latest
            platform: mac
          - os: windows-latest
            platform: win
          - os: ubuntu-latest
            platform: linux
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - name: Build & Sign
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # macOS（署名ありの場合のみ）
          CSC_LINK: ${{ secrets.MAC_CERTIFICATE }}
          CSC_KEY_PASSWORD: ${{ secrets.MAC_CERTIFICATE_PASSWORD }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_PASSWORD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
          # Windows（署名ありの場合のみ）
          WIN_CSC_LINK: ${{ secrets.WIN_CERTIFICATE }}
          WIN_CSC_KEY_PASSWORD: ${{ secrets.WIN_CERTIFICATE_PASSWORD }}
        run: npx electron-builder --${{ matrix.platform }} --publish always
```

署名なし（PoC/社内）の場合は `CSC_*` / `APPLE_*` / `WIN_CSC_*` の env 行を削除した
軽量版を使う（Secrets 未設定でも CI が通る）。

### Step 3: gh-create-repo-and-push（共通）

`gh-create-repo-and-push` を呼ぶ（owner_override は `USE_ORG` に従う）。
**Vercel パスと完全に同じツール**を使う。Desktop 固有の処理はない。

### Step 4: 初回タグ push → Actions トリガー

```bash
# Cowork が github_push で実行:
# 1. v0.1.0 タグを打つ（Actions の on.push.tags トリガー）
git tag v0.1.0
git push origin v0.1.0
```

`github_push` でタグ付き push を行い、GitHub Actions のビルドを開始する。

### Step 5: desktop-release-monitor（CI 完了監視）

`desktop-release-monitor` atomic スキルを呼ぶ。GitHub API で Actions の
workflow run 状態を 15 秒間隔でポーリングし、進捗を実況:

```
🟡 Windows ビルド中...
🟢 Mac ビルド完了 (3:42)
🟢 Linux ビルド完了 (2:15)
🟢 Windows ビルド完了 (4:28)
✅ 全プラットフォームのビルド完了 — GitHub Release を確認中...
🟢 Release v0.1.0 公開済み (3 assets)
```

タイムアウト 15 分。失敗時は `desktop-release-monitor` がビルドログを取得して提示。

### Step 6: Release asset URL 取得

GitHub Releases API から各 OS のダウンロード URL を取得:

```
GET /repos/{owner}/{repo}/releases/latest
→ assets[]: { name, browser_download_url, size }
```

### Desktop パスの冪等ガード

- GitHub Release は同一タグで 1 回のみ。再ビルドが必要な場合はタグを削除 → 再作成、
  または `workflow_dispatch` で手動トリガー。
- `vercel_create_project_and_deploy` のような「二重作成」リスクはない（Release は
  タグに紐づくため名前衝突しない）。

### Desktop パスのローカルクローン

Vercel パスと同じく `~/projects/<repo-name>` に clone。`DEPLOY.md` には:
- 更新は `clone → 修正 → push → tag → CI 自動ビルド`
- `update-deploy` で再ビルド可能（Desktop 対応版）

---

## Phase 4.9-D: ドライブへ接続情報を記録（必須・アプリ台帳）

> **DoD ゲート（必須）**：この記録を完了するまで Phase 5-D 完了レポートを出さない。
> 手順・テンプレは **Phase 4.9-V と同一**（`アプリ情報_README.md` 生成 + `_アプリ台帳.md`
> 追記 + evidence を `deploy-progress.md` に貼る）。Desktop パスでは接続先に
> GitHub Releases URL・各 OS のダウンロードリンクを記載する。

Desktop 固有の `アプリ情報_README.md` 記載項目:

| 種別 | URL / ID |
| --- | --- |
| 📦 GitHub | {REPO_URL} |
| 📥 GitHub Releases | {RELEASE_URL} |
| 🪟 Windows DL | {.exe リンク} |
| 🍎 Mac DL | {.dmg リンク} |
| 🐧 Linux DL | {.AppImage リンク} |
| 署名 | あり（Apple Developer ID + Windows Authenticode）/ なし |

---

## Phase 5-D: Desktop 完了レポート

> **DoD ゲート（必須）**：Phase 4.9-D（Drive 記録）の evidence を `deploy-progress.md` に
> 貼ってからこのレポートを出す。GitHub Actions の全 OS ビルドが `success` であることを
> 確認してから完了と書く。

```
🎉 デスクトップアプリ完了 (Desktop パス)

【ダウンロード】
  Windows: {.exe リンク}
  Mac: {.dmg リンク}
  Linux: {.AppImage リンク}

【リポジトリ】 {REPO_URL}
【GitHub Releases】 {RELEASE_URL}
【構成】 Electron + React + electron-builder
【署名】 {あり / なし（社内PoC）}
【自動更新】 {electron-updater（GitHub Releases 経由）/ なし}

【次にやること】
  1. 各 OS でインストール → 起動確認
  2. Windows（署名なし）: SmartScreen 警告 →「詳細情報」→「実行」
  3. Mac（署名なし）: 「開発元を検証できません」→ システム設定 > セキュリティ で許可
  4. Mac（署名あり）: Gatekeeper が自動で通過することを確認
  5. 更新版リリース: main に push + `git tag v0.2.0 && git push origin v0.2.0`
     → GitHub Actions 自動ビルド → Release 自動公開
  6. 本番化（署名追加）: setup-deploy-environment で証明書を登録
```

---

## Phase 4-A: AWS パス: インフラ構築 (インフラ先行)

> **着手前に必ず：Terraform state を共有S3 backend にする（orphan化防止）。**
> 初回 apply の前に **`tf-state-backend` スキル**を呼び、state基盤（共有バケット
> `aiosiuri-tfstate-<ACCOUNT_ID>` + ロック `aiosiuri-tf-lock`）を用意し、`infra/backend.tf` を
> 差し込む。これで state は最初からS3に置かれ、Cowork の揮発フォルダに残らない。
> 既存のローカルstateアプリを移行する場合も同スキル（migrate-existing）を使う。
> 詳細は [references/aws-app-gotchas.md](references/aws-app-gotchas.md) の項7。

### Step 1: spec.md と infra-decision.md を生成

Phase 1 (アプリ定義) と Phase 2 (インフラ判断) の結果を 2 つのファイルにまとめて
outputs/ に保存。Claude Code 側のスキルが読む。

#### spec.md テンプレ

```markdown
# {PROJECT_NAME}

## 概要
{PROJECT_DESCRIPTION}

## 業種
{retail / food / education / medical / real-estate / etc.}

## エンティティ
- {entity_1}: {description, 主要フィールド}
- {entity_2}: {description}
...

## 認証ロール
- {role_1}: {label}
- {role_2}: {label}
...

## 機能要件
- {feature_1}
- {feature_2}
...
```

#### infra-decision.md テンプレ

```markdown
# Infrastructure Decision for {PROJECT_NAME}

## 規模
{PoC / 中規模 / 本番}

## 採用構成
- VPC: dev=10.20.0.0/16, prod=10.30.0.0/16
- Aurora: {mysql/postgres} {instance_class}
- ECS: {desired_count}
- WAF: {enabled}
- CloudFront + S3: {enabled}
- Lambda + SQS: {required / not_required}

## コンプライアンス対応
- KMS CMK: {yes/no}
- 監査ログ: {yes/no}
- 機微情報強化: {医療 3 省 / FISC / なし}

## ドメイン
{custom_domain or auto}

## terraform.tfvars 用パラメータ
project_name = "{name}"
environment = "dev"
vpc_cidr = "10.20.0.0/16"
...
```

### Step 2: Claude Code 起動コマンドを clipboard へ

```bash
# Cowork が clipboard にセット:
git clone https://github.com/ai-osi-uri/project-template.git \
  ~/Desktop/{PROJECT_NAME_LOWER} && \
cd ~/Desktop/{PROJECT_NAME_LOWER} && \
cp "{OUTPUTS}/spec.md" ./.claude/plans/spec.md && \
cp "{OUTPUTS}/infra-decision.md" ./.claude/plans/infra-decision.md && \
claude
```

ユーザーに **明確な順序の指示**を案内:

```
ターミナルで Cmd+V → Enter を実行してください。Claude Code が起動したら、
以下を**この順番で**実行してください:

  1. /initialize-project
     placeholder 置換、ロール削除、ディレクトリ構成確定

  2. /setup-infra
     Terraform apply (Phase 4-A のインフラ構築完了)

  ⚠️ ここで一旦 Claude Code の作業を止めて、Cowork に戻ってきてください。
     私が次の Phase 5-A (アプリ + CI 構築) の指示を出します。

  ❌ /create-app をまだ実行しないでください。
     インフラ出力 (ECR URI / Aurora endpoint) を環境変数に埋めるため、
     /setup-infra 完了を Cowork が確認してから次に進みます。
```

### Step 3: Phase 4-A 監視 (MCP ポーリング)

Cowork は以下を 30 秒ごとにポーリング:

```bash
# 1. GitHub repo 作成検出
gh api repos/ai-osi-uri/{PROJECT_NAME_LOWER} --jq .id

# 2. main / develop ブランチ作成検出
gh api repos/ai-osi-uri/{PROJECT_NAME_LOWER}/branches --jq '.[].name'

# 3. Terraform State バケット作成検出
aws s3api head-bucket --bucket "{PROJECT_NAME_LOWER}-dev-terraform-state"

# 4. VPC + ECR + Aurora 作成検出 (AWS MCP)
aws ec2 describe-vpcs --filters "Name=tag:Project,Values={PROJECT_NAME}"
aws ecr describe-repositories --repository-names "{PROJECT_NAME_LOWER}-dev-..."
aws rds describe-db-clusters
```

進捗を Cowork チャットで実況中継:

```
🟢 GitHub repo 作成完了
🟢 Terraform State バケット作成完了
🟡 VPC / Subnet 作成中... (terraform apply ~50%)
🟢 ECR repository 作成完了
🟢 Aurora cluster 作成完了 (Master)
🟢 ALB / WAF 作成完了
✅ Phase 4-A (インフラ構築) 完了 — Phase 5-A に進みます
```

タイムアウト 30 分。完了したら Phase 5-A へ。

---

## Phase 5-A: AWS パス: アプリ + CI 構築 (アプリ後発)

Phase 4-A 完了を確認したら、Cowork が次の指示を clipboard に投入:

```bash
# Claude Code で以下を実行:
/create-app .claude/plans/spec.md

# 完了後、続けて:
cd {API_DIR}
make ecr-login
docker build -t {PROJECT_NAME_LOWER}-dev-api:latest .
docker tag {PROJECT_NAME_LOWER}-dev-api:latest \
  {ACCOUNT}.dkr.ecr.ap-northeast-1.amazonaws.com/{PROJECT_NAME_LOWER}-dev-api:latest
docker push \
  {ACCOUNT}.dkr.ecr.ap-northeast-1.amazonaws.com/{PROJECT_NAME_LOWER}-dev-api:latest

aws ecs update-service \
  --cluster {PROJECT_NAME_LOWER}-dev-cluster \
  --service {PROJECT_NAME_LOWER}-dev-api \
  --force-new-deployment

make migration-run
make seed
```

### Phase 5-A 監視

Cowork が ECS task の起動状態を MCP でポーリング:

```bash
aws ecs describe-services \
  --cluster {PROJECT_NAME_LOWER}-dev-cluster \
  --services {PROJECT_NAME_LOWER}-dev-api \
  --query 'services[0].runningCount'
```

`runningCount` が `desiredCount` に達したら ✅。

---

## Phase 6-A: 動作確認 (smoke test)

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names {PROJECT_NAME_LOWER}-dev-alb \
  --query 'LoadBalancers[0].DNSName' --output text)

curl -i "https://$ALB_DNS/health"
```

`/health` が 200 を返したら ✅。失敗時は CloudWatch Logs を確認案内。

---

## Phase 6.9-A: ドライブへ接続情報を記録（必須・アプリ台帳）

> **DoD ゲート（必須）**：この記録を完了するまで Phase 7-A 完了レポートを出さない。
> 手順・テンプレは **Phase 4.9-V と同一**（`アプリ情報_README.md` 生成 + `_アプリ台帳.md`
> 追記 + evidence を `deploy-progress.md` に貼る）。AWS パスでは接続先に
> ALB/CloudFront ドメイン・ECS クラスタ名・Aurora endpoint を記載する。

---

## Phase 7-A: 完了レポート (AWS パス)

> **DoD ゲート（必須）**：Phase 6-A の smoke test（`/health` 200 等）と Phase 6.9-A
> （Drive 記録）の evidence を `deploy-progress.md` に貼ってからこのレポートを出す。
> ECS の `runningCount` 到達や apply 成功だけを根拠に完了と書かない。未検証項目は
> 「未検証: ◯◯」と明記する。

```
🎉 アプリ作成完了 (AWS パス)

【公開 URL】
  - API: https://{ALB_DNS}/health
  - Frontend: https://{CLOUDFRONT_DOMAIN}

【リポジトリ】
  https://github.com/ai-osi-uri/{PROJECT_NAME_LOWER}

【構成】
  - 業種: {retail / food / etc.}
  - ホスティング: AWS (project-template 準拠)
  - フレームワーク: NestJS + React
  - DB: Aurora ({engine})
  - 認証: {auth_roles}
  - 機微情報強化: {applied / not}

【次にやること】
  1. ALB / CloudFront ドメインで動作確認
  2. staging/prod 構築は infra/README.md 参照
  3. カスタムドメイン化は ACM 証明書発行から
```

---

## エラーハンドリング

| Phase | 失敗 | 対応 |
| --- | --- | --- |
| 0 | 拡張未導入 / トークン不足（`health_check` で valid でない） | setup-deploy-environment（拡張導入）案内、中断 |
| 1 sparse | 業種が読み取れない | 「もう少し詳しく教えてください、例: 何屋さん？何を管理するアプリ？」と再度聞く |
| 1 詳細 | エンティティ抽出失敗 | LLM で再抽出、それでもダメなら箇条書きで聞く |
| 2 | 規模が不確定 | デフォルトで PoC、後で見直し可と案内 |
| 3 | プラン却下 | Phase 1-2 に戻って再ヒアリング |
| 4-V | scaffold 失敗 | 既存テンプレートを使う or 手動 scaffold 案内 |
| 4-V | atomic 失敗 | 既存 deploy-app のロールバック責務マップ準拠 |
| 4-A | /setup-infra タイムアウト | CloudWatch Logs と terraform plan/apply のエラー出力を確認案内 |
| 5-A | docker build 失敗 | Dockerfile を Cowork が確認、修正案を提示 |
| 5-A | ECS task 起動失敗 | ECS event + CloudWatch Logs を取得、原因分析 |
| 6-A | smoke test 失敗 | health endpoint 実装漏れの可能性、ログ確認案内 |
| 4-D | scaffold 生成失敗 | Electron テンプレートをフォールバックで使用 |
| 4-D | GH Actions ビルド失敗（1 OS） | `desktop-release-monitor` がログを取得、修正案を提示して `github_push` で再トリガー |
| 4-D | GH Actions ビルド失敗（署名エラー） | 署名なしに切り替えるか、証明書 Secrets の設定を案内 |
| 4-D | GH Actions タイムアウト | `workflow_dispatch` で手動再トリガー、または Actions の制限を案内 |

---

## 注意事項

- **既存 Vercel ユーザーの体験を壊さない**: Phase 1 で「既存コードあり」or「LP のみ」を選び、
  Phase 3 で Vercel を選べば従来の deploy-app と同じ流れになる
- **AWS パスでは Claude Code が起動する必要がある**: ローカルに `claude` CLI が
  インストールされていること
- **`/bootstrap-project` は使わない**: アプリ先・インフラ後の順序になるため、本スキルの
  「インフラ先・アプリ後」と矛盾する。代わりに `/initialize-project` → `/setup-infra` →
  `/create-app` を順次呼ぶ
- **MCP 監視は best effort**: ポーリング失敗してもエラーにせず、ユーザーに状況確認の余地を残す
- **Phase 4-A と Phase 5-A の境界が明確**: インフラ完了 → イメージ push → ECS 起動、
  の連続を Cowork が監視・誘導することで「ECS が空回り」状態を回避できる
- **sparse 入力は推測を出してユーザー確認**: 一言依頼でも「業種から推測したロール
  候補・エンティティ候補・規模候補」を提示して、ユーザーは選ぶだけにする。3 個以上
  続けて自由記述させない
- **Desktop パスでは GitHub Actions がビルドを実行**: Cowork のサンドボックス（Linux）では
  macOS のコード署名・Notarization ができないため、GitHub Actions の matrix ビルドに委譲。
  Cowork は scaffold 生成・push・CI 監視に専念する（Vercel パスと同じ体験）
- **Desktop パスの更新は `update-deploy`**: 初回デプロイ後の修正は `update-deploy` を使い、
  `git push` + tag で GitHub Actions を再トリガーする

---

## 関連スキル

- `setup-deploy-environment` — 前提となる初期設定
- `gh-create-repo-and-push` — Vercel パスの初期 push
- `vercel-connect-and-deploy` — Vercel パスのデプロイ
- `supabase-set-auth-url` — Vercel + Supabase 構成
- `app-smoke-test` — 両パスの最終チェック
- `aws-static-deploy` — 静的サイト軽量 AWS パス用
- `switch-to-live-mode` — Stripe テスト→本番化
- `electron-scaffold-and-build` — Desktop パスの scaffold 生成 + GH Actions workflow 同梱
- `desktop-release-monitor` — Desktop パスの GitHub Actions ビルド監視
- Claude Code 側:
  - `/initialize-project` — placeholder 置換、AWS パスで使用
  - `/setup-infra` — Terraform apply (インフラ構築)、AWS パスで使用
  - `/create-app` — エンティティ生成 + CI 設定、AWS パスで使用
  - `/bootstrap-project` — **本スキルでは使わない** (順序が逆のため)
