---
name: vp-character-action-or
description: OpenRouter版「キャラ一貫アクション」メソッド。同一キャラ・マスコット・VTuber・商品を、何カット出しても見た目をブレさせずに、躍動感のあるアクション動画にする。中核は A:キービジュアル / B:設定シート / C:Seedanceビート列 の3プロンプトを書くこと。書いたプロンプトは vp-core-or の承認ゲートに渡し、承認後に MCP osi-creative-openrouter の generate_image / submit_video で生成する。「OpenRouterでこのキャラで動画」「マスコット動画をORで」等で呼ばれる（オーケストレータ ai-video-production-or 経由 or 単独）。カメラムーブ主体は vp-moveboard-or、ナレ主体の企業説明は vp-corporate-narrated-or。
version: 0.1.0
requires_connectors:
  - server: osi-creative-openrouter
    provision: user-install
    tools: [generate_image, edit_image, submit_video, check_status, image_to_video]
---

# vp-character-action-or — キャラ一貫アクション（OpenRouter版）

`osi-creative/vp-character-action` と**同じ A/B/C プロンプト設計**。差分は使う MCP ツールと model slug だけ。

## フロー

1. キャラのブリーフを受け取る（例「サイバー忍者の悪魔暗殺者」）
2. A→B→C の3プロンプトを書き起こす
3. `vp-core-or` に渡す → プロンプト承認ゲート → 承認後に生成
4. C は **Seedance 2.0 の一発生成**（`bytedance/seedance-2.0`）
5. 検証・納品は `vp-core-or`

## プロンプト・ジェネレータ

雛形は `osi-creative/vp-character-action/SKILL.md` を**そのまま流用**（A/B/Cの本文は同じ）。

### 差分（呼び出し側の plan）

| 段階 | osi-creative（既存） | 本メソッド（OR版） |
|---|---|---|
| A: キービジュアル | nano-banana-pro (fal) | `google/gemini-3-pro-image` (OpenRouter) |
| B: 設定シート | nano-banana-pro (fal) + extra.image_urls | 同モデル + `input_references=[Aの画像URL]` |
| C: Seedance ビート | seedance20-i2v (fal) 起点=Aの画像 | `bytedance/seedance-2.0` (OpenRouter) `frame_images=[{...frame_type:"first_frame", image_url:Aの画像URL}]` |

vp-core-or に渡す `plan` の例:
```json
{
  "image_model": "google/gemini-3-pro-image",
  "video_model": "bytedance/seedance-2.0",
  "aspect_ratio": "16:9",
  "duration": 10
}
```

## 鉄則
- **躍動感＝C を Seedance 2.0 で一発生成**。継ぎ接ぎしない
- 起点画像は **A のキービジュアル**（B の設定シートを起点にしない）
- OpenRouter `submit_video` で **frame_images**（i2v）を使う（reference-to-video ではない）

詳細レシピは `osi-creative/ai-video-production/references/character-consistency-pipeline.md` を参照。
生成・承認・連結ループは `vp-core-or` に委譲する。
