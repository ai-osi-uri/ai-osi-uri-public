# osi-creative-openrouter (プラグイン)

OpenRouter 経由で AI 動画・画像・音声を生成する制作パイプライン一式。
`osi-creative`（fal + ElevenLabs）と対を成す、**単一 API キーで完結する版**。

## 収録スキル

| スキル | 役割 |
|---|---|
| `ai-video-production-or` | オーケストレータ（動画タイプ判定→メソッド振り分け） |
| `vp-core-or` | 承認ゲート付き生成ループの共通インナー |
| `vp-character-action-or` | キャラ一貫アクション（A/B/C 3プロンプト） |
| `vp-corporate-narrated-or` | ナレ付き企業動画（12シーン構成） |
| `vp-moveboard-or` | 1枚の画像＋カメラムーブ（reference-to-video） |

## 依存 MCP

このプラグインは MCP `osi-creative-openrouter` を必要とします。
別途 `osi-creative-openrouter.mcpb` を Claude Desktop にドラッグしてインストールし、
OpenRouter API キー（https://openrouter.ai/keys）を設定してください。

## osi-creative との併存

**osi-creative は削除しないでください**。本プラグインは references / templates / scripts
（プロンプト雛形、pitfalls、moveboard レシピ、build_video.sh 等）を osi-creative から流用します。
両方インストールした状態で使うのが前提です。

## セットアップ

1. `osi-creative-openrouter.mcpb` を Claude Desktop にドラッグ → 設定欄に OpenRouter API キーを入力
2. 本プラグイン（`osi-creative-openrouter.plugin`）を Cowork にインストール
3. `check_key` で疎通確認 → `list_models kind=image/video/tts` で今日の slug を確認
4. 「OpenRouter で ○○ の PR 動画作って」等で発動
