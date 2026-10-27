# 台帳の置き場（手元／Web）と、道具の読み替え

台帳（請求管理台帳・支払管理台帳・仕訳台帳・共通マスタ）は、会社（または個人）ごとに置き場を選ぶ。

| 置き場 | 正本 | Claude が使う道具 | 人が見る画面 |
|---|---|---|---|
| 手元（local・既定） | 経理フォルダの xlsx | 手元の Finance 拡張の `sheets_*`・`ledger_maintain` | 手元のコンソール |
| Web（web） | 会計のサイトの中の台帳 | URL のコネクタの `ledger_*` | 会計のサイトの「台帳」画面 |

表と列は、どちらの置き場でも同じ（正本は `assets/schema/data-layout.yaml`）。スキル本文の手順・判断は置き場に関係なくそのまま使い、
**道具の名前だけを読み替える。**

## 置き場の確かめ方（Finance の仕事を始める前に 1 回）

1. URL のコネクタに `ledger_status` があれば呼ぶ。返事の `backend` が置き場。
   - `web` … 下の対応表で `sheets_*` を `ledger_*` に読み替える
   - `local` … 本文どおり手元の `sheets_*` を使う
2. URL のコネクタが無い（`ledger_status` が見えない）ときは、手元（local）として本文どおり進める。
3. 置き場を変えたいと言われたら `ledger_set_backend`（または会計のサイトの「台帳」画面）。中身は自動では移らない。

## 対応表（手元 → Web）

| 手元（local） | Web（web） | 違い |
|---|---|---|
| `sheets_list_tabs` | `ledger_list_tabs` | |
| `sheets_get_values`（range はタブ名） | `ledger_get_values`（tab） | 範囲ではなくタブ名で読む。ヘッダーはいつも 1 行目 |
| `sheets_read_schedule` | `ledger_read_schedule` | `__row` はどちらもシートの行番号 |
| `sheets_update_status` | `ledger_update_status` | **Web は既定で dry_run。** 書くときは `dry_run:false` |
| `sheets_append_row` | `ledger_append_row` | **Web は既定で dry_run。** `dedupe_by` は同じ |
| `sheets_update_values`（A1 範囲） | `ledger_update_rows` | 範囲ではなく「行番号＋列名→値」で書く |
| `sheets_create_tab` | `ledger_create_tab` | 標準の表は `ledger_setup` が作る |
| `ledger_maintain` の `expand_schedule` | `ledger_expand_schedule` | 展開するのは 状態=締結済 の契約だけ |
| `ledger_maintain` のほかの action | （無い） | 読んで直す（`ledger_read_schedule` → `ledger_update_rows`） |
| 手元の `sync_ledger` | URL のコネクタの `sync_ledger` | Web 台帳に書き戻す。既定で dry_run |
| 手元の `mfi_*` | URL のコネクタの `mfi_*` | **置き場に関係なく、どちらでも使える。** つなぐのは会計のサイト（`mfi_connect` が URL を返す） |
| `mfi_get_billing_pdf` の `out_path`（台帳フォルダ） | 同じ道具の `out_path`（会計のサイトのファイル置き場） | Web では「送付請求書ファイル」列に返った `saved` を書く |
| 手元のコンソール | 会計のサイト `/ledger` | |

## メール・電子署名・書類の置き場（共通の道具）

メールと電子署名は Finance の道具ではなく、URL のコネクタの**共通の道具**（どの仕事からも使う）。
台帳の置き場（local / web）に関係なく使える。**つなぐのはポータルの「鍵設定」**（https://www.ai-osi-uri.info/keys/use/mail ・ /keys/use/esign）。
Finance のスキルは「使う側」として、請求書の送付・受け取った請求書の保存・契約書の送付にこれらを使う。

| 使い道（Finance の仕事） | 共通の道具 | つなぐ場所（鍵設定） |
|---|---|---|
| 請求書 PDF・契約書を置く・一覧・見せる | `files_put`・`files_list`・`files_url`（会社の書類の置き場） | 置き場は会計のサイトの「書類」でも見られる |
| 請求書を添付して送る・受け取った請求書をしまう | `mail_status`・`mail_connect`・`mail_create_draft`・`mail_send_draft`・`mail_list_attachments`・`mail_save_attachments` | `/keys/service/gmail`・`/keys/service/outlook`（人ごと） |
| 契約書を DocuSign で送る・締結済みを戻す | `ds_status`・`ds_connect`・`ds_create_envelope`・`ds_get_envelope`・`ds_list_envelopes`・`ds_save_documents` | `/keys/service/docusign` |
| 契約書をクラウドサインで送る・締結済みを戻す | `cs_status`・`cs_create_document`・`cs_send_document`・`cs_get_document`・`cs_list_documents`・`cs_save_files` | `/keys/service/cloudsign` |

- メールと電子署名は URL のコネクタの道具だけ（手元の Finance 拡張の `mail_*`・`ds_*` は 1.47.0 で外した・2026-10-16）。ファイルは会社の書類の置き場の相対パスで指す。
  台帳が手元（local）でも同じ。手元の台帳フォルダのファイルを送るときは、先に `files_put` で置き場に上げる。受け取った添付を手元の台帳フォルダにも置きたいときは、`mail_save_attachments` で置き場に保存してから `files_url` で取ってくる。
- 作る道具は既定で `dry_run:true`、作っても下書き（`send:false`）。送るのは本人が宛先・書類を確かめて OK したときだけ。
  - `cs_send_document` は `expect_emails`、`mail_send_draft` は `expect_to`・`expect_attachments` が実物と一致しないと送らない。
- 締結済みの保存先は既定で `03.契約書/締結済/`、受け取った添付は `04.受領書類/YYYY-MM/`。保存した `path` を台帳の「〜ファイル」列に書く。
- つながりは人ごと（本人の鍵とトークン。本人に無いアプリの鍵は会社に預けた鍵を使う）。
- まだつないでいないときは、道具が鍵設定の URL を返す。その URL を本人に渡し、鍵の値は会話に貼ってもらわない。

## 事故の型

- 置き場を確かめずに手元の `sheets_*` を叩き、Web 台帳と手元の xlsx が食い違う → 仕事の始めに `ledger_status`
- Web の道具は既定で dry_run。書いたつもりで書けていない → 書くときは `dry_run:false` を明示し、返事の `appended` / `updatedCells` を見る
- URL のコネクタの `ds_*`・`cs_*`・`mail_*` に手元のパスを渡して「ファイルがありません」→ 先に `files_put` で置き場に上げる（`files_list` で確かめる）
- 置き場を切り替えたら中身も移ったと思い込む → 移すのは別の作業（会計のサイトの「台帳」画面の「AI に頼む」）
