# Dart Material/Cupertino → SwiftUI 標準の写像早見表

## 色

```dart
// Dart
Color(0xFF3366CC)                       // ARGB, alpha 先頭
Colors.blue.shade600                    // Material palette
```

```swift
// Swift
Color(red: 0x33/255.0, green: 0x66/255.0, blue: 0xCC/255.0)
// or DesignSystem に登録して:
AppColors.primary
```

**注意**: Dart の 0xFF は alpha channel。SwiftUI の `Color(red:green:blue:opacity:)` は
デフォルト opacity=1 なので指定不要。

## タイポグラフィ

| Dart TextStyle | SwiftUI Font |
|---|---|
| `TextStyle(fontSize: 12)` | `.font(.system(size: 12))` |
| `TextStyle(fontSize: 14, fontWeight: FontWeight.w500)` | `.font(.system(size: 14, weight: .medium))` |
| `TextStyle(fontSize: 16, fontWeight: FontWeight.w600)` | `.font(.system(size: 16, weight: .semibold))` |
| `TextStyle(fontSize: 20, fontWeight: FontWeight.bold)` | `.font(.system(size: 20, weight: .bold))` |
| `letterSpacing: -0.2` | `.tracking(-0.2)` |
| `height: 1.4` (行送り倍率) | `.lineSpacing(fontSize * 0.4)` |
| `color: Colors.red` | `.foregroundColor(.red)` / `.foregroundStyle(.red)` |

## 余白・レイアウト

| Dart | Swift |
|---|---|
| `Padding(padding: EdgeInsets.all(16), child: ...)` | `... .padding(16)` |
| `EdgeInsets.symmetric(horizontal: 16, vertical: 8)` | `.padding(.horizontal, 16).padding(.vertical, 8)` |
| `EdgeInsets.only(top: 12)` | `.padding(.top, 12)` |
| `SizedBox(height: 12)` | `Spacer().frame(height: 12)` or `.padding(.top, 12)` on next |
| `SizedBox(width: 8)` | `Spacer().frame(width: 8)` |
| `Row(children: [...])` | `HStack { ... }` |
| `Column(children: [...])` | `VStack { ... }` |
| `Stack(children: [...])` | `ZStack { ... }` |
| `Expanded(child: ...)` | `... .frame(maxWidth: .infinity)` |
| `Center(child: ...)` | `... .frame(maxWidth: .infinity).frame(maxHeight: .infinity)` |

## 装飾

| Dart BoxDecoration | Swift modifier |
|---|---|
| `borderRadius: BorderRadius.circular(12)` | `.cornerRadius(12)` |
| `border: Border.all(color: Colors.grey, width: 1)` | `.overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.gray, lineWidth: 1))` |
| `color: Colors.white` | `.background(Color.white)` |
| `boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 8, offset: Offset(0, 2))]` | `.shadow(color: Color.black.opacity(0.15), radius: 4, x: 0, y: 2)` **← blurRadius / 2** |

## アイコン

| Material Icon | SF Symbol |
|---|---|
| `Icons.favorite` | `heart.fill` |
| `Icons.favorite_border` | `heart` |
| `Icons.share` | `square.and.arrow.up` |
| `Icons.settings` | `gearshape` |
| `Icons.arrow_back` | `chevron.backward` |
| `Icons.arrow_forward` | `chevron.forward` |
| `Icons.close` | `xmark` |
| `Icons.check` | `checkmark` |
| `Icons.add` | `plus` |
| `Icons.notifications` | `bell` / `bell.fill` |
| `Icons.person` | `person` / `person.fill` |
| `Icons.camera_alt` | `camera` / `camera.fill` |
| `Icons.photo_library` | `photo.on.rectangle` |
| `Icons.search` | `magnifyingglass` |
| `Icons.more_vert` | `ellipsis` |
| `Icons.chat_bubble_outline` | `bubble.left` |
| `Icons.location_on` | `location.fill` |
| `Icons.calendar_today` | `calendar` |

## ボタン

| Dart | Swift |
|---|---|
| `ElevatedButton(onPressed: fn, child: Text('OK'))` | `Button("OK", action: fn).buttonStyle(.borderedProminent)` |
| `TextButton(onPressed: fn, child: Text('Cancel'))` | `Button("Cancel", action: fn)` (plain) |
| `OutlinedButton(onPressed: fn, child: Text('X'))` | `Button("X", action: fn).buttonStyle(.bordered)` |
| `IconButton(icon: Icon(...), onPressed: fn)` | `Button { fn() } label: { Image(systemName: "...") }` |

## リスト

| Dart | Swift |
|---|---|
| `ListView.builder(itemBuilder: ...)` | `List { ForEach(items) { item in ... } }` |
| `SingleChildScrollView(child: Column(...))` | `ScrollView { VStack(...) }` |
| `SliverList(delegate: ...)` | `LazyVStack { ForEach(...) }` in `ScrollView` |
| `RefreshIndicator(onRefresh: fn, child: ...)` | `.refreshable { await fn() }` |
| `ListView.separated(separatorBuilder: ...)` | `List { ForEach {...} }` with `.listRowSeparator(.visible)` |

## 状態管理

| Flutter | SwiftUI |
|---|---|
| `StatefulWidget` + `setState` | `struct X: View` + `@State` |
| `Provider` / `Riverpod` | `@StateObject` / `@EnvironmentObject` |
| `StreamBuilder` | Combine `@Published` + `.onReceive` or `AsyncSequence` |
| `FutureBuilder` | `.task { ... }` + `@State` for result |
| `ChangeNotifier` | `ObservableObject` + `@Published` |

## Navigation

| Flutter | SwiftUI |
|---|---|
| `Navigator.push(context, MaterialPageRoute(...))` | `NavigationLink(destination: ...)` / `.navigationDestination(for:)` |
| `Navigator.pop(context)` | `dismiss()` (@Environment(\\.dismiss)) |
| `showDialog(context: ..., builder: ...)` | `.alert(...)` / `.confirmationDialog(...)` |
| `showModalBottomSheet(...)` | `.sheet(isPresented:)` / `.presentationDetents([.medium])` |
| Named routes (`Navigator.pushNamed`) | `NavigationStack` + `@Published var path` |

## その他

| Dart | Swift |
|---|---|
| `CircularProgressIndicator()` | `ProgressView()` |
| `LinearProgressIndicator(value: 0.5)` | `ProgressView(value: 0.5)` |
| `TextField(controller: ..., decoration: ...)` | `TextField("placeholder", text: $binding)` |
| `TextFormField(validator: ...)` | 標準の `TextField` + 手動 validation |
| `SnackBar` | `.overlay` + auto-dismiss `Task { try await Task.sleep(...) }` or ToastKit |
| `Toast` (Fluttertoast) | 同上 |
| `SafeArea(child: ...)` | 標準で safe area 適用済み。`.ignoresSafeArea()` で解除 |
