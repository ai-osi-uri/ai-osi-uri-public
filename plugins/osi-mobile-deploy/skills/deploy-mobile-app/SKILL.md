---
name: deploy-mobile-app
description: |
  AI OSI URI が Cowork から **ネイティブモバイルアプリ（iOS = SwiftUI / Android =
  Kotlin + Jetpack Compose）を新規に作って TestFlight / Google Play Internal Track
  まで配信する** ための唯一のオーケストレータスキル。**既定スタックはネイティブ 2 本立てで、
  Flutter / React Native は greenfield では選ばない**（既存 Flutter アプリからの移行が
  必要な場合のみ `flutter-swift-parity-port` を別途使う）。「モバイルアプリ作って」
  「iOS アプリ作りたい」「Android アプリを立ち上げて」「SwiftUI で ○○ アプリ」
  「Kotlin Compose で作って」「TestFlight に上げるところまでやって」「ネイティブアプリ
  新規作成」「iPhone アプリ作って」「Play Store に出したい」「iOS も Android も両方
  作って」「Flutter じゃなくてネイティブでモバイルアプリを作って」など、モバイルアプリの
  新規作成と配信を依頼されたときに必ず発動する。既存モバイルリポの局所修正は
  `mobile-update-deploy` の役割で、本スキルは新規作成専用。Web / LP / SaaS の作成は
  `deploy-app`（osi-deploy）の担当。
version: 0.2.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
  - server: cowork
    provision: builtin
  - server: computer-use
    provision: builtin
  - server: ai-osi-uri-creative
    provision: user-install
---

# deploy-mobile-app — モバイルアプリ新規作成オーケストレータ

「モバイルアプリ作って」と言われたら、業種・機能・iOS/Android の希望を聞き出して、
Golden Template（SwiftUI + Jetpack Compose のネイティブ 2 本立て）から新規リポを起こし、
Firebase プロビジョニング・Secrets 投入・CI 監視・TestFlight / Play Internal Track 到達
まで **1 つの対話で完結**させる。

> **重要な設計原則**：本スキルは「判断・順序制御・引き渡し・監視」に専念する。実際の
> scaffold / Firebase / Secrets / icon / deploy は atomic スキル（`mobile-*` / `ios-*` /
> `android-*`）に委譲する。単一責任を守ることで、途中失敗しても再開できる。

> **スタック方針**：AI OSI URI の新規モバイルアプリは **iOS = SwiftUI / Android =
> Kotlin + Jetpack Compose** を既定とする。Flutter / React Native は greenfield では
> 選ばない。ユーザーが明示的に「Flutter で作って」と要望した場合は、既定がネイティブで
> ある旨と（採用したい強い事情があるかを）確認し、既存 Flutter アプリからの移行なら
> `flutter-swift-parity-port` に案内する。新規で Flutter を選ぶ強い事情がなければ
> ネイティブで進める。詳細は `mobile-app-scaffold/SKILL.md` の「方針」節を参照。

---

## ハーネス: 状態ログと DoD（必須）

`{OUTPUTS}/mobile-deploy-progress.md` を作成し、各フェーズの完了時に evidence 付きで更新。
セッションが切れても再開できるように「唯一の進捗の正典」を持つ。

```markdown
# Mobile Deploy Progress — {APP_NAME}
更新: {YYYY-MM-DD HH:MM}

## 確定事項
- App Name: {APP_NAME}
- Bundle ID (iOS): {BUNDLE_ID}
- Package Name (Android): {PACKAGE_NAME}
- Targets: {iOS / Android / both}
- Stack: SwiftUI + Jetpack Compose (AI OSI URI 既定 — Flutter は不使用)
- GitHub Org: {ai-osi-uri | personal}
- Firebase Project: {project_id}

## 完了（evidence 付き）
- [x] Phase 0 認証確認 — evidence: health_check 成功一覧
- [x] Phase 1 ヒアリング — evidence: 上記「確定事項」
- [x] Phase 2 scaffold — evidence: repo URL + commit sha
- [x] Phase 3 Firebase — evidence: project_id + app_id (iOS/Android)
- [x] Phase 4 icons — evidence: 生成した密度別ファイル数
- [x] Phase 5 secrets — evidence: 投入した secret 名リスト
- [x] Phase 6 CI green (iOS) — evidence: run_id + conclusion=success
- [x] Phase 7 CI green (Android) — evidence: run_id + conclusion=success
- [x] Phase 8 smoke test — evidence: simctl / adb 起動ログ

## 進行中 / ブロック中
- （なし）

## TestFlight / Play リンク
- TestFlight: {link}
- Play Internal: {link}
```

