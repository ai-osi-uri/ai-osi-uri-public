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

**5. 表の下に置いたカードに、表の最終行が食われる（本番で最頻発）。**
`rowH` は**高さの指定ではなく最小値**。セル内テキストが折り返すと行はその分だけ伸びる。だから「BY + rowH × 行数」で計算した位置にカードを置くと、必ず重なる。

必ずこの順で見積もる：

```
1行の高さ ≒ フォントpt × 0.0176"（日本語）× 折り返し行数 + セル余白 0.12"
折り返し行数 = ceil( セル文字数 ÷ (列幅inch × 72 ÷ フォントpt × 0.92) )
表の実高さ = Σ(ヘッダ行 + 各行の高さ)  ← rowH ではなく実測見積もりを使う
カードの y = BY + 表の実高さ + 0.10"
```

事故の起き方は毎回同じ：**列を狭くして文字を長く書き、行が2〜3行に伸びて、最後の1〜2行が下のカードに隠れる。** 表の最終行は往々にして一番言いたい行なので、これは致命的。

対策の優先順位：
1. **セル文字数を削る**（1セル30字以内、理想は列幅で1〜2行に収まる長さ）
2. 行数を減らす（5行を超える表は、そもそも1スライド1メッセージから外れている疑い）
3. 表の下のカードを**1行の言い切りテキスト**に置き換える（カードは高さを食う）
4. それでも入らないなら2枚に割る

**表を含むスライドは、必ず画像に変換して最終行が見えているか目視する。** 数値計算だけで通したと思わない。

**6. 箇条書きが折り返して、末尾の数文字だけが次行の左端に落ちる。**
「・3ヶ月区切りの更新制。撤退も継続も軽くす／**る**」のように、送り仮名1〜2文字が単独行になる。
1箇所なら軽微だが、3列×3項目のカードだと6箇所同時に出て、**一目で「作りかけ」に見える**。

原因は2つあり、両方潰す：

**(a) ぶら下げインデントが無い** — 折り返し行が行頭「・」の下に潜り込む。段落に marL/indent を入れて頭を揃える。

```python
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches

def hang(p, inch=0.155):
    """折り返し行を1文字分ぶら下げる（python-pptx に API が無いので pPr を直接触る）"""
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Emu(Inches(inch)))))
    pPr.set("indent", str(-int(Emu(Inches(inch)))))
```

**(b) 1項目が列幅に対して長い** — 折り返す前提でも、末尾が孤立しない長さに削る。

```
1行に入る全角字数 ≒ テキスト幅inch × 72 ÷ フォントpt × 0.92
```

3列レイアウト（10"スライド）の実測値：**列幅2.8" → テキスト幅2.5" → 10.5ptで約16字**。
つまり **1項目16字以内なら1行、32字以内なら2行**。20字前後で書くと「16字＋4字」になり最悪。
**16の倍数付近を避けて書く**（12字前後 or 28字前後）のが実務的な逃げ方。

同じ理屈で、**カード内の見出し＋説明を1セット2行に収める**設計が安全。狭い列に3行以上を入れない。

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

### 具体スライドの3型（deck-composition 原則11〜12 を描くための型）

slide-plan に「他社事例」「相手ではこうする」「最初の2週間」が来たら、この3型で描く。列構成を毎回考え直さない。

**型A：事例テーブル（他社の動き）** — 列＝`会社 / やったこと / 出た結果 / 時期`
`出た結果` 列だけをブランド強調色にする。数字が無い行は載せない。4行以内。
最下部に1行の言い切りを置いて次のスライドへ橋を架ける（カードにしない。高さを食う）。

**型B：Before/After テーブル（相手ではこうする）** — 列＝`業務 / いまの姿 / AIを入れた後 / 効果の測り方`
- `業務` セルには**出所を改行で添える**（例：`① 開発用地の一次スクリーニング\n（中計「不動産査定システム」）`）。
  相手の公表資料にある施策と、こちらの追加提案が一目で分かる状態にする。
