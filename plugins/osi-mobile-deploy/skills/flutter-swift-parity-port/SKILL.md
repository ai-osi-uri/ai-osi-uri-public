---
name: flutter-swift-parity-port
description: |
  **既存 Flutter (Dart) アプリを SwiftUI ネイティブに移行**するときだけ使う、専用の
  migration ワークフロー skill。**新規モバイルアプリの構築には使わない**（新規は
  `mobile-app-scaffold` で SwiftUI + Jetpack Compose のネイティブスタックから始めるのが
  AI OSI URI の既定）。既存 Flutter プロダクトを iOS ネイティブに置き換える必要が
  出た局面（例: MustPost の SwiftUI 化・Firebase Auth の keychain 事情・OS 新機能の
  即時追随・チーム構成の変更）で、感覚頼りの「なんとなく似せる」を避けて 1 対 1 の
  見た目パリティを取るための systematic な 5 フェーズを提供する。「Flutter を SwiftUI に
  置き換える」「Flutter 版と挙動をそろえて」「Dart のこの画面を Swift に移して」
  「UI parity を取って」「Flutter から iOS ネイティブに移行したい」などの
  **移行前提** のリクエストで発動する。「新規で Flutter アプリを作って」「Flutter で
  作りたい」は本スキルの対象外（新規開発では Flutter を選ばない方針。`mobile-app-scaffold`
  にネイティブで作るよう案内すること）。
version: 0.2.0
---

# flutter-swift-parity-port — 既存 Flutter → SwiftUI 移植 workflow (migration only)

## いつ使うか / 使わないか

| シチュエーション | 本スキル | 代わりに使うスキル |
|---|---|---|
| **既存の** Flutter アプリを SwiftUI に置き換える | ✅ 使う | — |
| Flutter 版と SwiftUI 版が並走している間、見た目を parity にしたい | ✅ 使う | — |
| Dart の特定画面を Swift に移す（部分移植） | ✅ 使う | — |
| **新規** で iOS / Android アプリを作る | ❌ 使わない | **`mobile-app-scaffold`**（既定は SwiftUI + Jetpack Compose） |
| 新規で「Flutter で作りたい」と要望が来た | ❌ 使わない | ネイティブ既定を説明したうえで、それでも Flutter を選ぶ強い理由があるかを確認する |
| 既存 SwiftUI アプリの機能追加 | ❌ 使わない | `mobile-update-deploy` |

> **AI OSI URI の方針**：新規モバイルアプリの既定スタックは **iOS = SwiftUI /
> Android = Kotlin + Jetpack Compose**。Flutter は既存資産の移行時にのみ扱う。
> 実運用（MustPost の Flutter→SwiftUI 移植）で得た結論：新規で Flutter を選ぶより、
> 最初からネイティブで書いた方が総コストが低い。詳細は `mobile-app-scaffold/SKILL.md`
> の冒頭「方針」参照。

---

**問題**: Flutter アプリの SwiftUI 移植を「見た目で似せる」感覚でやると、色が微妙に違う・
余白が違う・日本語が意訳される・ボタンが 1 個消える、といった小さなズレが積み重なり、
ユーザーが「別のアプリ感」を感じてしまう。感覚ではなく **diff で直す**。

**解決**: (1) Widget と View を全数対応付ける → (2) Dart と Swift を横並びで読んで違いを
列挙 → (3) 直す優先度をつけて batch で処理 → (4) 各 batch でビルド + Sim で目視 →
(5) 機能単位で PR。この 5 フェーズを 1 スクリーンずつ回す。

---

## Phase 1: Inventory（対応表を作る）

Flutter 側のウィジェット構造と SwiftUI 側の View 構造を **1 対 1 で表にする**。

### 手順

```
1. Flutter 側の lib/ 配下から全 StatelessWidget / StatefulWidget を列挙
   find <flutter_root>/lib -name '*.dart' -exec grep -l 'class .* extends State' {} +

2. SwiftUI 側の apps/ios/<App>/Features/ 配下から全 View struct を列挙
   grep -rn 'struct .* : View' apps/ios/<App>/Features/

3. 表にする（Markdown / スプレッドシート / 進捗ノート）
```

### 対応表の例

| 領域 | Flutter Widget | SwiftUI View | 状態 |
|---|---|---|---|
| ホーム | `lib/features/home/home_page.dart` `HomePage` | `Features/Home/HomeView.swift` `HomeView` | diff 済 |
| フィード | `lib/features/feed/feed_page.dart` `FeedPage` | `Features/Feed/FeedView.swift` `FeedView` | 未着手 |
| プロフィール編集 | `lib/features/profile/edit_profile_page.dart` | `Features/Profile/EditProfileView.swift` | 部分実装 |
| カメラ | `lib/features/camera/camera_page.dart` | `Features/Camera/CameraCaptureView.swift` | iOS 独自 (AVFoundation) |
| ボトムナビ | `BottomNavigationBar` in `home_shell.dart` | `TabView` in `AppShell.swift` | iOS 標準に**意図的に逸脱** |

