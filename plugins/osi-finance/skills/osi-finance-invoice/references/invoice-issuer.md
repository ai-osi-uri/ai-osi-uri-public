# 発行者情報（AR 請求書 発行元）— 汎用ロジック ＋ osi-finance-settings 参照

> **具体値（社名・登録番号・住所・振込先・税率・採番ルール・支払サイト）は組織固有値であり、
> `{{paths.finance}}/osi-finance-settings.md`（テンプレ：`config/osi-finance-settings.example.md`）を正本とする。**
> 台帳に「発行者設定」シートがある場合はそれを最優先し、無ければ osi-finance-settings を参照する。
> **発行者設定の値が空欄・括弧書きの入力指示（「（自社名を入力）」「（口座番号）」など）・`{{ }}` のままなら未記入として扱い、
> settings の値を使う。settings も未記入なら発行しない**（SKILL.md「発行者情報」）。タブは setup が
> `assets/scripts/fill_issuer_settings.py` で埋める。
> このファイルには**汎用のレイアウト・運用ルールのみ**を置き、自社の実値は持たない。

## 参照すべき値（すべて osi-finance-settings から）

| 項目 | osi-finance-settings のキー |
|---|---|
| 発行者名義 | `ISSUER_NAME` |
| インボイス登録番号（T＋13桁） | `ISSUER_INVOICE_REG_NO` |
| 郵便番号・住所 | `ISSUER_POSTAL_CODE` / `ISSUER_ADDRESS` |
| 振込先 銀行・支店・預金種別・口座番号・口座名義 | `BANK_NAME` / `BANK_BRANCH` / `ACCOUNT_TYPE` / `ACCOUNT_NUMBER` / `ACCOUNT_HOLDER` |
| 消費税率 | `CONSUMPTION_TAX_RATE` |
| 振込手数料の負担 | `TRANSFER_FEE_BEARER` |
| 採番ルール（AR） | `AR_NUMBERING` |
| 支払サイト | `AR_PAYMENT_TERMS` |
| 発行者の電話番号 | `ISSUER_TEL`（台帳「発行者設定」の「電話番号」） |
| 振込先の表記（3行） | `PAYMENT_BLOCK`（台帳「発行者設定」の「振込先の表記」） |
| 備考の文言 | `INVOICE_NOTE`（台帳「発行者設定」の「備考の文言」） |

## 標準フォーマット（全請求書で統一。値は発行者設定で差し込む）

```
請 求 書
{正式名称} 御中                      {ISSUER_NAME}
〒{相手の郵便番号}                    登録番号：{ISSUER_INVOICE_REG_NO}
{相手の住所}                          〒{ISSUER_POSTAL_CODE}
                                      {ISSUER_ADDRESS}
                                      TEL: {ISSUER_TEL}
請求書番号：{AR_NUMBERING に従う採番}
請求日：{日付}　　お支払期限：{日付}
件名：{契約内容}（YYYY年M月分）
ご請求金額  {合計税込} 円
─ 明細 ─ 品目 / 単価 / 数量 / 価格
  {品目}（YYYY年M月分）
小計 {税抜} 円 ／ 消費税({CONSUMPTION_TAX_RATE}) {税額} 円 ／ 合計 {税込} 円

振込先
{BANK_NAME} {BANK_BRANCH}
{ACCOUNT_TYPE} {ACCOUNT_NUMBER}
口座名義 {ACCOUNT_HOLDER}

備考
{INVOICE_NOTE}（例：お振込手数料はお客様にてご負担をお願いいたします。）
```

**決まりごと**

- **宛名は `{正式名称} 御中` だけ。** 担当者名（〜様）・部署名（「本社」等）を入れない。下に相手の郵便番号・住所。住所は取引先マスタ（無ければ契約書→法人番号の公表情報→公式サイト）から補い、取引先マスタに書き戻す。
- **品目は品目名だけ。** 品目の下の詳細行（「対象期間：…」「（完了時）」など）は付けない。品目名は前月と同じ（月の部分だけ変える）。対象期間を見せる必要があれば件名・品目名に入れる。
- **請求日**は「請求日の決め方」（`AR_BILLING_DATE`：予定日／発行日）に従う。番号と保存フォルダの月は請求月のまま。
- **振込先は3行**（銀行・支店／種別・番号／口座名義）。1行に詰めない。「銀行名：」などの見出しは付けない。
- **口座名義は銀行登録のカナ表記**（例 `サンプル（カ`）。振込人がカナの受取人名と照合できるようにする。
- **振込手数料の一文は備考欄に置く。** 振込先欄に混ぜない。
- **発行者欄は名義・登録番号・郵便番号・住所・電話番号の5点。** 住所は階数まで書く。
- **日付**：MF 発行は MF の仕様で `YYYY/MM/DD`（変更不可）。ローカル生成は `YYYY年M月D日`。

## 登録番号についての汎用ルール

- 発行者は**常に自社のインボイス登録番号**（`ISSUER_INVOICE_REG_NO`）で固定する（相手側の番号ではない）。
- 形式は **`T` ＋数字13桁**（ハイフン・空白なし）。形式が違う・`T0000000000000` のままなら発行しない
  （`scripts/verify_invoice.py` / `render_invoice.py` が止める）。
- 自社の登録番号が不明な場合は、国税庁 適格請求書発行事業者公表サイト
  （https://www.invoice-kohyo.nta.go.jp/）で確認し、osi-finance-settings に記録する。
