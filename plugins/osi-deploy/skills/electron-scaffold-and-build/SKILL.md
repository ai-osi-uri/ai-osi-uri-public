---
name: electron-scaffold-and-build
description: |
  Electron の scaffold 生成 + electron-builder 設定注入 + GitHub Actions の matrix
  ビルド workflow 同梱 + push + CI 監視までを行う。`create-app` の Phase 4-D
  から呼ばれる。単体では「Electron アプリの scaffold を作って Actions でビルド」
  で発動。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# Electron scaffold + electron-builder + GitHub Actions CI（atomic）

Electron + React の scaffold を生成し、electron-builder 設定と GitHub Actions の
matrix ビルド workflow を同梱して GitHub に push、タグで CI をトリガーし、
`desktop-release-monitor` でビルド完了まで監視する。**Windows / Mac / Linux の
インストーラを GitHub Releases に自動公開するところまでが本スキルの責務**。

認証情報は AI OSI URI Deploy 拡張が保持する GitHub PAT を使う。`.env` は読まない。

---

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| AI OSI URI Deploy 拡張が有効・GitHub PAT 入力済み | `health_check` で `github.valid: true` | `setup-deploy-environment` を案内 |
| PAT に `repo` + `workflow` スコープあり | Classic PAT で発行 | Fine-grained だと Actions 権限不足の可能性。Classic 推奨 |
| Node.js 18+ がローカルにある | `node -v` | npm install バリデーションをスキップ（CI 側で検証） |

---

## 入力契約

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `PROJECT_NAME` | ✅ | 表示名（例: `Flower Inventory`）。electron-builder の `productName` に使う |
| `PROJECT_NAME_LOWER` | ✅ | kebab-case 名（例: `flower-inventory`）。リポ名・appId に使う |
| `PROJECT_DESCRIPTION` | 任意 | package.json の description（デフォルト: `PROJECT_NAME`） |
| `target_platforms` | 任意 | `["win", "mac", "linux"]` のサブセット。デフォルト `["win", "mac"]` |
| `signing_config` | 任意 | `{ mac: bool, win: bool }` または `null`。証明書署名の有無。`null` = 署名なし（開発配布） |
| `auto_update` | 任意 | `true` / `false`。デフォルト `true`。electron-updater による自動更新機能 |
| `USE_ORG` | 任意 | deploy-app の org 判定結果。真=`ai-osi-uri`、偽=個人。未指定時は個人（安全側） |

---

## scaffold 構造

```
{PROJECT_NAME_LOWER}/
├── package.json
├── electron-builder.yml
├── tsconfig.json
├── src/
│   ├── main/
│   │   ├── index.ts          # BrowserWindow 生成、app ライフサイクル
│   │   ├── preload.ts        # contextBridge による IPC 公開
│   │   └── ipc-handlers.ts   # ファイル操作、ネイティブ API ラッパー
│   └── renderer/
│       ├── index.html
│       ├── index.tsx          # React エントリ
│       ├── App.tsx
│       └── components/
├── .github/
│   └── workflows/
│       └── build-and-release.yml
├── CLAUDE.md
└── DEPLOY.md
```

---

## package.json テンプレート

```json
{
  "name": "{PROJECT_NAME_LOWER}",
  "version": "0.1.0",
  "description": "{PROJECT_DESCRIPTION}",
  "main": "dist/main/index.js",
  "scripts": {
    "start": "electron .",
    "dev": "tsc && electron .",
    "build": "tsc && electron-builder",
    "build:win": "tsc && electron-builder --win",
    "build:mac": "tsc && electron-builder --mac",
    "build:linux": "tsc && electron-builder --linux"
  },
  "devDependencies": {
    "electron": "^33.0.0",
    "electron-builder": "^25.1.0",
    "typescript": "^5.6.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  }
}
```

`auto_update` が `true` の場合、`dependencies` に以下を追加:

```json
"electron-updater": "^6.3.0"
```

---

## electron-builder.yml テンプレート

