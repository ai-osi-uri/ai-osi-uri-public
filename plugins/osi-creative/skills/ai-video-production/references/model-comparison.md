# モデル比較・使い分けガイド

「AI OSI URI Creative」コネクタ（旧 fal-video）が公開する13ツールの中から、シーンに合わせて選ぶ。

> **モデル指定の仕組み**：`model` 引数には ① コネクタに登録済みの **ショートカット slug**（`veo31-fast` 等）か、② `fal-ai/` ・ `bytedance/` で始まる **生エンドポイント**を直接渡せる。
> ✅ **v0.5 以降**：Veo 3.1（`veo31` / `veo31-fast`）・Kling 3.0（`kling30`）・Seedance 2.0（`seedance20`）はすべて slug 登録済み。Seedance の `bytedance/` 始まりエンドポイントも解決できる（v0.4 までは `Unknown video model` で弾かれていた）。

---

## 動画モデル（2026現行・フラッグシップ3枠）

> 2026年現在、fal 1本で下記すべてに通る。毎案件 AskUserQuestion で枠を選ばせてよい。
> 価格は fal の従量（秒単価）。**8秒クリップ**を基準にした目安を併記する。

### Veo 3.1 Fast（`fal-ai/veo3.1/fast`）★標準デフォルト
- 安く写実。環境・抽象・単独人物に最強の汎用枠
- 単価：**$0.10/s**（720p/1080p, audio off）〜 $0.35/s（4K+audio） → 8s ≒ **$0.80〜**
- ネイティブ音声トグル対応、最大 8s/生成（チェーンで延長可）
- i2v は `fal-ai/veo3.1/fast/image-to-video`
- **使用シーン**：オフィス、街、データ画面、抽象、自然、単独人物
- **苦手**：複数人物の細かい相互作用（→ Kling 3.0）

### Veo 3.1（`fal-ai/veo3.1`）ヒーローカット用
- 最高品質・**4K**・ネイティブ音声同期。ナレ音声まで一発で乗せたいヒーローカット向け
- 単価：**$0.20/s**（標準）〜 $0.60/s（4K+audio） → 8s ≒ **$1.60〜**
- バリアント：`/image-to-video`, `/first-last-frame-to-video`, `/reference-to-video`, `/extend-video`（各 `/fast/` 版あり）
- **使用シーン**：本当のヒーローカット1〜2本、最終ロゴカット

### Kling 3.0 Pro（`fal-ai/kling-video/o3/pro/text-to-video`）人物・連結に強い
- 人物動作・物理表現が最強クラス。**最大6カット連結**・per-shot プロンプト（カットごとに尺指定）
- 単価：**$0.112/s**（audio off）/ $0.168/s（audio on） → 8s ≒ **$0.90〜$1.34**
- 最大 1080p、3〜15s
- i2v は `fal-ai/kling-video/o3/pro/image-to-video`、廉価枠は `fal-ai/kling-video/o3/standard/text-to-video`
- **使用シーン**：握手、対話、複数人会議、家族、コミュニティ、連続アクション
- **苦手**：単純な環境カット（→ Veo 3.1 Fast の方が安い）

### Seedance 2.0（slug `seedance20`）コスパ＆モーション最強
- 激しい動き・スポーツ・ダンス・衝突などの物理表現に強い。多参照入力（**画像9 / 動画3 / 音声3**）対応
- 単価：**$0.3034/s**（標準）/ $0.2419/s（fast slug `seedance20-fast`） → 8s ≒ **$2.4 / $1.9**
- 最大 720p（fal）、4〜15s（`duration: "auto"` で自動最適化）、ネイティブ音声込み
- マルチショットは "Shot 1:" ラベルでプロンプト内指定
- **使用シーン**：激しいモーション、モンタージュ、多素材参照の合成
- ✅ **v0.5 で利用可**：`seedance20` / `seedance20-fast` / `seedance20-i2v` で呼べる（生 `bytedance/seedance-2.0/...` も可）

### レガシー／フォールバック枠（コネクタに slug 登録済み・引き続き使用可）
| slug | 用途 |
|---|---|
| `veo3-fast` / `veo3` | Veo 3 系（旧標準）。3.1 が使えない時のフォールバック |
| `kling25` / `kling25-i2v` | Kling 2.5 Turbo Pro。3.0 が使えない時のフォールバック |
| `minimax` / `minimax-i2v` | MiniMax Hailuo 02。$0.15〜$0.50、予算逼迫時 |
| `hunyuan` | Tencent Hunyuan。抽象・風景・エモーショナル |
| `luma` | Luma Dream Machine。text+image 両対応、滑らかなカメラ |

---

## 推奨シーン別配分

### スタイル：ドキュメンタリー実写

