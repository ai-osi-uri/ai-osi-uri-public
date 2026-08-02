# モデル比較・使い分けガイド

「AI OSI URI Creative」コネクタ（旧 fal-video）が公開する13ツールの中から、シーンに合わせて選ぶ。

> **モデル指定の仕組み**：`model` 引数には ① コネクタに登録済みの **ショートカット slug**（`veo31-fast` 等）か、② `fal-ai/` ・ `bytedance/` で始まる **生エンドポイント**を直接渡せる。
> ✅ **v0.5 以降**：Veo 3.1（`veo31` / `veo31-fast`）・Kling 3.0（`kling30`）・Seedance 2.0（`seedance20`）はすべて slug 登録済み。Seedance の `bytedance/` 始まりエンドポイントも解決できる（v0.4 までは `Unknown video model` で弾かれていた）。

---

## 動画モデル（2026-08 現行）

> 単価は fal の従量（秒単価）。**8秒クリップ**基準の目安を併記。改定が速いので、金額は発注前に fal のモデルページで確認する。

### 使い分けの原則：カットの性質で価格帯を分ける

**全カットを同じモデルで作らない。** 人物が破綻しない領域に高単価モデルを使うのは無駄。

| カットの性質 | 推奨 slug | 単価目安 | 理由 |
|---|---|---|---|
| 環境・風景・抽象（人物なし） | **`ltx23`** / `ltx23-fast` | $0.06 / $0.04 per s | 破綻リスクが低い領域。単発20秒・最大4Kで尺も稼げる |
| 単独人物・標準カット | **`veo31-fast`** | $0.10〜 per s → 8s ≒ $0.80 | 安く写実。汎用の標準枠 |
| **喋る人物・リップシンク** | **`happyhorse-i2v`** | $0.14〜0.18 per s | **日本語を含む7言語のネイティブ・リップシンク**。1080p 音声同期でこの価格は突出 |
| 複数人物・対話・激しい動き | **`kling30`** / `kling30-i2v` | $0.112（音声off）/ $0.168（on）per s | 人物動作・物理表現。最大6カット連結・per-shot プロンプト |
| キャラ一貫の連番カット | **`wan27-ref`** | $0.10 per s 一律 | キャラ参照＋声の一貫性を最安クラスで |
| ムーブボード（線駆動カメラ） | **`seedance20-ref`** | $0.30 per s | 参照モード。線が出力に出ない（#17 の根本解決） |
| ↑の当たり確認・試作 | **`seedance20-mini-ref`** | 最安ティア | 構図の当たりを安く取ってから本番へ |
| ヒーローカット（1〜2本だけ） | **`veo31`**（4K・ネイティブ音声） | $0.20〜0.60 per s | 本当の見せ場に限定する |

### 注意すべき課金の癖

- **Seedance 2.0 は常に音声込みで課金**（$0.3034/s〜）。無音カットに使うと割高。無音なら `kling30`（音声off $0.112/s）や `ltx23` に逃がすとコストが約1/3。
- **エンドポイントの名前空間がベンダーごとに違う**。`fal-ai/` のほか `bytedance/` `alibaba/` `minimax/` `google/` がある。slug を使えば意識不要。

### 連結・尺の制御

| 用途 | slug |
|---|---|
| 参照画像でキャラ一貫 | `veo31-ref` / `wan27-ref` / `seedance20-ref` |
| 開始/終了フレーム指定（厳密な構図制御。躍動感は落ちる） | `veo31-flf` |
| 生成済み動画の尺を延長 | `veo31-extend` |

### Kling の系統に注意

fal 上では **`v3` 系と `O3` 系が別ライン**として並存する（どちらも 2026-02 追加）。
- `kling30` / `kling30-i2v` → **O3 ライン**（`fal-ai/kling-video/o3/pro/...`）
- `kling3` / `kling3-i2v` → **v3 ライン**（`fal-ai/kling-video/v3/pro/...`）

slug 名が紛らわしいので、指定時は `list_models` で endpoint を確認する。

### Seedance 2.5 について（2026-08 時点）

2026-07-31 に発表。単発30秒・参照最大50点・4K・3Dカメラブロックアウトと大幅強化されているが、
**fal.ai には未提供**（fal 公式が「未リリース」と明記）。Volcano Ark / BytePlus 側で API 開放が近いとされる。
fal に載り次第 `seedance25*` を追加する。**それまでは 2.0 で組む。**

### レガシー／フォールバック枠

| slug | 用途 |
|---|---|
| `veo3` / `veo3-fast` | Veo 3 系（旧標準）。3.1 が不調なときのみ |
| `kling25` / `kling25-i2v` | Kling 2.5 Turbo Pro |
| `minimax` / `minimax-i2v` | MiniMax Hailuo 02 |
| `hunyuan` | Tencent Hunyuan |
| `luma` | Luma Dream Machine |

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

i2v は「静止画を作る → `image_to_video` の起点に渡す」流れ。起点画像は Creative の `generate_image` で作る
（fal 経由なので **fal キー1本で完結**。別 Gemini キーは不要）。

