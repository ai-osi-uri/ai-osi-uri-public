---
name: narration
description: AI音声ナレーション（日本語特化）を作る atomic スキル。ElevenLabs v3 ＋ 日本語ネイティブ声（既定 Konoha）で、原稿を壊さずクリーンな漢字かな混じりのまま、読みの補正は「発音辞書(.pls)」に外出しして生成する。誤読検出は pyopenjtalk（G2P前処理）で機械化し、固有名詞・英字・複数読み漢字の読みを共通辞書＋会社別辞書に蓄積する。「ナレーションを作って」「この原稿を読み上げて」「音声を生成」「ナレ音声」「日本語の読み上げ」「TTSで音声化」など、音声ナレ生成のリクエストで発動する。動画オーケストレータ ai-video-production / vp-corporate-narrated から「ナレ生成パート」として呼ばれるほか、単体（ナレ単発・ポッドキャスト等）でも使える。BGM生成は music、動画は各vpメソッド、字幕焼き込みは subtitle（将来）の担当。
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_speech, submit_speech, check_speech, list_voices, create_pronunciation_dictionary, add_pronunciation_rules, list_pronunciation_dictionaries, get_pronunciation_dictionary]
# スキルの一覧（つないだときに Claude に渡す）に出す短い用途
label: ナレーション音声
---

# narration — 日本語音声ナレーション（クリーンテキスト＋発音辞書）

ElevenLabs v3 ＋ 日本語ネイティブ声で、**原稿を壊さず**に自然な日本語ナレを作る atomic スキル。
旧方式（原稿の字面を二重母音化・ひらがな化する力技）を廃し、**読みは発音辞書に外出し**する。

## 役割
- 入力：クリーンなナレ原稿（漢字かな混じり。感情タグ `[calm]` 等は行頭OK）。
- 出力：ナレ音声（mp3）。字幕とナレは同一テキストで運用できる。
- 動画制作からは「ナレ生成パート」として呼ばれる。単体でも動く。

## 前提（初回設定・一度だけ）
`references/INITIAL_SETUP.md` 参照。要点は3つ：
1. ElevenLabs プラン Starter 以上（Creator 推奨）
2. 日本語ネイティブ声を追加 → voice_id（既定 **Konoha = `T7yYq3WpB94yAuOXraRi`**）
3. 共通辞書 **osi-common** 登録 → id/version（`UWU1mPUOcLYUFl5Ene4k` / `gmMrErDfxMMUPgYJ5iuZ`）

## フロー
1. **クリーンなナレ原稿**を用意（壊さない。字幕と同一）。
2. **読みチェック＆辞書生成**：
   `python3 scripts/jp_yomi_check.py narration.txt --glossary dict-{会社}.csv --out-pls dict-{会社}.pls --report review.md`
   → `review.md` の要レビュー（固有名詞・英字）を消し込み、誤読は CSV に正読み追記 → 再実行。
3. **会社別辞書を登録**：`create_pronunciation_dictionary(name, pls_path)` で登録（`name` は案件名）。
   以後 id/version はコネクタが管理するので、生成時は辞書名を渡すだけでよい。
   `.pls` を作らずに直接渡したいときは `rules` 配列でもよい
   （`{string_to_replace, type:"alias", alias}` / `{..., type:"phoneme", phoneme, alphabet:"ipa"}`）。
4. **生成**：`generate_speech`
   ```jsonc
   generate_speech({
     text: "[calm] OKWEBは、…",          // クリーンテキスト
     voice: "T7yYq3WpB94yAuOXraRi",       // 既定 Konoha
     model: "elevenlabs-v3",
     stability: 0.45,
     pronunciation_dictionaries: ["osi-common", "<会社辞書名>"] // 第一級・名前指定→コネクタが最新版を自動解決（最大3件）
   })
   ```
   試作1本で読み・抑揚を確認 → 本番。

## 動画のナレ：通し1回で生成して、実測で尺を決める

動画に乗せるナレは、**行ごと・カットごとに別々に作らない**。リクエストを分けると声色・話速・温度がばらつき、
並べたときに「別の日に録った声」に聞こえる。次の順で作る。

1. **原稿は1秒5〜6字**で書く（3秒のカットなら15〜18字）。速度を上げて詰め込まない（詰まって聞こえる）。足りなければ原稿を削る。
2. **読みの事前チェック**（フローの手順2）を先に済ませる。通しで1回生成するので、1か所読み間違えると全部作り直しになる。ここで拾うのが一番安い。
3. **通しで1回生成**：全行を改行でつないで `generate_speech` に1回で渡す（v3 の上限 5,000字に収まる尺＝短尺〜3分程度なら1回で足りる）。
   - **感情タグは冒頭の1つだけ**（例 `[calm]`）。行の途中にタグを入れない（字幕と原稿が食い違い、尺の計算もずれる）。
     12シーンの企業動画のようにシーンごとに温度を変えたいとき（`templates/voice-strategy.md` §3）も、通し生成のまま**シーンの頭にだけ**タグを置く（字幕の原稿からはタグを外す）。
   - 間は句読点と改行で作る（v3 は `<break>` 非対応）。
   - 5,000字を超える長尺だけ、章の切れ目（シーン単位）で分ける。分けた境目の温度差は、感情タグと文の切り方でそろえる（下の「Eleven v3 の制約」）。
