# osi-creative

AI OSI URI のクリエイティブ系スキル集。

## 含まれるスキル

| スキル名 | 何をするか |
|---|---|
| `ai-video-production` | 台本→fal.ai (Veo 3 Fast / Kling 2.5) でシーン動画生成→ElevenLabs ナレーション→ffmpeg 合成。60〜75 分・$5〜$10 で 2〜3 分尺の動画を生成。 |

## 前提

- **ai-video-production を使う場合**：
  - `fal-video-mcp` v0.3 以降が Cowork に登録されていること
  - 環境変数 `ELEVENLABS_API_KEY` が設定されていること（TTS 用）
  - 環境変数 `FAL_OUTPUT_DIR` が設定されていること（任意、未設定なら `/tmp/`）
  - ffmpeg / curl が使える Linux サンドボックス

## インストール

ルート README を参照。マーケットプレイス登録後、`/plugin install osi-creative@ai-osi-uri` 1 行で導入できます。
