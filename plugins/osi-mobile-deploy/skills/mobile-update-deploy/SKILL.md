---
name: mobile-update-deploy
description: |
  既存のネイティブモバイルアプリを修正して再配信する（修正 → push → CI 監視 →
  TestFlight / Play Internal 到達確認）。「モバイルアプリの○○を直して」「iOS
  の文言を修正して再配信」「Android の crash を直して」
  「既存モバイルアプリに機能を足して」で発動する。新規作成は `deploy-mobile-app`、Web
  は `update-deploy`（osi-deploy）。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
  - server: cowork
    provision: builtin
  - server: computer-use
    provision: builtin
---

# mobile-update-deploy — 既存モバイルアプリを更新するオーケストレータ

Web 版 `update-deploy` と同じ思想。新規作成ではなく、既にある GitHub リポ + TestFlight /
Play Internal Track を、ローカル修正 → push → CI 自動修正ループ → 実配信確認まで貫通する。

## いつ発動するか

- 「モバイルの ○○ 直して」「iOS の文言修正して」「Android の crash を直して」
- 「TestFlight に新しいビルド上げて」「Play Internal に再配信」
- 既に公開済みのモバイルリポを編集したい全シナリオ

新規モバイルアプリを 0 から作る依頼は `deploy-mobile-app` を使うこと。

## ハーネス（必須）

`{OUTPUTS}/mobile-update-progress.md` を作成し、各フェーズの結果を evidence 付きで貼る。
DoD: TestFlight / Play Internal のビルド ID が processing 完了ステータスで取れるまで
「配信完了」と報告しない。

---

## Phase 0: 認証・接続の確認

Web 版 `update-deploy` と同じ:

1. `health_check` で `github.valid: true` / `firebase.valid: true`
2. Keychain の secrets（`APPLE_TEAM_ID` / `APP_STORE_CONNECT_API_KEY_ID` / `ANDROID_KEYSTORE_PASSWORD` etc.）が読めるか確認
3. 不足があれば登録コマンドを案内して halt

---

## Phase 1: 対象リポ特定

自由文から:

| 項目 | 抽出例 |
|---|---|
| `repo_owner` | `ai-osi-uri` |
| `repo_name` | `mustpost-native` |
| `platform` | iOS / Android / both |
| `bundle_id` / `package_name` | ローカル repo の `project.yml` / `build.gradle.kts` から抽出 |

ローカルに clone があるか確認（既定: `~/projects/{repo_name}`）。無ければ Web 版と同じ手順で
ユーザーのターミナルに `gh repo clone` を投入 → `mcp__cowork__request_cowork_directory` で
フォルダをマウント。

---

## Phase 2: pull で最新化

Web 版と同じ Cowork sandbox 制約に注意:

- サンドボックスから `git fetch/pull/clone` は認証で必ず落ちる
- ユーザーのターミナルで `gh` を実行してもらう（コマンドは `write_clipboard` で投入）
- `github_push` は拡張の PAT で通る

Step 2-1〜2-3 は Web 版 SKILL の相当節と同じロジック（remote 再追加、`--ff-only` pull、
dirty check）を踏襲する。

---

## Phase 3: 修正対象の特定と編集

### 不具合タイプの推定（モバイル特有）

| タイプ | 典型シグナル | 探索ヒント |
|---|---|---|
| 文言・翻訳 | 「タイトル変更」「日本語ミス」 | `Localizable.strings` / `strings.xml` / Swift ソース内の String literal |
| クラッシュ | 「起動しない」「落ちる」 | まず `mobile-crash-triage` を呼んで原因特定してから |
| UI 微調整 | 「色変えて」「パディング直して」 | `AppColors.swift` / `AppSpacing.swift` / `themes.xml` |
| Firebase 設定 | 「plist 差し替え」「app id 変えて」 | `Resources/GoogleService-Info-Dev.plist` を `mobile-firebase-setup` で再生成 |
| deps 追加 | 「Google Sign-In 入れて」 | `project.yml` (SPM) / `libs.versions.toml` (Gradle) |
| CI/CD 修正 | 「fastlane で失敗する」 | `.github/workflows/*.yml` / `fastlane/Fastfile` |

### 修正適用

Edit ツールで局所修正。原則:

- 1 ファイル 1 関数の最小変更
- クラッシュ修正の場合は `mobile-crash-triage` の提案通りに直す
- 変更が複数ファイルにまたがるなら diff サマリを `mobile-update-progress.md` に書く

### ローカル sanity check

```bash
# iOS
cd apps/ios && xcodegen generate && xcodebuild -project MyApp.xcodeproj -scheme MyApp -destination 'generic/platform=iOS' -showBuildSettings >/dev/null

# Android
cd apps/android && ./gradlew tasks --no-daemon | head -20
```

エラーが出ても続行可能。CI で最終確認する（自動修正ループ込み）。

---

## Phase 4: push → CI 自動デプロイ