**DoD**: TestFlight / Play Internal Track の URL を提示していい条件 =
`ios_get_status` / `android_get_status` で processing 完了ビルドの ID が取れて、
かつスモークテストで crash していないこと。それ以前に「配信完了しました」と
ユーザーに言わない（early victory declaration の防止）。

---

## Phase 0: 認証・接続の確認

1. `health_check` を呼び、以下がすべて OK であることを確認:
   - `github.valid: true`
   - `firebase.valid: true`（Google 認証 or Service Account）
   - iOS 配信をするなら App Store Connect API Key（Keychain の `APP_STORE_CONNECT_API_KEY_ID` 等）
   - Android 配信をするなら Google Play Service Account JSON
2. Keychain の secrets を `security find-generic-password -s <name> -a "$USER" -w` で読めるか確認:

    ```
    iOS 用 (7 個):
      APPLE_TEAM_ID
      APP_STORE_CONNECT_API_KEY_ID
      APP_STORE_CONNECT_API_KEY_ISSUER_ID
      APP_STORE_CONNECT_API_KEY_B64
      IOS_DIST_CERT_P12_B64
      IOS_DIST_CERT_PASSWORD
      IOS_KEYCHAIN_PASSWORD

    Android 用 (5 個):
      ANDROID_KEYSTORE_B64
      ANDROID_KEYSTORE_PASSWORD
      ANDROID_KEY_ALIAS
      ANDROID_KEY_PASSWORD
      GOOGLE_PLAY_SERVICE_ACCOUNT_JSON
    ```

3. 不足があればユーザーに登録コマンドを案内して停止:

    ```
    security add-generic-password -U -s "APPLE_TEAM_ID" -a "$USER" -w "24X327Z9SJ"
    ```

    ループしない・見切り発車しない。登録完了を待ってから Phase 1 へ。

---

## Phase 1: ヒアリング（不足分だけ聞く）

ユーザーの初発入力から次の項目を読み取り、埋まらない部分だけ AskUserQuestion で 1〜2 問に絞って聞く。

| 項目 | 例 | デフォルト |
|---|---|---|
| APP_NAME | `Foo` / `MustPost` | 必須（推測しない） |
| APP_DESCRIPTION | `メモを記録するアプリ` | 「Hello World デモ」 |
| CORE_FEATURES | `写真を投稿できる / 位置情報を保存` | `Hello World`（空） |
| TARGETS | `iOS only` / `Android only` / `both` | `both` |
| STACK | 既定は **iOS = SwiftUI / Android = Kotlin + Jetpack Compose**。Flutter は聞かない | ネイティブ 2 本立て |
| BUNDLE_ID | `com.aiosiuri.foo` | `com.aiosiuri.{app_name_lower}` |
| PACKAGE_NAME | `com.aiosiuri.foo` | Bundle ID と同じ |
| DISPLAY_NAME | `Foo` | APP_NAME をそのまま |
| GITHUB_ORG | `ai-osi-uri` / `personal` | `deploy-app` の `USE_ORG` 判定に準拠 |
| ICON_SOURCE | 1024x1024 PNG / 画像URL / なし（nano-banana で生成） | なし |

**「Flutter で作って」と要望が来たとき**:
1. AI OSI URI の既定スタックがネイティブ 2 本立てで、実運用（MustPost 移植）で
   得た結論に基づくものであることを説明
2. 既存 Flutter アプリからの移行なら `flutter-swift-parity-port` を案内
3. 新規で Flutter を採用したい強い理由（例：既存の Flutter プラグイン資産、チームの
   Flutter 熟練度、社外の Flutter エコシステム上に SDK が乗る要件など）があるかを 1 問確認
4. 強い理由が無ければネイティブで進める。ある場合は本スキルの対象外として halt し
   ユーザー判断を仰ぐ（本プラグインは Flutter の scaffold は持たない）

**確認プロンプト例**:

```
以下でよろしいですか？

  アプリ名: Foo
  スタック: SwiftUI (iOS) + Jetpack Compose (Android)   ← AI OSI URI 既定のネイティブ 2 本立て
  Bundle ID: com.aiosiuri.foo
  Package Name: com.aiosiuri.foo
  ターゲット: iOS + Android
  リポ配置先: github.com/ai-osi-uri/foo
  アイコン: 仮ロゴ（nano-banana 自動生成）→ 後で差し替え可能
  Firebase: 新規プロジェクト `foo-dev` を作成

修正点があれば教えてください。この構成で進めるなら「OK」でどうぞ。
```

---

## Phase 2: mobile-app-scaffold を呼ぶ

Golden Template（SwiftUI + Jetpack Compose）から新規リポを生成し、GitHub に push する。

