# osi-finance-settings（組織固有値テンプレート）— EXAMPLE

このファイルは **配布用テンプレート（プレースホルダ）** です。各組織は本ファイルを
同ディレクトリに `osi-finance-settings.md` としてコピーし、`{{ }}` を自社の実値で埋めて使います。
**実値版 `osi-finance-settings.md` はコミットしないこと**（`.gitignore` で除外済み）。

OSI Finance（osi-finance）の各 osi-finance スキル（contract-intake / invoice / payment-intake /
payment-detect / mf-sync / monthly）は、社名・登録番号・振込先・税率・採番ルール・
Drive ルート・台帳ファイル名などの**組織固有値をすべてこのファイルから読む**前提です。
各 references（invoice-issuer / monthly-rules / ledger-schema）の具体値も、原則ここを正本とし、
references 側には「汎用ロジック・判断基準」だけを残します。

---

## 1. 発行者情報（AR 請求書 発行元）

| 項目 | 値 |
|---|---|
| 発行者名義 | {{ISSUER_NAME 例: ○○株式会社}} |
| インボイス登録番号 | {{ISSUER_INVOICE_REG_NO 例: T0000000000000（T+13桁）}} |
| 郵便番号 | {{ISSUER_POSTAL_CODE 例: 000-0000}} |
| 住所 | {{ISSUER_ADDRESS 例: ○○都○○区○○ 1-2-3 ○○ビル N階}} |

## 2. 振込先（AR 請求書に記載する自社入金口座）

| 項目 | 値 |
|---|---|
| 銀行 | {{BANK_NAME 例: ○○銀行}} |
| 支店 | {{BANK_BRANCH 例: ○○支店（店番000）}} |
| 預金種別 | {{ACCOUNT_TYPE 例: 普通}} |
| 口座番号 | {{ACCOUNT_NUMBER 例: 0000000}} |
| 口座名義 | {{ACCOUNT_HOLDER 例: ○○（カナ可）}} |
| 振込手数料 | {{TRANSFER_FEE_BEARER 例: お客様負担}} |

## 3. 税率

| 項目 | 値 |
|---|---|
| 標準消費税率 | {{CONSUMPTION_TAX_RATE 例: 10%}} |

## 4. 採番ルール

| 種別 | 形式 | 例 |
|---|---|---|
| AR（送付請求書番号） | {{AR_NUMBERING 例: INV-YYYY-MM-連番3桁（YYYY-MM=対象月）}} | INV-2026-06-006 |
| AP（支払先ID） | {{AP_PAYEE_ID_FORMAT 例: V-連番3桁}} | V-013 |
| 契約マスタ（契約ID） | {{CONTRACT_ID_FORMAT 例: C-連番}} | C-007 |
| 支払サイト（AR） | {{AR_PAYMENT_TERMS 例: 月末締め翌月末払い（請求日=対象月翌月1日／支払期限=翌月末）}} | |

## 4-2. AR 会計設定（売上・売掛金・入金消込のMF計上に使う）

`osi-finance-ar-sync`（請求済→売上計上／入金済→消込のMF突合・登録）が参照する勘定科目・税区分。
科目・税区分名は MF の getAccounts / getTaxes の**実在名**に合わせる（実行時にIDへ解決する）。

| キー | 値 | 用途 |
|---|---|---|
| AR_SALES_ACCOUNT | {{AR_SALES_ACCOUNT 例: 売上高}} | 売上計上の貸方科目 |
| AR_OUTPUT_TAX_ACCOUNT | {{AR_OUTPUT_TAX_ACCOUNT 例: 仮受消費税}} | 仮受消費税（税区分から自動計算。明示行は作らない） |
| AR_ACCOUNTS_RECEIVABLE | {{AR_ACCOUNTS_RECEIVABLE 例: 売掛金}} | 売上計上の借方／入金消込の貸方科目 |
| AR_TAX_CLASS | {{AR_TAX_CLASS 例: 課税売上 10%}} | 売上行の課税売上 税区分 |
| AR_DEPOSIT_ACCOUNT | {{AR_DEPOSIT_ACCOUNT 例: 普通預金}} | 入金消込の借方科目 |
| AR_BANK_LINK_HANDLING | {{AR_BANK_LINK_HANDLING 選択: 連携側を売掛金消込に振替 / 台帳から消込}} | 入金bank連携の扱い（後述） |

> **入金bank連携の扱い（AR_BANK_LINK_HANDLING）**
> - `連携側を売掛金消込に振替`：MF銀行連携が入金を自動仕訳する場合、その仕訳を (借)普通預金/(貸)売掛金 に
>   振り替える。`osi-finance-ar-sync` は消込仕訳を**作らない**（入金消込は突合上「除外」。二重計上防止）。
> - `台帳から消込`：銀行連携が入金を自動仕訳しない（または別科目で入る）場合、`osi-finance-ar-sync` が
>   台帳の入金済から (借)普通預金/(貸)売掛金 の消込仕訳をレビューのうえ登録する。
>
> **計上タイミング**：売上は請求発生時＝対象月末で計上（発生主義）。過去分は遡及計上（計上月は要確認）。
> **源泉・値引・貸倒は初期対象外**（要確認）。**科目・税区分・計上タイミングは各社の税理士確認を前提**とする。

