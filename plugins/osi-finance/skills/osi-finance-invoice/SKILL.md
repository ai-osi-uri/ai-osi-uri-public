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

### 4. 公式PDFを Drive に格納（正本はDrive）
- `mfi_get_billing_pdf`（id または pdf_url）で**MF生成の公式PDF**を base64 取得。
- **マウント済みの Drive 共有ドライブ（ローカル同期フォルダ＝FS）** に base64 をデコードして書き出す：
  `{請求管理ルート}/{送付請求書}/YYYY-MM/{INV}_{取引先}_{件名短縮}.pdf`（同期で Drive に反映。直アップロードより安定）。
- 書き出し後にファイルが開けることを確認。

### 5. Gmail 下書き作成（送付は人が1クリック）
- 宛先＝契約マスタ/部署の請求先To、CC＝CCアドレス。件名例：`【{ISSUER_NAME}】請求書送付（{件名}）`。本文は定型（お礼＋添付＋振込先＋支払期限）。
- **MFのPDF**を添付して**下書きのみ作成（送信しない）**。運用者が内容を確認し、Gmailで送信する＝実質「1クリック送付」。
  （MF API にメール送信は無い。郵送が要る場合のみ別途 `posting` を使う方針。）

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

## エラー処理

詳細は **[`docs/エラー処理ガイド.md`](../../docs/エラー処理ガイド.md)** を正本とする。本スキルで詰まりやすい点：

- **請求書PDF・台帳xlsx の Drive 格納が失敗**するとき：Google Drive の**ローカル同期フォルダにコピー**して配置する（直アップロードは大容量で不安定）。配置後に開けるか確認。
- repo/台帳ファイルの差し替えは **in-place 編集を避け新規 Write**（`.fuse_hidden*` 残り対策）。
- `osi-finance-settings.md`（発行者・採番・振込先）が無ければ作成を案内し、埋まるまで採番・格納先確定を止める。送信・確定は人（下書きまで）。
