---
name: osi-finance-setup
description: >
  OSI Finance（請求AR・支払APの経理自動化）を新しい組織・Cowork に初回セットアップする
  オーケストレータ・スキル。対話で組織の値を集めて `{{paths.finance}}/osi-finance-settings.md`（実値版・
  gitignore対象）を生成し、Drive にフォルダ構造を作成、台帳テンプレ（共通マスタ・請求管理台帳・
  支払管理台帳・仕訳台帳）を配置して「発行者設定」タブを settings の値で埋め、必要コネクタ
  （Google Drive＋ローカル同期／メール=Gmailまたは Superhuman／任意: 会計SaaS=MoneyForward・freee、
  DocuSign）の疎通を確認、日次・月次のスケジュールタスク登録を案内し、最後にスモークテストまで行う。「OSI Finance を導入」「OSI Finance をセットアップ」「経理を初期セットアップ」
  「請求支払台帳を立ち上げ」「finance を新しい組織に入れる」「経理の初期設定をして」「請求と支払の
  自動化を導入したい」「osi-finance-settings を作りたい」「台帳をDriveに置いて経理を始めたい」などで発動する。
  機微値（社名・登録番号・口座番号・支払先名）はチャットに貼らせず設定ファイルへ書く。
  **送金しない／台帳の自動確定はしない**（既存 osi-finance スキルと同じ安全原則）。日常運用の各処理
  （請求書発行・支払起票・突合・月次クローズ）は osi-finance-* 各スキルの役割で、本スキルは初回導入専用。
requires_connectors:
  - server: money-forward
    provision: user-install
  - server: gmail
    provision: user-install
  - server: superhuman
    provision: user-install
  - server: ai-osi-uri-finance   # DocuSign は自前コネクタの ds_* を使う（公式MCPは remoteUrl しか受けず送付に使えない）
    provision: user-install

connector_prose_ok:  # DocuSign は任意の補助。無くても運用は成立する
  - docusign
---

# osi-finance-setup（OSI Finance 初回セットアップ・オーケストレータ）

> **組織固有値はプロファイルから読む。** 本文の `{{paths.*}}` `{{ledgers.*}}` `{{company.*}}` `{{members.*}}` は、連結フォルダ直下の `osi-profile.md`（雛形: osi-core の `plugins/osi-core/skills/getting-started/assets/osi-profile.example.md`。作るときは getting-started の `scripts/init_kit.py`）の値に置き換えて解釈する。無ければ会社名・案件フォルダ・台帳の有無・使うコネクタを質問して先に作る。値をここに直書きしない。

> **役割**：新しい組織（1 Cowork = 1 組織）に OSI Finance を導入するための初回セットアップを、
> 対話で一気通貫に進める。**この後の日常運用は osi-finance-* 各スキルが担当**するので、本スキルは
> 「設定ファイル生成 → フォルダ構成 → 台帳配置 → コネクタ確認 → スケジュール案内 → スモークテスト」
> までで完了する。

> **安全原則（既存 osi-finance スキルと共通・厳守）**
> - **送金しない。** 振込は人が振込口座（例: Trunk）で実行する。
> - **台帳を自動確定しない。** 起票・更新は案として提示し、人が確認してから反映する。
> - **機微値はチャットに貼らせない。** 社名・インボイス登録番号・口座番号・実在の支払先名などは
>   ユーザーに直接 `osi-finance-settings.md`（gitignore対象）へ書いてもらうか、こちらが受け取った値を
>   設定ファイルにだけ書く。チャット本文・コミット対象には残さない。

導入は対話形式で進める。各ステップの結果を逐一報告し、ユーザーの確認を取りながら次へ進む。

---

## ステップ 0: 前提の確認

最初に次を確認する（未接続でも進めるが、後段の疎通確認で再確認する）。

