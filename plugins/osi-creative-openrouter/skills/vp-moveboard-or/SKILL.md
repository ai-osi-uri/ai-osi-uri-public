---
name: vp-moveboard-or
description: OpenRouter版「1枚の画像をカメラの動きで魅せる」メソッド。写真・絵画・イラスト・商品・建築・人物など動かしたい画像1枚を、引いた線（ムーブボード）の通りに動かす。中核は「ルート＋番号＋動き説明ラベル付きのムーブボードをコードで1本だけ描き、Seedance 2.0 reference-to-video の参照画像として渡す」こと。書いたムーブボード／プロンプトは vp-core-or の承認ゲートに渡し、承認後に MCP osi-creative-openrouter の submit_video で生成する。「ORで空撮」「ORでこの絵を動かして」「ORで商品オービット」等で呼ばれる。キャラの躍動アクションは vp-character-action-or、ナレ主体の企業説明は vp-corporate-narrated-or。
version: 0.1.0
requires_connectors:
  - server: osi-creative-openrouter
    provision: user-install
    tools: [generate_image, submit_video, check_status]
---

# vp-moveboard-or — 1枚の画像をカメラムーブで魅せる（OpenRouter版）

`osi-creative/vp-moveboard` の **4つの確定原則をそのまま踏襲**。差分はバックエンドのみ。

## 4つの確定原則（変えるとどうせ失敗する）

1. **入力は `reference-to-video`**：OpenRouter `submit_video` に `input_references=[{...}]` で渡す（`frame_images` は使わない。#17 の再現を避ける）
2. **ルート線は AI に描かせず、コードで1本だけ描く**：Python(Pillow) で通過点を Catmull-Rom 補間
3. **線で表せない情報はラベルで補う**：番号＋短い動き説明ラベル（例 `PUSH IN / strong motion`, `CLIMB / rise quickly`, `HERO ORBIT / around the landmark`, `PULL BACK / widen`）
4. **動画プロンプトは短く**：振り付けはムーブボード（画像）が担う

## 差分（vp-core-or に渡す plan）

```json
{
  "image_model": "google/gemini-3-pro-image",
  "video_model": "bytedance/seedance-2.0",
  "aspect_ratio": "16:9",
  "duration": 10
}
```

生成呼び出しの型:
```
submit_video(
  model = "bytedance/seedance-2.0"
  prompt = "Follow the drawn route smoothly. Do not render the guide line. Ambient FX audio only."
  input_references = [{type:"image_url", image_url:{url: <ムーブボード画像URL>}}]
  aspect_ratio = "16:9"
  duration = 10
)
```

## フロー

1. ヒアリング（`AskUserQuestion`）：①元画像はある？(自前/生成) ②被写体タイプ(6プリセット) ③カメラムーブ ④迫力レベル ⑤尺・縦横・音
2. ベース画像：無ければ `generate_image`（`google/gemini-3-pro-image`, 4K, 指定アスペクト, テキスト/線なし）
3. **ムーブボード描画**（コード）：Python(Pillow)で1本の連続曲線＋矢印＋番号＋動き説明ラベル
4. `vp-core-or` → プロンプト/ムーブボード承認ゲート
5. 生成：上記 `submit_video` パターン、非同期 → `check_status`
6. 検証：reference-to-video なので赤線は出ない。数フレーム抜いて線無し＆経路追従を確認

## 鉄則
- ❌ `frame_images`（i2v）でムーブボードを起点にしない（赤線が映る／カメラ固定）
- ❌ ルート線を AI に描かせない
- ✅ パス設計はAI、線描画はコード、振り付けはラベル、動かすは `input_references`

詳細レシピは `osi-creative/ai-video-production/references/moveboard.md`、
空撮6ビートは `osi-creative/ai-video-production/references/drone-aerial-fpv.md` を参照。
生成・承認・連結ループは `vp-core-or` に委譲する。
