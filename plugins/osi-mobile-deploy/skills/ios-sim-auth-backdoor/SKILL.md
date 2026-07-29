---
name: ios-sim-auth-backdoor
description: |
  iOS Simulator 上で Firebase Auth の keychain 永続化を成立させ、Google/Apple の SSO UI を
  経由せずに Claude / QA が「サインイン済み画面」まで到達できるようにする 2 本立てスキル。
  (a) MCP `xcode_build_for_sim` を **proper signing 既定**で叩き（`CODE_SIGNING_ALLOWED=NO`
  を注入しない）、entitlements を保った .app を作る。これで Firebase Auth の
  `errSecMissingEntitlement -34018` / 内部エラー 17995 (keychainError) が消える。
  (b) DEBUG ビルドに `mustpost://debug/signin?token=XXX` 形式のディープリンクバックドアを
  仕込み、IAM signJwt で発行した Firebase Custom Token を渡して
  `Auth.auth().signIn(withCustomToken:)` で即サインインさせる。AppDelegate と SwiftUI 側の
  `DeepLinkHandler` の**両方**にハンドラを置くのがミソ（SwiftUI の `.onOpenURL{}` は
  AppDelegate を経由しない）。「iOS Simulator でサインインできない」「keychainError -34018」
  「シミュレータでログイン画面を突破したい」「テスト用のバックドアを iOS に仕込みたい」
  「Firebase Custom Token でサインインさせて」「Sim で QA する導線」で発動する。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# ios-sim-auth-backdoor — Simulator で Firebase Auth を成立させる 2 本立て

iOS Simulator で「サインイン画面をタップで突破する」のは実は 2 つの独立した罠を同時に
踏んでいる。この skill はその両方に対して具体的な処方箋を渡す。

1. **keychain 罠**：Simulator 用 .app が code signing なしでビルドされていると
   `keychain-access-groups` entitlement が付かず、Firebase Auth が現行セッションを
   keychain に書き込めない（`errSecMissingEntitlement -34018` → FirebaseAuth 内部で
   17995 になる）。サインインは**サーバ側では成功しているのに**、ローカル永続化が
   失敗するので UI が「未サインイン」に戻ってしまう。
2. **入力罠**：Simulator の IME は Google Sign-In の web view と Apple Sign-In の
   認可 sheet を確実に扱えない（キーボード出ない・カーソル飛ぶ）。Claude 経由の
   `xcode_sim_tap` / `xcode_sim_type` では突破しきれないので、UI を経由しない
   サインイン導線 = **Custom Token deep link** を用意する。

これらは片方だけ直しても意味がない：keychain を直しても IME で入力できない、入力導線を
直しても keychain で落ちる。両方セットで潰す。

---

## 前提

- 拡張 `osi-mobile-deploy` MCP は **v1.18.5+**（`xcode_build_for_sim` に
  `code_signing: "auto"` 既定と `code_signing: "off"` オプトインが入ったバージョン）。
  それ未満は `xcodebuild` に `CODE_SIGNING_ALLOWED=NO` を無条件注入していたので必ず
  entitlements が落ちる。バージョン確認は `health_check` で見える。
- `firebase_auth_mint_custom_token` MCP が使える環境（GCP プロジェクトに IAM
  `iam.serviceAccountTokenCreator` を持っている GCP SA、または Application Default
  Credentials に Owner）。
- ローカルに Xcode.app が入っていて **一度は起動している** こと（Xcode を一度も
  起動していない Mac だと Automatic Signing の初期セットアップが未完了で
  entitlements が付かない）。

---

## Part A: proper signing で .app をビルドさせる

### 前提の確認

```
mcp__AI_OSI_URI_Deploy__health_check → mobile.mcp_version が "1.18.5" 以上
```

古い版で `xcode_build_for_sim` を叩くと内部で

```
xcodebuild ... CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY=""
```

が入り、`.app/Contents/embedded.mobileprovision` も entitlements も落ちる。
それだけで Firebase Auth は keychain に書けなくなる。

### ビルド

```
mcp__AI_OSI_URI_Deploy__xcode_build_for_sim({
  work_dir: "/Users/…/mustpost-native",
  project_relative: "apps/ios/MustPost.xcodeproj",
  scheme: "MustPost",
  configuration: "Debug-Dev",     # DEBUG フラグと DEV フラグが両方立つ config
  simulator: "iPhone 16",
  code_signing: "auto"            # ← 既定。明示するのが安全。
})
```

