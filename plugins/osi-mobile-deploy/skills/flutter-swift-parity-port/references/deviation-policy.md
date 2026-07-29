# iOS ネイティブに寄せてよい / 寄せてはいけない逸脱ポリシー

Flutter → SwiftUI 移植で「parity=100%」を目指すと、iOS ユーザーに違和感が出る領域が
ある。以下の分野は iOS ネイティブに寄せてよい（=Flutter とわざと違うのが正解）:

## OK: iOS ネイティブに寄せる（parity 違反にしない）

| 領域 | Flutter 側 | SwiftUI 側 | 理由 |
|---|---|---|---|
| ボトムナビ | `BottomNavigationBar` (Material) | `TabView(selection:)` | iOS ユーザーは Tab bar に慣れている。Material 風に寄せると「なぜか分厚い bar」になる |
| モーダル | `showModalBottomSheet` / `Navigator.push(...)` | `.sheet(isPresented:)` / `.fullScreenCover(isPresented:)` | iOS の sheet は drag-to-dismiss 前提。ここを Material に寄せると触感が異物 |
| Back gesture | 自前の `AppBar` に戻るボタン | 標準の swipe-back + `.navigationTitle` | swipe-back を殺すと iOS ユーザーはストレスを感じる |
| アイコン | Material Icons | SF Symbols | 同義のアイコンは SF Symbols に置換。無いものだけ Material を持ち込む |
| ハプティクス | `HapticFeedback.lightImpact()` | `UIImpactFeedbackGenerator(style: .light)` | 感触は OS 側に寄せる |
| キーボード付随 | `MediaQuery.of(context).viewInsets.bottom` | `.ignoresSafeArea(.keyboard, edges: .bottom)` | 標準の safe area 挙動に任せる |
| Pull-to-refresh | `RefreshIndicator` (Material) | `.refreshable {}` (iOS 15+) | iOS 標準のスピナ |
| ロング押下メニュー | `PopupMenuButton` | `.contextMenu {}` | iOS の Peek-and-Pop 風の触感を保つ |
| カメラ | `camera` パッケージ | AVFoundation + `PHPickerViewController` | ネイティブ SDK を使う |
| 写真ピッカー | `image_picker` | `PhotosPicker` (iOS 16+) | ネイティブに任せる |
| 通知権限 | `firebase_messaging` の permission flow | `UNUserNotificationCenter` | Firebase iOS SDK が結局これを呼ぶ |
| Deep link | `uni_links` / GoRouter | `.onOpenURL{}` + AppDelegate `application(_:open:...)` | どちらもネイティブ API を叩くだけ |

## NG: 逸脱ではなく parity を取るべき領域

| 領域 | 理由 |
|---|---|
| 主要色（primary / accent） | ブランドカラーは 100% 一致させる。`0xFF3366CC` → `Color(red: 0.2, green: 0.4, blue: 0.8)` に厳密写像 |
| ロゴ・アイコン画像 | Assets を Flutter プロジェクトから持ってきて `.xcassets/` にコピー |
| 日本語ラベル | Dart の `Text('...')` の string literal をそのままコピー。翻訳しない |
| 主要な余白 (投稿カードの padding など) | Dart `EdgeInsets.all(16)` → SwiftUI `.padding(16)` |
| 主要動線の順序 | 「ホーム → 投稿 → 通知 → プロフィール」の順は Dart 側の順序を維持 |
| 認証フロー | Google / Apple / メール の順、ボタン文言、エラーメッセージは全部 parity |
| 空状態 (empty state) | 「まだ投稿がありません」等の文言・イラストは同じもの |

## グレーゾーン（ケースバイケース）

| 領域 | 判定基準 |
|---|---|
| Animation | Flutter の `AnimatedContainer` で手作りしたトランジションは、SwiftUI の `.animation(.spring())` で置換して OK。**動きの秒数** (0.3s → 0.3s) は合わせる |
| フォント | 独自フォント使用時のみ .otf/.ttf を Xcode に登録して合わせる。システムフォント使用時は SF Pro / Roboto の差は許容 |
| ダークモード | Dart が対応していないなら Swift も v1 では light-only で OK。将来対応するときに合わせて追加 |

## 逸脱を残す時のドキュメント化

逸脱を「意図的に」入れる場合、コード上に理由コメントを残す:

```swift
// DEVIATION: Flutter uses BottomNavigationBar; iOS TabView is the natural
// native equivalent. See plugins/osi-mobile-deploy/skills/
// flutter-swift-parity-port/references/deviation-policy.md
TabView(selection: $selectedTab) { ... }
```

コミットメッセージにも「意図的な逸脱」と書き、レビュアが「これ Flutter と違う」と
指摘してきたときに議論が短くなる。
