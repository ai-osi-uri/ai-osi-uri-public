---
# osi-profile — 会社プロファイル（雛形）
# このファイルを、Claude に連結しているフォルダの直下に `osi-profile.md` としてコピーし、値を埋める。
# 実値版はコミットしない（.gitignore の `**/osi-profile.md`）。
osi_profile: 1

company:
  name: "{{登記どおりの正式社名 例: サンプル株式会社}}"
  name_display: "{{読みやすい表記 例: Sample Inc.}}"
  name_kana: "{{読み}}"
  corporate_number: "{{法人番号13桁}}"
  representative: "{{代表者 例: 代表取締役 山田 太郎}}"
  postal_code: "{{郵便番号}}"
  address: "{{本社所在地}}"
  phone: "{{代表電話}}"
  domain: "{{example.com}}"
  url: "{{https://example.com/}}"
  contact_email: "{{info@example.com}}"
  invoice_registration_no: "{{T+13桁。機微値。チャットに貼らず、ここにだけ書く}}"
  business: "{{事業内容を1行で}}"
  tagline: "{{理念・一言（任意）}}"
  slug: "{{英小文字の短い識別子 例: sample。S3 バケット名などの接頭辞に使う}}"
  reverse_domain: "{{com.example のような逆ドメイン。アプリの Bundle ID / Package Name の接頭辞}}"
  reverse_domain_path: "{{com/example（reverse_domain をパス区切りにしたもの）}}"

members:
  owner: "{{台帳の担当者列に使う自分の表記 例: 山田}}"
  team: []            # 任意。記事の会社概要などで使う。例: ["代表取締役 山田 太郎", "取締役 佐藤 花子（略歴）"]

# パスはすべて root からの相対。root は「この osi-profile.md があるフォルダ」。
paths:
  root: "."
  projects: "案件"                              # 案件フォルダの親
  project_naming: "{案件ID3桁}.{企業名}"         # 案件フォルダの命名
  project_subfolders: ["01_提案・見積", "02_契約", "03_制作・成果物", "04_請求", "05_受領資料"]
  project_template: "案件/000.フォルダ構造テンプレート"
  shared: "共通"                                # 案件横断の置き場（鍵の退避・ピン状態など）
  sales_admin: "営業管理"                        # 営業管理表とそのルール
  sales_materials: "営業資料"
  pr_articles: "広報/案件記事"                   # PR 記事の保存先
  finance: "経理"                               # OSI Finance のルート（osi-finance-settings.md を置く場所）
  contracts: "契約管理"
  billing: "請求管理"
  expenses: "経費管理"
  vault: ""                                     # Obsidian vault の絶対パス（使う場合のみ 例: ~/ObsidianVault）

ledgers:
  sales: "営業管理/営業管理表.xlsx"              # 案件マスタ（営業管理表）の実ファイル
  sales_tab: "取引先管理"
  sales_header_row: 5
  sales_rules: "営業管理/営業管理表_運用ルール.md"
  apps: "案件/_アプリ台帳.md"                    # 作ったアプリの一覧

# 使うコネクタ（true のものだけスキルが前提にする。false なら該当機能を案内して止まる）
connectors:
  deploy: false        # AI OSI URI Deploy（GitHub / Vercel / AWS / Supabase / Stripe）
  finance: false       # AI OSI URI Finance（台帳同期・MF請求書）
  creative: false      # AI OSI URI Creative（画像・動画・音声）
  obsidian: false
  money_forward: false
  docusign: false
  plaud: false
  slack: false
  gmail: false
  google_calendar: false
---

# osi-profile の読み方（スキル向け）

## 1. 役割

スキルの本文には会社固有の値（社名・パス・台帳名・担当者名）を書かない。
本文は `{{company.name}}` `{{paths.projects}}` `{{ledgers.sales}}` のような**変数**で書き、
値はこのプロファイルから引く。プロファイルを差し替えるだけで別の会社で同じスキルが動く。

## 2. 解決規則（スキルが値を引く順）

1. 連結フォルダ直下の `osi-profile.md`（このファイルの実値版）
2. 連結フォルダ直下の `_shared/osi-profile.md`
3. どちらも無ければ **質問して作る**（`config/osi-profile.example.md` を雛形に、会社名・案件フォルダ・
   台帳の有無・使うコネクタの 4〜5 問）。値が埋まるまで、パスや社名に依存する処理へ進まない。

`{{paths.*}}` `{{ledgers.*}}` は root からの相対パス。実体は `{{paths.root}}/<値>`。
`{{company.*}}` `{{members.*}}` は文字列をそのまま差し込む。

## 3. プラグイン固有の設定との関係

- `osi-finance-settings.md`（`{{paths.finance}}` に置く）と `osi-sales-settings.md` は、
  **各プラグインだけが使う項目**（採番規則・税率・列名・ステータス値 など）を持つ。
- 会社共通の項目（社名・住所・登録番号・案件ルート・台帳の場所）は **このプロファイルが正本**。
  プラグイン設定に同じ項目があれば、プラグイン設定を優先して読む（移行期の互換のため）。

## 4. 機微値の扱い

- インボイス登録番号・法人番号・口座番号は **このファイルにだけ**書く。チャットに貼らない。
  スキルは必要なときにこのファイルから読み、出力（請求書・契約書）にだけ使う。
- 実値版 `osi-profile.md` は Git に入れない。共有は連結フォルダ（Drive 等）の権限で行う。

## 5. 書き手向け（スキルを作る・直す人）

- 本文に固有値を書きそうになったら、ここにキーがあるか探す。無ければキーを**足す**（消さない）。
- 固有値を書いてよいのは `examples/` と `*.example.md` だけ（CI の `validate_skills.py` が検査する）。
- 例文には `サンプル株式会社` `山田太郎` `example.com` を使う。