- `AIを入れた後` 列を強調色に。行は3つまで（4つ以上は絞れていない）。
- 1セル30字以内。長いと行が伸びて最終行が消える（Collision Prevention 5）。

**型C：日程テーブル（最初の2週間）** — 列＝`日 / やること / 誰が / 出てくるもの`
- 「動くものが出る日」の行だけ行ハイライト＋強調色にする。ここが提案の核。
- 表の下に「◯週間後に判定すること」を1カードだけ置く（止める条件を書く）。
- 「Phase 0：現状把握」のような**プロセス語では書かない**。「1〜2日目：担当者3名に同席し、直近10件の判断を記録」のように、誰が何をするかで書く。

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

### 人物写真は「顔で切って円形」にする

メンバー紹介・体制ページで受け取る顔写真は、たいてい**引きの縦長**で、そのまま置くと背景ばかりになる。
顔の位置を指定して正方形に切り、円形アルファのPNGにしてから貼る（PowerPointの図形トリミングに頼らない。
LibreOffice でのQA描画がずれる）。

```python
from PIL import Image, ImageDraw

def round_avatar(src, out, cx=0.45, cy=0.26, side=0.42, px=300):
    """cx,cy=顔の中心（画像比）／side=切り出す正方形の一辺（短辺比）"""
    im = Image.open(src).convert("RGB"); W, H = im.size
    sd = int(min(W, H) * side)
    l = max(0, min(W - sd, int(W * cx - sd / 2)))
    t = max(0, min(H - sd, int(H * cy - sd / 2)))
    im = im.crop((l, t, l + sd, t + sd)).resize((px, px), Image.LANCZOS)
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, px - 1, px - 1), fill=255)
    im.putalpha(mask); im.save(out, optimize=True)
```

`cx, cy` は**人ごとに変える**（既定 0.45/0.26 は立ち姿の一般値）。1枚ずつ画像化して顔が中心に来ているか見る。

**px は貼るサイズ × 300 で足りる。** 1.0インチの円なら300px。それ以上は容量だけ増える。

### 写真入り pptx はファイルサイズを見る

画像1枚を無加工で入れると簡単に数百KBになり、**Drive等のコネクタに base64 で渡せなくなる**
（1ファイル=1回の呼び出しで全体を渡す方式のため、数百KBで上限に当たる）。

- 貼るサイズから逆算した px に落とす（上記）
- 写真が多いなら `im.quantize(colors=192).convert("RGB")` を挟む（顔写真は192色でほぼ劣化が分からない）
- それでも通らないときは**画質を落として通すより、ローカルのDriveミラーに `cp` する**（`proposal-package` 参照）。
  納品物の画質を運搬経路の都合で下げない。

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

## 日本語ビジネス文書の絶対ルール（Non-negotiables）

顧客提出物で**毎回同じ手戻りを生んだ**項目。**判断ではなくルール**として守る（迷ったら守る側に倒す）。

### 単位は数値と一体で書く

金額は必ず「◯◯**億円**」「◯◯**万円**」。**「1,150億」で終わらせない。** 表のセル・stat の値・脚注・章扉も同じ。
単位無しの「億」「万」が許されるのは、別のカウンタが続くときだけ（`295万食` `130万食` `9,500店`）。

```python
import re, glob
from pptx import Presentation
C="円食店人件本杯枚回口社名年月日千万拠"
BAD=re.compile(r'[億万](?!['+C+r'])')
for f in glob.glob("*.pptx"):
    for s in Presentation(f).slides:
        for sh in s.shapes:
            ts=[c.text for r in sh.table.rows for c in r.cells] if sh.has_table else []
            if sh.has_text_frame: ts.append(sh.text_frame.text)
            for t in ts:
                if BAD.search(t or "") or "円円" in (t or ""): print(f, t[:60])
```

**0件になるまで直す。** なお既存 pptx を後から一括置換すると、ランが分割されていて「**億円円**」になる事故が起きる。`円円` も必ず 0 件を確認する。

### 章には必ず中扉を置く

本編に章立てがあるなら、**すべての章に扉を1枚**。1つでも欠けると読み手が迷子になる。生成後に「章ラベルの種類数 ＝ 中扉の枚数」を数えて一致を確認する。

