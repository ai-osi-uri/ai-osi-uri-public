---
name: create-app
description: |
  自社が Claude から
  **アプリを新規に作って公開する**ための唯一のオーケストレータ。Web（Vercel / AWS / Cloudflare / Railway）
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
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
  - server: aws-api
    provision: user-install
  - server: slack
    provision: user-install
# 手元が要る準備（get_skill が「手元の準備」の節を出す。導入手順は osi-core:local-setup）
local_setup: [ext-deploy]
# スキルの一覧（つないだときに Claude に渡す）に出す短い用途
label: アプリ・サイトを新しく作る
---

# create-app v1.0 — 汎用アプリ作成エントリポイント

> **Git の道（2026-10-16）**：Git の push・取り込みは**手元の Deploy 拡張の道具（`github_push`・`github_clone`・`github_pull` など）が基本**（差分だけを送るので大きなリポジトリでも軽い）。
> 入っていなければ、先に入れる（get_skill の頭の「手元の準備」→ `local_tools_status` → 本人が「インストール」を1回押す）。
> 入れられない・断られたとき（ブラウザ版の Claude など）や小さなアプリだけ、URL でつなぐコネクタの `github_upload_url` → `github_push_folder` ／ `github_download_folder` を予備に使う
> （毎回フォルダ全体を zip で送るので 1 回 200MB まで）。手順は osi-deploy の update-deploy の `references/git-via-url-connector.md`。

> **組織固有値はプロファイルから読む。** 本文の `{{paths.*}}` `{{ledgers.*}}` `{{company.*}}` `{{members.*}}` は、連結フォルダ直下の `osi-profile.md`（雛形: `config/osi-profile.example.md`）の値に置き換えて解釈する。無ければ会社名・案件フォルダ・台帳の有無・使うコネクタを質問して先に作る。値をここに直書きしない。

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
7. **画面はオブジェクト基準・横幅いっぱい**: ナビ（サイドバー）に並べるのはオブジェクトの一覧だけ。「〜する」はそのオブジェクトの画面の中のボタン。「使い方・設定」はフッター。本文は画面の横幅いっぱいに使い、`max-width` で中央に寄せない → [references/screen-structure.md](references/screen-structure.md)
8. **待ちは必ず見せる（必須・試作でも省かない）**: 画面遷移の進み具合バー（layout に `NavigationProgress`）、本文の「読み込み中…」（`app/loading.tsx`）、ボタンの処理中表示（`useFormStatus` で押せなくして文言を変える）の3つを必ずそろえる。押したのに何も起きない時間を作らない → [references/screen-structure.md](references/screen-structure.md) の「ローディング表示の入れ方」
9. **一覧は全件を読まない（必須）**: どの一覧にも、はじめから検索欄とページ送り（既定 50 件）を付け、絞り込みはサーバ（DB）で行う。一覧の API は 1 ページ分と全件数だけ返す。検索・ページは URL に残す → [references/screen-structure.md](references/screen-structure.md) の「一覧の組み方」
10. **詳細は決める場所でタブに分ける**: 1件の画面は自分の URL を持つ（ドロワーにしない）。項目が増えたら「誰が・どこで決める設定か」でタブに分け、先頭の「概要」に「いまの値・決まっている場所・どこで変えるか」を並べる。1 つの設定を変えられる場所は 1 か所だけ → [references/screen-structure.md](references/screen-structure.md) の「1件の画面（詳細）の組み方」

---

## 作成先の決定ルール

**作る先（GitHub の作る先）に入れたところに作る。空なら、GitHub の組織に入っていない人は個人アカウントに作り、組織に入っている人には作らずに聞く。**（2026-10-22〜）
道具がトークンの持ち主（GET /user）と所属組織（GET /user/orgs）を見て決める。
10/20 の事故（組織名が空のまま別の owner を指定すると黙って個人に作り、返事には指定した owner の名前を返した）は、
「作る先が空のまま別の組織を指定されたら作らない」「返事は GitHub が実際に作った先を正にする」で防ぐ。

