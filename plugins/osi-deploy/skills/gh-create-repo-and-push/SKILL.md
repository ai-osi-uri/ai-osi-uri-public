---
name: gh-create-repo-and-push
description: ローカル作業ディレクトリの内容を新規 GitHub リポジトリに作成して push する atomic スキル。認証は AI OSI URI Deploy 拡張（mcp/ai-osi-uri-deploy）が保持する GitHub PAT を使い、`.env` は読まない。拡張の MCP ツール `github_create_repo_and_push` を呼ぶだけ。命名衝突時の自動採番・PAT 入り remote の削除はツール側が担当。オーケストレータ `deploy-app` の Step 1 相当として呼ばれる。「GitHub に push して」「リポジトリ作って push」「新しい repo に上げて」「コードを GitHub に上げて」などで発動。GitHub PAT の入力は拡張設定の役割。リポ作成のみ・push のみの片割れ作業には使わない。
version: 0.3.0
---

# GitHub リポジトリ作成 + 初回 push（atomic / 拡張ツール版）

入力ディレクトリの中身を新規 GitHub リポジトリに push する。**認証情報は AI OSI URI Deploy
拡張**（`mcp/ai-osi-uri-deploy`、設定欄に入力した GitHub PAT がキーチェーンに保存される）が
保持する。本スキルは `.deploy-credentials/.env` を読まず、拡張が提供する MCP ツール
`github_create_repo_and_push` を呼ぶだけ。

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| AI OSI URI Deploy 拡張が有効・GitHub PAT 入力済み | `health_check` ツールで `github.valid: true` | `setup-deploy-environment` を案内（拡張インストール手順） |
| `INPUT_DIR` が存在し中身がある | 呼び出し側が用意 | エラーで中断 |

## 入力契約（= ツール引数）

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `input_dir` | ✅ | push したい中身が入っているローカル絶対パス |
| `repo_name` | ✅ | 希望リポジトリ名（衝突時は `-002` 等を自動採番） |
| `is_private` | 任意 | `true`/`false`（デフォルト `true`） |
| `commit_message` | 任意 | 初回コミットメッセージ（デフォルト `Initial scaffold`） |
| `owner_override` | 任意 | 呼び出し側（deploy-app）の `USE_ORG` 判定に従う。真=`"ai-osi-uri"`、偽=`"personal"`。atomic 単体呼び出し時の既定は personal（安全側） |

> 作成先ポリシー（2026-07）: org と個人を混在させない。deploy-app が GitHub/Vercel/Supabase の
> org 3点をプリフライト判定し（USE_ORG）、全部揃えば `"ai-osi-uri"`、1つでも欠ければ `"personal"`
> を `owner_override` に渡す。403（org 権限なし）は「欠け」として personal に倒す。

## 実行

`.env` 読み込みや curl・git は不要。**拡張の MCP ツールを 1 回呼ぶ**だけ：

```
github_create_repo_and_push({
  input_dir: "<INPUT_DIR>",
  repo_name: "<REPO_NAME>",
  is_private: true,
  commit_message: "Initial scaffold",
  owner_override: "ai-osi-uri"   // USE_ORG が偽なら "personal"（呼び出し側が決定）
})
```

ツールはリポ作成（衝突時サフィックス採番・最大5回）→ 作業ディレクトリへコピー（`.git` 除外）→
`git init`/commit/push → **PAT 入り remote の削除**まで行う。

## 戻り値（後続 atomic への引き継ぎ）

ツールの戻り JSON をそのまま使う：`repo_name` / `repo_owner` / `repo_id`（数値・Vercel 必須）/
`repo_url` / `work_dir`。これらを `vercel-connect-and-deploy` に渡す。

## エラー時の挙動

| 事象 | ツール出力 | 対応 |
| --- | --- | --- |
| GitHub PAT 未設定 | `error: GITHUB_PAT が未設定…` | 拡張設定で PAT 入力を案内 |
| PAT 無効（401） | `error: …401` | 拡張設定で PAT 再発行・更新 |
| Org 権限なし（403） | `error: …403` | `owner_override:"personal"` で再試行、または Org 権限付与を依頼 |
| 名前衝突 5 連続 | `error: …名前衝突` | 別の `repo_name` を提案して再試行 |
| push 失敗 | `error: git push…`（repo は作成済み） | オーケストレータの判断に委ねる |

## 注意事項

- 作成先は `owner_override` で制御。org と個人を混在させないため、呼び出し側（deploy-app）の USE_ORG 3点判定に従う（未指定時の安全既定は personal）。
- ツールが push 後に PAT 入り remote を削除するので、認証情報は残らない。
- `input_dir` に `.env` / `node_modules` を含めないのは呼び出し側の責任（ツールは `node_modules`・`.git`・`.DS_Store` をコピー除外する）。
