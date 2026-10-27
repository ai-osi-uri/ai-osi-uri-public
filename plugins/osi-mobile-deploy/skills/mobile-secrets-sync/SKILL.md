---
name: mobile-secrets-sync
description: |
  モバイル配信に必要な GitHub Actions Secrets（App Store Connect の鍵 3 点 / Play SA
  / keystore / Firebase config 等）を入れ、鍵がそろったらそのまま 1 回目の配信を流す。
  配信の鍵は鍵設定の会社の鍵から mobile_keys_to_github で入れる。keystore が未生成なら
  作成して Drive に退避する。`deploy-mobile-app` の Phase 5 から呼ばれる。単体では
  「モバイルの Secrets を入れて」「配信の鍵を GitHub に入れて」「鍵を入れて TestFlight に出して」で発動。
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
  - server: cowork
    provision: builtin
# 手元が要る準備（get_skill が「手元の準備」の節を出す。導入手順は osi-core:local-setup）
local_setup: [mac, ext-deploy]
# スキルの一覧（つないだときに Claude に渡す）に出す短い用途
label: スマホ配信の鍵を入れる
---

# mobile-secrets-sync — GitHub Secrets への全自動投入

> **組織固有値はプロファイルから読む。** 本文の `{{paths.*}}` `{{ledgers.*}}` `{{company.*}}` `{{members.*}}` は、連結フォルダ直下の `osi-profile.md`（雛形: `config/osi-profile.example.md`）の値に置き換えて解釈する。無ければ会社名・案件フォルダ・台帳の有無・使うコネクタを質問して先に作る。値をここに直書きしない。

**配信の鍵（App Store Connect・Google Play）は、ポータルの「鍵設定」に預けた会社の鍵から、コネクタの
`mobile_keys_to_github` が GitHub のシークレットに入れる**（値はサーバーの中で暗号化して送るので、会話にも画面にも出ない）。
手元の Keychain から読んで入れるやり方（〜0.8.x）はやめた。Keychain を使うのは、Android のアップロード用キーストアを控えるときだけ。

## 決まり（0.9.0〜）

- **シークレットの名前は固定**。雛形のワークフロー（`ios-release-auto.yml` / `android-release-auto.yml`）はこの名前で読む。
  名前を変えない・別名で二重に入れない。
- **iOS は 3 点だけ**（`ASC_KEY_ID` / `ASC_ISSUER_ID` / `ASC_PRIVATE_KEY`）。署名は Apple のクラウド署名なので、
  証明書（.p12）・そのパスワード・一時 Keychain のパスワード・Team ID のシークレットは要らない（Team ID は project.yml）。
- **鍵を入れたら、そのまま 1 回目の配信を流す**（`start_release: true`）。人に GitHub の画面でボタンを押してもらわない。
  動かす前に「◯◯ のリポに鍵を入れて TestFlight（Google Play の内部テスト）に出します」と本人に見せて OK をもらう。
- **鍵が足りなくても止めない**。足りない配信先は動かさず、足りない鍵の名前を本人に伝える。雛形の CI は鍵が無いと「鍵待ち」で緑のまま終わる。

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `repo_name` | ✅ | GitHub repo name（会社の org。自分の鍵のときだけ `repo_owner`） |
| `targets` | 任意 | `ios` / `android`（既定: 両方） |
| `start_release` | 任意 | 入れたあと配信のワークフローを 1 回動かす（既定: 本人の OK があれば true） |
| `include_firebase` | 任意 | GoogleService-Info.plist / google-services.json も投入（既定: true） |
| `generate_keystore_if_missing` | 任意 | Android のアップロード用キーストアが無ければ作る（既定: true） |
| `keystore_backup_dir` | 任意 | keystore バックアップ先 Drive パス（既定: `{{paths.shared}}/mobile-release/keystores/`） |

## 入れるシークレット

### iOS 3 個（`mobile_keys_to_github` が入れる）

| Secret 名 | 中身（鍵設定の鍵） |
|---|---|
| `ASC_KEY_ID` | App Store Connect API キーの ID（10 文字） |
| `ASC_ISSUER_ID` | Issuer ID（UUID） |
| `ASC_PRIVATE_KEY` | .p8 の中身そのまま（base64 にしない） |

### Android 5 個

