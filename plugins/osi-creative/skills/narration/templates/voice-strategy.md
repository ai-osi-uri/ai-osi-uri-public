# Voice Strategy Guide v2（日本語特化：クリーンテキスト＋発音辞書）

ナレ品質を **日本語ネイティブ声 × v3 × G2P前処理＋発音辞書** で最大化する。
旧 v1（テキストを壊す力技）から、**原稿はクリーンに保ち読みは辞書に外出しする**方式へ全面移行（案B）。

---

## 0. 方式の転換（旧→新）

| | 旧（v1・力技） | 新（v2・案B） |
|---|---|---|
| ナレ原稿 | 読みを直すため字面を破壊（デエタ／々（ふりがな）） | **クリーンな漢字かな混じり**（字幕と共用） |
| 誤読対策 | 手作業ハックを毎回作り直す | **pyopenjtalkで自動検出 → 発音辞書(.pls)に蓄積** |
| 蓄積物 | 属人的な暗黙知 | 再利用できる辞書ファイル（共通＋会社別） |
| 声 | 英語ベースのSarah等／GENELクローン | **日本語ネイティブ声（既定 Konoha）** |

---

## 1. 既定の音声（日本語ネイティブ）

```
Voice    : Konoha（日本語ネイティブ女性・プレミアム。自然なリズムと明瞭さ）★ 既定
Model    : elevenlabs-v3   （= eleven_v3。2026 最新フラッグシップ、感情タグ対応）
Stability: 0.4 〜 0.5
Speed    : 1.0
感情タグ : シーン別（§3）
発音辞書 : dict-common.pls ＋ dict-{会社}.pls を pronunciation_dictionaries（辞書名）で適用
```

> ⚙ **セットアップ必須**：Konoha は ElevenLabs Voice Library の声。利用前に自社アカウントへ「Add」し、
> 付与された **voice_id を確認**して使う（`voice:"Konoha"` の名前指定も可だが、アカウント追加済みが前提）。
> Library voice の API 利用は **Starter 以上**。商用可否は Voice Library ページで確認。

### 用途別の声の使い分け（すべて日本語ネイティブ）

| 用途・トーン | 推奨voice | 備考 |
|---|---|---|
| 企業PR / IR / 上品・明瞭 | **Konoha（女性）** ★既定 | 自然なリズム。コーポレート全般 |
| 汎用ナレ / サービス紹介 | Kyoko（女性・落ち着き） | 標準的で幅広い |
| ニュース / 朗読 / 信頼感 | Hideki（男性・落ち着き） | 男性ナレ・会社説明 |
| 最終形（最強の差別化） | **自社メンバーの声クローン** | Creator+ で日本語クローン |

---

## 2. なぜ「クリーンテキスト＋辞書」なのか

- v3 は **発音辞書（Pronunciation Dictionaries）** に対応：`alias`（別読み）と `phoneme`（IPA、v3は非英語も対応）。
- 読みを辞書に外出しすれば、**原稿＝字幕を同一テキストに**でき、二重管理が消える。
- 辞書は **案件横断で蓄積・再利用** できる資産。新案件の立ち上げが速くなる。
- 解決順は **alias（かな読み）でほぼ解決 → 頑固な箇所だけ IPA**。v3のIPAは一貫性80〜90%。

---

## 3. 感情タグマップ（Eleven v3）

テキスト**先頭に角括弧**でタグ。読みではなく抑揚・温度感を制御する（読みは辞書側）。

| タグ | 雰囲気 | 適用 |
|---|---|---|
| `[thoughtful]` | 思慮深い・問いかけ | 問題提起・オープニング |
| `[calm]` | 落ち着き・信頼 | 標準説明・IR |
| `[serious]` | 重さ・問題意識 | 課題・リスク |
| `[confident]` | 自信・強調 | 強み・サービス |
| `[hopeful]` | 期待・ビジョン | 未来・クライマックス |
| `[warm]` | 余韻・親しみ | クロージング |
| `[excited]` | 高め | 採用・商品紹介 |

### 12シーン標準（IR/PR）
①[thoughtful] ②[calm] ③[calm] ④[calm] ⑤[serious] ⑥[confident] ⑦[confident] ⑧[hopeful] ⑨[calm] ⑩[confident] ⑪[hopeful] ⑫[warm]

---

## 4. ワークフロー（案B）

1. **クリーンなナレ原稿を書く**（漢字かな混じり。字幕と同一。読みのために壊さない）。
2. **G2Pチェック**：`scripts/jp_yomi_check.py narration.txt --glossary dict-{会社}.csv --out-pls dict-{会社}.pls --report review.md`
   - 推定読みを目視 → 誤読（固有名詞・英字・複数読み漢字）を `dict-{会社}.csv` に正読み追記 → 再実行。
3. **辞書適用で生成**：`dict-common.pls`＋`dict-{会社}.pls` を `create_pronunciation_dictionary` で登録し、
   `generate_speech` の `pronunciation_dictionaries`（辞書名）で参照（詳細は narration-rules.md §3）。
4. 試作1本で読み・抑揚を確認 → OKなら本番。

---

## 5. プラン

| プラン | 月額 | 用途 |
|---|---|---|
| Starter | $5 | Library voice（Konoha等）＋発音辞書。**標準** |
| Creator+ | $22 | 自社メンバーの声を日本語クローン |
| Pro | $99 | Professional Voice Clone |

---

## 6. トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| `402 paid_plan_required` | Free で Library voice | Starter 以上へ |
| 固有名詞・社名の誤読 | 辞書未登録 | glossary CSV に正読み → .pls 再生成 |
| 英字が「ジーアールエー…」 | アルファベット読み | glossary で alias（かな）登録（jp_yomi_check が自動検出） |
| alias でも直らない頑固な箇所 | aliasの限界 | IPA(phoneme)ルールに切替（v3） |
| 抑揚がフラット/暴れる | stability | 0.4〜0.5 に調整 |

詳細：`narration-rules.md`（辞書ルールの作り方）、`scripts/jp_yomi_check.py`。
