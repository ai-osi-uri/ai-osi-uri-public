# CI 失敗パターン辞書（iOS + Android）

`deploy-mobile-app` の Phase 6/7 で CI ログをこの辞書と照合し、既知パターンなら
auto-fix push で回復する。**新しく踏んだ罠は必ずここに追記する**（次回同じ罠で
時間を溶かさないため）。

各パターン行の構成:

- **症状**: ログの特徴的な文字列（正規表現）
- **原因**: なぜ起きるか
- **修正**: 何をどう直すか
- **再発防止**: Golden Template に焼き込むべき初期状態

---

## iOS 系

### 1. `${FLAVOR^}: bad substitution`

- **症状**: `.github/workflows/ios-release-auto.yml` の `Fastlane ios_beta` step で出る。
- **原因**: bash 4+ の大文字化構文 `${FLAVOR^}` を macos-14 の bash 3.2 が理解できない。
- **修正**: workflow の shell 側で以下の `case` 文に置換:

    ```bash
    case "$FLAVOR" in
      dev)  FLAVOR_CAP="Dev"  ;;
      stg)  FLAVOR_CAP="Stg"  ;;
      prod) FLAVOR_CAP="Prod" ;;
    esac
    ```

- **再発防止**: Golden Template の workflow は最初から `case` 文で書く（`${FLAVOR^}` を絶対に使わない）。

### 2. `ITMS-90426: The bundle contains disallowed nested bundles` / `SwiftSupport missing`

- **症状**: `altool --upload-app` の validation フェーズで返る。
- **原因**: 手動で `unzip` → 修正 → `zip -r` した ipa は `SwiftSupport/iphoneos/*.dylib` を保全できない。
- **修正**: ipa を再 zip する時は `-y --symlinks` オプションを付けて symlink を保全する。より安全なのは `ditto`:

    ```bash
    ditto -c -k --sequesterRsrc --keepParent Payload "$APP_NAME.ipa"
    ```

- **再発防止**: fastlane `gym` の出力を触らない。触るなら `ditto` を使うヘルパースクリプトを Golden Template に置く（`scripts/repack_ipa.sh`）。

### 3. `Missing required icon file (120x120)` / `The bundle does not contain an app icon`

- **症状**: `altool --upload-app` の validation で出る（AppIcon が Assets.car に入っていない）。
- **原因**: Assets.xcassets 側に AppIcon-1024 だけ置いても、Xcode Cloud / GitHub Actions の gym が Assets.car にコンパイルしないことがある（iOS 26 の単一アイコン形式の不一致）。
- **修正**: `xcrun actool` で Assets.car を自前コンパイルしてから ipa に差し込む:

    ```bash
    xcrun actool \
      --compile "$OUT_DIR" \
      --platform iphoneos \
      --minimum-deployment-target 17.0 \
      --app-icon AppIcon \
      --output-partial-info-plist "$OUT_DIR/AssetsInfo.plist" \
      "apps/ios/MyApp/Resources/Assets.xcassets"
    cp "$OUT_DIR/Assets.car" "Payload/$APP.app/Assets.car"
    ```

- **再発防止**: Golden Template の workflow に `Materialize legacy AppIcon file names` step を入れて、Assets.car 生成後に `AppIcon60x60@2x.png` `AppIcon60x60@3x.png` を明示的に Payload 直下にコピーする（iOS 26 単一アイコンでも旧命名ファイルを併置しないと validation を通らないビルダーがある）。

### 4. `AuthKey_XXXX.p8 not found` / `Could not find the API key file`

- **症状**: `altool` / `pilot` の初期化で出る。
- **原因**: altool は `~/private_keys/AuthKey_<KEY_ID>.p8` という固定命名を期待する。base64 復号したファイルを `asc_api_key.p8` にリネームしていると読めない。
- **修正**: 復号したファイルを必ず `AuthKey_${APP_STORE_CONNECT_API_KEY_ID}.p8` にリネーム、`~/private_keys/` か `$RUNNER_TEMP/private_keys/` に置く:

    ```bash
    mkdir -p "$RUNNER_TEMP/private_keys"
    echo "$APP_STORE_CONNECT_API_KEY_B64" | base64 --decode \
      > "$RUNNER_TEMP/private_keys/AuthKey_${APP_STORE_CONNECT_API_KEY_ID}.p8"
    export APP_STORE_CONNECT_API_KEY_PATH="$RUNNER_TEMP/private_keys/AuthKey_${APP_STORE_CONNECT_API_KEY_ID}.p8"
    ```