| Secret 名 | 由来 |
|---|---|
| `PLAY_SERVICE_ACCOUNT_JSON` | `mobile_keys_to_github` が入れる（鍵設定の Play のサービスアカウント JSON そのまま） |
| `ANDROID_KEYSTORE_B64` | Step 3（既存 or `mobile_generate_keystore` の `keystore_b64`） |
| `ANDROID_KEYSTORE_PASSWORD` | 同上 `keystore_password` |
| `ANDROID_KEY_ALIAS` | 同上 `alias`（既定 `upload`） |
| `ANDROID_KEY_PASSWORD` | 同上 `key_password` |

### Firebase 2〜4個（`include_firebase: true` のみ）

| Secret 名 | 由来 |
|---|---|
| `GOOGLE_SERVICE_INFO_PLIST_DEV_B64`  | `mobile-firebase-setup` が既に投入済み or 案件フォルダから取得 — dev flavor iOS 必須 |
| `GOOGLE_SERVICE_INFO_PLIST_STG_B64`  | 同上 — stg flavor を使う案件のみ |
| `GOOGLE_SERVICE_INFO_PLIST_PROD_B64` | 同上 — **prod flavor 必須**（SampleApp 2026-08 で追加忘れてブロックされた） |
| `GOOGLE_SERVICES_JSON_DEV_B64`       | 同上 — dev flavor Android 必須 |
| `GOOGLE_SERVICES_JSON_STG_B64`       | 同上 — stg flavor を使う案件のみ |
| `GOOGLE_SERVICES_JSON_PROD_B64`      | 同上 — **prod flavor 必須** |
| `FIREBASE_ANDROID_APP_ID`            | `firebase apps:list --json` or Firebase Console | Android Crashlytics / クラッシュレポート送信で使う |
| `GCP_SA_KEY_JSON`                    | GCP Console → IAM → Service Accounts → Keys → Create JSON | Firebase Functions を CI で `firebase deploy --only functions` するなら必須（Firebase Admin + Cloud Run Admin + Cloud Functions Admin） |

## 実行フロー

### Step 1: 前提チェック

```
1. github_list_secrets({repo_owner, repo_name}) で既存のシークレット名を見る
2. mobile_health_check で、鍵設定の App Store Connect / Play の鍵が生きているかを見る
   （apple.ok / google が false なら、足りない鍵を本人に伝える。止めずに Step 3 以降は進める）
3. リポに配信のワークフロー（ios-release-auto.yml / android-release-auto.yml）があるか
   （github_workflow_runs の workflows で見られる。無ければ mobile-app-scaffold の雛形から置く）
```

### Step 2: 配信の鍵を入れて、1 回目を流す

```
mobile_keys_to_github({
  repo_name: "<repo_name>",
  targets: ["ios", "android"],   // 配信する先だけ
  start_release: true            // Android は Step 3 のキーストアを入れてから true にする
})
```

戻り値の `set`（入れた名前）・`missing`（足りない鍵）・`releases`（配信先ごとの run_id・URL）を本人に短く伝える。
Android は キーストア（Step 3）が入るまで配信しても鍵待ちになるので、iOS だけ先に `start_release` してよい。

### Step 3: Android keystore（既存 or 新規生成）

```
既存確認（まず github_list_secrets に ANDROID_KEYSTORE_B64 があれば、作り直さずそのまま使う）:
  read_keychain() { security find-generic-password -s "$1" -a "$USER" -w 2>/dev/null || echo ""; }
  ANDROID_KEYSTORE_B64="$(read_keychain ANDROID_KEYSTORE_B64)"

  if [ -z "$ANDROID_KEYSTORE_B64" ] && [ "$generate_keystore_if_missing" = "true" ]; then
    # MCP 呼出（Claude が実行）
    result = mobile_generate_keystore({
      alias: "upload",
      validity_days: 10000,
      keystore_type: "PKCS12",
      key_algorithm: "RSA"
    })
    → 戻り値の keystore_b64 / keystore_password / key_password / alias を採用

    # Keychain にも保存（次回以降の再生成防止）
    security add-generic-password -U -s "ANDROID_KEYSTORE_B64" -a "$USER" -w "$KEYSTORE_B64"
    security add-generic-password -U -s "ANDROID_KEYSTORE_PASSWORD" -a "$USER" -w "$KEYSTORE_PW"
    security add-generic-password -U -s "ANDROID_KEY_ALIAS" -a "$USER" -w "$KEY_ALIAS"
    security add-generic-password -U -s "ANDROID_KEY_PASSWORD" -a "$USER" -w "$KEY_PW"

    # Drive にも .jks 実ファイルをバックアップ（重要: 失うとアプリ更新不可）
    echo "$KEYSTORE_B64" | base64 --decode > /tmp/{repo_name}-release.jks
    → mcp__cowork__ の Drive ツールで
       {keystore_backup_dir}/{repo_name}-release.jks にアップロード
       同時に metadata JSON (パスワード除く・alias・作成日・sha256) も
       {keystore_backup_dir}/{repo_name}-release.meta.json に置く
    → パスワード類は別途 1Password / Vault にも入れるよう案内（本スキルは Drive まで）
  elif [ -z "$ANDROID_KEYSTORE_B64" ]; then
    halt & ask: Keychain に無いので generate_keystore_if_missing:true で再実行するか、
                手動で security add-generic-password で登録してほしい
  fi
```

