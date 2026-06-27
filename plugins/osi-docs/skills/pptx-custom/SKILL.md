---
name: pptx-custom
description: "AI OSI URI の社内体裁（ブランド配色・レイアウト規約）で .pptx を描画/整形する**描画エンジン**スキル。構成（どのスライドが何を言い、どう並ぶか）は deck-composition が決めた slide-plan.md を受け取る前提で、本スキルはそれをレイアウト・配色・図形・画像として綺麗に刷ることに専念する。社内テンプレで提案資料やピッチを刷る、既存 pptx を社内体裁に整える、business-plan-builder / architecture-proposal / proposal 系のオーケストレータから「pptx に刷る部品」として呼ばれる、といった場合に発動する。体裁不問の汎用的な .pptx の読み取り・抽出・変換は基盤 `pptx` スキルの担当。※ スライドの構成・順序・タイトルの言い切り（Action title）・章立ては deck-composition の責任で、本スキルは行わない。"
license: Proprietary. LICENSE.txt has complete terms
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_image]

---

# PPTX Skill（描画エンジン）

このスキルは **「刷る」層**。何を言うか・どう並べるかは前工程で決まっている前提で、見た目を作る。

```
storyline-gate → deck-composition → ★pptx-custom（ここ）
  考える            構成する            刷る
```

**構成は受け取る。** 新規デッキを作るときは、まず deck-composition が出した `slide-plan.md`（スライド順・各 Action title・1メッセージ・載せる証拠）を入力にする。`slide-plan.md` が無いまま「どのスライドを何枚、どの順で」を本スキルで決め始めない——それは deck-composition の仕事。本スキルは各スライドを綺麗に刷り、構成の良し悪しは判断しない。

> 既存 pptx の整形・体裁直しなど、構成が既に存在する作業では deck-composition を経由しなくてよい（入力＝既存の .pptx）。

## Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `python -m markitdown presentation.pptx` |
| Edit or create from template | Read [editing.md](editing.md) |
| Create from scratch (JS) | Read [pptxgenjs.md](pptxgenjs.md) |
| Create from scratch (Python) | Read [python-pptx.md](python-pptx.md) |
| 構成の原則・コード（前工程） | deck-composition スキル ＋ [exec-deck-patterns.md](exec-deck-patterns.md) / [exec-deck-code.md](exec-deck-code.md) |

**Which creation tool?** Try pptxgenjs first (`npm install -g pptxgenjs`). If npm fails (403/network), fall back to python-pptx (`pip install python-pptx`). Both produce valid .pptx; the guides contain equivalent design patterns.

---

## Reading Content

```bash
# Text extraction (.pptx only — for .docx use pandoc, see the docx skill)
python -m markitdown presentation.pptx

# Visual overview
python scripts/thumbnail.py presentation.pptx

# Raw XML
python scripts/office/unpack.py presentation.pptx unpacked/
```

---

## Editing Workflow

**Read [editing.md](editing.md) for full details.**

1. Analyze template with `thumbnail.py`
2. Unpack → manipulate slides → edit content → clean → pack

---

## Creating from Scratch

新規作成は **slide-plan.md（deck-composition の出力）を入力にする**。各スライドの Action title・1メッセージ・載せる証拠は plan に書かれている。本スキルはそれを下記のレイアウト機構で刷る。実装の詳細は [pptxgenjs.md](pptxgenjs.md) または [python-pptx.md](python-pptx.md)。

> 章扉・目次・パンくず等のナビ部品が必要かは slide-plan.md に記載がある。実装ヘルパーは [exec-deck-code.md](exec-deck-code.md)（`addSectionHeader` / `addPartDivider` / `addTOC`）を使う。

---

## Layout Architecture

要素を置く前に、まずレイアウトの仕組みを作る。視覚バグ（重なり・はみ出し・不揃いな余白）の最大の原因は、場当たりの座標指定。仕組みで防ぐ。

### Define Reusable Helper Functions

すべての from-scratch デッキは、生のシェイプ呼び出しではなく**ヘルパー関数**から始める。これがレイアウトバグを防ぐ最も効果的な一手。最低限、長方形・1行テキスト・複数行テキスト・カード（ヘッダーバー＋本文）・バッジ＋タイトル対のヘルパーを定義し、全スライドをこれらから組む。生API呼び出しから組まない。ヘルパーは要素間の空間関係（「タイトルはバッジの右端から始まる」）を一度だけ定義し、全箇所で保証する。実装は [pptxgenjs.md](pptxgenjs.md) / [python-pptx.md](python-pptx.md)。

### Collision Prevention

頻出レイアウトバグ4種（苦情の多い順）：

**1. バッジ/ラベルがタイトル文字に重なる。** タイトルの x はバッジの終端の後から始める：`title_x = badge_x + badge_width + gap`。同じ x に置かない。プログラム生成スライドの視覚バグNo.1。

**2. テキストがコンテナを溢れる。** pptxgenjs も python-pptx も自動縮小しない。可変長テキスト（価格・要約・説明）は、ほぼ全幅（10"スライドで8–9"）のボックスにするか、文字数から必要幅を計算する。日本語14ptは約0.23"/字、英字は約0.12"/字。

