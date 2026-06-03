# プロンプトテンプレ：ドキュメンタリー実写

Apple "Shot on iPhone" / Patagonia / 採用ブランディング動画系。OKWEBの「ありがとう」の世界観に最適。

## 共通アンカーフレーズ

**冒頭**：
```
Documentary cinematic shot of [SUBJECT],
```

**末尾**：
```
shallow depth of field,
gentle handheld camera (or slow dolly),
realistic photographic style,
warm color grading,
no text overlays,
4K cinematic 24fps documentary aesthetic,
real lifelike footage,
photorealistic
```

## 推奨モデル使い分け

| シーン特性 | モデル |
|---|---|
| 単独人物・環境・抽象 | **Veo 3 Fast** |
| 複数人物・対話・握手 | **Kling 2.5 Turbo Pro** |
| ヒーローカット最高品質 | Veo 3（パラメータ厳しい） |

## 日本人キャラクターの強調

OKWEB事例では海外モデルが多いため、明示的に：
```
... young Japanese office worker ...
... Japanese executives ...
... diverse Japanese business teams ...
... Japanese ethnicity, asian features ...
```

## シーン別プロンプト例（OKWEB事例から）

### ①オープニング（オフィスの女性）
```
Documentary cinematic shot of a young Japanese office worker at her desk
in a softly lit modern Tokyo office in early morning,
warm golden sunlight streaming gently through tall windows,
she stops typing momentarily and looks thoughtfully out the window,
natural facial expression of quiet contemplation,
shallow depth of field with focus on her face and hands,
gentle handheld camera movement,
realistic photographic style, warm color grading with cream and amber tones,
a coffee mug and notepad on the wooden desk,
professional yet very human atmosphere,
no text, 4K cinematic 24fps documentary aesthetic,
real lifelike footage, photorealistic, natural lighting
```

### ②国際会議
```
Documentary cinematic shot of an international business conference
with diverse professionals from multiple countries seated around a large modern conference table,
soft natural daylight from tall windows,
ISO 25554 document and laptop on the table foreground,
a global map visualization on a screen behind,
sense of global cooperation and discussion,
shallow depth of field, gentle handheld camera,
realistic photographic style, warm and professional color grading,
no text, 4K cinematic 24fps documentary aesthetic,
real lifelike footage, photorealistic
```

### ④朝の東京
```
Documentary cinematic shot of morning rush in Tokyo business district,
Japanese salarymen and businesswomen in formal suits walking briskly along Otemachi sidewalks,
modern office buildings in background,
soft golden morning sunlight,
shallow depth of field on their movement,
slow tracking camera,
realistic photographic style, warm color grading,
no text, 4K cinematic 24fps documentary aesthetic,
real lifelike Japanese corporate footage, photorealistic
```

### ⑤困った経営層
```
Documentary cinematic shot of frustrated Japanese business executives in a modern meeting room
looking thoughtfully at complex data on a large screen,
scattered documents on the table,
one executive rubbing his temple, another looking concerned at the data,
sense of unsolved problems,
shallow depth of field, gentle handheld camera,
realistic photographic style, warm but slightly muted color grading,
no text, 4K cinematic 24fps documentary aesthetic, real lifelike Japanese business footage, photorealistic
```

### ⑧握手（ヒーローカット）
```
Documentary cinematic shot of two diverse Japanese business teams meeting
in a bright modern conference room, warm natural daylight streaming in through large windows,
two team leaders, a Japanese woman and Japanese man, shaking hands warmly across a clean glass table,
their colleagues standing behind them with open warm smiles and supportive expressions,
sense of meaningful partnership and synthesis between two organizations,
shallow depth of field focusing on the handshake in the foreground,
gentle slow camera push-in, realistic photographic style,
warm and hopeful color grading, cream and soft daylight tones,
a whiteboard in the background with collaborative sketches and notes,
no text overlays, 4K cinematic 24fps documentary aesthetic,
real lifelike business footage, photorealistic, natural lighting
```

### ⑫クロージング（サンクスカード）
```
Documentary cinematic shot of two thank-you handwritten cards
placed gently next to each other on a clean white wooden surface,
soft warm light from the side, minimal serene composition,
shallow depth of field, slow gentle inward camera push,
realistic photographic style, warm cream tones,
sense of meaningful conclusion and partnership,
no text overlays, 4K cinematic 24fps documentary aesthetic,
real lifelike footage, photorealistic
```

## 共通ボキャブラリ

- 光：warm natural daylight, golden morning sunlight, soft afternoon light
- 質感：cinematic, photorealistic, real lifelike footage
- カメラ：handheld, slow dolly, shallow depth of field
- カラーグレード：warm color grading, cream and amber tones
- ムード：thoughtful, hopeful, contemplative, professional yet human

## 注意事項

### 不気味の谷リスク
顔のクローズアップは避け、引き気味の構図に。
- ❌ "extreme close-up of her face"
- ✅ "shallow depth of field with focus on her face and hands"
- ✅ 後ろ姿、横顔、手のクローズアップを多用

### 西洋人化リスク
プロンプト内で **「Japanese」を3〜4回**繰り返す。
失敗したら Kling 2.5 に切替（アジア系顔の再現が比較的安定）。

### スマホっぽくなりすぎ防止
- "cinematic" を必ず入れる
- "shallow depth of field" でボケ感を出す
- "documentary" + "photorealistic" の組み合わせ
