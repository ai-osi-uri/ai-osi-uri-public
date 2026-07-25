# altool / pilot / xcrun actool の癖まとめ

TestFlight upload で今日実際に踏んだ罠。同じ罠で二度時間を溶かさないためのメモ。
Golden Template には既に対策済み。ここは「なぜそう書いたか」を残す層。

---

## 1. altool が要求する `.p8` の命名

**症状**: `altool` 起動時に `Could not find the API key file at ~/private_keys/`。

**原因**: `altool` は環境変数 `APP_STORE_CONNECT_API_KEY_PATH` を尊重せず、
`~/private_keys/AuthKey_<KEY_ID>.p8` という固定命名を期待する（fastlane pilot は
`APP_STORE_CONNECT_API_KEY_PATH` を尊重するが、内部で altool を呼ぶ経路もある）。

**対策**:

```bash
mkdir -p ~/private_keys
echo "$APP_STORE_CONNECT_API_KEY_B64" | base64 --decode \
  > ~/private_keys/AuthKey_${APP_STORE_CONNECT_API_KEY_ID}.p8
chmod 600 ~/private_keys/AuthKey_${APP_STORE_CONNECT_API_KEY_ID}.p8
```

CI では `$RUNNER_TEMP/private_keys/` を使い、workflow で `HOME=$RUNNER_TEMP` を一時的に
export するか、シンボリックリンクで `~/private_keys` を寄せる。

**確認**: `bundle exec fastlane pilot list --api_key_path=...` が通れば OK。

---

## 2. `ITMS-90426`（SwiftSupport が入っていない）

**症状**: `altool --upload-app` の validation が
`The bundle contains disallowed nested bundles` / `SwiftSupport missing` で reject。

**原因**: `gym` が出した ipa を手動で unzip → 中身修正 → `zip -r` で再パッケージすると、
`SwiftSupport/iphoneos/libswift*.dylib` の symlink が壊れる（`zip` は resource fork や symlink を落とす）。

**対策**: 再 zip する必要があるなら `ditto` を使う。

```bash
cd Payload_dir
ditto -c -k --sequesterRsrc --keepParent Payload "$OUT_IPA"
# SwiftSupport がある場合は、ipa の中身に SwiftSupport ディレクトリも含める
```

または、そもそも触らない。`gym` の出力 ipa をそのまま `pilot` に渡す。中身をいじりたくなる
のは大抵「Assets.car を差し込む」用途だが、それは事前に xcodebuild 側で解決すべき。

---

## 3. `Missing required icon file (120x120)`

**症状**: `altool` validation が「AppIcon が bundle に無い」で reject。ローカルの
`Assets.xcassets/AppIcon.appiconset/` には正しく置いてあるのに。

**原因（複合）**:
- (a) `gym` が Assets.car を Payload に含めていない（Copy Bundle Resources から漏れている）
- (b) iOS 26 の「単一アイコン形式」（AppIcon-1024 だけ）だと、古い altool のバリデータが
  legacy PNG（`AppIcon60x60@2x.png`）を探して失敗することがある

**対策**:

1. `xcrun actool` で Assets.car を自前コンパイル:

    ```bash
    xcrun actool \
      --compile "$PAYLOAD/MyApp.app" \
      --platform iphoneos \
      --minimum-deployment-target 17.0 \
      --app-icon AppIcon \
      --output-partial-info-plist "$TMP/AssetsInfo.plist" \
      "apps/ios/MyApp/Resources/Assets.xcassets"
    ```

2. legacy PNG を併置:

    ```bash
    cp AppIcon-120.png "$PAYLOAD/MyApp.app/AppIcon60x60@2x.png"
    cp AppIcon-180.png "$PAYLOAD/MyApp.app/AppIcon60x60@3x.png"
    ```

3. Info.plist に `CFBundleIconName` と `CFBundleIcons` dict を追加。

---

## 4. `CFBundleIconName` が無い

**症状**: `altool` validation が `Missing Info.plist value: CFBundleIconName`。

