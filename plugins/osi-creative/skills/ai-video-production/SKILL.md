---
name: ai-video-production
description: AI動画を作るスキル。台本構成→シーン別動画生成（fal.ai経由のVeo 3 Fast / Kling 2.5）→ナレーション生成（ElevenLabs）→字幕生成→ffmpeg合成→BGMミックスまで自動化。「動画を作って」「動画作成」「PR動画」「IR動画」「採用動画」「企業説明動画」「ピッチ動画」「ナレーション付き動画」「アニメ動画」「実写動画」「ドキュメンタリー動画」「TikTok動画」「Reels動画」など、AI動画制作のリクエスト全般で発動する。既存の動画台本テキストが渡された場合も発動する。fal-video-mcp（v0.3以降）がCoworkに登録されていることを前提とする。PPT・スライドのみ、静止画のみの依頼では使わない。
version: 0.1.0
---

# AI動画制作パイプライン

OKWEB × JINEN動画制作で確立した全工程を再現可能な形にしたスキル。**60〜75分／約 $5〜$10** で2〜3分尺の動画を完成させる。

## 前提

- fal-video-mcp v0.3 以降が Cowork に登録されている（13ツール: 動画5＋TTS4＋音楽4）
- fal.ai のAPIキーが設定済み、最低 $10 のクレジットがある
- ffmpeg が利用可能なBash環境がある（Linux sandbox）
- 出力先フォルダ（FAL_OUTPUT_DIR）が Drive 等に設定済み

## 全工程（10 Phase）

```
[Phase 0]  ヒアリング（5分・無料）
[Phase 1]  台本構成設計（10分・無料）
[Phase 2]  ビジュアル方向性決定（5分・無料）
[Phase 3]  シーン別プロンプト設計（5分・無料）
[Phase 4]  ★試作（コスト管理の要）（5分・$1〜$2）
[Phase 5]  残りシーン一括生成（10分・$3〜$8）
[Phase 6]  ナレーション生成（5分・$0.30）
[Phase 7]  SRT字幕生成（1分・無料）
[Phase 8]  ffmpeg合成（5分・無料）
[Phase 9]  最終納品（1分）
```

各フェーズで**ユーザー確認を必ず取る**。一気に全部生成しない。

---

## Phase 0: ヒアリング

`AskUserQuestion` で以下を一括確認する。すべて選択式 + Other で。

| 質問 | 選択肢 |
|---|---|
| 動画の用途は？ | IR / 採用 / PR・広報 / 営業説明 / その他 |
| 想定尺は？ | 30秒 / 1分 / 2〜3分（推奨） / 5分 |
| ビジュアルスタイル？ | アニメ（ジブリ風）/ ドキュメンタリー実写 / コーポレートCG / ライフスタイル |
| ナレーター声 | 落ち着いた女性（推奨）/ 落ち着いた男性 / 力強い男性 / 明るい女性 / なし |
| 字幕焼き込み？ | 焼き込み（推奨）/ SRT別出力 / なし |
| BGM？ | Stable Audioで生成（推奨）/ なし |
| アスペクト比 | 16:9（推奨）/ 9:16 / 1:1 |

既存台本がある → そのまま読み込み Phase 1 構成検討へ。
台本なし → Phase 1 で構成を一緒に作る。

---

## Phase 1: 台本構成設計

**目標**：起承転結のある12シーン（標準）を設計する。

### 標準構成テンプレ（2〜3分動画）

| # | 役割 | 尺 |
|---|---|---|
| ① | オープニング・問題提起 | 10秒 |
| ② | 社会トレンド・背景 | 15秒 |
| ③ | 数字・市場規模 | 20秒 |
| ④ | ローカル文脈・日本市場 | 10秒 |
| ⑤ | 現状の課題 | 15秒 |
| ⑥ | サービスA の強み | 10秒 |
| ⑦ | サービスB の強み | 10秒 |
| ⑧ | 統合・コア（ヒーローカット） | 20秒 |
| ⑨ | 成長モデル・サイクル | 15秒 |
| ⑩ | 競争優位性 | 15秒 |
| ⑪ | 未来・ビジョン | 15秒 |
| ⑫ | クロージング・タグライン | 10秒 |

合計 165 秒（約2:45）。実際のナレ尺は20%増しを見込む。

ユーザーに**全12シーンの主旨と1〜2文の要約**を確認させる。

---

## Phase 2: ビジュアル方向性決定

`templates/prompts-*.md` から該当スタイルを読み込んで、以下を確定：

- 配色（暖色 / 寒色 / モノトーン）
- 主役（人物 / 風景 / 抽象）
- 配色（白＋金 / 濃紺＋ゴールド / クリーム＋ミント等）
- カメラワーク（スロードリー / 手持ち / タイムラプス）
- 質感（写実 / 水彩アニメ / フラットベクター）