| シーン | モデル | 理由 |
|---|---|---|
| ① オフィスの単独人物 | Veo 3.1 Fast | 環境＋単独人物、写実 |
| ② 国際会議（複数人） | Kling 3.0 | 多人数対話・連結 |
| ③ 金融街・データ | Veo 3.1 Fast | 環境・グラフィック |
| ④ 朝の東京 | Veo 3.1 Fast | 街並み |
| ⑤ 困った経営層（会議） | Kling 3.0 | 複数人物の表情 |
| ⑥ 画面・図書館 | Veo 3.1 Fast | 抽象 |
| ⑦ デザインチーム | Kling 3.0 | 多人数ブレスト |
| ⑧ 握手のクローズアップ | **Veo 3.1（ヒーロー）または Kling 3.0** | ヒーローカット候補 |
| ⑨ オフィスタイムラプス | Veo 3.1 Fast | 環境 |
| ⑩ 3モニター統合 | Veo 3.1 Fast | 抽象・グラフィック |
| ⑪ 多様な日常モンタージュ | Seedance 2.0 または Kling 3.0 | 多シーン・激しい動き |
| ⑫ ロゴカード | Veo 3.1 Fast | 静謐 |

合計コスト目安（8s/カット基準）：Veo 3.1 Fast×7（≒$5.6）＋Kling 3.0×5（≒$4.5）＝ **約 $10**。
コスト最優先なら全カット Veo 3.1 Fast で **約 $6.4**。

### スタイル：アニメ（ジブリ風）

全シーン Veo 3.1 Fast で統一。
- 「Studio Ghibli style 2D hand-drawn anime」を強くアンカー
- IP filter回避のため "watercolor" "hand-painted" を併記
- 全12本で約 **$6.4**

---

## 静止画モデル（i2v 起点フレーム用）

i2v（image-to-video）は「静止画を作る → `fal_image_to_video` の起点に渡す」流れ。**起点の静止画は fal ではなく専用の直コネクタで作る**（ElevenLabs を直で呼ぶのと同じ思想：直の方が一貫性・グラウンディング・テキスト精度で有利）。

| コネクタ | モデル | ツール | 強み | 鍵 |
|---|---|---|---|---|
| **`nano-banana`** ★既定 | Gemini Nano Banana Pro | `generate_image` / `edit_image` | **キャラ/絵柄の一貫性**・雰囲気・量産・グラウンディング | `GEMINI_API_KEY` |
| **`openai-image`** | OpenAI GPT Image 2 | `openai_generate_image` / `openai_edit_image` | 写実の極み・**画面内テキスト/ロゴ/コピー焼き込み**・指示追従 | `OPENAI_API_KEY` |

### 使い分け（動画フレーム用途）
- **多シーンで同じ人物・世界観を揃えたい**（動画の基本）→ **`nano-banana`**。1枚キーフレームを作り、`edit_image` で「同じ人物のまま別シーン」を派生させると一貫性が保てる
- **ヒーロー静止画・写実の極み・テロップ/ロゴ/コピーを画像内に焼く** → **`openai-image`（GPT Image 2）**
- 2枚を併用して使い分けるのが基本（どちらか一方ではない）

### 標準フロー（i2v）
```
1. nano-banana の generate_image でシーン①のキーフレーム生成
2. nano-banana の edit_image で②③…を「同じ人物・絵柄」で派生（一貫性キープ）
   ※ テロップ/ロゴ入りカットは openai-image で焼き込む
3. 各フレームを fal_image_to_video（kling30-i2v / veo31-i2v）に渡して動画化
```

> なぜ fal 経由で画像を作らないか：fal にも画像モデルはあるが、(1) 画像は専用直コネクタが既にあり、(2) Gemini 直は Google 検索グラウンディング、(3) GPT Image 2 直はテキスト描画精度、(4) ElevenLabs と同じく「直の方が機能欠損が無い」という整理。動画/音楽は fal アグリゲータ、音声/画像は直、が現行の役割分担。

---

## 音声系モデル

> **重要**：v8〜v24の検証で確立した結論
> - 日本語動画は **ElevenLabs DIRECT API + Eleven v3 + クローンvoice** が最高品質
> - fal.ai プロキシ経由よりも DIRECT が安定（402エラーなし、感情タグ完全対応）

### ElevenLabs v3（`elevenlabs-v3`）★現在の標準（2025〜）
- 最新モデル、**感情タグ対応**（`[calm]` `[hopeful]` 等）
- クローンvoice との相性が抜群、抑揚が自然
- 単価：~$0.30 / 1K chars
- 1動画 12シーンで約 $0.50
- **stability**: 0.35〜0.5（低いほど抑揚強）
- **推奨**：すべてのIR/PR/採用動画はこれを使う
- **必ずTTSルール（templates/narration-rules.md §8）を遵守**

