---
name: osi-finance-connect
description: >
  AI OSI URI Finance 拡張（請求管理台帳＝Googleスプレッドシート読み書き＋MoneyForward
  クラウド請求書ポーリング）の **OAuth 接続を Claude in Chrome で伴走して通す** 初期セットアップ・
  アトミックスキル。MoneyForward クラウド請求書のアプリ登録（アプリポータル）→OAuth認可→
  refresh_token 取得→コネクタへ貼り付け→疎通確認（health_check / mfi_list_billings）までを、
  ブラウザ画面操作で半自動に進める。Google 側も SA鍵（最短）と OAuth（横展開・社外配布）の
  両方の接続手順を持つ。「OSI Finance のMF連携をして」「請求書APIをつないで」「AI OSI URI Finance を
  接続して」「refresh_token を取って」「MoneyForward 請求書のOAuthを通して」「台帳同期コネクタを
  セットアップして」「Chromeで連携手順をやって」などで発動する。オーケストレータ osi-finance-setup の
  コネクタ接続ステップから呼ばれることも、単体で呼ばれることもある。
  ※ 日常運用（請求書発行・突合・月次）は osi-finance-* 各スキルの役割。本スキルは「接続を通す」ことに特化する。
requires_connectors:
  - server: claude-in-chrome
    provision: user-install
  - server: AI_OSI_URI_Finance
    provision: mcpb
---

# osi-finance-connect（AI OSI URI Finance の OAuth 接続を Chrome 伴走で通す）

> **役割**：`AI OSI URI Finance` 拡張（.mcpb）に必要な認証情報を、Claude in Chrome で画面を
> 一緒に操作しながら取得し、コネクタ設定に入れて疎通確認まで持っていく。**接続を通す**ことだけが責務。
>
> **前提**
> - `AI OSI URI Finance` 拡張がインストール＆**有効**になっている（設定→コネクタ→デスクトップ）。
> - `Claude in Chrome` 拡張が接続済み。
> - 対象ブラウザに、対象組織の MoneyForward / Google に**ログイン済み**であること。
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
> 請求書番号(INV)で台帳と突合してステータスを書き戻す（sync_ledger）。**scope は参照のみ
> `mfc/invoice/data.read` で十分**（書き込み発行まで自動化する場合のみ `.write`）。

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

### A-3. 認可（refresh_token 取得）
1. まず **sandbox から token エンドポイントに到達できるか**確認：
   `curl -s -o /dev/null -w "%{http_code}" -X POST https://api.biz.moneyforward.com/token`
   → 401 が返れば到達OK（後段の交換が sandbox bash で可能）。
2. 認可URLへ `navigate`（CLIENT_ID は実値、scope/redirect_uri はURLエンコード）：
   `https://api.biz.moneyforward.com/authorize?client_id=<CLIENT_ID>&redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Fcallback&response_type=code&scope=mfc%2Finvoice%2Fdata.read`
   - PKCE なしで通る（confidential client + CLIENT_SECRET_POST）。
   - ここでも**アカウント選択→事業者選択→次へ**が挟まる。
3. 「**アプリとの連携を許可しますか？**」（アプリ名・事業者・権限=クラウド請求書 データ参照）が出る。
   → **OAuth許可ゲート。ユーザーに確認**してから「許可」を押す（本人に押してもらってもよい）。
4. 許可後、ブラウザは `http://localhost:8765/callback?code=...&iss=...` へ遷移（ページは読めなくてOK）。
   `tabs_context_mcp` を呼び、**タブURLから `code` を抜き取る**。
5. **すぐに**トークン交換（code は短命）。sandbox bash で：
   ```bash
   curl -s -X POST https://api.biz.moneyforward.com/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     --data-urlencode "grant_type=authorization_code" \
     --data-urlencode "code=<CODE>" \
     --data-urlencode "redirect_uri=http://localhost:8765/callback" \
     --data-urlencode "client_id=<CLIENT_ID>" \
     --data-urlencode "client_secret=<CLIENT_SECRET>"
   ```
   → `access_token` / `refresh_token` / `scope` / `token_type=Bearer` / `expires_in=3600` が返る。
   `refresh_token` を控える（access_token は使い捨て）。
