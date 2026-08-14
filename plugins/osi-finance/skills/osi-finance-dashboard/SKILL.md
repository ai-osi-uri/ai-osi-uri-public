---
name: osi-finance-dashboard
description: >
  OSI Finance の「会計ダッシュボード」を Cowork のライブ・アーティファクトとして生成するスキル。
  開くたびに MoneyForward（当期の費用構成・純損益・直近の支払仕訳）と請求管理台帳（当月の請求・
  入金状況）から最新データを取得し、請求(AR)・支払(AP)・経費の状況を1枚で一覧表示する。
  「会計ダッシュボードを作って」「今月の請求状況・支払状況・経費状況を一覧で見たい」「経理の
  ダッシュボードを出して」「請求と支払と経費をまとめて管理したい」「財務の現状を一目で」「損益と
  費用の内訳を見せて」などで発動する。組織固有値（台帳の場所・ファイル名・会計年度開始月）は
  `config/osi-finance-settings.md` を参照する。データの確定・送金・台帳更新はしない（表示専用）。
requires_connectors:
  - server: money-forward
    provision: user-install
  - server: cowork
    provision: builtin

---

# osi-finance-dashboard（会計ダッシュボード — ライブ・アーティファクト生成）

> **組織固有値（台帳ルート／ファイル名・会計年度開始月・科目の支払/経費分類）は
> `config/osi-finance-settings.md`（テンプレ：`config/osi-finance-settings.example.md`）を参照する。**

請求(AR)・支払(AP)・経費の「今の状況」を1画面で見えるようにする、表示専用のダッシュボード。
`mcp__cowork__create_artifact` で**ライブ・アーティファクト**として作る（開くたびにコネクタから最新取得・再オープン可）。

> **正本の前提（重要）**：AR が `osi-finance-ar-sync` で MF に計上される設計になったため、本ダッシュボードは
> **MF の構造化データ（試算表 PL/BS・仕訳）を正本**にする。台帳テキストの自然言語解釈はやめ、台帳は
> 「今月のオペレーション（請求予定・採番待ち・宛先未補完）」の補助にのみ使う。

## 画面構成（5タブ／業績と資金を分離）

`references/dashboard-template.html` は**5タブの1ファイル**。各タブはクリックで切替（チャートは表示後に遅延生成＝`display:none` 回避）。会計年度は `mfc_ca_currentOffice` から自動判定（開始月を決め打ちしない）。**業績は発生主義（請求＝計上）、資金は回収（入金）で分けて見る**のが核。

- **① 当期サマリ**：当期 売上・純損益（PL）／売掛金(未回収)・未払金（BS）のカード＋費用科目ドーナツ＋AP・経費内訳＋直近仕訳。
- **② 履歴・分析（確定値＝MF）**：`mfc_ca_getReportsTransitionProfitLoss`（月次）で売上／費用／純損益の推移グラフ＋前月比。各月行に「売上・費用→③」「回収・支払→④」のその月ジャンプ。
- **③ 案件別 売上・費用（業績）**：対象月セレクタつき。売掛金 取引先別 補助科目の当月 `debit`＝**案件先別の売上(計上)＋構成比**、費用は PL 科目別（当月発生＝借方−貸方）。費用は**科目クリックで仕訳明細を展開**。入金・未回収は混ぜない。
- **④ 回収・支払（資金）**：対象月セレクタつき。**回収トラッカー**（請求管理台帳ベース：請求1件ごとに 取引先・対象月・請求額・**支払期限・入金日・状態**＝🔴遅延/発行漏れ・🟡期限前・🟢入金済、先頭に問題件数・金額）。あわせて MF 未回収残の取引先別チャートと、未払金 支払先別（計上・支払・未払残）。「未請求(発行漏れ)」は台帳ステータスをそのまま映すもので、実際に未発行か台帳の更新漏れかは人が確認する。

