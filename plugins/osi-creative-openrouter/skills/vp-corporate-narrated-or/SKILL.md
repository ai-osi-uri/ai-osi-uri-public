---
name: vp-corporate-narrated-or
description: OpenRouter版「ナレ付き企業動画」メソッド。IR・採用・PR・会社説明・ピッチなど、起承転結の12シーン構成＋ナレーション＋字幕＋BGMで2〜3分尺に仕上げる。中核は 12シーンの台本設計 / シーン別プロンプト / TTS最適化ナレ原稿。書いた台本・プロンプト・ナレ原稿は vp-core-or の承認ゲートに通し、承認後に MCP osi-creative-openrouter で生成→字幕→osi-creative の build_video.sh で合成する。「ORで採用動画」「OpenRouterで会社説明動画」「OR経由でIR動画」等で呼ばれる。1枚＋カメラムーブだけは vp-moveboard-or、キャラの躍動アクションは vp-character-action-or。
version: 0.1.0
requires_connectors:
  - server: osi-creative-openrouter
    provision: user-install
    tools: [generate_image, image_to_video, submit_video, check_status, generate_speech]
---

# vp-corporate-narrated-or — ナレ付き企業動画（OpenRouter版）

`osi-creative/vp-corporate-narrated` と**同じ12シーン設計・同じ承認フロー**。差分は生成バックエンドとナレ運用。

## フロー

1. **ヒアリング**（`AskUserQuestion` 一括）：用途／尺／スタイル／ナレ声／字幕焼込み／BGM／アスペクト比
2. **台本設計（12シーン・起承転結）**：osi-creative の標準テンプレを使用
3. **シーン別プロンプト（画像起点）**：スタイルの `prompts-{style}.md`（osi-creative）の構造で12本起草
4. **ナレ原稿（TTS最適化）**：★本メソッドの品質差ポイント（下記「ナレ運用の差分」参照）
5. **承認ゲート（vp-core-or）**：台本＋12プロンプト＋ナレ原稿をまとめて提示
6. **生成（vp-core-or／試作必須）**：
   - 試作：ヒーロー①と中盤⑧の **2本だけ** 先に生成
   - 本番：3〜5本ずつ非同期 `submit_video` → `check_status`
7. **ナレ生成** → **SRT字幕**（`osi-creative/ai-video-production/scripts/make_subs.py`）
8. **ffmpeg合成＋BGM**（`osi-creative/ai-video-production/scripts/build_video.sh`）
9. **納品**：final.mp4 ＋ 字幕なし ＋ BGMなし ＋ subtitles.srt ＋ 累計 `cost_usd`

## バックエンド差分

### 画像・動画
```
plan = {
  image_model: "google/gemini-3-pro-image",
  video_model: "google/veo-3.1-fast",   # 環境/単独人物のヒーロー以外は Fast で単価下げ
  hero_model:  "google/veo-3.1",        # ヒーロー①⑧⑫ は Veo 3.1（音声同期対応）
  action_model:"bytedance/seedance-2.0" # 激しい動きは Seedance
}
```

### ★ ナレ運用の差分（重要）

osi-creative の ElevenLabs v3 + GENEL voice + 感情タグ `[thoughtful]/[calm]/[hopeful]` は **OpenRouter 経由では使えない**。以下に振り替える:

```
generate_speech(
  model  = "openai/gpt-4o-mini-tts"            # 既定
  voice  = "nova" | "shimmer"                  # 落ち着いた女性は nova / shimmer
                                                # 力強い男性は onyx / echo
                                                # 明るい女性は fable / coral
  text   = "自然な日本語（角括弧の感情タグは削除）"
  response_format = "mp3"
  provider = {
    options: {
      openai: {
        instructions: "落ち着いた・思慮深い女性のナレーター。抑揚を抑えめに。"
      }
    }
  }
)
```

**シーン→instructions マップ**（osi-creative の感情タグから移植）:

| シーン | osi-creative の感情タグ | OR TTS instructions |
|---|---|---|
| ① | `[thoughtful]` | 「思慮深く、控えめに問いかける」 |
| ②③ | `[calm]` | 「落ち着いて事実を淡々と」 |
| ⑤ | `[serious]` | 「重さと真剣さ、テンポは遅め」 |
| ⑥⑦ | `[confident]` | 「自信を持って、はっきりと」 |
| ⑧ | `[hopeful]` | 「期待感、少し明るく開ける」 |
| ⑩ | `[confident]` | 「自信を持って断言する」 |
| ⑪ | `[hopeful]` | 「未来を語る、少し高揚」 |
| ⑫ | `[warm]` | 「温かく、親しみを込めて」 |

### 誤読対策（voice別）

- **OpenAI 系**（gpt-4o-mini-tts）: 日本語の漢字読みはかなり自然。数字は「27年 → にじゅうななねん」等の**軽い置換だけ**で足りることが多い（Elevenほど厳しくない）
- **Voxtral**（クローン）: `voice` に事前登録したプロファイルIDを渡す（Voxtral 側でクローン登録が必要）
- **Gemini 3 Flash TTS**: 70+ 言語対応で日本語は自然。voice に `Kore` 等を指定

**運用**: 1シーンだけ試聴 → 気に入った voice / instructions を全12シーンに適用 → 本番生成。

### BGM
- OpenRouter は音楽生成モデルを提供していない。BGMは以下の運用:
  - **YouTuber定番フリー曲**（DOVA-SYNDROME等）を Claude in Chrome で取得 → `~/Downloads` から `cp`
  - AI 生成 BGM が要る案件では、Claude Desktop に別途 `stable-audio` 系拡張を入れるか、osi-creative（fal 経由）を併用
- 選定・著作権・途切れ防止は `osi-creative/ai-video-production/references/bgm-selection.md` 参照

## 鉄則
- ❌ 角括弧の感情タグをそのまま `input` に入れない（OpenRouter TTS は解釈しない）
- ❌ 一気に全12本生成（必ず試作）
- ✅ 感情表現は `provider.options.openai.instructions` に自然文で書く
- ✅ 台本・プロンプト・ナレ原稿を **先に承認 → それから生成**（vp-core-or ゲート）

生成・承認・合成ループは `vp-core-or` に委譲し、本メソッドは台本・プロンプト・ナレ原稿の作成に責任を持つ。