**逸脱を許容するもの**（`references/deviation-policy.md` に定義）:
- Bottom nav: iOS は `TabView`、Android は `NavigationBar` を使うのが自然
- Back gesture: iOS 標準の swipe-back を使う（Flutter の Navigator に強制寄せしない）
- Modal presentation: iOS は `sheet` / `fullScreenCover` を使う
- Camera preview: `AVFoundation` / `PhotosUI` を使う（Flutter の `camera` パッケージを
  bridge しない）

これらは Golden として明示することで、後から「これも直して」の議論が消える。

---

## Phase 2: Diff（Dart と Swift を並列で読む）

1 画面ずつ、Dart のウィジェットと SwiftUI の View を **並べて読み**、以下の観点で
違いを列挙する:

### チェックリスト

| 観点 | Dart 側の探し方 | SwiftUI 側の探し方 |
|---|---|---|
| レイアウト | `Column` / `Row` / `Stack` / `Padding` の階層 | `VStack` / `HStack` / `ZStack` / `.padding()` |
| 色 | `Color(0xFF3366CC)` / `Colors.blue.shade600` | `Color(red:…, green:…, blue:…)` / `Color("PrimaryBlue")` |
| タイポ | `TextStyle(fontSize: 16, fontWeight: FontWeight.w600, letterSpacing: -0.2)` | `.font(.system(size: 16, weight: .semibold))` + `.tracking(-0.2)` |
| 余白・間隔 | `SizedBox(height: 12)` / `EdgeInsets.symmetric(...)` | `Spacer().frame(height: 12)` / `.padding(.horizontal, 16)` |
| アイコン | `Icons.favorite` (Material Icons) | `Image(systemName: "heart.fill")` (SF Symbols) |
| ラベル文字列 | `Text('お気に入り')`, `'投稿を保存しました'` などの String literal | `Text("お気に入り")` |
| 影 | `BoxShadow(color: …, blurRadius: 8, offset: Offset(0, 2))` | `.shadow(color: …, radius: 4, x: 0, y: 2)` (blurRadius/2 が radius) |
| 角丸 | `borderRadius: BorderRadius.circular(12)` | `.cornerRadius(12)` |
| ボタン | `ElevatedButton` / `TextButton` / `OutlinedButton` | `Button` + `.buttonStyle(.borderedProminent)` 等 |
| リスト | `ListView.builder` / `SliverList` | `List` / `LazyVStack` in `ScrollView` |

### 出力の形

画面ごとに `diff-<screen>.md` を書く:

```markdown
# HomeView diff (vs lib/features/home/home_page.dart)

- [ ] AppBar タイトル: Dart は「ホーム」 / Swift は「Home」 → 「ホーム」に統一
- [ ] お気に入りアイコン: Dart は `Icons.favorite_outline` / Swift は `heart` →
      SF Symbol `heart` は同等。塗りは Dart 側 outline なので Swift も outline のまま
- [ ] 投稿カードの角丸: Dart 12 / Swift 8 → Swift を 12 に
- [ ] 投稿カードの影: Dart blurRadius 8 offset (0,2) / Swift radius 6 y=1 →
      radius 4 (=8/2), y=2 に
- [ ] 「投稿する」ボタン背景: Dart `Color(0xFF3366CC)` / Swift `.blue` →
      DesignSystem/AppColors に `primaryAction = Color(red: 0.2, green: 0.4, blue: 0.8)` を追加
- [ ] お気に入りタップ後のトースト: Dart 「保存しました」 / Swift 「Saved」 → 「保存しました」に
- [ ] Bottom nav: **意図的な逸脱**。iOS は `TabView` を使う (deviation-policy.md ref)
```

---

## Phase 3: 優先度バッチで直す

diff リストが大きいとき、以下の**優先順**で処理する:

1. **P0 メインナビ**：AppShell / TabView / トップ導線。これがズレていると「アプリが違う」
2. **P1 頻度の高いフロー**：ホーム、投稿作成、カメラ、通知
3. **P2 詳細画面**：投稿詳細、コメント、プロフィール
4. **P3 設定・稀な導線**：設定各ページ、退会、問い合わせ

各 P で **1 コミット = 1 スクリーン** を目指す（レビュアが読みやすい粒度）。

### DesignSystem に寄せる

同じ色・タイポが 3 画面以上で使われる場合は SwiftUI 側の DesignSystem に定数化する:

```
apps/ios/<App>/DesignSystem/
├── AppColors.swift        // Color extension で Dart の 0xFFxxxxxx を Swift Color に写像
├── AppTypography.swift    // 見出し H1〜H4, Body, Caption などのフォント定義
├── AppSpacing.swift       // 8pt グリッドの CGFloat 定数
└── AppShapes.swift        // 角丸半径・影プリセット
```

Dart の `Color(0xFF3366CC)` を毎回書き下ろすと保守が破綻するので、DesignSystem に
名前をつけて呼ぶ。

