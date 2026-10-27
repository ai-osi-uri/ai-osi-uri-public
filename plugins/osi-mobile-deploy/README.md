# osi-mobile-deploy

自社のネイティブモバイルアプリ（iOS / Android）作成〜配信自動化。「モバイルアプリ作って」の一言で、SwiftUI + Jetpack Compose の Golden Template から新規リポを起こし、Firebase プロビジョニング・アイコン生成・GitHub Secrets 投入・CI 自動修正ループを回し、TestFlight / Google Play Internal Track まで到達させる。

`osi-deploy`（Web / SaaS デプロイ）と対を成す、モバイル配信専用プラグイン。

## スタック方針（重要）

**新規モバイルアプリの既定スタック**:

| プラットフォーム | UI | 言語 | 最小サポート |
|---|---|---|---|
| **iOS** | **SwiftUI** (`@main App`) | Swift 5.10+ | **iOS 16.0** |
| **Android** | **Jetpack Compose** (`@Composable`) | Kotlin 1.9+ | **minSdk 26**（Android 8.0） |

**Flutter は原則使用しない**（既存 Flutter アプリの移行時のみ `flutter-swift-parity-port` で例外的に扱う）。実運用（SampleApp の Flutter→SwiftUI 移植）で得た結論として、新規で単一コードベース（Flutter / React Native）を採用するより、最初からネイティブで書いた方が総コストが低い。OS 標準のアクセシビリティ・ハプティクス・写真ピッカー・通知権限フローに素直に乗れる／iOS 26 / Android 15 の新機能に bridge 遅延なく追える／クラッシュログが 1 発で読める／Firebase iOS/Android SDK は SwiftUI / Compose 公式対応。

新規で「Flutter で作りたい」という要望が来たら、既定がネイティブである旨と、既存資産の移行が必要かを確認する。単なる好みではネイティブで進めるのが本プラグインの方針。

## Changelog

### v0.10.0 — 配信用のキーは Admin、Xcode は一番新しいもの（2026-10）

- App Store Connect の API キーは「管理者（Admin）」で作る。App Manager だとクラウド署名の書き出しで `Cloud signing permission error` になる（役割は後から変えられないので作り直す）
- 雛形の iOS 配信は `macos-26` の runner で、入っている中で一番新しい Xcode（ベータ以外）を選んでからビルドする。古い SDK だと App Store Connect が `SDK version issue` で受け付けない
- `ios-testflight-deploy` の決まり・よくある失敗、`deploy-mobile-app` の失敗パターン・App 記録の説明をこれに合わせて直した

### v0.9.0 — 配信を人のボタン待ちにしない（2026-10）

鍵を GitHub に入れる道具はあったのに配信を動かす道具が無く、手作りの「手動だけ」のワークフローで最後の一押しが人の手になった実例を教訓にする。

- **雛形 `ios-release-auto.yml` を作り直し** — 鍵は App Store Connect の 3 点（`ASC_KEY_ID` / `ASC_ISSUER_ID` / `ASC_PRIVATE_KEY`）だけ、署名は Apple のクラウド署名（.p12・一時 keychain をやめた）。鍵が無いときは「鍵待ち」で緑のまま終わる。`set -o pipefail` で失敗を隠さない。ビルド番号は `run_number` + `BUILD_NUMBER_OFFSET`
- **雛形 `android-release-auto.yml`** — Play の鍵の名前を `PLAY_SERVICE_ACCOUNT_JSON` に（コネクタが入れる名前とそろえた）。鍵待ちスキップを追加
- **配信の仕組みの決まりを明文化**（`mobile-app-scaffold`）— push で動く＋手でも動かせる／鍵待ちは緑／pipefail／鍵の名前固定。手で書くときも守る
- **`ios-testflight-deploy` v0.4.0** — fastlane + altool + P12 の手順を、鍵 3 点 + xcodebuild + クラウド署名に書き直し。鍵を入れて流す・成否を見る・届いたかを見る、をコネクタの道具（`mobile_keys_to_github` / `github_run_workflow` / `github_workflow_runs` / `ios_get_status`）で通す
- **`mobile-secrets-sync` / `deploy-mobile-app` / `mobile-update-deploy`** — 配信の鍵は手元の Keychain ではなく鍵設定の会社の鍵から入れる。鍵がそろったら `start_release: true` で 1 回目を流す。鍵が足りなくても止めない
- 前提: remote-mcp 0.51.0（`github_run_workflow` / `github_workflow_runs` / `mobile_keys_to_github` の `start_release`）

### v0.6.0 — ASC App 記録の Phase 0 事前登録（2026-08）

SampleApp の prod 初回 TestFlight 配信が 37 秒で失敗した実例（`Could not find App with App Identifier {{company.reverse_domain}}.sampleapp.prod`）を教訓としてプラグインに定着させる。

