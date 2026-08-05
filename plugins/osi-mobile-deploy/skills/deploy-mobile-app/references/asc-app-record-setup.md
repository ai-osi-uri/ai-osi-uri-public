# App Store Connect ・ Apple Developer Portal の事前登録

iOS の flavor（`dev` / `stg` / `prod`）ごとに、**Apple Developer Portal の Bundle ID**
と **App Store Connect の App 記録**の両方が必要。片方でも欠けると `fastlane`
（`get_provisioning_profile` / `pilot` / `altool`）が失敗する。**これは CI が始まる**
**前に人が確認するべき pre-flight**（deploy-mobile-app Phase 0）。

> **なぜ Golden Template だけでは不足するか**：Golden Template は「ソース + workflow」
> は用意するが、Apple の Developer Portal / App Store Connect は Apple の管理面。API
> キーの role が Admin でないと App 記録は作れず、キー発行者が自分でやる必要がある。

---

## MustPost で実際に踏んだ罠（2026-08-05）

**症状**：Prod flavor で TestFlight ワークフローが 37 秒で失敗:

```
[!] Could not find App with App Identifier ''com.aiosiuri.mustpost.prod''
fastlane finished with errors
```

**原因**：Prod flavor 用の Bundle ID `com.aiosiuri.mustpost.prod` が
Apple Developer Portal に登録されていなかった（Dev flavor `com.aiosiuri.mustpost.dev`
は登録済みで動いていた）。App Store Connect 側の App 記録も未作成。

**教訓**：**flavor を追加した瞬間に Bundle ID + App 記録を作る**。
CI が動く直前に「App 記録あるだろう」で走らせない。

---

## 事前登録チェックリスト（flavor ごと）

flavor を有効化する **前に** 次の 2 つを確認する。

### ✅ 1. Apple Developer Portal — Bundle ID 登録

**Web UI**：https://developer.apple.com/account/resources/identifiers/list
→ 「+」→ App IDs → App → Continue
→ Description: `MustPost Prod`（人が読める名前、後で変えられる）
→ Bundle ID: Explicit → `com.aiosiuri.mustpost.prod`
→ Capabilities：**この時点では最小限**（Push / IAP / Sign in with Apple 等は後で追加可能）
→ Continue → Register

**確認コマンド（Spaceship 経由）**：

```bash
bundle exec ruby -r spaceship -e ''
  Spaceship::ConnectAPI.token = Spaceship::ConnectAPI::Token.create(
    key_id: ENV["ASC_KEY_ID"], issuer_id: ENV["ASC_ISSUER_ID"],
    key: Base64.strict_decode64(ENV["ASC_P8_B64"]))
  b = Spaceship::ConnectAPI::BundleId.all(filter: { identifier: "com.aiosiuri.mustpost.prod" }).first
  puts b ? "OK: #{b.id}" : "MISSING"
''
```

### ✅ 2. App Store Connect — App 記録作成

**Web UI**：https://appstoreconnect.apple.com/apps → 「+」→ New App
→ Platforms: iOS
→ Name: `MustPost`（ユーザ表示名。既存アプリと衝突しないこと）
→ Primary Language: 日本語 (Japanese)
→ Bundle ID: `com.aiosiuri.mustpost.prod`（step 1 で登録した ID をプルダウンから選ぶ）
→ SKU: 案件横断でユニークな任意文字列（例: `mustpost-prod-2026`）
→ User Access: Full Access
→ Create

**この画面が必須なのは、API キーが Admin role でない場合**。App Store Connect の
`POST /v1/apps` は Admin role 必須で、Developer role や App Manager role のキーでは
`403 FORBIDDEN` になる（fastlane `spaceship` 経由も同じ）。

**確認コマンド**：

```bash
bundle exec ruby -r spaceship -e ''
  Spaceship::ConnectAPI.token = Spaceship::ConnectAPI::Token.create(
    key_id: ENV["ASC_KEY_ID"], issuer_id: ENV["ASC_ISSUER_ID"],
    key: Base64.strict_decode64(ENV["ASC_P8_B64"]))
  app = Spaceship::ConnectAPI::App.find("com.aiosiuri.mustpost.prod")
  puts app ? "OK: #{app.id} — #{app.name}" : "MISSING"
''
```

