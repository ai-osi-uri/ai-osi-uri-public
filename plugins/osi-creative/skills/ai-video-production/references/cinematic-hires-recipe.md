# 高解像度・シネマティックAI動画レシピ（Infinite Peace系）★デフォルト

画像起点・高解像度シネマティック動画の標準レシピ。本スキルの **デフォルト生成モード（モードA）** の中核。
2026-06 のセッションで「cyborg.digitalart の Infinite Peace 系動画」に寄せる検証から確立。

> SKILL.md の「モードA: 高解像度シネマティック・パイプライン」がこのファイルを必読参照する。
> ナレーション付き2〜3分尺の長尺（モードB）は SKILL.md の Phase 0〜9 を使う。両者は併用可。

---

## 0. 結論（最重要）

- 動画のクオリティは **入力する静止画1枚で9割決まる**。プロンプトより画像作りに時間をかける。
- 「派手な動き（回転）」より **被写体と等速の追従＋緩やかなアングル変化** の方が、狙って出せて品が出る。
- 「キラキラ」「影の綺麗さ」は **画像 → 動画 → 仕上げ編集** の3層の積み重ね。特に仕上げの発光（bloom）が効く。

---

## 1. 使用モデルと正確なエンドポイント

### 画像生成（キービジュアル）
- **nano-banana / Gemini 3 Pro Image**（`model_tier: pro`, `resolution: 4k`, `aspect_ratio: 9:16`）
  - ツール：`mcp__nano-banana__generate_image`
- 写実・シネマティックな光の質感は現状トップ。出力 3072×5504。
- 文字を画像内に入れたい時だけ GPT Image 2 を部分併用。

### 動画生成（image-to-video / fal経由「AI OSI URI Creative」コネクタ）
| 用途 | model（fal endpoint） | 備考 |
|---|---|---|
| 高解像度の本命 | `fal-ai/kling-video/v3/4k/image-to-video` | 出力 約2148×3856。Kling 3.0 4K。**これが本レシピの基準** |
| 標準 | `fal-ai/kling-video/v3/pro/image-to-video` | 約1076×1924。速い・安い |
| 激しい動き | Seedance 2.0（fal）| モーション最強・合議ベンチ首位 |
| 最高画質ヒーロー | `fal-ai/veo3.1/image-to-video` | ※現行 fal コネクタは **ポーリング不可（Unprocessable Entity）**。引き出せないので当面は Kling を使う |

> モデルは fal 1本で endpoint 直指定すれば最新も呼べる。`fal_list_models` の既定は Kling 2.5 / Veo 3 止まりなので **必ず endpoint を直書きする**。
> 投入は `fal_submit_video`、状態確認は `fal_check_status`（i2v 用に画像URL/参照を渡す）。

### 音楽
- `fal_submit_music`（Stable Audio）, 30〜35秒, 壮大で穏やかなシネマティック。

---

## 2. 静止画プロンプトの型（構図・パース）

元動画の「感動」の正体 = **後ろ姿の孤独な人物 × 強い遠近感 × 超現実の大景**。

必須要素を必ず盛り込む:

```
- Shot from BEHIND a lone figure walking AWAY from camera（後ろ姿・奥へ歩く）
- Extreme LOW ground-level camera（地面近くの低カメラ）
- Foreground grass/objects loom close to the lens, tunnel-like depth（手前の要素が大きく迫る）
- Wide-angle lens, strong dramatic perspective, vanishing point（広角・強いパース・消失点）
- An ENORMOUS celestial/surreal element on the horizon（巨大な月/太陽/鏡面など）
- Hyperrealistic 35mm cinematic film still, 4K, 9:16
- negative: facing camera, front view, high angle
```

---

## 3. ライティングの型（影の美しさ・境界のシャープさ）

「影が綺麗・境界がはっきり」は **硬い低逆光** で作る。盛りすぎた霧/ブルームはシルエットを溶かすので被写体には乗せない。

```
- HARD low backlight from the light source directly ahead（低い位置の硬い逆光）
- Bright crisp RIM LIGHT outlining the body（体の縁に強いリムライト＝境界がくっきり）
- Subtle FILL LIGHT on one side（片側に回り込む光＝純シルエットでなく立体感）
- Long sharp SHADOW stretching toward the camera（カメラ側へ伸びる長くシャープな影）
- Subject SHARP in focus, HIGH CONTRAST, deep shadows（被写体はシャープ・高コントラスト）
- Sparkle/bokeh/haze ONLY in background & around the light（キラキラ・霧は背景だけに限定）
- Clear walking STRIDE pose（歩く一歩を明確に：片脚前・腕振り・裾と髪がなびく）
- negative: flat lighting, pure flat black silhouette, hazy subject, washed out, low contrast
```

