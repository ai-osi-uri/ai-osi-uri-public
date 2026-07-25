---
name: android-play-deploy
description: |
  Gradle + bundletool + Google Play Publisher API v3 で Android AAB を Play Console の
  Internal Track にアップロードする atomic スキル。osi-mobile-deploy の Golden Template に
  焼き込まれた `.github/workflows/android-release-auto.yml` + `fastlane/Fastfile` の
  `android_beta_auto` lane を実行する。keystore の base64 復元、`versionCode` の自動増分、
  Play Publisher API 認証、track=internal upload、bundletool でのローカル検証、を扱う。
  トラック昇格（internal → alpha → production）は `android_promote` MCP で明示的に指示された
  時のみ実行する。単体で「Play Internal に上げて」「Android を再配信」で発動する。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# android-play-deploy — Android Google Play Internal Track 配信

Golden Template の Fastfile / workflow に「動く形」で焼き込み済み。本スキルは:

1. 実行の入り口
2. Play Publisher API の癖と対策のノウハウ

を担う。

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `work_dir` | ✅ | モバイルリポの絶対パス |
| `flavor` | 任意 | `dev` / `stg` / `prod`（既定: `dev`） |
| `track` | 任意 | `internal` / `alpha` / `beta` / `production`（既定: `internal`） |
| `rollout_fraction` | 任意 | `production` 昇格時のみ意味を持つ（既定: 0.1 = 10%） |

## 実行モード

### モード A: ローカル Mac で fastlane を直叩き

```bash
cd "$WORK_DIR"

# Keychain から secrets を env に展開
export ANDROID_KEYSTORE_PASSWORD="$(security find-generic-password -s ANDROID_KEYSTORE_PASSWORD -a "$USER" -w)"
export ANDROID_KEY_ALIAS="$(security find-generic-password -s ANDROID_KEY_ALIAS -a "$USER" -w)"
export ANDROID_KEY_PASSWORD="$(security find-generic-password -s ANDROID_KEY_PASSWORD -a "$USER" -w)"

# keystore を base64 から復元
security find-generic-password -s ANDROID_KEYSTORE_B64 -a "$USER" -w \
  | base64 --decode > /tmp/release.keystore
export ANDROID_KEYSTORE_PATH=/tmp/release.keystore

# Service Account JSON を復元
security find-generic-password -s GOOGLE_PLAY_SERVICE_ACCOUNT_JSON -a "$USER" -w \
  > /tmp/play-sa.json
export GOOGLE_PLAY_JSON_KEY_PATH=/tmp/play-sa.json

# fastlane 実行
bundle install --quiet
bundle exec fastlane android android_beta_auto flavor:"${FLAVOR:-dev}"
```

### モード B: GitHub Actions で走らせる（既定）

`.github/workflows/android-release-auto.yml` は push で自動起動する。何もせずに
`git push origin main`。CI 監視は `deploy-mobile-app` / `mobile-update-deploy` が行う。

## fastlane lane の中身（`fastlane/Fastfile` の `android_beta_auto`）