## 役割と非役割
- やる：MF（試算表PL/BS・仕訳）を正本に、当期の売上／費用構成／純損益・売掛金(未回収)／未払金・直近仕訳を可視化。
  台帳は当月オペレーション（請求予定・採番待ち等）の補助としてのみ読む。
- やらない：仕訳の確定・台帳の更新・送金（= 各 osi-finance-* スキルや人の役割）。本スキルは**読み取り表示のみ**。

## データ源（MF 正本・確実な順）

> **税基準（表示の前提・ここを黙って混ぜない）**
> MFのレポート系（TrialBalance / Transition の PL・BS）は、経理方式が「税抜(内税)」のとき
> **既定で税抜**を返す。一方、**請求管理台帳の請求額・BSの売掛金/未払金は税込**。
> したがって本ダッシュボードは「**PL＝税抜／回収トラッカーと売掛金＝税込**」が混在する。
> - PLの数字には必ず「税抜」と明示する（既定テンプレは注記済み）。
> - PLと台帳の請求額を**引き算・突合しない**。比較が必要なら `include_tax: true` で税込に揃えるか、
>   `osi-finance-mf-sync` に回す。ここで安易に混ぜると1割ずれた比較を人に見せることになる。
> - `include_tax` が効くのは経理方式が「税抜(内税)」のときだけ。

0. **MoneyForward 事業者・会計期間** `mfc_ca_currentOffice` → `accounting_periods[0]` の `start_date`/`end_date`/`fiscal_year` で当期（期首〜本日、期末を超えない）を決める。会計年度開始月を決め打ちしない（2月期首等にも自動対応）。
0.5 **推移PL（②月次推移）** `mfc_ca_getReportsTransitionProfitLoss`（`type:"monthly"`）→ `columns` が月、`rows` の売上高合計／販管費合計／当期純利益(損失) の各月 `values[i]`。`settlement_balance`/`total` は除外、期首〜当月で打ち切り。
0.6 **補助科目（取引先別）** PL/BS を `with_sub_accounts:true` で取得。売掛金 補助科目＝**案件先別売上**（debit=請求/credit=入金/closing=未回収）、未払金 補助科目＝**支払先別**。費用科目には補助が無いため、費用の取引先内訳は**仕訳**(`getJournals` を費用 account_id で)から取る。
0.7 **回収トラッカー＝請求管理台帳（④）** Drive `read_file_content` で台帳の「月次請求スケジュール」を読み（markdown 行を `|` 分割し3列目が `YYYY-MM` の行のみ採用）、各請求行の **支払期限・入金日・請求ステータス** から「いつまでに・いくら・入金あったか・いつ・遅延か」を判定（🔴遅延/発行漏れ・🟡期限前・🟢入金済）。台帳ローダー(`ensureLedger`)が `LEDGER_ROWS` に一度だけ読み込む。
1. **MoneyForward 試算表 PL（売上・費用・純損益＝正本）**
   - `mfc_ca_getReportsTrialBalanceProfitLoss`（`start_date`=会計年度開始日, `end_date`=本日）
     → `rows` の「**売上高合計**」`values[3]`＝当期売上、「販売費及び一般管理費合計」の子 `rows`（`type:account`）が
       科目別費用、「当期純損益/税引前当期純損益」`values[3]`＝**正しい純損益**（売上−費用）。
   - 科目を **支払(AP)** と **経費** に分類：osi-finance-settings の分類表（既定：AP＝業務委託料・地代家賃・支払報酬／経費＝通信費・旅費交通費・接待交際費・会議費・備品消耗品費・広告宣伝費）。
2. **MoneyForward 試算表 BS（売掛金=未回収・未払金=未払＝正本）**
   - `mfc_ca_getReportsTrialBalanceBalanceSheet`（同期間）→ BS の「**売掛金**」`closing_balance`＝AR 未回収、
     「未払金」`closing_balance`＝AP 未払。AR が `osi-finance-ar-sync` で MF に載るため、未回収はここを正本にできる。