- 対象は **1 つの組織**であること（1 Cowork = 1 組織）。複数法人を1つの Cowork で混ぜない。
- 国＝日本（消費税・インボイス・源泉の前提）。
- 会計SaaS は**任意**。settings の `ACCOUNTING_SYNC`（`mf` / `freee` / `none`、**既定 none**）で選ぶ。
  none でも台帳＋内部仕訳帳（仕訳台帳）で運用できる。MF を使う組織は `mf`、freee は `freee`（CSV 突合のみ）。
- このプラグイン（osi-finance）が入っており、`assets/templates/` に台帳テンプレ4ファイル
  （`共通マスタ_テンプレート.xlsx`・`請求管理台帳_テンプレート.xlsx`・`支払管理台帳_テンプレート.xlsx`・`仕訳台帳_テンプレート.xlsx`）
  と `コンソールを開く.html` があること。

---

## ステップ 1: 質問に答えてもらう → `osi-finance-settings.md` を生成

設定ファイルは**経理フォルダ直下（`{{paths.finance}}/osi-finance-settings.md`）**に1つだけ作る。台帳（xlsx）を置くフォルダと同じ。
全 osi-finance スキルがここを読む。**実値版はコミットされない**（`.gitignore` の `**/osi-finance-settings.md`）。
旧版の置き場所（プラグインの `config/`・`skills/config/`、台帳フォルダの `_shared/`）に既存の設定がある組織は、
新しく作らずに内容を引き継いで `{{paths.finance}}/` へ移す（2か所にあると片方だけ直される）。

**雛形（`config/osi-finance-settings.example.md`）を手で写して埋めない。** 約390行あり、例の社名（○○株式会社）や
支払先マッピングの例の行が残ったまま使われる。必ず次の道具で作る。

### 1-1. 聞くこと（普通の言葉で・4問だけ）

設定キーの名前（`OPERATION_MODE` `ACCOUNTING_SYNC` `WRITE_CONFIRMATION` `INVOICE_ENGINE` `xlsx_ledger_dir` など）は
**お客さんに見せない。** 下の言葉で聞き、答えをこちらでキーに対応させる。**既定値で作って後から直せる項目は聞かない**
（税率・採番・支払サイト・金額区分・フォルダ名・台帳名・自動送信・操作ログ・定型仕訳の自動登録 など）。

| 聞き方（このまま使う） | 答え → answers.json | 対応する設定キー |
|---|---|---|
| 会計ソフトは何を使っていますか？（マネーフォワード／freee／使っていない） | `"accounting": "mf" / "freee" / "none"` | ACCOUNTING_SYNC |
| 請求書はいま何で作っていますか？（マネーフォワードの請求書／freee／Excel・Word など特になし） | `"invoice_tool": "mf" / "freee" / "none"` | INVOICE_ENGINE（none → local＝同梱の雛形） |
| 台帳に書く前に、毎回あなたが確認しますか？（はい＝おすすめ／いいえ＝先に書いて後で見る） | `"confirm_before_write": true / false` | WRITE_CONFIRMATION（事前確認／事後確認） |
| 請求書を送るメールは何ですか？（Gmail／Outlook／メールはつながない） | `"mail": "gmail" / "outlook" / "none"` | GMAIL_INTAKE |

- 次は**相手が自分から言ったときだけ**入れる（聞かない）：見るだけの導入（`"read_only": true` → OPERATION_MODE=参照専用）、
  電子署名を使う（`"esign": true` → ESIGN=docusign）、銀行の明細CSVで入金を確かめる（`"bank_csv": true` → BANK_RECON=ON）、
  台帳の作成者欄に入れる名前（`"operator": "山田"`）、レシートを出す人（`"members": [...]`）。
- 会社名・郵便番号・住所は `osi-profile.md` から取る（聞き直さない）。`osi-profile.md` が無ければ先に osi-core の
  getting-started で作る（雛形は `plugins/osi-core/skills/getting-started/assets/osi-profile.example.md`）。
