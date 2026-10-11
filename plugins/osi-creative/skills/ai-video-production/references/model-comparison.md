# モデル比較・使い分けガイド

「AI OSI URI Creative」コネクタ（旧 fal-video）が公開するツールの中から、シーンに合わせて選ぶ。

> **モデル指定の仕組み**：`model` 引数には ① コネクタに登録済みの **ショートカット slug**（`veo31-fast` 等）か、② `fal-ai/` `bytedance/` `alibaba/` `minimax/` `google/` `lightricks/` `xai/` `blackforestlabs/` で始まる **生エンドポイント**を直接渡せる。**slug が無い新モデルもコネクタ改修なしで使える**（ただしこの8つ以外の名前空間はコネクタへの追加が要る）。
> ✅ **v0.5 以降**：Veo 3.1（`veo31` / `veo31-fast`）・Kling 3.0（`kling30`）・Seedance 2.0（`seedance20`）はすべて slug 登録済み。Seedance の `bytedance/` 始まりエンドポイントも解決できる（v0.4 までは `Unknown video model` で弾かれていた）。

---

## 動画モデル（2026-10-11 現行・コネクタ v2.4）

> 単価は fal の従量（秒単価）。**8秒クリップ**基準の目安を併記。改定が速いので、金額は発注前に fal のモデルページで確認する。
>
> **単価・解像度・尺の正本は fal の `llms.txt`。** 任意のモデルについて
> `https://fal.ai/models/<endpoint-id>/llms.txt` を開くと、resolution/duration の enum と課金式が
> 機械可読で出る（例: `https://fal.ai/models/bytedance/seedance-2.0/text-to-video/llms.txt`）。
> **このファイルの数字を信じる前に、必ずそこで突き合わせる。** 過去に本ファイルの解像度記述が
> 3か月古いまま残り、使えるはずの 1080p / 4K を「非対応」と書いていた事故がある。

### 使い分けの原則：カットの性質で価格帯を分ける

**全カットを同じモデルで作らない。** 人物が破綻しない領域に高単価モデルを使うのは無駄。

| カットの性質 | 推奨 slug | 単価目安 | 理由 |
|---|---|---|---|
| 環境・風景・抽象（人物なし） | **`ltx25-fast`** / `ltx25` | $0.09（720p）/ $0.13（1080p）per s | 破綻リスクが低い領域。単発20秒・最大4K・音声つき・マルチショット。2.3 より顔・文字・速い動きが改善 |
| **試作・当たり取り（全カット共通）** | **`h3max-turbo`** / `h3max` / `h3max-i2v` | Turbo $0.04・通常 $0.08 per s（768P） | **5秒が3秒未満で返る**。音声込み。詳細は下の「H3 Max」節 |
| 単独人物・標準カット | **`veo31-fast`** | $0.10〜 per s → 8s ≒ $0.80 | 安く写実。汎用の標準枠 |
| **喋る人物・リップシンク** | **`happyhorse-i2v`** | $0.14〜0.18 per s | **日本語を含む7言語のネイティブ・リップシンク**。1080p 音声同期でこの価格は突出 |
| 複数人物・対話・激しい動き | **`kling30`** / `kling30-i2v` | $0.112（音声off）/ $0.168（on）per s | 人物動作・物理表現。最大6カット連結・per-shot プロンプト |
| キャラ一貫の連番カット | **`wan30-ref`** / `h3max-ref` | fal で確認 | 画像・動画・音声の参照でキャラと声を保つ（`wan27-ref` の後継） |
| ムーブボード（線駆動カメラ） | **`seedance20-ref`** | $0.30 per s | 参照モード。線が出力に出ない（#17 の根本解決） |
| ↑の当たり確認・試作 | **`seedance20-mini-ref`** | 最安ティア | 構図の当たりを安く取ってから本番へ |
| ヒーローカット（1〜2本だけ） | **`veo31`**（4K・ネイティブ音声） | $0.20〜0.60 per s | 本当の見せ場に限定する |

