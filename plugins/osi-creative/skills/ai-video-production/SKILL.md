---
name: ai-video-production
description: AI動画を作るオーケストレータ（ディスパッチャ）スキル。依頼から動画タイプを判定し、最適なメソッド（vp-character-action＝キャラ一貫アクション / vp-cinematic-camera-move＝1枚＋カメラムーブ / vp-corporate-narrated＝ナレ付き企業動画 等）へ振り分け、共通インナー vp-core（プロンプト承認ゲート→生成→検証→連結）で作る。「動画を作って」「動画作成」「PR動画」「IR動画」「採用動画」「企業説明動画」「ピッチ動画」「ナレーション付き動画」「アニメ動画」「実写動画」「ドキュメンタリー動画」「TikTok動画」「Reels動画」「このキャラで動画」「商品を動かして」など、AI動画制作のリクエスト全般で発動する。既存の動画台本テキストが渡された場合も発動する。「AI OSI URI Creative」コネクタ（旧 fal-video。動画・音楽・ナレーション・静止画[nano-banana]を内包）が Cowork に登録されていることを前提とする。PPT・スライドのみ、静止画のみの依頼では使わない。
version: 1.0.0
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_image, edit_image, generate_video, image_to_video, submit_video, check_status, generate_speech, generate_music]
---

# AI動画制作パイプライン（ディスパッチャ）

このスキルは **動画タイプを判定して最適なメソッドへ振り分けるオーケストレータ**。
各メソッドは「そのタイプ向けにプロンプトを書く人」で、生成・承認・連結の芯は共通インナー `vp-core` が担う。
（3層：ディスパッチャ＝本スキル ／ メソッド群 ／ インナー `vp-core`）

## ★ ディスパッチ（動画タイプ → メソッド）

依頼を読み、まず下表でメソッドを選んで**ハンドオフ**する。判断に迷うときだけ1問確認。

| 依頼の型 | メソッド | 例 |
|---|---|---|
| 同一キャラ/マスコット/商品を崩さず動かす・アクション/PV | **`vp-character-action`** | 「このキャラで動画」「マスコット動かして」「戦闘PV」 |
| 1枚の画像＋カメラの動き（ドローン空撮含む） | **`vp-cinematic-camera-move`**（移行中：当面は下記カメラムーブモード節） | 「この絵を動かして」「商品を回して」「空撮」 |
| ナレ付き企業動画（IR/採用/PR・12シーン） | **`vp-corporate-narrated`**（移行中：当面は下記 12 Phase） | 「採用動画」「会社説明動画」 |

- どのメソッドも、起草したプロンプトを **`vp-core` の承認ゲート**（プロンプトを先に承認 → 生成）に通す。
- メソッド未整備のタイプは、当面は本ファイル下部の従来フロー（カメラムーブモード／12 Phase）で代替する。
- 新しい動画タイプは「メソッドを1つ追加する」だけで拡張できる（本表に1行足す）。

> **移行方針（増分）**：まず `vp-character-action` と `vp-core` を切り出した（増分1）。
> 以降 `vp-cinematic-camera-move` / `vp-corporate-narrated` を順次メソッド化し、本ファイルの
> 該当フロー（カメラムーブモード／12 Phase）をメソッドへ移設していく。共通参照
> （model-comparison / pitfalls / narration-rules / character-consistency-pipeline）は本スキル配下を正本として共有。

## 前提

- 「AI OSI URI Creative」コネクタ（fal + ElevenLabs を内包）が Cowork に登録されている（動画・音楽・ナレーション＋静止画[nano-banana]。`generate_image` を含む）。**画像も Creative に統合済みなので、別途 nano-banana コネクタは不要**（既存の fal キーで動く）
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

## ★ シネマティック・カメラムーブモード（どんな画像でも動かす）

「1枚の画像（写真・絵画・イラスト・商品・建築・人物…）＋カメラの動き → シネマティックな動画」を最短で出す対話型ショートカット。
**ドローン空撮はこのモードの1プリセット**。核は「**ルート＋番号＋動き説明ラベル付きの“ムーブボード”を参照画像にして、Seedance 2.0 `reference-to-video` で線どおりに動かす**」。
依頼が「この画像を動かして」「絵の中を動くみたいに」「商品をかっこよく回して」「ドローン空撮」等のとき、12 Phase のフル工程より先にこれを提案する。