```yaml
appId: com.aiosiuri.{PROJECT_NAME_LOWER}
productName: "{PROJECT_NAME}"
copyright: "Copyright (c) AI OSI URI"

directories:
  output: release
  buildResources: build

asar: true

publish:
  provider: github
  owner: "{USE_ORG が真なら ai-osi-uri、偽なら GitHub ユーザー名}"

win:
  target:
    - target: nsis
      arch:
        - x64
  icon: build/icon.ico

nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
  installerIcon: build/icon.ico
  uninstallerIcon: build/icon.ico

mac:
  target:
    - target: dmg
      arch:
        - x64
        - arm64
  category: public.app-category.business
  icon: build/icon.icns

linux:
  target:
    - target: AppImage
      arch:
        - x64
  icon: build/icon.png
  category: Office
```

`target_platforms` に含まれないプラットフォームのセクションは生成しない。

### 署名設定（signing_config が指定されている場合）

**Mac コード署名**: `mac` セクションに以下を追加:

```yaml
mac:
  identity: null  # CI 環境で CSC_LINK / CSC_KEY_PASSWORD 環境変数から自動取得
  hardenedRuntime: true
  gatekeeperAssess: false
  entitlements: build/entitlements.mac.plist
  entitlementsInherit: build/entitlements.mac.plist
```

**Windows コード署名**: `win` セクションに以下を追加:

```yaml
win:
  signingHashAlgorithms:
    - sha256
  # 証明書は CI の環境変数 CSC_LINK / CSC_KEY_PASSWORD で注入
```

---

## GitHub Actions workflow テンプレート（build-and-release.yml）

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          # target_platforms に応じて含めるエントリを制御
          - os: windows-latest
            platform: win
          - os: macos-latest
            platform: mac
          - os: ubuntu-latest
            platform: linux
    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build Electron app
        run: npx electron-builder --${{ matrix.platform }} --publish always
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 署名あり（signing_config に応じた条件付き env）

Mac 署名が有効な場合、`Build Electron app` ステップに以下の env を追加:

```yaml
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CSC_LINK: ${{ secrets.MAC_CERTS }}
          CSC_KEY_PASSWORD: ${{ secrets.MAC_CERTS_PASSWORD }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
```

Windows 署名が有効な場合:

```yaml
          CSC_LINK: ${{ secrets.WIN_CERTS }}
          CSC_KEY_PASSWORD: ${{ secrets.WIN_CERTS_PASSWORD }}
```

`target_platforms` に含まれないプラットフォームの matrix エントリは生成しない。

---

## 自動更新設定（auto_update = true の場合）

`src/main/index.ts` に以下の更新チェックコードを注入:

```typescript
import { autoUpdater } from 'electron-updater';
import log from 'electron-log';

autoUpdater.logger = log;
autoUpdater.logger.transports.file.level = 'info';

app.whenReady().then(() => {
  // ... BrowserWindow 生成の後
  autoUpdater.checkForUpdatesAndNotify();
});

autoUpdater.on('update-available', () => {
  log.info('Update available');
});

autoUpdater.on('update-downloaded', () => {
  log.info('Update downloaded — will install on quit');
});
```

electron-builder.yml の `publish` セクションにより、GitHub Releases から自動更新
フィードが提供される。新しいタグ（`v0.2.0` 等）を push すると CI がビルドして
Release に公開し、既存ユーザーのアプリが次回起動時に自動更新を検出する。

---

## 実行ステップ

### Step 1: scaffold 生成

`{OUTPUTS}/{PROJECT_NAME_LOWER}/` に上記テンプレートからファイル群を生成する。
`target_platforms` / `signing_config` / `auto_update` に応じてテンプレートを分岐。

- アイコンファイル（`build/icon.ico` / `.icns` / `.png`）はプレースホルダを配置。
  デザインがある場合は後から差し替え。
- `CLAUDE.md` にはプロジェクト概要・ビルドコマンド・ディレクトリ構成を記載。
- `DEPLOY.md` にはリリース手順（タグ push → CI → GitHub Releases）を記載。

### Step 2: 依存バリデーション

ローカルに Node.js がある場合、sandbox で `npm install` を実行して依存の互換性を
検証する。ない場合はスキップ（CI 側で検証）。

```bash
cd {OUTPUTS}/{PROJECT_NAME_LOWER}
npm install --ignore-scripts
```

### Step 3: GitHub push

`gh-create-repo-and-push` を呼ぶ:

```
github_create_repo_and_push({
  input_dir: "{OUTPUTS}/{PROJECT_NAME_LOWER}",
  repo_name: "{PROJECT_NAME_LOWER}",
  is_private: true,
  commit_message: "Initial scaffold: Electron + electron-builder + GitHub Actions",
  owner_override: "{USE_ORG が真なら ai-osi-uri、偽なら personal}"
})
```

