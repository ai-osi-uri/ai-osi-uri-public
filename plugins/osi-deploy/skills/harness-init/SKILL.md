---
name: harness-init
description: 生成・デプロイするアプリのリポジトリに「ハーネスエンジニアリング」の最小構成（AGENTS.md / CLAUDE.md・init.sh・claude-progress.md・feature_list.json）を仕込む atomic スキル。エージェント（Codex / Claude Code）が長時間・複数セッションでも文脈を失わず、検証なしに完了宣言せず、1機能ずつ証拠ありで進められるように、指示・環境・状態・フィードバックの4サブシステムをリポジトリに自己記述させる。プロジェクトのスタック（INSTALL/VERIFY/START コマンド、テスト・Lint）を受け取り、プレースホルダを実値に埋めて配置する。「ハーネスを入れて」「AGENTS.md を作って」「このリポにハーネスエンジニアリングを仕込んで」「エージェントが迷子にならないようにして」「進捗管理とfeature_listを入れて」など、リポジトリにエージェント運用の足場を入れるリクエストで発動する。通常はオーケストレータ deploy-app の scaffold 直後（Vercel パス Phase 4-V / AWS パス Phase 4-A）から呼ばれる。実デプロイ・課金・インフラ構築は行わない（それぞれ vercel-connect-and-deploy / aws-static-deploy / setup-infra の役割）。
version: 0.1.0
---

# harness-init — リポジトリにハーネスエンジニアリングの足場を仕込む（atomic）

生成済み or 既存のアプリリポジトリに、エージェントが信頼して作業できる **最小ハーネス**
4 ファイルを配置する。モデルを賢くするのではなく、モデルの周りに **閉ループの作業システム**
を作るのが目的。

参考: Learn Harness Engineering / OpenAI "Harness Engineering" / Anthropic "Effective
harnesses for long-running agents"。

このスキルは **ファイルを置いて埋めるところまで**が責任範囲。実ビルド・デプロイ・
課金・インフラ構築は呼び出し側（`deploy-app` や各 atomic）に委譲する。

---

## 何を置くか（4サブシステム）

| ファイル | サブシステム | 役割 |
|---|---|---|
| `AGENTS.md`（Claude Code 中心なら `CLAUDE.md`） | 指示 | 最初に読む「地図」。約100行。技術スタック・検証コマンド・完了の定義・hard constraints |
| `init.sh` | 環境 | 依存インストール→検証→起動を一発。失敗したらベースライン修復を促す |
| `claude-progress.md` | 状態 | セッションをまたぐ進捗ログ。終了前に更新、開始時に最初に読む |
| `feature_list.json` | フィードバック/制御 | 機械可読の機能トラッカー。in_progress は常に1件、証拠ありで passing |

> 5つ目の「ツール」サブシステムはスキルでファイル配置しない（最小権限でシェル等を
> 与える運用判断のため）。AGENTS.md にツール方針を1行書くに留める。

---

## 入力契約

| 項目 | 必須 | 説明 | 既定 |
| --- | --- | --- | --- |
| `TARGET_DIR` | ✅ | ハーネスを置くリポジトリのルート | — |
| `AGENT_FILE` | 任意 | `AGENTS.md` か `CLAUDE.md` のどちらを置くか | `AGENTS.md` |
| `INSTALL_CMD` | 任意 | 依存インストール | `npm install` |
| `VERIFY_CMD` | 任意 | 基本検証（テスト等） | `npm test` |
| `START_CMD` | 任意 | 開発サーバ起動 | `npm run dev` |
| `TEST_CMD` / `TYPECHECK_CMD` / `LINT_CMD` | 任意 | AGENTS.md 検証コマンド欄に展開 | 空欄=TODO |
| `PROJECT_NAME` / `PROJECT_DESCRIPTION` | 任意 | 概要欄に展開 | 空欄=TODO |
| `STACK` | 任意 | `node` / `python` / `static` 等。既定コマンドの推定に使う | `node` |
| `OVERWRITE` | 任意 | 既存ファイルを上書きするか（`1` で上書き） | `0`（既存は温存しスキップ） |

スタック別の既定コマンド推定（`STACK` 未指定時はリポジトリを見て判定）：

| STACK | INSTALL_CMD | VERIFY_CMD | START_CMD |
|---|---|---|---|
| node | `npm install` | `npm test` | `npm run dev` |
| python | `pip install -r requirements.txt`（`uv.lock` あれば `uv sync`） | `pytest -x` | `（プロジェクト依存）` |
| static | `（なし）` | `（リンク切れチェック等、任意）` | `（不要 / プレビュー）` |

---

## ワークフロー