### 目次は階層化し、ページ番号は最終ビルド後に実測する

- 章をフラットに並べない。**大区分（現状／ご提案／効果と進め方 等）→ 章**の2階層にする。
- **ページ番号を手で書かない。** スライドを増減させたら必ず実測して振り直す。

```python
start={}
for i,s in enumerate(prs.slides):                      # 表紙が index 0 → 印字番号 = index
    for sh in s.shapes:
        if not sh.has_text_frame or sh.top is None: continue
        y=sh.top/914400; t=sh.text_frame.text.strip()
        if 0.25<=y<=0.45 or 1.5<=y<=1.75:              # 章ラベル or 中扉の「第N章」
            for ch in ["第10章","第1章","第2章","第3章","第4章","第5章",
                       "第6章","第7章","第8章","第9章","APPENDIX"]:
                if t.startswith(ch) and ch not in start: start[ch]=i
```

ページ番号のテキストボックス自体も、スライド挿入・削除のたびに**通し番号を振り直す**。

### 色は毎回、相手から取り直す（前案件のパレットを絶対に流用しない）

**顧客向け資料の色は、案件ごとに変わる。前に作ったデッキの定数をコピーして使い始めない。**
1つ前の顧客の色のまま出すのは、宛名を間違えた手紙を送るのと同じ。

**取り方（この順に試す）**

1. **相手のIR資料・決算説明資料のPDF** — 最も確実。ロゴとグラフの色が両方入っている
   ```bash
   pdftoppm -jpeg -r 300 -f 1 -l 1 ir.pdf hi     # 1ページ目を高解像度で
   ```
   ```python
   from PIL import Image; from collections import Counter
   im=Image.open("hi-01.jpg").convert("RGB"); c=Counter()
   for r,g,b in im.resize((600,340)).getdata():
       if r>238 and g>238 and b>238: continue
       if abs(r-g)<15 and abs(g-b)<15: continue          # グレー除外
       c[(r//8*8,g//8*8,b//8*8)]+=1
   for (r,g,b),n in c.most_common(10): print(f"#{r:02X}{g:02X}{b:02X} {n}")
   ```
2. **コーポレートサイトのロゴ画像を canvas で集計**（IR PDF が手に入らないときの本命。数十秒で終わる）
   サイトを開き、ロゴ画像を canvas に描いてピクセルを数える。`getComputedStyle` の集計より確実で、
   **マークが多色の会社では色数そのものが分かる**（＝相手が何色で運用しているかが取れる）。
   ```javascript
   // ブラウザツールの javascript_exec で実行。ロゴのパスはページのDOMから拾う
   await (async () => {
     const img = new Image(); img.crossOrigin = "anonymous";
     img.src = "/cmn/img/logo.png";                    // ← 実際のロゴパス
     await new Promise((ok, ng) => { img.onload = ok; img.onerror = ng; });
     const c = document.createElement("canvas");
     c.width = img.width; c.height = img.height;
     c.getContext("2d").drawImage(img, 0, 0);
     const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data, cnt = {};
     for (let i = 0; i < d.length; i += 4) {
       if (d[i+3] < 200) continue;                     // 透明を除外
       const k = "#" + [d[i], d[i+1], d[i+2]].map(v => (v>>3<<3).toString(16).padStart(2,"0")).join("");
       cnt[k] = (cnt[k]||0) + 1;
     }
     return Object.entries(cnt).sort((a,b)=>b[1]-a[1]).slice(0,8);
   })()
   ```
   **ロゴ候補は複数試す。** ヘッダー用（白抜き）は白1色しか返らないことがあり、`/cmn/img/logo.png` のような
   マーク版に本来の色が入っている。返り値が白/黒だけなら別パスを当たる。
3. ロゴ画像のピクセルサンプリング（画像を手元に落とせる場合）

**取れた色を、相手の使い方どおりに使う。** ブランド色が1色しかない会社に無理やり4色の意味割り当てをしない。
「メイン1色＋サブ1色＋グレー」で運用している相手なら、こちらも3色で組む。**色数は相手のIR資料に合わせる。**