| 経路 | 作る先 | 作る先が空のとき |
|---|---|---|
| ローカル（.mcpb） | 拡張設定の「GitHub Organization」（`health_check` の `github.repo_target`） | `auto:<ユーザー名>`。組織に入っていなければ個人アカウント、入っていれば聞く |
| リモート・お試し | 自社の org に固定（名前に会社の接頭辞が付く）。個人アカウントには作れない | — |
| リモート・自分の鍵 | 鍵設定の「GitHub の作る先」（`github.org`）。組織名か自分のユーザー名 | 組織に入っていなければ個人アカウント、入っていれば聞く |

- 作ったら、返事の `owner_type`（`user`＝個人／`org`＝組織）と `repo` を本人に一言で伝える（例：「個人アカウント taro に customer-karte を作りました」）。`auto_target: true` は作る先が空で個人に決めた印
- 道具が `needs_target`（組織に入っている）で止まったら、`orgs` の名前を見せて「どの組織に作るか／個人アカウントにするか」を聞き、鍵設定（https://www.ai-osi-uri.info/keys#app）の「GitHub の作る先」に入れてもらってから作り直す
- 会社のアプリなら組織に置くほうを勧める（担当が変わっても引き継げる）。個人で良いと言われたらそのまま進める
- 作ったあとは、返事の `repo` と `html_url` の持ち主が作る先と同じかを必ず見る。違えば中身を入れずに止めて報告する
- 403 / 404 が返ったら、トークンにその作る先へ作る権限が無い（組織なら組織の承認・Administration の書き込み、個人なら repo 権限）。別の場所に作り直さない
- GitHub を組織にしたら、Vercel / Supabase もチーム・組織の側に寄せる

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
  Vercel:     Phase 4-W-V → references/web-vercel-path.md
  AWS:        Phase 4-W-A → references/web-aws-path.md
  Cloudflare: Phase 4-W-C → references/web-cloudflare-path.md
  Railway:    Phase 4-W-R → references/web-railway-path.md

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
Phase N-0.5: 使い方マニュアル → app-manual
Phase N-0.3: 事例に載せる（お客さまのアプリのとき）→ 道具 add_case
Phase N:   完了レポート
```

---

## 動作要件

必要 mcpb（AI OSI URI Deploy）: >= 1.23.0（リモート経路は上の読み替え表）

## 経路の判定: ローカル（.mcpb）かリモート（マネージド）か

道具は 2 つの経路のどちらかで来る。**最初の `health_check` の返り方で判定し、以後は読み替え表に従う。**

| 見分け方 | 経路 |
|---|---|
| `health_check` が JSON（`server_version` / `github.valid` …）で返る | **ローカル**（.mcpb・自分の鍵）。本文どおりに進める |
| `health_check` がテキストで返り、`managed :` と `tools : Deploy N 道具` の行がある | **リモート**（マネージド・自社の Machine Account の鍵）。下の読み替え表に従う |

### リモート経路の読み替え表

| 本文の手順・道具 | リモートではこうする |
|---|---|
| 「必要 mcpb >= 1.23.0」の版チェック | `tools : Deploy` の道具数が **33 以上**なら続行。少なければ「コネクタを切断→接続し直して」と案内して中断 |
| `github.repo_target` / `owner_override` | お試しでは読まない・渡さない。自分の鍵では鍵設定の「GitHub の組織名」の組織に作る（空なら作らずに止まる）。お試しの作成先は自社の org に固定され、リポ名には会社の接頭辞（`health_check` の `projects : … 名前空間 <slug>-*`）が自動で付く |
| `gh-create-repo-and-push`（`github_create_repo_and_push`） | `github_create_repo`（`name` = アプリの slug、`project_name` = 表示名）→ `github_put_files`（`files: [{path, content}]` を **1 コミット**で。`node_modules` / `.next` / `.env*` は含めない。合計 200 ファイルや 5 MB を超えそうなら数回に分けて push する） |
| `github_push`（再 push） | 変更したファイルだけを `github_put_files`（同じブランチ・上書き） |
| `vercel-connect-and-deploy`（`vercel_create_project_and_deploy`） | `vercel_create_project`（`repo_name`, `env_vars`, 必要なら `framework`）→ `vercel_get_deployment_status` で READY を待つ。clone / push は要らない |
| `supabase_create_project` | `organization_id` と `db_pass` 以外は同じ。`project_slug` は稼働案件が 1 本なら省略可。以後の `supabase_*` は返ってきた `ref` で呼ぶ |
| `from_extension`（`vercel_set_env`） | 使えない。値は `value` で渡す |
| 案件台帳への登録 | 不要（`github_create_repo` / `vercel_create_project` / `supabase_create_project` が自動で「公開中のアプリ」に載せる） |
| `[quota_exceeded:…]` / `[managed_disabled]` が返る | 上限・残高・利用権の停止。作業を止めて理由を伝え、運用者への相談を案内する（`usage_status` で残りが見える） |
| `[quota_exceeded:projects]` / `[quota_exceeded:resources]`（お試しの枠：アプリ 2 本・GitHub 2・Vercel 2・Supabase（データベース）1。画像・動画は生成枠で `[quota_exceeded:generation]`）／本人が枠を超えて作りたい／Stripe の鍵が未登録 | お試し（マネージド）は体験用。`own-keys-setup` に渡し（やりたいこと `app`、決済なら `pay`）、鍵がそろって「自社アカウント」に切り替わったら、止まったところから続ける |

リモートで**使えない**道具: `github_create_repo_and_push` / `github_push` / `github_clone` / `aws_terraform_*` / `mobile_*`（ローカル FS が要る）。Web-AWS・Desktop・Mobile パスはローカル経路でのみ実行できる。リモートでそれらを求められたら「この経路では Web-Vercel だけ」と伝える。

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
   - Web-Cloudflare: `cloudflare.valid: true`（+ `cloudflare_health_check` で権限を個別確認）
   - Web-Railway: `railway.valid: true`（+ `railway_health_check` で作成先ワークスペースを確認）
   - Stripe: `stripe.test` / `stripe.live`
   - Supabase: `supabase.valid: true`
   - AI 機能: `anthropic.valid: true`（URL のコネクタでは、鍵設定に Anthropic・OpenAI・TypeSafe の鍵があるか。アプリへは `vercel_set_env` の `from_extension` で値を見せずに入れる）
3. **`github.repo_target` を読み、リポジトリを作る組織を確定する**（[作成先の決定ルール](#作成先の決定ルール組織だけ)）。
   `none` は GitHub が未接続。`auto:<名前>` は作る先が空（組織に入っていなければ個人アカウントに作る）
4. 不足 → `setup-deploy-environment` を案内して中断。**発行そのものが必要なら `credential-handoff` に渡す**
   （何のため／どこで生まれる／どこで使う／どう確かめる を添える）。「○○で発行して貼ってください」と
   文章で説明して止まらない。鍵の値は受け取らない

> `health_check` はトークンの**有効性**しか見ない。「リポジトリを作れるか」までは判定できないため、
> 403 / 404 が出たら、トークンがその作る先に作る権限を持っているかを確かめる。別の場所に作り直さない。

### 使用する拡張ツール

| ツール | 用途 |
|---|---|
| `github_create_repo_and_push` / `github_push`（ローカル）、`github_create_repo` + `github_put_files`（リモート） | リポ作成+push / 再push |
| `vercel_create_project_and_deploy`（ローカル）、`vercel_create_project`（リモート） / `vercel_get_deployment_status` / `vercel_get_build_logs` | Vercel |
| `supabase_*` | Supabase 操作一式 |
| `stripe_*` | Stripe（`mode:"test"` 既定） |
| `cloudflare_deploy_worker` / `cloudflare_deploy_status` / `cloudflare_d1_*` / `cloudflare_r2_*` | Cloudflare（Workers / D1 / R2） |
| `railway_create_service` / `railway_add_database` / `railway_create_domain` / `railway_deployment_status` | Railway（常駐サーバー / DB） |

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
| **判定（Jev）** | **使う / 推奨カードのみ**（主要機能に「振り分け・チェック・分類・点数付け」があり、**TypeSafe の鍵があるときだけ**「使う」） |
| **画面構成** | **ナビに出すオブジェクト（名詞）1〜5 個**と、各オブジェクトの「作る／一括／1件」の動詞の置き場（下記） |
| **非機能** | `nonfunctional.yaml` の 7 項目（下記） |

**非機能は「決めていない」を既定値にしない。** harness-init が置く `nonfunctional.yaml` の
冒頭に不変条件 7 行がある。機密性レベル・想定規模・課金から、この案件で決めるべきことを
自分で洗い出し、`decided` を埋める（「不要」「許容する」も決定）。プラットフォームが黙って
選ぶ値（プラン・リージョン・バックアップの有無など、自分で見つけたもの）は
`accepted_defaults` に決定として書く。**人に聞くのは、機密性レベルと復旧の許容範囲の 2 点**
まで。ここで決めた内容は、Phase 4 で harness-init がファイルを置いた直後に書き込む。
空欄が残ると `deploy-preflight` が FAIL で止める。

**Jev はオプション。鍵があるときだけ使い、無ければ使わない。** 判定の箇所があれば [references/jev-in-app.md](references/jev-in-app.md) を読む。
- 鍵がある（お客様自身の TypeSafe の鍵。社内の見本は当社の鍵）→ 判定の部分を Jev で作り、自信の低いものを人が確認する画面を付ける。
- 鍵が無い → Jev は組み込まず、従来どおり作る。そのうえで完了レポートと提案資料に **「推奨オプション」カード**（jev-in-app.md のひな形）を 1 枚添える。
- お客様に納めるアプリに当社の鍵を入れない。

**管理画面が「要」なら [references/admin-console.md](references/admin-console.md) を必ず読んでから実装する。**
利用者画面と管理画面はルートグループで最初から分ける。後から分けるのは面倒で、
1ページに全機能を積んだ管理画面は必ず作り直しになる。

**画面構成は [references/screen-structure.md](references/screen-structure.md) の原則で組む（必読・全パス共通）。**
ナビ（サイドバー）に並べるのは**オブジェクトの一覧だけ**（受注票・顧客・案件…）。
「新しく作る」は一覧画面の右上の主ボタン、「取り込み・書き出し」は同じ場所の副ボタン、
「1件を確定する・出力する」はその1件の画面の中、「使い方・設定」はサイドバーのフッター。
動詞と名詞を同じ列に並べない。`/` は主オブジェクトの一覧へ転送する。
**本文は画面の横幅いっぱいに使う**。`main` に `max-width` を付けて中央に寄せない（表と入力欄が主役の
業務アプリでは、幅を絞ると一画面で見える件数が減る）。中央寄せはログインなど単機能の1枚だけ。
エンティティの中から「人が一覧で見たい名詞」を 1〜5 個選んだものがナビの項目で、
Phase 3 のプランに**【画面構成】**として書き、承認を取る。

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
| 公開可 (LP/コーポ) | 任意 | **Cloudflare Workers**（静的のみなら最安・最速） or Vercel |
| 個人情報あり | ~500 | **Vercel + Supabase**（認証が要るなら既定） |
| 個人情報 + Stripe | ~500 | **Vercel + Supabase + Stripe** |
| 認証不要 + 配信量が多い / コスト最適化 | 任意 | **Cloudflare Workers + D1 + R2** |
| 社内ツール（Cloudflare Access で前段認証） | ~500 | **Cloudflare Workers + D1** |
| 常駐サーバー・WebSocket・ジョブ/cron・Python 等のバックエンド・Dockerfile 前提 | 任意 | **Railway**（+ Postgres / Redis） |
| 大規模 / 業務系 / 機微情報 | 5000+ | **AWS** |

**Vercel と Cloudflare の切り分け**: 判断軸は「**アプリ側で認証が必要か**」。
必要なら Supabase Auth がある Vercel、不要（または Cloudflare Access で足りる）なら
Cloudflare。D1 には RLS も組み込み認証も無いため、認証つき SaaS を Cloudflare に
寄せると自前実装のコストと責任を負う。ユーザーが「Cloudflare で」と明示した場合でも、
認証要件があるなら**このトレードオフを伝えてから**進める。

**Railway を選ぶとき**: 判断軸は「**サーバーレス関数で書けるか**」。常時接続（WebSocket）、
キュー処理・長時間処理、cron、Python / Go などのサーバー、Dockerfile 前提のアプリは Railway。
画面は Vercel・API だけ Railway の併用もよい。Railway にも認証機能は無いので、認証要件があれば
Vercel と同じく Phase 3 で扱いを合意する。

---

## Phase 3: プラン承認

ターゲット + 構成をプランとして提示し、承認を取る。

```
=== 構築プラン ===
【アプリ定義】名前 / 業種 / 概要
【ターゲット】Web / Desktop / Mobile / ローカル
【構成】Vercel + Supabase / Cloudflare Workers + D1 + R2 / Railway + Postgres / Electron + SQLite / React Native 等
【画面構成】ナビに出すオブジェクト（例: 受注票／顧客）と、各一覧の右上に置く操作（例: ＋注文を入れる・取り込み）。本文は横幅いっぱい
【作成先】作る先（health_check の repo_target。組織名・個人アカウント・空なら自動（組織に入っていなければ個人））
【配布方法】Vercel URL / workers.dev URL / *.up.railway.app URL / GitHub Releases / TestFlight 等
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

