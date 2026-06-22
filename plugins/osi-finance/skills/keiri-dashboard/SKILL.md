---
name: keiri-dashboard
description: >
  OSI Finance の「会計ダッシュボード」を Cowork のライブ・アーティファクトとして生成するスキル。
  開くたびに MoneyForward（当期の費用構成・純損益・直近の支払仕訳）と請求管理台帳（当月の請求・
  入金状況）から最新データを取得し、請求(AR)・支払(AP)・経費の状況を1枚で一覧表示する。
  「会計ダッシュボードを作って」「今月の請求状況・支払状況・経費状況を一覧で見たい」「経理の
  ダッシュボードを出して」「請求と支払と経費をまとめて管理したい」「財務の現状を一目で」「損益と
  費用の内訳を見せて」などで発動する。組織固有値（台帳の場所・ファイル名・会計年度開始月）は
  `config/keiri-settings.md` を参照する。データの確定・送金・台帳更新はしない（表示専用）。
requires_connectors:
  - server: money-forward
    provision: user-install

---

# keiri-dashboard（会計ダッシュボード — ライブ・アーティファクト生成）

> **組織固有値（台帳ルート／ファイル名・会計年度開始月・科目の支払/経費分類）は
> `config/keiri-settings.md`（テンプレ：`config/keiri-settings.example.md`）を参照する。**

請求(AR)・支払(AP)・経費の「今の状況」を1画面で見えるようにする、表示専用のダッシュボード。
`mcp__cowork__create_artifact` で**ライブ・アーティファクト**として作る（開くたびにコネクタから最新取得・再オープン可）。

## 役割と非役割
- やる：MF＋台帳から読み取り、当期の費用構成／純損益／直近の支払／当月の請求・入金状況を可視化。
- やらない：仕訳の確定・台帳の更新・送金（= 各 keiri-* スキルや人の役割）。本スキルは**読み取り表示のみ**。

## データ源（確実な順）
1. **MoneyForward（構造化・確実）**
   - `mfc_ca_getReportsTrialBalanceProfitLoss`（`start_date`=会計年度開始日, `end_date`=本日）
     → `rows` の「販売費及び一般管理費合計」の子 `rows`（`type:account`）が科目別費用。各 `values[3]`＝期末残高。
       「当期純損失/税引前当期純損失」`values[3]`＝純損益。
   - `mfc_ca_getJournals`（同期間）→ 直近の支払仕訳（`branches[].debitor` の `account_name` と `value+tax_value`、`remark` の摘要から支払先）。
   - 科目を **支払(AP)** と **経費** に分類：keiri-settings の分類表（既定：AP＝業務委託料・地代家賃・支払報酬／経費＝通信費・旅費交通費・接待交際費・会議費・備品消耗品費・広告宣伝費）。
2. **請求管理台帳（AR・台帳が正本／MFは売上未計上）**
   - Google Drive の `read_file_content`（keiri-settings の AR台帳パス）で「月次請求スケジュール」を取得。
   - 返るのは自然言語テキストなので、アーティファクト内で `window.cowork.askClaude(prompt, [台帳テキスト])` を使い
     「当月（対象月）の未請求合計・請求総額・入金済・未回収」をJSONで抽出させる（堅牢化）。
   - 簡易運用では、起動時にスキル側で当月数値を算出し初期値として埋め込んでもよい。

## アーティファクトの作り方
1. `references/dashboard-template.html`（同梱）を土台にする。3パネル構成：
   - カード（当期費用合計／当期純損益／当月未請求(AR)／AR未回収残）
   - 費用科目ドーナツ（🔵AP/🟠経費で色分け・Chart.js）＋ AP/経費の内訳バー
   - 請求状況(AR) テーブル ＋ 直近の支払仕訳テーブル
2. テンプレ内の会計年度開始月（既定4月）・台帳パス・科目分類を keiri-settings の値に差し替える。
3. 完成HTMLをワークスペースに書き出し、`create_artifact`：
   - `id`：例 `keiri-dashboard`
   - `html_path`：書き出したファイル
   - `mcp_tools`：`["mcp__…__mfc_ca_getReportsTrialBalanceProfitLoss","mcp__…__mfc_ca_getJournals"]`（＋AR台帳を読むなら Drive `read_file_content` も）。**当該セッションで実際に呼んで形を確認したツールだけ**列挙する。
4. ライブ表示のためページ読み込み時にツールを呼ぶ。ヘッダのリロードで最新化される（自前の更新ボタンは作らない）。

## 実装メモ
- ライト用：`:root{color-scheme:light}`、薄背景＋濃文字。Chart.js は指定の integrity 付きCDNのみ。
- `callMcpTool` の戻りは `r.structuredContent ?? JSON.parse(r.content[0].text)` で読む。
- 取得失敗は各パネルでエラー表示（全体を落とさない）。localStorage で表示設定の記憶可。
- 売上(AR)はMF未計上が前提。AR の数字は必ず「請求管理台帳より」と出典明記する。

## 留意
- 表示専用。数値の確定・修正は台帳/MF側で人が行う。
- 機微値は出さない（口座番号等）。各組織のデータはその組織のコネクタ越しにのみ取得される。
