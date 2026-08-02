---
name: desktop-release-monitor
description: |
  GitHub Actions の workflow run を polling し、全 OS（Windows/Mac/Linux）
  のビルド完了後に GitHub Release の asset URL を集めて返す。
  `electron-scaffold-and-build` から呼ばれる。単体では「GitHub Actions
  のビルドを監視して」「Release の URL を取得して」で発動。Vercel
  のデプロイ監視には使わない。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# GitHub Actions ビルド監視 + Release asset 収集（atomic）

GitHub Actions の workflow run を polling し、全プラットフォームのビルドが完了したら
GitHub Releases の asset URL を収集して返す。**Electron デスクトップアプリのクロス
プラットフォームビルドの完了待ち**が主な用途。

認証情報は AI OSI URI Deploy 拡張が保持する GitHub PAT を使う。`.env` は読まない。
Vercel のデプロイ監視には使わない（それは `vercel_get_deployment_status` の役割）。

---

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| AI OSI URI Deploy 拡張が有効・GitHub PAT 入力済み | `health_check` で `github.valid: true` | `setup-deploy-environment` を案内 |
| 対象リポに GitHub Actions workflow がある | push 済み `.github/workflows/build-and-release.yml` | `electron-scaffold-and-build` で scaffold 生成 |
| workflow が tag push でトリガー済み | タグ push 済み or `workflow_dispatch` 済み | タグ push を案内 |

---

## 入力契約

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `repo` | ✅ | `"{owner}/{repo}"` 形式（例: `"ai-osi-uri/flower-inventory"`） |
| `run_id` | 任意 | workflow run の数値 ID、または `"latest"`（最新の run を自動取得）。デフォルト `"latest"` |
| `expected_platforms` | 任意 | `["win", "mac", "linux"]` のサブセット。全 asset が揃っているか検証する。デフォルト `["win", "mac"]` |
| `timeout_minutes` | 任意 | polling タイムアウト（分）。デフォルト `15` |

---

## 戻り値

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `status` | `"success" \| "failure" \| "in_progress" \| "timeout"` | 最終ステータス |
| `release_tag` | `string` | リリースタグ（例: `"v0.1.0"`） |
| `release_url` | `string` | GitHub Releases ページ URL |
| `download_urls` | `{ win?: string, mac?: string, linux?: string }` | 各 OS のインストーラダウンロード URL |
| `failure_info` | `{ job_name, conclusion, logs_url }[]` | 失敗時のジョブ情報（成功時は空配列） |

---

## polling メカニズム

GitHub REST API を使って workflow run の状態を監視する。API アクセスには Deploy
拡張の `github_push` ツール経由か、`web_fetch` による直接 REST 呼び出しを使う。

### 使用する API エンドポイント

```
# 最新の workflow run を取得（run_id が "latest" の場合）
GET /repos/{owner}/{repo}/actions/runs?per_page=1

# 特定の run のステータス取得
GET /repos/{owner}/{repo}/actions/runs/{run_id}

# run 内の各ジョブのステータス取得
GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs

# 最新の Release を取得（ビルド完了後）
GET /repos/{owner}/{repo}/releases/latest
```

### polling ループ

```
interval = 15 秒
max_iterations = timeout_minutes * 60 / 15

ループ:
  1. GET /actions/runs/{run_id} → status, conclusion を取得
  2. GET /actions/runs/{run_id}/jobs → 各ジョブの個別ステータスを取得
  3. 完了したジョブがあれば進捗を報告
  4. status == "completed" なら:
     - conclusion == "success" → Release asset 収集へ
     - conclusion == "failure" → 失敗情報収集へ
  5. status == "in_progress" または "queued" → 15 秒待って再 polling
  6. iteration > max_iterations → timeout として返す
```

---

## 進捗報告

polling 中、各ジョブの完了を検出するたびに Cowork チャットに進捗を報告する:

```
ビルド監視を開始します（flower-inventory v0.1.0）

  [待機] Windows ビルド中...
  [完了] Mac ビルド完了 (3:42)
  [完了] Linux ビルド完了 (2:15)
  [完了] Windows ビルド完了 (4:28)

全プラットフォームのビルド完了 -- GitHub Release を確認中...

  [確認] Release v0.1.0 公開済み (3 assets)

ダウンロード URL:
  Windows: https://github.com/ai-osi-uri/flower-inventory/releases/download/v0.1.0/Flower-Inventory-Setup-0.1.0.exe
  Mac:     https://github.com/ai-osi-uri/flower-inventory/releases/download/v0.1.0/Flower-Inventory-0.1.0.dmg
  Linux:   https://github.com/ai-osi-uri/flower-inventory/releases/download/v0.1.0/Flower-Inventory-0.1.0.AppImage
```

---

## asset マッチングロジック

GitHub Releases の asset 一覧から、ファイル拡張子でプラットフォームを判定する:

| 拡張子 / パターン | プラットフォーム |
| --- | --- |
| `.exe` / `.nsis` / `Setup*.exe` | win |
| `.dmg` | mac |
| `.AppImage` | linux |
| `.zip`（Mac 用バンドル） | mac（名前に `mac` / `darwin` を含む場合） |
| `.deb` / `.rpm` | linux（AppImage と併存する場合あり） |
| `*.blockmap` / `latest*.yml` | メタファイル（プラットフォーム判定には使わない） |

### 検証

`expected_platforms` の各プラットフォームに対して、少なくとも 1 つのマッチする
asset が存在することを確認する。不足があれば警告を返す:

