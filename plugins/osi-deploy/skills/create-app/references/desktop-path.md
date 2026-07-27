# Desktop Path リファレンス（Phase 4-D）

> Electron アプリをビルド・配布するための実行パス。
> 既存の atomic スキル `electron-scaffold-and-build` と `desktop-release-monitor` を使う。

---

## 1. Phase 4-D 実行手順

create-app の Phase 0-3 でアプリ定義（エンティティ・ロール・機能要件・技術選定）が確定した後、
Phase 4-D では以下の順序で Desktop アプリを構築・配布する。

### Step 1: scaffold 生成

Electron Forge + React + TypeScript のテンプレートを生成する。

```
テンプレート構成:
├── src/
│   ├── main.ts          # メインプロセス（BrowserWindow 生成、IPC ハンドラ）
│   ├── preload.ts       # contextBridge による安全な API 公開
│   └── renderer/        # React アプリ（Phase 2-3 で設計した UI）
│       ├── App.tsx
│       ├── index.tsx
│       └── components/
├── forge.config.ts       # Electron Forge 設定（maker/publisher）
├── package.json
├── tsconfig.json
└── webpack.main.config.ts
```

- `npx create-electron-app <PROJECT_NAME> --template=webpack-typescript` をベースに、React を追加する
- Phase 2 で設計したエンティティ・画面を `src/renderer/` に反映する

### Step 2: gh-create-repo-and-push（共通 atomic）

`osi-deploy:gh-create-repo-and-push` を呼び出す。

- `USE_ORG` 設定に従い、個人リポジトリまたは組織リポジトリに作成する
- リポジトリ名は `PROJECT_NAME`（ケバブケース）
- `.gitignore` に `out/`（ビルド成果物）を含める

### Step 3: harness-init（共通 atomic）

`osi-deploy:harness-init` を呼び出す。

- README.md、LICENSE、CONTRIBUTING.md を生成する
- CI の基盤（lint + test）を `.github/workflows/ci.yml` に設定する

### Step 4: electron-scaffold-and-build を呼ぶ

`electron-scaffold-and-build` atomic スキルを呼び出す。

- Electron Forge の設定を検証する
- `npm run make` でローカルビルドを実行する
- ビルド成果物を確認する:
  - macOS: `.dmg`（`out/make/` 配下）
  - Windows: `.exe`（Squirrel.Windows installer）
  - Linux: `.AppImage` または `.deb`

### Step 5: GitHub Actions ワークフロー設定

`.github/workflows/release.yml` を生成する。

```yaml
# リリースワークフローの骨格
name: Release
on:
  push:
    tags: ['v*']
jobs:
  build:
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run make
      - uses: actions/upload-artifact@v4
        with:
          name: release-${{ matrix.os }}
          path: out/make/**/*
```

- タグ push（`v*`）をトリガーにビルドを実行する
- 3 プラットフォーム（macOS / Windows / Linux）の成果物を GitHub Release にアップロードする

### Step 6: desktop-release-monitor を呼ぶ

`desktop-release-monitor` atomic スキルを呼び出す。

- GitHub Actions のリリースワークフローの実行状態を監視する
- ビルド成功時: GitHub Release にアセットがアップロードされたことを確認する
- ビルド失敗時: エラーログを取得して報告する

---

## 2. DB 選択: SQLite vs Supabase

| 観点 | SQLite（ローカル） | Supabase（クラウド同期） |
|------|-------------------|------------------------|
| 用途 | オフライン完結、個人利用 | 複数端末同期、チーム利用 |
| セットアップ | `better-sqlite3` を依存に追加 | Supabase プロジェクト作成 + `@supabase/supabase-js` |
| データ保存先 | `app.getPath('userData')` 配下 | Supabase PostgreSQL |
| オフライン対応 | 常時利用可 | オフライン時はローカルキャッシュが必要 |
| マイグレーション | `better-sqlite3-migrations` | Supabase CLI (`supabase db push`) |
| 推奨ケース | 単一ユーザーの個人ツール | 認証・マルチユーザー・リアルタイム同期が必要な場合 |

### 判断基準

- 「ログインなしで使いたい」「オフラインで使う」→ **SQLite**
- 「チームで使う」「データを共有する」「認証が必要」→ **Supabase**
- 両方必要（オフライン + 同期）→ SQLite をローカルキャッシュ、Supabase を正本として併用

---

## 3. IPC 通信の定型コード（contextBridge）

Electron のセキュリティモデルに従い、メインプロセスとレンダラープロセスの通信には
`contextBridge` を使用する。`nodeIntegration: true` は使わない。

### preload.ts

```typescript
import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('api', {
  // データの読み取り（invoke パターン: リクエスト→レスポンス）
  getData: (query: string) => ipcRenderer.invoke('get-data', query),

  // データの書き込み
  saveData: (data: unknown) => ipcRenderer.invoke('save-data', data),

  // メインプロセスからの通知を受け取る（on パターン: 一方向）
  onNotify: (callback: (message: string) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, message: string) => callback(message);
    ipcRenderer.on('notify', handler);
    return () => ipcRenderer.removeListener('notify', handler);
  },
});
```

