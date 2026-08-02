---
name: narration
description: AI音声ナレーション（日本語特化）を作る atomic スキル。ElevenLabs v3 ＋ 日本語ネイティブ声（既定 Konoha）で、原稿を壊さずクリーンな漢字かな混じりのまま、読みの補正は「発音辞書(.pls)」に外出しして生成する。誤読検出は pyopenjtalk（G2P前処理）で機械化し、固有名詞・英字・複数読み漢字の読みを共通辞書＋会社別辞書に蓄積する。「ナレーションを作って」「この原稿を読み上げて」「音声を生成」「ナレ音声」「日本語の読み上げ」「TTSで音声化」など、音声ナレ生成のリクエストで発動する。動画オーケストレータ ai-video-production / vp-corporate-narrated から「ナレ生成パート」として呼ばれるほか、単体（ナレ単発・ポッドキャスト等）でも使える。BGM生成は music、動画は各vpメソッド、字幕焼き込みは subtitle（将来）の担当。
version: 0.1.0
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_speech, submit_speech, check_speech, list_voices, create_pronunciation_dictionary, add_pronunciation_rules, list_pronunciation_dictionaries, get_pronunciation_dictionary]
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
3. **会社別辞書を登録**：`create_pronunciation_dictionary` で登録（`name` は案件名）。以後 id/version はコネクタが管理するので、生成時は辞書名を渡すだけでよい。
   - **BYOK版（自分の鍵）**：`pls_path` にローカルの `.pls` を渡せる。
   - **マネージド版（ゲートウェイ経由）**：ローカルファイルを読めないので **`rules` 配列で渡す**
     （`{string_to_replace, type:"alias", alias}` / `{..., type:"phoneme", phoneme, alphabet:"ipa"}`）。
     `pls_path` を渡すとその旨のエラーが返る。辞書名はテナントごとに名前空間が切られるため、他社の辞書と衝突しない。
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
| **文字数** | v3 は **5,000文字上限**（v2 は10,000、flash_v2.5 は40,000） | 長尺は**シーン単位で分割**する。12シーン構成なら元々1シーンずつなので問題にならないが、一度で流し込まない |
| **分割時の連続性** | 分割すると境目で話速・トーンが飛ぶ | `extra` に **`previous_text` / `next_text`** を渡して前後の文脈を与える |
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
