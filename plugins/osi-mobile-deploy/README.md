# osi-mobile-deploy

AI OSI URI のネイティブモバイルアプリ（iOS / Android）作成〜配信自動化。「モバイルアプリ作って」の一言で、SwiftUI + Jetpack Compose の Golden Template から新規リポを起こし、Firebase プロビジョニング・アイコン生成・GitHub Secrets 投入・CI 自動修正ループを回し、TestFlight / Google Play Internal Track まで到達させる。

`osi-deploy`（Web / SaaS デプロイ）と対を成す、モバイル配信専用プラグイン。

## Changelog

### v0.3.0 — MustPost SwiftUI 移植のノウハウ追加（2026-07）

MustPost（Flutter → SwiftUI ネイティブ化）で獲得した実運用ノウハウを 5 スキルで追加。既存スキルとの重複は避け、実際にハマった問題単位で切り出している。

- **`ios-sim-auth-backdoor`** — iOS Simulator で Firebase Auth の keychain 永続化を成立させる proper signing 既定（拡張 v1.18.5+ で `xcode_build_for_sim({code_signing: "auto"})` が既定に）と、`mustpost://debug/signin?token=XXX` の Custom Token deep link バックドア（AppDelegate と SwiftUI 側 DeepLinkHandler の両方に置くのがミソ）
- **`flutter-swift-parity-port`** — Flutter → SwiftUI 移植を「感覚で似せる」ではなく inventory → diff → 優先度バッチ → build + 目視 → コミット の 5 フェーズで systematic に回す。日本語ラベル逐語コピー、iOS ネイティブに寄せてよい逸脱ポリシー、Dart→SwiftUI 写像早見表を同梱
- **`apiv2-callable-iam-gotchas`** — Cloud Functions v2（Cloud Run 実装）の apiv2-* が client から `UNAUTHENTICATED` / `communication error` になる 2 大原因（allUsers → roles/run.invoker の一括付与忘れ + JSONEncoder の snake_case 変換）を潰す
- **`firestore-bulk-index-sync`** — `firebase deploy --only firestore:indexes` が 50+ index で詰まる問題を、Admin REST 直叩き（`collectionGroups/{cg}/indexes` POST）+ 409 と 400「not necessary」を成功に丸めて冪等化
- **`xcodegen-project-regen`** — `git pull` 後の「Missing package product 'FirebaseCore'」× 14 個症状を `xcodegen generate --spec apps/ios/project.yml` + Reset/Resolve Packages で 30 秒修復
- **`ios-testflight-deploy` v0.2.0** — MustPost 実運用中の `.github/workflows/ios-release-auto.yml` 完全版を `references/ios-release-auto.yml.example` に同梱（macos-15 + Xcode 26.x + P12 一時 keychain + auto-signing + flavor 3 種）

### v0.2.0 — 初版（10 スキル）

deploy-mobile-app オーケストレータ + 9 atomic を用意。

## スキル一覧

**オーケストレータ**:
- `deploy-mobile-app` — 「モバイルアプリ作って」で発動する新規作成の唯一の入口。ヒアリング → scaffold → Firebase → Secrets → push → CI 監視 → TestFlight / Play Internal Track 到達まで一気通貫。

**atomic（新規作成）**:
- `mobile-app-scaffold` — Golden Template（SwiftUI + Compose）から新規リポを clone → 6箇所置換 → GitHub push。
- `mobile-firebase-setup` — Firebase プロジェクト作成 + iOS/Android App 追加 + plist/json 取得 → base64 化 → GitHub Secrets 一括投入。
- `mobile-secrets-sync` — GitHub リポに TestFlight / Play 配信に必要な Secrets 10 個を投入。
- `mobile-icon-generator` — 1 枚の 1024x1024 PNG から iOS AppIcon / Android mipmap 全 density を一括生成。ソース画像が無ければ nano-banana で生成。

**atomic（既存の更新・トリアージ）**:
- `mobile-update-deploy` — 既存モバイルリポの局所修正 → push → CI 監視 → TestFlight 到達確認。Web版 `update-deploy` のモバイル相当。
- `mobile-app-smoke-test` — 生成された IPA / AAB を Simulator / Emulator で起動確認。5 秒待ってクラッシュを検知したら crash-triage を呼ぶ。
- `mobile-crash-triage` — TestFlight / Play Internal Track のクラッシュを取得 → シンボリケート → known-crash-patterns.md と照合 → 修正提案を出す（自動修正はしない）。

**atomic（実配信の詳細ノウハウ層）**:
- `ios-testflight-deploy` — fastlane + altool で TestFlight にアップロード。SwiftSupport 保全・actool 自前コンパイル・AuthKey 命名など全部入り。v0.2.0 で `ios-release-auto.yml` 全文同梱。
- `android-play-deploy` — Gradle + bundletool + Play Publisher API で Internal Track にアップロード。track: internal → 昇格は `android_promote` MCP で。