被写体プリセット（6種）：①空撮（実景）②名画・アートの潜り込み ③商品ヒーロー ④建築・内装ウォークスルー ⑤人物の微動 ⑥抽象・テクスチャ。

進め方：
1. イメージ/狙いを一言もらう。被写体タイプを見極め、必要なら **「迫力のある仕上げにしますか？」** と一度きく。
2. `AskUserQuestion` で確認：①元画像はある？(ある=自前/アップロード/URL、ない=生成) ②被写体タイプ(6プリセット) ③カメラムーブ ④迫力レベル ⑤尺(10/15秒)・縦横(16:9/9:16)・音。
3. ベース画像を用意（無ければ `generate_image` nano-banana-pro でクリーンな1枚）。
4. **ムーブボードを作る（線はコードで！）**：パスはこちらが設計し、**Python(Pillow)で1本の連続曲線＋矢印＋番号＋動き説明ラベル**をベース画像に重ねる。**AIに線を描かせない**（2本目・余計なループが出る）。ループ(orbit)は `ORBIT` ラベル付きで可。
5. **承認ループ**：ムーブボードを提示→「OK？/どこを変える？」を `AskUserQuestion`→通過点の座標を直して描き直し、納得まで反復。動きを“画像で”合意するのが肝。
6. **動画化**：`submit_video`（model: `bytedance/seedance-2.0/reference-to-video`）に**承認済みムーブボードを参照画像(`image_url`)として渡す**。動画プロンプトは短く（「線の通りに飛べ／線は出すな」＋FX）。`check_status`→DL。
7. 検証：reference モードは赤線が出ない（頭トリック不要）。数フレーム抜いて線無し＆経路追従を確認。

**重要な原則（今回の確定知見）**：
- 入力は **`reference-to-video`（参照）**。`image-to-video`（1フレーム目固定）は赤線が映り込むので使わない（#17）。
- ルート線は **コードで1本だけ**描く（AI描画は曖昧線が出る）。
- 線だけでは伝わらない**動きの種類・速度・高さ(3D)・orbit**は**番号＋動き説明ラベル**で補う（元ネタの肝）。
- 動画プロンプトは短く、振り付けはムーブボードに持たせる。
- 360°等は詰め込みすぎない／一定距離で（#18）。

詳しい6プリセット・カメラ語彙・対話フロー・プロンプト雛形は **`references/cinematic-camera-move.md`**、空撮の6ビート詳細は **`references/drone-aerial-fpv.md`** を参照。
**著作権注意**：現存/近年の作家作品（例：エッシャー）は権利が生きていることが多い。デモ・配布例は**パブリックドメイン作品・自前・生成画像**を使う（詳細は cinematic-camera-move.md 末尾）。
ナレーション・BGM・字幕・連結が必要なら、その後に通常の Phase 6〜8 へ接続する。

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
| BGM？ | Stable Audioで生成 / フリー定番曲（DOVA等のYouTuber定番・ショート推奨） / なし |
| アスペクト比 | 16:9（推奨）/ 9:16 / 1:1 |

※ **ショート（9:16・〜60秒）・SNS拡散狙い・「流行りのBGM」希望のときは、AI生成より "YouTuber定番のフリー曲" を選ぶと刺さる。`references/bgm-selection.md` 参照（調査→選定→取得→ミックスの定型と著作権ルール）。**

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

## Phase 3.5: キービジュアル生成（画像起点・デフォルト）

**デフォルトは画像起点フロー**。text-to-video で直接生成するより、まず Creative の
`generate_image`（model: nano-banana / 4Kは nano-banana-pro）で キービジュアルを作り、
それを `image_to_video` で動かす方が、構図・ブランド・被写体の一貫性を制御しやすい。
**画像も動画も同じ Creative コネクタ＝falキー1本で完結する。**

