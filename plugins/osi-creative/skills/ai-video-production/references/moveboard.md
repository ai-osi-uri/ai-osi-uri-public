# ムーブボード（線でカメラを動かす）— どんな画像でも

「1枚の画像（写真でも絵画でもイラストでも）＋カメラの動き → 動画」を最短で作る対話型レシピ（vp-moveboard の正本）。仕上がりはシネマティックにもフラットにも、用途次第。
**ドローン空撮はこのモードの1プリセット**。被写体を問わず、同じ「ラベル付きムーブボード（絵コンテ）を**参照画像**にして、Seedance 2.0 **reference-to-video** で線どおりに動かす」で作る。

確立元：2026-06 video-creator-market。元ネタ（ISTANBUL/SNSのテク）の核心は **(a) ルート＋番号＋動き説明ラベル付きの絵コンテを“参照画像(reference)”として渡す → (b) 短い動画プロンプトで「線の通りに飛べ／線は出すな」**。
重要：**入力モードは `reference-to-video`（参照）であって `image-to-video`（1フレーム目固定）ではない**。i2v だと赤線が1フレーム目に映り込む（`pitfalls.md` #17）。参照モードなら線は出力に出ない。

---

## いつ発動するか

- 「この画像を動かして」「絵の中を動くみたいに」「商品をかっこよく回して」「部屋の中を歩くlike」「ドローン空撮」
- 場所・被写体・絵だけ渡されて「動かして/動画にして」と言われた

人物の会話・複数人芝居・尺の長いストーリー動画はこのモードではなく通常 Phase フローへ。

---

## 被写体プリセット（6種）

| # | プリセット | 典型カメラムーブ | 用途 |
|---|---|---|---|
| 1 | 空撮（実景） | 低空スキム→push-in→climb→orbit→pull-back→reveal | 観光PR・都市・自然・オープニング |
| 2 | 名画・アートの潜り込み | slow dive / parallax / push-in into the scene | アート系SNS・導入・教養コンテンツ |
| 3 | 商品ヒーロー | orbit / push-in / slow rotate / rack focus | EC・広告・ブランド |
| 4 | 建築・内装ウォークスルー | dolly forward / crane up / doorway pass-through | 不動産・施設紹介 |
| 5 | 人物・被写体の微動 | subtle parallax / slow push-in（“リビングフォト”） | ポートレート・SNS |
| 6 | 抽象・テクスチャ | flowing drift / slow zoom | 背景・つなぎ・ロゴ前 |

「迫力レベル（迫力重視／優雅／標準）」は全プリセット共通で動きの強さを切替（`drone-aerial-fpv.md` の対応表を流用）。

---

## カメラムーブ・ボキャブラリ（共通語彙）

push-in / pull-back / orbit(left|right) / fly-through(dive into the scene) / parallax(layers separate with depth) /
dolly(forward|back) / crane(up|down) / tilt / whip / rack focus。
プロンプトでは「one continuous shot」と動きの順番を明示すると安定。

---

## 対話フロー（AskUserQuestion）

1. **元画像はある？** → ある（アップロード/自前/既存URL）／ない（生成する）
2. **被写体タイプ**（上の6プリセット）
3. **カメラムーブ**（プリセット推奨を提示。例：名画なら「潜り込み＋パララックス」）
4. **迫力レベル**（迫力重視／優雅／標準）
5. **尺・縦横・音**（15秒・16:9・FXのみ が既定）

---

## ★ ムーブボード承認ループ（動きを“画像”で先に合意する）

このモードの中核。**最終動画を作る前に、カメラの動きを1枚の絵（ムーブボード）で見せ、ユーザーの承認を得る**。動きをテキストだけでなく目で合意できるので、出戻りが激減する。

1. **起点画像を用意**（生成 or 受領）。これは最終動画の1フレーム目になる**クリーン画像**。
2. **ムーブボードを提示**：ベース画像に、カメラの動き（赤い軌道＋矢印＋①②…の番号＋各点の短い動き説明ラベル）を重ねた“動きの絵”を作って提示する。**線は AI に描かせず Python(Pillow) でコード描画**する（AIに描かせると2本目・余計なループが出る。詳細は下の STEP2）。
3. **承認 or 調整ループ**：ユーザーに「この動きでOK？／どこを変える？」と問う（`AskUserQuestion`）。
   - 例の調整：「もっと寄る」「逆回りで」「最後に上昇を足す」「①を速く・④をゆっくり」。
   - 返答どおり**通過点（コードの座標）を直して描き直す**。納得（承認）まで反復。座標で持つので正確かつ一意に直せる。
4. **動画化へ**：承認されたムーブボードを **そのまま参照画像にして** `reference-to-video` に渡す（下の生成ステップ STEP2）。動画プロンプトは短くてよい（振り付けは画像のラベルが担う）。
5. **ムーブボードは成果物として残す**（提案資料・記事で「この動きで作ります」と提示できる）。

