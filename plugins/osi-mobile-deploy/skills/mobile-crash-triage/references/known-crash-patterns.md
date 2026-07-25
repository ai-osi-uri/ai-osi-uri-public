# 既知のクラッシュパターン辞書（iOS + Android）

`mobile-crash-triage` の Step 4 でこの辞書と照合する。`ci-failure-patterns.md`（CI ビルド系）
とは別レイヤ：本ファイルは **配信済みバイナリが実機・シミュレータで落ちる** 症状に絞る。

各エントリの構成:

- **pattern_id**: 参照用の短い id
- **症状**: crash log の特徴（トップフレーム / 例外種別 / メッセージ）
- **原因**: なぜ落ちるか
- **修正提案**: どのファイルを直すか
- **再発防止**: Golden Template や CI 側の予防策

---

## iOS

### `pattern_id: firebase-not-configured`

- **症状**: 起動直後 SIGABRT。トップフレーム `+[FIRApp defaultApp]` or `-[FIRApp configureWithOptions:]`。メッセージ: `The default Firebase app has not been configured`
- **原因**: `AppDelegate.application(_:didFinishLaunchingWithOptions:)` で `FirebaseApp.configure()` を無条件で呼ぶが、`GoogleService-Info.plist` が bundle に入っていない
- **修正提案**:
  1. `AppDelegate.swift` に guard を入れる（`if let path = Bundle.main.path(...)`）
  2. Xcode で plist を Copy Bundle Resources に追加
  3. CI で `GOOGLE_SERVICE_INFO_PLIST_DEV_B64` を復号する step を追加
- **再発防止**: Golden Template の AppDelegate に最初から guard を入れる（本テンプレは既に対応済み）

### `pattern_id: empty-url-scheme`

- **症状**: 起動時 or Google Sign-In 呼び出し時に crash。メッセージ: `Invalid URL scheme` or `unrecognized URL scheme <empty>`
- **原因**: `Info.plist` の `CFBundleURLSchemes[0]` が `$(REVERSED_CLIENT_ID)` のまま、GoogleService-Info.plist にその key が無い（Google Sign-In OAuth client 未作成）
- **修正提案**:
  1. Google Sign-In を使う予定が無い → Info.plist から該当 `CFBundleURLTypes` entry を削除
  2. 使う → Firebase Console → Auth → Google → OAuth client を作成 → `REVERSED_CLIENT_ID` を xcconfig に export
- **再発防止**: Golden Template の Info.plist に URL scheme を最初から入れない

### `pattern_id: font-registration-failed`

- **症状**: 起動時 crash。ログに `Font registration failed for '<file>.otf'`
- **原因**: `UIAppFonts` に宣言したフォントファイルが Bundle に無い
- **修正提案**:
  1. Info.plist の `UIAppFonts` を丸ごとコメントアウト（今使っていない）
  2. または `Resources/Fonts/` に .otf を配置し、`project.yml` の `resources` に登録
- **再発防止**: Golden Template の Info.plist で `UIAppFonts` は最初からコメントアウト

### `pattern_id: assets-car-missing`

- **症状**: 起動時に真っ黒画面（クラッシュはしないが icon / images が出ない）。TestFlight 側で「Missing required icon file」warning
- **原因**: `Assets.car` が Payload に入っていない（gym の設定ミス or 手動 zip の事故）
- **修正提案**:
  1. `xcrun actool` で Assets.car を自前生成する step を workflow に追加
  2. ipa 再 zip は `ditto` を使う（`zip` は resource fork を落とす）
- **再発防止**: Golden Template の workflow に `Compile Assets.car` step 焼き込み済み

### `pattern_id: main-thread-checker`

- **症状**: iOS 15+ で `Main Thread Checker: UI API called on a background thread` から SIGTRAP
- **原因**: URLSession completion handler や Task 内で `@MainActor` を明示せず UI 更新
- **修正提案**: 該当関数に `@MainActor` を付ける、または `await MainActor.run { ... }` で包む
- **再発防止**: SwiftUI + Concurrency のコード規約を CLAUDE.md に追加

### `pattern_id: cocoapods-swift-runtime-missing`

- **症状**: 起動時 `dyld: Symbol not found: _swift_...` で crash
- **原因**: Swift runtime library が bundle に含まれていない（`SwiftSupport/iphoneos/` 欠落）
- **修正提案**: fastlane gym の出力 ipa をそのまま使う（触らない）。触ったなら `ditto` で再 zip
- **再発防止**: `ci-failure-patterns.md` の項目 2 と同じ（SwiftSupport 保全）

---

## Android

### `pattern_id: google-services-json-missing`

- **症状**: 起動時 `FirebaseInitProvider` で crash。ログ `Default FirebaseApp is not initialized`
- **原因**: `google-services.json` が app 直下に無い / flavor サブディレクトリ (`app/src/dev/`) にも無い
- **修正提案**: CI で `GOOGLE_SERVICES_JSON_DEV_B64` を復号する step を追加、`app/src/dev/google-services.json` に配置
- **再発防止**: Golden Template の Android workflow に "Restore google-services.json" step 焼き込み済み

### `pattern_id: hilt-missing-annotation`

- **症状**: `IllegalStateException: Hilt Activity must be attached to an @HiltAndroidApp Application`
- **原因**: `Application` サブクラスに `@HiltAndroidApp` が付いていない、または `AndroidManifest.xml` で `android:name` を指定していない
- **修正提案**: `MyApplication.kt` に `@HiltAndroidApp` を追加、`AndroidManifest.xml` の `<application android:name=".MyApplication">`
- **再発防止**: Golden Template でDI 導入するときは最初から Hilt をセットアップ

### `pattern_id: compose-runtime-mismatch`

- **症状**: `NoSuchMethodError: ...ComposerImpl.startReplaceableGroup`
- **原因**: Compose Compiler と Compose Runtime のバージョンずれ
- **修正提案**: `libs.versions.toml` で `androidx.compose.bom` に統一、`kotlin("plugin.compose")` を使う
- **再発防止**: Golden Template で BOM 経由の版管理を最初から採用

### `pattern_id: r8-strip-model`

- **症状**: release ビルドでのみ `ClassNotFoundException` や JSON deserialization 失敗
- **原因**: R8 の minify が Kotlin data class を消してしまう
- **修正提案**: `proguard-rules.pro` に `-keep class com.example.myapp.model.** { *; }` を追加
- **再発防止**: Golden Template の proguard-rules.pro にモデル保護ルールを最初から入れる

### `pattern_id: android-anr`

- **症状**: ANR (Application Not Responding)、5 秒以上メインスレッドをブロック
- **原因**: `Room` / `Retrofit` を main thread で呼んでいる
- **修正提案**: `viewModelScope.launch(Dispatchers.IO) { ... }` で包む
- **再発防止**: `mobile-crash-triage` は crash log だけでなく ANR も同じフローで扱う

---

## 追記ルール

新しい crash を踏んだら:

1. `pattern_id`（kebab-case）を決める
2. 症状 → 原因 → 修正提案 → 再発防止 の 4 行に整理
3. 本ファイルに追記
4. Golden Template を直せる罠なら Template も同時に更新
5. commit message: `docs(crash-patterns): add <pattern_id>`

このファイルは「生きた辞書」。同じ罠で二度時間を溶かさないための投資として扱う。
