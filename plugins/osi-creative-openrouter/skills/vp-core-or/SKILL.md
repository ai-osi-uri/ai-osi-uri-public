---
name: vp-core-or
description: OpenRouter版 vp-core。承認ゲート付き生成ループの共通インナー atomic スキル。オーケストレータ ai-video-production-or または各メソッド（vp-character-action-or / vp-corporate-narrated-or / vp-moveboard-or）から呼ばれ、①メソッドが書いたプロンプトを提示して承認を取り、②承認後に MCP `osi-creative-openrouter` の generate_image / submit_video / check_status / image_to_video / generate_speech で生成、③検証、④必要なら ffmpeg で連結、⑤納品する。単独発動しない。プロンプト起草や動画タイプ判定は各メソッドの責任で、本スキルは行わない。
version: 0.1.0
requires_connectors:
  - server: osi-creative-openrouter
    provision: user-install
    tools: [generate_image, edit_image, submit_video, check_status, image_to_video, generate_speech]
---

# vp-core-or — 動画制作の共通インナー（OpenRouter版）

`osi-creative/vp-core` と**同じ責務・同じ STEP 構成**。差分は「呼ぶ MCP ツールが `osi-creative-openrouter` になる」点だけ。

## 入力（メソッドから受け取る）
- `prompts`: 起草済みプロンプト一式（A:キービジュアル / B:設定シート / C:ビート列 / 台本 等）
- `plan`: 生成計画（**model slug** = OpenRouter の slug ／尺・アスペクト比・枚数・連結要否）
- `assets`: 既存の参照画像URL等

## ループ

### STEP 1. プロンプト承認ゲート（★最重要）
`osi-creative/ai-video-production/references/prompt-quality-rubric.md` で**自己採点必須**。
MUST ❌ が1つでもあればメソッドに直させて再採点。合格後にプロンプトをそのままユーザーに提示。
「試作動画を見て直す」より前に**文章段階で合意**する。

### STEP 2. 生成（承認後のみ）— OpenRouter 版

**画像**:
```
generate_image(
  model = plan.image_model            # 既定: google/gemini-3-pro-image
  prompt = "..."
  aspect_ratio = "16:9" | "9:16"
  resolution = "2K" | "4K"
  input_references = [参照画像URL, ...]  # 一貫性用
)
→ saved_paths[], cost_usd
```

**動画（必ず非同期）**:
```
submit_video(
  model = plan.video_model           # 既定: bytedance/seedance-2.0
  prompt = "..."
  duration = 5 | 10
  resolution = "720p" | "1080p"
  aspect_ratio = "16:9" | "9:16"
  # 2系統を取り違えない:
  frame_images = [{...frame_type:"first_frame"}]  # ← i2v（vp-character-action-or）
  input_references = [{...}]                      # ← reference-to-video（vp-moveboard-or）
  generate_audio = true/false
)
→ {job_id, polling_url, status}

# 30秒間隔でポーリング:
check_status(job_id)
→ status ∈ {pending, in_progress, completed, failed}
→ completed のとき saved_paths[] に mp4 のローカルパス
```

**音声**:
```
generate_speech(
  model = plan.tts_model             # 既定: openai/gpt-4o-mini-tts
  text = "..."
  voice = "alloy" | "nova" | ...
  response_format = "mp3"
  provider = {
    options: {
      openai: {instructions: "落ち着いた女性・thoughtful"}   # 感情タグの代替
    }
  }
)
→ saved_path
```

- コスト見込みを生成前に提示する。OpenRouter は `check_key` で残高、`list_models` で単価を出せる。
- **並列制限は fal と違い OpenRouter が吸収する**が、動画生成は数分単位で完了するので同時 3〜5 本に留める。

### STEP 3. 検証
- 画像/動画を取得し、内容を確認（`ffmpeg -ss 0.5 -i out.mp4 -vframes 1 frame.png` で数フレーム抽出）
- i2v: 1フレーム目が意図通りか。reference-to-video: 赤線/番号が出ていないか＋経路追従
- 連結前提なら各区間の**繋ぎ目フレーム**が一致するか

### STEP 4. 連結・仕上げ（必要時）
- ffmpeg は **必ず /tmp で作業 → cp で配置**（Drive直書きは破損）
- 連結は `setsar=1,fps=24,scale=...,pad=...` で正規化してから concat
- 字幕/BGM合成は **osi-creative の `scripts/build_video.sh` を流用**（本プラグインは独自スクリプトを持たない）

### STEP 5. 納品
- 成果物を提示。累計 `cost_usd`（OpenRouter 一本）を表示

## 共通参照（osi-creative 側の正本を参照）
- `osi-creative/ai-video-production/references/prompt-quality-rubric.md` … 提示前の自己採点ゲート
- `osi-creative/ai-video-production/references/pitfalls.md` … #17 i2v 1フレーム目・#18 モーション予算
- `osi-creative/ai-video-production/references/character-consistency-pipeline.md`
- `osi-creative/ai-video-production/references/moveboard.md`

## 原則
- ❌ 承認前に生成しない（プロンプトゲートを飛ばさない）
- ❌ 一気に全カット生成しない（試作を挟む）
- ✅ 迫力アクションは Seedance 2.0 の一発生成
- ✅ 単一 OpenRouter キーで完結（fal / ElevenLabs 別キー不要）
