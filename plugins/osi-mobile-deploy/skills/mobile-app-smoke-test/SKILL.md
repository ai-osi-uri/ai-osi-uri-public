---
name: mobile-app-smoke-test
description: |
  ローカルビルドした IPA / AAB を iOS Simulator / Android Emulator にインストールし、
  起動して 5 秒待ってクラッシュ検知するだけの軽量スモークテスト atomic スキル。
  iOS は `xcrun simctl` で Simulator 起動 → .app を install → launch → stderr 監視。
  Android は `emulator` + `adb install` + `adb shell am start` + `logcat` 監視。
  クラッシュしたら stderr / logcat を取得して `mobile-crash-triage` を呼ぶ。オーケストレータ
  `deploy-mobile-app` / `mobile-update-deploy` から呼ばれる。単体で「iOS Simulator で起動確認」
  「Emulator でスモークして」でも発動する。
version: 0.1.0
---

# mobile-app-smoke-test — Simulator / Emulator でのスモーク起動確認

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `work_dir` | ✅ | モバイルリポの絶対パス |
| `targets` | 任意 | `ios` / `android` / `both`（既定: `both`） |
| `wait_seconds` | 任意 | launch 後の待機秒数（既定: 5） |
| `simulator_device` | 任意 | 既定: `iPhone 16` |
| `emulator_avd` | 任意 | 既定: `Pixel_8_API_34` |

## ワークフロー

```
1. iOS の場合
   a. .app を build（IPA は install できないので .app を Debug 用に生成）
   b. simulator を boot（既に booted ならスキップ）
   c. .app を install
   d. launch
   e. wait_seconds 待つ
   f. crash check（`xcrun simctl spawn <UDID> log stream --level=debug --predicate ...` or 単純に app が生きているかを PID で確認）
2. Android の場合
   a. debug APK を build（./gradlew assembleDevDebug）
   b. emulator を boot
   c. adb install
   d. adb shell am start
   e. wait_seconds 待つ
   f. adb logcat で crash pattern を検索（FATAL EXCEPTION など）
3. 結果を返す
```

### Step 1: iOS

```bash
IOS_DIR="$WORK_DIR/apps/ios"
APP_NAME="$(basename "$(find "$IOS_DIR" -maxdepth 1 -type d -name '*.xcodeproj' | head -1)" .xcodeproj)"

# Debug ビルド
cd "$IOS_DIR"
xcodegen generate
xcodebuild \
  -project "$APP_NAME.xcodeproj" \
  -scheme "$APP_NAME" \
  -configuration Debug \
  -destination "generic/platform=iOS Simulator" \
  -derivedDataPath ./build \
  build

APP_PATH="./build/Build/Products/Debug-iphonesimulator/$APP_NAME.app"

# Simulator 起動
SIM_DEVICE="${SIMULATOR_DEVICE:-iPhone 16}"
SIM_UDID=$(xcrun simctl list devices "$SIM_DEVICE" | grep -oE '[0-9A-F-]{36}' | head -1)
if [ -z "$SIM_UDID" ]; then
  echo "❌ Simulator '$SIM_DEVICE' が無い。 xcrun simctl list devices で確認"
  exit 1
fi
xcrun simctl boot "$SIM_UDID" 2>/dev/null || true
open -a Simulator

# install + launch
xcrun simctl install "$SIM_UDID" "$APP_PATH"
BUNDLE_ID=$(defaults read "$(pwd)/$APP_PATH/Info" CFBundleIdentifier)
xcrun simctl launch --console-pty "$SIM_UDID" "$BUNDLE_ID" &
LAUNCH_PID=$!

sleep "${WAIT_SECONDS:-5}"

# crash check
if kill -0 $LAUNCH_PID 2>/dev/null; then
  IOS_STATUS="ok"
  kill $LAUNCH_PID 2>/dev/null || true
else
  IOS_STATUS="crashed"
  IOS_CRASH_LOG=$(xcrun simctl spawn "$SIM_UDID" log show --last 30s --predicate "process == '$APP_NAME'" 2>&1 | tail -100)
fi
```

### Step 2: Android

```bash
AND_DIR="$WORK_DIR/apps/android"
cd "$AND_DIR"

# Debug APK build
./gradlew assembleDevDebug -q

APK_PATH="$(find app/build/outputs/apk/dev/debug -name '*.apk' | head -1)"
PKG_NAME_DEBUG="$(./gradlew -q printApplicationId 2>/dev/null || echo com.example.myapp.debug)"

# Emulator 起動
EMU_AVD="${EMULATOR_AVD:-Pixel_8_API_34}"
if ! adb devices | grep -q emulator; then
  emulator -avd "$EMU_AVD" -no-snapshot -no-audio -no-window &
  # ブート完了待ち
  adb wait-for-device
  for i in $(seq 1 60); do
    BOOT_COMPLETED=$(adb shell getprop sys.boot_completed | tr -d '\r')
    [ "$BOOT_COMPLETED" = "1" ] && break
    sleep 2
  done
fi

# install + launch
adb install -r "$APK_PATH"
adb shell monkey -p "$PKG_NAME_DEBUG" -c android.intent.category.LAUNCHER 1
adb logcat -c   # clear previous logs

sleep "${WAIT_SECONDS:-5}"

# crash check
CRASH_LINES=$(adb logcat -d -s AndroidRuntime:E "$PKG_NAME_DEBUG:E" | grep -E "FATAL EXCEPTION|ANR in" || true)
if [ -n "$CRASH_LINES" ]; then
  ANDROID_STATUS="crashed"
  ANDROID_CRASH_LOG="$(adb logcat -d -s AndroidRuntime:E "$PKG_NAME_DEBUG:E" | tail -100)"
else
  ANDROID_STATUS="ok"
fi
```

### Step 3: 結果まとめ

```json
{
  "ios": {
    "status": "ok" | "crashed" | "skipped",
    "crash_log": "..."
  },
  "android": {
    "status": "ok" | "crashed" | "skipped",
    "crash_log": "..."
  },
  "duration_seconds": 47
}
```

## エラーハンドリング

| 症状 | 対応 |
|---|---|
| Simulator が boot しない | `xcrun simctl erase all && xcrun simctl boot ...` を提案 |
| Simulator device が無い | `xcrun simctl create` で作る、または簡単な device 名を指定 |
| Emulator が boot しない（30秒） | 60秒に延長、それでもだめならユーザーに Android Studio の AVD Manager を開いてもらう |
| adb がインストールされていない | `brew install --cask android-platform-tools` を案内 |
| Debug ビルドが失敗 | エラーログを提示、`mobile-crash-triage` は crash log 前提なので該当せず「build 失敗」として返す |
| crash した | `mobile-crash-triage` を呼ぶ提案をユーザーに提示 |

## 注意事項

- **IPA は Simulator にインストールできない**。IPA は実機用 (arm64) で Simulator は arm64/x86_64。必ず Debug ビルドの .app を使う。
- **release ビルドは Simulator で crash することがある**（App Attest / DeviceCheck が Simulator では動かない）。smoke test は debug ビルドで OK。
- **並列実行の注意**: iOS と Android を同時に走らせると Mac の負荷が高い。逐次でも 1〜2 分で終わる。
- **wait_seconds を長くしても保証にはならない**。深いバグは実機 / 実データで初めて出る。あくまで「起動時 crash 検知」の位置づけ。
