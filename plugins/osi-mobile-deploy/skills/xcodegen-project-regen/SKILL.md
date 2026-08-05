---
name: xcodegen-project-regen
description: |
  xcodegen 管理の iOS プロジェクトで、pull 後に「Missing package product
  'FirebaseCore'」「Cannot find 'Firebase' in scope」等が束で出るときの修復。原因は
  stale .xcodeproj で、project.yml から再生成し Package Cache を reset する。
  「xcodeproj が壊れた」「pull したらビルドできない」「SPM の product が見つからない」
  「Unable to find module dependency: FirebaseFunctions」「Debug-Dev で build する」
  で発動する。
version: 0.2.0
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

または Swift 側で:

```
Unable to find module dependency: 'FirebaseFunctions'
Unable to find module dependency: 'FirebaseAuth'
Unable to find module dependency: 'FirebaseStorage'
Unable to find module dependency: 'FirebaseRemoteConfig'
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
mcp__AI_OSI_URI_Deploy__xcode_regenerate_project({
  project_dir: "/Users/…/mustpost-native/apps/ios"
})

mcp__AI_OSI_URI_Deploy__xcode_resolve_packages({
  project: "/Users/…/mustpost-native/apps/ios/MustPost.xcodeproj",
  scheme: "MustPost-Dev"
})
```

---

## 大罠 1: configuration 名は "Debug-Dev" — 単純 "Debug" は壊れる

xcodegen が `configurations: [Debug, Release] × configVariants: [Dev, Stg, Prod]` を
組み合わせて **`Debug-Dev` / `Debug-Stg` / `Debug-Prod` / `Release-Dev` / ...** を
生成する。scheme の buildConfiguration もこの合成名を指す:

```bash
grep buildConfiguration apps/ios/MustPost.xcodeproj/xcshareddata/xcschemes/*.xcscheme
# → buildConfiguration = "Debug-Dev"
```

にもかかわらず `xcode_build_for_sim` に `configuration: "Debug"` を渡すと:

- main target は `Debug-Dev-iphonesimulator/` に build product を落とす
- SPM の resource bundles (`nanopb_nanopb.bundle` 等) は `Debug-iphonesimulator/` に落ちる
- Copy Files step が `Debug-Dev-iphonesimulator/` から拾おうとして **ENOENT で fail**
- しかも `.app` のガワは生成されてしまうが、中身が空（Frameworks/ に何も無い、
  executable も無い）で **install できても launch で即死する**

**必ず scheme の buildConfiguration と一致させる**:

```
mcp__AI_OSI_URI_Deploy__xcode_build_for_sim({
  scheme: "MustPost-Dev",
  configuration: "Debug-Dev"      # ← "Debug" ではなく必ずこれ
})
```

### 破損したビルドの検出

```bash
APP=$(find ~/Library/Developer/Xcode/DerivedData -name 'MustPost.app' -path '*Debug-Dev-iphonesimulator*' | head -1)
ls -la "$APP"
# 期待: MustPost (executable) + Frameworks/ 配下に .framework 多数 + Info.plist + PkgInfo
# 破損: plist しか無い / Frameworks/ が空 / MustPost binary が無い → configuration 名を疑う
```

---

## 大罠 2: DerivedData を rm -rf すると Index.noindex で ENOTEMPTY

APFS の `Index.noindex/DataStore/v5/records/` は `rm -rf` で **ENOTEMPTY** を返す
（プレフィックス衝突する tmp file を APFS が clone している影響）。

```bash
rm -rf ~/Library/Developer/Xcode/DerivedData/MustPost-abc123
# → rm: /.../Index.noindex/DataStore/v5/records: Directory not empty
```

**対処**: `find -delete` を使う（bottom-up で削除するので tmp との衝突が起きない）:

```bash
find ~/Library/Developer/Xcode/DerivedData/MustPost-abc123 -delete
```

MCP の `xcode_wipe_derived_data` も内部で ENOTEMPTY を返すことがある。fallback:

```
mcp__AI_OSI_URI_Deploy__mac_shell({
  cmd: "find",
  args: ["/Users/…/Library/Developer/Xcode/DerivedData/MustPost-abc123", "-delete"]
})
```

---