```
mobile-app-scaffold:
  app_name: {APP_NAME}
  bundle_id: {BUNDLE_ID}
  package_name: {PACKAGE_NAME}
  display_name: {DISPLAY_NAME}
  targets: {ios|android|both}
  github_org: {ai-osi-uri|personal}
```

戻り値: `repo_url`, `repo_owner`, `repo_name`, `local_clone_dir`, `initial_commit_sha`。

**冪等ガード**: 同名リポが既にあれば `mobile-update-deploy` に切り替えるか確認する
（勝手に上書きしない）。

---

## Phase 3: mobile-firebase-setup を呼ぶ

Firebase プロジェクトをプロビジョニングし、plist / json を GitHub Secrets に投入する。

```
mobile-firebase-setup:
  app_name: {APP_NAME}
  bundle_id: {BUNDLE_ID}
  package_name: {PACKAGE_NAME}
  targets: {ios|android|both}
  repo_owner: {repo_owner}
  repo_name: {repo_name}
  environment: dev   # v1 は dev のみ。stg/prod は後追い
```

戻り値: `firebase_project_id`, `ios_app_id`, `android_app_id`, `secrets_injected`（true）。

**注意**:
- Firebase プロジェクト作成は非同期。10〜30 秒ポーリング。
- iOS/Android 両方追加した場合、それぞれで plist/json を取得して両方 Secrets へ。
- `REVERSED_CLIENT_ID` は初期は空でよい（Google Sign-In を後で入れる場合の準備）。

---

## Phase 4: mobile-icon-generator を呼ぶ

アイコンを AppIcon / mipmap 全 density に配置する。

```
mobile-icon-generator:
  work_dir: {local_clone_dir}
  source_png: {ICON_SOURCE or null}   # null なら nano-banana で生成
  app_name: {APP_NAME}
  targets: {ios|android|both}
```

戻り値: `generated_files: [...]`, `used_source: nano-banana|user-provided`。

---

## Phase 5: mobile-secrets-sync を呼ぶ

Keychain から secrets を読み、GitHub リポに投入する。

```
mobile-secrets-sync:
  repo_owner: {repo_owner}
  repo_name: {repo_name}
  targets: {ios|android|both}
```

戻り値: `secrets_set: [...]`, `secrets_skipped: [...]`, `warnings: [...]`。

**注意**:
- MCP に `github_secrets_set` は無い。REST API 経由（`PUT /repos/{owner}/{repo}/actions/secrets/{name}`）
  で libsodium sealed box 暗号化して投入する。詳細は `mobile-secrets-sync/SKILL.md`。
- 直接 API が難しい場合は Chrome MCP でブラウザ経由 fallback（詳細は同スキル参照）。

---

## Phase 6-7: CI 監視 + 自動修正ループ（iOS / Android）

Phase 2〜5 で push されたコミットが CI を走らせる。iOS ワークフロー
（`.github/workflows/ios-release-auto.yml`）と Android ワークフロー
（`android-release-auto.yml`）を並行監視する。

### 監視手順（各ターゲットで）

1. `github_fetch` で `repos/{owner}/{repo}/actions/runs?per_page=5` を取得
2. 対応する run（`head_sha == initial_commit_sha` かつ workflow_name が対象）を特定
3. 30 秒ごとにポーリング → `status=completed` かつ `conclusion=success` で ✅
4. `conclusion=failure` なら次の Step へ

### 自動修正ループ（最大 3 回）

1. `github_fetch` で失敗した job の logs を取得
2. `references/ci-failure-patterns.md` と照合（正規表現マッチ）
3. マッチしたら該当ファイルを Edit ツールで修正
4. `github_push` で再 push
5. 新しい run を検知して手順 3 に戻る
6. 3 回試して直らなければユーザーに丸ごとログを提示して停止

### 既知の失敗パターン

`references/ci-failure-patterns.md` にすべて。特に頻出:

- `${FLAVOR^}: bad substitution` → bash 3.2 対応の `case` 文に置換
- `ITMS-90426 (SwiftSupport missing)` → ipa 再 zip 時に SwiftSupport 保全
- `Missing required icon file (120x120)` → xcrun actool で Assets.car 自前コンパイル
- `AuthKey_XXX.p8 not found` → altool は `AuthKey_<ID>.p8` 命名必須
- `Firebase not configured crash` → AppDelegate で `FirebaseApp.app() != nil` guard
- `Invalid URL scheme (empty REVERSED_CLIENT_ID)` → 空の URL scheme を Info.plist から削除
- `Font registration failed` → Info.plist の `UIAppFonts` をコメントアウト

---

## Phase 8: mobile-app-smoke-test を呼ぶ

Simulator / Emulator で起動確認する。

