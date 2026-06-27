---
name: vp-corporate-narrated
description: AI動画の「ナレ付き企業動画」メソッド。IR・採用・PR・会社説明・ピッチなど、起承転結の12シーン構成＋ナレーション＋字幕＋BGMで2〜3分尺に仕上げる。中核は「①12シーンの台本を設計し ②各シーンの画像起点プロンプトを書き ③ナレ原稿をTTS最適化（感情タグ＋誤読対策）で書く」こと。書いた台本・プロンプト・ナレ原稿は vp-core の承認ゲートに通し、承認後に生成→ナレ→字幕→ffmpeg合成→BGMミックスする。「採用動画」「会社説明動画」「IR動画」「PR動画」「ピッチ動画」「ナレーション付き動画」「2〜3分の企業動画」などのリクエストで、オーケストレータ ai-video-production から呼ばれる（単独指定も可）。1枚＋カメラムーブだけは vp-moveboard、キャラの躍動アクションは vp-character-action。
version: 0.2.0
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_image, image_to_video, submit_video, check_status, generate_speech, generate_music]
---

# vp-corporate-narrated — ナレ付き企業動画（プロンプト＆台本作者）

このメソッドの仕事は **「12シーンの台本」「シーン別の画像起点プロンプト」「TTS最適化済みのナレ原稿」を書く**こと。
生成ループ（承認ゲート→生成→検証→連結）と納品は `vp-core` に委譲し、本メソッドは**中身（何を言い・何を映すか）**を作る。
OKWEB × JINEN 制作で確立。標準 60〜75分／約 $5〜$10。

**正本テンプレ（必ず参照）**：
- スタイル別プロンプト雛形：`../ai-video-production/templates/prompts-{corporate|documentary|lifestyle|anime-ghibli}.md`
- ナレ：**`narration` スキルに委譲**（`../narration/SKILL.md`。声選択・感情タグ・発音辞書・誤読対策）
- BGM：`../ai-video-production/references/bgm-selection.md`（ショートはYouTuber定番フリー曲）
- モデル使い分け・単価：`../ai-video-production/references/model-comparison.md`
- 落とし穴／チェック：`../ai-video-production/references/pitfalls.md`・`checklist.md`
- 合成スクリプト：`../ai-video-production/scripts/build_video.sh`（ffmpeg一式）・`make_subs.py`（SRT）

## フロー

### 1. ヒアリング（`AskUserQuestion` 一括）
用途（IR/採用/PR/営業説明）／尺（30秒・1分・2〜3分推奨・5分）／スタイル（アニメ・実写ドキュメンタリー・コーポレートCG・ライフスタイル）／ナレ声／字幕焼込み／BGM（生成 or フリー定番）／アスペクト比。既存台本があれば読み込んで2へ。

### 2. 台本設計（12シーン・起承転結）
標準テンプレ（各シーンの役割と尺）で12シーンを設計し、**各シーンの主旨を1〜2文**でユーザー確認。
①問題提起 ②背景 ③数字・市場 ④日本市場 ⑤課題 ⑥強みA ⑦強みB ⑧統合ヒーロー ⑨成長 ⑩優位性 ⑪未来 ⑫クロージング（合計≒165秒、ナレは20%増を見込む）。

### 3. シーン別プロンプト（画像起点）
スタイルの `prompts-{style}.md` の構造（STYLE_PREFIX / SUBJECT / LIGHTING / CAMERA / SETTING / MOOD / STYLE_SUFFIX / no text / 4K）で12本起草。
被写体の一貫性が要る人物・商品は `generate_image` の1枚目を参照に派生（character一貫が主目的なら vp-character-action を併用）。

### 4. ナレ原稿（→ narration スキルに委譲）
ナレの読み制御・声・発音辞書は **`narration` スキル**が担当する。本メソッドは
**台本（何を言うか）と感情タグ設計**だけ行い、原稿はクリーンな漢字かな混じりで書く（壊さない）。
- 声：既定 Konoha（`T7yYq3WpB94yAuOXraRi`）。感情タグ：[thoughtful]/[calm]/[serious]/[confident]/[hopeful]/[warm]。
- 生成手順・辞書・誤読対策は `../narration/SKILL.md` を参照。

### 5. 承認ゲート（vp-core）
**台本＋12プロンプト＋ナレ原稿をまとめて提示**し、文章段階で承認/修正。承認まで生成しない。

### 6. 生成（vp-core｜試作必須）
- 試作：ヒーロー①と中盤⑧の **2本だけ** 先に生成して方向確認（コスト管理）。
- 本番：5本ずつ2バッチ（6本以上同時で Forbidden #1）、45〜60秒間隔でポーリング。
- モデル：環境/単独人物=Veo 3.1 Fast、複数人物/対話=Kling 3.0、激しい動き=Seedance 2.0、ヒーロー=Veo 3.1。

### 7. ナレ生成（→ narration）
クリーンな台本を `narration` に渡してナレ音声を生成する（jp_yomi_check→辞書→generate_speech）。
詳細は `../narration/SKILL.md` フロー参照。SRT字幕（`make_subs.py`）・ffmpeg合成（`build_video.sh`：尺合わせPTS・12連結・BGM≈-15dB fade・字幕焼込み Noto Sans JP）は従来どおり vp-core/スクリプト。

### 10. 納品
final.mp4（BGM＋字幕）／字幕なし／BGMなし／subtitles.srt と、累計コストを提示。

## 鉄則
- ❌ 一気に全12本生成（必ず試作）。❌ Drive直書き。
- ✅ ナレは narration スキルに委譲（クリーンテキスト＋発音辞書）。原稿の字面は壊さない。
- ✅ 声は日本語ネイティブ（既定 Konoha）。
- ✅ 文章（台本・プロンプト・ナレ）を先に承認 → それから生成（vp-core ゲート）。
- ✅ ショート/SNS狙いのBGMは AI生成より YouTuber定番フリー曲（`bgm-selection.md`）。

生成・承認・連結ループは `vp-core` に委譲し、本メソッドは台本・プロンプト・ナレ原稿の作成に責任を持つ。
