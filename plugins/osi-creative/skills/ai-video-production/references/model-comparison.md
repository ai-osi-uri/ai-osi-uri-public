# モデル比較・使い分けガイド

fal-video-mcp が公開する13ツールの中から、シーンに合わせて選ぶ。

---

## 動画モデル

### Veo 3（`model: "veo3"`）
- 最高品質、写実・物理表現が強い
- 単価：$0.50〜$3.00 / clip
- duration：固定 8s（変更不可？）
- パラメータが厳しく `Unprocessable Entity` が出やすい
- **使用シーン**：本当のヒーローカット1〜2本のみ
- **注意**：duration_seconds を送るとエラーが出ることあり、デフォルト依存推奨

### Veo 3 Fast（`model: "veo3-fast"`）★標準
- バランス型・推奨デフォルト
- 単価：$0.20〜$0.80 / clip
- duration：8s
- 写実度が高い、環境カット・抽象シーンに最強
- **使用シーン**：オフィス、街、データ画面、抽象、植物、自然
- **得意**：単独人物、風景、CG的なシーン
- **苦手**：複数人物の細かい相互作用、握手など

### Kling 2.5 Turbo Pro（`model: "kling25"`）
- 人物動作・物理表現に強い
- 単価：$0.30〜$1.00 / clip
- duration：5s, 10s 選択可
- アジア系の顔の再現が比較的安定
- **使用シーン**：握手、対話、複数人会議、家族、コミュニティ場面
- **苦手**：単純な環境カット、抽象画

### Kling 2.5 image-to-video（`kling25-i2v`）
- 静止画からの動画化
- 既存ロゴ・キャラクター・実画面を動かしたい場合
- nano-banana で生成した画像を起点にする使い方が安定

### MiniMax Hailuo 02（`minimax`）
- コスパ良
- 単価：$0.15〜$0.50
- 中庸の品質。Veo3 Fast の代替として
- **使用シーン**：予算がタイトな場合のフォールバック

### Hunyuan Video（`hunyuan`）
- シネマティック表現
- 単価：$0.10〜$0.40
- **使用シーン**：抽象、風景、エモーショナルな場面

### Luma Dream Machine（`luma`）
- 滑らかなカメラワーク
- text & image 両対応
- **使用シーン**：環境ショット、エンディング

---

## 推奨シーン別配分（OKWEB事例から）

### スタイル：ドキュメンタリー実写

| シーン | モデル | 理由 |
|---|---|---|
| ① オフィスの単独人物 | Veo 3 Fast | 環境＋単独人物、写実 |
| ② 国際会議（複数人） | Kling 2.5 | 多人数対話 |
| ③ 金融街・データ | Veo 3 Fast | 環境・グラフィック |
| ④ 朝の東京 | Veo 3 Fast | 街並み |
| ⑤ 困った経営層（会議） | Kling 2.5 | 複数人物の表情 |
| ⑥ 画面・図書館 | Veo 3 Fast | 抽象 |
| ⑦ デザインチーム | Kling 2.5 | 多人数ブレスト |
| ⑧ 握手のクローズアップ | **Veo 3 Fast または Kling 2.5** | ヒーローカット候補 |
| ⑨ オフィスタイムラプス | Veo 3 Fast | 環境 |
| ⑩ 3モニター統合 | Veo 3 Fast | 抽象・グラフィック |
| ⑪ 多様な日常モンタージュ | Kling 2.5 | 多シーンの人物 |
| ⑫ ロゴカード | Veo 3 Fast | 静謐 |

合計コスト目安：Veo 3 Fast×7（$2.80）＋Kling 2.5×5（$2.50）＝ **約 $5.30**

### スタイル：アニメ（ジブリ風）

全シーン Veo 3 Fast で統一。
- 「Studio Ghibli style 2D hand-drawn anime」を強くアンカー
- IP filter回避のため "watercolor" "hand-painted" を併記
- 全12本で約 **$5**

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
