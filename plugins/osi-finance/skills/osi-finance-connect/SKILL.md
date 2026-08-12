---
name: osi-finance-connect
description: >
  AI OSI URI Finance 拡張（請求管理台帳の読み書き＋MoneyForward
  クラウド請求書ポーリング）の **OAuth 接続を Claude in Chrome で伴走して通す** 初期セットアップ・
  アトミックスキル。MoneyForward クラウド請求書のアプリ登録（アプリポータル）→OAuth認可（scope は data.write）→
  refresh_token 取得→コネクタへ貼り付け→疎通確認（health_check / mfi_list_billings）までを、
  ブラウザ画面操作で半自動に進める。「OSI Finance のMF連携をして」「請求書APIをつないで」「AI OSI URI Finance を
  接続して」「refresh_token を取って」「MoneyForward 請求書のOAuthを通して」「台帳同期コネクタを
  セットアップして」「Chromeで連携手順をやって」などで発動する。オーケストレータ osi-finance-setup の
  コネクタ接続ステップから呼ばれることも、単体で呼ばれることもある。
  ※ 日常運用（請求書発行・突合・月次）は osi-finance-* 各スキルの役割。本スキルは「接続を通す」ことに特化する。
requires_connectors:
  - server: claude-in-chrome
    provision: user-install
  - server: AI_OSI_URI_Finance
    provision: mcpb
  - server: money-forward
    provision: user-install
---

# osi-finance-connect（AI OSI URI Finance の OAuth 接続を Chrome 伴走で通す）

> **役割**：`AI OSI URI Finance` 拡張（.mcpb）に必要な認証情報を、Claude in Chrome で画面を
> 一緒に操作しながら取得し、コネクタ設定に入れて疎通確認まで持っていく。**接続を通す**ことだけが責務。
>
> **前提**
> - `AI OSI URI Finance` 拡張がインストール＆**有効**になっている（設定→コネクタ→デスクトップ）。
> - `Claude in Chrome` 拡張が接続済み。
> - 対象ブラウザに、対象組織の MoneyForward に**ログイン済み**であること。
>
> **安全原則（厳守）**
> - **利用規約への同意・OAuthの「許可」ボタンは必ずユーザーに確認**してから押す（または本人に押してもらう）。
> - **秘匿情報（client_secret / refresh_token / SA鍵）はチャット本文に貼らない。** 受け渡しは
>   outputs に作る一時ファイル経由にし、コネクタへ貼り付け後にユーザーへ削除を依頼。こちらの一時
>   ファイル（トークンJSON等）も完了後に `rm` する。
> - コネクタ設定欄への入力は**ユーザーが行う**（私は値を用意するだけ）。
> - 送金・台帳の自動確定はしない（他 osi-finance スキルと共通）。

接続は対話形式。各画面でスクリーンショットを撮って状態を確認し、ゲート（規約同意・許可）で止まる。

---

## Part A: MoneyForward クラウド請求書 の OAuth 接続（v0.2 で必要）

> MoneyForward クラウド請求書 API v3 を使う。発行済み請求書を `GET /billings` で取得し、
> 請求書番号(INV)で台帳と突合してステータスを書き戻す（sync_ledger）。請求書の発行
> （`mfi_create_billing`）も行うため、**scope は `mfc/invoice/data.write` を要求する**。
> `.read` だけだと発行が 403 で落ちる。

### A-0. 確認できている確定値（実装と一致）
- API ベース: `https://invoice.moneyforward.com/api/v3`（コネクタ既定 `MFI_API_BASE`）
- 認可: `https://api.biz.moneyforward.com/authorize`
- トークン: `https://api.biz.moneyforward.com/token`（コネクタ既定 `MFI_TOKEN_URL`）
- アプリ登録は「アプリポータル」。クライアント認証方式は **CLIENT_SECRET_POST**（拡張の実装に一致）。

### A-1. クラウド請求書を開く（必要なら有効化）
1. `mcp__Claude_in_Chrome__navigate` で `https://invoice.moneyforward.com/api/documentation` を開く。
2. **アカウント選択／事業者選択が複数回挟まる**ことがある（マネーフォワードID→事業者一覧→…）。
   既存ログイン済みアカウント・対象事業者を選んで進む（パスワード入力は発生しない想定）。