- 回数券・チケットなど前受けの商品がある組織だけ、あとで settings §4-4 の金額区分に足す（ここでは聞かない）。

### 1-2. 生成（`assets/scripts/make_settings.py`）

答えを `answers.json` に書き、次を実行する（`<連結フォルダ>` は osi-profile.md のあるフォルダ）。

```bash
python3 assets/scripts/make_settings.py --profile <連結フォルダ>/osi-profile.md --answers answers.json --dry-run
python3 assets/scripts/make_settings.py --profile <連結フォルダ>/osi-profile.md --answers answers.json
```

- 出力先は `<連結フォルダ>/<paths.finance>/osi-finance-settings.md`。**既にあれば上書きせずに止まる**（exit 1）。直すときはファイルを直す。
- 聞かなかった項目は既定値（税率10%・`INV-YYYY-MM-連番3桁`・取引先ID `P-001` 形式・月末締め翌月末払い など）で入る。
- 雛形の**例の行（支払先→科目マッピング・カード加盟店・定期支払先）は空の行で出る。** 運用しながら追記する。
- **機微値（インボイス登録番号・振込先口座）は空欄で出る。** 最後の JSON の `blanks_for_person` に並ぶ欄を、
  **本人にファイルを開いて直接書いてもらう**（チャットに貼らせない）。書き終わったと言われたらステップ3-2へ。
  口座番号・登録番号をこちらから復唱しない（「記入済み」とだけ言う）。
- 生成後、機微値以外（会計ソフト・確認方式・台帳名・採番）を1〜2行で要約して伝える。

---

## ステップ 2: Drive のフォルダ構造を作成（ルート1点方式）

**正本は `assets/schema/data-layout.yaml`**。ステップ1で決めた置き場所に、規定ツリーを作る。

```
OSI Finance/                 ← 顧客が決めるのはこの置き場所だけ（共有ドライブ推奨）
├── 00.契約書/
├── 01.受領請求書/           （受領した請求書PDF）
├── 02.送付請求書/           （発行した請求書PDF。YYYY-MM/ 配下・YYYY-MM は請求月）
└── 03.経費管理/
    ├── カードSaaS証憑/
    └── レシート未処理/       （人単位サブフォルダ {氏名}/）
```

- **このツリーは書類の置き場所で、台帳（xlsx）はここには置かない。** 台帳の場所は経理フォルダ（拡張があれば拡張の設定
  「台帳フォルダ」＝ `xlsx_ledger_dir`、ステップ3）が唯一の正本。両方を同じ親フォルダにするのが分かりやすいが、
  片方だけ移動すると台帳と発行PDFが離れて所在不明になるので、移動するときは必ず両方を見る。
- settings に上書き（既存フォルダ体系）がある場合のみ、その名前で作成・照合する。
- 既に同名フォルダがあれば作らずに再利用する（冪等）。
- 作成・再利用したフォルダのパスを一覧で報告する。

**共有の設定（ルート1点に共有 → 配下へ継承）**：作成後、次の共有を案内する。

1. **経理担当**（編集）— 日々台帳を確定する人
2. **コネクタの実行主体**（編集）— SA 鍵方式ならサービスアカウントのメールアドレス。
   **共有しないと台帳同期拡張が読み書きできない**ため必須
3. **税理士・経営者など**（閲覧）— 任意

> **「組織全体に共有」はしない**（支払管理台帳に振込先口座が含まれる）。
> 共有先は上記ホワイトリストのみとし、以後の追加もルートフォルダへの共有で行う。
> **運用モード＝参照専用のときは、コネクタ実行主体（SA）の共有を「閲覧者」に落とす**
> （MF API も read スコープで接続。設定キーと権限の二重防御）。

---

## ステップ 3: 台帳の配置

台帳はローカルの xlsx。Google スプレッドシート版は 2026-08 に廃止した。