| slug | 実体 | 単価目安 | 使いどころ |
|---|---|---|---|
| **`nano-banana-2`** ★既定 | Gemini 3.1 Flash Image | 約 $0.08/枚 | 4K・複数参照・確実なテキスト描画。ほぼこれで足りる |
| `nano-banana-pro` | Gemini 3 Pro Image | 約 $0.15/枚 | **人物参照5枚＋スタイル参照3枚**。キャラ一貫性が最重要なときだけ |
| `nano-banana` | Gemini 2.5 Flash Image（初代） | 約 $0.039/枚 | レガシー。Google は Nano Banana 2 系への移行を推奨 |
| `flux` | FLUX schnell | 最安 | 雰囲気だけのラフ |

### キャラ一貫性で使える参照枚数（Google 公式）

| | nano-banana-2 | nano-banana-pro |
|---|---|---|
| オブジェクト参照 | 最大10枚 | 最大6枚 |
| **人物（キャラ一貫性）** | **最大4枚** | **最大5枚** |
| スタイル参照 | 非対応 | 最大3枚 |

→ 設定シート1枚だけを参照に渡す運用は過去のもの。**別角度・別表情を複数枚まとめて渡せる**。

### 使い分け（動画フレーム用途）
- **多シーンで同じ人物・世界観を揃えたい**（動画の基本）→ Creative の `generate_image` で1枚キーフレームを作り、`edit_image` で「同じ人物のまま別シーン」を派生させると一貫性が保てる
- **テロップ/ロゴ/コピーを画像内に焼く必要がある** → 任意で `openai-image`（GPT Image 2）を別途導入
- 既定は **Creative 1本でOK**。openai-image は焼き込みが要るときだけ追加する

### 標準フロー（i2v）
```
1. generate_image（model: nano-banana / 4Kは nano-banana-pro）でシーン①のキーフレーム生成
2. edit_image で②③…を「同じ人物・絵柄」で派生（一貫性キープ）
   ※ テロップ/ロゴ入りカットは任意で openai-image で焼き込む
3. 各フレームを image_to_video（kling30-i2v / veo31-i2v）に渡して動画化
```

> v0.6.0 での方針変更：以前は「画像は専用直コネクタ(nano-banana=Gemini直)で作る」設計だったが、**fal が nano-banana 本体をホストしている**ため、Creative 1コネクタ＋fal キーに統合した（別 Gemini キー・LOCAL DEV の nano-banana コネクタは不要）。テキスト焼き込みが要る案件のみ openai-image を任意で併用。動画/音楽/画像/ナレーションが Creative 1本に集約。

---

## 音声系モデル → `narration` スキルが正本

ナレの声・モデル・パラメータ・発音辞書は **`../../narration/`** に集約した。ここでは重複させない。

| 知りたいこと | 参照先 |
|---|---|
| 声の選択・感情タグマップ・プラン要件 | `../../narration/templates/voice-strategy.md` |
| 発音辞書ルールの作り方（alias / IPA） | `../../narration/templates/narration-rules.md` |
| 手順（誤読検出→辞書登録→生成） | `../../narration/SKILL.md` |

要点だけ：**日本語ネイティブ声（既定 Konoha）× `elevenlabs-v3` × クリーンテキスト＋発音辞書**。
原稿の字面を壊す旧方式（ひらがな化・カタカナ強制・GENEL固定）は廃止。

コスト目安：v3 で 12シーン約 $0.50。

## 音楽系モデル

| slug | 実体 | 最大尺 | 使いどころ |
|---|---|---|---|
| **`stable-audio-3`** ★既定 | Stable Audio 3 Medium | **6分20秒** | **一発生成でループ不要**＝BGMの継ぎ目が途切れて聞こえる問題が構造的に消える。学習データが全てライセンス済みで商用の法務リスクが低い（年商$1M超は法的補償付きの Enterprise あり） |
| `stable-audio-3-sfx` | Stable Audio 3 Small SFX | 2分 | 効果音 |
| `cassetteai` | CassetteAI | 3分 | 最安クラス（$0.02/出力分）。尺が足りるなら実用 |
| `lyria2` | Google Lyria 2 | 30秒 | 短尺スティング |
| `stable-audio` | Stable Audio Open（レガシー） | 47秒 | ループ必須で継ぎ目が出る。新規では使わない |

> **ショート/SNS狙いは AI生成より「YouTuber定番のフリー曲」が刺さる**ことが多い。
> 選定・取得・著作権・途切れ防止は `bgm-selection.md` を参照。

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
- [ ] voice 選択（日本語ネイティブ。既定 Konoha）
- [ ] ElevenLabs プラン確認（Library voice は Starter 以上）
- [ ] ナレ原稿はクリーンなまま（発音辞書で読みを補正／`../../narration/SKILL.md`）
- [ ] 感情タグマップ確認（`../../narration/templates/voice-strategy.md` §3）
- [ ] BGM 選定
- [ ] コスト見積もり（$5〜$10レンジ内か）
