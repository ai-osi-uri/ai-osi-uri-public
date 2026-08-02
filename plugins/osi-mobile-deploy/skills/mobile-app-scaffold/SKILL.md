---
name: mobile-app-scaffold
description: |
  Golden Template（SwiftUI + Jetpack Compose、Firebase / CI / fastlane 込み）
  から新規モバイルリポを起こして GitHub に push する。`deploy-mobile-app` の Phase 2
  から呼ばれる。単体では「モバイルの雛形を作って」「Golden Template からリポ作って」
  で発動。
version: 0.2.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# mobile-app-scaffold — Golden Template（SwiftUI + Compose）から新規モバイルリポを起こす

**方針**：AI OSI URI の新規モバイルアプリは **ネイティブ 2 本立て**（iOS = SwiftUI、
Android = Kotlin + Jetpack Compose）を **既定**とする。単一コードベースの誘惑（Flutter /
React Native）は greenfield では **選ばない**。理由は次の通り:

- OS 標準のアクセシビリティ・ハプティクス・写真ピッカー・通知権限フローに素直に乗れる
- iOS 26 / Android 15 の新機能（Live Activities, Predictive Back, Widget, etc.）に **その日から**追えて、bridge の遅延を待たなくてよい
- クラッシュログが `symbolicate` / `mapping.txt` で 1 発で読める（Flutter engine の thunk を辿らなくてよい）
- Firebase iOS SDK / Firebase Android SDK は SwiftUI / Compose 対応が公式でドキュメント化されている
- AI OSI URI の実運用（MustPost の Flutter→SwiftUI 移植）で「結局ネイティブに寄せる」という結論に至った

**Flutter を選ぶのは、既存の Flutter アプリの改修が必要な場合だけ**（そのときは
`flutter-swift-parity-port` の 5 フェーズ移植ワークフローに乗る）。**新規で Flutter を
書き始めることは、本プラグインでは行わない**。

`template/` 配下の Golden Template（`apps/ios/` + `apps/android/` + `.github/workflows/` +
`fastlane/`）を clone し、プレースホルダを置換して GitHub に push する。

## Golden Template のスタック（既定）

| プラットフォーム | UI | 言語 | 最小サポート | ビルド | CI |
|---|---|---|---|---|---|
| iOS | **SwiftUI** (`@main App`) | Swift 5.10+ | **iOS 16.0** | xcodegen + xcodebuild + fastlane pilot | `.github/workflows/ios-release-auto.yml` |
| Android | **Jetpack Compose** (`@Composable`) | Kotlin 1.9+ | **minSdk 26** (Android 8.0) | Gradle + Kotlin DSL + fastlane supply | `.github/workflows/android-release-auto.yml` |

**DI**：v1 は SwiftUI 側は `@StateObject` / `@EnvironmentObject`、Compose 側は
`viewModel()` + `remember`。DI コンテナ（Swinject / Hilt）は 3 画面以上に増えた時点で
導入する（初期は入れない）。

**Networking**：iOS は `URLSession` + `async/await`、Android は `Ktor client` + `coroutines`。
`Alamofire` / `Retrofit` は v1 では入れない（薄い層を素で書いた方が Firebase Functions v2
の Callable レスポンス整形に馴染む）。

**Firebase 配線**：iOS は SPM + `FirebaseCore.configure()` を AppDelegate に置く
（`FirebaseApp.app() != nil` guard あり）。Android は `google-services` plugin +
`FirebaseApp.initializeApp(this)` を `Application.onCreate()` に置く。両方とも
plist / json 未配置でも起動時に crash しない guard 済み。

**リリース自動化**：本スキルで scaffold 後、`ios-testflight-deploy` と
`android-play-deploy` が CI を回して TestFlight / Play Internal Track まで届ける。
`.github/workflows/*-release-auto.yml` は「今日の罠回避全部入り」の実運用版を同梱。

## 入力契約

