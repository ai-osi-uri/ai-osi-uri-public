---
name: vp-core
description: AI動画制作の「共通インナー」atomicスキル。どの動画タイプのメソッド（vp-character-action / vp-moveboard / vp-corporate-narrated 等）からも呼ばれる、承認ゲート付きの生成ループを標準化する。役割は「①メソッドが書いたプロンプトを提示して承認/修正をもらう → ②承認後に AI OSI URI Creative コネクタで生成（generate_image / submit_video→check_status）→ ③1フレーム目・繋ぎ目を検証 → ④必要なら ffmpeg で連結 → ⑤納品」。プロンプトそのものを承認対象にするのが肝。単独では発動せず、上位メソッド／オーケストレータ ai-video-production から呼ばれる前提。動画タイプ判定や台本設計、プロンプト起草そのものは各メソッドの責任で、本スキルは行わない。
version: 0.1.0
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_image, edit_image, image_to_video, submit_video, reference_to_video, check_status, generate_speech, generate_music]
---

# vp-core — 動画制作の共通インナー（承認ゲート付き生成ループ）

どの動画タイプのメソッドからも呼ばれる「芯」。メソッドは**何を作るか**（プロンプト）を決め、
本スキルは**どう承認して生成・検証・連結するか**を標準化する。

> 単独発動しない。`ai-video-production`（ディスパッチャ）が選んだメソッドから呼ばれる。
> プロンプトの起草・動画タイプ判定は各メソッドの責任。本スキルは生成ループだけを担う。

## 入力（メソッドから受け取る）
- `prompts`: 起草済みプロンプト一式（例 A:キービジュアル / B:設定シート / C:動画ビート列）。
- `plan`: 生成計画（使用モデル・尺・アスペクト比・枚数・連結要否）。
- `assets`: 既存の参照画像URL等（あれば）。

## ループ（必ずこの順）

### STEP 1. プロンプト承認ゲート（★最重要・本スキルの肝）
- **提示前に自己採点（必須）**：`../ai-video-production/references/prompt-quality-rubric.md` でプロンプトを採点する。
  MUST が1つでも ❌ なら**提示せずメソッドに直させて再採点**（proposal-self-review の動画版＝自分が最も厳しいレビュアーになって叩いてから出す）。
- 合格したら、メソッドが書いた **プロンプトをそのままユーザーに提示**し（「自己採点で確認した点」を一文添えて）、承認 or 修正をもらう。
- 「試作動画を見て直す」より前に、**まず文章（プロンプト）の段階で合意**する（生成コストを使う前に方向を固める）。
- 修正要望があればメソッドにプロンプトを直させ、再提示。承認が出るまで生成しない。

### STEP 2. 生成（承認後のみ）— **ドラフト → 本番の2段構え**

承認されたプロンプトを、いきなり本番モデルで焼かない。**まず `h3max` で全カットの当たりを取る。**

**2a. ドラフト（`h3max` / `h3max-i2v`・480P）**
- 5秒クリップが**3秒未満**で返る。全カット分を投げても待ち時間が実質ない。
- 単価 $0.0125/s（480P）なので、12カット×5秒でも **$0.75**。**外して捨てる前提で回す。**
- ここで見るのは「構図・被写体・動きの方向が意図通りか」だけ。**画質は見ない**（768P 上限で本番には使わない）。
- 外したカットはプロンプトを直して投げ直す。**ここで直すのが一番安い。**
- ユーザーにドラフトを見せ、**どのカットを本番に上げるか合意してから 2b に進む**。

**2b. 本番（合意したカットだけ）**
- ドラフトで通ったプロンプトを、`model-comparison.md` の使い分け表どおりの本番モデルへ。
- **ドラフトが通ったからといって本番でも同じ絵が出るとは限らない**（モデルが違う）。構図の当たりが取れているだけ、と理解して STEP 3 の検証は省かない。

