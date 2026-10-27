---
name: deploy-mobile-app
description: |
  ネイティブモバイルアプリ（iOS = SwiftUI / Android = Kotlin + Jetpack Compose）
  を新規に作って TestFlight / Google Play Internal Track
  まで配信するオーケストレータ。「モバイルアプリ作って」「iOS アプリ作りたい」
  「Android アプリを立ち上げて」「SwiftUI で○○」「Kotlin Compose で作って」「iPhone
  アプリ作って」「Play Store に出したい」「TestFlight に上げるところまでやって」
  で発動する。既定はネイティブ 2 本立て（新規で Flutter / React Native は選ばない）。
  既存リポの修正は `mobile-update-deploy`、Web / SaaS は `create-app`（osi-deploy）。
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
  - server: cowork
    provision: builtin
  - server: computer-use
    provision: builtin
  - server: ai-osi-uri-creative
    provision: user-install
# 手元が要る準備（get_skill が「手元の準備」の節を出す。導入手順は osi-core:local-setup）
local_setup: [ext-deploy, mac, android]
# スキルの一覧（つないだときに Claude に渡す）に出す短い用途
label: スマホアプリを新しく作る
---

# deploy-mobile-app — モバイルアプリ新規作成オーケストレータ

> **Git の道（2026-10-16）**：Git の push・取り込みは**手元の Deploy 拡張の道具（`github_push`・`github_clone`・`github_pull` など）が基本**（差分だけを送るので大きなリポジトリでも軽い）。
> 入っていなければ、先に入れる（get_skill の頭の「手元の準備」→ `local_tools_status` → 本人が「インストール」を1回押す）。
> 入れられない・断られたとき（ブラウザ版の Claude など）や小さなアプリだけ、URL でつなぐコネクタの `github_upload_url` → `github_push_folder` ／ `github_download_folder` を予備に使う
> （毎回フォルダ全体を zip で送るので 1 回 200MB まで）。手順は osi-deploy の update-deploy の `references/git-via-url-connector.md`。

> **組織固有値はプロファイルから読む。** 本文の `{{paths.*}}` `{{ledgers.*}}` `{{company.*}}` `{{members.*}}` は、連結フォルダ直下の `osi-profile.md`（雛形: `config/osi-profile.example.md`）の値に置き換えて解釈する。無ければ会社名・案件フォルダ・台帳の有無・使うコネクタを質問して先に作る。値をここに直書きしない。

「モバイルアプリ作って」と言われたら、業種・機能・iOS/Android の希望を聞き出して、
Golden Template（SwiftUI + Jetpack Compose のネイティブ 2 本立て）から新規リポを起こし、
Firebase プロビジョニング・Secrets 投入・CI 監視・TestFlight / Play Internal Track 到達
まで **1 つの対話で完結**させる。

> **重要な設計原則**：本スキルは「判断・順序制御・引き渡し・監視」に専念する。実際の
> scaffold / Firebase / Secrets / icon / deploy は atomic スキル（`mobile-*` / `ios-*` /
> `android-*`）に委譲する。単一責任を守ることで、途中失敗しても再開できる。

> **スタック方針**：自社の新規モバイルアプリは **iOS = SwiftUI / Android =
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
- Stack: SwiftUI + Jetpack Compose (既定 — Flutter は不使用)
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
   - iOS 配信をするなら App Store Connect の鍵 3 点（`mobile_health_check` の `apple.ok: true`）
   - Android 配信をするなら Google Play のサービスアカウント（`mobile_health_check` の `google`）
2. 配信の鍵は**ポータルの「鍵設定」に会社の鍵として預けたもの**を使う（手元の Keychain は使わない）。
   iOS は App Store Connect の 3 点（Key ID・Issuer ID・.p8）だけ。証明書（.p12）・Team ID の別登録は要らない
   （署名は Apple のクラウド署名。Team ID は project.yml の `DEVELOPMENT_TEAM` に書く）。
   Android は Play のサービスアカウント JSON と、Phase 5 で作るアップロード用キーストア。
3. **鍵が足りなくても止めない。** 雛形の配信ワークフローは鍵が無いと「鍵待ち」で緑のまま終わるので、
   アプリづくり（Phase 1〜4）は先に進め、足りない鍵だけ本人に「鍵設定で預けてください」と 1 回伝える。
   鍵がそろったら Phase 5 で入れて、そのまま 1 回目の配信を流す。

