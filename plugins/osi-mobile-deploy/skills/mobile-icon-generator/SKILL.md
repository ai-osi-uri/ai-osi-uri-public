---
name: mobile-icon-generator
description: |
  1枚の 1024x1024 PNG（またはユーザー指定の画像 URL）から、iOS AppIcon と Android
  mipmap の全 density（mdpi/hdpi/xhdpi/xxhdpi/xxxhdpi + adaptive-icon）を一括生成
  する atomic スキル。sips / ImageMagick / Node の sharp を用いて resize。ソース画像が
  無ければ nano-banana MCP でロゴを生成する fallback を持つ。オーケストレータ
  `deploy-mobile-app` から Phase 4 で呼ばれる。単体で「アプリのアイコン差し替えて」
  「1024px のロゴから各サイズ生成して」でも発動する。
version: 0.1.0
requires_connectors:
  - server: nano-banana
    provision: user-install
---

# mobile-icon-generator — 1枚から全 density を生成

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `work_dir` | ✅ | 新規モバイルリポの絶対パス（例: `~/projects/foo`） |
| `source_png` | 任意 | 1024x1024 PNG の絶対パス、または画像 URL、または `null`（nano-banana 生成） |
| `app_name` | ✅ | プロンプト生成に使う（`{app_name} という名前のシンプルなミニマルロゴ、透過背景`） |
| `targets` | 任意 | `ios` / `android` / `both`（既定: `both`） |
| `theme_color` | 任意 | 生成時のヒント色（`#FF6B00` など、任意）|

## 出力ファイル

### iOS (`apps/ios/{APP_NAME}/Resources/Assets.xcassets/AppIcon.appiconset/`)

- `AppIcon-1024.png` — 1024x1024（App Store / Marketing）
- `AppIcon-120.png` — 60pt @2x（iPhone Notification）
- `AppIcon-180.png` — 60pt @3x（iPhone App）
- `Contents.json` — iOS 26 単一アイコン形式（後述）

### Android (`apps/android/app/src/main/res/`)

- `mipmap-mdpi/ic_launcher.png` — 48x48
- `mipmap-hdpi/ic_launcher.png` — 72x72
- `mipmap-xhdpi/ic_launcher.png` — 96x96
- `mipmap-xxhdpi/ic_launcher.png` — 144x144
- `mipmap-xxxhdpi/ic_launcher.png` — 192x192
- `mipmap-mdpi/ic_launcher_round.png` — 48x48（丸型）
- 各密度で `ic_launcher_round.png` を同じ絵で生成
- `mipmap-anydpi-v26/ic_launcher.xml` — adaptive icon
- `drawable/ic_launcher_foreground.xml` — foreground vector（sourceからPNGを foreground として使う簡易版）

## ワークフロー

```
1. source_png の解決
   - path が指定 → そのファイルを使う
   - URL が指定 → curl で DL して /tmp/source.png
   - null → nano-banana で生成
2. リサイズ実行（sips 優先、無ければ ImageMagick、それも無ければ sharp）
3. Contents.json / adaptive-icon の XML を書き出し
4. 生成ファイル数を返す
```

### Step 1: source 解決

```bash
if [ -n "${SOURCE_PNG:-}" ] && [ -f "$SOURCE_PNG" ]; then
  SRC="$SOURCE_PNG"
elif [ -n "${SOURCE_PNG:-}" ] && [[ "$SOURCE_PNG" =~ ^https?:// ]]; then
  SRC="/tmp/osi-mobile-icon-src.png"
  curl -sSL "$SOURCE_PNG" -o "$SRC"
else
  # nano-banana fallback
  # 実装は MCP tool の generate_image を呼ぶ
  echo "→ nano-banana でロゴ生成中..."
  # 例: mcp__nano-banana_________generate_image({
  #        prompt: "${APP_NAME} という名前のシンプルなミニマルロゴ、正方形、透過背景、パステルカラー",
  #        size: "1024x1024",
  #        output_path: "/tmp/osi-mobile-icon-src.png"
  #     })
  SRC="/tmp/osi-mobile-icon-src.png"
fi

# 検証: 1024x1024 の PNG か
if command -v sips >/dev/null 2>&1; then
  W=$(sips -g pixelWidth "$SRC" | awk '/pixelWidth/ {print $2}')
  H=$(sips -g pixelHeight "$SRC" | awk '/pixelHeight/ {print $2}')
  if [ "$W" -lt 1024 ] || [ "$H" -lt 1024 ]; then
    echo "⚠️  source が 1024x1024 未満（${W}x${H}）。品質が落ちます。"
  fi
fi
```

### Step 2: リサイズ

`sips` が macOS 標準で確実に使えるのでこれを第一選択にする。