---

## 4. キラキラの作り方（3層）

1. **画像**: backlight bloom + 大量の soft round bokeh orbs + fireflies + luminous pollen + sparkling dew + volumetric moonbeams + faint aurora + rainbow lens flare。
2. **動画**: 「草が風でなびき、穂先や露が光を反射して glint / sparkle する」と動きを明示。
3. **仕上げ（ffmpeg bloom）**: ハイライトを抽出してぼかし screen 合成（§6）。これが“人がやる光のレイヤー”の擬似再現で、最も効く。

---

## 5. カメラモーションの型（追従）

回転（barrel roll）より、被写体と一緒に動く追従が自然。

```
- Smooth cinematic TRACKING / FOLLOWING SHOT from behind
- Camera travels with the subject at exactly their walking speed (steadicam/gimbal)
- The angle gradually & subtly shifts as they move（アングルが徐々に変わる）
- Foreground sweeps past with strong parallax
- no spinning, no abrupt motion
```
※「世界が回る」演出が欲しい時だけ `barrel roll / dutch rotation / camera rolls 360°` を明示（当たり外れあり、数回回して選ぶ）。

---

## 6. 仕上げ ffmpeg コマンド集

### Bloom（発光）＋グレード（縦1080配信用）
```bash
ffmpeg -y -i IN.mp4 -filter_complex \
"[0:v]scale=1080:1920[s];[s]split=2[base][bri]; \
 [bri]curves=all='0/0 0.72/0.26 1/1',gblur=sigma=9[glow]; \
 [base][glow]blend=all_mode=screen:all_opacity=0.42,eq=saturation=1.1:contrast=1.06[v]" \
-map "[v]" -an -c:v libx264 -preset ultrafast -crf 20 -pix_fmt yuv420p bloom.mp4
```
> 4K素材に直接かけると重くタイムアウトしやすい。**1080へscaleしてから**かけると安定。マスターは別途4Kで保管。

### BGMミックス（フェード付き）
```bash
ffmpeg -y -i bloom.mp4 -i bgm.wav \
-filter_complex "[1:a]atrim=0:10,afade=t=in:st=0:d=1.2,afade=t=out:st=8.3:d=1.7,volume=0.9[aud]" \
-map 0:v -map "[aud]" -c:v copy -c:a aac -b:a 192k -shortest FINAL.mp4
```

### 複数シーンをクロスフェード連結（縦1080・24fps正規化済み前提）
```bash
# 各クリップを先に正規化
ffmpeg -y -i SCENE.mp4 -t 5 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24,format=yuv420p,setsar=1" -an -c:v libx264 -preset veryfast -crf 19 n_X.mp4
# xfade連結（offsetは各クリップ長-0.6で前から積算）
ffmpeg -y -i n_A.mp4 -i n_B.mp4 -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.6:offset=4.4[v]" -map "[v]" -c:v libx264 -preset veryfast -crf 19 out.mp4
```

---

## 7. 運用上の注意（落とし穴）

- **fal 並列制限**: 短時間に大量投入すると `Forbidden`。5本ずつ＋間に待機。発生したら数十秒〜数分待って1本ずつ再投入。クレジット残高も確認。
- **ポーリング間隔**: 投入後 40〜60秒待ってから `fal_check_status`。Kling 3.0 4K は2〜4分。
- **保存先**: fal出力は `FAL_OUTPUT_DIR`（Drive）に保存される。Cowork で提示するには outputs フォルダへコピー（curlでsource URL取得が確実）。
- **edit モードは解像度が落ちることがある**（768px等）。高解像度を保ちたい時は edit より **同条件で再 generate**。
- **bloom を4Kに直接かけない**（タイムアウト）。1080化してから。

---

## 8. 標準パイプライン（このレシピ版＝モードA）

```
1. キービジュアル静止画を nano-banana pro 4k で生成（構図§2＋ライト§3＋キラキラ§4）
   → ユーザー確認（構図が刺さるか）
2. 確定画像を Kling 3.0 4K（§1）で追従カメラ（§5）動画化
3. ffmpeg で bloom＋グレード（§6）→ BGMミックス（§6）
4. 複数シーンなら xfade 連結（§6）
5. 4Kマスター＋配信用1080 の2本を納品
```
