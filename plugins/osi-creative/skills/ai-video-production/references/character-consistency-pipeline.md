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
