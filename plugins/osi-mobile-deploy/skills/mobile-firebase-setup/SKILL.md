---
name: mobile-firebase-setup
description: |
  モバイルアプリ用に Firebase プロジェクトを新規作成し、iOS App と Android App を追加、
  `GoogleService-Info.plist` / `google-services.json` を取得して base64 化 → GitHub Secrets
  に **`github_set_secrets_batch` で一括自動投入** する atomic スキル。AI OSI URI Deploy
  拡張の `firebase_api` / `firebase_list_projects` / `firebase_add_ios_app` /
  `firebase_add_android_app` / `firebase_get_ios_config` / `firebase_get_android_config`
  + `github_set_secrets_batch` を使う。オーケストレータ `deploy-mobile-app` から Phase 3
  で呼ばれる。単体で「モバイルの Firebase 設定して」でも発動する。
  前提: AI OSI URI Deploy 拡張 **v1.17.3 以降**（`github_set_secrets_batch` 必須）。
version: 0.2.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# mobile-firebase-setup — Firebase プロビジョニング + GitHub Secrets 投入

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `app_name` | ✅ | Firebase プロジェクト名の元。実際は `{app_name_lower}-dev` で作る |
| `bundle_id` | ✅ | iOS Bundle ID（Firebase iOS App 追加時に必須） |
| `package_name` | ✅ | Android package name |
| `targets` | 任意 | `ios` / `android` / `both`（既定: `both`） |
| `repo_owner` | ✅ | GitHub owner（Secrets 投入先） |
| `repo_name` | ✅ | GitHub repo name |
| `environment` | 任意 | `dev` / `stg` / `prod`（既定: `dev`）。v1 は dev のみ |
| `use_existing_project` | 任意 | 既存の Firebase project_id を再利用（quota 対策） |

## ワークフロー

```
1. Firebase プロジェクトを新規作成（or 既存を再利用）
2. iOS App を追加（targets が ios/both）
3. Android App を追加（targets が android/both）
4. GoogleService-Info.plist を取得（iOS）
5. google-services.json を取得（Android）
6. base64 化して GitHub Secrets に投入
7. 結果を返す
```

### Step 1: Firebase プロジェクト作成

`use_existing_project` が指定されていればスキップ。無ければ:

```
firebase_list_projects()
  → 既に `{app_name_lower}-{env}` があれば再利用（重複作成しない）
  → 無ければ以下:

firebase_api({
  method: "POST",
  path: "/v1beta1/projects",
  body: {
    projectId: "{app_name_lower}-{env}",
    displayName: "{app_name} ({env})",
    labels: { "created_by": "osi-mobile-deploy" }
  }
})
  → 戻り値の operation.name を取得
  → 10秒ごとにポーリング（`firebase_api GET /v1/{operation.name}` で done: true になるまで）
  → 通常 20〜60 秒で完了
```

**注意**:
- GCP アカウントの `Owner` / `Firebase Admin` 権限が必要。
- プロジェクト ID は全 GCP 内でユニーク。既存衝突なら `{app_name_lower}-{env}-{4桁数字}` を試す。
- プロジェクト数の quota は 25（無料枠）。超えたらユーザーに古いプロジェクトの削除を促す。

### Step 2: iOS App 追加

```
firebase_add_ios_app({
  project_id: "{firebase_project_id}",
  bundle_id: "{bundle_id}",
  display_name: "{app_name} iOS"
})
  → 戻り値: { app_id: "1:xxx:ios:yyy" }
```

### Step 3: Android App 追加

```
firebase_add_android_app({
  project_id: "{firebase_project_id}",
  package_name: "{package_name}",
  display_name: "{app_name} Android"
  # sha1_hash は debug keystore の SHA-1 を後で追加可能（初期は空でよい）
})
  → 戻り値: { app_id: "1:xxx:android:yyy" }
```

### Step 4-5: config 取得

