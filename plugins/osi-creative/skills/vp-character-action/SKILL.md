---
name: vp-character-action
description: AI動画の「キャラ一貫アクション」メソッド。同一キャラ・マスコット・VTuber・商品を、何カット出しても見た目をブレさせずに、躍動感のあるアクション動画にする。中核は3つのプロンプトを自分で書くこと——A:キービジュアル、B:設定シート、C:Seedanceビート列。書いたプロンプトは vp-core の承認ゲートに渡し、承認後に生成する。「このキャラで動画」「マスコットを動かす」「キャラの戦闘/アクション動画」「アニメキャラのPV」「同じキャラを複数カットでブレさせず」などのリクエストで、オーケストレータ ai-video-production から呼ばれる（単独指定も可）。1枚＋カメラムーブだけ・ナレ主体の企業説明は別メソッド（vp-moveboard / vp-corporate-narrated）。
version: 0.1.0
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_image, edit_image, submit_video, check_status]
---

# vp-character-action — キャラ一貫アクション（プロンプト作者）

このメソッドの仕事は **「3つのプロンプトを的確に書く」** こと。生成・承認・連結は `vp-core` に渡す。
PDF（キャラ→設定シート→Seedance）の方法を一般化。AKUMA / ロボット猫ヒーローで実証済み。

## フロー
1. キャラのブリーフ（一言）を受け取る（例「サイバー忍者の悪魔暗殺者」）。
2. 下記 A→B→C の3プロンプトを書き起こす。
3. `vp-core` に渡す → **プロンプト承認ゲート** → 承認後に生成。
4. C は **Seedance 2.0 の一発生成**（躍動感の要）。`vp-core` が検証・納品。

## プロンプト・ジェネレータ（A/B/C）

### A：キャラ・キービジュアル（generate_image / nano-banana-pro / 16:9）
```
[主体の正体：年齢・種族・役割]
[シグネチャ特徴を具体列挙：髪型/マスク/装備/素材/色/小物/ロゴ]
[ポーズ・スタンス]／[カメラ・アングル]／[世界観・背景]
[画風＋レンダ品質]／[ライティング]／[配色パレット5語前後]
no text, no logos, no watermarks
```

### B：設定シート（generate_image / 参照= A のURLを extra.image_urls）
```
Create a 16:9 professional character model sheet using the provided reference image
as the authoritative C1 reference for [キャラ名]. Preserve [顔/マスク/目/髪/装備/武器/
proportions/silhouette]. Do not redesign the character.
SHEET CONTENT: Hero pose / Turnaround(front,3/4,side,back) / Expressions x5 /
 Action poses x3 / Silhouette lineup / Detail callouts / Weapon breakdown(武器時) /
 Color palette swatches.
STYLE: AAA game character model sheet, neutral studio background, precise labeling.
NEGATIVE: no environment, no redesign, no alternate characters, no logos, no watermarks.
```

### C：Seedance ビートタイムライン（submit_video / seedance20-i2v / 起点= A の画像）
```
Preserve the exact character from the input image: [特徴1行]. No redesign.
STYLE: AAA cinematic trailer, Unreal Engine 5, fast-paced action, aggressive camera,
 speed ramps, motion blur, impact frames, heavy VFX, no idle posing, immediate action.
ENVIRONMENT: [場所/天候/象徴物]   ENEMIES: [任意]
0.0s-1.0s: [ショット種別]. [アクション]. [カメラ].
1.0s-4.0s: [ショット]. [アクション]. [カメラ].
4.0s-7.5s: [ショット]. [アクション]. [カメラ].
7.5s-12.0s: [ショット]. [クライマックス]. [決めポーズ]. [カメラpull-back].
```

## 鉄則（実地検証で確定）
- **躍動感＝C を Seedance 2.0 で一発生成**。短尺クリップを継ぎ接ぎすると「もっさり」する。
- **first-last-frame チェーン**（Kling 2.1 `tail_image_url`）は各カットを厳密に構図制御したいとき限定。
  終点ポーズへ等速モーフィングするため**迫力は落ちる**ので、アクション用途では使わない。
- 起点画像は **A のキービジュアル**（B の設定シートを起点にしない）。
- API：Veo の first-last-frame は当社コネクタで422、Kling 2.1 が working。長尺Seedanceは数分。

詳細レシピ・実測は `../ai-video-production/references/character-consistency-pipeline.md` を参照。
生成・承認・連結ループは `vp-core` に委譲する。
