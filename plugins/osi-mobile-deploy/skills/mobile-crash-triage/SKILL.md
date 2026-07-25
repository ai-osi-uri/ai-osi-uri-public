---
name: mobile-crash-triage
description: |
  TestFlight / Google Play Internal Track に配信済みのビルドがクラッシュした時に、
  クラッシュログを取得・シンボリケート・分析して原因候補と修正提案を出す atomic スキル。
  iOS は `ios_get_status` で対象ビルドの診断情報 + dSYM でシンボリケート。Android は
  `android_get_status` + Firebase Crashlytics。取得したスタックトレースを LLM で解析し、
  `references/known-crash-patterns.md` と照合して典型パターン（Firebase 未設定 / URL scheme
  空 / font 欠落 / Assets.car 欠落 など）に落とし込む。**自動修正はしない**、修正提案までで
  人が承認して `mobile-update-deploy` に渡す。「配信したアプリが起動しない」「TestFlight
  ビルドが落ちる」「Play で ANR が出てる」で発動する。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# mobile-crash-triage — クラッシュ調査と修正提案

## 入力契約

| 項目 | 必須 | 説明 |
|---|---|---|
| `platform` | ✅ | `ios` / `android` / `both` |
| `bundle_id` | iOS 必須 | 対象アプリの Bundle ID |
| `package_name` | Android 必須 | 対象アプリの Package Name |
| `build_number` | 任意 | 特定ビルドに絞る。未指定なら直近 5 ビルド |
| `local_clone_dir` | 任意 | dSYM を local から拾う場合の repo path |

## ワークフロー

```
1. プラットフォーム別にクラッシュログを取得
2. dSYM / mapping.txt でシンボリケート（可能なら）
3. LLM でスタックトレースを解析
4. references/known-crash-patterns.md と照合
5. 修正提案を出す（自動修正はしない）
6. mobile-update-deploy を呼ぶ提案をユーザーに提示（承認待ち）
```

### Step 1: iOS のクラッシュ取得

```
ios_get_status({
  bundle_id: "{bundle_id}",
  limit: 5   # 直近5ビルド
})
  → 戻り値の diagnostic_signatures や processing_state を確認
  → crash が記録されているビルドを特定

# より詳細は App Store Connect API から diagnostic signatures を pull:
firebase_api({ method: "GET", path: "/... diagnostic ..." })   # 実装依存
```

App Store Connect の diagnostic signatures は「症状の要約（スレッド + 上位 5 フレーム）」だけを返す。完全な .ips ファイルは Xcode の Organizer からしか取れないので、ユーザーに「Xcode → Window → Organizer → Crashes を開いて対象を「Show in Finder」→ .ips を持ってきて」と案内するのが確実。

### Step 2: Android のクラッシュ取得

```
android_get_status({
  package_name: "{package_name}",
  track: "internal"
})
  → 戻り値の crashRate / anrRate をチェック

# Firebase Crashlytics を確認
firebase_api({
  method: "GET",
  path: "/v1/projects/{project_id}/apps/{app_id}/... /crashlytics/issues"
})
```

より詳細な spreadable のスタックトレースは Firebase Console → Crashlytics → 詳細で取得。MCP から未対応な場合は Chrome MCP で URL を開いてスクショ + テキスト読み取り fallback。

### Step 3: シンボリケート

iOS の .ips が生（unsymbolicated）で来た場合:

```bash
# dSYM を local から探す（fastlane gym が出力する build/ios/ 配下）
DSYM_PATH=$(find "$LOCAL_CLONE_DIR/build" -name "*.app.dSYM" | head -1)
if [ -n "$DSYM_PATH" ]; then
  xcrun symbolicatecrash "$CRASH_IPS" "$DSYM_PATH" > "$CRASH_IPS.symbolicated.txt"
else
  echo "⚠️  dSYM が local に無い。App Store Connect からダウンロードするか、次のビルドで dSYM upload を有効化してください。"
fi
```

Android の mapping.txt が必要な場合:

```bash
MAPPING="$LOCAL_CLONE_DIR/apps/android/app/build/outputs/mapping/prodRelease/mapping.txt"
# Play Console にアップロード済みなら Crashlytics が自動で symbolicate してくれる
```

### Step 4: パターン照合

`references/known-crash-patterns.md` に登録された症状・原因・修正の辞書と照合する。マッチしたら人にわかる言葉で説明する。

### Step 5: 修正提案（自動修正しない）

```
🚨 クラッシュ検出（TestFlight ビルド 42）

【症状】
  起動直後に SIGABRT
  トップフレーム: `+[FIRApp defaultApp]`

【推定原因】（known-crash-patterns.md との照合）
  Firebase not configured — GoogleService-Info.plist が bundle に入っていない、
  もしくは AppDelegate の FirebaseApp.configure() が失敗している

【修正提案】
  1. AppDelegate に guard を追加:
     ```
     if let path = Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist"),
        let opts = FirebaseOptions(contentsOfFile: path) {
       FirebaseApp.configure(options: opts)
     }
     ```
  2. Xcode で GoogleService-Info-Dev.plist を Copy Bundle Resources に入れる
  3. CI では `GOOGLE_SERVICE_INFO_PLIST_DEV_B64` secret を復号する step を追加

【次のアクション】
  この提案でよければ「これで直して」と言ってください。
  mobile-update-deploy が該当ファイルを修正 → push → 再ビルドします。
```

## 戻り値

```json
{
  "crashes_found": 3,
  "crashes_analyzed": [
    {
      "build_number": "42",
      "symbol": "+[FIRApp defaultApp]",
      "matched_pattern": "firebase-not-configured",
      "confidence": "high",
      "fix_suggestion_files": ["apps/ios/Foo/App/AppDelegate.swift"]
    }
  ],
  "unmatched_crashes": [ ... ]   // 辞書に無いものは LLM 分析のみ
}
```

## エラーハンドリング

| 症状 | 対応 |
|---|---|
| App Store Connect の diagnostic が空 | 「Xcode Organizer から .ips を取ってきて」と案内 |
| dSYM が無い | 次回ビルドで `debug symbols upload` を workflow に追加提案 |
| Crashlytics に data が無い（新規アプリで数時間経過待ち） | 「30分待ってからもう一度」と案内 |
| パターン照合で何もマッチしない | LLM で spec ヒントを出しつつ、`references/known-crash-patterns.md` に追記候補として提示 |

## 注意事項

- **絶対に自動修正しない**。crash 原因が誤診の時、勝手にコードを書き換えると症状が悪化する。必ずユーザー承認を挟む。
- **提案は 1 crash あたり 1 fix**。複数原因が同時に出ている時は「まず A を直して再ビルド → まだ落ちるなら B を検討」と段階を示す。
- **新パターンは必ず `references/known-crash-patterns.md` に追記**。次回同じ症状で時間を溶かさないため。
- crash が macOS Simulator でしか再現しない（実機では出ない）ケースもあるので、`mobile-app-smoke-test` の結果と TestFlight のクラッシュを混同しない。