**3. カード/列がスライド端を超える。** N個を横並びにする前に：`item_width = (usable_width - (N-1)*gap) / N`。`start_x + N*(item_width+gap) - gap + margin <= slide_width` を検証。

**4. 縦のコンテンツがスライド高を超える。** 5.625"スライド・上余白0.5"・アクセントバー0.06"なら使用可能高は約5.0"。yの累積を追い、超えるなら全体を縮めず2枚に割る。

### Consistent Spacing System

間隔の単位（例0.25"）を1つ決め、全箇所でその倍数を使う。16:9（10"×5.625"）の推奨：

- 外余白: 0.5–0.6"（全辺）
- タイトルy: 上アクセントバーから0.25"
- コンテンツ開始: 上から1.0–1.1"
- カード/列の間隔: 0.2–0.3"
- カード内パディング: 0.1–0.15"
- アクセントバー高: 0.05–0.06"

---

## Layout Patterns（描画レイアウトの引き出し）

slide-plan で「画像＋文」「章扉」等が指定されたとき使う描画パターン。どのスライドにどれを使うかは plan の指定に従う（構成判断は deck-composition 側）。

### Split-Page（画像＋コンテンツ）

画像を片側（通常左）、ダーク/カラーのコンテンツパネルを反対側に、細いアクセント線で分ける。画像はコンテナ寸法に**事前クロップ**して歪みを防ぐ（後述）。

### Full-Bleed Divider（章扉）

章の転換に、全面背景画像＋半透明オーバーレイ（30–50%）＋中央タイトル。視覚リズムを作り、内容過多の連続を区切る。

---

## Image Layout Patterns

画像（AI生成・支給問わず）は正しいサイズが命。歪んだ画像はプロらしさを最速で損なう。

### Pre-Cropping for Non-Standard Containers

AI生成画像やストックは通常16:9（1024×576等）。16:9でないコンテナ（ハーフスライド 5.0"×5.625" 等）に直に置くと歪む。**事前にセンタークロップ**する。

```javascript
const sharp = require("sharp");

async function cropImgForCover(imagePath, targetW, targetH) {
  const meta = await sharp(imagePath).metadata();
  const srcRatio = meta.width / meta.height;
  const tgtRatio = targetW / targetH;
  let cropW, cropH, left, top;
  if (srcRatio > tgtRatio) {
    cropH = meta.height;
    cropW = Math.round(meta.height * tgtRatio);
    left = Math.round((meta.width - cropW) / 2);
    top = 0;
  } else {
    cropW = meta.width;
    cropH = Math.round(meta.width / tgtRatio);
    left = 0;
    top = Math.round((meta.height - cropH) / 2);
  }
  const buf = await sharp(imagePath)
    .extract({ left, top, width: cropW, height: cropH })
    .png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
```

| Container | Dimensions | Ratio |
|-----------|-----------|-------|
| Full slide | 10.0" × 5.625" | 16:9（クロップ不要） |
| Half-slide | 5.0" × 5.625" | ~0.89:1（ほぼ正方） |
| Wide panel | 5.5" × 5.625" | ~0.98:1 |
| Two-thirds | 6.67" × 5.625" | ~1.19:1 |

**`sizing: { type: "cover" }` を使わない理由：** LibreOffice（QAのPDF変換で使用）が正しく描画せず、画像が伸びる/ずれる。常に事前クロップする。python-pptx は Pillow で同等のクロップを行う（[python-pptx.md](python-pptx.md)）。

---

## AI-Generated Images

スライド用にAI画像生成（nano-banana 等）を使うとき：

### Always Request No Text

AI画像生成は文字を崩す（特に日本語）。常にテキスト抑制を明示：プロンプトに "no text, no words, no letters, no writing, no captions"／negative に "text, words, letters, writing, captions, signs with text, watermark"。残るなら強い negative で再生成。

> 顧客向けの画面モック等、日本語UIが要る図はAI生成を使わない（崩れる）。図形描画で作る。

### Prompt Tips

- シーン・ムード・スタイル（"photorealistic" / "flat illustration" / "isometric"）を具体的に
- ライティングと色調をスライドのパレットに合わせる
- ペルソナ画像は文脈（デスク・オフィス・会議）を描写
- 概念画像は視覚メタファを具体的に（"holographic data dashboard floating above a desk"）

### Workflow

1. 画像は早めに生成（時間がかかる・再生成あり）
2. 埋め込み前に文字アーティファクトを確認
3. コンテナ寸法に事前クロップ
4. base64 埋め込みで信頼性を確保（ファイルパスは環境で壊れる）

---

## Design Ideas

**退屈なスライドを作らない。** 白地に箇条書きだけでは誰も動かない。

### Before Starting

