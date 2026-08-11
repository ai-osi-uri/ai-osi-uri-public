---
name: osi-finance-console
description: >-
  OSI Finance のローカルコンソール（ブラウザで開く台帳ビュー）の入口。URL の案内と、
  コンソールから積まれた「依頼キュー」の消化を担当する。
  「コンソールを開きたい」「台帳の画面を出して」「経理コンソールのURLを教えて」
  「溜まっている依頼を処理して」「コンソールからの依頼を見せて」「依頼キューを確認」
  「DocuSign送付の依頼が来ていないか確認して」など、コンソールの起動導線と、
  コンソール発の依頼の実行に関わるリクエストで発動する。
  ※ 請求書の発行は osi-finance-invoice、支払起票は osi-finance-payment-intake、
  突合は osi-finance-mf-sync / ar-sync、契約の DocuSign 送付は contract-docusign-send の担当。
  本スキルは「コンソールへの入口」と「依頼を適切なスキルへ橋渡しすること」に特化し、
  実処理そのものは各担当スキルに委ねる。
---

# OSI Finance ローカルコンソール

設計: `docs/osi-finance-local-console-design.md`

台帳（ローカル Excel またはスプレッドシート）を見て直すための画面は、Finance コネクタが
`127.0.0.1` で配信している。Cowork のアーティファクトではない。

## 1. URL を案内する

ユーザーが「コンソールを開きたい」と言ったら、コネクタの `console_url` ツールを呼んで URL を返す。

- 返ってきた URL をそのまま提示する。初回アクセスで Cookie が発行され、以降は
  `http://127.0.0.1:<port>/` だけで開ける。ブックマークを勧める
- 台帳フォルダの **「コンソールを開く.html」** からも入れることを併せて伝える。
  Finder から台帳の隣をダブルクリックするのが一番早い
- `console_url` がエラーを返す場合は、Claude Desktop が起動しているか、拡張の設定で
  `console_http` が `off` になっていないかを確認する

**コンソールは Claude Desktop の起動中しか開けない。** ブックマークが繋がらないという
相談を受けたら、まずここを疑う。

## 2. 依頼キューを消化する

コンソールの「DocuSignで発送を依頼」「MFと突合」などのボタンは、その場では実行せず
依頼を積むだけになっている。外部への送信・発行を無確認で行わないため。

依頼は台帳フォルダの `_requests/` に1件1 JSON で入っている。

```json
{ "id":"REQ-20260811-090501-001", "type":"docusign_send",
  "created_at":"2026-08-11 09:05", "created_by":"...",
  "target":{"contract_id":"C-031"}, "note":"...", "status":"pending" }
```

### 手順

1. `_requests/` の `pending` を読む（ファイルを直接読む。Read/Glob で足りる）
2. **一覧をユーザーに提示して確認を取る。** ここは省略しない
3. 承認されたものだけ、`type` に応じて担当スキルへ渡す

   | type | 渡す先 |
   | --- | --- |
   | `docusign_send` | `osi-backoffice:contract-docusign-send` |
   | `mf_reconcile` | `osi-finance-mf-sync`（AP）／ `osi-finance-ar-sync`（AR） |
   | `invoice_issue` | `osi-finance-invoice`（単票モード） |
   | `journal_generate` | `osi-finance-journal` |

4. 完了したら当該 JSON の `status` を `done` にし、`_requests/done/` へ移す。
   実行しないと判断したものは `rejected` にして理由を `note` に追記する

### やらないこと

- 依頼を無確認で実行しない
- 送金しない。振込は人がネットバンキングで行う
- 台帳の状態遷移（請求済・入金済など）をこのスキルで勝手に進めない。
  それはコンソールのボタンか、各担当スキルの仕事

## 3. 台帳に触るときの原則

台帳ファイルを開いているのはコネクタのプロセスだけ、という前提で全体が組まれている。
`xlsx-tools.js` がロックファイル検知と mtime ガードを持っているので、**必ず
`sheets_*` ツール経由で読み書きする。** openpyxl や pandas で直接 xlsx を開かない。
直接開くと、コンソール側の書き込みと衝突してどちらかが消える。

Excel でその台帳を開いていると書き込みは拒否される。「台帳が Excel で開かれています」
というエラーが出たら、閉じてもらってから再実行する。
