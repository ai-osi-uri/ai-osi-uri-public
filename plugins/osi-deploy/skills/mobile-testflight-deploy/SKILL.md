---
name: mobile-testflight-deploy
description: |
  iOS アプリを Fastlane 経由で TestFlight に配信するスキル。
  「TestFlight にアップロードして」「iOS を配信」「ベータ配信して」など、
  ローカル Mac で iOS アプリをビルド → App Store Connect に upload するリクエストで発動する。
  前提: Mac に Xcode 16+ / Fastlane / xcodegen がインストールされていること、
  macOS Keychain に osi-mobile-deploy.* シリーズの secrets（App Store Connect API Key
  ID/Issuer ID/.p8 のパス、Apple Team ID）が格納されていること。
  osi-deploy プラグインの他スキル（deploy-app, aws-static-deploy）と対を成す、
  モバイル配信レーン専用の手順書。
version: 0.1.0
requires:
  - fastlane
  - xcodegen
  - xcode >= 16.0
---

# mobile-testflight-deploy

## 目的
リポジトリ内の Fastlane `ios_beta_auto` レーンを叩いて **iOS アプリを TestFlight に配信**する。Xcode Automatic Signing を使うため、`fastlane match` の証明書用 private git repo は不要。

## 前提

### Mac 側
- Xcode 16 以上（`xcodebuild -version` で確認）
- Homebrew の Ruby 3.x（`ruby -v` → 3.x 系）
- `brew install fastlane xcodegen`
- リポジトリに Fastfile の `ios_beta_auto` レーンが実装済み

### Keychain 側（osi-mobile-deploy 準拠キー名）
以下 4 つが `security find-generic-password` で取得できること:

| service 名 | 値 |
|---|---|
| `osi-mobile-deploy.app-store-connect-key-id` | App Store Connect API Key ID (例: `79L9K48XS6`) |
| `osi-mobile-deploy.app-store-connect-issuer-id` | Issuer ID (UUID) |
| `osi-mobile-deploy.app-store-connect-key-path` | `.p8` ファイルの絶対パス |
| `osi-mobile-deploy.apple-team-id` | Apple Team ID (例: `958VNCR6BK`) |

未登録の場合はユーザに以下を案内すること:
```
security add-generic-password -U -s "osi-mobile-deploy.<key>" -a "$USER" -w "<value>"
```

### App Store Connect 側
- 対象 Bundle ID の App ID が Apple Developer Portal に登録済み
- App Store Connect にアプリレコード作成済み（`https://appstoreconnect.apple.com/apps` に表示される）

## 実行手順

### Step 1: 環境変数展開（Keychain → shell）
```bash
export APP_STORE_CONNECT_API_KEY_ID="$(security find-generic-password -s osi-mobile-deploy.app-store-connect-key-id -a "$USER" -w)"
export APP_STORE_CONNECT_API_KEY_ISSUER_ID="$(security find-generic-password -s osi-mobile-deploy.app-store-connect-issuer-id -a "$USER" -w)"
export APP_STORE_CONNECT_API_KEY_PATH="$(security find-generic-password -s osi-mobile-deploy.app-store-connect-key-path -a "$USER" -w)"
export APPLE_TEAM_ID="$(security find-generic-password -s osi-mobile-deploy.apple-team-id -a "$USER" -w)"
```

いずれかが空だったら **halt & ask** — Keychain 登録漏れをユーザに伝える。

### Step 2: リポ最新化
```bash
cd <REPO_ROOT>
git pull --ff-only origin main
bundle install --quiet
```

`bundle install` が Ruby バージョンエラーなら:
```
brew install ruby
echo 'export PATH="/opt/homebrew/opt/ruby/bin:$PATH"' >> ~/.zshrc
export PATH="/opt/homebrew/opt/ruby/bin:$PATH"
```

### Step 3: TestFlight 配信レーン実行
```bash
bundle exec fastlane ios ios_beta_auto flavor:<dev|stg|prod>
```

このレーンは順に:
1. `xcodegen generate` → .xcodeproj 再生成
2. `latest_testflight_build_number` → 次ビルド番号取得
3. `increment_build_number` → CFBundleVersion 更新
4. `gym` → Release-<Flavor> configuration で archive + export (自動署名)
5. `pilot` → TestFlight upload (処理待ちはスキップ)

**所要時間**: 初回 SPM 解決 10〜15 分、以降は 3〜5 分。

### Step 4: アップロード確認
```bash
bundle exec fastlane ios ios_get_status flavor:<dev|stg|prod>
```

または App Store Connect の TestFlight タブで新ビルドが「処理中 (Processing)」表示されていれば成功。処理完了まで通常 10〜30 分。

## エラーハンドリング

### `Unable to find Xcode project`
Fastfile のパスが相対パスの場合、`Dir.chdir` ブロック外では解決できない。`IOS_PROJECT_ABS` (絶対パス) を使う実装に更新すること。

### `Signing for "MustPost" requires a development team`
xcconfig の `DEVELOPMENT_TEAM` が未設定 or 誤 team。以下で確認:
```bash
grep -r DEVELOPMENT_TEAM apps/ios/MustPost/Config/
```

### `Could not find a build upload for any version on ios platform`
初回配信では正常な情報メッセージ。`initial_build_number: 0` を使う。

### `No profiles for '...' were found`
`-allowProvisioningUpdates` フラグが gym に渡っていない、または App ID が Apple Developer Portal に未登録。以下を確認:
- Fastfile の `gym` に `xcargs: "-allowProvisioningUpdates ..."` が入っているか
- https://developer.apple.com/account/resources/identifiers/list に対象 Bundle ID があるか

### Firebase plist 不在で起動時クラッシュ (実行時)
配信自体は成功するが、実機起動時にクラッシュする場合は `apps/ios/MustPost/Resources/GoogleService-Info-<Flavor>.plist` を配置する。開発中は `.plist.sample` の複製で仮起動可能。

## 関連スキル
- `deploy-app` — Web アプリ（Vercel/AWS）の初回セットアップ
- `update-deploy` — Web アプリの更新デプロイ
- `app-smoke-test` — デプロイ後の HTTP スモークテスト
- （将来）`mobile-play-internal-deploy` — Android AAB を Play Console Internal に配信

## 参考
- Fastlane `ios_beta_auto` レーン: `<REPO>/fastlane/Fastfile`
- `osi-mobile-deploy` MCP（並行使用可能な TypeScript 実装）: `<REPO>/mcp/osi-mobile-deploy/`
