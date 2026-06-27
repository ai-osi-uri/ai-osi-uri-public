# 発行者情報（AR 請求書 発行元）— 汎用ロジック ＋ osi-finance-settings 参照

> **具体値（社名・登録番号・住所・振込先・税率・採番ルール・支払サイト）は組織固有値であり、
> `config/osi-finance-settings.md`（テンプレ：`config/osi-finance-settings.example.md`）を正本とする。**
> 台帳に「発行者設定」シートがある場合はそれを最優先し、無ければ osi-finance-settings を参照する。
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

## 請求書レイアウト（汎用テンプレ・値は osi-finance-settings で差し込む）

```
請 求 書
{宛名} 御中                         {ISSUER_NAME}
                                     登録番号: {ISSUER_INVOICE_REG_NO}
                                     〒{ISSUER_POSTAL_CODE} {ISSUER_ADDRESS}
請求書番号: {AR_NUMBERING に従う採番}
請求日: YYYY年M月D日
お支払期限: YYYY年M月D日
件名: {契約内容}（YYYY年MM月分）
ご請求金額  {合計税込} 円
─ 明細 ─ 納品日 / 品目 / 単価 / 数量 / 単位 / 価格
小計 {税抜} 円 ／ 消費税({CONSUMPTION_TAX_RATE}) {税額} 円 ／ 合計 {税込} 円
お振込先 {BANK_NAME} {BANK_BRANCH} {ACCOUNT_TYPE} {ACCOUNT_NUMBER} {ACCOUNT_HOLDER}
備考 お振込手数料は{TRANSFER_FEE_BEARER}にてお願いいたします。
```

## 登録番号についての汎用ルール

- 発行者は**常に自社のインボイス登録番号**（`ISSUER_INVOICE_REG_NO`）で固定する（相手側の番号ではない）。
- 自社の登録番号が不明な場合は、国税庁 適格請求書発行事業者公表サイト
  （https://www.invoice-kohyo.nta.go.jp/）で確認し、osi-finance-settings に記録する。
