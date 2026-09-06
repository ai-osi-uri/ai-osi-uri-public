---
name: create-app
description: |
  AI OSI URI が Cowork から
  **アプリを新規に作って公開する**ための唯一のオーケストレータ。Web（Vercel / AWS）
  ・Desktop（Electron）・ローカル出力（素のプロジェクト / コンテナ）に対応する。
  「アプリ作って」「LP 立ち上げて」「○○屋向けの在庫管理アプリ作って」
  「予約サイトを作って」「会員制のサブスク SaaS 作って」「業務系のシステム作って」
  「デスクトップアプリを作って」「Electron で作って」「PC にインストールできるアプリ」
  「ローカルで動くアプリ」で発動する。**モバイルアプリ（iOS / Android）は
  `deploy-mobile-app`（osi-mobile-deploy）が直接受ける**ので「iPhone アプリ作って」
  「Android アプリを作って」では発動しない。Web
  前提で進めた結果モバイルと判明したときだけ Phase 4-M で委譲する。既存アプリの修正は
  `update-deploy`。**Lovable で作られたアプリの決済実装（Stripe 有効化・本番化）は
  `lovable-payments-golive` が直接受ける**（本スキルは Lovable プロジェクトの新規作成・
  改修は扱わない）。旧名 deploy-app。
version: 1.2.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
  - server: aws-api
    provision: user-install
  - server: slack
    provision: user-install
---

# create-app v1.0 — 汎用アプリ作成エントリポイント

「アプリ作って」と言われたら、業種・規模・ターゲットに関わらず要件を聞き出して、
公開・配布するところまで 1 つの対話で完結させる。

> 旧名 `deploy-app`。v1.0 で Web/Desktop/Mobile/ローカルの 4 パスに対応。

---

## 設計原則

1. **Single entry point**: ユーザーは「アプリ作って」と言うだけ。パスや Phase を意識させない
2. **業種非依存**: 花屋・飲食・学習塾・医療・不動産・EC — どんな業種でも同じフロー
3. **ターゲット非依存**: Web / Desktop / Mobile / ローカルを同じ入口から分岐
4. **入力の粒度に頑健**: 詳細な仕様でも一言依頼でも対応
5. **責務分離**: 本スキルは判定・順序制御・引き渡しに専念。実ビルドは atomic に委譲
6. **既存資産活用**: 各パスの atomic スキルを組み合わせる

---

## 作成先の決定ルール（org or 個人）

リポジトリの作成先は `health_check` の `github.repo_target` が示す。**推測しない。**

| `github.repo_target` | 意味 | 既定の作成先 |
|---|---|---|
| `org:<slug>` | 拡張設定の「GitHub Organization」に slug が入っている | その Org 配下 |
| `personal:<username>` | Org 未設定 | 個人アカウント配下 |

**重要:** `GITHUB_ORG` が未設定だと、`github_create_repo_and_push` は `owner_override` を
渡さない限り**必ず個人アカウント**（`POST /user/repos`）に作りにいく。
Org 配下に置きたいのに設定が空、というのが最も多い取り違えなので、Phase 3 のプラン提示で
**作成先を必ず明示してユーザーの承認を取る**。

- `repo_target` が意図と違う → `owner_override` を渡す（`'personal'` で個人、Org slug でその Org）。
  恒久的に変えるなら拡張設定の「GitHub Organization」を埋めてもらう
- 403 が返ったら、エラー本文の `target` フィールドで**どちらに作りにいって失敗したか**を確認する。
  個人で 403 なら PAT に個人リポの作成権限がないだけで、Org 側の権限は無関係
- **org と個人を混在させない**。GitHub を Org にしたら Vercel / Supabase も Org / Team 側に寄せる

---

## 実行の絶対ルール

1. **着手前に `health_check`** で拡張ロードを確認。通るまで進まない。
2. **操作は必ず Deploy 拡張のツール経由**。CLI にフォールバックしない。

---

## ワークフロー全体像