1. 経理用のフォルダを1つ決める（例: `{{paths.finance}}/`）。Drive 等の同期フォルダ配下でよい。
   **ステップ2の書類ツリーと同じ親の下に置くと、台帳と書類が離れない。**
2. プラグインの `assets/templates/` から、次の2種類をそのフォルダに置く。
   - `*_テンプレート.xlsx` の4本 … `_テンプレート` を外した台帳ファイル名（settings §6 で名前を変えた組織はその名前）にして置く：
     `共通マスタ.xlsx`・`請求管理台帳.xlsx`・`支払管理台帳.xlsx`・`仕訳台帳.xlsx`。
     `python3 assets/scripts/build_templates.py --ledger-set <経理フォルダ>` で一度に置ける（既定の名前で置く。既存のファイルは上書きしない。§6 で名前を変えた組織は置いた後に改名する）。
     テンプレートのデータ行は空（記入例は各ファイルの「00_使い方_◯◯」タブにだけある）。
   - **`コンソールを開く.html` … 名前はそのまま置く。台帳と必ずセットで配る**
     （これが台帳を画面で見る入口。xlsx だけ置いて HTML を忘れると、利用者から見て
     「コンソールが存在しない」状態になる。2026-09-22 に別 PC で実際に起きた）
   **拡張（.mcpb）が無い環境はここで下の「拡張が無いとき」へ進む**（3〜4 と「拡張を入れる」は飛ばしてよい）。
3. 拡張の設定で `xlsx_ledger_dir` にそのフォルダの**ローカルのフルパス**を入れ、
   **Claude Desktop を完全に終了して開き直す**（設定は起動時にしか読まれない）。
4. 開き直したら `console_url` を呼び、`started: true` と URL が返ること、`launcher` が
   台帳フォルダの `コンソールを開く.html` を指していることを確かめる。
   利用者に「コンソールを開く.html」をダブルクリックしてもらい、画面が出たらこのステップは完了。
   - `console_url` そのものが無い → 拡張（.mcpb）が入っていない。下の「拡張を入れる」へ
   - 画面に「コンソールに接続できません」と出る → 画面の案内（起動・拡張・台帳フォルダ）どおりに直す
   - 拡張は入っていて HTML だけ無い → `health_check` を呼べば拡張が作り直す（`console.launcher_created`）

### 拡張が無いとき（外部接続も拡張も無い環境）

台帳の読み書きは同梱の **`assets/scripts/ledger_io.py`** で行う。拡張の `sheets_*` と同じく「タブ名＋列名」で指定し、
見出し行の位置（data-layout.yaml の header_row）・末尾への追記・書く前のバックアップ（`<経理フォルダ>/_backup/`）・
作成者/更新者の記録（settings の OPERATOR_EMAIL）・「〜ファイル」列の実在検査を道具が守る。

```bash
python3 assets/scripts/ledger_io.py <経理フォルダ> tabs                          # タブが読めるか（≒ sheets_list_tabs）
python3 assets/scripts/ledger_io.py <経理フォルダ> read --tab 月次請求スケジュール  # 読む（≒ sheets_read_schedule）
```

- 追記は `append --tab … --row '{列名:値}' --dedupe-by …`、更新は `update --tab … --where 列=値 --set '{…}'`、
  請求ステータスは `update-status`、ID の採番は `next-id`、契約からの展開は `expand-schedule`（引数は各スキル本文）。
- **コンソール（`コンソールを開く.html`）は拡張が無いと動かない。** 台帳は Excel で直接見る、と伝える。
  書き込み中は Excel で台帳を閉じてもらう（開いていると道具が書かずに止まる）。
- 拡張を後から入れたら、以後は拡張の道具を使う（台帳は同じファイルなのでそのまま引き継げる）。

### 拡張を入れる（スキルが取ってきて置く）

