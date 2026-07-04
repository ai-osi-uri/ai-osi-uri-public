---
name: osi-finance-invoice
description: >
  OSI Finance の月次請求書発行。請求管理台帳「月次請求スケジュール」の当月分（請求ステータス=未請求）
  を抽出し、取引先ごとに請求書PDFを生成して `{請求管理ルート}/{送付請求書}/YYYY-MM/` に格納、請求先To
  （CCあり）宛の Gmail 下書きをPDF添付で作成し、台帳のステータスを「下書き済」に更新する。発行者情報
  （社名・登録番号・住所・振込先・採番ルール）は組織固有値として `config/osi-finance-settings.md` を正本とし、
  台帳「発行者設定」または references/invoice-issuer.md（汎用レイアウト）から参照。「今月の請求書を作って」「○○社の請求書を発行」「請求下書きを
  作成」「月初の請求書ドラフト」「請求書PDFを生成してメール下書き」など、請求書発行に関わるリクエストで
  発動する。送信は人が下書きを確認して実行（自動送信しない）。契約の取込・スケジュール展開は
  osi-finance-contract-intake、入金確認は別ワークフロー。
requires_connectors:
  - server: AI_OSI_URI_Finance
    provision: mcpb
  - server: gmail
    provision: user-install
  - server: claude-in-chrome
    provision: user-install
  - server: plaud
    provision: user-install

---

# osi-finance-invoice（月次 請求書発行 → Gmail下書き）

> **組織固有値（社名・登録番号・住所・振込先・税率・採番ルール・Drive ルート／フォルダ名・台帳ファイル名）は
> `config/osi-finance-settings.md`（テンプレ：`config/osi-finance-settings.example.md`）を参照する。** 実値版が無ければ作成を案内。

請求管理台帳の請求予定から請求書を作り、人が送る一歩手前（下書き）まで用意する。

## 役割と非役割

- やる：当月の未請求予定 → **MFクラウド請求書で発行**（AI OSI URI Finance 拡張の `mfi_*`）→ **MF公式PDF**を送付請求書フォルダ（設定の `送付請求書/YYYY-MM/`、例: `02.送付請求書/YYYY-MM/`）格納 → Gmail下書き作成 → 台帳ステータス更新。
- やらない：メール送信（人が実行）／契約取込・スケジュール展開（= osi-finance-contract-intake）／入金確認・消込（別ワークフロー）。
- **自動送信・自動確定はしない。** 下書き作成までで止め、人の確認を待つ。
- **請求書の発行と会計計上は分離。** 売上のMF計上（(借)売掛金/(貸)売上+仮受消費税）は `osi-finance-ar-sync` が担う（発行＝即計上にはしない）。

## 前提コネクタ

- **AI OSI URI Finance 拡張**（`mfi_create_partner` / `mfi_create_billing` / `mfi_get_billing_pdf` / `sheets_*`）＝発行と台帳の読み書き。発行には MF を **data.write スコープ**で接続しておく（osi-finance-connect 参照）。
- Google Drive（公式PDFの格納）、Gmail（下書き作成）。
- 請求書PDFは**MFが生成**（自前PDF生成はしない）。発行者情報・採番・支払条件は `osi-finance-settings` を参照。
- 任意：既存下書きへの確実な添付に Claude in Chrome（ブラウザ操作の `file_upload`）、本文パーソナライズに Obsidian（`obsidian-knowledge-consult`）／Plaud／Drive。無ければ手動・汎用にフォールバック。

## 台帳アクセス（重要）

- `sheets_*`（`sheets_read_schedule` / `sheets_get_values` / `sheets_update_status` / `sheets_update_values`）は **`spreadsheet_id` を必ず明示**する。`osi-finance-settings` の `LEDGER_BILLING_SHEET_ID`（URL `/d/<ここ>/edit`）を使う。拡張のデフォルトID未設定だと `HTTP 404 NOT_FOUND` になり原因が分かりにくい（`health_check` が ok でも起きる）。タブ名：「月次請求スケジュール」「契約マスタ」「発行者設定」。

## 発行者情報（組織固有値・osi-finance-settings 参照）

