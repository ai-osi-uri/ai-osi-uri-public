# android：Android アプリを手元で確かめる

ビルドと配信（Google Play）は CI で動くので、手元の Android Studio は要らない。
要るのは、エミュレーターでの起動確認と、署名の鍵（keystore）をパソコンで作るときだけ。

## 揃っているか
- `adb version` が通る
- エミュレーターが要る仕事なら `emulator -list-avds` に 1 つ以上ある
- keystore を作る仕事なら `keytool -help` が通る（Java が入っている）

## 手順
1. まず computer（本人のパソコンとつなぐ）を済ませる。
2. Android Studio を公式サイト（https://developer.android.com/studio）から入れてもらう。
3. 初回起動の案内どおりに SDK を入れ、「Device Manager」でエミュレーターを 1 つ作ってもらう。
4. `adb` と `emulator` が見つからなければ、SDK の場所を PATH に足す（本人の OK のもとで Claude が設定してよい）。
5. 上の「揃っているか」のコマンドで確かめる。

## Android の端末やパソコンが無いとき
エミュレーターでの確認は飛ばし、Google Play の内部テストに上げて本人の端末で確かめる道を案内する。
