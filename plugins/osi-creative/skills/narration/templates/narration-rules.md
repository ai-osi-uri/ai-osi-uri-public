# ナレーション（TTS）読み制御ルール v2 — 発音辞書方式（案B）

**ElevenLabs v3（日本語ネイティブ声）で、原稿を壊さずに読みを正す方法。**

旧 v1 は「字面を壊す力技」（デエタ／ヨンセン ハッピャク／々（ふりがな））だった。
v2 は **クリーンテキスト＋発音辞書(.pls)** で読みを外出しし、誤読検出を pyopenjtalk で機械化する。

> 📚 先に `voice-strategy.md`（声・モデル・全体フロー）を読むこと。

---

## 0. 大原則

✅ **ナレ原稿は壊さない**（漢字かな混じりのまま＝字幕と同一テキスト）。
✅ 読みの補正は **辞書(.pls)** に書く（共通 `dict-common.pls` ＋ 会社別 `dict-{会社}.pls`）。
✅ 誤読検出は **`scripts/jp_yomi_check.py`（pyopenjtalk）** で自動化。手作業ハックは廃止。
❌ 原稿のひらがな化・二重母音化・`々（ふりがな）`は **使わない**（旧方式・参考のみ §5）。

---

## 1. 手順（毎回これ）

1. クリーンなナレ原稿 `narration.txt` を書く（感情タグ `[calm]` は行頭OK）。
2. 読みチェック＆辞書生成：
   ```bash
   python3 scripts/jp_yomi_check.py narration.txt \
       --glossary dict-company.csv \
       --out-pls  dict-company.pls \
       --report   review.md
   ```
3. `review.md` を確認。**§要レビュー（固有名詞・英字）** と **推定読み行** を目視し、
   誤読は `dict-company.csv` に `表記,正しい読み` を追記 → 2 を再実行。
4. `dict-common.pls`＋`dict-company.pls` を ElevenLabs に登録し、生成時に参照（§3）。

---

## 2. 辞書ルールの種類

| 種類 | いつ | 例 |
|---|---|---|
| **alias（別読み・かな）** | 基本これ。固有名詞・英字・複数読み漢字 | `河野 → かわの`、`OKWEB → おーけーうぇぶ` |
| **phoneme（IPA）** | alias で直らない頑固な箇所のみ（v3対応） | アクセント位置まで固定したい固有名詞 |

`dict-company.csv` の書式：`surface,yomi[,ipa]`（ipa列があればphoneme優先）。

### よくある誤読パターン（jp_yomi_check が自動で拾う）
- **英字 → アルファベット読み**：`OKWEB→オーケーダブリューイービー`、`GRATICA→ジーアールエー…` ⇒ alias（かな）
- **固有名詞の独自読み**：`河野→コウノ`（正：かわの）、社名・人名・製品名 ⇒ glossaryで確定
- **複数読み漢字**：`最大級`、`蓄え`、`見える化` 等 ⇒ 推定読み行で目視、必要なら alias
- **桁の大きい数字**：`4,800万件` ⇒ 通常はv3が読むが、崩れる場合のみ alias（よんせんはっぴゃくまんけん）

---

## 3. 発音辞書を生成に適用する（コネクタ連携）

ElevenLabs では辞書を**先に作成**し、生成時に**参照**する。
本コネクタ（AI OSI URI Creative v1.2.0+）は辞書を**第一級パラメータ**で受けるので、
辞書名を渡すだけでよい（コネクタが最新版を自動解決。最大3件）：

```jsonc
generate_speech({
  text: "[calm] OKWEBは、27年にわたり…",   // ← 壊さないクリーンテキスト
  voice: "Konoha",                          // 日本語ネイティブ既定（要・アカウント追加）
  model: "elevenlabs-v3",
  stability: 0.45,
  pronunciation_dictionaries: ["osi-common", "<会社辞書名>"]   // 名前指定→最新版を自動解決（最大3件）
})
```

**辞書の作成**：コネクタの `create_pronunciation_dictionary(name, pls_path)` で `.pls` を登録する
（`name` は識別名＝案件名。同名は upsert）。id/version はコネクタが管理するので、以後は**名前で参照**できる。
（旧来の `extra.pronunciation_dictionary_locators` での id/version 手渡しも後方互換で動くが、新規は名前指定を使う。）

---

## 4. チェックリスト（生成前）

- [ ] 原稿はクリーン（壊していない・字幕と同一）か
- [ ] `jp_yomi_check.py` を通したか／`review.md` の要レビューを消し込んだか
- [ ] 固有名詞・社名・人名・製品名を `dict-company.csv` に登録したか
- [ ] `dict-common.pls`＋会社辞書を生成に適用（`pronunciation_dictionaries` に辞書名指定）したか
- [ ] 声は日本語ネイティブ（既定 Konoha、アカウント追加済み）か
- [ ] 試作1本で読み・抑揚を確認したか

---

## 5. 付録：旧 v1 ハック（原則禁止・歴史的参考）

旧方式は原稿の字面を壊して読みを矯正していた（デエタ／エエアイ／ヨンセン ハッピャク／`々（じねん）`）。
**v2 では使わない。** これらの知見は `dict-common.pls` の alias 規則に移植済み。
もし辞書方式が使えない緊急時のフォールバックとしてのみ参照する。
