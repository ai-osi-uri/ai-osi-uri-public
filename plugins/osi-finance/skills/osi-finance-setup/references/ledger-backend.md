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

## まだ手元にしかないもの

`ds_*`（DocuSign）と `mail_*`（メールの添付）は手元の Finance 拡張にだけある。置き場が Web でも、これらは手元の拡張を使う。
手元の拡張が無い環境では、DocuSign とメールの添付は Chrome の画面操作か、人の手に回す。

## 事故の型

- 置き場を確かめずに手元の `sheets_*` を叩き、Web 台帳と手元の xlsx が食い違う → 仕事の始めに `ledger_status`
- Web の道具は既定で dry_run。書いたつもりで書けていない → 書くときは `dry_run:false` を明示し、返事の `appended` / `updatedCells` を見る
- 置き場を切り替えたら中身も移ったと思い込む → 移すのは別の作業（会計のサイトの「台帳」画面の「AI に頼む」）
