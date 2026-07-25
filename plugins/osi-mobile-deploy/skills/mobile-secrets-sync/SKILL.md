---
name: mobile-secrets-sync
description: |
  モバイル配信に必要な GitHub Actions Secrets（App Store Connect API Key、iOS Distribution
  証明書 P12、Android Keystore、Google Play Service Account JSON など計 10+ 個）を、
  macOS Keychain から取得して GitHub リポに投入する atomic スキル。GitHub REST API +
  libsodium sealed box で暗号化投入。REST が使えない環境用に Chrome MCP でブラウザ経由
  fallback も持つ。オーケストレータ `deploy-mobile-app` から Phase 5 で呼ばれる。
  単体で「モバイルの Secrets 入れて」でも発動する。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
  - server: computer-use
    provision: builtin
---

# mobile-secrets-sync — Keychain → GitHub Secrets の一括投入

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `repo_owner` | ✅ | GitHub owner |
| `repo_name` | ✅ | GitHub repo name |
| `targets` | 任意 | `ios` / `android` / `both`（既定: `both`） |
| `include_firebase` | 任意 | Firebase の plist/json も同時に投入（既定: false — `mobile-firebase-setup` で既に投入済みの想定） |

## 投入する Secrets（source は macOS Keychain）

### iOS 用（7 個）

| Secret 名 | Keychain service | 内容 |
|---|---|---|
| `APPLE_TEAM_ID` | `APPLE_TEAM_ID` | 10桁英数（例: `24X327Z9SJ`） |
| `APP_STORE_CONNECT_API_KEY_ID` | `APP_STORE_CONNECT_API_KEY_ID` | 10桁英数（例: `79L9K48XS6`） |
| `APP_STORE_CONNECT_API_KEY_ISSUER_ID` | `APP_STORE_CONNECT_API_KEY_ISSUER_ID` | UUID |
| `APP_STORE_CONNECT_API_KEY_B64` | `APP_STORE_CONNECT_API_KEY_B64` | .p8 ファイルの base64 |
| `IOS_DIST_CERT_P12_B64` | `IOS_DIST_CERT_P12_B64` | Distribution 証明書 .p12 の base64 |
| `IOS_DIST_CERT_PASSWORD` | `IOS_DIST_CERT_PASSWORD` | .p12 のパスワード |
| `IOS_KEYCHAIN_PASSWORD` | `IOS_KEYCHAIN_PASSWORD` | CI 上で作る一時 Keychain のパスワード |

### Android 用（5 個）

| Secret 名 | Keychain service | 内容 |
|---|---|---|
| `ANDROID_KEYSTORE_B64` | `ANDROID_KEYSTORE_B64` | release.keystore の base64 |
| `ANDROID_KEYSTORE_PASSWORD` | `ANDROID_KEYSTORE_PASSWORD` | keystore のパスワード |
| `ANDROID_KEY_ALIAS` | `ANDROID_KEY_ALIAS` | key alias（例: `upload`） |
| `ANDROID_KEY_PASSWORD` | `ANDROID_KEY_PASSWORD` | key alias のパスワード |
| `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | Play Publisher API 用 SA JSON |

### Firebase 用（`include_firebase: true` のみ、任意）

| Secret 名 | 内容 |
|---|---|
| `GOOGLE_SERVICE_INFO_PLIST_DEV_B64` | iOS Firebase config の base64 |
| `GOOGLE_SERVICES_JSON_DEV_B64` | Android Firebase config の base64 |

## ワークフロー

```
1. 前提チェック（Keychain の各 secret が読めるか）
2. GitHub リポの public key を取得
3. libsodium sealed box で暗号化
4. REST API で PUT 投入
5. 結果を返す（成功一覧 / 失敗一覧）
```

### Step 1: Keychain 読み出し

```bash
read_secret() {
  local svc="$1"
  local val
  val=$(security find-generic-password -s "$svc" -a "$USER" -w 2>/dev/null || true)
  if [ -z "$val" ]; then
    echo "MISSING: $svc" >&2
    return 1
  fi
  printf '%s' "$val"
}

# iOS
APPLE_TEAM_ID="$(read_secret APPLE_TEAM_ID)"
APP_STORE_CONNECT_API_KEY_ID="$(read_secret APP_STORE_CONNECT_API_KEY_ID)"
# ... 他も同様
```

**halt & ask**: 1 つでも MISSING なら以下を提示して停止:

```
以下の secrets が Keychain にありません。ターミナルで登録してください:

  security add-generic-password -U -s "APPLE_TEAM_ID" -a "$USER" -w "24X327Z9SJ"
  security add-generic-password -U -s "APP_STORE_CONNECT_API_KEY_ID" -a "$USER" -w "79L9K48XS6"
  ...