### Web-Cloudflare パス (Phase 4-W-C)

> 詳細: [references/web-cloudflare-path.md](references/web-cloudflare-path.md)
> wrangler 設定テンプレ: `cloudflare-deploy` スキルの references/wrangler-config.md

```
scaffold → gh-create-repo-and-push → harness-init
→ (D1/R2/KV) リソース先出し → wrangler.jsonc 記述
→ cloudflare-deploy → D1 マイグレーション適用 → app-smoke-test
```

### Web-Railway パス (Phase 4-W-R)

> 詳細: [references/web-railway-path.md](references/web-railway-path.md)

```
scaffold（PORT で listen・/health）→ gh-create-repo-and-push → harness-init
→ (DB) railway_add_database → railway-deploy → app-smoke-test
```

**順序原則**: D1 / KV は**作ってから ID を wrangler.jsonc に書く**。先に deploy すると
バインディング未定義で落ちる。Vercel パスの「env を全部揃えてから 1 回だけ create」と同じ。

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
2. アプリ台帳（`{{ledgers.apps}}`）に 1 行追記
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

### Phase N-0.3: 事例に載せる（お客さまのアプリのとき・必須ゲート）

**お客さまに作って持っていったアプリは、次のお客さまへの提案の引き出しになる。**
アプリが今動いている必要はない。どういう考え方で作ったかと、ソースの場所が分かれば、
次の提案のときに AI がソースを読み、その会社用に組み直せる。後から人が台帳に書く運用は続かないので、
作り終えたこの時点で載せる。