- **`deploy-mobile-app` v0.3.0** — Phase 0 に step 4 を追加：**flavor ごとの Apple Developer Portal Bundle ID + App Store Connect App 記録の存在確認を必須化**。`references/create-asc-app-record.rb` ヘルパーと `references/asc-app-record-setup.md` 詳細手順を同梱。Bundle ID は API で作成されるが、App 記録は Admin role 必須なので Web UI に誘導するフォールバック付き
- **`ios-testflight-deploy` v0.3.0** — Pre-flight セクションを追加し、CI を回す前に ASC 登録の確認ヘルパーに飛ばせる。`ensure_assets_car_in_payload!` の actool `--minimum-deployment-target` を 17.0 → 16.0 に修正（Golden Template の project.yml と一致）
- **`mobile-secrets-sync` v0.3.0** — Firebase 周りの Secrets を dev/stg/prod の 3 flavor に拡張し、SampleApp で実際に必要だった `FIREBASE_ANDROID_APP_ID`（Android Crashlytics 用）と `GCP_SA_KEY_JSON`（`firebase deploy --only functions` 用）を一覧とバッチ例に追加
- **`ci-failure-patterns.md`** — pattern #16 「Could not find App with App Identifier」を追加。症状（fastlane 37 秒失敗）・原因 (Bundle ID / App 記録 未登録)・修正（Phase 0 に戻って `create-asc-app-record.rb`）・再発防止（Phase 0 必須化）の 4 行完備

### v0.4.0 — 新規はネイティブ既定を明文化（2026-07）

Flutter→SwiftUI ポートが実運用でほぼ稀（既存の移行案件だけ）と判明したので、新規モバイルアプリの既定スタックを **iOS = SwiftUI / Android = Kotlin + Jetpack Compose** に統一する方針を全スキルに反映。

- **`mobile-app-scaffold` v0.2.0** — description をネイティブ 2 本立て既定に書き換え、Golden Template のスタック表を追加（iOS 16.0 / minSdk 26）。「Flutter で作って」が来た時の対応をエラーハンドリング表に追加。iOS deployment target を 17.0 → 16.0 に、Android minSdk を 24 → 26 に更新（プロジェクトポリシーに合わせる）
- **`deploy-mobile-app` v0.2.0** — オーケストレータの description を「ネイティブ 2 本立て既定 + Flutter は greenfield では選ばない」に更新。Phase 1 ヒアリング表に「STACK」行を追加し、「Flutter で作って」要望への対応フローを Phase 1 と エラーハンドリング表に追記。完了レポートにスタック行を追加
- **`flutter-swift-parity-port` v0.2.0** — description と冒頭を「**既存 Flutter アプリの SwiftUI 移行専用**」に再フレーミング。「いつ使うか / 使わないか」表を追加し、新規開発では使わないことを明示。技術的な 5 フェーズ workflow・逸脱ポリシー・Dart→SwiftUI 写像表は保持
- **template/README.md** — 冒頭に「Flutter / React Native は使わない」の 1 行を追加
- **template/apps/ios/project.yml** — スタックポリシーコメント追加、iOS deployment target を 16.0 に
- **template/apps/android/app/build.gradle.kts** — スタックポリシーコメント追加、minSdk を 26 に

### v0.3.0 — SampleApp SwiftUI 移植のノウハウ追加（2026-07）

SampleApp（Flutter → SwiftUI ネイティブ化）で獲得した実運用ノウハウを 5 スキルで追加。既存スキルとの重複は避け、実際にハマった問題単位で切り出している。

- **`ios-sim-auth-backdoor`** — iOS Simulator で Firebase Auth の keychain 永続化を成立させる proper signing 既定（拡張 v1.18.5+ で `xcode_build_for_sim({code_signing: "auto"})` が既定に）と、`sampleapp://debug/signin?token=XXX` の Custom Token deep link バックドア（AppDelegate と SwiftUI 側 DeepLinkHandler の両方に置くのがミソ）
- **`flutter-swift-parity-port`** — Flutter → SwiftUI 移植を「感覚で似せる」ではなく inventory → diff → 優先度バッチ → build + 目視 → コミット の 5 フェーズで systematic に回す。日本語ラベル逐語コピー、iOS ネイティブに寄せてよい逸脱ポリシー、Dart→SwiftUI 写像早見表を同梱（v0.4.0 で移行専用として再フレーミング）
- **`apiv2-callable-iam-gotchas`** — Cloud Functions v2（Cloud Run 実装）の apiv2-* が client から `UNAUTHENTICATED` / `communication error` になる 2 大原因（allUsers → roles/run.invoker の一括付与忘れ + JSONEncoder の snake_case 変換）を潰す
- **`firestore-bulk-index-sync`** — `firebase deploy --only firestore:indexes` が 50+ index で詰まる問題を、Admin REST 直叩き（`collectionGroups/{cg}/indexes` POST）+ 409 と 400「not necessary」を成功に丸めて冪等化
- **`xcodegen-project-regen`** — `git pull` 後の「Missing package product 'FirebaseCore'」× 14 個症状を `xcodegen generate --spec apps/ios/project.yml` + Reset/Resolve Packages で 30 秒修復
- **`ios-testflight-deploy` v0.2.0** — SampleApp 実運用中の `.github/workflows/ios-release-auto.yml` 完全版を `references/ios-release-auto.yml.example` に同梱（macos-15 + Xcode 26.x + P12 一時 keychain + auto-signing + flavor 3 種）※ v0.9.0 でクラウド署名に置き換え