```ruby
lane :android_beta_auto do |options|
  flavor = options[:flavor] || "dev"
  variant_name = "#{flavor.capitalize}Release"     # DevRelease / StgRelease / ProdRelease

  # 1. keystore.properties を書き出す
  File.write("apps/android/keystore.properties", <<~PROPS)
    storeFile=#{ENV.fetch("ANDROID_KEYSTORE_PATH")}
    storePassword=#{ENV.fetch("ANDROID_KEYSTORE_PASSWORD")}
    keyAlias=#{ENV.fetch("ANDROID_KEY_ALIAS")}
    keyPassword=#{ENV.fetch("ANDROID_KEY_PASSWORD")}
  PROPS

  # 2. Play Console 上の最新 versionCode を取得して +1
  latest = google_play_track_version_codes(
    package_name: PACKAGE_NAME_BY_FLAVOR.fetch(flavor),
    track:        "internal",
    json_key:     ENV.fetch("GOOGLE_PLAY_JSON_KEY_PATH"),
  ).max || 0
  next_code = latest + 1
  sh "sed -i.bak 's/versionCode = [0-9]*/versionCode = #{next_code}/' apps/android/app/build.gradle.kts"

  # 3. AAB build
  gradle(
    project_dir: "apps/android",
    tasks:       ["bundle#{variant_name}"],
    print_command: false,
  )
  aab_path = "apps/android/app/build/outputs/bundle/#{flavor}Release/app-#{flavor}-release.aab"

  # 4. bundletool でローカル検証（オプション、時間かかるならスキップ可）
  # sh "bundletool validate --bundle #{aab_path}"

  # 5. Play Publisher API で internal track へ upload
  upload_to_play_store(
    package_name:            PACKAGE_NAME_BY_FLAVOR.fetch(flavor),
    aab:                     aab_path,
    track:                   "internal",
    json_key:                ENV.fetch("GOOGLE_PLAY_JSON_KEY_PATH"),
    release_status:          "draft",
    skip_upload_metadata:    true,
    skip_upload_changelogs:  false,
    skip_upload_images:      true,
    skip_upload_screenshots: true,
  )
end

lane :android_promote_internal_to_production do |options|
  fraction = (options[:rollout_fraction] || "0.1").to_f
  upload_to_play_store(
    package_name:      PACKAGE_NAME_BY_FLAVOR.fetch("prod"),
    track:             "internal",
    track_promote_to:  "production",
    rollout:           fraction.to_s,
    json_key:          ENV.fetch("GOOGLE_PLAY_JSON_KEY_PATH"),
    skip_upload_aab:   true,
    skip_upload_apk:   true,
    skip_upload_metadata: true,
    skip_upload_changelogs: true,
    skip_upload_images: true,
    skip_upload_screenshots: true,
  )
end
```

## bundletool でローカル検証

Play にアップロードする前に、AAB が壊れていないかを bundletool でチェック:

```bash
# AAB → apks (universal) 変換
bundletool build-apks --bundle=app-release.aab --output=/tmp/app.apks --mode=universal
# extract して adb install で emulator に流す
```

`mobile-app-smoke-test` はこの `/tmp/app.apks` から取り出した universal APK を install する
オプションを持つ（v1 は debug APK 前提だが、AAB 経路が要る案件では有効化）。

## 戻り値

```json
{
  "version_code": 42,
  "track": "internal",
  "upload_status": "uploaded",
  "play_console_url": "https://play.google.com/console/u/0/developers/.../app/{app_id}/tracks/internal-testing"
}
```

## エラーハンドリング

| 症状 | 対処 |
|---|---|
| `Google Play Console API access denied` | Service Account が Play Console の対象アプリに access 権限を持っていない → Play Console → API access → SA を招待、権限「Release manager」以上 |
| `You cannot rollout this release because it does not allow any existing users to upgrade` | `versionCode` が前と同じ or 小さい → 自動 increment の実装バグ、`google_play_track_version_codes` の戻り値を確認 |
| `Certificate fingerprint mismatch` | keystore が Play Console 側の app signing key と食い違い → 初回登録時の keystore を使うか、Play App Signing を使っているなら upload key 差し替え申請 |
| `Missing dSYM / mapping.txt for Crashlytics` | `firebase-crashlytics-gradle` プラグインを有効化していれば自動 upload。手動する場合は `firebase crashlytics:symbols:upload` |
| `Play Publisher: 400 The APK is not signed with the upload certificate` | Play App Signing 未有効。Play Console → App integrity → 有効化 |

## 注意事項

- **`release_status: "draft"` を既定にする**。draft ならユーザー確認後に Play Console 側で
  「レビューへ送信」を人が押す運用。auto-release だと事故る。
- **本番昇格（production track）は autoスキルでは絶対にしない**。`android_promote` MCP で
  明示指示された時だけ `android_promote_internal_to_production` lane を叩く。
- **バージョンコードは monotonically increasing**。debug と release で衝突しないよう
  Golden Template では debug は `applicationIdSuffix = ".debug"` で分離済み。
- **AAB は Play 経由でしか install できない**（本番配布）。emulator 検証は debug APK で。
- **Play App Signing の upload key と app signing key**: 初回は同じでよい。key rotation の
  ときだけ「Play にある app signing key を jarsigner で export」→ 再署名の手順が必要。