### 注意すべき課金の癖

- **Seedance 2.0 は常に音声込みで課金**（720p $0.3034/s・**1080p $0.682/s**）。無音カットに使うと割高。無音なら `kling30`（音声off $0.112/s）や `ltx23` に逃がすとコストが約1/3。
- **エンドポイントの名前空間がベンダーごとに違う**。`fal-ai/` のほか `bytedance/` `alibaba/` `minimax/` `google/` `lightricks/` `xai/` `blackforestlabs/` がある。slug を使えば意識不要。**この8つは生エンドポイントとしてそのまま `model` に渡せる**（コネクタの `RAW_ENDPOINT_PREFIXES`）。slug 未登録の新モデルは、コネクタを直さなくても今日から使える。

### 解像度：モデルごとに上限が違う（コネクタ v2.2 で修正済み）

**「上位バージョンほど高解像度」ではない。** Seedance で 4K が通るのは 2.0 だけ。

| slug | 受け付ける resolution |
|---|---|
| `seedance20` / `seedance20-ref` | 480p / 720p / 1080p / **4k** |
| `seedance25` / `-i2v` / `-ref` | 480p / 720p / **1080p**（4K は無い） |
| `seedance20-mini` | 480p / 720p |
| `h3max` 系（`-i2v` / `-turbo` / `-ref` / `-camera`） | **480P / 768P / 1080P**（大文字 P。他モデルと綴りが違う） |
| `ltx25-fast` / `ltx25-i2v-fast` | 720p / 1080p / 1440p / **2160p** |
| `ltx25` / `ltx25-i2v` | 720p / 1080p |
| `wan30` 系 / `wan30-prime` 系 | 480p / 720p / 1080p |
| `vidu-q4-i2v` / `-ref` | 540p / 720p / 1080p / **2K / 4K** |
| `gemini-omni` 系 | 360p / 720p / 1080p / **4k** |
| `veo31-lite` 系 | 720p / 1080p |
| 上記以外 | 検証していないので素通し。fal 側が判断する |

モデルに無い値を渡すと、**fal に送る前に**「Allowed: …」付きのエラーで止まる。

> **v2.1 までの既知の不具合（履歴として残す）**：ツールスキーマの `resolution` が
> `enum:["480p","720p"]` に固定され、さらに `resolution` を受け付ける指定が `seedance25` 系
> 3本にしか付いていなかった。結果、**Seedance 2.0 は解像度を指定できず 720p 固定、
> 2.5 の 1080p は黙って捨てられていた**。呼び出し側にエラーが出ないので誰も気付かなかった。
> → v2.2 でモデルごとの許可リストに置き換え、未知の値は素通し＋既知の違反は明示エラー、に変更。
> **「黙って落とす」実装を書かない。** 落ちたことが見えない失敗が一番高くつく。

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

### Seedance 2.5（2026-08 に fal で公開済み・利用可）

`seedance25` / `seedance25-i2v` / `seedance25-ref` をコネクタ v2.1 で登録済み。2.0 との差は3点：

| | Seedance 2.0 | **Seedance 2.5** |
|---|---|---|
| 尺 | クリップ単位 | **つなぎ目なしで最大30秒を一発生成**（4〜30秒 or auto） |
| 参照 | 画像9 / 動画3 / 音声3 | **最大50点**（画像30 / 動画10 / 音声10） |
| 尺の配分 | プロンプト任せ | **タイムスタンプ付きショットリスト**で指定できる（pacing control） |
| 尺の上限 | 4〜15秒 | **4〜30秒** |
| 解像度 | 480p / 720p / 1080p / **4k** | 480p / 720p / **1080p**（4K は無い） |

