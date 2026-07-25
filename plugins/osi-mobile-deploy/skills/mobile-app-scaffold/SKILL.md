---
name: mobile-app-scaffold
description: |
  osi-mobile-deploy の Golden Template（SwiftUI + Kotlin Compose の空の Hello World
  ネイティブアプリ）から新規リポジトリを起こす atomic スキル。テンプレを clone → 6箇所を
  置換（App Name / Bundle ID / Package Name / Team ID / Application ID / Display Name）→
  GitHub に新規リポ作成 → push まで実行する。オーケストレータ `deploy-mobile-app` から
  Phase 2 で呼ばれる。単体で「モバイルアプリのテンプレを起こして」「Golden Template から
  リポ作って」でも発動する。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# mobile-app-scaffold — Golden Template から新規モバイルリポを起こす

`template/` 配下の Golden Template（`apps/ios/` + `apps/android/` + `.github/workflows/` +
`fastlane/`）を clone し、プレースホルダを置換して GitHub に push する。

## 入力契約

| 項目 | 必須 | 説明 | 例 |
|---|---|---|---|
| `app_name` | ✅ | PascalCase | `Foo` |
| `bundle_id` | ✅ | iOS Bundle ID | `com.aiosiuri.foo` |
| `package_name` | ✅ | Android Package Name（= applicationId） | `com.aiosiuri.foo` |
| `display_name` | 任意 | 画面表示名（既定: `app_name`） | `Foo` |
| `team_id` | 任意 | Apple Developer Team ID（既定: Keychain の `APPLE_TEAM_ID`） | `24X327Z9SJ` |
| `targets` | 任意 | `ios` / `android` / `both`（既定: `both`） | `both` |
| `github_org` | 任意 | `ai-osi-uri` / `personal`（既定: personal） | `ai-osi-uri` |
| `local_dir` | 任意 | 既定: `~/projects/{app_name_lower}` | |

## 置換対象（Golden Template 内のプレースホルダ）

| プレースホルダ | 置換後 | 出現箇所 |
|---|---|---|
| `MyApp` | `{app_name}` | ディレクトリ名、Swift ソース内、xcodeproj |
| `com.example.myapp` | `{bundle_id}` / `{package_name}` | Info.plist, project.yml, build.gradle.kts |
| `com/example/myapp` | `{package_name_slash}` | Android の java パッケージパス |
| `MY_APP_DISPLAY_NAME` | `{display_name}` | Info.plist の CFBundleDisplayName |
| `MY_APP_TEAM_ID` | `{team_id}` | project.yml の DEVELOPMENT_TEAM |
| `my-app-splash` | `{app_name_lower}-splash` | Assets のスプラッシュ参照名 |

## ワークフロー

```
1. スキル自身の template/ ディレクトリの絶対パスを解決
2. rsync -a --exclude '.DS_Store' template/ {local_dir}/   （新規または上書き）
3. sed で全ファイルのプレースホルダを一括置換
   - Bundle ID / Package Name（ドット区切り）
   - パッケージパス（スラッシュ区切り）
   - Java パッケージのディレクトリを mv でリネーム
   - App 名（PascalCase）
   - Display Name
   - Team ID
4. targets に応じて不要な apps/ サブディレクトリを削除（ios only なら apps/android を消す）
5. git init → 初回 commit
6. github_create_repo_and_push で GitHub に新規リポ作成 + push
7. 結果を返す
```

### Step 1〜3: テンプレ展開 + 置換