> 重要：ムーブボード（赤い線・番号・説明ラベル入り）は **参照画像(reference)として渡す**。`image-to-video` ではなく **`reference-to-video`** を使うこと。i2v は渡した画像を1フレーム目にするため赤線が映り込むが（#17）、reference モードは線を出力に出さずに“指示”としてだけ使える（＝元ネタ「only use it for instructions」が成立）。

---

## 生成ステップ

### STEP 1: ベース画像
- 画像が**ある**：それを使う（名画・商品・自前写真など）。
- 画像が**ない**：`generate_image`（`nano-banana-2`、アスペクトは尺に合わせる）でクリーンな1枚を作る。
  - 画像プロンプト型：`{被写体の具体描写}, {光・雰囲気}, strong depth and layered foreground/midground/background, cinematic, 4K. No text, no overlays, no path lines.`
  - ※「奥行き（layered depth）」を入れると、後段のパララックス/潜り込みが効きやすい。

### STEP 2: ムーブボード（参照画像）を作る — **線はコードで描く**
カメラのルートを **AIに描かせない**。AIに線を描かせると2本目や勝手なループが出て解釈がブレる。手順：
1. **パスはAIが設計**：被写体を見て「どこを通すと美しいか」通過点（数点）を決める（START→…→END、一方向）。
2. **線はコードで1本だけ描画**：Python(Pillow)で通過点を Catmull-Rom 等で滑らかな**1本の連続曲線**にし、ベース画像へ赤線＋進行方向の矢印＋**番号＋短い動き説明ラベル**を重ねる。
   - ラベルは元ネタ準拠で各区間の“動きの意味”を書く（例：`PUSH IN / strong motion`、`CLIMB / rise quickly`、`HERO ORBIT / around the landmark`、`PULL BACK / widen`、`GRAND REVEAL / finish high`）。これが**速度・高さ(3D)・orbit といった線だけでは表せない情報**を補う。
   - **ループ(orbit)は描いてよい**。隣に `ORBIT` ラベルがあれば曖昧にならない（消すのは“ラベル無しの曖昧さ”だけ）。
3. このムーブボードを **承認ループ**（上記）で確定。

### STEP 3: 動画化（Seedance 2.0 **reference-to-video**）
`submit_video`（model: `bytedance/seedance-2.0/reference-to-video`）→ `check_status`。
**承認済みムーブボードを `image_url`（参照画像）に渡す。** `seedance20-i2v`（1フレーム目固定）は使わない。
動画プロンプトは**短く**（振り付けは画像のラベルが担う）。型：
```
{尺}-second cinematic {FPV flight / camera move} over {被写体}, following the numbered red route in order as the camera path.
Do not render the red lines, numbers or label boxes — use them only as instructions.
One continuous shot, {迫力レベルの動きワード}. {音: no music, only ambient FX sounds / no audio}.
```
設定：`duration_seconds`=15(or10)、`aspect_ratio`=16:9(or 9:16)。

### 検証
`reference-to-video` なら赤線は出力に出ない（頭トリム不要）。それでも ffmpeg で数フレーム抜き、線・文字が無いこと＆経路に沿っているかを目視：
```
for t in 0 5 10 14; do ffmpeg -y -ss $t -i out.mp4 -frames:v 1 chk_$t.png; done
```
※ 360°など大きい動きが回りきらない/距離差でカットが入る場合は `pitfalls.md` #18 を参照（動きを詰め込みすぎない・一定距離・速度で詰める）。

---

## プリセット別プロンプト雛形（抜粋）

- **名画・アートの潜り込み**：`15-second cinematic slow dive into this painting, parallax depth as foreground and background separate, gentle push-in toward the focal point, the artwork stays intact. No text/lines.`
- **商品ヒーロー**：`12-second product hero shot, slow 180° orbit around {product} with soft studio light, rack focus to the logo, premium feel. No text.`
- **建築・内装**：`15-second smooth walkthrough, dolly forward through {room}, pass through the doorway, crane up to reveal the space. No text.`
- **人物の微動**：`8-second living photo, very subtle parallax and breath-like motion, slow push-in on the subject's eyes. Keep identity intact. No text.`

詳細な空撮の6ビートは `drone-aerial-fpv.md` を参照。

---

## ⚠️ 著作権の注意（必読）

- **現存・近年の作家の作品（例：エッシャー等）は著作権が生きている**ことが多い。デモ・配布例・テンプレに使わない。
- 安全に使えるのは：**パブリックドメインの古典作品**（例：ゴッホ／フェルメール／葛飾北斎 等、十分に古いもの）、**自前の作品**、**生成したオリジナル画像**。
- 顧客案件では、入力画像の**権利確認**を必ず取ってから動かす。
- 人物の実写を扱う場合は肖像権・本人同意に配慮する。
