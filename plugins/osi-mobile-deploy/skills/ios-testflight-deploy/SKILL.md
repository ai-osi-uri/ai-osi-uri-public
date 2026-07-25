---
name: ios-testflight-deploy
description: |
  fastlane + altool で iOS ビルドを TestFlight にアップロードする atomic スキル。
  osi-mobile-deploy の Golden Template に焼き込まれた「今日獲得したノウハウ全部入り」の
  fastlane / GitHub Actions workflow を実行する。SwiftSupport 保全（ITMS-90426 回避）、
  xcrun actool による Assets.car 自前コンパイル、AuthKey_<ID>.p8 命名規約、
  pilot polling スキップ、CFBundleIconName + CFBundleIcons 設定、Xcode 26 選択、
  bash 3.2 互換の case 文、といった落とし穴回避を「なぜそれが必要か」まで
  references/altool-quirks.md に残す。単体で「TestFlight に上げて」「iOS を再配信」で発動する。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# ios-testflight-deploy — iOS TestFlight 配信の詳細ノウハウ

Golden Template には既に「動く形」で焼き込み済み。本スキルは:

1. 実行の入り口（fastlane lane を叩く）
2. ノウハウの根拠と「なぜこう書くか」の説明（references/ 配下）

の 2 つを担う。**同じ罠で二度時間を溶かさない**ためのナレッジ層。

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `work_dir` | ✅ | モバイルリポの絶対パス |
| `flavor` | 任意 | `dev` / `stg` / `prod`（既定: `dev`） |
| `notes` | 任意 | TestFlight の what-to-test メモ |

## 実行モード

### モード A: ローカル Mac で fastlane を直叩き

```bash
cd "$WORK_DIR"

# Keychain から secrets を env に展開
export APPLE_TEAM_ID="$(security find-generic-password -s APPLE_TEAM_ID -a "$USER" -w)"
export APP_STORE_CONNECT_API_KEY_ID="$(security find-generic-password -s APP_STORE_CONNECT_API_KEY_ID -a "$USER" -w)"
export APP_STORE_CONNECT_API_KEY_ISSUER_ID="$(security find-generic-password -s APP_STORE_CONNECT_API_KEY_ISSUER_ID -a "$USER" -w)"

# .p8 を AuthKey_<ID>.p8 という命名で置く（altool の必須命名）
mkdir -p ~/private_keys
security find-generic-password -s APP_STORE_CONNECT_API_KEY_B64 -a "$USER" -w \
  | base64 --decode > ~/private_keys/AuthKey_${APP_STORE_CONNECT_API_KEY_ID}.p8
export APP_STORE_CONNECT_API_KEY_PATH=~/private_keys/AuthKey_${APP_STORE_CONNECT_API_KEY_ID}.p8

# fastlane 実行
bundle install --quiet
bundle exec fastlane ios ios_beta_auto flavor:"${FLAVOR:-dev}" notes:"${NOTES:-}"
```

このモードは Mac local で完結。CI が調子悪い時のリカバリ用途にも使う。

### モード B: GitHub Actions で走らせる（既定）

`.github/workflows/ios-release-auto.yml` は push で自動起動する構成。何もせずに
`git push origin main` するだけ。CI 監視は `deploy-mobile-app` / `mobile-update-deploy`
が行う。

## fastlane lane の中身（`fastlane/Fastfile` の `ios_beta_auto`）

Golden Template に焼き込み済み。要点:

```ruby
lane :ios_beta_auto do |options|
  flavor = options[:flavor] || "dev"
  configuration = { "dev" => "Release-Dev", "stg" => "Release-Stg", "prod" => "Release-Prod" }.fetch(flavor)
  app_id        = APP_ID_BY_FLAVOR.fetch(flavor)
  api_key       = load_app_store_connect_api_key!

  # 1. xcodegen で .xcodeproj を再生成（ソース追加漏れの防止）
  Dir.chdir("apps/ios") { sh "xcodegen generate" }

  # 2. build number を Apple 側の最大値 + 1 に
  latest = latest_testflight_build_number(app_identifier: app_id, api_key: api_key, initial_build_number: 0)
  increment_build_number(xcodeproj: "apps/ios/MyApp.xcodeproj", build_number: (latest.to_i + 1).to_s)

  # 3. archive + export（Automatic Signing）
  gym(
    project: "apps/ios/MyApp.xcodeproj",
    scheme:  "MyApp",
    configuration: configuration,
    clean:   true,
    export_method: "app-store",
    output_directory: "build/ios/ipa",
    output_name: "MyApp-#{flavor}.ipa",
    xcargs: "-allowProvisioningUpdates DEVELOPMENT_TEAM=#{ENV.fetch('APPLE_TEAM_ID')}",
  )

  # 4. Assets.car が Payload に入っているかを検証。無ければ actool で自前コンパイル
  ensure_assets_car_in_payload!(ipa: "build/ios/ipa/MyApp-#{flavor}.ipa")

  # 5. pilot で TestFlight upload。polling はスキップ（時間の無駄）
  pilot(
    api_key: api_key,
    app_identifier: app_id,
    ipa: "build/ios/ipa/MyApp-#{flavor}.ipa",
    skip_waiting_for_build_processing: true,
    changelog: options[:notes],
    distribute_external: false,
  )
end
```