### entitlements の検証（毎回やる）

```bash
APP="$(find $WORK_DIR -name 'MustPost.app' -path '*Debug-iphonesimulator*' | head -1)"
xcrun codesign -d --entitlements :- "$APP" 2>&1 | head -40
```

**期待する出力**：

```xml
<plist>
  <dict>
    <key>application-identifier</key>
    <string>ABCD1234EF.com.aiosiuri.mustpost.dev</string>
    <key>keychain-access-groups</key>
    <array>
      <string>ABCD1234EF.*</string>
      ...
    </array>
    <key>com.apple.developer.team-identifier</key>
    <string>ABCD1234EF</string>
  </dict>
</plist>
```

`keychain-access-groups` が入っていれば OK。空の `<dict/>` しか出なければ signing が
外れている → MCP バージョンか Xcode 側の Automatic Signing 設定を疑う。

### Xcode 未起動 Mac のリカバリ

Automatic Signing は Xcode を一度起動しないと provisioning profile を作らない。
以下を 1 回だけ手で:

1. `open -a Xcode` （GUI を出す）
2. Xcode → Settings → Accounts で Apple ID にサインイン
3. `MustPost.xcodeproj` を開き、Signing & Capabilities → Team を選び直す
4. 一度普通にビルド（Cmd+B）

以降は `xcode_build_for_sim` が自動で profile を再生成できる。

---

## Part B: Custom Token deep link backdoor

### 1. トークンを発行（バックエンド側）

MCP から Firebase Auth の Custom Token を鋳造:

```
mcp__AI_OSI_URI_Deploy__firebase_auth_mint_custom_token({
  project_id: "mustpost-dev",
  uid: "<既存の Firebase Auth UID>",         # or 新規 UID を渡すと anonymous 化
  additional_claims: { "qa_backdoor": true }, # 任意。監査用
  expires_in_seconds: 3600
})
→ { token: "eyJhbGci..." }
```

**注意**：戻ってきた token は 1 時間で失効。使い捨てで OK。Custom Token は
`Auth.auth().signIn(withCustomToken:)` の一度で消費される。

### 2. アプリを起動して deep link を発火

```bash
xcrun simctl openurl booted "mustpost://debug/signin?token=eyJhbGci..."
```

MCP 経由なら:

```
mcp__AI_OSI_URI_Deploy__xcode_sim_open_url({
  udid: "booted",
  url: "mustpost://debug/signin?token=eyJhbGci..."
})
```

### 3. Info.plist（URL Types）

`mustpost` scheme はもう Google Sign-In のリバース ID とかで登録済みならそれで OK。
最低限これが必要（既存を壊さない前提で追加）:

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLName</key>
    <string>app.debug</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>mustpost</string>
    </array>
  </dict>
