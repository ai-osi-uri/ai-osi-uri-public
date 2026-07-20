---
name: ai-video-production-or
description: AI動画をOpenRouter経由で作るオーケストレータ。osi-creative の ai-video-production と同じ責務（動画タイプ判定→メソッド振り分け→承認ゲート付き生成→合成→納品）を、fal+ElevenLabs ではなく OpenRouter の統一マルチモーダルAPI（Veo 3.1 / Seedance 2.0 / Kling 3.0 / nano-banana-pro / GPT-4o TTS 等）を単一APIキーで叩く MCP `osi-creative-openrouter` を通して実行する。「OpenRouterで動画作って」「OR経由でPR動画」「fal使わず動画」「単一キーで動画制作」「Veo/Seedance/Kling切替」「マルチベンダーで動画」等で発動。fal/ElevenLabsを使いたい場合は osi-creative 側の ai-video-production を使う。
version: 0.1.0
requires_connectors:
  - server: osi-creative-openrouter
    provision: user-install
    tools: [generate_image, edit_image, submit_video, check_status, image_to_video, generate_speech, list_models, check_key]
---

# AI動画制作パイプライン（OpenRouter版・ディスパッチャ）

**osi-creative の `ai-video-production` と全10Phase・全メソッド・全落とし穴集を共有する**。相違はバックエンドだけ:

| 領域 | osi-creative（既存） | 本スキル（OpenRouter版） |
|---|---|---|
| バックエンドMCP | `ai-osi-uri-creative`（fal + ElevenLabs） | **`osi-creative-openrouter`**（OpenRouter統一API） |
| 画像 | nano-banana / nano-banana-pro（fal経由） | `google/gemini-3-pro-image` / `openai/gpt-image-1` / `bytedance-seed/seedream-4.5` |
| 動画 | Seedance 2.0 / Veo 3.1 / Kling 3.0（fal経由） | 同モデル群を OpenRouter `/videos` 非同期エンドポイントで |
| 音声 | ElevenLabs v3（GENEL voice, stability 0.35, 感情タグ） | `openai/gpt-4o-mini-tts` / `google/gemini-3-flash-tts` / `mistralai/voxtral-mini-tts` |
| 認証 | fal.ai + ElevenLabs 2キー | **OpenRouter 1キーだけ**（macOS Keychain保存） |
| コスト精算 | fal + ElevenLabs 別請求 | OpenRouter 1本にまとまる |

## ★ ディスパッチ（動画タイプ → メソッド）

依頼を読み、下表でメソッドを選んで**ハンドオフ**する。

| 依頼の型 | メソッド | 例 |
|---|---|---|
| 同一キャラ/マスコット/商品を崩さず動かす | **`vp-character-action-or`** | 「このキャラで動画」「マスコット動かして」 |
| 1枚の画像＋カメラの動き（空撮含む） | **`vp-moveboard-or`** | 「この絵を動かして」「商品オービット」「空撮」 |
| ナレ付き企業動画（IR/採用/PR・12シーン） | **`vp-corporate-narrated-or`** | 「採用動画」「会社説明」「IR動画」 |

どのメソッドも、起草プロンプトを **`vp-core-or` の承認ゲート**に通す。

## 全10 Phase（osi-creative の SKILL.md と同じ設計）

台本設計・シーン構成・ヒアリング項目・試作／本番の分割・字幕・BGM ルールは
osi-creative 側の references / templates を**そのまま流用する**。本プラグイン独自のバックエンド差分だけを以下で規定する。

## バックエンド差分（重要）

### Phase 3.5: キービジュアル生成
```
Tool: generate_image
Model (default): google/gemini-3-pro-image  ← nano-banana-pro相当
Alt: openai/gpt-image-1, bytedance-seed/seedream-4.5
Params: aspect_ratio ("16:9"|"9:16"|"1:1"), resolution ("2K"|"4K"),
        input_references (参照画像URL配列で subject consistency)
```

### Phase 4-5: 動画生成
```
Tool: submit_video → check_status（非同期・OR公式パターン）
Model (default): bytedance/seedance-2.0
Alt: google/veo-3.1 / google/veo-3.1-fast / kuaishou/kling-3.0 / alibaba/wan-2.7
Params:
  - frame_images: [{type:image_url, image_url:{url}, frame_type:"first_frame"}]  ← i2v
  - input_references: [{type:image_url, image_url:{url}}]                        ← reference-to-video
  - duration / resolution / aspect_ratio / generate_audio
Polling: 30秒間隔、status in {pending, in_progress, completed, failed}
完了時: unsigned_urls[0] を自動DLして OUTPUT_DIR に mp4 保存
```

**動画API並列制限は fal と違い OpenRouter 側で吸収**。ただし秒当たり単価は fal 経由より高いモデルもあるため、
起動前に `list_models kind=video` で単価を提示するのを推奨。

### Phase 6: ナレーション生成
ElevenLabs 直叩き（GENEL voice + 感情タグ）は OpenRouter からは使えない。代替:

```
Tool: generate_speech
Model (default): openai/gpt-4o-mini-tts
Voice: alloy / nova / echo / shimmer / onyx / fable（openai系）
        自然な日本語なら google/gemini-3-flash-tts + voice="Kore" 等
        ゼロショットクローンなら mistralai/voxtral-mini-tts（voice_id にプロファイル）
Params: response_format="mp3", speed(openaiのみ)
Provider options（GPT-4o系）:
  provider.options.openai.instructions = "落ち着いた女性・thoughtful"
    ← Eleven v3 の [thoughtful] [calm] 感情タグの代替は
       instructions 文字列で「声のトーン」を指示する運用に変える
```

**注意**: OpenRouter TTS は「感情タグ角括弧」を解釈しない。台本の `[thoughtful]` 等は削除し、
シーンごとに `provider.options.openai.instructions` で声色を切り替える。

### Phase 7-9: 字幕/合成/納品
osi-creative の `scripts/make_subs.py` と `scripts/build_video.sh` を**そのまま使える**（ffmpegローカル）。
本プラグインでは独自スクリプトを持たず、osi-creative のスクリプト再利用を前提とする。

## 事前チェック

初回発動時:
1. `check_key` で OpenRouter API キーの疎通と残高を表示
2. `list_models` で今日の image/video/tts モデル slug を確認（モデル名は月次で入れ替わる）
3. 案件のヒアリング（Phase 0）→ メソッド振り分け

## 参照

osi-creative の下記ファイルを本スキルからも読む（重複を避けるため本プラグインは複製しない）:
- `../../../osi-creative/ai-video-production/references/pitfalls.md`（#17 i2v 1フレーム目・#18 モーション予算 等）
- `../../../osi-creative/ai-video-production/references/character-consistency-pipeline.md`
- `../../../osi-creative/ai-video-production/references/moveboard.md`
- `../../../osi-creative/ai-video-production/templates/prompts-*.md`
- `../../../osi-creative/ai-video-production/scripts/build_video.sh` / `make_subs.py`

（osi-creative プラグインが未インストールなら Cowork の Skills から追加を案内する）

## 鉄則

- ✅ 単一 API キー（OpenRouter）で動画・画像・音声を完結
- ✅ 動画は必ず `submit_video → check_status` の非同期パターン
- ✅ ffmpeg ローカル合成は osi-creative のスクリプトを流用
- ❌ ElevenLabs GENEL voice + 感情タグは使えない（`instructions` で代替）
- ❌ fal 経由が必要なプロプライエタリな挙動（音楽生成 stable-audio 等）は本プラグインでは提供しない