## `ensure_assets_car_in_payload!` の中身

```ruby
def ensure_assets_car_in_payload!(ipa:)
  Dir.mktmpdir do |tmp|
    sh "unzip -q '#{ipa}' -d '#{tmp}'"
    app_dir = Dir["#{tmp}/Payload/*.app"].first
    unless File.exist?("#{app_dir}/Assets.car")
      UI.important "Assets.car missing — recompiling"
      partial = "#{tmp}/AssetsInfo.plist"
      sh "xcrun actool --compile '#{app_dir}' --platform iphoneos " \
         "--minimum-deployment-target 17.0 --app-icon AppIcon " \
         "--output-partial-info-plist '#{partial}' " \
         "apps/ios/MyApp/Resources/Assets.xcassets"
    end
    # 旧命名の AppIcon60x60@2x.png / @3x.png も Payload 直下にコピー（iOS 26 の validation 対策）
    ["120", "180"].each do |px|
      src = "apps/ios/MyApp/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-#{px}.png"
      dst = "#{app_dir}/AppIcon60x60#{px == '120' ? '@2x' : '@3x'}.png"
      FileUtils.cp(src, dst) if File.exist?(src) && !File.exist?(dst)
    end
    # 再 zip（ditto を使わないと SwiftSupport が壊れる → ITMS-90426）
    FileUtils.rm(ipa)
    sh "cd '#{tmp}' && zip -qry '#{ipa}' Payload SwiftSupport 2>/dev/null || " \
       "cd '#{tmp}' && zip -qry '#{ipa}' Payload"
  end
end
```

より安全なのは `ditto -c -k --sequesterRsrc --keepParent`。`references/altool-quirks.md` 参照。

## 戻り値

```json
{
  "build_number": "42",
  "upload_status": "uploaded",
  "processing": true,
  "app_store_connect_url": "https://appstoreconnect.apple.com/apps/.../testflight/ios"
}
```

## エラーハンドリング

`references/altool-quirks.md` に典型症状と対処を全部並べている。頻出は以下:

| 症状 | 対処 |
|---|---|
| `ITMS-90426 SwiftSupport missing` | ditto で再 zip（unzip → zip すると死ぬ） |
| `Missing required icon file` | actool で Assets.car を自前生成、legacy PNG も併置 |
| `AuthKey_XXX.p8 not found` | ファイル名を `AuthKey_${KEY_ID}.p8` にする |
| `Cannot find provisioning profile` | `xcargs: "-allowProvisioningUpdates"` を追加、または Developer Portal で App ID を事前登録 |
| `Build number already used` | fastlane の `latest_testflight_build_number` で自動 increment（既に組み込み済み） |

## 注意事項

- **pilot の polling をスキップする**。processing 完了まで 10〜30 分待つのは無駄。upload だけしてすぐ抜ける。processing 完了確認は `ios_get_status` で別途行う。
- **App Store review 提出は本スキルの範疇外**。`ios_submit_review` MCP で明示的に指示された時だけ。
- **flavor 3 種類（dev/stg/prod）を最初から用意**。BundleID を分けることで Firebase / TestFlight を並行運用できる。v1 は dev のみ実運用、stg/prod は Golden Template に entry として残しつつ運用開始は案件が本番化したタイミング。
- **CI で走らせる時の provisioning は Automatic**（`match` を使わない）。証明書は Distribution 1 枚を Keychain / GitHub Secrets 経由で流し込む。`match` を後で入れたくなった時は明示的に切り替える。