```
Phase 0: 認証情報・接続状況の確認
Phase 1: アプリ定義（入力解析 → ギャップ埋め）
Phase 2: ターゲット判定（Web / Desktop / Mobile / ローカル）
Phase 3: プラン承認

─── パス分岐 ───

[Web パス]
  Vercel: Phase 4-W-V → references/web-vercel-path.md
  AWS:    Phase 4-W-A → references/web-aws-path.md

[Desktop パス]
  Phase 4-D → references/desktop-path.md
    electron-scaffold-and-build → desktop-release-monitor

[Mobile パス]
  Phase 4-M → references/mobile-path.md
    osi-mobile-deploy プラグインの deploy-mobile-app へ委譲

[ローカル出力パス]
  Phase 4-L → references/local-output-path.md
    local-project-output / app-builder-export / app-builder-container-export

─── 共通後処理 ───

Phase N-1: Drive 記録 → references/drive-record.md
Phase N:   完了レポート
```

---

## 動作要件

必要 mcpb（AI OSI URI Deploy）: >= 1.23.0

## Phase 0: 認証情報・接続状況の確認

1. `health_check` を呼ぶ
   - **バージョン整合チェック**（設計: docs/mcpb-update-notification-design.md）:
     - `server_version` が上の「必要 mcpb」**未満** → **中断**し、更新を案内する
       （「コネクタが古く、このスキルの新しい手順が動きません。ポータルにログインして
       新しい .mcpb をダウンロードし、開き直してください」）。旧版のまま進むと後半で
       分かりにくい失敗になるため、ここで止めるのが正しい
     - `update.status: "update_available"` → 作業は**止めずに** `update.notice` を一言案内する
     - `update.status: "unreachable"` → 何も言わずに続行（オフラインで作業を妨げない）
     - `server_version` が返ってこない（旧 mcpb）→ 「必要 mcpb」未満として扱う
2. パスごとに必要なトークンを確認:
   - 全パス共通: `github.valid: true`
   - Web-Vercel: `vercel.valid: true`
   - Stripe: `stripe.test` / `stripe.live`
   - Supabase: `supabase.valid: true`
   - AI 機能: `anthropic.valid: true`