- **内容に合った大胆なパレット**：別のプレゼンに入れ替えても成立するなら、選び方が一般的すぎる。
- **支配色を作る**：1色が60–70%の視覚的重み、支える1–2色、鋭いアクセント1色。全色を均等にしない。
- **ダーク/ライトのコントラスト**：タイトル＋結論はダーク、コンテンツはライト（サンドイッチ）。または全面ダークでプレミアム感。
- **視覚モチーフを1つに統一**：角丸フレーム／色付き円のアイコン／太い片側ボーダー等を全スライドで繰り返す。
- **色は名前付き定数でスクリプト冒頭に定義**。生のhexをインラインに書かない。

### Color Palettes（汎用の引き出し。社内案件は brand-design を優先）

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| Midnight Executive | `1E2761` | `CADCFC` | `FFFFFF` |
| Forest & Moss | `2C5F2D` | `97BC62` | `F5F5F5` |
| Coral Energy | `F96167` | `F9E795` | `2F3C7E` |
| Charcoal Minimal | `36454F` | `F2F2F2` | `212121` |
| Teal Trust | `028090` | `00A896` | `02C39A` |
| Cherry Bold | `990011` | `FCF6F5` | `2F3C7E` |

### Typography

ヘッダーは個性のあるフォント＋クリーンな本文フォントの対で（Arial 既定にしない）。サイズ目安：スライドタイトル 36–44pt bold ／セクションヘッダー 20–24pt bold ／本文 14–16pt ／キャプション 10–12pt muted。

### Avoid（頻出ミス）

- 同じレイアウトの繰り返し ／ 本文の中央揃え（段落・リストは左揃え、中央は見出しのみ）
- サイズコントラスト不足（タイトルは36pt+で本文14–16ptと差を）
- 青のデフォルト ／ 間隔の混在
- 1枚だけ凝って残りは素 ／ テキストのみのスライド（画像・アイコン・図を入れる）
- テキストボックスのパディング無視（線や図形を文字端に合わせるとき `margin:0`）
- 低コントラスト（明地に明文字／暗地に暗アイコン）
- **タイトル下のアクセント線は使わない**（AI生成スライドの典型。余白か背景色で代替）
- 隣接要素の座標を独立にハードコード（バッジ＋タイトル等は必ず一方の境界＋gapから導く）

---

## QA (Required)

**問題はあるものとして探す。** 初回レンダリングはまず正しくない。QAは確認ではなくバグ狩り。ゼロ件なら見方が甘い。

### Content QA

```bash
python -m markitdown output.pptx
```

抜け・誤字・順序を確認。テンプレ使用時はプレースホルダ残りを：

```bash
python -m markitdown output.pptx | grep -iE "\bx{3,}\b|lorem|ipsum|\bTODO|\[insert|this.*(page|slide).*layout"
```

ヒットしたら直してから success 宣言。

### Visual QA

**サブエージェントを使う**（2–3枚でも）。自分はコードを見続けて「期待」を見てしまう。サブエージェントは新鮮な目。スライドを画像化（下記）し、次の観点で点検：重なり／溢れ・切れ／1行用の装飾線にタイトルが2行化／脚注の衝突／要素が近すぎ(<0.3")／不揃いな余白／端からの余白不足(<0.5")／列の不揃い／低コントラスト文字・アイコン／狭すぎるテキストボックス／プレースホルダ残り／バッジのラベル重なり／画像の歪み／AI画像の文字アーティファクト。各スライドごとに、軽微でも全て報告させる。

### Verification Loop

生成→画像化→点検→**問題列挙**（無ければより批判的に再点検）→修正→**影響スライドを再検証**（1つの修正が別を生む）→新規問題が出なくなるまで。**最低1回の修正→検証サイクルを終えるまで success 宣言しない。**

---

## Converting to Images

```bash
python scripts/office/soffice.py --headless --convert-to pdf output.pptx
rm -f slide-*.jpg
pdftoppm -jpeg -r 150 output.pdf slide
ls -1 "$PWD"/slide-*.jpg
```

印字された絶対パスを view ツールに渡す。`rm` で前回の画像を消す。`pdftoppm` はページ数でゼロ埋めが変わる（<10で `slide-1.jpg`、10–99で `slide-01.jpg`）。**修正後は4コマンドを再実行**（編集済み .pptx からPDFを作り直してから画像化）。

---

## Dependencies

- `pip install "markitdown[pptx]"` — テキスト抽出
- `pip install Pillow` — サムネイル＋画像クロップ（Python）
- `npm install pptxgenjs` — from scratch（JS）
- `npm install sharp` — 画像クロップ（JS、非16:9コンテナ）
- `pip install python-pptx` — from scratch（Python、フォールバック）
- LibreOffice (`soffice`) — PDF変換（`scripts/office/soffice.py` がサンドボックス向けに自動設定）
- Poppler (`pdftoppm`) — PDF→画像

---

## 参照ドキュメント

- （前工程）`deck-composition` スキル — slide-plan.md（構成）を作る。本スキルはそれを刷る
- [editing.md](editing.md) — テンプレ編集
- [pptxgenjs.md](pptxgenjs.md) / [python-pptx.md](python-pptx.md) — from-scratch 実装とヘルパー
- [exec-deck-patterns.md](exec-deck-patterns.md) / [exec-deck-code.md](exec-deck-code.md) — 構成原則とナビ部品の実装（構成判断は deck-composition）