---

## 半自動化スクリプト（Bundle ID は API で・App は Web UI で）

**Bundle ID の作成は API キーの role に関わらず動く**ので、可能な限り自動化する。
App Store Connect の App 記録作成は Admin role が必須なので、Web UI で人がやる。

本 references の隣に置いてある `create-asc-app-record.rb` を叩く:

```bash
cd <mobile-repo>
export ASC_KEY_ID="$(security find-generic-password -s APP_STORE_CONNECT_API_KEY_ID -a $USER -w)"
export ASC_ISSUER_ID="$(security find-generic-password -s APP_STORE_CONNECT_API_KEY_ISSUER_ID -a $USER -w)"
export ASC_P8_B64="$(security find-generic-password -s APP_STORE_CONNECT_API_KEY_B64 -a $USER -w)"
export TARGET_BUNDLE_ID="com.aiosiuri.mustpost.prod"
export TARGET_BUNDLE_NAME="MustPost Prod"
bundle exec ruby scripts/create-asc-app-record.rb
```

出力:

```
✅ Bundle ID com.aiosiuri.mustpost.prod (id=VC537CXA23) registered/exists
⚠️  App record on ASC: MISSING
    → Web UI に移動して手動作成が必要:
       https://appstoreconnect.apple.com/apps/new/app
       Name: MustPost, Bundle ID: com.aiosiuri.mustpost.prod, SKU: mustpost-prod-2026
```

App 記録作成後に再実行すると:

```
✅ Bundle ID com.aiosiuri.mustpost.prod (id=VC537CXA23) registered/exists
✅ App record on ASC: 6801234567 — MustPost

次にやれること: git push で ios-release-auto.yml を回す
```

---

## deploy-mobile-app Phase 0 への組み込み

`deploy-mobile-app/SKILL.md` の Phase 0（認証・接続の確認）で、iOS を配信する場合は
**flavor ごとに** 次を確認する:

1. Bundle ID が Developer Portal に登録されているか → Spaceship で確認
2. App 記録が App Store Connect にあるか → Spaceship で確認

どちらかが欠けている場合は本 references の手順を提示して halt。CI を走らせない。

---

## FAQ

**Q: 全部 API 化できないの？**  
A: Bundle ID 登録は API で全自動化可能。App 記録作成だけ Admin role 必須で、通常の
API キー（App Manager role で証明書・プロビジョニング・アップロードは足りる）では
弾かれる。Admin role のキーを新しく作るのはセキュリティリスクなので、App 記録は
人がやる想定（1 flavor で 1 回きり）。

**Q: dev / stg / prod 全部 App 記録要る？**  
A: **要る**。TestFlight でグループ分けする運用でも、Bundle ID が違えば別 App 扱い。
MustPost は dev のみ動かしていたが、prod TestFlight を配りたくなった瞬間に本問題を踏む。

**Q: App Store 申請前でも App 記録は作れる？**  
A: 作れる。App 記録を作った時点では審査に出ない。TestFlight のみに配布可能。
審査提出は `ios_submit_review` MCP で明示的にやる（`ios-appstore-release` の担当）。

**Q: Bundle ID の名前を後で変えられる？**  
A: **変えられない**（削除・再作成しかない）。TestFlight の履歴・レビュー・IAP は
Bundle ID に紐づく。`com.example.myapp` を絶対に本番で使わない、`com.aiosiuri.*`
か `com.<org>.<app>` で確定させてから登録すること。

**Q: 既に App Store で公開中のアプリの flavor（`.dev`）を追加したい**  
A: 全く別 App として登録する。Prod（無サフィックス）と Dev（`.dev`）は Firebase / TestFlight /
App Store で完全に独立して並行運用できる。ASC 上の App 名は `MustPost` / `MustPost Dev` のように
分けると管理しやすい。