3. **MoneyForward 仕訳（直近の動き）**
   - `mfc_ca_getJournals`（同期間）→ 直近仕訳（売上計上・入金消込・支払。`branches[].debitor/creditor` の
     `account_name` と `value+tax_value`、`remark` の摘要から相手先・請求書ID）。
4. **請求管理台帳（当月オペレーションの補助のみ）**
   - Google Drive の `read_file_content`（osi-finance-settings の AR台帳パス）で「月次請求スケジュール」を取得し、
     **当月の請求予定・採番待ち・宛先未補完**など"やること"を出す補助に使う（会計の数字＝AR残高は MF の BS を正本）。
   - 自然言語テキストのため、必要時のみアーティファクト内で `window.cowork.askClaude(prompt, [台帳テキスト])` で
     当月オペ項目を JSON 抽出する。**売上・未回収の金額は台帳ではなく MF を出典にする。**

## アーティファクトの作り方
1. `references/dashboard-template.html`（同梱・5タブ実装済み）を土台にする。
2. テンプレ先頭の `T`（MFコネクタ接頭辞）を実コネクタIDに、`AP_ACCOUNTS`（科目分類）を osi-finance-settings に差し替える。**④の回収トラッカー（台帳）を使う場合**は `AR_LEDGER_FILE_ID`（請求管理台帳の Drive fileId）・`DRIVE`（`mcp__…__`）を差し替える（未設定なら④回収トラッカーは台帳取得エラー表示）。会計年度は currentOffice 自動取得。
3. 完成HTMLをワークスペースに書き出し、`create_artifact`：
   - `id`：例 `osi-finance-dashboard`
   - `mcp_tools`：MF 5ツール
     `["mcp__…__mfc_ca_currentOffice","mcp__…__mfc_ca_getReportsTrialBalanceProfitLoss","mcp__…__mfc_ca_getReportsTrialBalanceBalanceSheet","mcp__…__mfc_ca_getJournals","mcp__…__mfc_ca_getReportsTransitionProfitLoss"]`
     **＋④の回収トラッカー（台帳）を使うなら Drive `read_file_content`**（`mcp__…__read_file_content`）。**当該セッションで実際に呼んで形を確認したツールだけ**列挙する。
4. ライブ表示のためページ読み込み時にツールを呼ぶ。ヘッダのリロードで最新化される（自前の更新ボタンは作らない）。
   売上=0 の現状（AR 未計上の事業者）でも各パネルがエラーで落ちないようガードする（0表示・空テーブルで継続）。

## 実装メモ
- ライト用：`:root{color-scheme:light}`、薄背景＋濃文字。Chart.js は指定の integrity 付きCDNのみ。
- `callMcpTool` の戻りは `r.structuredContent ?? JSON.parse(r.content[0].text)` で読む。
- 取得失敗は各パネルでエラー表示（全体を落とさない）。localStorage で表示設定の記憶可。
- **売上・売掛金(未回収)は MF（試算表 PL/BS）を正本**に表示し「MoneyForwardより」と出典明記する。
  売上=0 の事業者（AR 未計上）でも 0 表示で落とさない。台帳由来は「当月オペレーション（請求予定等）」に限り、その出典は「請求管理台帳より」と明記する。

## 留意
- 表示専用。数値の確定・修正は台帳/MF側で人が行う。
- 機微値は出さない（口座番号等）。各組織のデータはその組織のコネクタ越しにのみ取得される。

## エラー処理

詳細は **[`docs/エラー処理ガイド.md`](../../docs/エラー処理ガイド.md)** を正本とする。本スキルで詰まりやすい点：

- **MF の対象事業者・会計年度期間ズレ**：処理前に対象事業者を社名で確認し、期間は会計年度開始日〜本日で取る（`osi-finance-settings` の会計年度開始月に合わせる）。
- **AR台帳の読取が大容量で失敗**するとき：台帳はローカル同期で開ける状態にし、アーティファクト内は `window.cowork.askClaude` で堅牢に抽出する。
- 取得失敗は**各パネルでエラー表示し全体を落とさない**。表示専用で、数値の確定・台帳更新・送金はしない。