4. **iOS を配信する場合、flavor ごとの ASC 事前登録を確認**（見落とすと CI 37 秒で死ぬ）:

   - Apple Developer Portal に **Bundle ID** が登録されているか
   - App Store Connect に **App 記録** があるか

   確認は `references/create-asc-app-record.rb` を叩く:

   まず `ios_get_status`（bundle_id）で App 記録があるかを見る（`app_id` が返れば記録あり）。無い flavor だけ下のスクリプトで作る
   （手元の Mac で、ASC の 3 点を環境変数に入れて回す。鍵の値は会話に出さない）:

   ```bash
   # ASC_KEY_ID / ASC_ISSUER_ID / ASC_P8_B64（.p8 を base64 にしたもの）を環境変数に入れておく
   for FLAVOR in dev stg prod; do
     export TARGET_BUNDLE_ID="{{company.reverse_domain}}.{app_lower}.$FLAVOR"
     export TARGET_BUNDLE_NAME="{APP_NAME} $(echo $FLAVOR | tr a-z A-Z)"
     export TARGET_APP_NAME="{APP_NAME}"
     export TARGET_SKU="{app_lower}-$FLAVOR-$(date +%Y)"
     bundle exec ruby scripts/create-asc-app-record.rb || echo "→ $FLAVOR: manual step needed"
   done
   ```

   Bundle ID 作成は API で自動化される（App Manager role で足りる）。App 記録の作成は
   Admin role 必須なので、失敗した flavor はスクリプトの案内どおり Web UI で作成する。
   詳細と背景は `references/asc-app-record-setup.md` 参照（SampleApp で実際に踏んだ罠つき）。

   **どれか 1 flavor でも App 記録が無ければ、その flavor は Phase 6-7 で必ず失敗する**。
   halt して人にお願いする（勝手に "あとで" と流さない）。

---

## Phase 1: ヒアリング（不足分だけ聞く）

ユーザーの初発入力から次の項目を読み取り、埋まらない部分だけ AskUserQuestion で 1〜2 問に絞って聞く。

| 項目 | 例 | デフォルト |
|---|---|---|
| APP_NAME | `Foo` / `SampleApp` | 必須（推測しない） |
| APP_DESCRIPTION | `メモを記録するアプリ` | 「Hello World デモ」 |
| CORE_FEATURES | `写真を投稿できる / 位置情報を保存` | `Hello World`（空） |
| TARGETS | `iOS only` / `Android only` / `both` | `both` |
| STACK | 既定は **iOS = SwiftUI / Android = Kotlin + Jetpack Compose**。Flutter は聞かない | ネイティブ 2 本立て |
| BUNDLE_ID | `{{company.reverse_domain}}.foo` | `{{company.reverse_domain}}.{app_name_lower}` |
| PACKAGE_NAME | `{{company.reverse_domain}}.foo` | Bundle ID と同じ |
| DISPLAY_NAME | `Foo` | APP_NAME をそのまま |
| GITHUB_ORG | `ai-osi-uri` / `personal` | `create-app` の `USE_ORG` 判定に準拠 |
| ICON_SOURCE | 1024x1024 PNG / 画像URL / なし（nano-banana で生成） | なし |

**「Flutter で作って」と要望が来たとき**:
1. 自社の既定スタックがネイティブ 2 本立てで、実運用（SampleApp 移植）で
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
  スタック: SwiftUI (iOS) + Jetpack Compose (Android)   ← 既定のネイティブ 2 本立て
  Bundle ID: {{company.reverse_domain}}.foo
  Package Name: {{company.reverse_domain}}.foo
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

## Phase 5: 鍵を GitHub に入れて、1 回目の配信を流す（mobile-secrets-sync）

配信の鍵は、コネクタの `mobile_keys_to_github` が「鍵設定」の会社の鍵から GitHub のシークレットに入れる
（値は会話に出ない）。**鍵がそろっていれば `start_release: true` を付け、入れたその場で配信のワークフローを 1 回動かす**
（動かす前に「◯◯ のリポに鍵を入れて TestFlight に出します」と本人に見せて OK をもらう）。

```
mobile_keys_to_github:
  repo_name: {repo_name}
  targets: [ios, android]     # 配信する先だけ
  start_release: true         # 鍵がそろった配信先のワークフローを動かす
```

戻り値: `set`（入れたシークレット名）・`missing`（足りない鍵）・`releases`（配信先ごとの run_id と URL）。
Android のアップロード用キーストアと Firebase の設定は `mobile-secrets-sync` の手順で入れる。

**注意**:
- 鍵が足りない配信先は動かさない（動かしても「鍵待ち」で終わるだけ）。足りない鍵を本人に伝え、預けてもらったら呼び直す。
- 配信の CI は**後から設定を変えない前提**で雛形に入っている（push で自動・手でも動かせる・鍵待ちは緑）。
  AI が後から CI の動き方（`on:`）を書き換えようとすると安全チェックで止まるので、手で動かしたいときは `github_run_workflow` を使う。

---

## Phase 6-7: CI 監視 + 自動修正ループ（iOS / Android）

Phase 2〜5 で push されたコミットが CI を走らせる。iOS ワークフロー
（`.github/workflows/ios-release-auto.yml`）と Android ワークフロー
（`android-release-auto.yml`）を並行監視する。

### 監視手順（各ターゲットで）

1. Phase 5 の `releases` に run_id があればそれを、無ければ `github_workflow_runs`（workflow: `ios-release-auto.yml` など）で直近の実行を取る
2. `github_workflow_runs`（run_id）を 1〜2 分おきに見る → `summary` が「成功」で ✅（「鍵待ち」と出たら鍵が届いていない＝Phase 5 に戻る）
3. 「失敗（ステップ名）」なら次の Step へ。ログは返る `url` で見られる

### 自動修正ループ（最大 3 回）

1. 失敗した job のログを取る（手元の Deploy 拡張の `github_fetch`、無ければ `github_workflow_runs` の `url` を本人に開いてもらう）
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
| 0 | 配信の鍵が「鍵設定」に無い | 足りない鍵を伝えて先に進める（配信は鍵待ちで止まるだけ）。そろったら Phase 5 |
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