### Step 4: キーストアと Firebase を `github_set_secrets_batch` で入れる

```
github_set_secrets_batch({
  repo_owner: "<repo_owner>",
  repo_name: "<repo_name>",
  secrets: {
    ANDROID_KEYSTORE_B64: "...",
    ANDROID_KEYSTORE_PASSWORD: "...",
    ANDROID_KEY_ALIAS: "upload",
    ANDROID_KEY_PASSWORD: "...",
    GOOGLE_SERVICE_INFO_PLIST_DEV_B64:  "...",   // include_firebase:true のみ
    GOOGLE_SERVICE_INFO_PLIST_PROD_B64: "...",   // prod を配信するなら必須
    GOOGLE_SERVICES_JSON_DEV_B64:       "...",
    GOOGLE_SERVICES_JSON_PROD_B64:      "...",
    FIREBASE_ANDROID_APP_ID:            "1:xxx:android:yyy",  // Android の Crashlytics などで使うとき
    GCP_SA_KEY_JSON:                    "{...}"                // Firebase Functions を CI で deploy するなら
  }
})
```

入れ終わったら Android も `github_run_workflow`（workflow: `android-release-auto.yml`）で 1 回動かす（本人の OK のうえで）。

戻り値の `results` を人間可読に整形して報告:

```
✅ 投入完了 (6/6)
  - ANDROID_KEYSTORE_B64: created
  - GOOGLE_SERVICES_JSON_DEV_B64: updated
  ...
```

失敗があれば失敗リストを提示して halt。

### Step 5: 検証

```
github_list_secrets({repo_owner, repo_name}) を再度叩いて、
期待した全 Secret 名が存在することを確認。
```

## 戻り値

```json
{
  "repo": "ai-osi-uri/{repo_name}",
  "total": 13,
  "succeeded": 13,
  "failed": 0,
  "generated_keystore": true,
  "keystore_backup_path": "{{paths.shared}}/mobile-release/keystores/{repo_name}-release.jks",
  "releases": { "ios": { "run_id": 123, "url": "https://github.com/..." } },
  "method": "mobile_keys_to_github + github_set_secrets_batch"
}
```

## エラーハンドリング

| 症状 | 対応 |
|---|---|
| 鍵設定に配信の鍵が無い（`missing`） | 足りない鍵の名前を伝えて「鍵設定」で預けてもらう。止めずに他の手順は進め、預けたら呼び直す |
| `releases` が「workflow_dispatch がありません」 | 古い手作りのワークフロー。雛形の `ios-release-auto.yml` に置き換える（CI の動き方の変更なので本人の OK をもらってから） |
| keytool 無し | mobile_generate_keystore が fail 返却 → JDK 案内、halt |
| github_set_secrets_batch・github_run_workflow で 403 | GitHub の鍵の権限不足（`repo`+`workflow`）、案内、halt |
| Drive バックアップ失敗 | Claude の Drive tool 状態確認、非致命的（Secret は既に投入済み） |
| 一部 Secret のみ失敗 | 失敗した Secret 名を提示、再実行を案内 |

## 注意事項

- **既存の同名 Secret は上書き**（`github_set_secrets_batch` の semantics）。同名を守りたいなら
  事前に `github_list_secrets` で確認。
- **サイズ制限**: GitHub Actions Secret は 64KB まで。keystore base64（〜3.7KB）は余裕。
- **keystore は絶対に失わない**: 失うとアプリ更新不可（新規 keystore で署名した AAB は
  Play が「別アプリ」扱いする）。Drive バックアップ + 1Password の 2重化必須。
- **Play App Signing を使う場合**、アップロード鍵は差し替え可能だが「初回アップロード鍵の
  base64」は Play Console に登録済みの状態なので、差し替える時は Play サポート経由。
- Keychain の値そのものをチャットに出さない（機微値）。secret 名と `OK` / `MISSING` の
  状態だけ表示。
