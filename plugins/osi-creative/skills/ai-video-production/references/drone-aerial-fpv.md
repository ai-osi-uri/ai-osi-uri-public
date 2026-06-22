# ドローン空撮モード（インタラクティブ FPV 空撮）

「動画を作りたい」が**風景・都市・自然・観光・空撮っぽい**ときに使う、対話型のワンショット空撮生成レシピ。
ユーザーは日本語でイメージを言うだけ。こちらがヒアリング→確定→生成まで導く。

確立元：2026-06 video-creator-market（イスタンブール／東京／城）。空撮はカメラムーブモードの1プリセット。

> **最新の正しい作法はこちら（必読）**：`references/cinematic-camera-move.md`。
> 要点＝**ルート＋番号＋動き説明ラベル付きのムーブボード**を作り（線はコードで1本だけ描く）、それを **Seedance 2.0 `reference-to-video` の参照画像として渡す**（`image-to-video` は1フレーム目に赤線が映るので使わない＝#17）。動画プロンプトは短く「線の通りに飛べ／線は出すな」。
> 以下の「6ビート」はそのラベル文面の雛形として使う。落とし穴は #17（reference-to-videoで解決）と #18（モーション予算）を参照。

---

## いつ発動するか

- 「ドローン（空撮）動画を作って」「上空から○○を撮ったような動画」「FPVっぽい映像」
- 場所＋雰囲気だけ言われた（例：「夕暮れの東京を上から」「京都を空撮で」）
- 観光PR・オープニング・ブランドの導入カットで“迫力ある俯瞰”が欲しいとき

純粋な人物・対話・商品クローズアップ等はこのモードではない（通常の Phase フローへ）。

---

## ヒアリング（AskUserQuestion で一括）

イメージが曖昧なら、まず1イメージを言ってもらい、空撮向きと判断したら次を確認する。

| 質問 | 選択肢の例 |
|---|---|
| 場所・被写体 | 都市（東京/京都/ドバイ…）/ 自然（富士山・海岸・渓谷…）/ ランドマーク1つ |
| 時間帯・雰囲気 | 夕暮れ（推奨）/ ブルーアワー / 朝もや / 夜景 / 快晴 |
| 迫力レベル | **迫力重視** / 優雅 / 標準 |
| 尺・縦横 | 15秒・16:9（推奨）/ 10秒 / 9:16（Reels・TikTok） |
| 音 | FX（環境音）のみ（推奨）/ なし / BGM追加 |

「迫力のあるドローン空撮にしますか？」を必ず一度きく（このモードの体験の核）。

---

## 迫力レベル → 動きワードの対応（プロンプトに反映）

| レベル | カメラの動き（動画プロンプトに入れる語） |
|---|---|
| **迫力重視** | low fast skim, rapid push-in, sharp climb, dynamic banking orbit, whip pull-back, explosive grand reveal |
| 標準 | smooth skim, push-in, climb, hero orbit, pull-back, grand reveal |
| 優雅 | slow graceful glide, gentle rise, slow elegant orbit, soft drift, serene wide reveal |

---

## 生成手順（2ステップ・各ユーザー確認）

### STEP 1: クリーンなキーフレーム（起点フレーム）
`generate_image`（model: `nano-banana-pro`、4K、アスペクトは尺に合わせ 16:9 か 9:16）。
画像プロンプトの型：

```
Cinematic aerial drone photograph of {場所} at {時間帯}, {被写体/ランドマーク} as the focal point,
{雰囲気・空・光}, atmospheric haze, strong depth and scale, like the opening frame of a luxury aerial drone film.
Photoreal, 4K cinematic color grading. No text, no graphic overlays, no path lines.
```

> 絵コンテ（俯瞰図＋赤線ルート）は作らない／渡さない。作る場合も**プランニング専用**。i2v の入力に渡すと1フレーム目に映り込む（#17）。

### STEP 2: 動画化（Seedance 2.0 i2v）
`submit_video`（model: `seedance20-i2v`）→ `check_status`。クリーン画像を起点に、6ビートのルートを文章で指示。

```
{尺}-second cinematic FPV drone flight over {場所} at {時間帯}, one continuous shot following six beats:
(1) {skim} low over {手前の要素}, (2) {push-in} toward {主役}, (3) {climb} opening up the skyline,
(4) {orbit} around {主役}, (5) {pull-back} to reveal {周辺}, (6) {grand reveal} high over {全景}.
No title cards, no split screen, no diagrams, no text, no red lines/arrows/markers at any point.
Photoreal {時間帯} grading, {迫力レベルの動きワード}. {音: no music, only ambient FX sounds / no audio}.
```

設定：`duration_seconds`=15（or 10）、`aspect_ratio`=16:9（or 9:16）。

### 検証
ffmpeg で1フレーム目を抜いて、線・文字・分割が無くクリーンに始まるか必ず確認：
```
ffmpeg -i out.mp4 -vf "select=eq(n\,0)" -vframes 1 first.png
```

---

## そのまま使えるお題例

- 「夕暮れの東京、高層ビルの谷間を抜けて東京タワーへ向かうFPV、15秒、迫力重視」
- 「ブルーアワーの京都、五重塔の上空を旋回、15秒、優雅」
- 「朝もやの富士山と湖、湖面すれすれから上昇して山頂を見せる、15秒」
- 「夜のドバイ、ビル群を抜けて世界一の高層ビルへ上昇、9:16、迫力重視」

被写体を差し替えるだけで同質の空撮が作れる。コスト目安：画像 nano-banana-pro $0.30 ＋ Seedance 2.0 15秒（≒$3〜4）。