</array>
```

### 4. AppDelegate 側のハンドラ（必須）

`application(_:open:options:)` で `DEBUG || DEV` ガード付きで捕まえる。詳細な実装は
`references/deep-link-handler.swift` を参照。要点だけ:

```swift
#if DEBUG || DEV
if url.scheme == "mustpost", url.host == "debug", url.path == "/signin",
   let comps = URLComponents(url: url, resolvingAgainstBaseURL: false),
   let token = comps.queryItems?.first(where: { $0.name == "token" })?.value,
   !token.isEmpty {
    Task { @MainActor in
        try? await AuthService.shared.signInWithCustomToken(token)
    }
    return true
}
#endif
```

### 5. SwiftUI 側の DeepLinkHandler にも同じハンドラ（**忘れがち**）

SwiftUI の `.onOpenURL{ url in ... }` は AppDelegate を経由せず直接
`DeepLinkHandler` に飛ぶ経路があるので、そちらにも同じ判定を置く。**片方だけだと
「初回起動だけ動いて 2 回目から動かない」というフレーキーな挙動になる**。

### 6. AuthService 側の keychainError 対策

万一 signing が完璧でなくても、Firebase Auth の内部エラー 17995（keychainError）は
「サインイン自体は成功したが local persist で失敗」を意味する。soft-success として
扱い、`Auth.auth().currentUser` を見て state を確定させる:

```swift
private static func signInIgnoringKeychainError(_ op: () async throws -> AuthDataResult)
    async throws -> AuthDataResult?
{
    do {
        return try await op()
    } catch let error as NSError {
        // FirebaseAuth keychain error = 17995 / underlying macOS = -34018
        let isKeychain =
            error.code == 17995 ||
            (error.userInfo["NSUnderlyingError"] as? NSError)?.code == -34018 ||
            error.localizedDescription.lowercased().contains("keychain")
        if isKeychain {
            Logger.auth.warning("Sign-in threw keychain error but user may still be signed in; treating as soft success.")
            return nil
        }
        throw error
    }
}
```

Custom Token 用の DEBUG 呼び出しはこう:

```swift
#if DEBUG || DEV
@discardableResult
public func signInWithCustomToken(_ token: String) async throws -> AuthDataResult {
    let auth = try await Self.signInIgnoringKeychainError {
        try await Auth.auth().signIn(withCustomToken: token)
    }
    try? await refreshClaims(forceRefresh: true)
    if auth == nil {
        if Auth.auth().currentUser == nil {
            throw APIError.internalError("Sign-in failed and currentUser is nil")
        }
        return try await Auth.auth().signIn(withCustomToken: token)
    }
    return auth!
}
#endif
```

---

## 検証手順（毎回）

1. 拡張バージョン `mobile.mcp_version >= 1.18.5` を `health_check` で確認
2. `xcode_build_for_sim({code_signing: "auto"})` でビルド
3. `xcrun codesign -d --entitlements :- <.app>` で `keychain-access-groups` を目視
4. `firebase_auth_mint_custom_token` で token を発行
5. `xcode_sim_install_app` → `xcode_sim_launch_app`
6. `xcode_sim_open_url({url: "mustpost://debug/signin?token=..."})`
7. 5 秒待って `xcode_sim_describe_ui` で「サインイン済み画面」に居ることを確認
   （出力が巨大なので `xcode_sim_screenshot` → 目視のほうが早いこともある）

---

## エラーハンドリング

| 症状 | 原因の切り分け | 対処 |
|---|---|---|
| Deep link を叩いても何も起きない | AppDelegate ハンドラだけで SwiftUI 側に無い | `DeepLinkHandler.handleIncomingURL` にも `mustpost://debug/signin` の分岐を追加 |
| `errSecMissingEntitlement -34018` が Console.app に出る | signing が外れている | `xcrun codesign -d --entitlements` で確認、`code_signing: "auto"` で再ビルド |
| Custom Token が invalid | token 失効 or project mismatch | 発行 project_id と `GoogleService-Info-Dev.plist` の GCM_SENDER_ID を照合 |
| 17995 が返るが `Auth.auth().currentUser` が居る | keychain persist だけ失敗、サインイン自体は成功 | `signInIgnoringKeychainError` で soft-success 扱いすれば UI は動く |
| DEV ビルドでは動くが Release-Dev で動かない | `#if DEBUG` ガードが外れて deep link handler が実行時に入っていない | `#if DEBUG || DEV` に緩める（`DEV` は Release-Dev config でも立てる） |
| Google Sign-In のコールバックと競合する | `handleIncomingURL` の判定順が悪い | `GIDSignIn.sharedInstance.handle(url)` の**前に** debug 分岐で `return true` させる |

---

## セキュリティメモ

- **Release ビルドには絶対に入れない**。`#if DEBUG || DEV` ガードを二重に確認。
  `DEV` フラグは Release-Dev config でのみ立つ設計。Release-Prod では **立たない**。
- Custom Token は 1 時間で失効するが、それでも QA 用の UID 以外に対して発行しない。
- IAM `iam.serviceAccountTokenCreator` を持つ SA は絞る（QA 用の別 SA が理想）。
- CI 上に token を長期 secret として貯めない。**毎回 mint する**。

---

## 関連スキル

- `deploy-mobile-app` — Simulator QA が必要になる場面の親スキル
- `mobile-app-smoke-test` — 実際に Sim を叩くフロー（本 skill は事前準備）
- `ios-testflight-deploy` — 実機配信時にはこの backdoor は無関係（TestFlight は
  実機 keychain / provisioning profile で普通に動く）