### Step 4-0: pre-push hygiene（Web 版と同じ）

`.git/*.lock` の退避 → 空コミット回避 → github_push。詳細は
`osi-deploy/skills/update-deploy/SKILL.md` の Phase 4-0 参照（同じロジック）。

### Step 4-1: github_push

```
mcp__AI_OSI_URI_Deploy__github_push:
  work_dir: {local_clone_dir}
  repo_owner: {repo_owner}
  repo_name: {repo_name}
  commit_message: "fix: <要約> (mobile-update-deploy)"
```

### Step 4-2: CI 監視 + 自動修正ループ

`deploy-mobile-app` の Phase 6-7 と同じロジックを再利用。iOS/Android どちらか（or 両方）の
workflow を監視し、失敗したら `deploy-mobile-app/references/ci-failure-patterns.md` と
照合して auto-fix push。最大 3 回。

### Step 4-3: TestFlight / Play Internal Track 到達確認

CI green だけでは不十分。実配信が完了したかを別途確認する:

```
# iOS: App Store Connect API から build を pull
ios_get_status({
  bundle_id: "{bundle_id}",
  limit: 3
})
  → 直近ビルドの processing_state が "PROCESSING" or "VALID" になっているか
  → head_sha に紐づくビルドか確認（build number で照合）

# Android: Play Publisher API から version_code を pull
android_get_status({
  package_name: "{package_name}",
  track: "internal"
})
  → 最新の version_code が push 後のものか確認
```

**processing 完了まで通常 10〜30 分**。5分ごとにポーリング、30分でタイムアウト。
タイムアウトしたら `未検証（processing 中）` として正直に報告する。

---

## Phase 5: 検証（DoD ゲート）

| 検証項目 | 方法 | 合格条件 |
|---|---|---|
| コミット一致 | `git rev-parse HEAD` ↔ CI run の `head_sha` | 完全一致 |
| CI green | GitHub Actions API | conclusion=success |
| TestFlight 到達 | `ios_get_status` | 該当ビルドが VALID |
| Play Internal 到達 | `android_get_status` | 該当 version_code が internal track に存在 |
| smoke test | `mobile-app-smoke-test` | crash なしで launch |

evidence を全て `mobile-update-progress.md` に貼ってから完了報告。

---

## Phase 6: 完了報告

```
✓ mobile-update-deploy 完了

リポ: https://github.com/{repo_owner}/{repo_name}
コミット: {short_sha} "{commit_message}"
プラットフォーム: {ios / android / both}

変更ファイル: {N} 件
  - apps/ios/{APP_NAME}/Features/HomeView.swift（コピー修正）
  - apps/android/app/src/main/res/values/strings.xml（同期修正）

配信状況:
  📱 TestFlight ビルド {build_number}: VALID
  🤖 Play Internal Track version_code {code}: available

検証:
  - コミット一致: ✓
  - CI green: ✓ (workflow_run {run_id})
  - smoke test: ✓ (crash なし)

次のアクション:
  TestFlight でテスターに配布 or Play Console で内部テスターに配布
```

---

## エラーハンドリング

| Phase | 失敗 | 対応 |
|---|---|---|
| 0 | Keychain 不足 | 登録コマンド案内、halt |
| 1 | repo 特定できない | ユーザーに repo URL を直接聞く |
| 2 | clone が dirty | `--force` しない、確認 |
| 3 | 該当箇所が複数 | 全箇所を提示し選んでもらう |
| 4 | index.lock | Web 版 Phase 4-0 と同じ hygiene |
| 4 | CI が 3 回失敗 | 最後のログを提示、halt |
| 4-3 | 30 分待っても processing 完了せず | 「未検証」と正直に報告、Apple 側の delay の可能性を案内 |
| 5 | smoke test 失敗 | `mobile-crash-triage` を呼ぶ |

---

## やってはいけないこと

- **既存 TestFlight ビルドを force-upload しない**（build number 衝突で App Store Connect が拒否する）。fastlane が build number を自動 increment する仕組みに任せる。
- **CI green で「配信完了」と言わない**。TestFlight processing が終わるまで待つ。processing 中はビルドがまだ配布不可。
- **Play の production track に勝手に promote しない**。本番昇格は `android_promote` MCP で明示的に指示された時だけ。
- **リポの Bundle ID / Package Name を局所修正で変えない**。変えたい場合は Apple Developer / Firebase 側の再登録が必要 → `deploy-mobile-app` で新規リポを立てるほうが安全。

---

## 関連スキル

- `deploy-mobile-app` — 新規モバイルアプリ作成（既存リポなしならこちら）
- `mobile-app-scaffold` — 新規リポ作成 atomic
- `mobile-crash-triage` — Phase 3 の前に crash 原因を特定する
- `mobile-app-smoke-test` — Phase 5 で呼ばれる
- `ios-testflight-deploy` — Apple 側の詳細ノウハウ
- `android-play-deploy` — Google 側の詳細ノウハウ