```
1. TARGET_DIR の存在確認。スタック自動判定（package.json / pyproject.toml / *.html）
2. 既定コマンドを決定（入力 > 自動判定 > フォールバック）
3. assets/ の4テンプレをコピーし、プレースホルダを実値で置換して TARGET_DIR に配置
   - 既存ファイルがあり OVERWRITE!=1 ならスキップ（既存を壊さない）
4. AGENT_FILE が CLAUDE.md 指定なら AGENTS.md → CLAUDE.md にリネーム配置
5. init.sh を chmod +x
6. 配置結果サマリを返す（置いた / スキップした / 埋めた値）
7. （任意）init.sh を実行してベースライン検証が通るか確認
```

---

## Step 1: スタック判定と既定コマンド決定

`scripts/scaffold_harness.sh` が以下を行う。手で実行する場合の例：

```bash
bash scripts/scaffold_harness.sh \
  --target "$TARGET_DIR" \
  --agent-file "${AGENT_FILE:-AGENTS.md}" \
  --stack "${STACK:-auto}" \
  --install "${INSTALL_CMD:-}" \
  --verify "${VERIFY_CMD:-}" \
  --start "${START_CMD:-}" \
  --project-name "${PROJECT_NAME:-}" \
  --project-desc "${PROJECT_DESCRIPTION:-}" \
  --overwrite "${OVERWRITE:-0}"
```

`--stack auto` のとき、`package.json` があれば node、`pyproject.toml`/`requirements.txt`
があれば python、`*.html` のみなら static と判定する。

## Step 2: テンプレ配置と置換

`scaffold_harness.sh` は `assets/` の以下4ファイルを置換しながら配置する：

- `AGENTS.md` … `{{PROJECT_NAME}}` `{{PROJECT_DESCRIPTION}}` `{{INSTALL_CMD}}`
  `{{VERIFY_CMD}}` `{{START_CMD}}` `{{TEST_CMD}}` `{{TYPECHECK_CMD}}` `{{LINT_CMD}}` を置換。
  未指定の項目は `【TODO: ...】` のまま残す（埋め漏れを可視化するため）
- `init.sh` … `INSTALL_CMD` / `VERIFY_CMD` / `START_CMD` の3変数を置換。`chmod +x`
- `claude-progress.md` … `Current Verified State` の起動/検証パスに実コマンドを反映
- `feature_list.json` … example-001/002 のひな形をそのまま配置（中身は呼び出し側 or 人が埋める）

> **冪等性**: 既存ファイルがあり `OVERWRITE!=1` なら触らずスキップ。誤って既存の
> AGENTS.md を上書きしないこと。スキップした旨はサマリに必ず出す。

## Step 3: 配置サマリを返す

```
=== harness-init 完了 ===
TARGET: <dir>
配置: AGENTS.md(新規) / init.sh(新規,+x) / claude-progress.md(新規) / feature_list.json(新規)
スキップ: （なし or 既存ファイル名）
埋めた値: INSTALL=<...> VERIFY=<...> START=<...>
残TODO: AGENTS.md 内の【TODO】が N 箇所（hard constraints / docs リンク等）
次の一手: feature_list.json に最初の機能を1件書き、init.sh でベースライン検証を通す
```

## Step 4（任意）: ベースライン検証

`RUN_VERIFY=1` のとき `cd TARGET_DIR && ./init.sh` を実行し、VERIFY が通ることを
確認する。失敗したら「新機能着手前にベースライン修復が必要」と報告し、ここで止める。

---

## 完了の定義

- 4ファイル（または CLAUDE.md 版）が TARGET_DIR に存在する
- init.sh が実行可能（+x）になっている
- AGENTS.md の検証コマンド欄に、判定 or 指定したコマンドが入っている
- 配置サマリ（置いた/スキップ/残TODO）を返した

---

## エラーハンドリング

| ケース | 対応 |
| --- | --- |
| TARGET_DIR が無い | エラー。先に scaffold（リポジトリ生成）を済ませる |
| スタック判定不能 | static 扱いにフォールバックし、コマンドは TODO のまま置く |
| 既存 AGENTS.md あり & OVERWRITE!=1 | スキップしてサマリに明記（壊さない） |
| RUN_VERIFY で検証失敗 | ベースライン破損として報告し中断。デプロイには進ませない |

---

## 注意事項

- このスキルは **足場を置くだけ**。機能実装・デプロイ・課金はしない
- `AGENTS.md` は「百科事典でなく地図」。約100行に保ち、詳細は `docs/` に逃がす
- 検証コマンド（フィードバックサブシステム）が最重要。ここだけは TODO で残さず、
  可能な限り実値を入れる
- Claude Code 中心の案件は `AGENT_FILE=CLAUDE.md` を渡す。Codex 併用なら `AGENTS.md`
- 生成済みアプリだけでなく、既存リポの「後入れ」にも使える（冪等なので安全）

---

## 関連スキル

- `deploy-app` — オーケストレータ。scaffold 直後に本スキルを呼ぶ
- `gh-create-repo-and-push` — 本スキルで足場を入れてから push すると初回コミットに含められる
- `app-smoke-test` — feature_list.json の verification と役割が連続する（HTTP 検証）
- `vercel-connect-and-deploy` / `aws-static-deploy` — 実デプロイ（本スキルの後段）