| 項目 | 必須 | 説明 | 例 |
|---|---|---|---|
| `app_name` | ✅ | PascalCase | `Foo` |
| `bundle_id` | ✅ | iOS Bundle ID | `com.aiosiuri.foo` |
| `package_name` | ✅ | Android Package Name（= applicationId） | `com.aiosiuri.foo` |
| `display_name` | 任意 | 画面表示名（既定: `app_name`） | `Foo` |
| `team_id` | 任意 | Apple Developer Team ID（既定: Keychain の `APPLE_TEAM_ID`） | `24X327Z9SJ` |
| `targets` | 任意 | `ios` / `android` / `both`（既定: `both`） | `both` |
| `github_org` | 任意 | `ai-osi-uri` / `personal`（既定: personal） | `ai-osi-uri` |
| `local_dir` | 任意 | 既定: `~/projects/{app_name_lower}` | |

## 置換対象（Golden Template 内のプレースホルダ）

| プレースホルダ | 置換後 | 出現箇所 |
|---|---|---|
| `MyApp` | `{app_name}` | ディレクトリ名、Swift ソース内、xcodeproj |
| `com.example.myapp` | `{bundle_id}` / `{package_name}` | Info.plist, project.yml, build.gradle.kts |
| `com/example/myapp` | `{package_name_slash}` | Android の java パッケージパス |
| `MY_APP_DISPLAY_NAME` | `{display_name}` | Info.plist の CFBundleDisplayName |
| `MY_APP_TEAM_ID` | `{team_id}` | project.yml の DEVELOPMENT_TEAM |
| `my-app-splash` | `{app_name_lower}-splash` | Assets のスプラッシュ参照名 |

## ワークフロー

```
1. スキル自身の template/ ディレクトリの絶対パスを解決
2. rsync -a --exclude '.DS_Store' template/ {local_dir}/   （新規または上書き）
3. sed で全ファイルのプレースホルダを一括置換
   - Bundle ID / Package Name（ドット区切り）
   - パッケージパス（スラッシュ区切り）
   - Java パッケージのディレクトリを mv でリネーム
   - App 名（PascalCase）
   - Display Name
   - Team ID
4. targets に応じて不要な apps/ サブディレクトリを削除（ios only なら apps/android を消す）
5. git init → 初回 commit
6. github_create_repo_and_push で GitHub に新規リポ作成 + push
7. 結果を返す
```

### Step 1〜3: テンプレ展開 + 置換

```bash
TEMPLATE_DIR="$(dirname "$0")/template"   # スキル自身の template/
LOCAL_DIR="${LOCAL_DIR:-$HOME/projects/${APP_NAME_LOWER}}"

# 展開（既存なら halt & ask ユーザー）
if [ -d "$LOCAL_DIR" ]; then
  echo "既に $LOCAL_DIR がある。上書きすると差分が失われる。"
  echo "続けるなら OSI_FORCE=1 を再設定して再実行。"
  [ "${OSI_FORCE:-}" = "1" ] || exit 1
fi
mkdir -p "$LOCAL_DIR"
rsync -a --exclude '.DS_Store' --exclude '.git' "$TEMPLATE_DIR/" "$LOCAL_DIR/"

# iOS ディレクトリ / Swift ソースを rename
cd "$LOCAL_DIR"
if [ -d apps/ios/MyApp ]; then
  mv apps/ios/MyApp "apps/ios/${APP_NAME}"
  mv "apps/ios/${APP_NAME}/App/MyAppApp.swift" "apps/ios/${APP_NAME}/App/${APP_NAME}App.swift"
fi

# Android の Java パッケージパス rename
PKG_SLASH_OLD="com/example/myapp"
PKG_SLASH_NEW="$(echo "$PACKAGE_NAME" | tr '.' '/')"
if [ -d "apps/android/app/src/main/java/${PKG_SLASH_OLD}" ]; then
  mkdir -p "apps/android/app/src/main/java/${PKG_SLASH_NEW}"
  # rsync でファイルを移動（親ディレクトリが違うため）
  rsync -a "apps/android/app/src/main/java/${PKG_SLASH_OLD}/" \
           "apps/android/app/src/main/java/${PKG_SLASH_NEW}/"
  rm -rf "apps/android/app/src/main/java/com/example"
fi

# 全ファイル一括置換（*.swift, *.kts, *.xml, *.plist, *.json, *.yml, project.yml, Fastfile, Info.plist）
# BSD sed (macOS) と GNU sed で挙動が違うので -i.bak 経由で共通化
find "$LOCAL_DIR" -type f \
  \( -name '*.swift' -o -name '*.kt' -o -name '*.kts' -o -name '*.gradle' \
     -o -name '*.xml' -o -name '*.plist' -o -name '*.json' -o -name '*.yml' \
     -o -name '*.yaml' -o -name 'Fastfile' -o -name 'Appfile' -o -name 'project.yml' \
     -o -name 'README.md' -o -name '.gitignore' \) \
  -exec sed -i.bak \
    -e "s|com\.example\.myapp|${BUNDLE_ID}|g" \
    -e "s|com/example/myapp|${PKG_SLASH_NEW}|g" \
    -e "s|MyApp|${APP_NAME}|g" \
    -e "s|MY_APP_DISPLAY_NAME|${DISPLAY_NAME}|g" \
    -e "s|MY_APP_TEAM_ID|${TEAM_ID}|g" \
    -e "s|my-app-splash|${APP_NAME_LOWER}-splash|g" \
    {} +
find "$LOCAL_DIR" -name '*.bak' -delete
```

