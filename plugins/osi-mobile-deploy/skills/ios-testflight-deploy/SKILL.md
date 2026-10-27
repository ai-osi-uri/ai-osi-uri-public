---
name: ios-testflight-deploy
description: |
  iOS ビルドを TestFlight に上げる。GitHub Actions（macOS）で xcodebuild が archive して、
  Apple のクラウド署名で TestFlight にアップロードする。鍵は App Store Connect の 3 点だけ
  （証明書 .p12 は要らない）。`deploy-mobile-app` / `mobile-update-deploy` から呼ばれる。
  単体では「TestFlight に上げて」「iOS を再配信して」「鍵を入れて TestFlight に出して」で発動。
  TestFlight に上がった後のビルド昇格・App Store 申請・Xcode バージョン運用は `ios-appstore-release` の担当。
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
# スキルの一覧（つないだときに Claude に渡す）に出す短い用途
label: iPhoneアプリをTestFlightへ
---

# ios-testflight-deploy — iOS を TestFlight に上げる

> **組織固有値はプロファイルから読む。** 本文の `{{paths.*}}` `{{ledgers.*}}` `{{company.*}}` `{{members.*}}` は、連結フォルダ直下の `osi-profile.md`（雛形: `config/osi-profile.example.md`）の値に置き換えて解釈する。無ければ会社名・案件フォルダ・台帳の有無・使うコネクタを質問して先に作る。値をここに直書きしない。

配信は **リポの CI（`.github/workflows/ios-release-auto.yml`）が行う**。Claude がやるのは、
鍵を入れる・CI を動かす・成否と TestFlight への到達を確かめる・落ちたら直す、の 4 つ。
手元の Mac・Xcode・GitHub の画面は要らない（全部 URL のコネクタの道具でできる）。

## 決まり（0.10.0〜。理由つき）

| 決まり | 理由 |
|---|---|
| **鍵は App Store Connect の 3 点だけ**（`ASC_KEY_ID` / `ASC_ISSUER_ID` / `ASC_PRIVATE_KEY`）。署名は Xcode の自動署名（Apple のクラウド署名）に任せる | 証明書（.p12）は会社の鍵として預かっていない。3 点なら鍵設定から `mobile_keys_to_github` でそのまま入る。名前を変えると CI が読めない |
| **配信のワークフローは最初から push で動き、手でも動かせる**（`on: push` + `workflow_dispatch`） | 「手動だけ」にすると、最後の一押しが人のボタン待ちになる。AI が後から CI の動き方（`on:`）を書き換えるのは安全チェックで止まるので、作る時点で正しい形にしておく |
| **鍵が無いときは失敗にせず「鍵待ち」で終わる** | 鍵を後から入れる進め方でも、push のたびに赤（失敗）が並ばない。鍵を入れたら 1 回動かせば届く |
| **xcodebuild の出力を tail で絞る行には `set -o pipefail`** | 付けないと xcodebuild が失敗しても tail の成功で「成功」と出る（落ちたのに気づけない） |
| **ビルド番号は `github.run_number`（＋ Variables の `BUILD_NUMBER_OFFSET`）** | 同じ番号は TestFlight に二度上げられない。実行のたびに必ず増える番号を使う。後から入れたリポで既に大きい番号があるときだけ下駄を履かせる |
| **`xcodegen generate` を archive の前に必ず走らせる** | stale な .xcodeproj で「Missing package product」が束で出る（`xcodegen-project-regen`） |
| **App Store Connect の API キーは「管理者（Admin）」で作る** | クラウド署名（配布用の証明書を Apple に任せる）は Admin のキーでしか動かない。App Manager のキーだと archive までは通り、書き出しで `Cloud signing permission error` → `No profiles for … were found` になる。キーの役割は作成後に変えられないので、作り直して鍵設定に入れ替える |
| **最新の macOS runner（`macos-26`）＋ 入っている中で一番新しい Xcode を選ぶ** | App Store Connect は毎年、最新の SDK で作ったものしか受け付けなくなる（例: iOS 26 SDK＝Xcode 26 以降）。古い runner の既定の Xcode だと、書き出しの検査で `SDK version issue` で断られる。runner の版を上げても既定の Xcode が古いことがあるので、ワークフローで一番新しい Xcode を `xcode-select` で選ぶ |

ワークフローの完全版は `references/ios-release-auto.yml.example`（`mobile-app-scaffold` の雛形と同じもの）。

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `repo_name` | ✅ | モバイルリポ（会社の org） |
| `flavor` | 任意 | `dev` / `stg` / `prod`（既定: `dev`。push で動くときは dev） |
| `bundle_id` | 任意 | 到達確認用（既定: project.yml の flavor の Bundle ID） |

## 手順

### 1. 事前確認

```
mobile_health_check            → apple.ok: true（鍵設定の App Store Connect の鍵が生きている）
ios_get_status(bundle_id)      → app_id が返る＝App Store Connect に App 記録がある
github_workflow_runs(repo)     → workflows に ios-release-auto.yml（または testflight.yml）がある
```

- **App 記録が無い flavor は必ず落ちる**（Bundle ID と App 記録の両方が要る）。作り方は
  `deploy-mobile-app/references/asc-app-record-setup.md`。App 記録の作成は Admin 権限が要るので、無ければ人に頼んで止まる。
