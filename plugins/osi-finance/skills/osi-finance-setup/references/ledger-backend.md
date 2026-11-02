# 台帳のふだんの向き（手元が正／Web が正）と、道具の読み替え・同期

台帳（請求管理台帳・支払管理台帳・仕訳台帳・共通マスタ）は、手元の xlsx と会計のサイトの両方に置き、**同期して同じ中身にそろえる**。
どちらを正にするか（ふだんの向き）を会社（または個人）ごとに決める（`ledger_status` の `backend`）。

| ふだんの向き | 正本 | Claude が書く道具 | 人が見る画面 |
|---|---|---|---|
| 手元が正（local・既定） | 経理フォルダの xlsx | 手元の Finance 拡張の `sheets_*`・`ledger_maintain` | 手元のコンソール／会計のサイト（同期した写し） |
| Web が正（web） | 会計のサイトの中の台帳 | 会計のコネクタの `ledger_*` | 会計のサイトの「台帳」画面 |

会計の道具は、会計専用のコネクタ「AI OSI URI Finance」（`https://mcp.ai-osi-uri.info/mcp/finance`）にある。共通の AI OSI URI のコネクタにも 2026-11-16 までは同じ道具が残る。

表と列は、どちらの置き場でも同じ（正本は `assets/schema/data-layout.yaml`）。スキル本文の手順・判断は置き場に関係なくそのまま使い、
**道具の名前だけを読み替える。**

## 置き場の確かめ方（Finance の仕事を始める前に 1 回）

1. URL のコネクタに `ledger_status` があれば呼ぶ。返事の `backend` が置き場。
   - `web` … 下の対応表で `sheets_*` を `ledger_*` に読み替える
   - `local` … 本文どおり手元の `sheets_*` を使う
2. URL のコネクタが無い（`ledger_status` が見えない）ときは、手元（local）として本文どおり進める。
3. ふだんの向きを変えたいと言われたら `ledger_set_backend`（または会計のサイトの「台帳」画面）。中身は動かない（そろえるのは同期）。

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


## 同期（2026-11-02〜）

正にする側の内容で、もう一方を上書きする。**上書きされる側で前回の同期のあとに直した行は、黙って上書きしない**（確認に出る）。
台帳の中身は会話を通らない（手元の拡張と会計のサーバーが、1 回だけ使える URL で直接やりとりする）。

### いつ同期するか

- **手元が正の会社で、台帳を書いた仕事の最後に必ず**（請求・入金・支払・仕訳・契約の起票など）。向きはふだんの向き。
- 毎朝の自動の同期：ドライブの台帳フォルダが設定されていれば、会計のサーバーがドライブから読んで写す（人は何もしない）。
  確認が要る行があれば書かずに止まり、運営に知らせが来る。
- 本人が逆向き（Web の内容で手元を上書き）を頼んだときだけ、`direction` を逆にする。

### 手順（会話から）

1. `ledger_sync_start`（`trigger: skill`。`source` は省略＝手元の拡張から送る。書いた直後はドライブへの上がりが遅れるため `drive` にしない）
2. 返った `push_url` を、手元の Finance 拡張の `ledger_sync_push` にそのまま渡す（URL は本人に見せない）
3. `ledger_sync_plan` で差分を出す。書く行の件数と、確認が要る行（表・見分けの値・列名・どちらで直したか）を本人に見せる。
   値は会話に出さず、返った `see_values`（会計のサイトのその回の画面）で見てもらう
4. 確認が要る行は、本人に行ごとに「上書きする（`overwrite`）／この行は残す（`keep`）」を聞く。**聞かずに `overwrite_all` を使わない**
5. `ledger_sync_apply`（`decisions` に答え）。手元に書く行があれば返った `pull_url` を `ledger_sync_pull` に渡す
   （Excel で台帳を開いていると止まる。閉じてもらってやり直す）
6. 結果（Web に書いた行数・手元に書いた行数・残った確認の行）を報告する

- 手元への書き込み待ちのまま止まった回（会計のサイトの画面から書いた回など）は、`ledger_sync_status` で見つけて `ledger_sync_resume` → `ledger_sync_pull`。
- 手元の拡張が無い・パソコンが閉じているときは、`source: drive`（会計のサーバーがドライブから読む）。ドライブのフォルダは `ledger_sync_settings` で決め、返った `share_with` のメールにフォルダを「閲覧者」で共有してもらう。

### 同期しないもの

- 見分けの列（契約ID など）が空・重複の行。形の定義（`assets/schema/data-layout.yaml`）に無い表・列。
- 正の側で表ごと空だったとき（消しすぎを防ぐため、その表は飛ばす）。消す行が多いときは、消す行を全部確認に回す。
- 数式の列（手元に書くとき、数式のセルは上書きしない）。