### v0.2.0 — 初版（10 スキル）

deploy-mobile-app オーケストレータ + 9 atomic を用意。

## スキル一覧

**オーケストレータ**:
- `deploy-mobile-app` — 「モバイルアプリ作って」で発動する新規作成の唯一の入口。ヒアリング → scaffold（SwiftUI + Jetpack Compose）→ Firebase → Secrets → push → CI 監視 → TestFlight / Play Internal Track 到達まで一気通貫。**Flutter で新規は作らない**方針の明示付き。

**atomic（新規作成）**:
- `mobile-app-scaffold` — **Golden Template（SwiftUI + Jetpack Compose）** から新規リポを clone → 6 箇所置換 → GitHub push。ネイティブ 2 本立て既定・iOS 16+ / minSdk 26 のポリシーを SKILL.md に明記。
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
- `ios-appstore-release` — **TestFlight より先**（ビルド昇格・App Store 申請・審査追跡）と Xcode バージョンの N-1 ピン運用（週次カナリア）。2026-08 に osi-deploy から移設。ビルド〜TestFlight の正本 CI は GitHub Actions（`ios-testflight-deploy`）で、本スキルの Xcode Cloud 操作は代替経路。**internal 扱い**（外部配布には含めない）。

**atomic（v0.3.0 追加：SampleApp 移植ノウハウ）**:
- `ios-sim-auth-backdoor` — Simulator 上で Firebase Auth の keychain と Custom Token deep link を両立させる 2 本立て（keychain + IME 罠を同時に潰す）。
- **`flutter-swift-parity-port`** — **既存 Flutter アプリ → SwiftUI 移行専用**（v0.4.0 で新規開発では使わないことを明示）。5 フェーズ workflow + 逸脱ポリシー + 写像表。
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

- Claude デスクトップに `AI OSI URI Deploy` MCP 拡張 v1.18.5+ が導入済み
- 配信の鍵はポータルの「鍵設定」に会社の鍵として預ける（手元の Keychain は使わない）:
  - iOS: App Store Connect の 3 点（Key ID・Issuer ID・.p8）。証明書（.p12）は要らない（Apple のクラウド署名）
  - Android: Play のサービスアカウント JSON。アップロード用キーストアは `mobile_generate_keystore` で作り Drive に控える
  - GitHub への投入は URL のコネクタの `mobile_keys_to_github`（シークレット名は `ASC_KEY_ID` / `ASC_ISSUER_ID` / `ASC_PRIVATE_KEY` / `PLAY_SERVICE_ACCOUNT_JSON`）
- ローカル環境: Xcode 26+（iOS 26 SDK）, fastlane, xcodegen, Android Studio / SDK, JDK 17+
- **Xcode を一度は起動していること**（Automatic Signing の初期セットアップに必要）

## 使い方

Claude で:

```
モバイルアプリ作って。名前は Foo、メモを記録するだけの Hello World、iOS と Android 両方
```

とだけ言うと、`deploy-mobile-app` が発動して以下が自動で回る:

1. アプリ情報のヒアリング（Bundle ID / GitHub Org 等）— スタックは既定でネイティブ 2 本立て
2. Golden Template（SwiftUI + Jetpack Compose）から新規リポ生成 → GitHub push
3. Firebase プロジェクト新規作成 + iOS/Android App 追加 + plist取得
4. 配信の鍵を GitHub に入れて、そのまま 1 回目の配信を流す（`mobile_keys_to_github` の `start_release`）
5. `github_workflow_runs` で iOS/Android の両ワークフローを監視
6. CI 失敗したら `ci-failure-patterns.md` と照合 → 既知パターンなら auto-fix push（最大3回）
7. 両方 green → Simulator / Emulator でスモークテスト
8. TestFlight リンク + Play Internal Track リンクをユーザーに提示

途中で Simulator QA が必要になる場合は `ios-sim-auth-backdoor` が自動で参照される。

## 関連プラグイン

- `osi-deploy` — Web / SaaS 側の対応プラグイン
- `osi-sales/proposal-package` — 提案書パッケージ（モバイルアプリを見積もりに含める案件で参照）