**atomic（v0.3.0 追加：MustPost 移植ノウハウ）**:
- `ios-sim-auth-backdoor` — Simulator 上で Firebase Auth の keychain と Custom Token deep link を両立させる 2 本立て（keychain + IME 罠を同時に潰す）。
- `flutter-swift-parity-port` — Flutter → SwiftUI 見た目パリティ移植の 5 フェーズ workflow + 逸脱ポリシー + 写像表。
- `apiv2-callable-iam-gotchas` — Cloud Functions v2 apiv2-* の allUsers invoker 一括付与 + camelCase encoder pin。
- `firestore-bulk-index-sync` — 50+ composite index を Admin REST で冪等一括作成。
- `xcodegen-project-regen` — stale .xcodeproj → Missing package product を 30 秒で修復。

## MCP-first mobile automation stack

osi-mobile-deploy が前提とする AI OSI URI Deploy 拡張は、モバイル開発のフルスタックを MCP で叩ける（v1.18.5+）:

| 用途 | ツール | ポイント |
|---|---|---|
| ビルド | `xcode_build_for_sim` | v1.18.5 で `code_signing: "auto"` が既定に。以前は `CODE_SIGNING_ALLOWED=NO` を無条件注入していて keychain 罠を踏んでいた |
| Shell 実行 | `mac_shell` | 既定 timeout 600s（Firebase フルビルド想定）。ホワイトリスト方式で安全 |
| Simulator 制御 | `xcode_sim_boot` / `install_app` / `launch_app` / `tap` / `type` / `screenshot` / `open_url` | Custom Token deep link や UI 検証に使う |
| UI インスペクション | `xcode_sim_describe_ui` | 出力が巨大（数百 KB）なので save_to でファイルに落として python3 で grep するのが正解 |
| Firebase Auth | `firebase_auth_mint_custom_token` | IAM signJwt で Custom Token を発行 → Sim の deep link に渡す |
| Firebase | `firebase_upgrade_to_blaze` / `firebase_add_ios_app` / `firebase_get_ios_config` / etc. | 19 種類のツールで初期プロビジョニングを完結 |
| GCP IAM | `gcp_iam_add_roles_batch` | apiv2-* に allUsers invoker を一括付与 |
| Firestore | `firestore_get_doc` / `firestore_query` / `firestore_set_doc` etc. | ドキュメント CRUD |
| GitHub Secrets | `github_set_secrets_batch` | libsodium sealed box 暗号化は自動 |
| TestFlight / Play | `ios_get_status` / `android_get_status` / `android_promote` / `ios_submit_review` | 配信状態確認・昇格・審査提出 |

各スキルはこの MCP スタックを前提に書かれている。

## 前提

- Cowork または Claude Desktop に `AI OSI URI Deploy` MCP 拡張 v1.18.5+ が導入済み
- macOS Keychain に以下の secrets が格納済み（初回のみユーザーが登録）:
  - iOS: `APPLE_TEAM_ID`, `APP_STORE_CONNECT_API_KEY_ID`, `APP_STORE_CONNECT_API_KEY_ISSUER_ID`, `APP_STORE_CONNECT_API_KEY_B64`, `IOS_DIST_CERT_P12_B64`, `IOS_DIST_CERT_PASSWORD`, `IOS_KEYCHAIN_PASSWORD`
  - Android: `ANDROID_KEYSTORE_B64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`, `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`
- ローカル環境: Xcode 26+（iOS 26 SDK）, fastlane, xcodegen, Android Studio / SDK, JDK 17+
- **Xcode を一度は起動していること**（Automatic Signing の初期セットアップに必要）

## 使い方

Cowork で:

```
モバイルアプリ作って。名前は Foo、メモを記録するだけの Hello World、iOS と Android 両方
```

とだけ言うと、`deploy-mobile-app` が発動して以下が自動で回る:

1. アプリ情報のヒアリング（Bundle ID / GitHub Org 等）
2. Golden Template から新規リポ生成 → GitHub push
3. Firebase プロジェクト新規作成 + iOS/Android App 追加 + plist取得
4. GitHub Secrets 10個を投入
5. CI 起動を検知 → iOS/Android の両ワークフローを監視
6. CI 失敗したら `ci-failure-patterns.md` と照合 → 既知パターンなら auto-fix push（最大3回）
7. 両方 green → Simulator / Emulator でスモークテスト
8. TestFlight リンク + Play Internal Track リンクをユーザーに提示

途中で Simulator QA が必要になる場合は `ios-sim-auth-backdoor` が自動で参照される。

## 関連プラグイン

- `osi-deploy` — Web / SaaS 側の対応プラグイン
- `osi-sales/proposal-package` — 提案書パッケージ（モバイルアプリを見積もりに含める案件で参照）