発行者ブロック（社名・登録番号・住所・振込先・税率・手数料負担）は組織固有値。
**優先順位：台帳シート「発行者設定」→ `config/osi-finance-settings.md` → `references/invoice-issuer.md`（汎用レイアウト）。**
実値はスキルに直書きせず、上記から読み込む（具体値の一覧と差し込みキーは invoice-issuer.md を参照）。

## 手順

### 1. 当月の請求予定を抽出
- 台帳「月次請求スケジュール」から `対象月 = 当月（または指定月）` かつ `請求ステータス = 未請求` を取得。
- 各行に契約マスタ（宛名・住所・To/CC・件名素・金額）を結合。

### 2. 採番（osi-finance-settings の AR 採番ルール）
- 採番形式は `osi-finance-settings` の `AR_NUMBERING`（例：`INV-YYYY-MM-連番3桁`、YYYY-MM＝対象月）。
- 連番はその対象月内の発行順（既存の最大連番+1）。採番済み番号は台帳「請求書番号」に書き戻し、欠番・重複を出さない。

### 3. 請求書を MF クラウド請求書で発行（正本PDFはMF生成・AI OSI URI Finance 拡張）
> **発行エンジンは MoneyForward クラウド請求書（`mfi_*` ツール）。** 自前PDF生成はしない。
> MFが採番・適格請求書フォーマット・PDFを担い、台帳は正本として番号/状態/リンクを保持する。

1. **取引先の解決**：`mfi_list_partners` で取引先を名前一致検索し、`department_id`（送付先メール/CC を持つ部署）を得る。
   無ければ `mfi_create_partner`（name＝正式名称、dept_name、email＝請求先To、cc_emails＝CC）で作成し department_id を得る。
2. **品目の組み立て**：台帳の `請求額(税込)` から税抜単価を算出（既定10%なら `price = round(税込 / 1.1)`、`excise = "ten_percent"`、`quantity = 1`、`name = 件名`）。軽減/非課税はその税区分を使う。源泉が要る取引先は `is_deduct_withholding_tax`。
3. **プレビュー**：`mfi_create_billing` を `dry_run:true` で1回呼び、`would_post` の中身（department_id・billing_date・due_date・billing_number＝台帳INV・items）を人に提示して確認を取る（金額・宛先・期日）。
4. **発行**：確認後 `mfi_create_billing`（`dry_run:false`）。
   - `billing_date`/`due_date` は `osi-finance-settings` の `AR_PAYMENT_TERMS`（請求日＝対象月翌月1日、支払期限＝翌月末）。
   - `billing_number` に**台帳の請求書番号(INV)をそのまま指定**（台帳とMFの番号を一致させる）。
   - 返り値の `billing_id` / `billing_number` / `pdf_url` を控える。
5. **MFが使えない場合のフォールバック（暫定）**：MF を data.write で接続できない等で `mfi_*` が使えないときに限り、自前PDFを暫定生成してよい。**HTML→PDF（weasyprint + Noto Sans CJK JP を埋め込み）＋ ghostscript 軽量化**で作る（reportlab の非埋め込みCIDフォントは英数字・数字が □ 化して金額が読めないため不可。生成後は `pdftoppm` で画像化し目視検証）。適格請求書要件・採番はMF正本に劣るため、MF発行に戻せるようになったら差し替える。

### 4. 公式PDFを Drive に格納（正本はDrive）
- `mfi_get_billing_pdf`（id または pdf_url）で**MF生成の公式PDF**を base64 取得。
- **マウント済みの Drive 共有ドライブ（ローカル同期フォルダ＝FS）** に base64 をデコードして書き出す：
  `{請求管理ルート}/{送付請求書}/YYYY-MM/{INV}_{取引先}_{件名短縮}.pdf`（同期で Drive に反映。直アップロードより安定）。
- 書き出し後にファイルが開けることを確認。

### 5. Gmail 下書き作成（送付は人が1クリック）
- 宛先＝契約マスタ/部署の請求先To、CC＝CCアドレス。件名例：`【{ISSUER_NAME}】請求書送付（{件名}）`。本文は定型（お礼＋添付＋振込先＋支払期限）。
- **MFのPDF**を添付して**下書きのみ作成（送信しない）**。運用者が内容を確認し、Gmailで送信する＝実質「1クリック送付」。
  （MF API にメール送信は無い。郵送が要る場合のみ別途 `posting` を使う方針。）