コンソールと台帳の読み書きは拡張（`ai-osi-uri-finance` の .mcpb）の中にある。**MCP（URL 型コネクタ）には
載せない**：台帳はお客様の手元に置くものなので、手元で完結する拡張のまま配る（2026-09-22 方針）。
利用者にポータルで探させず、スキルがファイルを取ってきて台帳フォルダに置く。

1. `get_download_link`（AI OSI URI の URL 型コネクタ）を `product: "ai-osi-uri-finance"` で呼ぶ。
   返るのは**管理コンソールで反映済みの版**の、ログイン不要の URL（5 分で切れる）とファイル名。
   - 道具が無い／利用権が無いと言われた → ポータルの「インストール」からダウンロードしてもらう（従来の道）
2. その URL を台帳フォルダにダウンロードする（`curl -fL -o "<台帳フォルダ>/<filename>" "<url>"`）。
   PC のシェルでネットに出られないときは、作業環境で取ってから台帳フォルダへ書き込む
3. 利用者に頼むのは3つだけ。**文面はこのまま出す**：
   「台帳フォルダに置いた ◯◯.mcpb をダブルクリックして『インストール』を押してください。
   初めての方は、設定画面の『台帳フォルダ』でこのフォルダを選んでください。
   そのあと Claude のデスクトップアプリを完全に終了して、開き直してください。」
   - アプリの安全の決まりで、インストールと設定の保存は本人の操作が要る（スキルからは押せない）
   - **更新（2回目以降）は台帳フォルダなどの設定が引き継がれる**ので、ダブルクリック→開き直しだけ（2026-09-22 実機で確認）
4. 開き直したら `health_check` を呼び、`server_version` が配った版であること、`console.launcher` が
   台帳フォルダを指すことを確かめる。置いた .mcpb は確かめたあと `_backup/` などへ移してよい

同期フォルダに置く場合の注意。同時編集は解決されないので、**書き手は1人**に絞る運用にする
（他のメンバーには `operation_mode: 参照専用` を設定する）。誰かが Excel で台帳を開いている間は
書き込みが拒否される（ロックファイル検知）。バックアップは既定で同期フォルダの外に置かれる。


- 配置後、各台帳が開けること・タブ構成と見出しが `assets/schema/data-layout.yaml` と一致することを確認する：
  `python3 assets/scripts/build_templates.py --check --ledgers <経理フォルダ> --allow-data`（ERROR 0 で OK）。
  タブ：取引先マスタ／発行者設定・契約マスタ・雛形マスタ・月次請求スケジュール／支払先マスタ・月次支払管理・
  経費一覧・源泉徴収管理・月次支払スケジュール／仕訳帳・勘定科目マスタ・月次サマリ。
- 既に同名台帳があれば**上書きしない**（既存運用を壊さない）。テンプレ配置をスキップした旨を報告し、
  既存台帳に対してステップ6の台帳ヘルスチェックを実施する。

### 3-2. 「発行者設定」タブを settings の値で埋める（必須）

**osi-finance-invoice は発行者情報を台帳の「発行者設定」タブから最優先で読む。**テンプレートの値は空欄なので、
ここを埋めないと請求書の社名・口座が空、または旧テンプレートの「（自社名を入力）」のまま出る（別環境で実際に起きた）。
settings が正本、タブはコンソールと請求書発行のための写し。

```bash
python3 assets/scripts/fill_issuer_settings.py <経理フォルダ> --dry-run   # 何が入るかを確認
python3 assets/scripts/fill_issuer_settings.py <経理フォルダ>             # 書く（書く前に _backup/ へ控える）
```

- 埋める項目：発行者名義・登録番号・郵便番号・住所・振込先（銀行・支店・預金種別・口座番号・口座名義）・
  振込手数料・消費税率・採番ルール・支払サイト、**連携トグル**（電子署名＝ESIGN／会計SaaS＝ACCOUNTING_SYNC／
  銀行明細突合＝BANK_RECON）、**金額区分**（BILLING_PATTERNS）、prepaid を使う組織は 前受の有効期限・失効前通知。
