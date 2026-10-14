# キャラ／商品の一貫性パイプライン（キービジュアル → 設定シート → 一発動画）

同一キャラクター・マスコット・VTuber・商品を、**何カット出しても見た目をブレさせず**に
動画化するための再現レシピ。AKUMA（サイバー忍者）作例で実証済み（2026-06）。
アニメでも実写でも物撮りでも同じ手順で通る。

> 適用タイミング：Phase 3.5（画像起点）の一種。「同じ主役が複数カット／長尺に登場する」案件で使う。
> 単発の背景・抽象カットには不要（通常の Phase 3.5 でよい）。

> **このスキルの本当の価値＝下記「3つのプロンプトの型」を、任意のキャラに対して自分で書き起こせること。**
> 特定の呪文をコピーするのではなく、キャラのブリーフ（一言）から A/B/C の3プロンプトを生成するのが仕事。

---

## なぜブレるのか

text-to-video は毎回ゼロから絵を起こすため、同じ指示でも顔立ち・配色・装備が揺れる。
鍵は **「正解の見た目を1枚決め、それを全工程の基準として渡し続ける」** こと。

---

## 手順（PDF 忠実・推奨）

```
A. キービジュアル   generate_image（nano-banana-pro, 4K, 16:9）        ← プロンプトA
       ↓ ①のURLを参照に渡す（extra.image_urls）
B. 設定シート       generate_image（多視点モデルシート）              ← プロンプトB
       ↓
C. 一発動画        submit_video（seedance20-i2v, 起点=キービジュアル） ← プロンプトC（ビート列）
```

### ★躍動感の正体＝C を「Seedance 2.0 の1回生成」でやること
- 動きの勢い・スピードランプ・衝撃フレームは **Seedance 2.0 が1パスで連続生成**するから出る。
- 「たくさんのフレーム」はモデルが一発で作る。**人間が短尺クリップを継ぎ接ぎしない。**
- AKUMA で実証：同じキャラ・同じタイムラインでも、Seedance一発＝かっこいい／継ぎ接ぎ＝もっさり。

### ❌ やりがちな失敗（実地検証で確認）
- **first-last-frame チェーンで“躍動感”を出そうとする**：決めポーズを鎖にして繋ぐと動きは連続するが、
  モデルが終点ポーズに等速で“モーフィング”するため**緩急・衝撃が消えてもっさりする**。
  → first-last-frame は「各カットを厳密に構図制御したいとき限定の上級オプション」。アクションの迫力用途では使わない。
- **5秒クリップ×Nの連結**：各クリップが静止（速度ゼロ）から始まり終点で減速→momentum が途切れる。

---

## 3つのプロンプトの型（プロンプト・ジェネレータ）

キャラのブリーフ（例：「サイバー忍者の悪魔暗殺者」「丸い企業マスコットのロボット猫」）から、
下記の slot を埋めて A→B→C を生成する。これがこのスキルの中核成果物。

### プロンプトA：キャラ・キービジュアル（generate_image / nano-banana-pro / 16:9）
```
[主体の正体：年齢・種族・役割]
[シグネチャ特徴を具体列挙：髪型/マスク/装備/素材/色/小物/ロゴ]
[ポーズ・スタンス]
[カメラ/アングル：extreme low-angle 等]
[世界観・背景：場所/時間/天候/象徴物]
[画風＋レンダ品質：semi-realistic anime + Unreal Engine 5 / Pixar 3D 等]
[ライティング：cinematic rim light / volumetric fog / dramatic shadows]
[配色パレット：色を5語前後]
no text, no logos, no watermarks
```

### プロンプトB：設定シート（generate_image / 参照= A のURLを extra.image_urls）
```
Create a 16:9 professional character model sheet using the provided reference image
as the authoritative C1 reference for [キャラ名]. Preserve the exact
[顔/マスク/目/髪/装備/武器/proportions/silhouette]. Do not redesign the character.

SHEET CONTENT:
 Hero pose（全身・決めポーズ）
 Turnaround（front, 3/4, side, back）
 Expressions x5（[5種：neutral, focused, ... など]）
 Action poses x3（[3種：blade draw, dash, ... など]）
 Silhouette lineup
 Detail callouts（[マスク/目/髪/腕/装甲/武器]）
 Weapon breakdown（武器の正投影＋エネルギー状態）  ← 武器がある場合
 Color palette swatches（[5色]）

STYLE: AAA game character model sheet, clean production design board,
 neutral studio background, organized layout, precise labeling, production-ready.

NEGATIVE: no environment scene, no redesigns, no alternate costumes,
 no extra characters, no logos, no watermarks. Focus entirely on the model-sheet.
```

### プロンプトC：Seedance ビートタイムライン（submit_video / seedance20-i2v / 起点= A の画像）
```
Preserve the exact character from the input image: [特徴を1行で]. No redesign.
STYLE: AAA game cinematic trailer, Unreal Engine 5 quality, fast-paced action
 choreography, aggressive camera, speed ramps, motion blur, impact frames,
 heavy VFX, no idle posing, immediate action.
ENVIRONMENT: [場所/天候/象徴物]
ENEMIES: [任意。群がる敵など]

0.0s-1.0s: [ショット種別（extreme close-up等）]. [アクション]. [カメラ（whip-pan等）].
1.0s-4.0s: [ショット]. [アクション]. [カメラ].
4.0s-7.5s: [ショット]. [アクション]. [カメラ].
7.5s-12.0s: [ショット]. [クライマックス/必殺]. [最後の決めポーズ]. [カメラpull-back].
```
- `duration_seconds: 12`, `extra: {"duration":"auto"}`。10秒超＋激しい動きは**完了まで数分**、非同期（submit→check_status）で。
- 起点画像＝A のキービジュアル（**B の設定シートを起点にしない**：i2v は入力が1フレーム目になる #17）。