登録が終わったら「登録した」と言ってください。もう一度実行します。
```

### Step 2〜4: GitHub REST API で投入

```bash
# public key 取得
PUBKEY_JSON=$(curl -sS -H "Authorization: token $GITHUB_PAT" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/actions/secrets/public-key")
KEY_ID=$(echo "$PUBKEY_JSON" | jq -r .key_id)
PUB_KEY_B64=$(echo "$PUBKEY_JSON" | jq -r .key)

# 1個ずつ暗号化して PUT
put_secret() {
  local name="$1"
  local value="$2"
  local encrypted
  encrypted=$(node -e '
    const sodium = require("libsodium-wrappers");
    (async () => {
      await sodium.ready;
      const pk = sodium.from_base64(process.argv[1], sodium.base64_variants.ORIGINAL);
      const enc = sodium.crypto_box_seal(process.argv[2], pk);
      process.stdout.write(sodium.to_base64(enc, sodium.base64_variants.ORIGINAL));
    })();
  ' "$PUB_KEY_B64" "$value")

  curl -sS -X PUT \
    -H "Authorization: token $GITHUB_PAT" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/actions/secrets/$name" \
    -d "$(jq -n --arg v "$encrypted" --arg k "$KEY_ID" \
           '{encrypted_value: $v, key_id: $k}')"
}

put_secret "APPLE_TEAM_ID" "$APPLE_TEAM_ID"
put_secret "APP_STORE_CONNECT_API_KEY_ID" "$APP_STORE_CONNECT_API_KEY_ID"
# ... 全 secret 分繰り返し
```

**注意**:
- `libsodium-wrappers` は Cowork の Node 環境にあることが多いが、無い場合は `npm i -g libsodium-wrappers` を一時的に流す。
- 大きな値（.p12 の base64 は 3〜10KB）は `-d @-` でパイプ入力にする（コマンドラインの ARG_MAX を超えないため）。

### Fallback: Chrome MCP でブラウザ経由

REST API が使えない環境（GitHub PAT に `repo` scope が無い、org policy で API が blocked など）は
Chrome MCP でダッシュボード操作にフォールバック:

```
1. mcp__claude-in-chrome__navigate:
   https://github.com/{repo_owner}/{repo_name}/settings/secrets/actions

2. 各 secret に対して:
   a. mcp__claude-in-chrome__navigate:
      https://github.com/{repo_owner}/{repo_name}/settings/secrets/actions/new
   b. mcp__claude-in-chrome__form_input で
      "name" フィールド → secret 名
      "value" フィールド → secret 値
   c. mcp__claude-in-chrome__computer で "Add secret" ボタンを click
   d. success トースト or "Secrets" ページに遷移したことを確認

3. Chrome セッションのログインが切れていたら computer-use で 2FA を促す
```

処理数が 10+ 個あるので、進捗を都度ログに出しつつユーザーに時間がかかる旨を伝える。

## 戻り値

```json
{
  "secrets_set": ["APPLE_TEAM_ID", "APP_STORE_CONNECT_API_KEY_ID", ...],
  "secrets_skipped": [],
  "secrets_failed": [],
  "method": "rest_api"   // or "chrome_fallback"
}
```

## エラーハンドリング

| 症状 | 対応 |
|---|---|
| Keychain に secret 無し | 登録コマンドを提示、halt |
| GitHub REST 401 | GITHUB_PAT の scope 不足。案内して halt |
| GitHub REST 403 | Org の Secret 投入権限不足。オーナー確認 |
| libsodium が無い | `npm install libsodium-wrappers` を案内 |
| Chrome fallback で 2FA が必要 | computer-use でユーザーに 2FA を促す |
| Secret の値が空文字 | Keychain の登録ミス。halt |

## 注意事項

- **既存の同名 Secret は上書き**（PUT の POSIX）。それが困る運用なら事前に一覧を出してユーザー確認する。
- **サイズ制限**: GitHub Actions Secret は 64KB まで。.p12 の base64 が超えることは通常無い。
- **本番リリース用の Secret 差し替え**は「案件が本番化する時」にユーザーが `mobile-secrets-sync` を明示的に `environment: prod` で呼ぶ運用（v1 は環境固定なしで dev のみ）。
- Keychain の値そのものをチャットに出さない（機微値）。secret 名と `MISSING` / `OK` の状態だけ表示する。
