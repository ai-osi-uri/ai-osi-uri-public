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

### STEP 2. 生成（承認後のみ）
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
- ❌ 一気に全カット生成しない（試作を挟む）
- ✅ 迫力アクションは「Seedance 2.0 の一発生成」。first-last-frame チェーンは精密制御用（躍動感は落ちる）
