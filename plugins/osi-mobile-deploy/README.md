# osi-mobile-deploy

AI OSI URI のネイティブモバイルアプリ（iOS / Android）作成〜配信自動化。「モバイルアプリ作って」の一言で、SwiftUI + Jetpack Compose の Golden Template から新規リポを起こし、Firebase プロビジョニング・アイコン生成・GitHub Secrets 投入・CI 自動修正ループを回し、TestFlight / Google Play Internal Track まで到達させる。

`osi-deploy`（Web / SaaS デプロイ）と対を成す、モバイル配信専用プラグイン。

## スキル一覧

- `deploy-mobile-app` — 唯一のオーケストレータ。「モバイルアプリ作って」で発動し、ヒアリング → scaffold → Firebase → Secrets → push → CI 監視 → TestFlight / Play Internal Track 到達まで一気通貫。
- `mobile-app-scaffold` — Golden Template（SwiftUI + Compose）から新規リポを clone → 6箇所置換 → GitHub push。
- `mobile-firebase-setup` — Firebase プロジェクト作成 + iOS / Android App 追加 + `GoogleService-Info.plist` / `google-services.json` 取得 → base64 化 → GitHub Secrets 投入。
- `mobile-secrets-sync` — GitHub リポに TestFlight / Play 配信に必要な Secrets 10個を投入（App Store Connect API Key / P12 証明書 / Keystore / Service Account JSON など）。
- `mobile-icon-generator` — 1枚の 1024x1024 PNG から iOS AppIcon / Android mipmap 全 density を一括生成。ソース画像が無ければ nano-banana で生成。
- `mobile-crash-triage` — TestFlight / Play Internal Track のクラッシュを取得 → シンボリケート → known-crash-patterns.md と照合 → 修正提案を出す（自動修正はしない）。
- `mobile-update-deploy` — 既存モバイルリポの局所修正 → push → CI 監視 → TestFlight 到達確認。Web版 `update-deploy` のモバイル相当。
- `mobile-app-smoke-test` — 生成された IPA / AAB を Simulator / Emulator で起動確認。5秒待ってクラッシュを検知したら crash-triage を呼ぶ。
- `ios-testflight-deploy` — fastlane + altool で TestFlight にアップロード。SwiftSupport 保全・actool 自前コンパイル・AuthKey 命名など今日獲得したノウハウ全部入り。
- `android-play-deploy` — Gradle + bundletool + Play Publisher API で Internal Track にアップロード。track: internal → 昇格は `android_promote` MCP で。

## 前提

- Cowork または Claude Desktop に `AI OSI URI Deploy` MCP 拡張が導入済み。以下のツールを提供:
  - `ios_get_status`, `ios_get_reviews`, `ios_submit_review`, `ios_xcode_cloud_trigger`
  - `android_get_status`, `android_get_reviews`, `android_promote`, `android_upload_status`
  - `xcode_cloud_list_products`, `xcode_cloud_list_workflows`, `xcode_cloud_create_workflow`
  - `firebase_*`（19個: プロジェクト作成 / iOS/Android app 追加 / plist取得 / Firestore / Auth）
  - `github_*`, `gcp_api`, `bq_query`
- macOS Keychain に以下の secrets が格納済み（初回のみユーザーが登録）:
  - iOS: `APPLE_TEAM_ID`, `APP_STORE_CONNECT_API_KEY_ID`, `APP_STORE_CONNECT_API_KEY_ISSUER_ID`, `APP_STORE_CONNECT_API_KEY_B64`, `IOS_DIST_CERT_P12_B64`, `IOS_DIST_CERT_PASSWORD`, `IOS_KEYCHAIN_PASSWORD`
  - Android: `ANDROID_KEYSTORE_B64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`, `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`
- ローカル環境: Xcode 26+（iOS 26 SDK）, fastlane, xcodegen, Android Studio / SDK, JDK 17+.

## 使い方

Cowork で:

```
モバイルアプリ作って。名前は Foo、メモを記録するだけの Hello World、iOS と Android 両方
```

とだけ言うと、以下が自動で回る:

1. アプリ情報のヒアリング（Bundle ID / GitHub Org 等）
2. Golden Template から新規リポ生成 → GitHub push
3. Firebase プロジェクト新規作成 + iOS/Android App 追加 + plist取得
4. GitHub Secrets 10個を投入
5. CI 起動を検知 → iOS/Android の両ワークフローを監視
6. CI 失敗したら `ci-failure-patterns.md` と照合 → 既知パターンなら auto-fix push（最大3回）
7. 両方 green → Simulator / Emulator でスモークテスト
8. TestFlight リンク + Play Internal Track リンクをユーザーに提示

## 関連プラグイン

- `osi-deploy` — Web / SaaS 側の対応プラグイン
- `osi-sales/proposal-package` — 提案書パッケージ（モバイルアプリを見積もりに含める案件で参照）