```
firebase_get_ios_config({ app_id: "1:xxx:ios:yyy" })
  → 戻り値: { config_file_contents: "<?xml ... ?>" }
  → これを apps/ios/{APP_NAME}/Resources/GoogleService-Info-Dev.plist に保存（ローカルは .gitignore 済み）

firebase_get_android_config({ app_id: "1:xxx:android:yyy" })
  → 戻り値: { config_file_contents: "{ ... }" }
  → apps/android/app/src/dev/google-services.json に保存
```

### Step 6: GitHub Secrets へ一括投入（`github_set_secrets_batch` を1回叩くだけ）

拡張 v1.17.3+ の MCP ツールで完結。手動 curl / libsodium install は不要:

```
# Step 6-1: base64 化（sandbox の bash で）
IOS_B64=$(base64 -i "apps/ios/{APP_NAME}/Resources/GoogleService-Info-Dev.plist" | tr -d '\n')
ANDROID_B64=$(base64 -i "apps/android/app/src/dev/google-services.json" | tr -d '\n')

# Step 6-2: Claude が MCP ツールを呼ぶ
github_set_secrets_batch({
  repo_owner: "{repo_owner}",
  repo_name: "{repo_name}",
  secrets: {
    GOOGLE_SERVICE_INFO_PLIST_DEV_B64: "<IOS_B64>",
    GOOGLE_SERVICES_JSON_DEV_B64: "<ANDROID_B64>"
  }
})
  → 公開鍵取得は自動で1回のみ。libsodium sealed_box 暗号化も自動。
  → 戻り値の results で全 Secret の created/updated 状態を確認。
```

**投入する secret 名**（環境ごと）:

| Target | Secret 名 | 値 |
|---|---|---|
| iOS | `GOOGLE_SERVICE_INFO_PLIST_DEV_B64` | GoogleService-Info-Dev.plist を base64 化 |
| Android | `GOOGLE_SERVICES_JSON_DEV_B64` | google-services.json (dev) を base64 化 |

**stg / prod を後で足す時**は `_STG_B64` / `_PROD_B64` サフィックスで追加する（`environment`
引数を prod 指定して再実行）。

### 検証

```
github_list_secrets({repo_owner, repo_name}) を叩き、
期待した Secret 名が存在することを確認。
```

## 戻り値

```json
{
  "firebase_project_id": "foo-dev",
  "ios_app_id": "1:xxx:ios:yyy",
  "android_app_id": "1:xxx:android:zzz",
  "secrets_injected": [
    "GOOGLE_SERVICE_INFO_PLIST_DEV_B64",
    "GOOGLE_SERVICES_JSON_DEV_B64"
  ],
  "config_files_local": [
    "apps/ios/{APP_NAME}/Resources/GoogleService-Info-Dev.plist",
    "apps/android/app/src/dev/google-services.json"
  ]
}
```

## エラーハンドリング

| 症状 | 対応 |
|---|---|
| Firebase プロジェクト quota 超過 | ユーザーに古いプロジェクトの削除を促す or `use_existing_project` を指定 |
| Bundle ID / Package Name の重複追加 | `firebase_list_ios_apps` / `firebase_list_android_apps` で existing 確認 |
| `firebase_add_ios_app` が「App is being created」で 409 | 30 秒待って再試行 |
| GitHub Secrets 投入で 403 | PAT の scope に `repo` + `workflow` が必要。案内して停止 |
| `github_set_secrets_batch` ツールが見つからない | 拡張が v1.17.3 未満。新しい .mcpb をインストール後 Claude 完全再起動 |

## 注意事項

- **plist / json は .gitignore に必ず入れる**（credentials 漏洩防止）。実体はローカルと GitHub Secrets に。
- **REVERSED_CLIENT_ID は初期は使わない**。Google Sign-In を後で入れる時に Firebase Console → Authentication → Google → OAuth client を作って再取得する。
- **stg / prod の追加**は「案件が本番化する時」にユーザーが `mobile-firebase-setup` を `environment: prod` で明示的に呼ぶ運用。v1 では dev だけ。
- 認証用途で Firebase Auth を有効化するのは本スキルの範囲外（`firebase_api` で個別に有効化）。