### Step 4: タグ push で CI トリガー

push 完了後、v0.1.0 タグを作成して push する:

```
github_push({
  work_dir: "{戻りの work_dir}",
  repo_name: "{PROJECT_NAME_LOWER}",
  repo_owner: "{owner}",
  commit_message: "",
  tag: "v0.1.0"
})
```

タグ push により GitHub Actions の `build-and-release.yml` がトリガーされる。

### Step 5: CI 監視

`desktop-release-monitor` を呼んでビルド完了を待つ:

```
desktop-release-monitor({
  repo: "{owner}/{PROJECT_NAME_LOWER}",
  run_id: "latest",
  expected_platforms: target_platforms,
  timeout_minutes: 15
})
```

### Step 6: 完了報告

`desktop-release-monitor` の戻り値から以下を収集して返す:

| 戻り値 | 説明 |
| --- | --- |
| `REPO_URL` | GitHub リポジトリ URL |
| `RELEASE_URL` | GitHub Releases ページ URL |
| `DOWNLOAD_URLS` | `{ win?: string, mac?: string, linux?: string }` — 各 OS のインストーラ URL |

---

## エラー時の挙動

| 事象 | 対応 |
| --- | --- |
| scaffold 生成失敗（テンプレート不整合） | Electron 公式テンプレート（`electron/electron-quick-start`）にフォールバックし、electron-builder.yml と workflow を手動追加 |
| npm install 失敗（依存の互換性エラー） | エラーメッセージを提示し、バージョン制約の修正を案内。`--legacy-peer-deps` が有効な場合は自動適用 |
| push 失敗（PAT 権限不足 / Org 問題） | `health_check` で PAT 状態を確認し、`setup-deploy-environment` を案内 |
| CI ビルド失敗 | `desktop-release-monitor` がビルドログを取得 → エラー原因を特定 → scaffold を修正 → `github_push` で再 push → 新タグまたは `workflow_dispatch` で再トリガー → 再監視。最大 3 回 |
| CI タイムアウト（15 分超） | `desktop-release-monitor` が現在のステータスを報告し、`workflow_dispatch` での再実行を案内 |

### よくある CI ビルドエラーと対処

| エラー | 原因 | 修正 |
| --- | --- | --- |
| `electron-builder: command not found` | devDependencies に未記載 | package.json に `electron-builder` を追加 |
| `Error: Cannot find module 'electron'` | npm ci でインストール失敗 | `package-lock.json` の再生成（`npm install` → commit → push） |
| `Code signing failed` | 証明書 secret 未設定 | signing_config を `null` に変更、または Secrets 設定を案内 |
| `Error: ENOENT icon` | アイコンファイル未配置 | プレースホルダアイコンを `build/` に生成 |
| `notarization failed` | Apple 公証設定不備 | `mac.notarize: false` で一時回避、設定修正後に再ビルド |

---

## 注意事項

- **署名なし配布の警告**: `signing_config` が `null` の場合、Windows では SmartScreen
  警告、Mac では Gatekeeper 警告が出る。社内テスト配布では問題ないが、外部配布時は
  `setup-deploy-environment` でコード署名証明書を登録してから再ビルドする。
- **Electron のメジャーバージョン**: テンプレートは Electron 33 系を使用。Chromium の
  セキュリティ更新に追随するため、定期的なバージョン更新が必要。
- **asar パッケージ**: `asar: true` でソースを圧縮アーカイブに格納。`node_modules` の
  ネイティブモジュールは自動的に除外される（electron-builder が処理）。
- **GitHub Releases の容量制限**: 1 リリースあたり 2 GB まで。NSIS インストーラは
  通常 80-150 MB、DMG は 100-200 MB 程度。

---

## 関連スキル

| スキル | 関係 |
| --- | --- |
| `create-app` | オーケストレータ。Phase 4-D で本スキルを呼ぶ |
| `gh-create-repo-and-push` | GitHub push（Step 3 で使用） |
| `desktop-release-monitor` | CI 監視（Step 5 で使用） |
| `update-deploy` | 初回デプロイ後のコード更新 → 再ビルド・リリース |
| `setup-deploy-environment` | 証明書・PAT の登録 |