- **再発防止**: Golden Template の workflow の "Restore App Store Connect .p8" step に上記の命名を焼き込む。

### 5. `Firebase not configured — FirebaseApp.app() returned nil` でクラッシュ

- **症状**: TestFlight ビルドが起動直後に SIGABRT でクラッシュ。ログに `The default Firebase app has not been configured` と出る。
- **原因**: `AppDelegate.application(_:didFinishLaunchingWithOptions:)` で `FirebaseApp.configure()` を無条件で呼んでいるが、GoogleService-Info.plist が入っていないビルドでも走ってしまう。
- **修正**: guard を入れる:

    ```swift
    if let path = Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist"),
       let opts = FirebaseOptions(contentsOfFile: path) {
      FirebaseApp.configure(options: opts)
    } else {
      Logger.app.warning("GoogleService-Info.plist not found — skipping Firebase configuration")
    }
    ```

- **再発防止**: Golden Template の `AppDelegate.swift` に最初から guard を入れておく。

### 6. `Invalid URL scheme (empty REVERSED_CLIENT_ID)` → 起動時クラッシュ or 警告

- **症状**: Info.plist の `CFBundleURLTypes[0].CFBundleURLSchemes[0]` が `$(REVERSED_CLIENT_ID)` のまま、GoogleService-Info.plist にはその key が無い状態。TestFlight validation は通るが起動時に URL scheme dispatch でクラッシュする。
- **原因**: Google Sign-In を使う設計にしたが、OAuth client を作っていない → `REVERSED_CLIENT_ID` が空 → 空 scheme を Info.plist に埋め込む形になる。
- **修正**: Google Sign-In をまだ入れないなら、Info.plist の該当 `CFBundleURLTypes` エントリごと削除する。入れる時は Firebase Console → Authentication → Sign-in method → Google → iOS OAuth client を作り、`REVERSED_CLIENT_ID` を GoogleService-Info.plist から xcconfig に export する。
- **再発防止**: Golden Template の Info.plist に URL scheme を最初から入れない（コメントで「Google Sign-In を入れる時にここに追加」と誘導）。

### 7. `Font registration failed for '.otf'` → 起動時クラッシュ

- **症状**: `Info.plist` の `UIAppFonts` に `.otf` を宣言しているが、Resources/Fonts/ にファイルが無い（もしくは Copy Bundle Resources に含まれていない）。
- **原因**: MustPost で使っていた `NotoSansJP-Regular.otf` などをそのまま Golden Template に残していると再発する。
- **修正**: `UIAppFonts` を Info.plist からコメントアウトする（`<!-- ... -->` で囲む）か、削除する。カスタムフォントを本気で使うなら xcodegen の `resources` に確実にバンドルされていることを確認する。
- **再発防止**: Golden Template の Info.plist で `UIAppFonts` は最初からコメントアウト状態にする（フォントを入れる時のコメントを添えて）。

### 8. `Provisioning profile does not include the currently selected device` / signing 失敗

- **症状**: `xcodebuild archive` が signing で失敗。
- **原因**: fastlane match を使っていない、または match repo にプロビジョニングが無い。
- **修正**: 本 Golden Template は **Automatic Signing 前提**（`match` を使わない）。`project.yml` で `CODE_SIGN_STYLE: Automatic` を明示。それでもダメなら Apple Developer Portal で App ID を事前登録しておく。
- **再発防止**: Golden Template の `project.yml` に `CODE_SIGN_STYLE: Automatic` + `DEVELOPMENT_TEAM: $(APPLE_TEAM_ID)` を焼き込む。

### 9. `Xcode 15 not found` / iOS 26 SDK 不足

- **症状**: `xcodebuild archive` が「iOS 26.0 SDK not available」で失敗。
- **原因**: workflow で `sudo xcode-select -s /Applications/Xcode_15.4.app` を選んでいる。Xcode 26 は macos-14 image に含まれる。
- **修正**: workflow の "Select Xcode" step を `XCODE_VERSION: "26.0"` に上げる:

    ```yaml
    - name: Select Xcode
      run: sudo xcode-select -s /Applications/Xcode_${XCODE_VERSION}.app
    ```

