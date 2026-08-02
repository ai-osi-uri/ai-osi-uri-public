---
name: mobile-secrets-sync
description: |
  モバイル配信に必要な GitHub Actions Secrets（証明書 / ASC キー / keystore / Play SA
  / Firebase config 等）を一括投入する。keystore が未生成なら作成して Drive
  に退避する。`deploy-mobile-app` の Phase 5 から呼ばれる。単体では「モバイルの
  Secrets を入れて」で発動。
version: 0.2.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
  - server: cowork
    provision: builtin
---

# mobile-secrets-sync — GitHub Secrets への全自動投入

**手動 curl / bash / libsodium install はもう不要**。v0.2.0 から MCP ツール
`github_set_secrets_batch` + `mobile_generate_keystore` に完全委譲する。

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `repo_owner` | ✅ | GitHub owner |
| `repo_name` | ✅ | GitHub repo name |
| `targets` | 任意 | `ios` / `android` / `both`（既定: `both`） |
| `include_firebase` | 任意 | GoogleService-Info.plist / google-services.json も投入（既定: true） |
| `generate_keystore_if_missing` | 任意 | Keychain に Android keystore 無い場合に自動生成（既定: true） |
| `keystore_backup_dir` | 任意 | keystore バックアップ先 Drive パス（既定: `21.PJT資料/00.共通/mobile-release/keystores/`） |
| `dry_run` | 任意 | true なら「何を投入するか」だけ表示して PUT はしない |

## 投入する Secrets（12〜13個）

### iOS 7個

| Secret 名 | Keychain source |
|---|---|
| `APPLE_TEAM_ID` | `security find-generic-password -s APPLE_TEAM_ID` |
| `APP_STORE_CONNECT_API_KEY_ID` | 同上 (10文字英数) |
| `APP_STORE_CONNECT_API_KEY_ISSUER_ID` | 同上 (UUID) |
| `APP_STORE_CONNECT_API_KEY_B64` | 同上 (.p8 の base64) |
| `IOS_DIST_CERT_P12_B64` | 同上 (Distribution 証明書 .p12 の base64) |
| `IOS_DIST_CERT_PASSWORD` | 同上 |
| `IOS_KEYCHAIN_PASSWORD` | 同上（CI 上で作る一時 Keychain のパスワード） |

### Android 5個

| Secret 名 | 由来 |
|---|---|
| `ANDROID_KEYSTORE_B64` | Keychain（既存）or `mobile_generate_keystore` の戻り値 `keystore_b64` |
| `ANDROID_KEYSTORE_PASSWORD` | 同上 `keystore_password` |
| `ANDROID_KEY_ALIAS` | 同上 `alias`（既定 `upload`） |
| `ANDROID_KEY_PASSWORD` | 同上 `key_password` |
| `GOOGLE_PLAY_JSON_KEY_B64` | Keychain の `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` を base64 化 |

### Firebase 2〜4個（`include_firebase: true` のみ）

| Secret 名 | 由来 |
|---|---|
| `GOOGLE_SERVICE_INFO_PLIST_DEV_B64` | `mobile-firebase-setup` が既に投入済み or 案件フォルダから取得 |
| `GOOGLE_SERVICE_INFO_PLIST_PROD_B64` | 同上 |
| `GOOGLE_SERVICES_JSON_DEV_B64` | 同上 |
| `GOOGLE_SERVICES_JSON_PROD_B64` | 同上 |

## 実行フロー（全自動）

### Step 1: 前提チェック

```
1. github_list_secrets({repo_owner, repo_name}) を叩いて既存 Secret を確認
   → 全部揃っていて再投入不要ならスキップ判定
2. mobile_health_check({check_apple: true, check_google: true}) で
   拡張側の ASC / Play 認証が生きていることを確認
3. targets が android/both なら keytool が sandbox にあるか
   （mobile_generate_keystore の内部で自動確認・不足なら fail）
```

### Step 2: 値の収集

Keychain から bash で読み出し。**この部分だけは MCP ツールでは代替できない**（Keychain
アクセスは macOS ネイティブ）。以下のスクリプトを組み立てて実行:

```bash
#!/bin/bash
set -e
declare -A SECRETS

read_keychain() {
  local svc="$1"
  security find-generic-password -s "$svc" -a "$USER" -w 2>/dev/null || echo ""
}

# --- iOS ---
if [[ "$TARGETS" == "ios" || "$TARGETS" == "both" ]]; then
  SECRETS[APPLE_TEAM_ID]="$(read_keychain APPLE_TEAM_ID)"
  SECRETS[APP_STORE_CONNECT_API_KEY_ID]="$(read_keychain APP_STORE_CONNECT_API_KEY_ID)"
  SECRETS[APP_STORE_CONNECT_API_KEY_ISSUER_ID]="$(read_keychain APP_STORE_CONNECT_API_KEY_ISSUER_ID)"
  SECRETS[APP_STORE_CONNECT_API_KEY_B64]="$(read_keychain APP_STORE_CONNECT_API_KEY_B64)"
  SECRETS[IOS_DIST_CERT_P12_B64]="$(read_keychain IOS_DIST_CERT_P12_B64)"
  SECRETS[IOS_DIST_CERT_PASSWORD]="$(read_keychain IOS_DIST_CERT_PASSWORD)"
  SECRETS[IOS_KEYCHAIN_PASSWORD]="$(read_keychain IOS_KEYCHAIN_PASSWORD)"
fi

# --- Android ---
if [[ "$TARGETS" == "android" || "$TARGETS" == "both" ]]; then
  SECRETS[GOOGLE_PLAY_JSON_KEY_B64]="$(read_keychain GOOGLE_PLAY_SERVICE_ACCOUNT_JSON | base64)"
  # keystore の値は次の Step で（既存 or 生成）
fi

# 出力: name=value を1行ずつ（NULL区切りが理想だがまず素朴に）
for k in "${!SECRETS[@]}"; do
  # 値に改行が入る可能性のある .p8 base64 等は事前に tr -d '\n' で1行化
  v="${SECRETS[$k]}"
  echo "${k}=${v}"
done > /tmp/secrets-collected.env
```

