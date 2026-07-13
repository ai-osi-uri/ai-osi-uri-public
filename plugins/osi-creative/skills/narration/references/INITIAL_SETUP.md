# OSI Creative 初回設定（音声ナレ：ElevenLabs 発音辞書方式）

案Bの音声ナレを使う前に、**ElevenLabs 側で一度だけ**必要な設定。OSI Creative の導入手順に記載する。
（コネクタの `ELEVENLABS_API_KEY` 設定は既存の前提。ここはその上に乗る「日本語ナレ用の初期化」）

---

## 必須（初回 1 回・ワークスペース単位）

### 1. プランを Starter 以上にする
- Library voice（Konoha 等）と発音辞書の **API 利用に Starter+ が必須**。
- Free（残高 $0）のままだと生成時に `402 paid_plan_required`。

### 2. 日本語ネイティブ声を 1 つ追加 → voice_id を控える
- 既定：**Konoha（Professional JP Explainer・関東・女性プレミアム）**
- 確定済み voice_id：**`T7yYq3WpB94yAuOXraRi`**
- 別案：Kyoko / Hideki（同手順で voice_id を控える）

### 3. 共通発音辞書 `osi-common` を登録 → id/version を控える
- 全案件で効く共通の読み（AI・ISO・SaaS・見える化・最大級・蓄え 等）をまとめたベース辞書。
- 登録済み（今回作成）：
  - **dictionary_id：`UWU1mPUOcLYUFl5Ene4k`**
  - **version_id：`gmMrErDfxMMUPgYJ5iuZ`**
- 元データ：`templates/dict-common.pls`。ルール追加時は version_id が変わるので最新を控える。

> この3つが「ElevenLabs（11）側の初回設定」。OSI Creative の設定ファイル（例：`config/voice-settings.md`）に
> **既定 voice_id と osi-common の id/version を保存**しておくと、各スキルはそれを参照するだけでよい。

---

## 案件ごと（初回設定ではない・都度）

- `dict-{会社}` を案件単位で作成。id/version はコネクタが管理するので、生成時は辞書名で参照する。
  - 例（今回のテスト）：okweb … id `L8jIW8CpHyulmvaaaokC` / ver `JOEvvB7nOrgqMebKVeob`（参考。通常は名前指定でよい）
- 手順：`jp_yomi_check.py` で原稿チェック → 正読みを CSV 追記 → コネクタの `create_pronunciation_dictionary(name, pls_path)` で登録（同名は upsert）。

---

## 生成時の指定（参考）

```jsonc
generate_speech({
  text: "<クリーンなナレ原稿>",
  voice: "T7yYq3WpB94yAuOXraRi",        // 既定 Konoha
  model: "elevenlabs-v3",
  stability: 0.45,
  pronunciation_dictionaries: ["osi-common", "<会社辞書名>"]   // 第一級・名前指定→コネクタが最新版を自動解決（最大3件）
})
```

---

## 記載先の提案
- **OSI Creative の README / セットアップ節**に「音声ナレ初回設定」として上記 1〜3 を明記。
- 機微でない id/version は `config/voice-settings.md` に保存（voice_id・osi-common の id/version）。
- コネクタ（AI OSI URI Creative v1.2.0）で 3 の辞書登録（`create_pronunciation_dictionary`）と
  id/version 管理はコネクタ側に寄せ済み。生成時は辞書名を `pronunciation_dictionaries` に渡すだけ。
  初回設定は実質「プラン＋声の追加」に簡素化されている。