---

## 連番カットで見た目をそろえる手順（設定シート → 固定文 → 起点画像の清書 → 部分修正）

ナレ付き・物語・動画名刺など、**1カット1動作の i2v を何本も並べる**案件の手順。プロンプトB（設定シート）の軽量版と、
その後の「起点画像の清書」「部分修正」までを1本の流れにする。アクションの一発生成（プロンプトC）とは別の使い方。

```
① キービジュアル（全身・正面寄り・無地背景）   人が見て OK した1枚を正本にする
② 設定シート      正面・斜め・横・後ろ ＋ 表情3（笑顔・驚き・困り顔）＋ 手に持つ物
③ 見た目の固定文  英語1文に固定し、以後すべての画像・動画プロンプトに同じ文言で入れる
④ 起点画像の清書  設定シート＋構図ラフを参照に、カットごとの起点画像を高解像度で描き直す
⑤ 部分修正        崩れやすい小物・残った文字は、描き直さず edit_image で「消す・置き換える」だけ
```

### ② 設定シート（キャラごとに1回だけ作り、使い回す）
プロンプトBの「Turnaround＋Expressions」を最小構成にしたもの。アクション用の武器分解・シルエット一覧は要らない。
```
Character reference sheet of the SAME character as the reference image:
front, three-quarter, side and back views, plus three expressions (smile, surprised, troubled),
and the one object the character holds. Same outfit, colors and proportions.
Plain light background, no text, no labels.
```
- `generate_image`（`nano-banana-pro` 推奨）の `extra.image_urls` に①を渡す。横長（16:9）で作る。
- **設定シートは参照用。動画の起点にしない**（i2v は入力が1フレーム目になる #17）。

### ③ 見た目の固定文
- 例：`wavy dark-brown hair, round face, rosy cheeks, grey blazer over white T-shirt, grey trousers`
- 画像・動画のどのプロンプトにも**一字一句同じ文言**で入れる。言い換えると別人になりやすい。
- 世界観設計書の**画風の固定文（style_lock）**を先頭に、見た目の固定文をその次に置く（`prompt-quality-rubric.md` の i2v 節の型）。
- 作品のブリーフかブランドキット（`brandkit.md`）に書いて残し、次の動画でも使い回す。

### ④ 起点画像の清書（承認後・カットごと）
- 構図のラフ（コンテ段階の安い画像）は確認用。本番の起点は、**設定シート（1枚目）＋ラフ（2枚目）を参照**に描き直す。
  ```
  <style_lock>. Recreate the composition of the second reference image with the character exactly as
  in the first reference sheet. <見た目の固定文>. <場面>. No text, no speech bubbles, no logos.
  ```
- 縦型なら起点も 9:16 で作る（動画モデルの多くは起点画像の比率に従う）。
- ラフに描いてあった文字・吹き出し・ボタンの位置取りは、**起点画像では消す**（文字は仕上げで載せる）。

### ⑤ 部分修正（消す・置き換えるだけ）
- 小物の差し替え・仮置きの削除は `edit_image` で行う。**画風を変える指示は崩れの元**なので書かない。
  ```
  Remove the sickle: his right hand is empty, raised and waving (open palm, five fingers).
  Keep everything else exactly the same.
  ```
- 直した絵は元の絵と並べて目で確認し、元の絵は別名で残す。直し方の全体は `fix-ladder.md`（4段目）。

---

## モデル・API の実地知見（2026-06）

- **動画は Seedance 2.0（`seedance20-i2v`）が躍動感の要**。Kling は滑らかだが迫力では劣る。
- **first-last-frame（始点・終点指定）**：Veo の `fal-ai/veo3.1/.../first-last-frame-to-video` は当社コネクタで
  **422（Unprocessable）**。**Kling 2.1（`fal-ai/kling-video/v2.1/pro/image-to-video` + `extra.tail_image_url`）が working**。
  ただし前述のとおり躍動感が落ちるので、用途を選ぶ。
- **塩漬けキュー注意**：クレジット切れ中に submit したジョブは、後で課金しても自動再開せず、
  **並列枠（concurrency）を占有**して以後の submit が `Forbidden` になる。fal ダッシュボード（Settings →
  Concurrency Limits）で 0/N を確認、滞留は Cancel するか自動タイムアウトを待つ。
- キャラ一貫性を最優先するなら `nano-banana-pro`（人物参照5枚＋スタイル参照3枚）。
  コスト優先なら `nano-banana-2`（人物参照4枚・約半額）でも足りることが多い。
- 参照を多く渡すと稀に MCP タイムアウト → 枚数を減らすか再試行。

---

## チェックリスト

- [ ] ブリーフから A/B/C の3プロンプトを自分で書き起こしたか
- [ ] A：特徴を具体列挙して1枚で決め切ったか
- [ ] B：A を `image_urls` 参照に渡し「No redesign」を明記したか
- [ ] C：起点は A のキービジュアル（B のシートではない）か／ビート列で時間設計したか
- [ ] C は Seedance 2.0 の一発生成か（迫力用途で first-last-frame チェーンを使っていないか）
- [ ] 非同期（submit→check_status）で、長尺は数分待ちを見込んだか
- [ ] （連番カット）見た目の固定文が、全カットのプロンプトに同じ文言で入っている
- [ ] （連番カット）起点画像に文字・吹き出し・ロゴが無く、手に持つ物が形の単純なもの