6. （任意・確認）取れた access_token で実取得を確認：
   `curl "https://invoice.moneyforward.com/api/v3/billings?per_page=3" -H "Authorization: Bearer <AT>"`
   → `{"data":[...],"pagination":{...}}`。**発行済み請求書が無い組織は `data:[]`** になる（正常）。

### A-4. コネクタへ貼り付け
- outputs に「貼付用」一時ファイル（.md）を作り、`present_files` で渡す。中身は3つ：
  `MFI_CLIENT_ID` / `MFI_CLIENT_SECRET` / `MFI_REFRESH_TOKEN`（`MFI_API_BASE`・`MFI_TOKEN_URL` は既定のまま）。
- ユーザーがコネクタ「AI OSI URI Finance」設定へ貼り付け → 保存 → **貼付用ファイルを削除**してもらう。
- こちらの一時トークンJSON等も `rm` する。

### A-5. 疎通確認
- `mcp__AI_OSI_URI_Finance__*` ツールを ToolSearch で読み込み、`health_check` →
  `moneyforward_invoice: ok（トークン取得成功）` を確認。
- `mfi_list_billings` で取得確認（0件でも接続成功）。

---

## Part B: Google 側の接続

Google は2方式。**今すぐ動かすなら SA、横展開・社外配布なら OAuth**（拡張は両対応・OAuth優先）。

### B-1. サービスアカウント（SA）方式 ＝ 最短・社内/単体運用
1. Google Cloud で SA を作成 → **JSON鍵**をダウンロード。
2. その GCP プロジェクトで **Google Sheets API を有効化**。
3. 請求管理台帳を **SAメール(client_email) に「編集者」で共有**（※ここだけ人手の初期作業）。
4. コネクタの `Google サービスアカウント鍵 (JSON)` に貼り付け。
5. `health_check` → `google_auth_mode: sa` / `ok`、`sheets_list_tabs` で台帳が読めるか確認。
- 落とし穴：SAのプロジェクトを作り替えたら、**新SAメールへ共有し直す＋新プロジェクトでSheets API有効化**。
  共有漏れは `sheets_*` が **403 PERMISSION_DENIED**（health_check は ok でも起きる）。

### B-2. OAuth ユーザー認可方式 ＝ 横展開・社外配布（個別共有が不要）
> 利点：ユーザー本人のGoogleで認可するので、台帳のSA個別共有が要らない。
> 注意：**社外配布（External）＋Sheetsは機微スコープ → Googleのアプリ審査が必須**。審査通過まで
> テスト扱いで refresh_token が **7日で失効**。本番公開（審査通過）後は無期限。

1. Google Cloud で **OAuthクライアント（ウェブアプリ）**を作成。refresh_token を OAuth Playground で
   取るなら、リダイレクトURIに `https://developers.google.com/oauthplayground` を追加。
2. **OAuth同意画面**：社内のみ=「内部(Internal)」（審査不要・無期限）／社外配布=「外部(External)」
   （要審査）。スコープに `https://www.googleapis.com/auth/spreadsheets` を追加。
3. **refresh_token取得**：OAuth Playground →⚙「Use your own OAuth credentials」に CLIENT_ID/SECRET →
   Sheets スコープを認可 →「Exchange authorization code for tokens」で `refresh_token` をコピー。
   - （Chrome伴走でやる場合）Part A と同様に、自前 redirect への code を拾って
     `https://oauth2.googleapis.com/token` で `grant_type=authorization_code` 交換でもよい。
4. コネクタの OAuth 3項目（`GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN`）に貼り付け
   → 3つ揃うと**OAuthが優先**される。`health_check` → `google_auth_mode: oauth` / `ok`。

### B-3. 社外配布の本番化（Google審査）
- 必要物：同意画面ブランディング（アプリ名・サポートメール・ホームページURL・**プライバシーポリシーURL**）、
  **ドメイン所有権の確認**（Search Console）、機微スコープの**利用理由の説明**、**デモ動画**
  （YouTube限定公開／ユーザーが同意してSheetsを使う様子）。Cloud Console の Verification Center から申請。
- 実レビューは概ね 2〜3営業日（準備のほうが時間がかかる）。**Claude in Chrome は申請フォーム入力の
  補助はできるが、合否は出せない**（Google審査チームの人手レビュー）。

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