### 色は「意味」に割り当てる。1色の一辺倒にしない

ブランド色が複数あるなら役割を決めて使う。同じ色を強調全部に使うと、読み手は優先順位を判断できない。

| 役割 | 使う場所 |
|---|---|
| 事実・現状 | 現状把握の章、データ提示 |
| 課題・不足・リスク | 差分・懸念・未達の指標 |
| ご提案 | 方針・打ち手の章 |
| 効果・成功事例 | 効果の見込み、他社の成功実績 |

- 割り当ては**冒頭の定数で宣言**し、スライドごとにその章の色を引く。
- **表の中の数値の色は、章のアクセント色に引きずらない。** 「良い数字／悪い数字」の意味で全編一貫させる。
- どの色をどの役割に当てるかは**顧客の好みで入れ替わる**。ローテーションで一括入れ替えできる形（色→色のマップを1箇所で持つ）にしておく。

### 見出しの命名規約

- 「〜とは」「〜の分析」「〜について」を使わない。
- 事実を示す面 → 「**◯◯の実績**」「**◯◯の過去事例**」「**調査対象の◯◯**」
- 提案する面 → 「**◯◯へのご提案**」「**◯◯はこう変わる**」
- 「だから◯◯はこうする」は社内の言い方。顧客向けは「**◯◯へのご提案**」。

### 抽象は本編に置かない

「3つの型」「フレームワーク」「分類」などの抽象整理は **Appendix**。本編は「誰が・いつ・何をして・数字がどう動いたか」の具体だけで通す。抽象を本編に置くと必ず「これは要らない」と言われる。

### 隣接スライドの情報重複を検出する

連続する2枚が同じ表・同じ指標を出していないか。生成後に本文を抽出し、**指標名・固有名詞の重複**を機械的に見る。片方は削るか、片方に畳む。

---

## QA (Required)

**問題はあるものとして探す。** 初回レンダリングはまず正しくない。QAは確認ではなくバグ狩り。ゼロ件なら見方が甘い。

**先に「日本語ビジネス文書の絶対ルール」の機械チェック（単位・`円円`・中扉・目次番号）を 0 件にする。** そのうえで以下の Content QA / Visual QA に進む。

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

**サブエージェントを使う**（2–3枚でも）。自分はコードを見続けて「期待」を見てしまう。サブエージェントは新鮮な目。**サブエージェント禁止の環境では、自分で全ページを画像化して1枚ずつ見る。省略しない。** スライドを画像化（下記）し、次の観点で点検：重なり／溢れ・切れ／**表の最終行がカードに隠れていないか**／1行用の装飾線にタイトルが2行化／脚注の衝突／要素が近すぎ(<0.3")／不揃いな余白／端からの余白不足(<0.5")／列の不揃い／低コントラスト文字・アイコン／狭すぎるテキストボックス／プレースホルダ残り／バッジのラベル重なり／画像の歪み／AI画像の文字アーティファクト／**折り返しで末尾数文字だけが次行に落ちていないか**（Collision Prevention 6）／**枠線に文字が接触していないか**（下端1〜2pxは「切れている」ように見える）。各スライドごとに、軽微でも全て報告させる。

> サブエージェントに渡すときは「**軽微でも全て報告。問題なしと書くな**」と明示する。曖昧に頼むと「概ね良好です」で返ってきて、
> 孤立行や枠線接触のような**単体では軽微だが枚数分累積して"雑に見える"欠陥**が素通りする。

**表と目次は特に重点的に見る。** この2つが実運用での事故の大半：
- 表 → 折り返しで行が伸び、最終行が下の要素に食われる（Collision Prevention 5）
- 目次 → 章の項目を1つ増やしただけで、次の章の見出しに被る。**項目を増減したら必ず全章の y を取り直す**

**枚数が変わったら、目次のページ番号を必ず振り直す。** ページ番号は「スライド番号 − 表紙」でずれるので、フッタの実値を読んで目次に書き戻すこと（本文中で他ページを参照している箇所も同様）。

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