### ElevenLabs Multilingual v2（`elevenlabs-v2`）
- 安定的、日本語OK、感情タグ非対応
- 単価：~$0.18 / 1K chars
- **使用シーン**：v3 が不調・ベータが嫌なとき

### ElevenLabs Turbo v2.5（`elevenlabs-turbo`）
- 高速・安価
- 単価半額
- 品質はやや劣る
- **使用シーン**：プロト試聴

### 利用方法：DIRECT API 推奨
fal.ai 経由ではなく、**ElevenLabs Direct API** を直接呼ぶのが本番運用の鉄則。
理由：
- ライブラリvoice（GENEL等）が確実に使える
- voice_settings（stability, similarity_boost）の細かい制御
- 感情タグ `[calm]` `[hopeful]` 等が完全に効く
- レスポンスが速い、エラーが少ない

```bash
ELEVENLABS_API_KEY=sk_xxx
curl -X POST https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "[calm]人の価値は、正しく評価されているでしょうか。",
    "model_id": "eleven_v3",
    "voice_settings": {"stability": 0.4, "similarity_boost": 0.85}
  }' --output scene01.mp3
```

---

## 音楽系モデル

### Stable Audio（`stable-audio`）★標準
- 1〜47秒のクリップ生成
- 単価 $0.20 / clip
- ループで長尺カバー（ffmpeg `-stream_loop -1`）
- **注意**：レスポンスは `audio_file.url` で返ってくる（MCP の extractMediaUrl で拾えない場合あり）

### CassetteAI（`cassetteai`）
- 最大 3分まで一発生成
- 単価高め
- ループ不要

### Lyria 2（`lyria2`）
- 高品質、短尺
- ヒーロースティング向け

---

## ボイスプリセット

### A. 多言語汎用voice（fal.ai 経由でも DIRECT でも使える）

`fal_list_voices` で確認：

| プリセット | ElevenLabs voice | 用途 |
|---|---|---|
| calm-male | Adam | 落ち着いた男性、企業VI標準 |
| deep-male | Onyx | ドキュメンタリー、深い声 |
| calm-female | Rachel / Sarah | 落ち着いた女性、IR・PR |
| warm-female | Bella | 温かい、ブランド紹介 |
| energetic-male | Antoni | 力強い、ピッチ・ホテル起業家系 |

**注意**：これらは英語ベースの多言語voice。日本語の癖（長音脱落、小書き分離）あり。
narration-rules.md §1〜§7 のカタカナ強制ルールが必須。

### B. ネイティブクローンvoice ★現在の標準

| Voice ID | 名前 | 性別 | 特徴 |
|---|---|---|---|
| `GxhGYQesaQaYKePCZDEC` | **GENEL voice** | 女性 | **★OKWEB×JINENで採用。日本人ネイティブクローン、自然な抑揚** |

**使うには**：ElevenLabs **Starter プラン以上 ($5/月)** が必須。
Free tier では `402 paid_plan_required` エラー。

**癖**：自然な日本語だが、漢字の読み判定にやや誤り。
narration-rules.md §8 のひらがな化ルールが必須。
（27年→にじゅうななねん、AI→エーアイ、見える化→みえるか、等）

### Voice 選択の最終ルール

```
社内動画制作の標準フロー:
1. ElevenLabs Starter 以上に加入
2. GENEL voice (GxhGYQesaQaYKePCZDEC) をデフォルト
3. テキストを §8 のひらがな化ルールで最適化
4. Eleven v3 + 感情タグ + stability 0.35
5. DIRECT API で生成
6. ffmpeg で動画合成

→ プロ品質ナレーションが 1動画あたり $0.50 で完成。
```

詳細は **`templates/voice-strategy.md`** を必ず読むこと。

---

## コスト試算式

```
動画コスト = Σ (各シーンのモデル単価)
ナレコスト = 動画尺 × 0.10 × $0.30 / 1K chars  ※v3使用時
            ≒ $0.50 / 12シーン
BGMコスト = $0.20
合計 ≒ $5〜$10

※ ElevenLabs プラン代:
 - Starter $5/月（library voice 使用、月30K chars）
 - Creator+ $22/月（自分の声をクローン、Instant Clone × 10）
```

---

## 制作チェックリスト

新規動画制作の前に必ず確認：

- [ ] スタイル決定（ドキュメンタリー実写 / アニメ / ピッチ）
- [ ] シーン別モデル選択（上記マッピング参照）
- [ ] voice 選択（A 汎用 or B クローン）
- [ ] ElevenLabs プラン確認（Starter以上ならGENEL OK）
- [ ] テキスト最適化（voice 型に合わせて narration-rules.md 参照）
- [ ] 感情タグマップ確認（voice-strategy.md §3）
- [ ] BGM 選定
- [ ] コスト見積もり（$5〜$10レンジ内か）