3. **`github.repo_target` を読み、リポジトリの作成先を確定する**（[作成先の決定ルール](#作成先の決定ルールorg-or-個人)）。
   `personal:` になっていて Org に置きたい場合は、Phase 3 のプランで作成先を明示して承認を取り、
   `github_create_repo_and_push` に `owner_override: "<org slug>"` を渡す
4. 不足 → `setup-deploy-environment` を案内して中断

> `health_check` はトークンの**有効性**しか見ない。「リポジトリを作れるか」までは判定できないため、
> 403 が出たら第一容疑は権限ではなく**作成先の取り違え**。まず `repo_target` を疑うこと。

### 使用する拡張ツール

| ツール | 用途 |
|---|---|
| `github_create_repo_and_push` / `github_push` | リポ作成+push / 再push |
| `vercel_create_project_and_deploy` / `vercel_get_deployment_status` / `vercel_get_build_logs` | Vercel |
| `supabase_*` | Supabase 操作一式 |
| `stripe_*` | Stripe（`mode:"test"` 既定） |

---

## Phase 1: アプリ定義

### Step 1-A: 入力解析

| 分類 | 判定基準 | 次 |
|------|---------|-----|
| **detailed** | 業種+エンティティ+ロール+規模+機能 のうち 3 つ以上 | Phase 2 |
| **sparse** | 業種だけ・ジャンルだけ | Step 1-B |
| **既存コードあり** | 「フォルダがある」 | Phase 3 (軽量パス) |

### Step 1-B: ギャップ埋め（sparse のみ）

**業種から推測した候補を提示**。質問は 2-3 個まで。残りはデフォルト値で進める。

### Step 1-C: アプリ定義シート確定

| 項目 | 例 |
|------|-----|
| PROJECT_NAME | FlowerInventory |
| PROJECT_NAME_LOWER | flower-inventory |
| PROJECT_DESCRIPTION | 花屋向けの在庫管理アプリ |
| 業種 | 小売 / 飲食 / 教育 / 医療 等 |
| エンティティ | 主要な名詞 3-7 個 |
| ユーザー種別 | 1-4 ロール |
| 主要機能 | 5-10 個 |
| 機密性レベル | 公開可 / 個人情報あり / 機微情報あり |
| 想定規模 | ~50 / ~500 / 5000+ 人 |
| 課金 | 無料 / 月額 / 一回購入 / 内部利用のみ |
| **管理画面** | **要 / 不要**（ユーザー種別に「運営・管理者」があれば要） |
| **非機能** | `nonfunctional.yaml` の 7 項目（下記） |

**非機能は「決めていない」を既定値にしない。** harness-init が置く `nonfunctional.yaml` の
冒頭に不変条件 7 行がある。機密性レベル・想定規模・課金から、この案件で決めるべきことを
自分で洗い出し、`decided` を埋める（「不要」「許容する」も決定）。プラットフォームが黙って
選ぶ値（プラン・リージョン・バックアップの有無など、自分で見つけたもの）は
`accepted_defaults` に決定として書く。**人に聞くのは、機密性レベルと復旧の許容範囲の 2 点**
まで。ここで決めた内容は、Phase 4 で harness-init がファイルを置いた直後に書き込む。
空欄が残ると `deploy-preflight` が FAIL で止める。

**管理画面が「要」なら [references/admin-console.md](references/admin-console.md) を必ず読んでから実装する。**
利用者画面と管理画面はルートグループで最初から分ける。後から分けるのは面倒で、
1ページに全機能を積んだ管理画面は必ず作り直しになる。

---

## Phase 2: ターゲット判定

### Step 2-1: ターゲットプラットフォーム

| トリガー | ターゲット | パス |
|----------|-----------|------|
| 「Electronで」「デスクトップアプリ」「PCにインストール」「オフラインで使いたい」 | **Desktop** | Phase 4-D |
| 「iPhoneアプリ」「Androidアプリ」「モバイルアプリ」「ネイティブアプリ」 | **Mobile** | Phase 4-M |
| 「ローカルで動かしたい」「コンテナで配布」「Docker で渡したい」「スタンドアロン」 | **ローカル出力** | Phase 4-L |
| LP / SaaS / 予約 / EC / 管理画面 / 指定なし | **Web**（既定） | Step 2-2 へ |

### Step 2-2: Web インフラ判定（Web パスのみ）

| 機密性 | 規模 | 推奨 |
|--------|------|------|
| 公開可 (LP/コーポ) | 任意 | **Vercel** (or AWS 静的) |
| 個人情報あり | ~500 | **Vercel + Supabase** |
| 個人情報 + Stripe | ~500 | **Vercel + Supabase + Stripe** |
| 大規模 / 業務系 / 機微情報 | 5000+ | **AWS** |

---

## Phase 3: プラン承認

ターゲット + 構成をプランとして提示し、承認を取る。

```
=== 構築プラン ===
【アプリ定義】名前 / 業種 / 概要
【ターゲット】Web / Desktop / Mobile / ローカル
【構成】Vercel + Supabase / Electron + SQLite / React Native 等
【作成先】ai-osi-uri org 配下 / 個人アカウント配下（health_check の repo_target）
【配布方法】Vercel URL / GitHub Releases / TestFlight 等
【非機能】復旧の許容範囲 / 想定負荷 / 受け入れた既定値（nonfunctional.yaml の要約 3 行）

このプランで進めますか？
```

**【作成先】は省略しない。** ここを黙って進めると、意図と違う場所にリポジトリができ、
後から移すか作り直すことになる。

---

## Phase 4: パス別実行

### Web-Vercel パス (Phase 4-W-V)

> 詳細: [references/web-vercel-path.md](references/web-vercel-path.md)
> 落とし穴集: [references/gotchas.md](references/gotchas.md)
> **管理画面を含むなら: [references/admin-console.md](references/admin-console.md)（必読）**

```
scaffold → gh-create-repo-and-push → harness-init
→ (Supabase) provision → vercel-connect-and-deploy
→ supabase-set-auth-url → (Stripe) 商品作成 → app-smoke-test
```

**冪等原則**: Vercel プロジェクトは 1 リポにつき 1 つ。env を全部揃えてから 1 回だけ create。

### Web-AWS パス (Phase 4-W-A)

> 詳細: [references/web-aws-path.md](references/web-aws-path.md)
> AWS 固有の罠: [references/aws-app-gotchas.md](references/aws-app-gotchas.md)

```
tf-state-backend → spec.md + infra-decision.md 生成
→ Claude Code 引き渡し (/initialize-project → /setup-infra → /create-app)
→ docker push → ECS → app-smoke-test
```

### Desktop パス (Phase 4-D)

> 詳細: [references/desktop-path.md](references/desktop-path.md)

```
scaffold → gh-create-repo-and-push → harness-init
→ electron-scaffold-and-build（ローカルビルド確認）
→ desktop-release-monitor（GitHub Actions でリリース監視）
```

**呼び出すスキル:**
- `electron-scaffold-and-build` — Electron Forge で scaffold + ビルド
- `desktop-release-monitor` — GitHub Actions リリースパイプライン監視

### Mobile パス (Phase 4-M)

> 詳細: [references/mobile-path.md](references/mobile-path.md)

**`osi-mobile-deploy` プラグインの `deploy-mobile-app` に委譲する。**

```
create-app が Phase 0-3 でアプリ定義を確定
→ deploy-mobile-app に定義を渡す
→ mobile-app-scaffold → ios-testflight-deploy / android-play-deploy
→ mobile-app-smoke-test
```

`osi-mobile-deploy` プラグインが未インストールの場合は案内して中断。

**利用可能なモバイル atomic:**
| スキル | 責務 |
|--------|------|
| `deploy-mobile-app` | モバイルオーケストレータ |
| `mobile-app-scaffold` | React Native / Swift / Kotlin テンプレ |
| `ios-testflight-deploy` | TestFlight 配布 |
| `android-play-deploy` | Play Console 配布 |
| `mobile-app-smoke-test` | モバイル動作確認 |
| `mobile-firebase-setup` | Firebase 初期設定 |
| `mobile-icon-generator` | アイコン生成 |
| `mobile-secrets-sync` | シークレット管理 |
| `mobile-crash-triage` | クラッシュ分析 |
| `mobile-update-deploy` | モバイル更新 |

### ローカル出力パス (Phase 4-L)

> 詳細: [references/local-output-path.md](references/local-output-path.md)

サーバにデプロイせず、ローカル実行可能な形式で出力する。

```
scaffold → gh-create-repo-and-push → harness-init
→ local-project-output（プロジェクト一式を出力）
  or app-builder-export（.appbuilder.json 台帳スペック → App Builder に取り込む）
  or app-builder-container-export（単一イメージ .tar.gz → App Builder に取り込む＝生アプリ）
```

**呼び出すスキル:**
| スキル | 用途 |
|--------|------|
| `local-project-output` | プロジェクトフォルダをそのまま出力（受け手が npm install / npm start） |
| `app-builder-export` | 設定駆動の台帳スペック `.appbuilder.json` を書き出し、オンプレの App Builder に取り込む |
| `app-builder-container-export` | 任意スタックの生アプリを単一イメージ `.tar.gz` にして書き出し、App Builder に取り込む（生アプリ） |

---

## 決済実装（本番化）が必要になったタイミングの分岐

「決済を実装したい」「本番化したい」「Stripeを有効にしたい」と言われたら、**そのアプリが
何で作られたか**で使うスキルを切り替える。create-app 自身は Lovable プロジェクトの
作成・改修は扱わないため、Lovable 案件は最初からこの分岐で委譲する。

| 対象 | 使うスキル |
|---|---|
| Lovable で作られたプロジェクト | `lovable-payments-golive`（Lovable 内蔵 Payments。AI OSI URI Deploy 拡張は使わない） |
| create-app で作った Web（Vercel/AWS）アプリ | `switch-to-live-mode`（AI OSI URI Deploy 拡張 + Live キーで再作成） |
| どちらか不明 | ユーザーに一言確認してから振り分ける |

---

## 共通後処理

### Phase N-1: Drive 記録（必須ゲート）

> 詳細: [references/drive-record.md](references/drive-record.md)

1. `アプリ情報_README.md` を生成（公開URL / リポ / 構成 / 更新手順）
2. `_アプリ台帳.md` に 1 行追記
3. evidence を `deploy-progress.md` に貼る

**DoD**: この記録なしに完了レポートを出さない。

### Phase N-0.5: 使い方マニュアル（必須ゲート）

> 実行: `app-manual` スキル（`REPO_DIR` / `APP_URL` / `APP_NAME` を渡す）

**人が使うアプリを作ったなら、手順書までが納品。** 動くものだけ渡しても、
現場は最初のログインで止まる。

1. 実装（ルート・画面のラベル・サーバーアクション・メール文面・認証方式）から起こす
   — 記憶や会話履歴から書かない
2. 運営・現場向けの pptx を作る。会員・顧客が触る画面があるなら利用者向けも別ファイルで
3. 画像にして全ページ目視（はみ出しが必ず出る）
4. Drive の同じ案件フォルダに格納。旧版は `_旧版/` へ

**DoD**: マニュアルを格納するまで完了レポートを出さない。
社内の管理ツール等で明らかに読み手がいない場合のみ省略でき、その場合は
完了レポートに「マニュアル: 不要（理由）」と明記する。

### Phase N: 完了レポート

検証チェックリストの全項目に evidence を貼れたときだけ完了。
未検証は「未検証: ○○」と正直に明記。

---

## ハーネス: deploy-progress.md（必須）

最初の実作業に入る前に作成し、各フェーズの完了時に更新。

```markdown
# Deploy Progress — {PROJECT_NAME}
更新: {YYYY-MM-DD HH:MM}

## 確定事項
- ターゲット: {Web-Vercel|Web-AWS|Desktop|Mobile|ローカル}
- リポジトリ: {REPO_URL or 未作成}

## 完了（evidence 付き）
## 進行中
## 次セッションでの再開手順
```

---

## エラーハンドリング

| Phase | 失敗 | 対応 |
|---|---|---|
| 0 | 拡張未導入 / トークン不足 | setup-deploy-environment 案内 |
| 4 | リポジトリ作成が 403 | **まず作成先を疑う。** エラー本文の `target` を見る。`user/repos` なら個人に作りにいっている → `owner_override` に Org slug を渡して再実行。`orgs/<slug>` なら PAT の Resource owner / Administration 権限を確認 |
| 1 | 業種不明 | 再度聞く |
| 2 | ターゲット不確定 | デフォルト Web-Vercel |
| 3 | プラン却下 | Phase 1-2 に戻る |
| 4-M | osi-mobile-deploy 未インストール | プラグインインストールを案内 |
| 4 各パス | ビルド/デプロイ失敗 | 各 references のエラーハンドリングに従う |

---

## 関連スキル（osi-deploy プラグイン内）

**共通 atomic:**
- `gh-create-repo-and-push` — GitHub push
- `harness-init` — エージェント足場
- `app-smoke-test` — HTTP 検証
- `app-manual` — 使い方マニュアル（実装から起こす。Phase N-0.5）
- `setup-deploy-environment` — 初期設定

**Web パス:**
- `vercel-connect-and-deploy` — Vercel 接続+デプロイ
- `aws-static-deploy` — S3+CloudFront
- `supabase-set-auth-url` / `supabase-multitenant-rls` — Supabase 設定
- `tf-state-backend` — Terraform state
- `gcp-ops` — GCP 操作
- `switch-to-live-mode` — Stripe test→live（Vercel/AWS + Deploy拡張前提。Lovableは対象外）
- `lovable-payments-golive` — Lovable 内蔵 Payments の有効化〜Go Live（Lovable プロジェクト専用）
- `nextjs-pdf-export` / `scroll-3d-website` — テンプレ

**Desktop パス:**
- `electron-scaffold-and-build` — Electron scaffold + ビルド
- `desktop-release-monitor` — GitHub Actions リリース監視

**Mobile パス（委譲）:**
- `deploy-mobile-app`（osi-mobile-deploy） — モバイルは全面委譲。詳細は [references/mobile-path.md](references/mobile-path.md)

**ローカル出力:**
- `local-project-output` — プロジェクト出力（生ソース一式）
- `app-builder-export` — 台帳スペック(.appbuilder.json)を App Builder に取り込む
- `app-builder-container-export` — 生アプリを単一イメージ tar にして App Builder に取り込む

**運用:**
- `update-deploy` — **初回デプロイ後の更新はこちら**
- `app-concierge` — 非エンジニア向け入口

**別プラグイン（osi-mobile-deploy）:**
- `deploy-mobile-app` — モバイルオーケストレータ（Phase 4-M で委譲）