ユーザーに**3つの候補**を提示し1つに絞る。

---

## Phase 3: シーン別プロンプト設計

選択スタイルのテンプレを使い、12シーン分のプロンプトを起草する。
プロンプト構造（汎用）：

```
[STYLE_PREFIX] (e.g., "Documentary cinematic shot of")
[SUBJECT] specific to the scene
[LIGHTING] (warm natural daylight / golden hour / soft afternoon)
[CAMERA] (handheld / dolly / shallow DOF)
[SETTING] specific to the scene
[MOOD] (warm / problem-statement / hopeful)
[STYLE_SUFFIX] (color grading, aesthetic notes)
no text overlays
4K cinematic 24fps
```

詳細は `templates/prompts-{style}.md` を参照。

---

## Phase 4: ★試作（必ず挟む）

**最重要ステップ。全12本を一気に生成しない。**

ヒーローシーン①と中盤の代表的なシーン（⑧推奨）の **2本だけ** を生成。

```
fal_submit_video x 2
↓ 60秒待機
fal_check_status x 2
↓ ダウンロード
ユーザーに見せて判断
```

判断分岐：
- ✅ OK → Phase 5へ
- ⚠️ もっと○○な感じに → プロンプト調整して再試作
- ❌ 別モデルで試したい → Veo 3 Fast ⇄ Kling 2.5 切替
- 🔄 スタイル自体を変えたい → Phase 2に戻る

コスト：$0.80〜$1.50

---

## Phase 5: 残りシーン一括生成

**重要：fal.aiの並列ジョブ制限により、6本以上を同時投入するとForbidden発生。**

戦略：
- 5本ずつ2バッチに分割
- バッチ間に10秒待機
- Forbidden発生時は30秒待機 → 1本ずつ再投入
- ジョブIDを記録、 完了まで45〜60秒間隔でポーリング

モデル使い分け：
- 環境・抽象・単独人物 → **Veo 3 Fast**
- 複数人物・対話・握手 → **Kling 2.5**（人物動作に強い）
- ヒーローカット（最高品質欲しい場合）→ Veo 3（パラメータ要注意）

詳細は `references/model-comparison.md` を参照。

コスト：$3〜$8

---

## Phase 6: ナレーション生成

**最重要：voice選択 → モデル選択 → テキスト最適化 → 感情タグ の4段階で決める。**

### Phase 6-1. 推奨デフォルト構成（v10で確立）

```
Backend  : ElevenLabs DIRECT API（fal.ai 経由ではない直叩き）
Voice    : ネイティブ・クローンvoice（GENEL voice等、ElevenLabs Library）
Model    : elevenlabs-v3（最新、感情タグ対応）
Stability: 0.35〜0.5（低いほど抑揚強）
感情タグ : シーン別に [calm] [thoughtful] [confident] [hopeful] [warm] 等
```

### Phase 6-2. voice 選択フロー

詳細は `templates/voice-strategy.md`。

```
Q: ElevenLabs Starter以上のプランがあるか？
├─ Yes → ネイティブクローンvoice（GENEL等）を使う ★最推奨
└─ No  → 組込voice（calm-female=Sarah, calm-male=Adam）
         → ElevenLabs Starter（$5/月）にアップグレード推奨
```

GENEL voice ID: `GxhGYQesaQaYKePCZDEC`（公開クローン、商用OKを要確認）
※ライブラリvoiceはStarter以上で API 経由利用可。Free tierは 402 エラー。

### Phase 6-3. テキスト最適化（voice別）

voice タイプ別に**逆方向の最適化**が必要。詳細は `templates/narration-rules.md`。

**A. ネイティブクローンvoice（GENEL等）**：自然な日本語が基本だが、**読みが複数ある漢字はひらがな化**
- 27年 → にじゅうななねん（しち化を防ぐ）
- 4,800万件 → よんせんはっぴゃくまんけん（数字つぶれ防止）
- 最大級 → さいだいきゅう（しつ化を防ぐ）
- 蓄え → たくわえ（あろえ化を防ぐ）
- 力 → ちから（ちいら化を防ぐ）
- AI → エーアイ（カイーアイ化を防ぐ）
- 見える化 → みえるか
- OKWEB → オーケーウェブ（英字アルファベット読みを防ぐ）
- 2030年代 → にせん、さんじゅうねんだい（さん→じゃん化を読点で回避）

**B. 組込voice（Sarah等、多言語汎用）**：カタカナ強制＋二重母音
- データ → デエタ、サービス → サアビス、プラットフォーム → プラットフォオム
- ジネン → 々（じねん）などフリガナ括弧テクニック

### Phase 6-4. 感情タグマップ（Eleven v3）