> **解像度の注意**：ByteDance 本家の発表では 2.5 は 4K だが、**fal のエンドポイントは 1080p まで**。
> 逆に **2.0 は fal でも 4K が通る**（`resolution: "4k"`、$0.008/1K tokens と 1080p より安いトークン単価）。
> 「2.5 の方が上位だから解像度も上」ではない。**最高解像度が要るカットは 2.0 を使う。**
>
> `seedance20-ref` は**動画参照を渡すと単価が0.6倍**になる（720p $0.3034/s → **$0.1814/s**）。
> ムーブボードを動画で渡す運用は、画像だけで渡すより安い。

**単価**：トークン課金 $0.0214/1K（tokens = 縦×横×秒×24/1024）。16:9 換算で **720p 約 $0.473/秒・480p 約 $0.2205/秒**。
30秒フルだと 720p で約$14、480p で約$6.6。**veo31-fast の4〜5倍**。

**既定にはしない。** 動画名刺（6ビート）のような分割構成では、1ビートだけ約$0.8で撮り直せる
veo31-fast × 6本の方が量産に強い。2.5 でワンパス30秒を撮ると、1カット外しただけで全額を捨てる。

使うのは次の2つの場面に限る：

1. **同一人物・同一キャラを複数カットで崩したくない** → `seedance25-ref` に参照を束で渡す
   （`extra.image_urls` / `video_urls` / `audio_urls`、プロンプト内で `[Image1]` のように指す）。
   個人の自己紹介動画（`vp-personal-intro` の L1 アバター）で最も効く。
2. **ヒーローの1本**（社長・看板メンバー）を、連結・尺合わせの工程ごと省いて一発で出したい。

### H3 Max（2026-08-26・`h3max` / `h3max-i2v` は v2.2、`h3max-turbo` / `-turbo-i2v` / `h3max-ref` / `h3max-camera` は v2.4 で登録）

fal Research が MiniMax H3（7/31 リリースの omni-modal 公開重み）を**再学習＋推論最適化**した派生。
本家 MiniMax の公式エンドポイントに対して**品質で上、速度で約35倍**という珍しい位置にいる。

```
model: "h3max"            // t2v。resolution: "480P" | "768P" | "1080P"（大文字P）
model: "h3max-i2v"        // i2v
model: "h3max-turbo"      // 半額版（t2v）。h3max-turbo-i2v も有り
model: "h3max-ref"        // reference_to_video で使う（画像・動画・音声の参照）
model: "h3max-camera"     // i2v。extra.camera_trajectory でカメラ軌道を指定
extra: { "prompt_expansion_mode": "quality" }   // 任意。~30秒かけて richer な prompt に書き換える
```

| | 値 |
|---|---|
| 速度 | **5秒クリップが3秒未満**（平均レイテンシ 3.49s）。Seedance 2.5 は 68s、Gemini Omni Flash は 27s |
| 単価 | 480P $0.05/s・768P $0.08/s・1080P $0.16/s（promo は 9/7 で終了）。Turbo は半額 |
| 解像度 | 480P / 768P / **1080P**（2026-10 時点） |
| 尺 | 5〜15秒 |
| 音声 | **ネイティブ同期音声が常時付く**（別パス不要） |
| モード | t2v / i2v / **reference-to-video（8/29 追加）** / カメラ制御 / Turbo。fal には他に lip-sync・relight・recast・extend・スタイル系もある（動画→動画の道具が要るので未登録） |
| 評価 | Artificial Analysis・Design Arena いずれも i2v(音声付き) で1位 |

**使いどころは「試作の高速化」であって、納品の置き換えではない。** 1080P は出せるようになったが、
最終納品の画質は veo31 / seedance に分がある。逆に、これまで「1本2分待つから3案しか試さない」だった工程を
「20案投げて19本捨てる」に変えられる。**当たりを H3 Max で取り、決まったカットだけ
veo31 / seedance で本番解像度に焼き直す**、という二段構えが今の最適解。

> ※ 実測：`extra:{"resolution":"480P"}` を渡して 832×480・5.17秒・AAC音声つきの MP4 が返ることを確認済み（2026-09-02）。