4. **実測で尺を先に決める**：通しで聞いて合格したら、`ffprobe` で全体の長さを測り、行ごとの区間を出して、**カットの尺はそこから決める**（ナレより先にカット尺を決めない。pitfalls #26）。
   - 各カットの尺 ＝ その行の区間 ＋ 頭の間 0.35秒 ＋ 尻の間 0.25秒（ブランドムービーは `vp-brand-film` の決め方）。
   - 行ごとの区間は、`generate_speech` に `with_timestamps: true` を付けて取る（行は空行で区切って渡す）。PC 版の Creative は文字ごとの時刻を `<name>-align.json` に保存し、行ごとの開始・終了秒を返す。URL 版は単語ごとの時刻までなので、行の区切りは単語の時刻から読み取る。
   - 時刻が取れないとき（`submit_speech` の長尺など）は、無音検出で代用する（`../music/scripts/duck_expr.py --from-audio narration.mp3 --show-windows`。行と行の間に 0.3秒以上の無音があれば1行＝1区間になる）。区間の数が行数と合わないときは、聞いて手で直す。
5. **聞いて確認**：読み間違い・不自然な間・詰まりがあれば、辞書か原稿を直して**全体を作り直す**（部分の差し替えはしない。声色が変わる）。

> **時刻の取れ方は経路で違う。** PC 版の Creative（2.5.0〜）は ElevenLabs の with-timestamps で文字ごとの時刻を返す。
> URL 版（マネージド）は fal 経由のため単語ごとの時刻まで。どちらも `with_timestamps: true` を付けたときだけ返る（課金は通常と同じ）。

### 話す人が2人以上（ナレーターとキャラが交互に話す）
全部を1つの声で読ませると、キャラのセリフがナレーションに埋もれて「セリフが消えた」ように聞こえる。

1. **話す人ごとに声を決め**、カットが変わっても同じ人は同じ声にする。声の性質（高さ・年齢・温度）がナレーターと離れている方が聞き分けやすい。
2. **話す人ごとに1回で生成する**：同じ人のセリフを全部まとめて1リクエストにする（ナレーター1回・キャラ1回）。カットをまたいでも声色がそろう。感情タグは話す人ごとに冒頭の1つ。
3. 話す人ごとの音声を無音検出で行に切り分け、台本の順に並べ直す。
4. **`pause_before`**（そのセリフの前に置く間・秒）をカット表に持たせる。キャラが画面に現れてから話させたいときに使い、並べるときに `adelay` でその分だけ後ろにずらす。カットの開始もその分だけ前に取る。
5. 字幕でも誰が話しているか分かるように、キャラのセリフは「キャラ名「…」」のように書く。
6. 読みの補正（発音辞書）は話す人に関係なく共通で効かせる（声によって読み間違える語が違うので、話す人ごとに読みチェックの結果を聞いて確かめる）。

## 正本テンプレ（必ず参照）
- `templates/voice-strategy.md` … 声選択・モデル・感情タグ・全体方針
- `templates/narration-rules.md` … 発音辞書ルールの作り方（alias / IPA）
- `templates/dict-common.pls` … 共通辞書の元データ
- `templates/dict-company.sample.csv` … 会社別 正読み辞書テンプレ
- `scripts/jp_yomi_check.py` … G2P読みチェック＆.pls自動生成（pyopenjtalk）
- `references/INITIAL_SETUP.md` … 初回設定

## Eleven v3 の制約（必ず守る）

公式仕様。知らずに踏むと途中で切れたり、指示が無視されたりする。

| 項目 | 制約 | 対処 |
|---|---|---|
| **文字数** | v3 は **5,000文字上限**（v2 は10,000、flash_v2.5 は40,000） | 5,000字以内なら**通しで1回**（声色がそろう）。超える長尺だけ**章・シーン単位で分割**する |
| **分割時の連続性** | 分割すると境目で話速・トーンが飛ぶ | v2 系は `extra` に **`previous_text` / `next_text`** を渡す。**v3 はこの2つを受け付けず 400 になる**（2026-10 確認）ので、感情タグと文の切り方でそろえる |
| **ポーズ** | **v3 は `<break>` タグ非対応**（v2 系のみ有効） | 間は「…」やダッシュ、文の切り方で作る |
| **speed** | **0.7〜1.2** の範囲のみ | 尺調整をここだけに頼らない。足りない分は台本を削る |
| **phoneme ルール** | 効くのは **`eleven_v3` と `eleven_flash_v2` のみ**。他モデルは無視されデフォルト発音になる | 日本語の固有名詞を IPA で固定したいなら v3 一択。`alias` は全モデルで有効 |
| **辞書の同時適用** | **最大3件** | 共通辞書＋会社別辞書＋案件辞書、が上限 |
| **声の相性** | タグの効きは声の学習素材に依存。PVC は v3 に最適化されていない | Library voice / IVC を使う |

> `stability` は 0.0〜1.0 の連続値（既定 0.5）。ナレは 0.4〜0.5 が扱いやすい。
> UI 上は Creative / Natural / Robust の3プリセットとして提示されるが、API は連続値を受け取る。

## 鉄則
- ❌ ナレ原稿の字面を壊す（二重母音化・ひらがな化・々ハック）＝旧方式は使わない。
- ✅ クリーンテキスト＋発音辞書。誤読は jp_yomi_check で検出し辞書に蓄積（共通＋会社別）。
- ✅ 声は日本語ネイティブ（既定 Konoha）。英語ベース声は使わない。
- ✅ alias で直らない頑固な固有名詞（例: 河野→こうの 等）は IPA(phoneme)ルールに切替（v3対応）。

## 連携
- 動画：`ai-video-production` / `vp-corporate-narrated` から本スキルを「ナレ生成」として呼ぶ。
- BGM：`music`（generate_music）。字幕焼き込み：`subtitle`（将来）。画像：`image`（将来）。
