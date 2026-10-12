# mac：iPhone アプリを手元で確かめる

ビルドと配信（TestFlight・App Store）は CI（GitHub Actions・Xcode Cloud）で動くので Mac は要らない。
Mac が要るのは、シミュレーターでの起動確認・Xcode のプロジェクトの修理・キーチェーンにある鍵を使うときだけ。

## 揃っているか
- 本人のパソコンのシェルで `sw_vers` が通る（macOS）
- `xcodebuild -version` が通る（Xcode が入っていて、一度起動済み）
- シミュレーターが要る仕事なら `xcrun simctl list devices available` に iPhone がある

## 手順
1. まず computer（本人のパソコンとつなぐ）を済ませる。
2. Xcode が無ければ、Mac の App Store から入れてもらう（大きいので時間がかかると先に伝える）。
3. 入ったら一度 Xcode を起動して、追加の部品のインストールと利用条件の同意を済ませてもらう。
4. `sudo xcode-select -s /Applications/Xcode.app` が要る場合は、本人に実行してもらう（パスワードは本人が入れる）。
5. 上の「揃っているか」のコマンドで確かめる。

## Mac が無いとき
シミュレーターでの確認は飛ばし、CI でビルドして TestFlight で本人の iPhone で確かめる道を案内する。