- **添付が不確実なとき（重要）**：Gmail のメール系コネクタの下書き作成ツールは添付が不確実（「添付未対応」表記・検証不可）なことがある。その場合は **Claude in Chrome の `file_upload`** で、Drive上の公式PDF（または暫定PDF）を**既存下書きに直接添付**する：宛先で一意特定（`in:draft to:<addr>`）→開く→添付。**navigate→screenshot→click の順**で確実に開き、処理済みは一覧上位に繰り上がるため**固定座標でなく宛先検索で毎回特定**、重複下書きは作らない。Chrome不可なら人が手動D&D添付（本文に「PDF添付」と書くので添付漏れ注意を伝える）。

### 5.5 本文パーソナライズ（任意・レビュー前提）
- 当月ご一緒した取り組みを **Obsidian（`30_Projects/_Active/{社名}/議事録`、`obsidian-knowledge-consult` 経由）→ Plaud → Drive** の順で拾い、お礼文に1段落反映。記録が無い社は具体を書かず**厚めの汎用お礼にフォールバック**（不正確リスクを避け無理に具体を書かない）。
- **安全ガード（必須）**：送付先は客先本人。社内戦略・価格/割引・人脈・未確定構想などの**機微は本文に出さない**。件名/INVと本文を突合し取り違え防止。宛名の固有漢字は台帳表記を厳守（自動変換の誤字注意）。**送信前レビュー必須**。

### 6. 台帳更新
- 各行：請求ステータス→**「請求済」**、請求書番号(=MF billing_number)・請求日・支払期限・**送付請求書ファイル（DriveリンクまたはパスとMF billing_id）**を記入。
- 売上のMF会計計上（売掛金/売上）は `osi-finance-ar-sync` の役割（発行＝即計上にしない）。

### 7. 人レビュー
- 発行一覧（INV・宛先・税込金額・PDFリンク・Gmail下書き）を提示。人が下書きを確認して送信。

## 留意

- 送信・確定は人。下書きまで。
- 一括案件は該当月のみ。月額は各月1通。
- 金額・宛先は台帳（契約マスタ）を正とし、相違があれば人に確認。
- 入金確認・消込は対象外（別ワークフロー）。
- **月初スケジュールの発火漏れ防止（重要）**：月初ドラフト・スケジュール（`osi-finance-monthstart-invoice-draft` 等／毎月1日）は、(a) `sheets_*` に `spreadsheet_id` を明示、(b) スケジュールを新規登録・再作成した月は登録が発火時刻を過ぎると当月分が発火しない（cronは過去回を遡らない）→ **登録は月末までに済ませ初回は手動確認**、(c) 発火漏れ月の未請求分は次回実行で**併せて拾う（取りこぼし防止）**。

## エラー処理

詳細は **[`docs/エラー処理ガイド.md`](../../docs/エラー処理ガイド.md)** を正本とする。本スキルで詰まりやすい点：

- **台帳が 404（NOT_FOUND）**：ほぼ `sheets_*` の `spreadsheet_id` 未指定（「台帳アクセス」節）。全呼び出しでIDを明示。恒久対策は拡張設定にデフォルトID登録。
- **Gmail下書きにPDFが添付されない**：メール系コネクタの添付は不確実 → Chrome `file_upload` で既存下書きに添付、または人が手動添付（手順5）。
- **（フォールバックで自前PDFを作る場合）英数字が □ 化**：非埋め込みCIDフォントが原因。weasyprint + Noto Sans CJK JP 埋め込みに切替、生成後は画像化で目視検証。
- **請求書PDF・台帳xlsx の Drive 格納が失敗**するとき：Google Drive の**ローカル同期フォルダにコピー**して配置する（直アップロードは大容量で不安定）。配置後に開けるか確認。
- repo/台帳ファイルの差し替えは **in-place 編集を避け新規 Write**（`.fuse_hidden*` 残り対策）。
- `osi-finance-settings.md`（発行者・採番・振込先）が無ければ作成を案内し、埋まるまで採番・格納先確定を止める。送信・確定は人（下書きまで）。