**原因**: iOS 11+ で asset catalog icon を使う場合、Info.plist に明示が必要。

**対策**: Info.plist に:

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

Golden Template には最初から入っている。

---

## 5. `pilot` が polling で 10 分待つ問題

**症状**: `pilot upload` は upload 完了後、TestFlight processing が終わるまで待つ既定挙動。
CI 時間が無駄に伸びる。

**対策**: `skip_waiting_for_build_processing: true` を渡す:

```ruby
pilot(
  ...,
  skip_waiting_for_build_processing: true,
)
```

processing 完了は `ios_get_status` MCP で別途確認する（`deploy-mobile-app` Phase 9 で行う）。

---

## 6. Xcode 26 の選択

**症状**: `xcodebuild archive` が `iOS 26.0 SDK not available`。

**原因**: `sudo xcode-select -s /Applications/Xcode_15.4.app` を選んでいる（GitHub Actions
の macos-14 image は Xcode 15.4 が default）。

**対策**: workflow の `Select Xcode` step:

```yaml
- name: Select Xcode
  run: sudo xcode-select -s /Applications/Xcode_${XCODE_VERSION}.app
env:
  XCODE_VERSION: "26.0"
```

macos-14 image に Xcode 26 が含まれていない場合は `macos-15` に切り替える必要がある
（Actions runner の更新次第）。

---

## 7. bash 3.2 互換の `case` 文

**症状**: workflow の bash step で `${FLAVOR^}: bad substitution`。

**原因**: macOS のシステム bash は 3.2（GPL v3 を避けているため）。`^` 大文字化は bash 4+ 拡張。

**対策**: `case` 文で回す:

```bash
case "$FLAVOR" in
  dev)  FLAVOR_CAP="Dev"  ;;
  stg)  FLAVOR_CAP="Stg"  ;;
  prod) FLAVOR_CAP="Prod" ;;
  *)    echo "unknown flavor: $FLAVOR" >&2; exit 1 ;;
esac
```

または `brew install bash` して `bash-5` を明示。Golden Template では前者を採用（追加インストール不要）。

---

## 8. Automatic Signing vs match

- 本 Golden Template は Automatic Signing 前提（match を使わない）。
- Distribution 証明書 1 枚を Keychain / GitHub Secrets で管理する運用。
- match を使いたくなる状況（複数開発者・複数マシン・複数 profile 管理）は Golden Template
  Phase 2 以降で明示的に切り替える。
- `xcargs: "-allowProvisioningUpdates DEVELOPMENT_TEAM=$APPLE_TEAM_ID"` を fastlane gym に
  渡すと、App ID や profile を Apple 側に自動要求してくれる（fastlane match を使わない場合の代替）。

---

## 9. bundleId prefix `com.example.*` の禁止

**症状**: App Store Connect に app を作ろうとして「Bundle ID is invalid」。

**原因**: Apple は `com.example.*` 系を予約 / disallowed としている。

**対策**: 必ず `com.{org}.{app_name}` 形式。AI OSI URI 案件は `com.aiosiuri.{app}` を推奨。

---

## 10. Build number の重複

**症状**: TestFlight upload が「Bundle version already exists」で reject。

**原因**: 前と同じ `CFBundleVersion` を使っている。

**対策**: fastlane で自動 increment（既に Fastfile に組み込み済み）:

```ruby
latest = latest_testflight_build_number(app_identifier: app_id, api_key: api_key, initial_build_number: 0)
increment_build_number(xcodeproj: "apps/ios/MyApp.xcodeproj", build_number: (latest.to_i + 1).to_s)
```

`CFBundleShortVersionString`（マーケティング版数）は手動で bump（1.0.1 → 1.0.2）。

---

## パターンに無い罠を踏んだら

1. altool / pilot のログを full で保存
2. 症状・原因・対策 を 3 段落で書く
3. 本ファイルに追記
4. Golden Template を直せる罠なら Template も更新

同じ罠で二度時間を溶かさないため、辞書化のコストは常に払う。