```bash
TEMPLATE_DIR="$(dirname "$0")/template"   # スキル自身の template/
LOCAL_DIR="${LOCAL_DIR:-$HOME/projects/${APP_NAME_LOWER}}"

# 展開（既存なら halt & ask ユーザー）
if [ -d "$LOCAL_DIR" ]; then
  echo "既に $LOCAL_DIR がある。上書きすると差分が失われる。"
  echo "続けるなら OSI_FORCE=1 を再設定して再実行。"
  [ "${OSI_FORCE:-}" = "1" ] || exit 1
fi
mkdir -p "$LOCAL_DIR"
rsync -a --exclude '.DS_Store' --exclude '.git' "$TEMPLATE_DIR/" "$LOCAL_DIR/"

# iOS ディレクトリ / Swift ソースを rename
cd "$LOCAL_DIR"
if [ -d apps/ios/MyApp ]; then
  mv apps/ios/MyApp "apps/ios/${APP_NAME}"
  mv "apps/ios/${APP_NAME}/App/MyAppApp.swift" "apps/ios/${APP_NAME}/App/${APP_NAME}App.swift"
fi

# Android の Java パッケージパス rename
PKG_SLASH_OLD="com/example/myapp"
PKG_SLASH_NEW="$(echo "$PACKAGE_NAME" | tr '.' '/')"
if [ -d "apps/android/app/src/main/java/${PKG_SLASH_OLD}" ]; then
  mkdir -p "apps/android/app/src/main/java/${PKG_SLASH_NEW}"
  # rsync でファイルを移動（親ディレクトリが違うため）
  rsync -a "apps/android/app/src/main/java/${PKG_SLASH_OLD}/" \
           "apps/android/app/src/main/java/${PKG_SLASH_NEW}/"
  rm -rf "apps/android/app/src/main/java/com/example"
fi

# 全ファイル一括置換（*.swift, *.kts, *.xml, *.plist, *.json, *.yml, project.yml, Fastfile, Info.plist）
# BSD sed (macOS) と GNU sed で挙動が違うので -i.bak 経由で共通化
find "$LOCAL_DIR" -type f \
  \( -name '*.swift' -o -name '*.kt' -o -name '*.kts' -o -name '*.gradle' \
     -o -name '*.xml' -o -name '*.plist' -o -name '*.json' -o -name '*.yml' \
     -o -name '*.yaml' -o -name 'Fastfile' -o -name 'Appfile' -o -name 'project.yml' \
     -o -name 'README.md' -o -name '.gitignore' \) \
  -exec sed -i.bak \
    -e "s|com\.example\.myapp|${BUNDLE_ID}|g" \
    -e "s|com/example/myapp|${PKG_SLASH_NEW}|g" \
    -e "s|MyApp|${APP_NAME}|g" \
    -e "s|MY_APP_DISPLAY_NAME|${DISPLAY_NAME}|g" \
    -e "s|MY_APP_TEAM_ID|${TEAM_ID}|g" \
    -e "s|my-app-splash|${APP_NAME_LOWER}-splash|g" \
    {} +
find "$LOCAL_DIR" -name '*.bak' -delete
```

### Step 4: targets に応じた削除

```bash
case "$TARGETS" in
  ios)
    rm -rf apps/android
    rm -f .github/workflows/android-release-auto.yml
    ;;
  android)
    rm -rf apps/ios
    rm -f .github/workflows/ios-release-auto.yml
    ;;
  both)
    # 何もしない
    ;;
esac
```

### Step 5-6: git init + push

```
mcp__AI_OSI_URI_Deploy__github_create_repo_and_push:
  work_dir: {local_dir}
  repo_name: {app_name_lower}
  owner_override: {ai-osi-uri or personal}
  private: true
  description: "{app_name} — created by AI OSI URI osi-mobile-deploy"
```

## 戻り値

```json
{
  "repo_url": "https://github.com/{owner}/{repo}",
  "repo_owner": "{owner}",
  "repo_name": "{repo}",
  "repo_id": 123456,
  "local_clone_dir": "{local_dir}",
  "initial_commit_sha": "abc1234"
}
```

## エラーハンドリング

| 症状 | 対応 |
|---|---|
| 同名ローカルディレクトリあり | `OSI_FORCE=1` を要求、または新しい dir 名を確認 |
| 同名 GitHub リポあり | `mobile-update-deploy` に切り替え確認 |
| プレースホルダ置換で「MyApp」がユーザー入力の app_name に含まれる | 事前に `[[ "$APP_NAME" =~ ^[A-Za-z][A-Za-z0-9]*$ ]]` で validate |
| bundle_id が `com.example.*` のまま | halt & ask（App Store Connect に登録できない） |

## 注意事項

- **Bundle ID / Package Name は同じ値で OK**（`com.aiosiuri.foo` 統一）。iOS と Android で分けたい特別な理由がある時だけ変える。
- **Team ID が Keychain に無い** → Phase 0 でチェック済み前提。抜けていれば halt。
- Golden Template 側にある `.github/workflows/*.yml` は既に「今日の罠回避全部入り」。scaffold 時に workflow は書き換えない（Bundle ID / Package Name の env だけ差し替える）。
- `Podfile` は入っていない（SPM のみで組む前提）。Firebase iOS SDK も SPM から入れる。
