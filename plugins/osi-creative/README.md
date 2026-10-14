# osi-creative

自社のクリエイティブ系スキル集。

## 含まれるスキル

| スキル名 | 何をするか |
|---|---|
| `ai-video-production` | 台本→fal.ai（カットの性質でモデルを選ぶ。既定は Kling O3 / LTX 2.5 / Seedance 2.0。Veo 3.1 系は fal で 2026-11-17 廃止予定のため既定から外した）でシーン動画生成→ElevenLabs ナレーション→ffmpeg 合成。60〜75 分・$10〜$16 で 2〜3 分尺の動画を生成。 |
| `vp-core` | 各メソッド共通の生成ループ。プロンプト承認ゲート→生成（受付番号を `jobs.json` に残して途中再開）→全コマ QA（`scripts/qa_frames.py`：0.25秒ごとのコンタクトシート・0.4秒超の静止・つなぎ目の差）→直し方のラダー（`ai-video-production/references/fix-ladder.md`）→連結。 |
| `narration` | 日本語ナレ（ElevenLabs v3＋発音辞書）。動画用は通しで1回生成して声色をそろえ、実測で尺を決める。 |
| `music` | シグネチャー曲3本の使い回し、出どころの記録 `SOURCE.md`、ナレ区間だけ -20dB 下げるダッキング（`scripts/duck_expr.py`）。 |
| `vp-brand-film` | ブランドムービー。会社の言葉から世界観設計書を作り、静止画で方向を選び、ナレを先に作って尺を決めてから映像にする。 |

## 前提

- **ai-video-production を使う場合**：
  - `fal-video-mcp` v0.3 以降が Claude に登録されていること
  - 環境変数 `ELEVENLABS_API_KEY` が設定されていること（TTS 用）
  - 環境変数 `FAL_OUTPUT_DIR` が設定されていること（任意、未設定なら `/tmp/`）
  - ffmpeg / curl が使える Linux サンドボックス

## インストール

ルート README を参照。マーケットプレイス登録後、`/plugin install osi-creative@ai-osi-uri` 1 行で導入できます。

## 変更履歴

- 0.10.0（2026-10-14）: vp-core に全コマ QA（`qa_frames.py`）と受付番号の記録（`jobs.json`）、直し方のラダー（`fix-ladder.md`）、i2v カットの採点表、設定シート→見た目の固定文→起点画像の清書→部分修正、narration の通し生成・複数話者、music の `SOURCE.md` とダッキング（`duck_expr.py`）、世界観設計書の補強（本音4段階・比喩3案・style_lock・音のロゴ・人物の出し方2通り）を追加。Veo 3.1 系（fal で 2026-11-17 廃止予定）を既定から外し Kling O3 等へ。`kling30` の名前の衝突（O3 ライン／v3 ライン）を明記。`qa_frames.py` と `duck_expr.py` は MIT ライセンスの制作ツールからの移植（各ファイル冒頭に表示）。