### main.ts（ハンドラ登録）

```typescript
import { ipcMain } from 'electron';

ipcMain.handle('get-data', async (_event, query: string) => {
  // DB からデータを取得して返す
  return await db.query(query);
});

ipcMain.handle('save-data', async (_event, data: unknown) => {
  // DB にデータを保存する
  return await db.save(data);
});
```

### renderer 側（React コンポーネントでの利用）

```typescript
// window.api は preload.ts で公開した API
const data = await window.api.getData('SELECT * FROM items');
await window.api.saveData({ name: 'test', value: 42 });
```

### 型定義（src/types/electron.d.ts）

```typescript
interface ElectronAPI {
  getData: (query: string) => Promise<unknown>;
  saveData: (data: unknown) => Promise<void>;
  onNotify: (callback: (message: string) => void) => () => void;
}

declare global {
  interface Window {
    api: ElectronAPI;
  }
}
```

---

## 4. コード署名（任意）

配布するアプリにコード署名を行うことで、OS のセキュリティ警告を回避できる。
**必須ではないが、社外配布する場合は強く推奨する。**

### macOS: codesign + notarize

- Apple Developer Program への加入が必要（年額 $99）
- Electron Forge の `@electron-forge/maker-dmg` + `@electron-forge/plugin-auto-unpack-natives` で設定
- 環境変数:
  - `APPLE_ID`: Apple ID メールアドレス
  - `APPLE_ID_PASSWORD`: アプリ固有パスワード
  - `APPLE_TEAM_ID`: チーム ID
- `forge.config.ts` の `packagerConfig` に `osxSign` と `osxNotarize` を追加する

### Windows: signtool

- EV コード署名証明書が必要（DigiCert、GlobalSign 等）
- Electron Forge の `@electron-forge/maker-squirrel` で設定
- `certificateFile` と `certificatePassword` を環境変数で渡す

### CI での署名

- GitHub Secrets にコード署名の秘密鍵・証明書を格納する
- `release.yml` の各 OS ジョブで署名ステップを追加する

---

## 5. auto-update（任意）

`electron-updater` を使い、GitHub Release からの自動更新を実装できる。

### セットアップ

```bash
npm install electron-updater
```

### main.ts に追加

```typescript
import { autoUpdater } from 'electron-updater';

app.whenReady().then(() => {
  // 起動時に更新チェック
  autoUpdater.checkForUpdatesAndNotify();
});

autoUpdater.on('update-available', () => {
  // 更新があることをユーザーに通知
});

autoUpdater.on('update-downloaded', () => {
  // ダウンロード完了後、再起動を促す
  autoUpdater.quitAndInstall();
});
```

### 前提条件

- GitHub Release にビルド成果物がアップロードされていること
- `package.json` の `publish` 設定で GitHub を指定すること
- コード署名済みであること（macOS の場合、未署名アプリは auto-update が動作しない）

---

## 6. 完了レポートテンプレ

Phase 4-D 完了時に以下のレポートを生成する。

```
## Desktop アプリ完了レポート

### 基本情報
- アプリ名: {PROJECT_NAME}
- リポジトリ: {REPO_URL}
- フレームワーク: Electron Forge + React + TypeScript

### ビルド成果物
- macOS: {.dmg ファイルパス or "未ビルド"}
- Windows: {.exe ファイルパス or "未ビルド"}
- Linux: {.AppImage ファイルパス or "未ビルド"}

### DB
- 種類: {SQLite / Supabase}
- 接続先: {ファイルパス / Supabase URL}

### CI/CD
- GitHub Actions: {release.yml のステータス}
- コード署名: {設定済み / 未設定}
- auto-update: {設定済み / 未設定}

### 次のステップ
- [ ] 動作確認（各 OS でインストール・起動）
- [ ] コード署名の設定（社外配布する場合）
- [ ] auto-update の設定（継続的な更新が必要な場合）
```

---

## 7. 将来の Tauri 対応

現時点では Electron を使用するが、将来的に Tauri への移行パスも視野に入れる。

### Tauri の利点

- バイナリサイズが小さい（Electron: ~150MB → Tauri: ~10MB）
- メモリ使用量が少ない（Chromium を内蔵しないため）
- Rust バックエンドによる高速な処理

### 移行の前提条件

- Tauri 2.0 の安定リリースと iOS/Android サポートの成熟
- `osi-deploy` プラグインに `tauri-scaffold-and-build` スキルが追加されること
- React + TypeScript のフロントエンドはそのまま流用可能（レンダラー部分は共通）

### 移行時の変更点

- メインプロセス: TypeScript → Rust（`src-tauri/src/main.rs`）
- IPC: `contextBridge` → Tauri の `invoke` コマンド
- ビルド: Electron Forge → `tauri build`
- DB: `better-sqlite3` → `rusqlite`（SQLite の場合）

### 判断基準

- バイナリサイズ・パフォーマンスが重要 → Tauri を検討する
- npm エコシステムへの依存が大きい → Electron を継続する
- 現時点では Electron で構築し、Tauri スキルが整備された段階で移行を判断する