### Step 4: targets に応じた削除

```bash
case "$TARGETS" in
  ios)
    rm -rf apps/android
    rm -f .github/workflows/android-release-auto.yml
    ;;
  android)
    rm -rf apps/ios
    rm -f .github/workflows/ios-release-auto.yml
    ;;
  both)
    # 何もしない
    ;;
esac
```

### Step 5-6: git init + push

```
mcp__AI_OSI_URI_Deploy__github_create_repo_and_push:
  work_dir: {local_dir}
  repo_name: {app_name_lower}
  owner_override: {ai-osi-uri or personal}
  private: true
  description: "{app_name} — created by AI OSI URI osi-mobile-deploy (SwiftUI + Compose)"
```

## 生成される Golden Template のプロジェクトレイアウト

```
apps/
  ios/
    project.yml                  # xcodegen spec — 「xcodegen generate」で .xcodeproj を再生成可
    MyApp/
      App/
        MyAppApp.swift           # @main の SwiftUI App
        AppDelegate.swift        # FirebaseApp.configure() を guard 付きで呼ぶ
      ContentView.swift          # Hello World の SwiftUI View
      Config/
        Base.xcconfig
        Dev.xcconfig
        Prod.xcconfig
      Resources/
        Info.plist               # CFBundleIconName あり、UIAppFonts なし、REVERSED_CLIENT_ID なし
        Assets.xcassets/AppIcon.appiconset/   # iOS 26 の single-icon 形式
        GoogleService-Info-Dev.plist.sample   # mobile-firebase-setup が実物に差し替え
  android/
    settings.gradle.kts
    build.gradle.kts
    app/
      build.gradle.kts           # Kotlin + Compose + dev/stg/prod flavor + Firebase BOM
      src/main/
        AndroidManifest.xml
        java/com/example/myapp/
          MyApplication.kt       # Application.onCreate で FirebaseApp.initializeApp を guard
          MainActivity.kt        # ComponentActivity + setContent {}
          ui/MainScreen.kt       # Hello World の @Composable
          ui/theme/{Color,Theme,Type}.kt
        res/{mipmap-*/, values/, xml/, mipmap-anydpi-v26/}
      google-services.json.sample
    gradle/wrapper/gradle-wrapper.{jar,properties}
    gradlew / gradlew.bat
.github/workflows/
  ios-release-auto.yml           # push → TestFlight（罠回避全部入り／`ios-testflight-deploy` 参照）
  android-release-auto.yml       # push → Play Internal Track
fastlane/
  Fastfile                       # ios_beta_auto + android_beta_auto レーン
  Appfile
  Pluginfile
Gemfile
.gitignore
README.md
```

