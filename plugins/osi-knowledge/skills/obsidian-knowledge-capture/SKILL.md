---
name: obsidian-knowledge-capture
description: Obsidian vault（~/ObsidianVault）に会話・思考・気づき・調査結果を自律的に保存・整理するスキル。ユーザーが「知識化して」「Obsidianに保存」「vaultにまとめて」「Conceptに切り出して」「議事録にして」「Resourceとして保存」「Inboxに入れて」「ノートにして」「永続化して」「これ残しておいて」など、会話内容や思考を永続的な知識として保管したいと発話したときに必ず発動する。obsidian MCPサーバ（mcp__obsidian-mcp-tools__*）が利用可能な環境で使う。フォルダ・タイトル・frontmatter・リンクはすべてClaudeが自律判断し、ユーザーに細かく聞き返さない（判断つかない場合のみ最大1問）。判断ルールは vault 内の 90_Meta/ を毎回参照する単一情報源原則。完了後は必ず透明性レポート（新規N件・更新M件・リンクK本）を返す。AI OSI URI のメンバーが日々の会話・打ち合わせ・気づきを Obsidian に蓄積する運用で必須となる。
version: 0.2.0
---

# Obsidian Knowledge Capture

Obsidian vault に会話・思考・知見を**自律的に**保存・組織化するスキル。

## v0.2.0 で変わったこと

- **MCPツール名を `mcp__obsidian-mcp-tools__*` に統一**（旧 `mcp__obsidian__*` から変更。実環境で使えるツール名に合わせた）
- **Vault フォルダ構造を現状に合わせて修正**（`20_Concepts/` → `50_Resources/Concepts/` 等）
- **`90_Meta/` の必読ファイル一覧を最新化**（5本構成：運用ルール／フォルダ規約／frontmatterスキーマ／表記揺れ正規化表／Concept昇華基準）

## なぜこのスキルか

ユーザーの認知負荷をゼロに近づけることが目的。「どこに保存しますか？」「タイトルは？」と聞き返すと、知識化の習慣そのものが続かない。Claude側で**6項目（タイプ・重複・保存先・frontmatter・リンク・既存更新）を自律判断**して即座に書き込み、結果だけ報告する。

vault は「自己記述型」設計になっており、ルール（命名・分類・frontmatter）は vault 内の `90_Meta/` に書かれている。スキル本体にはルールを重複定義せず、毎回 `90_Meta/` を読みに行く。これによりルール更新が自動的にスキル挙動に反映される。

## トリガーフレーズと挙動

| フレーズ | 挙動 |
|---|---|
| 「知識化して」「ノートにして」「永続化して」「vaultにまとめて」「Obsidianに保存」「これ残して」 | 会話を解釈し、最適なノートタイプ・フォルダ・形式で保存（標準コマンド） |
| 「Conceptに切り出して」「永続ノートにして」 | `50_Resources/Concepts/` への永続ノート化に限定 |
| 「議事録にして」「ミーティングログに」 | `20_Clients/<顧客>/議事録/` または `30_Projects/<PJT>/議事録/` に保存 |
| 「Inboxに入れて」「とりあえず保存」 | `00_Inbox/` に整理せず放り込む |
| 「Resourceとして保存」「クリップして」 | `50_Resources/AI/` 等に外部資料として保存 |
| 「TILにして」「学びログに」 | `50_Resources/TIL/` に学びログとして保存 |
| 「人物ノートにして」 | 現状は `20_Clients/<会社>/README.md` の `## キーマン` テーブルに追記（独立 `40_People/` は未稼働） |

明示的なフォルダ指定がある場合（「Conceptに切り出して」等）はその指示に従う。「知識化して」のような汎用指示の場合は自分でタイプを判定する。

## ワークフロー

### Step 1: vault の運用ルールを読む（必須・毎回）

vault は自己記述型なので、保存ルールが vault 内に書かれている。これを単一情報源として尊重する。

以下を `mcp__obsidian-mcp-tools__get_vault_file` で読む：

1. `90_Meta/運用ルール.md` — 知識化コマンドの仕様、書き込み原則、姉妹スキルとの責務分担
2. `90_Meta/フォルダ規約.md` — このVaultにおけるパスの正
3. `90_Meta/frontmatterスキーマ.md` — type別のメタデータ仕様
4. `90_Meta/表記揺れ正規化表.md` — 顧客名・固有名詞の正規形
5. `90_Meta/Concept昇華基準.md` — Concept化判定基準

これを飛ばすと、命名や frontmatter が vault の規約と不整合になる。**省略してはいけない**。

### Step 2: 既存ノートを横断検索

`mcp__obsidian-mcp-tools__search_vault_simple` で会話の主要キーワード（概念・固有名詞）を検索。

目的は2つ：
- **重複確認** ── 既に同主題のノートがあれば新規作成しない
- **リンク候補発見** ── 関連ノートを 3-5本見つけて、新ノートからリンクを張る対象にする

検索キーワードが曖昧な場合は複数回の検索を許容する（コストより精度優先）。**表記揺れ（カタカナ／英語／略称）も1度試す**（`90_Meta/表記揺れ正規化表.md` を参照）。