```
mobile-app-smoke-test:
  work_dir: {local_clone_dir}
  targets: {ios|android|both}
  wait_seconds: 5
```

戻り値: `ios_launched: bool`, `android_launched: bool`, `ios_crash_log`, `android_crash_log`。

クラッシュがあれば `mobile-crash-triage` を呼んで原因分析（自動修正はしない・提案まで）。

---

## Phase 9: 完了レポート

> **DoD ゲート**: Phase 6, 7, 8 の evidence をすべて `mobile-deploy-progress.md` に貼ってから本レポートを出す。
> 未検証項目があるなら `未検証: ◯◯` と明記する。

```
🎉 モバイルアプリ作成完了

【リポジトリ】
  https://github.com/{repo_owner}/{repo_name}

【スタック】
  iOS: SwiftUI (deployment target iOS 16+)
  Android: Kotlin + Jetpack Compose (minSdk 26)

【配信先】
  📱 TestFlight: {link}   （processing 完了まで通常 10〜30 分）
  🤖 Play Internal Track: {link}

【Firebase】
  プロジェクト: {firebase_project_id}
  iOS App: {ios_app_id}
  Android App: {android_app_id}

【次にやること】
  1. TestFlight で自分のデバイスにインストールして動作確認
  2. Play Console → 内部テスト → テスターに自分を追加してインストール
  3. アイコンを差し替えたい → 「Foo のアイコンをこの画像に差し替えて」
  4. 機能追加は「Foo に ○○ 機能を足して」（mobile-update-deploy が発動）
```

---

## エラーハンドリング

| Phase | 失敗 | 対応 |
|---|---|---|
| 0 | Keychain に secret がない | 登録コマンドを案内、中断 |
| 0 | `firebase.valid: false` | Google 認証 or Service Account 設定を案内、中断 |
| 1 | APP_NAME が読み取れない | 「アプリ名は何にしますか？（英数字、例: Foo）」で 1 問だけ聞く |
| 1 | 「Flutter で作って」と要望された | 既定がネイティブである旨と、既存 Flutter アプリからの移行かを確認。新規で Flutter を選ぶ強い事情が無ければネイティブで進める。強い事情があるなら本プラグインの対象外として halt |
| 2 | 同名リポあり | 「既存のを更新しますか？（mobile-update-deploy へ）」で確認 |
| 3 | Firebase プロジェクト作成失敗（quota 超過） | 既存プロジェクトを指定できるか確認 |
| 5 | Secrets 投入失敗（REST API 401） | GitHub PAT の scope 不足 → 案内 |
| 6-7 | 自動修正ループが 3 回失敗 | 最後のログを提示して停止、ユーザー判断待ち |
| 8 | Simulator/Emulator が起動しない | `xcrun simctl list` / `emulator -list-avds` で診断案内 |

---

## やってはいけないこと

- **新規で Flutter / React Native を採用する**：本プラグインの既定はネイティブ 2 本立て。
  強い事情がある場合はユーザーに明示確認し、無ければネイティブで進める
- **早期の「完了」宣言**：CI が green になっただけで「TestFlight に上がりました」と言わない。
  `ios_get_status` で processing 完了ビルドの ID が取れるまで待つ。
- **既存リポの上書き**：同名リポがあれば新規作成せず、`mobile-update-deploy` に切り替え確認。
- **Bundle ID の自動生成で `com.example.*` を使う**：App Store Connect には登録できない。必ず `com.{org}.{app}` 形式で。
- **Firebase の URL scheme をユーザー確認なしに Info.plist へ追加**：空の `REVERSED_CLIENT_ID` を入れると起動時にクラッシュする。Google Sign-In を明示的に追加する時だけ入れる。
- **CI 失敗時に log を読まずに再 push**：pattern マッチせずに闇雲に push すると無限ループする。3 回失敗したら止まる。

---

## 関連スキル

- `mobile-app-scaffold` — Phase 2 で呼ぶ（SwiftUI + Compose の Golden Template）
- `mobile-firebase-setup` — Phase 3 で呼ぶ
- `mobile-icon-generator` — Phase 4 で呼ぶ
- `mobile-secrets-sync` — Phase 5 で呼ぶ
- `mobile-app-smoke-test` — Phase 8 で呼ぶ
- `mobile-crash-triage` — smoke test が失敗した時に呼ぶ
- `mobile-update-deploy` — 既存リポの局所修正（本スキルの範疇外）
- `ios-testflight-deploy` — 実配信の詳細ノウハウ（fastlane / altool の癖）
- `android-play-deploy` — 実配信の詳細ノウハウ（Gradle / bundletool / Play API）
- `flutter-swift-parity-port` — 既存 Flutter アプリの SwiftUI 移行時のみ（本スキルは呼ばない）