- 終了コード 0＝必須項目がそろった／2＝settings が未記入の必須項目が残った（名前が出るので settings を埋めて再実行）／
  1＝エラー（登録番号が T＋13桁でない、台帳が Excel で開かれている など。書いていない）。
- 口座番号・登録番号の値は画面に出ない（出さない）。報告も「記入済み」とだけ書く。
- 台帳に既に別の値が入っている項目は上書きしない（`--overwrite` で settings に揃える）。連携トグル・金額区分は常に settings に揃える。
- `OPERATION_MODE=参照専用` の組織では書かずに `--dry-run` の結果だけを示し、管理者に実行を頼む。
- settings を後で変えたら（口座の変更・連携の追加など）、このコマンドを再実行する。

---

## ステップ 4: 必要コネクタの確認（軽い疎通）

各コネクタが接続済みか確認し、未接続のものは導入を案内する。可能なら read 系で軽く疎通する。

- **会計SaaS（`ACCOUNTING_SYNC` が mf のときだけ）＝ MoneyForward（mfc_ca）**：`currentOffice` 等で対象事業者を確認。
  **対象事業者の取り違えは事故**なので、必ず社名を声に出して確認する。`freee` は CSV 突合のみなので接続確認は不要
  （`04.連携データ/freee/` の置き場所だけ確認）。`none` なら会計SaaS の確認は飛ばす。
- **ストレージ = Google Drive（＋ローカル同期）**：フォルダ作成・ファイル読取ができるか。
  大容量ファイルの格納は**ローカル同期フォルダ経由を推奨**（ステップ3参照）。
- **メール = Gmail または Superhuman**：
  - 契約・請求の**検索**は Gmail で可能。
  - **メール添付の取得（受領請求書PDFの添付ダウンロード）には Superhuman が必要**。
    **標準の Gmail コネクタでは添付の取得ができない**ため、添付起点の AP 運用をするなら Superhuman を入れる。
- **任意 = DocuSign**：自社送付契約のメタ補完にのみ使う補助。無くても運用は成立する。
- **台帳同期 = AI OSI URI Finance 拡張（.mcpb）・任意**：無い環境では `assets/scripts/ledger_io.py <経理フォルダ> tabs`
  で台帳が読めることを確かめて「拡張なし（台帳は同梱スクリプトで読み書き）」と記録し、次へ進む。
  拡張がある場合：請求管理台帳（台帳）の
  読み書きと MoneyForward クラウド請求書のポーリングを担う専用拡張。**この拡張の OAuth 接続
  （Google／MoneyForward 請求書）を通す作業は、`osi-finance-connect` スキルに委譲する**
  （Claude in Chrome で半自動。規約同意・OAuth許可はユーザー確認、秘匿情報はファイル受け渡し）。
  接続後は `health_check`（`google_auth_mode` と `moneyforward_invoice` が ok）→ `sheets_list_tabs`
  で台帳が読めるかを確認する。

確認結果（接続済み／未接続／要追加）を一覧で報告する。
**台帳同期拡張の接続が未了なら、`osi-finance-connect` を呼んで通す。**

---

## ステップ 5: スケジュールタスクの登録

日次・月次の自動実行を7本登録する（連携トグルで使わない機能のタスクは登録しなくてよい）。**定義（cron・description・prompt）の正本は
[`references/scheduled-tasks.md`](./references/scheduled-tasks.md) にある。**
そこの内容をそのまま `create_scheduled_task` に渡すこと。**プロンプトを自分で書き起こさない。**