```
警告: expected_platforms に "linux" が含まれていますが、
      Release に Linux 用 asset (.AppImage) が見つかりません。
      workflow の matrix 設定を確認してください。
```

---

## 失敗時の処理

### 一部ジョブの失敗

1 つ以上のジョブが失敗した場合、失敗したジョブのビルドログを取得する:

```
# 失敗ジョブの特定
GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs
→ jobs[] の中から conclusion == "failure" のものを抽出

# ビルドログ取得
GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs
```

報告:

```
  [失敗] Windows ビルド失敗

失敗ジョブ: build (windows-latest)
エラー概要: Error: Cannot find module 'electron-builder'
ログ URL: https://github.com/ai-osi-uri/flower-inventory/actions/runs/12345/job/67890

推奨修正:
  package.json の devDependencies に "electron-builder" が含まれているか確認してください。
```

### 全ジョブの失敗

全ジョブが失敗した場合は、workflow 設定自体の問題の可能性が高い:

```
  [失敗] 全プラットフォームのビルドが失敗しました

考えられる原因:
  - package.json の scripts.build が正しくない
  - electron-builder.yml の設定エラー
  - Node.js バージョン不一致

各ジョブのログ:
  Windows: https://github.com/.../job/111
  Mac:     https://github.com/.../job/222
  Linux:   https://github.com/.../job/333
```

### タイムアウト

polling が `timeout_minutes` を超えた場合:

```
  [タイムアウト] {timeout_minutes} 分経過してもビルドが完了しませんでした

現在のステータス:
  Windows: in_progress (8:42 経過)
  Mac:     success (5:30 で完了)
  Linux:   queued

再実行方法:
  1. GitHub Actions のページで "Re-run all jobs" をクリック
  2. または workflow_dispatch で再トリガー
```

### Release が見つからない（ビルド成功後）

ビルドは成功したが GitHub Release が作成されていない場合:

```
  [警告] ビルドは成功しましたが、GitHub Release が見つかりません

考えられる原因:
  - electron-builder の --publish オプションが指定されていない
  - GH_TOKEN が設定されていない（secrets.GITHUB_TOKEN が必要）
  - publish 設定が electron-builder.yml に含まれていない

修正:
  workflow の Build ステップに以下を確認:
    run: npx electron-builder --${{ matrix.platform }} --publish always
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## リトライメカニズム

ビルド失敗後、ユーザーが修正コードを提供した場合の再実行フロー:

```
1. ユーザーが修正内容を提示
2. work_dir のコードを修正
3. github_push で修正を push:
   github_push({
     work_dir: "{work_dir}",
     repo_name: "{repo_name}",
     repo_owner: "{owner}",
     commit_message: "fix: {エラー概要}"
   })
4. 新しいタグ push または workflow_dispatch で CI を再トリガー:
   github_push({
     work_dir: "{work_dir}",
     repo_name: "{repo_name}",
     repo_owner: "{owner}",
     commit_message: "",
     tag: "v0.1.1"
   })
5. 新しい run_id を取得して polling ループに再突入
```

再トリガー方法の判断:

| 状況 | 方法 |
| --- | --- |
| コード修正あり（package.json / ソース変更） | 新タグ push（バージョン bump）が確実 |
| workflow yml のみ修正 | `workflow_dispatch` で即座に再実行可能 |
| 一時的な CI 環境エラー（ネットワーク等） | GitHub Actions ページで "Re-run failed jobs" |

---

## エラー時の挙動まとめ

| 事象 | `status` | 対応 |
| --- | --- | --- |
| 全ジョブ成功 + Release 確認済み | `success` | `download_urls` を返す |
| 一部ジョブ失敗 | `failure` | 失敗ジョブのログを取得、`failure_info` で返す。修正→再 push を案内 |
| 全ジョブ失敗 | `failure` | 設定エラーの可能性を報告、全ログ URL を提示 |
| polling タイムアウト | `timeout` | 現在のステータスを報告、手動再実行を案内 |
| Release 未作成（ビルド成功後） | `failure` | `--publish always` と `GH_TOKEN` の設定確認を案内 |
| API アクセスエラー（401 / 403） | `failure` | PAT の権限・有効期限を確認、`setup-deploy-environment` を案内 |

---

## 注意事項

- **polling 間隔**: 15 秒。GitHub Actions API のレートリミット（認証済みで 5000 req/h）
  に対して十分余裕がある。15 分の監視で最大 60 回のリクエスト。
- **並行ビルド**: matrix strategy で各 OS のビルドが並行実行される。全ジョブの完了を
  待ってから Release asset を確認する。
- **Release のドラフト**: electron-builder は `--publish always` の場合、自動的に
  GitHub Release を作成する。最初のジョブが Release を作成し、後続のジョブが asset を
  追加する形になるため、全ジョブ完了前に Release が存在しても asset が不完全な場合がある。
  全ジョブ完了後に asset の完全性を検証する。
- **Vercel との違い**: Vercel のデプロイ監視は `vercel_get_deployment_status` ツールで
  行う（polling 間隔やステータス体系が異なる）。本スキルは GitHub Actions 専用。

---

## 関連スキル

| スキル | 関係 |
| --- | --- |
| `electron-scaffold-and-build` | 本スキルを Step 5 で呼ぶ |
| `create-app` | オーケストレータ。Phase 4-D から間接的に本スキルを使用 |
| `update-deploy` | 既存デスクトップアプリの更新時、再ビルド後の監視に使用 |
| `vercel-connect-and-deploy` | Vercel パスのデプロイ（本スキルとは別の監視系統） |