```bash
resize() {
  local out="$1"
  local size="$2"
  mkdir -p "$(dirname "$out")"
  if command -v sips >/dev/null 2>&1; then
    sips -z "$size" "$size" "$SRC" --out "$out" >/dev/null
  elif command -v magick >/dev/null 2>&1; then
    magick "$SRC" -resize "${size}x${size}" "$out"
  elif command -v convert >/dev/null 2>&1; then
    convert "$SRC" -resize "${size}x${size}" "$out"
  else
    # sharp (Node) は最終手段
    node -e "require('sharp')('$SRC').resize($size,$size).toFile('$out')"
  fi
}

case "$TARGETS" in
  ios|both)
    IOS_DIR="$WORK_DIR/apps/ios/$APP_NAME/Resources/Assets.xcassets/AppIcon.appiconset"
    mkdir -p "$IOS_DIR"
    resize "$IOS_DIR/AppIcon-1024.png" 1024
    resize "$IOS_DIR/AppIcon-120.png"  120   # 60pt @2x
    resize "$IOS_DIR/AppIcon-180.png"  180   # 60pt @3x
    ;;
esac

case "$TARGETS" in
  android|both)
    AND_RES="$WORK_DIR/apps/android/app/src/main/res"
    for entry in "mdpi:48" "hdpi:72" "xhdpi:96" "xxhdpi:144" "xxxhdpi:192"; do
      density="${entry%%:*}"
      size="${entry##*:}"
      resize "$AND_RES/mipmap-$density/ic_launcher.png"       "$size"
      resize "$AND_RES/mipmap-$density/ic_launcher_round.png" "$size"
    done
    ;;
esac
```

### Step 3: Contents.json + adaptive-icon の XML

**iOS の Contents.json（iOS 26 単一アイコン形式）**:

```json
{
  "images" : [
    {
      "filename" : "AppIcon-1024.png",
      "idiom" : "universal",
      "platform" : "ios",
      "size" : "1024x1024"
    },
    {
      "filename" : "AppIcon-120.png",
      "idiom" : "iphone",
      "scale" : "2x",
      "size" : "60x60"
    },
    {
      "filename" : "AppIcon-180.png",
      "idiom" : "iphone",
      "scale" : "3x",
      "size" : "60x60"
    }
  ],
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}
```

**Android adaptive-icon の XML** (`mipmap-anydpi-v26/ic_launcher.xml`):

```xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
    <monochrome android:drawable="@mipmap/ic_launcher_foreground" />
</adaptive-icon>
```

対応する `values/colors.xml` に `<color name="ic_launcher_background">#FFFFFF</color>` を追加
（既に Golden Template に入っている前提。無ければ append）。

foreground は簡易的に mipmap の 108x108 として PNG を再生成:

```bash
resize "$AND_RES/mipmap-mdpi/ic_launcher_foreground.png"       108
resize "$AND_RES/mipmap-hdpi/ic_launcher_foreground.png"       162
resize "$AND_RES/mipmap-xhdpi/ic_launcher_foreground.png"      216
resize "$AND_RES/mipmap-xxhdpi/ic_launcher_foreground.png"     324
resize "$AND_RES/mipmap-xxxhdpi/ic_launcher_foreground.png"    432
```

## 戻り値

```json
{
  "generated_files": [
    "apps/ios/Foo/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png",
    "apps/ios/Foo/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-120.png",
    "apps/ios/Foo/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-180.png",
    "apps/ios/Foo/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json",
    "apps/android/app/src/main/res/mipmap-mdpi/ic_launcher.png",
    ...
  ],
  "used_source": "nano-banana|user-provided",
  "source_path": "/tmp/osi-mobile-icon-src.png"
}
```

## エラーハンドリング

| 症状 | 対応 |
|---|---|
| source が 1024x1024 未満 | 警告を出して続行（品質は落ちるが動く） |
| source が透過背景でない | Android adaptive-icon の foreground で切り抜きが崩れる可能性を警告 |
| sips / ImageMagick / sharp どれも無い | Node.js 経由で `sharp` を `npm i -g sharp` 案内 |
| nano-banana が使えない環境 | ユーザーに「1024x1024 PNG のパスか URL を教えて」と halt & ask |

## 注意事項

- 生成後は `git add` してから commit するのを忘れない（`deploy-mobile-app` 側でまとめて push）。
- Contents.json は iOS 26 の「単一アイコン形式」を採用。旧来の 20 種類サイズ全部形式は使わない。
- iPad 対応アイコンは v1 の Golden Template では作らない（iPhone-only 前提）。iPad 案件は Contents.json を後で拡張。
- foreground の透過が無い画像だと Android の adaptive-icon で四角形が丸見えになる。UX がひどい時はユーザーに「透過 PNG に差し替えて」と促す。
