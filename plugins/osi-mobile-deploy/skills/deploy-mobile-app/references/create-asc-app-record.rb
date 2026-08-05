#!/usr/bin/env ruby
# create-asc-app-record.rb
#
# osi-mobile-deploy の Phase 0（手順）で flavor ごとに叩くヘルパー。
# → Apple Developer Portal の Bundle ID を登録（無ければ）
# → App Store Connect の App 記録の存在を確認し、無ければ Web UI に誘導する
#
# Bundle ID の作成は普通の API キー（App Manager role）でも可能。
# App 記録作成は Admin role 必須で、失敗した場合は Web UI を人に使わせる。
#
# Usage:
#   export ASC_KEY_ID="$(security find-generic-password -s APP_STORE_CONNECT_API_KEY_ID -a $USER -w)"
#   export ASC_ISSUER_ID="$(security find-generic-password -s APP_STORE_CONNECT_API_KEY_ISSUER_ID -a $USER -w)"
#   export ASC_P8_B64="$(security find-generic-password -s APP_STORE_CONNECT_API_KEY_B64 -a $USER -w)"
#   export TARGET_BUNDLE_ID="com.aiosiuri.mustpost.prod"
#   export TARGET_BUNDLE_NAME="MustPost Prod"
#   export TARGET_APP_NAME="MustPost"
#   export TARGET_SKU="mustpost-prod-2026"
#   export TARGET_PRIMARY_LOCALE="ja"
#   bundle exec ruby scripts/create-asc-app-record.rb

require "spaceship"
require "base64"

key_id     = ENV.fetch("ASC_KEY_ID")
issuer_id  = ENV.fetch("ASC_ISSUER_ID")
p8_b64     = ENV.fetch("ASC_P8_B64")
p8         = Base64.strict_decode64(p8_b64)

bundle_id_str  = ENV.fetch("TARGET_BUNDLE_ID")
bundle_name    = ENV.fetch("TARGET_BUNDLE_NAME", bundle_id_str)
app_name       = ENV["TARGET_APP_NAME"]        # nil なら App 作成をスキップ
app_sku        = ENV["TARGET_SKU"]
primary_locale = ENV["TARGET_PRIMARY_LOCALE"] || "ja"

puts "→ Authenticating to App Store Connect API..."
token = Spaceship::ConnectAPI::Token.create(
  key_id: key_id, issuer_id: issuer_id, key: p8,
)
Spaceship::ConnectAPI.token = token

# --- Step 1: Bundle ID ---
puts "→ Checking Bundle ID #{bundle_id_str}..."
bundle = Spaceship::ConnectAPI::BundleId
  .all(filter: { identifier: bundle_id_str })
  .find { |b| b.identifier == bundle_id_str }

if bundle
  puts "✅ Bundle ID exists: #{bundle.id}"
else
  puts "→ Creating Bundle ID..."
  begin
    bundle = Spaceship::ConnectAPI::BundleId.create(
      name: bundle_name,
      identifier: bundle_id_str,
      platform: "IOS",
      seed_id: nil,
    )
    puts "✅ Bundle ID created: #{bundle.id}"
  rescue Spaceship::AccessForbiddenError => e
    warn "❌ Bundle ID creation forbidden (API key role too low): #{e.message}"
    warn "   Web UI: https://developer.apple.com/account/resources/identifiers/list"
    exit 1
  end
end

# --- Step 2: ASC App record ---
if app_name.nil? || app_name.empty?
  puts "ℹ️  TARGET_APP_NAME not set — skipping App record check"
  exit 0
end

puts "→ Checking ASC App record for #{bundle_id_str}..."
app = Spaceship::ConnectAPI::App.find(bundle_id_str)

if app
  puts "✅ App record on ASC: #{app.id} — #{app.name}"
  puts ""
  puts "次にやること: git push で CI を回す"
  exit 0
end

puts "→ App record missing — attempting to create via API (needs Admin role)..."
begin
  new_app = Spaceship::ConnectAPI::App.create(
    name: app_name,
    version_string: "1.0",
    sku: app_sku || bundle_id_str.gsub(".", "-"),
    primary_locale: primary_locale,
    bundle_id: bundle_id_str,
    platforms: ["IOS"],
  )
  puts "✅ App record created: #{new_app.id} — #{new_app.name}"
rescue Spaceship::AccessForbiddenError => e
  puts "⚠️  App record on ASC: MISSING (API key role too low to create)"
  puts ""
  puts "   Web UI に移動して手動作成が必要:"
  puts "   https://appstoreconnect.apple.com/apps/new/app"
  puts ""
  puts "   Platforms:        iOS"
  puts "   Name:             #{app_name}"
  puts "   Primary Language: 日本語 (#{primary_locale})"
  puts "   Bundle ID:        #{bundle_id_str}"
  puts "   SKU:              #{app_sku || bundle_id_str.gsub(".", "-")}"
  puts "   User Access:      Full Access"
  puts ""
  puts "   作成後に本スクリプトを再実行すると OK 確認できる。"
  puts "   API キーを Admin role で発行し直すと以降自動化可能（セキュリティ上の判断）。"
  exit 2
end