> **この2段を飛ばしてよい場合**：カットが1〜2本しかない、または `h3max` に無いモード
> （reference-to-video＝キャラ一貫・ムーブボード）が必須のとき。その場合は 2b から始め、
> 理由を一言ユーザーに伝える。
>
> ⚠️ **H3 Max の $0.0125/$0.02 は 2026-09-07 までの promo。** 以降 $0.05/$0.08 に戻る（4倍）。
> 顧客見積は promo 後の価格で作る。

- 画像：`generate_image`（nano-banana-2, 4K, 16:9）。一貫性参照は `extra.image_urls`。
- 動画：**必ず非同期** `submit_video` → `check_status`（ブロッキング generate_video は使わない／タイムアウト #4）。
  - 並列は5本まで（6本以上で Forbidden #1）。塩漬けキュー（課金前ジョブが枠占有）に注意（fal Concurrency 0/N 確認）。クレジット切れ時はキューに入るが進まない→課金後に再投入。
  - **入力モードはメソッドが `plan` で指定する**。2系統あるので取り違えない：
    - **i2v（first-frame）**：`seedance20-i2v` 等。渡した画像が**1フレーム目**になる。キービジュアルを起点にする用途（例 vp-character-action）。**線や設定シート入りの画像を起点にしない**＝そのまま冒頭に映る（#17）。
    - **reference-to-video（参照）**：`bytedance/seedance-2.0/reference-to-video`。渡した画像は**参照(指示)**で1フレーム目にならない。**ルート/番号/ラベル入りのムーブボードを渡す用途（vp-moveboard）**。赤線は出力に出ない＝頭トリック不要（#17の根本解決）。
- コスト見込みを生成前に提示する。

### STEP 3. 検証
- 画像/動画を取得し、内容を確認（数フレーム抽出）。
- i2v：1フレーム目が意図通りか。reference-to-video：**赤線/番号が出力に出ていないか**＋経路に沿っているか。
- 連結前提なら各区間の**繋ぎ目フレーム**が一致するか。大きな動き（フル360°等）が回りきらない/カットは #18。

### STEP 4. 連結・仕上げ（必要時）
- ffmpeg は **必ず /tmp で作業 → cp で配置**（Drive直書きは破損 #9）。長尺処理は nohup+ポーリング #10。
- 連結は `setsar=1,fps=24,scale=...,pad=...` で正規化してから concat。

### STEP 5. 納品
- 成果物を提示。累計コストを表示。

## 共通参照（オーケストレータ ai-video-production 配下の正本を参照）
- `../ai-video-production/references/prompt-quality-rubric.md` … ★提示前の自己採点ゲート（STEP 1で必須）
- `../ai-video-production/references/model-comparison.md` … モデル使い分け・単価
- `../ai-video-production/references/pitfalls.md` … 落とし穴（#1〜、Forbidden/塩漬け/ffmpeg/#17 i2v1フレーム目/#18 モーション予算）
- `../ai-video-production/references/character-consistency-pipeline.md` … 一貫性とプロンプト型（vp-character-action用）
- `../ai-video-production/references/moveboard.md` … 線駆動カメラムーブ＋reference-to-video（vp-moveboard用）

## 原則
- ❌ 承認前に生成しない（プロンプトゲートを飛ばさない）
- ❌ 一気に全カット**本番で**生成しない（`h3max` のドラフトを挟む／STEP 2a）
- ✅ 高い方で1回試すより、**安い方で20回試して19本捨てる**。生成が速くなった分の価値はそこにある
- ⚠️ ドラフトが速いぶん、**人が見る時間がボトルネックになる**。12本を投げるのは1分でも、見るのは数分かかる。投げる本数を増やす前に、何を見て合否を決めるかを先に決める
- ✅ 迫力アクションは「Seedance 2.0 の一発生成」。first-last-frame チェーンは精密制御用（躍動感は落ちる）