- **再発防止**: Golden Template は最初から `XCODE_VERSION: "26.0"` で焼き込む。

### 10. `CFBundleIconName` が無い → validation 失敗

- **症状**: `altool` validation で `Missing Info.plist value` / `CFBundleIconName`。
- **原因**: iOS 11+ で asset catalog icon を使う場合、Info.plist に `CFBundleIconName = AppIcon` が必須。
- **修正**: Info.plist に以下を追加:

    ```xml
    <key>CFBundleIconName</key>
    <string>AppIcon</string>
    <key>CFBundleIcons</key>
    <dict>
        <key>CFBundlePrimaryIcon</key>
        <dict>
            <key>CFBundleIconName</key>
            <string>AppIcon</string>
        </dict>
    </dict>
    ```

- **再発防止**: Golden Template の Info.plist に最初から入れておく。

---

## Android 系

### 11. `Execution failed for task ':app:validateSigningRelease'`

- **症状**: `./gradlew bundleRelease` で keystore パスが解決できない。
- **原因**: `keystore.properties` を CI で `local.properties` と混同して置いていない。
- **修正**: workflow で Keychain の secrets から `keystore.properties` を作る:

    ```bash
    cat > apps/android/keystore.properties <<EOF
    storeFile=$RUNNER_TEMP/release.keystore
    storePassword=$ANDROID_KEYSTORE_PASSWORD
    keyAlias=$ANDROID_KEY_ALIAS
    keyPassword=$ANDROID_KEY_PASSWORD
    EOF
    echo "$ANDROID_KEYSTORE_B64" | base64 --decode > "$RUNNER_TEMP/release.keystore"
    ```

- **再発防止**: Golden Template の Android workflow に "Restore keystore" step を最初から入れる。

### 12. `Google Services JSON file not found`

- **症状**: `google-services` プラグインが `app/google-services.json` を探して失敗。
- **原因**: Secrets の `GOOGLE_SERVICES_JSON_DEV_B64` を復号して置いていない。
- **修正**: workflow の "Restore google-services.json" step:

    ```bash
    echo "$GOOGLE_SERVICES_JSON_DEV_B64" | base64 --decode \
      > apps/android/app/google-services.json
    ```

- **再発防止**: `.gitignore` に `google-services.json` を入れ、CI 側でのみ復号する。Golden Template の workflow に step を焼き込む。

### 13. `Upload failed: You cannot rollout this release because it does not allow any existing users to upgrade`

- **症状**: Play Publisher API に AAB を上げた時に返る。
- **原因**: `versionCode` を上げていない（前と同じ）。
- **修正**: fastlane lane で `versionCode` を「Play Console 上の最大値 + 1」に増分。Play 側の最新 code は `google_play_track_version_codes` action で取れる。
- **再発防止**: fastlane の `android_beta_auto` lane に自動増分を組み込む（Golden Template の Fastfile に焼き込み済み）。

### 14. `Unable to install app` on emulator

- **症状**: `adb install app-release.apk` が失敗。
- **原因**: emulator と apk の ABI が合わない、または署名が debug と release で衝突。
- **修正**: emulator は arm64-v8a の system image を使い、`./gradlew assembleDebug` で debug ビルドを install（release は Play にのみ）。smoke-test は debug 変種を使う。
- **再発防止**: `mobile-app-smoke-test` は最初から debug ビルドを install する仕様にする。

### 15. Kotlin Compose Compiler 版数不一致

- **症状**: `Could not find compose-compiler for Kotlin X.Y.Z`。
- **原因**: Kotlin と Compose Compiler の対応表がずれている。
- **修正**: `libs.versions.toml` で Kotlin と Compose Compiler を一致させる。`kotlin("plugin.compose")` プラグイン（Kotlin 2.0+）を使うと自動追従。
- **再発防止**: Golden Template では `kotlin("plugin.compose")` を使う（`composeOptions.kotlinCompilerExtensionVersion` を書かない）。

---

## パターンに無い失敗が出たら

1. まず失敗した job の logs を full で読む（末尾だけでなく最初のエラー行から）。
2. 症状 → 原因 → 修正 → 再発防止 の 4 行に整理する。
3. 本ファイルに追記して commit する（`references/ci-failure-patterns.md` は生きた辞書）。
4. Golden Template を直せる罠なら Template も同時に更新して、次回の新規アプリで再発しないようにする。