**fal.live / H3 Max Director**：fal は「生成が再生に追いつく」ことを使って、チャットで指示しながら
無限に生成し続けるライブ配信（`fal.live`）を出している。**これは fal の実験プラットフォームであって
API 製品ではない**ので、案件では使えない。「動画を生成しながら再生できるらしい」という記事は
このデモを指しており、**Seedance ではなく H3 Max の話**。混同しないこと。

### Gemini Omni Flash 1.1（slug `gemini-omni` / `-i2v` / `-ref` を v2.4 で登録）

**期待されていた Veo 4 は出ず、Google の次世代枠はこれになった。** Veo 3.1 は現役のまま。

```
model: "gemini-omni"      // = google/gemini-omni-flash/v1.1/text-to-video。360p〜4k
model: "gemini-omni-i2v"  // image-to-video
model: "gemini-omni-ref"  // reference_to_video（画像・動画の参照）
（/edit＝video-to-video は未登録。生エンドポイントで使う）
```

- 尺 3〜10秒、16:9 と 9:16、ネイティブ同期音声。レイテンシ約27秒
- 品質は H3 Max と 20 Elo 差（ほぼ互角）
- 単価はトークン課金（出力 $21.875/1M tokens）で**高め**
- **`/edit`（video-to-video の会話型編集）は今のスキルに無い能力。**
  「できた動画を言葉で直す」工程を作れる。ムーブボードや連結のやり直しコストが下がる可能性がある

### レガシー／フォールバック枠

| slug | 用途 |
|---|---|
| `veo3` / `veo3-fast` | Veo 3 系（旧標準）。3.1 が不調なときのみ |
| `ltx23` / `ltx23-fast` / `ltx23-i2v` | LTX-2.3。後継は `ltx25-fast` 系 |
| `wan27-ref` | Wan 2.7。後継は `wan30-ref` |
| `kling25` / `kling25-i2v` | Kling 2.5 Turbo Pro |
| `minimax` / `minimax-i2v` | MiniMax Hailuo 02。**H3 Max とは別物**（こちらは旧世代） |
| `hunyuan` | Tencent Hunyuan |
| `luma` | Luma Dream Machine |

### 2026-10 に登録したが、まだ使い分けを決めていない（v2.4）

| slug | 中身 |
|---|---|
| `wan30` / `wan30-i2v` / `wan30-ref`、`wan30-prime` 系 | Alibaba Wan 3.0（音声つき）。起点画像は `start_image_url`（コネクタが自動で合わせる） |
| `grok15` / `-i2v` / `-ref` / `grok15-lite` / `-lite-i2v` | xAI Grok Imagine Video 1.5。ref は画像のみ・480p/720p |
| `vidu-q4-i2v` / `vidu-q4-ref` | Vidu Q4（2026-10-05）。4K まで |
| `pixverse6` / `pixverse6-i2v` | PixVerse V6。`extra.style` でアニメ・クレイ等 |
| `kling3-turbo` / `-i2v` | Kling v3 Turbo Pro（v3 の高速版） |
| `veo31-lite` / `-i2v` | Veo 3.1 の最安版 |
| `happyhorse-ref` | Happy Horse 1.1 の参照版 |
| `flux3-video` / `flux3-i2v` | FLUX 3（Black Forest Labs）。5〜20秒・音声つき |

案件で使ったら、`llms.txt` で単価を取り、上の「使い分けの原則」表に昇格させる。
未登録：`happy-oyster`、Kandinsky 6、Seedance の `/us/` 版、H3 Max の動画→動画系（relight / recast / lip-sync 等）。

### Sora について（顧客に聞かれたとき用）

**OpenAI Sora は終了する。** Web/アプリは 2026-04-26 に停止済み、**API も 2026-09-24 に停止**。
「Sora で作れますか」と聞かれたら、*作れない（正確には、あと数週間で作れなくなる）* と答え、
Seedance 2.5 / Veo 3.1 / H3 Max を代替として出す。**Sora 前提の提案は書かない。**

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