1. 道具 `add_case`（リモートのコネクタ。運営の会社の人だけに見える）を呼ぶ。渡すもの：
   - `repo_url`：ソースの場所（`https://github.com/<org>/<repo>`）。必須
   - `approach`：考え方 ＝〈誰に・なぜ・何を出す提案か〉。要件定義書の冒頭の要約でよい。必須
   - `spec_url`：要件定義書の場所（Drive の URL かリポジトリ内のパス）
   - `pattern`（困りごとの型 A〜G。分からなければ `find_cases` を困りごとの言葉で呼ぶと型の一覧が出る）・
     `industry`・`role`・`problem`・`built`・`period`・`status`（試作なら `trial`）
   - `company_name`・`project_code`：お客さまの社名と案件ID。社名はここにだけ書き、ほかの欄には書かない
2. 同じ `repo_url` の事例がもうあれば、道具は新しく足さずに中身を直す（作り直し・直して出し直しで二重にならない）
3. 載った事例は「候補」として入る。運営が管理コンソールの「事例」で確かめて確定する

**省いてよいとき**：社内用のアプリ・お客さまに出さない試作だけのもの・`add_case` が見えない
（運営の会社の人でない）とき。省いたら完了レポートに「事例: 載せない（理由）」と書く。

**DoD**：お客さまのアプリなら、`add_case` の返事（事例の id）を `deploy-progress.md` に貼るまで完了レポートを出さない。

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
- ターゲット: {Web-Vercel|Web-AWS|Web-Cloudflare|Web-Railway|Desktop|Mobile|ローカル}
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
| 4 | リポジトリ作成が 403 / 404 | 作る先への作成権限が無い。組織なら PAT の Resource owner が組織か・Administration が書き込みか・組織がトークンを承認しているか、個人なら repo 権限を確認。別の場所には作り直さない |
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
- `cloudflare-deploy` — Cloudflare Workers + D1 + R2 + KV / Pages
- `railway-deploy` — Railway（常駐サーバー・ワーカー・cron + Postgres / MySQL / Redis / Mongo）
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