## 大罠 3: SPM cache 破損 → resolvePackageDependencies は 2 回試行

`~/Library/Caches/org.swift.swiftpm/` や `SourcePackages/checkouts/` が中途半端に
壊れると:

```
the package manifest at '.../SourcePackages/checkouts/GoogleSignIn-iOS/Package.swift'
cannot be accessed (Package.swift doesn't exist in file system)
```

or

```
error: input file '.../SourcePackages/checkouts/firebase-ios-sdk/Package.swift'
was modified during the build
```

**対処**: 2 回試行する。1 回目は checkout が競合するが、2 回目でクリーンに完走する
ことが多い:

```
# 1 回目
mcp__AI_OSI_URI_Deploy__xcode_resolve_packages({...})
# → 失敗しても

# 2 回目
mcp__AI_OSI_URI_Deploy__xcode_resolve_packages({...})
# → 成功する
```

それでもだめなら SPM cache を完全 wipe:

```bash
rm -rf ~/Library/Caches/org.swift.swiftpm/
find ~/Library/Developer/Xcode/DerivedData/MustPost-* -delete
xcodegen generate --spec apps/ios/project.yml
```

そのあと `xcode_resolve_packages` を 2 回。

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
5. Cmd+B (configuration は Debug-Dev / Debug-Stg / Debug-Prod のいずれかを選ぶ、
   単純 Debug は選べない)
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
find ~/Library/Developer/Xcode/DerivedData/MustPost-* -delete
rm -rf ~/Library/Caches/org.swift.swiftpm/

xcodegen generate --spec apps/ios/project.yml

# Xcode で再解決させる（2 回）
xcodebuild -resolvePackageDependencies \
  -project apps/ios/MustPost.xcodeproj \
  -scheme MustPost-Dev
# → 1回目失敗しても
xcodebuild -resolvePackageDependencies \
  -project apps/ios/MustPost.xcodeproj \
  -scheme MustPost-Dev
# → 2回目で通る
```

---

## 検証

```bash
# 1. project.yml と xcodeproj が同期していることを確認
xcodegen generate --spec apps/ios/project.yml
# → "Warning: Regenerating..." が出なければ既に同期済み。

# 2. scheme が指す configuration 名を確認
grep buildConfiguration apps/ios/MustPost.xcodeproj/xcshareddata/xcschemes/*.xcscheme
# → "Debug-Dev" / "Release-Dev" 等が並ぶ

# 3. build settings を確認（Package products が解決されているか）
xcodebuild -project apps/ios/MustPost.xcodeproj \
  -scheme MustPost-Dev \
  -configuration Debug-Dev \
  -showBuildSettings 2>&1 | grep -i firebase | head -5
# → FirebaseCore などの参照が出れば OK

# 4. 実ビルドで .app が中身付きで生成されるか
APP=$(find ~/Library/Developer/Xcode/DerivedData -name 'MustPost.app' -path '*Debug-Dev-iphonesimulator*' | head -1)
ls -la "$APP" | wc -l
# → 20+ (executable, Frameworks/, plist, PkgInfo 等が揃う) なら OK
# → 5-6 (plist だけ) なら configuration 名間違いを疑う
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
| `rm -rf DerivedData/MustPost-*` で ENOTEMPTY | `find <path> -delete` に切り替え |
| `resolvePackageDependencies` が "Package.swift was modified during the build" | もう一度そのまま実行（2 回目で通る） |
| .app は生成されるが Frameworks/ が空 | `configuration: "Debug"` を渡している。`"Debug-Dev"` に変更 |
| `Unable to find module dependency: FirebaseFunctions` | DerivedData wipe + xcodegen regen + resolvePackages 2 回、config 名も確認 |

---

## 関連スキル

- `mobile-app-scaffold` — Golden Template 生成時に xcodegen を焼き込む
- `mobile-update-deploy` — pull → build → push の Phase 3 で本 skill を先頭に呼ぶ
- `ios-testflight-deploy` — Fastfile で `xcodegen generate` を lane の 1 発目に置く
- `ios-sim-auth-backdoor` — Sim ビルド前に xcodeproj が最新であることが前提。configuration 名は本 skill 参照
- `mobile-app-smoke-test` — スモーク前提として project 再生成が必要