**同梱の「今日の罠回避」**（Golden Template に既に入っている）:

- `FirebaseApp.configure()` は plist が無くても crash しない guard 付き
- `Info.plist` に `CFBundleIconName` + `CFBundleIcons`（ITMS-90XXX ガード）
- `UIAppFonts` を **敢えて入れていない**（missing-font crash 回避）
- Google Sign-In の URL scheme を **敢えて入れていない**（空の REVERSED_CLIENT_ID で crash 回避）
- iOS CI は macOS 15 + Xcode 26.x + P12 一時 keychain + auto-signing + flavor 3 種
- IPA 再パッケージは `ditto` で SwiftSupport 保全（ITMS-90426 ガード）
- Android は `versionCode` を Play internal max + 1 に自動採番

## 戻り値

```json
{
  "repo_url": "https://github.com/{owner}/{repo}",
  "repo_owner": "{owner}",
  "repo_name": "{repo}",
  "repo_id": 123456,
  "local_clone_dir": "{local_dir}",
  "initial_commit_sha": "abc1234"
}
```

## エラーハンドリング

| 症状 | 対応 |
|---|---|
| 同名ローカルディレクトリあり | `OSI_FORCE=1` を要求、または新しい dir 名を確認 |
| 同名 GitHub リポあり | `mobile-update-deploy` に切り替え確認 |
| プレースホルダ置換で「MyApp」がユーザー入力の app_name に含まれる | 事前に `[[ "$APP_NAME" =~ ^[A-Za-z][A-Za-z0-9]*$ ]]` で validate |
| bundle_id が `com.example.*` のまま | halt & ask（App Store Connect に登録できない） |
| ユーザーが「Flutter で作って」と要求 | 本プラグインの既定はネイティブ 2 本立て。既存 Flutter アプリからの移行なら `flutter-swift-parity-port` を案内。新規で Flutter を採用したい特殊事情があるなら、その理由を明示的に確認したうえで本スキルの対象外として halt |

## 注意事項

- **既定はネイティブ 2 本立て**：iOS = SwiftUI, Android = Kotlin + Jetpack Compose。Flutter / React Native は greenfield では選ばない
- **Bundle ID / Package Name は同じ値で OK**（`com.aiosiuri.foo` 統一）。iOS と Android で分けたい特別な理由がある時だけ変える
- **Team ID が Keychain に無い** → Phase 0 でチェック済み前提。抜けていれば halt
- Golden Template 側にある `.github/workflows/*.yml` は既に「今日の罠回避全部入り」。scaffold 時に workflow は書き換えない（Bundle ID / Package Name の env だけ差し替える）
- `Podfile` は入っていない（SPM のみで組む前提）。Firebase iOS SDK も SPM から入れる
- iOS デプロイメントターゲットは **16.0** を既定（`apps/ios/project.yml`）。より広い互換性が必要な案件でも 16 未満には下げない
- Android は **minSdk 26**（Android 8.0）を既定（`apps/android/app/build.gradle.kts`）。26 未満は adaptive icon / Compose の JVM 要件で古くなり過ぎるので下げない

## 関連スキル

- `deploy-mobile-app` — 本スキルを Phase 2 で呼ぶオーケストレータ
- `mobile-firebase-setup` — scaffold 直後に呼ばれる Firebase プロビジョニング
- `mobile-secrets-sync` — TestFlight / Play 配信に必要な GitHub Secrets 投入
- `mobile-icon-generator` — 1024x1024 PNG から全 density アイコン生成
- `ios-testflight-deploy` — iOS の実配信（fastlane pilot + altool）
- `android-play-deploy` — Android の実配信（Gradle + bundletool + Play API）
- `flutter-swift-parity-port` — **既存 Flutter アプリからの移行時のみ** 使う（新規では使わない）