3. 初回利用の組織だと「**以下に同意して利用を開始する**」（クラウド請求書の利用規約同意）が出る。
   → **規約同意ゲート。ユーザーに確認**してから押す。
4. 「API連携（開発者向け）」で「**APIの利用を開始する**」を押す → 別タブで「アプリポータル」が開く。

### A-2. アプリポータルで連携アプリを作成
1. 「マネーフォワード IDでログイン」→ アカウント選択 → 事業者「選択」。
2. 左メニュー「**アプリ開発 [開発者向け]**」→「**新規登録**」。
3. フォーム入力（`browser_batch` でまとめて）：
   - **アプリ名称**: `AI OSI URI Finance`
   - **リダイレクトURI**: `http://localhost:8765/callback`
     （実際にサーバは立てない。認可後にブラウザがこのURLへ遷移し、**URLのクエリに付く code を
     `tabs_context_mcp` で読み取る**。ポート番号は任意だが後段の token 交換で同じ値を使う）
   - **クライアント認証方式**: `CLIENT_SECRET_POST` を選択
4. 「**利用規約に同意する**」チェック＋「**登録**」 → **規約同意ゲート。ユーザーに確認**してから実行。
5. アプリ詳細で **Client ID** を控える。**Client Secret** は目アイコンで表示して読む。
   - ⚠️ **Secret は UI上で2行に折り返して表示される**ことがある。`zoom` で**全体を読み、改行を除いて
     1本に連結**する（途中で切らないこと）。

### A-3. 認可（コネクタが自分でトークンを受け取る）

**手作業の curl は不要。** 拡張の `mfi_connect` ツールが認可を最後まで面倒を見る。

1. `mfi_connect` を呼ぶ。認可URL（scope は `mfc/invoice/data.write`）が返る。
2. その URL をユーザーに開いてもらう。アカウント選択→事業者選択→「**アプリとの連携を
   許可しますか？**」が出る。
   → **OAuth許可ゲート。ユーザーに確認**してから許可してもらう。
   **権限に「書き込み」が含まれることをこの画面で必ず確認する。**「データ参照」だけなら
   scope が効いていないので、そのまま進めても発行はできない。
3. 許可すると `http://localhost:8765/callback` へ戻り、**拡張が code を受け取ってトークン交換し、
   refresh_token を自分で保存する**（`~/.ai-osi-uri-finance/` に 0600）。ブラウザには
   「接続しました」と付与された scope が表示される。
4. `mfi_connect_status` で結果を確認する。`state: done` かつ scope に `write` が含まれていれば成功。
   含まれていなければ警告が返るので、やり直す。

> 認可の待ち受けは 300 秒で閉じる。時間切れなら `mfi_connect` からやり直せばよい。
> ポート 8765 はアプリポータルに登録したリダイレクトURIと一致させている（変更する場合は両方直す）。

### A-4. コネクタへ貼り付け

`refresh_token` の貼り付けは不要（A-3 で拡張が保存済み）。設定に入れるのは
**Client ID と Client Secret の2つだけ**で、これはアプリポータルで各組織が自分のアプリを
登録して得る値。初回に一度きり。

### A-5. 疎通確認
- `mcp__AI_OSI_URI_Finance__*` ツールを ToolSearch で読み込み、`health_check` →
  `moneyforward_invoice: ok（トークン取得成功）` を確認。
- `mfi_list_billings` で取得確認（0件でも接続成功）。

---

## 落とし穴まとめ（実運用の知見）
- **アカウント/事業者選択は何度も挟まる**。都度スクショで確認して進む。
- **Client Secret は2行折り返し表示**になることがある → 連結して1本に。
- **redirect_uri は登録値と完全一致**させる（token 交換でも同じ文字列）。
- **code は短命** → 取得したら即 token 交換。
- token 交換は **sandbox bash の curl で可能**（MFは到達OK／401で疎通確認）。
- **発行済み請求書が無い組織は billings が空**。配管成功と空データは別物（正常）。
- **秘匿情報はチャットに出さない**。ファイル受け渡し→貼付→削除。
- 規約同意・OAuth許可は**必ずユーザー確認**。

## 完了後
- `osi-finance-setup` から呼ばれた場合は、接続結果（google_auth_mode / moneyforward_invoice）を
  オーケストレータへ返す。
- 日次同期は別途 scheduled task（`sync_ledger`、初期は dry_run）で回す。