**halt & ask**: iOS 側で1つでも空なら以下を提示して停止:

```
以下の iOS secrets が Keychain にありません。ターミナルで登録してください:

  security add-generic-password -U -s "APPLE_TEAM_ID" -a "$USER" -w "24X327Z9SJ"
  security add-generic-password -U -s "APP_STORE_CONNECT_API_KEY_ID" -a "$USER" -w "..."
  security add-generic-password -U -s "APP_STORE_CONNECT_API_KEY_ISSUER_ID" -a "$USER" -w "UUID"
  security add-generic-password -U -s "APP_STORE_CONNECT_API_KEY_B64" -a "$USER" -w "$(base64 -i AuthKey_XXXXXXXXXX.p8)"
  security add-generic-password -U -s "IOS_DIST_CERT_P12_B64" -a "$USER" -w "$(base64 -i dist.p12)"
  security add-generic-password -U -s "IOS_DIST_CERT_PASSWORD" -a "$USER" -w "PASSWORD"
  security add-generic-password -U -s "IOS_KEYCHAIN_PASSWORD" -a "$USER" -w "$(openssl rand -base64 24)"

登録後に「登録した」と返してください。
```

### Step 3: Android keystore（既存 or 新規生成）

```
既存確認:
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

### Step 4: `github_set_secrets_batch` で一括 PUT

```
Claude が MCP ツールを呼ぶ:

github_set_secrets_batch({
  repo_owner: "<repo_owner>",
  repo_name: "<repo_name>",
  secrets: {
    APPLE_TEAM_ID: "...",
    APP_STORE_CONNECT_API_KEY_ID: "...",
    APP_STORE_CONNECT_API_KEY_ISSUER_ID: "...",
    APP_STORE_CONNECT_API_KEY_B64: "...",
    IOS_DIST_CERT_P12_B64: "...",
    IOS_DIST_CERT_PASSWORD: "...",
    IOS_KEYCHAIN_PASSWORD: "...",
    ANDROID_KEYSTORE_B64: "...",
    ANDROID_KEYSTORE_PASSWORD: "...",
    ANDROID_KEY_ALIAS: "upload",
    ANDROID_KEY_PASSWORD: "...",
    GOOGLE_PLAY_JSON_KEY_B64: "...",
    GOOGLE_SERVICE_INFO_PLIST_DEV_B64: "...",  // include_firebase:true のみ
    GOOGLE_SERVICES_JSON_DEV_B64: "..."         // 同上
  }
})
```

戻り値の `results` を人間可読に整形して報告:

```
✅ 投入完了 (13/13)
  - APPLE_TEAM_ID: updated
  - APP_STORE_CONNECT_API_KEY_ID: created
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
  "keystore_backup_path": "21.PJT資料/00.共通/mobile-release/keystores/{repo_name}-release.jks",
  "method": "github_set_secrets_batch (MCP v1.17.3+)"
}
```

## エラーハンドリング

| 症状 | 対応 |
|---|---|
| Keychain に iOS secret 無し | 登録コマンド提示、halt |
| keytool 無し | mobile_generate_keystore が fail 返却 → JDK 案内、halt |
| github_set_secrets_batch で 403 | GITHUB_PAT の scope 不足（`repo`+`workflow`）、案内、halt |
| Drive バックアップ失敗 | Cowork の Drive tool 状態確認、非致命的（Secret は既に投入済み） |
| 一部 Secret のみ失敗 | 失敗した Secret 名を提示、再実行を案内 |

## 注意事項

- **既存の同名 Secret は上書き**（`github_set_secrets_batch` の semantics）。同名を守りたいなら
  事前に `github_list_secrets` で確認。
- **サイズ制限**: GitHub Actions Secret は 64KB まで。.p12 base64（〜5KB）や keystore base64
  （〜3.7KB）は余裕。
- **keystore は絶対に失わない**: 失うとアプリ更新不可（新規 keystore で署名した AAB は
  Play が「別アプリ」扱いする）。Drive バックアップ + 1Password の 2重化必須。
- **Play App Signing を使う場合**、アップロード鍵は差し替え可能だが「初回アップロード鍵の
  base64」は Play Console に登録済みの状態なので、差し替える時は Play サポート経由。
- Keychain の値そのものをチャットに出さない（機微値）。secret 名と `OK` / `MISSING` の
  状態だけ表示。