| taskId | cron | 呼ぶスキル |
|---|---|---|
| `osi-finance-daily-contract-detect` | `20 8 * * *` | osi-finance-contract-intake |
| `osi-finance-daily-payment-detect` | `25 8 * * *` | osi-finance-payment-detect |
| `osi-finance-daily-bank-detect` | `30 8 * * *` | osi-finance-ar-sync ＋ osi-finance-mf-sync（`ACCOUNTING_SYNC=mf` のときだけ） |
| `osi-finance-monthstart-invoice-draft` | `30 9 1 * *` | osi-finance-invoice |
| `osi-finance-monthly-ar-close` | `0 9 2 * *` | osi-finance-ar-sync |
| `osi-finance-monthstart-close` | `0 9 3 * *` | osi-finance-monthly |
| `osi-finance-monthend-payment-list` | `0 9 25 * *` | osi-finance-payment-detect |

- **登録後は一度「Run now」で実行し、コネクタの接続許可を先取りする**
  （初回はOAuth許可ダイアログが出るため、無人実行の前に通しておく）。
- いずれのタスクも**送金・自動確定はしない**（検出・ドラフト・報告まで）。
- **taskId は `osi-finance-` で始める。**一括更新・一括削除の対象をこの接頭辞で見分けるため。
- **`osi-finance-daily-sync` は 2026-08-18 に廃止済み。登録しない**（既に登録されている組織では削除を案内する。経緯は `references/scheduled-tasks.md` の1番）。

### スケジュールはプラグインでは配れない（伝えること）

plugin.json に `schedules` / `cron` の欄は無く、`hooks` にも時刻で発火するイベントは無い。
スケジュールは**ユーザー単位・マシン単位**の設定なので、**プラグインを入れただけでは
自動実行は始まらない。**このステップを実行しない限り何も動かないことを、明確に伝える。

`~/Documents/Claude/Scheduled/` にファイルを置く方式は**成立しない**（cron はそのファイルの
中に無く、アプリ側の管理領域にある）。登録は必ず `create_scheduled_task` を通す。

### プロンプトに手順を書かせない（最重要）

各タスクのプロンプトは「◯◯スキルに従って実行する」＋固有の絞り込みだけにする。
**手順・フォルダパス・台帳のID・自社情報を書くと、構成が変わったときに
リポジトリの外で静かに古くなる。**2026-08-12 のフォルダ移行で実際に4本が壊れ、
5日間気づかれなかった。理由と判定基準は `references/scheduled-tasks.md` に書いてある。

---

## ステップ 6: スモークテスト

最後に、最小限の動作確認を行って結果を報告する。**書き込み・送金はしない。**

1. **設定の読込**：`osi-finance-settings.md` が読め、Drive ルート・台帳名・税率・採番が取れること。
2. **台帳ヘルスチェック**：`assets/schema/data-layout.yaml` と照合し、①ルート配下に required な
   フォルダが揃っているか、②各台帳に required なタブが揃っているか、③各タブのヘッダー行が
   仕様の列と一致するか（**ヘッダーは1行目とは限らない**。支払先マスタ・経費一覧・源泉徴収管理は3行目、
   月次支払管理は4行目にある。`sheets_get_values`（拡張が無ければ `ledger_io.py read`）が返す `header_row` を使うこと）、を検査する。
   ②③は `python3 assets/scripts/build_templates.py --check --ledgers <経理フォルダ> --allow-data` で機械的に見られる。
   あわせて「発行者設定」の必須項目が埋まっているか（`fill_issuer_settings.py --dry-run` が exit 0 か）も見る。**差分があっても自動修復しない**——欠け・不一致を一覧で報告し、
   テンプレ再配置／列名の復元／settings の上書き設定のいずれかを提案する。
3. **当月の請求予定**：請求管理台帳「月次請求スケジュール」から**請求月＝今月**の未請求行が拾えるか（0件でも可）。
   拡張が無ければ `python3 skills/osi-finance-invoice/scripts/make_invoice_data.py <経理フォルダ> --out-dir <作業フォルダ>` の件数で見る。