---

## Phase 4: Batch ごとにビルド + 目視検証

1 batch (= 1 スクリーン or 関連する 2〜3 スクリーン) を直したら:

```
1. xcode_build_for_sim({ code_signing: "auto" })   # entitlements を保つ
2. xcode_sim_install_app + xcode_sim_launch_app
3. xcode_sim_open_url("mustpost://debug/signin?token=...")   # 必要なら Custom Token で入る
4. xcode_sim_tap で対象画面に遷移
5. xcode_sim_screenshot で PNG を取り、Flutter 側の同じ画面と目視で並べる
```

**Flutter 側スクショの取り方**（対比用）:

```bash
# Flutter 側のリポで
flutter run -d "iPhone 16 (Flutter用の別 Simulator)"
# 目的画面まで進んで
xcrun simctl io booted screenshot flutter-home.png
```

Cowork 上で `present_files` を使って 2 枚を並べて見せると、パリティのズレが一目でわかる。

### xcode_sim_describe_ui のコツ

`xcode_sim_describe_ui` は Accessibility ツリーを JSON で返すが、**巨大**（数百 KB）
なので、ターミナルに垂れ流すと context を焼く。必ず一度ファイルに保存してから
python3 で grep:

```
xcode_sim_describe_ui({udid, save_to: "/tmp/ui.json"})
python3 -c "
import json
d = json.load(open('/tmp/ui.json'))
for n in d['nodes']:
    lbl = n.get('AXLabel','')
    frm = n.get('frame','')
    if 'お気に入り' in lbl:
        print(lbl, frm)
"
```

これで label + frame だけ抜けるので、タップ座標の決定や差分検出が context を焼かずに済む。

---

## Phase 5: 機能単位でコミット + PR

1 機能領域 (Home / Feed / Profile 等) 完成したら:

```
git add apps/ios/<App>/Features/Home/
git commit -m "swiftui: match Flutter Home parity (labels/colors/spacing)"
git push
```

CI (`ios-release-auto.yml`) が回って TestFlight まで届く。Flutter ユーザーに実機で
差し替えて配布し、フィードバックを回収する。

---

## References

- `references/deviation-policy.md` — iOS ネイティブに寄せてよい / 寄せてはいけない判定
- `references/design-system-map.md` — Dart Material / Cupertino → SwiftUI 標準への写像表

---

## エラーハンドリング

| 症状 | 対処 |
|---|---|
| 色が「近いけど違う」 | Dart の hex を SwiftUI Color に写像するときに sRGB 変換ミス。必ず `Color(red: Double(0x33)/255, green: Double(0x66)/255, blue: Double(0xCC)/255)` の分数計算で書く |
| フォントが違って見える | Flutter の `TextStyle` は `letterSpacing` と `height`（行送り）を持つ。SwiftUI の `.tracking()` `.lineSpacing()` に写像する。特に `letterSpacing: -0.2` のような負値は忘れがち |
| 影が濃すぎ / 薄すぎ | Flutter `blurRadius: 8` → SwiftUI `radius: 4`（半分にする）。offset は同じ |
| 日本語ラベルが違う | Phase 2 の diff で **必ず String literal 単位で拾う**。翻訳せず逐語 |
| SF Symbol に対応するアイコンがない | `Image(systemName:)` を諦めて Material Icons を SwiftUI に持ち込むか、Assets にカスタム SVG を入れる。頻出は前者、少数は後者 |

---

## やってはいけないこと

- **新規プロジェクトを Flutter で起こす**：AI OSI URI の既定はネイティブ 2 本立て。
  Flutter を採用したい強い事情があるなら、それを明示的にユーザーと確認したうえで
  本プラグインの対象外として halt する
- **感覚で「似せる」**：diff を書かずに移植すると必ず後から発覚してリワークになる
- **日本語ラベルの意訳**：`「投稿する」` を `Post` に変えると Flutter ユーザーが違和感を持つ
- **全部を parity にしようとする**：iOS ネイティブが妥当な逸脱 (TabView / sheet 等) は
  逸脱として明示する。すべてを Flutter に寄せるとむしろ iOS ユーザーに違和感が出る
- **DesignSystem 化を後回し**：3 画面以上で使われる色/タイポが直リテラルのままだと、
  後で全画面直しになる。**移植中に**寄せる

---

## 関連スキル

- `mobile-app-scaffold` — **新規モバイルアプリの標準入口**（SwiftUI + Jetpack Compose の
  ネイティブ Golden Template）。Flutter からの移行後、SwiftUI 側で足りない機能を
  追加したくなったら、まずこの Golden Template のパターンに寄せる
- `ios-sim-auth-backdoor` — Sim で「サインイン済み」画面を出すための前提 skill
  （Flutter → SwiftUI 移植で認証状態を保ちながら差分検証するときに必須）
- `mobile-update-deploy` — 移植後の局所修正を回す
- `deploy-mobile-app` — 新規モバイル作成オーケストレータ（本スキルは呼ばない）
