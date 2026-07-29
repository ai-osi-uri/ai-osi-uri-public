# MyApp — Native mobile app (iOS + Android)

Scaffolded by AI OSI URI **osi-mobile-deploy** plugin. Native stack from day one:

- **iOS**: SwiftUI (`@main App`), Swift 5.10+, deployment target **iOS 16.0**
- **Android**: Jetpack Compose (`@Composable`), Kotlin 1.9+, **minSdk 26** (Android 8.0)
- **Flutter / React Native は使いません**（新規開発の既定はネイティブ 2 本立て）。既存 Flutter アプリからの移行が必要な場合のみ `osi-mobile-deploy` の `flutter-swift-parity-port` スキルを別途使う。

This is a Hello World shell that already carries every hard-won lesson from the
plugin's initial build:

- Guarded `FirebaseApp.configure()` so a missing `GoogleService-Info.plist` no
  longer crashes at startup.
- `Info.plist` has `CFBundleIconName` + `CFBundleIcons` set (validates for iOS
  11+ asset-catalog icons; ITMS-90XXX guard).
- URL-scheme block for Google Sign-In is deliberately absent — no empty
  `$(REVERSED_CLIENT_ID)` = no launch-time crash.
- `UIAppFonts` is deliberately absent — no missing-font startup crash.
- Automatic Signing with `-allowProvisioningUpdates` (no `match` needed).
- CI workflow selects Xcode 26 (iOS 26 SDK), uses bash 3.2-compatible `case`
  (not `${FLAVOR^}`), restores `AuthKey_<ID>.p8` with the exact naming altool
  demands, and materializes legacy `AppIcon60x60@2x.png` filenames plus a
  self-recompiled `Assets.car` so old altool validators pass.
- IPA is re-packed with `ditto` when we touch it, keeping SwiftSupport symlinks
  intact (ITMS-90426 guard).
- Fastlane `pilot` uses `skip_waiting_for_build_processing: true` — no
  10-minute wait in CI.
- Android: `versionCode` auto-increments from Play internal max + 1;
  `MyApplication.onCreate` guards `FirebaseApp.initializeApp` so a missing
  `google-services.json` doesn't crash the process.

## Layout

```
apps/
  ios/
    project.yml            # xcodegen spec (regenerate: xcodegen generate)
    MyApp/
      App/
        MyAppApp.swift     # SwiftUI @main
        AppDelegate.swift  # Firebase guard, UIKit bridge
      ContentView.swift    # Hello World
      Config/              # xcconfig (Base / Dev / Prod)
      Resources/
        Info.plist         # CFBundleIconName present, UIAppFonts absent
        Assets.xcassets/AppIcon.appiconset/   # iOS 26 single-icon format
        GoogleService-Info-Dev.plist.sample   # replace with real via mobile-firebase-setup
  android/
    settings.gradle.kts
    build.gradle.kts
    app/
      build.gradle.kts     # Kotlin + Compose + dev/stg/prod flavors
      src/main/
        AndroidManifest.xml
        java/com/example/myapp/{MyApplication.kt, MainActivity.kt, ui/MainScreen.kt}
        res/{mipmap-*/, values/, xml/, mipmap-anydpi-v26/}
      google-services.json.sample
.github/workflows/
  ios-release-auto.yml       # push → TestFlight (all gotchas baked in)
  android-release-auto.yml   # push → Play Internal Track
fastlane/
  Fastfile                   # ios_beta_auto + android_beta_auto lanes
  Appfile
  Pluginfile
Gemfile
.gitignore
```

## Placeholders replaced by `mobile-app-scaffold`

The plugin rewrites these before `git push`:

| Placeholder | Replaced with | Example |
|---|---|---|
| `MyApp` | `<APP_NAME>` | `Foo` |
| `com.example.myapp` | `<BUNDLE_ID>` / `<PACKAGE_NAME>` | `com.aiosiuri.foo` |
| `com/example/myapp` | `<PACKAGE_PATH>` | `com/aiosiuri/foo` |
| `MY_APP_TEAM_ID` | `<APPLE_TEAM_ID>` | `24X327Z9SJ` |
| `MY_APP_DISPLAY_NAME` | `<DISPLAY_NAME>` | `Foo` |

## Next steps after scaffolding

1. `mobile-firebase-setup` provisions a Firebase project and pushes
   `GOOGLE_SERVICE_INFO_PLIST_DEV_B64` / `GOOGLE_SERVICES_JSON_DEV_B64` into
   this repo's Secrets.
2. `mobile-secrets-sync` pushes the App Store Connect / Distribution cert /
   Android keystore / Play SA Secrets from the operator's macOS Keychain.
3. `mobile-icon-generator` replaces the 1×1 placeholder PNGs with real icons.
4. `git push origin main` — CI takes over, and TestFlight / Play Internal
   Track are populated inside 15 minutes.