4. **受領請求書の検出**：受領請求書フォルダ／メール添付に当月分があれば軽く検出できるか（osi-finance-payment-detect の検出のみ）。
5. **会計SaaS 疎通**（`ACCOUNTING_SYNC=mf` のときだけ。none / freee はスキップ）：MF の対象事業者・当月明細の取得状況を軽く確認。

結果を「OK／要対応」で一覧化し、要対応があれば次アクション（コネクタ追加・テンプレ再配置・
マッピング追記など）を提示してセットアップを締める。

---

## ステップ 7: 導入完了レポート（B表スモークの自動実行）

ステップ6までの結果を、QA-リリースチェックリスト.md「B. 導入直後スモークテスト」の項目に沿って
**1枚の「導入完了レポート」に自動でまとめる**。雛形は `references/setup-completion-report.md`。

進め方：

1. **B表9項目を順に実行/確認**する（**読み取り・ドライランのみ。書き込み・送金・自動確定はしない**）。
   - 設定生成（1）・Drive フォルダ（2）・台帳配置（3）：ステップ1〜3 の結果をそのまま転記。
   - 請求(AR)（4）：osi-finance-invoice を当月で**ドライラン**し、未請求の件数・合計を取る（0件可）。
   - 受領検出(AP)（5）：osi-finance-payment-detect で新着の有無を取る（新着なし可）。
   - 突合(AP)（6）：`ACCOUNTING_SYNC=mf` なら osi-finance-mf-sync、`freee` なら osi-finance-freee-sync を**読み取りのみ**で回し、計上漏れ件数を取る（none はスキップ）。
   - ダッシュボード（7）：osi-finance-dashboard で費用構成・純損益・AR数値が描画されるか。
   - コネクタ（8）・スケジュール（9）：ステップ4・5 の結果を転記。
2. 各項目を **OK／要対応／スキップ** で判定し、件数・要対応内容をメモに書く。
   **機微値（口座番号・登録番号・実在支払先名）はレポートにも書かない。**
3. 雛形の `{ }` を埋めてレポートを生成し、**サマリ（OK/要対応/スキップ件数・導入判定）** と
   **要対応リスト（優先順・次アクション）** を提示する。
4. レポートの保存先はユーザーに確認（Drive の請求管理ルート直下など）。**この repo には保存しない。**

> このステップは「導入が実際に動く状態か」を人が一目で確認するためのもの。
> 要対応が残っても**勝手に直さず**、次アクションを添えて人に渡す。

---

## 完了報告

- 生成した `osi-finance-settings.md` の場所（機微値はエコーしない）
- 作成した Drive フォルダ・配置した台帳のパス
- コネクタ接続状況（会計SaaS／Drive／メール／任意DocuSign）
- 登録した（または案内した）スケジュールタスク
- スモークテスト結果と残課題
- **導入完了レポート**（ステップ7・B表9項目の OK/要対応/スキップ ＋ サマリ ＋ 要対応リスト）

を簡潔にまとめ、「日常運用は『この請求書払って』『契約を取り込んで』『今月の請求書を作って』などで
osi-finance-* 各スキルが動く」ことを案内して終了する。

---

## エラー処理

詳細は **[`docs/エラー処理ガイド.md`](../../docs/エラー処理ガイド.md)** を正本とする。導入時に詰まりやすい点：

- **台帳ヘルスチェックで差分検出**：自動修復しない。`assets/schema/data-layout.yaml` との差分を一覧報告し、対処（テンプレ再配置／列名復元／settings 上書き）を人が選ぶ。
- **メール添付の取得は Superhuman が必須**（標準 Gmail では不可）。AP 運用を添付起点でやるなら Superhuman 接続を案内する。
- **MF の対象事業者の取り違えは事故**。疎通確認で必ず社名を声に出して確認する。
- 詰まったら握りつぶさず、どのステップで・何が・なぜ失敗したかを報告して止める（**送金・自動確定はしない**）。
