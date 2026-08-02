---
name: xcodegen-project-regen
description: |
  xcodegen 管理の iOS プロジェクトで、pull 後に「Missing package product
  'FirebaseCore'」「Cannot find 'Firebase' in scope」等が束で出るときの修復。原因は
  stale .xcodeproj で、project.yml から再生成し Package Cache を reset する。
  「xcodeproj が壊れた」「pull したらビルドできない」「SPM の product が見つからない」
  で発動する。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# xcodegen-project-regen — stale .xcodeproj を xcodegen で 1 発で直す

## 症状

`git pull` 直後、ローカルで Xcode を開いてビルドすると:

```
Missing package product 'FirebaseCore'
Missing package product 'FirebaseAuth'
Missing package product 'FirebaseFirestore'
Missing package product 'FirebaseMessaging'
Missing package product 'FirebaseStorage'
Missing package product 'GoogleSignIn'
Missing package product 'FirebaseFunctions'
... (14個くらい束で)
```

CI では通っているのに、ローカルだけ落ちる。あるいは他の同僚は普通に動く。

## 原因

`project.yml` (xcodegen の spec) と `.xcodeproj` の食い違い。xcodegen パイプラインでは:

1. **正**: `project.yml`
2. **derived**: `.xcodeproj` （xcodegen が生成）

`.xcodeproj` は `.gitignore` に入っていない or 一部だけ ignore されていて、
`project.yml` が更新されると `.xcodeproj` の SwiftPM 参照セクションが古いままになる。
これで「SwiftPM から見て product は存在するのに、xcodeproj が product を知らない」
状態になる。

## 対処（30 秒）

```bash
cd /Users/…/mustpost-native
xcodegen generate --spec apps/ios/project.yml
```

これで `apps/ios/MustPost.xcodeproj/project.pbxproj` が最新化される。

その後 Xcode 側:

1. Xcode を開く: `open apps/ios/MustPost.xcodeproj`
2. **File → Packages → Reset Package Caches**（`~/Library/Caches/org.swift.swiftpm/` をクリア）
3. **File → Packages → Resolve Package Versions**（`Package.resolved` を再生成）
4. Cmd+B でビルド

MCP から:

```
mcp__AI_OSI_URI_Deploy__mac_shell({
  cmd: "xcodegen",
  args: ["generate", "--spec", "apps/ios/project.yml"],
  cwd: "/Users/…/mustpost-native"
})

mcp__AI_OSI_URI_Deploy__xcode_resolve_packages({
  work_dir: "/Users/…/mustpost-native",
  project_relative: "apps/ios/MustPost.xcodeproj",
  clean_cache: true
})
```

---

## 予防（推奨: onboarding + pre-build hook）

### 1. `.gitignore` を厳密にする

```gitignore
# apps/ios/.gitignore
MustPost.xcodeproj/         # 完全に derived。全部 ignore
!MustPost.xcodeproj/xcshareddata/xcschemes/*.xcscheme  # scheme だけは保持 (fastlane 用)

*.xcworkspace/xcuserdata/
xcuserdata/
DerivedData/
build/
```

`project.pbxproj` を Git に残す運用と混ぜない：xcodegen で管理するなら
**derived として ignore**、CI で毎回 `xcodegen generate` する。

### 2. fastlane / CI で必ず `xcodegen generate` を先に

```ruby
# fastlane/Fastfile
lane :ios_beta_auto do |options|
  # 1. Regenerate .xcodeproj from project.yml (Prevents stale-project drift).
  Dir.chdir("apps/ios") { sh "xcodegen generate" }

  # 2. archive + export
  gym(...)
end
```

GitHub Actions workflow でも:

```yaml
- name: Install XcodeGen
  run: brew install xcodegen

- name: XcodeGen — regenerate project
  working-directory: apps/ios
  run: xcodegen generate
```

### 3. Onboarding docs に必ず入れる

新しく repo を clone した人向けの `docs/ios-setup.md` に:

```markdown
1. `brew install xcodegen`
2. `cd apps/ios && xcodegen generate`
3. `open MustPost.xcodeproj`
4. File → Packages → Resolve Package Versions
5. Cmd+B
```

を書く。この 5 手順を守れば SPM 系のエラーはまず出ない。

### 4. `mobile-app-scaffold` にも組み込む

Golden Template から新規リポを起こす scaffold は既に `xcodegen generate` を焼き込むが、
本 skill の onboarding step を README に自動生成させると新規メンバーの詰まりが減る。

---

## 深い症状: `Package.resolved` mismatch

`xcodegen generate` で解決しない場合は、`Package.resolved` が原因かも:

```bash
# 消して再解決
rm -rf apps/ios/MustPost.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved
rm -rf ~/Library/Developer/Xcode/DerivedData/MustPost-*
rm -rf ~/Library/Caches/org.swift.swiftpm/

xcodegen generate --spec apps/ios/project.yml

# Xcode で再解決させる
xcodebuild -resolvePackageDependencies \
  -project apps/ios/MustPost.xcodeproj \
  -scheme MustPost
```

これで SwiftPM が最新の version を再取得する。

---

## 検証

```bash
# 1. project.yml と xcodeproj が同期していることを確認
xcodegen generate --spec apps/ios/project.yml
# → "Warning: Regenerating..." が出なければ既に同期済み。
#   ファイルが更新されていたら未同期だった、ということ。

# 2. build settings を確認（Package products が解決されているか）
xcodebuild -project apps/ios/MustPost.xcodeproj \
  -scheme MustPost \
  -showBuildSettings 2>&1 | grep -i firebase | head -5
# → FirebaseCore などの参照が出れば OK
```

---

## エラーハンドリング

| 症状 | 追加対処 |
|---|---|
| xcodegen not found | `brew install xcodegen` |
| project.yml の validation error | `xcodegen dump --spec apps/ios/project.yml` で構造を確認 |
| package resolution が hang | `~/Library/Caches/org.swift.swiftpm/` を消してリトライ |
| CI で失敗するがローカルは OK | CI の xcodegen version と macOS runner の Xcode version を確認。特に Xcode 16→26 移行時 |
| `xcodegen generate` は成功するが Missing package product が消えない | `Package.resolved` を削除して Xcode 再起動 → Resolve Packages |
| Xcode 側で「Package.resolved is out of date」 | 上と同じ。resolved を削除 |
| CocoaPods と SPM 混在で衝突 | `Podfile` を消して SPM 一本化。MustPost は SPM 専用 |

---

## 関連スキル

- `mobile-app-scaffold` — Golden Template 生成時に xcodegen を焼き込む
- `mobile-update-deploy` — pull → build → push の Phase 3 で本 skill を先頭に呼ぶ
- `ios-testflight-deploy` — Fastfile で `xcodegen generate` を lane の 1 発目に置く
- `ios-sim-auth-backdoor` — Sim ビルド前に xcodeproj が最新であることが前提