テキスト先頭にタグを置くと、声の抑揚が変わる：

| シーン傾向 | 推奨タグ |
|---|---|
| 問題提起・思慮深い | `[thoughtful]` |
| 落ち着いた説明 | `[calm]` |
| 重さ・問題意識 | `[serious]` |
| 自信を示す | `[confident]` |
| 期待感・クライマックス | `[hopeful]` |
| 余韻・親しみ | `[warm]` |
| ハイテンション（採用・PR） | `[excited]` |

12シーン構成の標準マップ：①thoughtful → ②③calm → ④calm → ⑤serious → ⑥⑦confident → ⑧hopeful → ⑨calm → ⑩confident → ⑪hopeful → ⑫warm

### Phase 6-5. 投入手順

1. **試作 1本**：シーン1本だけで音質・抑揚・読みを確認
2. **本番**：12本を6本ずつ並列投入（fal.ai並列上限考慮）
3. 全DL確認

ツール：`fal_text_to_speech`（ブロッキング、各5〜15秒）

```typescript
fal_text_to_speech({
  text: "[calm] ...",
  voice: "GxhGYQesaQaYKePCZDEC",  // GENEL voice_id
  model: "elevenlabs-v3",
  speed: 1.0,
  stability: 0.35,
})
```

---

## Phase 7: SRT字幕生成

`scripts/make_subs.py` を使う。各シーンのナレ実時間を測り、文字数比例でタイミング配分。

```bash
python3 scripts/make_subs.py \
  --scenes "scene_01:11.42:人の価値は…|02:23.72:今、世界は…|..." \
  --out subtitles.srt
```

字幕テキストは**漢字交じりの自然表記**（読みやすい）。
ナレーション用とは別物（ナレ用はカタカナ強制でTTS最適化）。

---

## Phase 8: ffmpeg合成

`scripts/build_video.sh` を実行。以下を行う：

1. **シーン別合成**：動画と narration の尺を合わせる
   - PTS factor = target_duration / source_video_duration
   - target = max(narration_duration, source_video_duration) + 0.3秒
2. **連結**：12シーンを concat
3. **BGMミックス**：stream_loop で長さ合わせ、volume=0.18 (-15dB)、fade in/out
4. **字幕焼き込み**：黒文字＋白縁取り、Noto Sans JP

**重要：必ず /tmp で作業し、最後に Drive に cp する。Drive直接書き込みは sync 干渉でファイルが壊れる。**

長時間処理（字幕焼き込み等）は `nohup ... &` でバックグラウンド実行 + ポーリング。

---

## Phase 9: 最終納品

3つの出力ファイルを提示：

| ファイル | 用途 |
|---|---|
| **final.mp4** | 公開用本命（BGM＋字幕） |
| final_no_subs.mp4 | 字幕なし（別字幕入れたい人用） |
| composite_no_bgm.mp4 | BGMなし（別BGMに差し替え用） |
| subtitles.srt | CapCut/YouTube/Premiere取り込み用 |

加えて累計コストを表示：

```
動画12本: $X.XX
ナレ12本: $0.30
BGM: $0.20
合計: $X.XX
```

---

## 必読参照ファイル

このスキルが発動したら、まず以下を `Read` する：

1. `references/pitfalls.md` — 落とし穴と回避策（実戦から）
2. `references/model-comparison.md` — 動画・音声・音楽モデル使い分け
3. `templates/voice-strategy.md` — ★ナレーターvoice選択戦略（Eleven v3、GENEL、感情タグ）
4. `templates/narration-rules.md` — TTS誤読対策（最重要）
5. 該当する `templates/prompts-{style}.md`

## 必須スクリプト

`scripts/build_video.sh` がffmpegパイプライン全体を実行する。
`scripts/make_subs.py` がSRTを生成する。

## ユーザー体験の原則

✅ 必ず守る：
- フェーズごとに確認を取る（一気に全工程を流さない）
- 試作（Phase 4）を挟む
- コスト見込みを毎フェーズ前に提示
- 既知の落とし穴は最初から回避

❌ 絶対やらない：
- 大量並列投入してForbiddenを浴びる
- 純粋ひらがなナレ
- Drive直接書き込み
- ブロッキング呼び出しでタイムアウト

---

## 想定する所要時間とコスト

| シナリオ | 動画モデル | 合計コスト | 所要時間 |
|---|---|---|---|
| 標準（Veo3 Fast中心） | $4.50 | $5〜$6 | 60分 |
| 高品質（Veo3＋Kling混在） | $7 | $8〜$9 | 75分 |
| 9:16縦版併発 | +$5 | +$5 | +30分 |

残予算が少ない場合は、シーン数を 12 → 8 に圧縮するなど提案する。