## 5. Drive ルート・フォルダ構成

請求・経費まわりの保存先ルートとサブフォルダ名。組織で名前が違う場合はここで差し替える。

| キー | 値（フォルダ名・パス） |
|---|---|
| 請求管理ルート | {{DRIVE_BILLING_ROOT 例: 31.請求管理}} |
| └ 契約書 | {{DRIVE_CONTRACTS 例: 00.契約書}} |
| └ 受領請求書（AP） | {{DRIVE_RECEIVED_INVOICES 例: 01.受領請求書}} |
| └ 送付請求書（AR） | {{DRIVE_SENT_INVOICES 例: 02.送付請求書}} |
| 経費管理ルート | {{DRIVE_EXPENSE_ROOT 例: 32.経費管理}} |
| └ カードSaaS証憑 | {{DRIVE_CARD_SAAS_EVIDENCE 例: カードSaaS証憑}} |

## 6. 台帳ファイル

| キー | 値 |
|---|---|
| 請求管理台帳（AR） | {{LEDGER_BILLING_FILE 例: 請求管理台帳.xlsx}} |
| 支払管理台帳（AP・支払先マスタの正本） | {{LEDGER_PAYMENT_FILE 例: 支払管理台帳.xlsx}} |
| 請求管理台帳 スプレッドシートID（ネイティブGoogle Sheets化した場合・自動追記用） | {{LEDGER_BILLING_SHEET_ID 例: 16Xm3-…（URL /d/<ここ>/edit）}} |
| 支払管理台帳 スプレッドシートID（同上） | {{LEDGER_PAYMENT_SHEET_ID 例: 1dRNut-…}} |

> **台帳を自動追記したい場合**：台帳をネイティブ Google スプレッドシートにし、上記の各 `..._SHEET_ID` を入れる。
> `AI OSI URI Deploy` 拡張の `sheets_append_row`（要：対象シートをサービスアカウントのメールに「編集者」で共有）で、
> osi-finance スキルが行を自動追記できる（重複は `sheets_get_values` で事前確認、確定は人）。未設定なら xlsx へ貼り付け運用。

> **支払先マスタの正本＝支払管理台帳**。各支払先に「既定の支払方法（振込／カード）」列を持たせ、
> 振込（Trunk 等）／カード（自動課金）の振り分けに使う（payment-intake / payment-detect が参照）。

## 7. 判断辞書（科目マッピング）の所在

科目・税区分・インボイス・源泉の判断辞書は
`plugins/osi-finance/skills/osi-finance-monthly/references/monthly-rules.md` を参照する。
**判断ロジック・税区分ルールは汎用**だが、**自社固有の「支払先→勘定科目」対応表**は
組織ごとに異なるため、その実値は下表に定義する（monthly-rules の `例:` 表は雛形）。

### 7-1. 支払先別 勘定科目マッピング（振込支払／自組織の実値）

| 支払先 | 既定支払方法 | 勘定科目 | 税区分(MF) | 源泉 | 備考 |
|---|---|---|---|---|---|
| {{PAYEE_1 例: ○○株式会社}} | {{振込/カード}} | {{ACCOUNT 例: 業務委託料}} | {{TAX 例: 課税仕入10%}} | {{源泉 例: なし}} | |
| {{PAYEE_2}} | | | | | |
| …（必要数だけ追加） | | | | | |

### 7-2. カード（自動課金 SaaS 等）加盟店マッピング

カード払いは会計側でカード連携（例: UPSIDER）が自動仕訳するため、**支払管理台帳には起票しない**。
証憑のみ `{{DRIVE_EXPENSE_ROOT}}/{{DRIVE_CARD_SAAS_EVIDENCE}}/` に保存する。
加盟店→科目の目安は monthly-rules の `例:` 表を参照（自組織の確定値が必要なら下に追記）。

| 加盟店の例 | 勘定科目 | 税区分(MF) |
|---|---|---|
| {{MERCHANT_1}} | {{ACCOUNT}} | {{TAX}} |
| …（必要数だけ追加） | | |

---

## 運用メモ

- 本テンプレ（`.example`）は配布対象。実値版 `osi-finance-settings.md` は各組織がローカルで作成し、
  Git にはコミットしない（`**/osi-finance-settings.md` を `.gitignore` で除外）。
- スキルから「組織固有値」を参照する場合は、まず実値版 `osi-finance-settings.md` を読み、
  無ければユーザーに「osi-finance-settings.md を作成してください」と案内する。
- 機微値（実口座番号・登録番号・実在支払先名など）は**この `.example` には書かない**。