### Step 3: 自律的に6項目を判定

ユーザーに聞かずに以下を決める。詳細は `references/classification-flow.md` を参照。

1. **タイプ判定** ── inbox/daily/client/project/concept/moc/meeting/resource/til のどれか
2. **重複/新規** ── 既存ノートに追記か、新規作成か
3. **保存先** ── `90_Meta/フォルダ規約.md` 準拠のフォルダパスとファイル名
4. **frontmatter** ── `90_Meta/frontmatterスキーマ.md` の該当 type 仕様に従う
5. **リンク** ── 関連既存ノート 3-5本に `[[ノート名]]` で張る
6. **タイトル** ── 内容から自然言語で決める（命名規則に従う）

判断つかない場合のみ、**最大1問だけ**ユーザーに確認する。「Conceptと既存Resourceの両方に該当するが、どちらを優先しますか？」のように具体的に。

固有名詞は **必ず `90_Meta/表記揺れ正規化表.md` の正規形** を使う。

### Step 4: ノート作成・更新

- **新規作成**: `mcp__obsidian-mcp-tools__create_vault_file`
- **既存追記**: `mcp__obsidian-mcp-tools__append_to_vault_file`（末尾追加）または `mcp__obsidian-mcp-tools__patch_vault_file`（特定セクション・frontmatter フィールド指定）

frontmatter は必ず `90_Meta/frontmatterスキーマ.md` の該当 type 仕様に従う。共通必須：`type`, `created`, `tags`。

### Step 5: 透明性レポート出力（必須）

何をどこに書いたか、必ず指定フォーマットで報告する。詳細は `references/transparency-report.md` を参照。

基本形：

```
✅ 知識化完了

新規作成（N件）:
- [フルパス]

既存ノート更新（M件）:
- [フルパス]  ← [どこに何を追記したか]

新規リンク（K本）:
- [ノートA] ⇔ [[ノートB]]
```

## NGパターン

- ❌ 「どこに保存しますか？」と聞く（タイプ判定で自分で決める）
- ❌ 「タイトルは何にしますか？」と聞く（内容から決める）
- ❌ 明示指示なしで全部 Inbox に放り込む（適切な場所へ振り分ける）
- ❌ 既存ノートとの重複を確認しない（必ず Step 2 を実行）
- ❌ リンクを張らずに孤立ノートを作る（最低 3本は関連を張る）
- ❌ `90_Meta/` を読まずに保存する（規約違反のノートが量産される）
- ❌ 透明性レポートを省略する
- ❌ 固有名詞を `90_Meta/表記揺れ正規化表.md` に照らさずに書く

## vault構造（参考・正は 90_Meta/フォルダ規約.md）

- `00_Inbox/` : 未整理の一時置き場
- `10_Daily/` : 日次ノート（`YYYY-MM-DD.md`）
- `20_Clients/<会社>/` : 顧客 CRM
- `30_Projects/<PJT>/` : 進行中／完了プロジェクト
- `40_Areas/` : 業務領域 MOC（現状は空き枠）
- `50_Resources/Concepts/` : 永続ノート（思考の核）
- `50_Resources/MOC/` : テーマ別 Map of Contents
- `50_Resources/AI/` : 外部資料
- `50_Resources/TIL/` : 学びログ
- `90_Archive/` : アーカイブ
- `90_Meta/` : Vault 運用ルール（このスキルが毎回読みに行く）

vault 構造が異なる場合は、Step 1 で読んだ `90_Meta/フォルダ規約.md` を信用すること。

## 利用可能な MCP ツール

- `mcp__obsidian-mcp-tools__list_vault_files`
- `mcp__obsidian-mcp-tools__get_vault_file`
- `mcp__obsidian-mcp-tools__search_vault_simple`
- `mcp__obsidian-mcp-tools__search_vault`
- `mcp__obsidian-mcp-tools__search_vault_smart`
- `mcp__obsidian-mcp-tools__create_vault_file`
- `mcp__obsidian-mcp-tools__append_to_vault_file`
- `mcp__obsidian-mcp-tools__patch_vault_file`
- `mcp__obsidian-mcp-tools__delete_vault_file`（削除指示時のみ）
- `mcp__obsidian-mcp-tools__show_file_in_obsidian`

## 姉妹スキルとの責務分担

| スキル | 役割 |
|---|---|
| `obsidian-knowledge-capture`（本スキル） | 書き込み・知識化 |
| `obsidian-knowledge-consult` | 読み込み・過去ノート引き出し |
| `daily-vault-sync` | 毎晩23:00の自動横断蓄積 |

3者とも `90_Meta/` を毎回読む点で揃えている。

## 参照

- `references/classification-flow.md` — タイプ判定の意思決定木
- `references/transparency-report.md` — 完了報告のフォーマット
- vault 内の `90_Meta/` — 全ての規約の単一情報源（このスキルより優先）

## 設計の核心

このスキルは「**vault を自己記述型として尊重する**」設計。スキル更新と vault 規約更新が二重作業にならないよう、ルールは常に vault 側に置く。スキルは「トリガー検知 + ワークフロー骨格 + 透明性ルール」だけを担う。