```
generate_image（model: nano-banana-pro, 各シーンのキービジュアル, 4K, no text）
   ↓ 画像を確認・採否
image_to_video（採用画像 → 動画化, カメラワーク指定）
```

- 画像プロンプトは Phase 3 のシーン別プロンプトの [SUBJECT][LIGHTING][SETTING][MOOD]
  をそのまま流用し、末尾に `4K, photorealistic, no text overlays` を付ける。
- 被写体の一貫性が要る場合（同一人物・同一商品が複数シーンに出る）は、nano-banana の
  subject consistency を活かし、1枚目を参照画像にして残りを生成する（`extra` で参照画像を渡す）。
- text-to-video を使うのは、抽象的・background 的なシーンで構図制御が要らない場合に限る。

> **同一キャラ／商品を“ブレさせず”動画化したい案件**（アニメキャラ・企業マスコット・VTuber・商品PR 等）は、
> **`references/character-consistency-pipeline.md`** の3工程レシピ（①キービジュアル → ②設定シート → ③i2v）を参照。
> ★最重要の落とし穴：`image_to_video` は **渡した画像が動画の1フレーム目**になる。設定シートを起点画像にすると
> シートそのものが動き出す。起点は必ず「実シーンのキービジュアル」、設定シートは `generate_image` の参照
> （`image_urls`）に渡して基準固定に使う——役割を分ける。

コスト目安：画像 $0.02〜/枚（4K は nano-banana-pro で $0.30）+ 動画 image-to-video 分。試作（Phase 4）は必ずこの後で挟む。

---

## Phase 4: ★試作（必ず挟む）

**最重要ステップ。全12本を一気に生成しない。**

ヒーローシーン①と中盤の代表的なシーン（⑧推奨）の **2本だけ** を生成。

```
submit_video x 2
↓ 60秒待機
check_status x 2
↓ ダウンロード
ユーザーに見せて判断
```

判断分岐：
- ✅ OK → Phase 5へ
- ⚠️ もっと○○な感じに → プロンプト調整して再試作
- ❌ 別モデルで試したい → Veo 3.1 / Seedance 2.0 / Kling 3.0 を AskUserQuestion で切替
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

モデル使い分け（2026現行・詳細は references/model-comparison.md が正本）：
- 環境・抽象・単独人物 → **Veo 3.1 Fast**（安く写実）
- 複数人物・対話・握手 → **Kling 3.0**（人物動作・最大6カット連結に強い）
- 激しい動き・多参照・モンタージュ → **Seedance 2.0**（コスパ＆モーション最強）
- ヒーローカット（最高品質・ナレ音声同期）→ **Veo 3.1**（4K・ネイティブ音声）

鍵は fal 1本で全モデルに通る。毎案件 AskUserQuestion で枠を選ばせてよい。

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

ツール：`generate_speech`（ブロッキング、各5〜15秒）

```typescript
generate_speech({
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
3. **BGMミックス**：volume=0.16〜0.18 (-15dB前後)、fade in 1.2s / fade out 2s。
   - **途切れ防止**：曲尺 ≥ 動画尺の曲を選び **ループしない**（`stream_loop` の継ぎ目は"途切れ"に聞こえる）。足りない時のみ acrossfade でループ。末尾は必ず 2秒フェードアウトし、`volumedetect` で末尾が十分小さいか確認。
   - フリー定番曲を使う場合の取得・選定・著作権は `references/bgm-selection.md` を参照（Web音源は Claude in Chrome で取得 → `~/Downloads` を mount → cp）。
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
6. `references/bgm-selection.md` — ★ショート向けBGM選定（YouTuber定番フリー曲・取得・著作権・途切れ防止）
7. `references/cinematic-camera-move.md` — ★シネマティック・カメラムーブモード（どんな画像でも動かす汎用版：6プリセット・カメラ語彙・著作権注意）
8. `references/drone-aerial-fpv.md` — ★ドローン空撮プリセットの詳細（ヒアリング→クリーン起点→6ビート→Seedance 2.0）
8. `references/character-consistency-pipeline.md` — ★キャラ／商品の一貫性モード（キービジュアル→設定シート→i2v。i2vは起点画像=1フレーム目の罠も）

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