- ワークフローが無い・`workflow_dispatch` が無い古い手作りのものなら、雛形の `ios-release-auto.yml` に置き換える。
  これは CI の動き方の変更なので、何をどう変えるかを本人に見せて OK をもらってから入れる。

### 2. 鍵を入れて、1 回目を流す

```
mobile_keys_to_github({ repo_name, targets: ["ios"], start_release: true })
```

動かす前に「◯◯ のリポに鍵を入れて TestFlight に出します」と本人に見せて OK をもらう。
鍵が既に入っていて、もう一度上げたいだけなら:

```
github_run_workflow({ repo_name, workflow: "ios-release-auto.yml", inputs: { flavor: "dev" } })
```

コードを直して main に push した場合は、push で自動的に動く（何も呼ばなくてよい）。

### 3. 成否を見る

```
github_workflow_runs({ repo_name, run_id })   → summary: 実行中 / 成功 / 失敗（ステップ名）
```

1〜2 分おきに見る。20〜40 分かかる。

- 「鍵待ち」と出た → 鍵が届いていない。手順 2 に戻る
- 「失敗（Archive …）」 → 下の表で原因を当てて直し、push（push で再実行される）
- 「成功」 → 手順 4 へ

### 4. TestFlight に届いたかを確かめる

```
ios_get_status({ bundle_id })   → builds の先頭が今回のビルド番号で processingState が VALID
```

Apple の処理に 10〜30 分かかる。**CI が成功しただけで「TestFlight に上がりました」と言わない。**
`ios_get_status` で今回のビルドが見えてから伝える。

## よくある失敗

| 症状（ログ） | 原因と対処 |
|---|---|
| `No Accounts` / `No signing certificate "iOS Distribution" found` | クラウド署名に鍵が渡っていない。`-authenticationKeyPath/ID/IssuerID` が書き出し（export）にあるか |
| `Cloud signing permission error`（続けて `No profiles for '…' were found`） | キーの役割が足りない。App Store Connect の「ユーザとアクセス → 統合 → チームキー」で、アクセスが「管理者」のキーを新しく作り（役割は後から変えられない）、鍵設定の App Store Connect に入れ替えて `mobile_keys_to_github` で入れ直す。今のキーの役割は同じ画面の「アクセス」列で分かる |
| `Could not find App with App Identifier` / `No profiles for '…' were found`（`Cloud signing permission error` が無いとき） | App Store Connect に Bundle ID か App 記録が無い（手順 1） |
| `The bundle version must be higher than the previously uploaded version` | 既に大きいビルド番号がある。リポの Variables に `BUILD_NUMBER_OFFSET` を置く |
| `Missing package product` が束で出る | `xcodegen generate` が抜けている／古い .xcodeproj がコミットされている（`xcodegen-project-regen`） |
| `SDK version issue. This app was built with the iOS XX SDK` / `SDK version … is required` | Xcode が古い。runner を最新（`macos-26` 以降）にし、「Select Xcode」の手順で一番新しい Xcode を選ぶ（雛形どおり）。ログの `xcodebuild -version` で選ばれた版を確かめる |
| `Missing required icon file` / `Invalid Info.plist value CFBundleIconName` | AppIcon（1024 の 1 枚）と Info.plist の `CFBundleIconName: AppIcon` を確かめる |
| `Invalid … ITSAppUsesNonExemptEncryption` で TestFlight に出ない | Info.plist に `ITSAppUsesNonExemptEncryption: false`（暗号の届け出が要らないアプリ） |
| `AuthKey_XXX.p8 not found` | .p8 のファイル名は `AuthKey_<KEY_ID>.p8` でなければならない |
| GitHub 上は成功なのに TestFlight に無い | `pipefail` が無く、失敗が隠れている。ワークフローを雛形に合わせる |

fastlane と altool で上げていた頃（〜0.8.x）の罠は `references/altool-quirks.md` に残してある（手元の Mac で上げるとき用）。

## 手元の Mac で上げる（予備）

CI が使えないときだけ。リポの `fastlane/Fastfile` の `ios_beta_auto` は、CI と同じ 3 点を環境変数
（`ASC_KEY_ID` / `ASC_ISSUER_ID` / `ASC_PRIVATE_KEY`）で読む。鍵の値は会話に出さない。

```bash
cd "$WORK_DIR" && bundle install --quiet && bundle exec fastlane ios ios_beta_auto flavor:dev
```

## 戻り値

```json
{
  "run_id": 123456,
  "run_url": "https://github.com/.../actions/runs/123456",
  "conclusion": "success",
  "build_number": "42",
  "testflight": "VALID"
}
```

## 注意事項

- **App Store の審査提出はこのスキルの範囲外**。`ios-appstore-release`（`ios_submit_review`）で、はっきり頼まれたときだけ。
- flavor は dev / stg / prod を雛形に用意している。Bundle ID が flavor ごとに違うので、配信する flavor ごとに App 記録が要る。最初は dev だけ運用する。
- 鍵の値（.p8 の中身など）は会話・ログ・コミットに出さない。ワークフローは最後に鍵のファイルを消す。

## 関連スキル

- `mobile-secrets-sync` — 鍵を入れて 1 回目を流す
- `xcodegen-project-regen` — CI 内 `xcodegen generate` の理由と手当て
- `deploy-mobile-app` — 新規リポ作成から配信まで
- `mobile-update-deploy` — 既存リポを直して再配信
- `ios-appstore-release` — TestFlight の後（昇格・申請）
