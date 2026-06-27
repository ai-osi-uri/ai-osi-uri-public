# exec-deck-code — pptxgenjs ready-to-use コードパターン

経営層デッキを刷るための、コピーして使えるヘルパー関数とレイアウト集。**生のシェイプ呼び出しから組まない**——まずヘルパーを定義し、全スライドをそれで組む（`pptx-custom` の SKILL.md「Layout Architecture」の方針）。座標は 16:9 = 10" × 5.625" 前提。python-pptx 版の等価実装は [python-pptx.md](python-pptx.md) を参照。

設計判断（どのスライドに何を、どの順で）は `deck-composition` の `slide-plan.md` に従う。本書は「刷る」実装だけを与える。

---

## 0. セットアップ（パレット・寸法・フォントを定数化）

```javascript
const PptxGenJS = require("pptxgenjs");
const pptx = new PptxGenJS();
pptx.defineLayout({ name: "OSI", width: 10, height: 5.625 });
pptx.layout = "OSI";

// 色は名前付き定数で（生 hex をインラインに書かない）
const C = {
  navy:   "1E2761",  // 支配色
  sky:    "CADCFC",  // 支える色
  ink:    "212121",  // 本文
  muted:  "6B7280",  // キャプション
  white:  "FFFFFF",
  accent: "F96167",  // 鋭いアクセント
  line:   "E5E7EB",  // 区切り線
};
const F = { head: "Montserrat", body: "Noto Sans JP" }; // 見出し/本文の対

// 余白・間隔（1単位の倍数で。SKILL.md「Consistent Spacing System」）
const M = 0.6;                 // 外余白
const W = 10, H = 5.625;       // スライド寸法
const usableW = W - M * 2;     // 8.8"
```

---

## 1. コアヘルパー（最低限この5つ）

```javascript
// 長方形（塗り/枠）
function rect(slide, x, y, w, h, fill, opts = {}) {
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h, fill: fill ? { color: fill } : { type: "none" },
    line: opts.line ? { color: opts.line, width: opts.lineW || 1 } : { type: "none" },
    rectRadius: opts.radius, shadow: opts.shadow,
  });
}

// 1行テキスト（タイトル等。溢れ防止に valign 固定、margin:0）
function line(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h, align: opts.align || "left", valign: opts.valign || "middle",
    fontFace: opts.face || F.head, fontSize: opts.size || 18,
    bold: opts.bold !== false, color: opts.color || C.ink, margin: 0,
  });
}

// 複数行本文（左揃え・行間。可変長は全幅近くに）
function body(slide, runs, x, y, w, h, opts = {}) {
  slide.addText(runs, {
    x, y, w, h, align: "left", valign: opts.valign || "top",
    fontFace: F.body, fontSize: opts.size || 15, color: opts.color || C.ink,
    lineSpacingMultiple: 1.25, margin: 0, bullet: opts.bullet || false,
  });
}

// カード（ヘッダーバー＋本文）。N枚横並びは item 幅を計算して渡す
function card(slide, x, y, w, h, title, lines, opts = {}) {
  const head = 0.5;
  rect(slide, x, y, w, h, C.white, { line: C.line, radius: 0.06, shadow: { type: "outer", blur: 6, offset: 2, color: "000000", opacity: 0.12 } });
  rect(slide, x, y, w, head, opts.headFill || C.navy, { radius: 0.06 });
  line(slide, title, x + 0.15, y, w - 0.3, head, { color: C.white, size: 14 });
  body(slide, lines, x + 0.15, y + head + 0.12, w - 0.3, h - head - 0.24, { size: 13 });
}

// バッジ＋タイトル対（★タイトル x はバッジ終端＋gap から導く。重なり防止No.1）
function badgeTitle(slide, badge, title, x, y, w, opts = {}) {
  const bw = opts.badgeW || 0.5, gap = 0.18, h = opts.h || 0.5;
  rect(slide, x, y, bw, h, opts.badgeFill || C.accent, { radius: 0.06 });
  line(slide, badge, x, y, bw, h, { align: "center", color: C.white, size: opts.badgeSize || 18 });
  line(slide, title, x + bw + gap, y, w - bw - gap, h, { size: opts.size || 22, color: opts.color || C.ink });
}
```

> 横並びは必ず幅計算：`const itemW = (usableW - (N - 1) * gap) / N;` とし、`M + N*(itemW+gap) - gap <= W - M` を満たすことを確認（SKILL.md「Collision Prevention」3）。

---

## 2. ナビ部品（章扉・章区切り・目次・パンくず）

slide-plan に章扉/目次/パンくずの指定があるとき使う。

```javascript
// 章扉：全面ダーク＋大見出し（サンドイッチの「区切り」）
function addSectionHeader(pptx, partNo, partTitle, subtitle) {
  const s = pptx.addSlide();
  rect(s, 0, 0, W, H, C.navy);
  rect(s, M, 2.0, 0.9, 0.9, C.accent, { radius: 0.45 });
  line(s, String(partNo).padStart(2, "0"), M, 2.0, 0.9, 0.9, { align: "center", color: C.white, size: 30 });
  line(s, partTitle, M + 1.2, 2.05, usableW - 1.2, 0.8, { size: 40, color: C.white });
  if (subtitle) body(s, subtitle, M + 1.2, 2.95, usableW - 1.2, 0.8, { size: 16, color: C.sky });
  return s;
}

// 章区切り（軽い版。章扉ほど大仰にしないとき）
function addPartDivider(pptx, label) {
  const s = pptx.addSlide();
  rect(s, 0, 0, W, H, C.sky);
  line(s, label, M, H / 2 - 0.5, usableW, 1.0, { size: 34, color: C.navy, align: "left" });
  return s;
}

// 目次（章番号＋タイトルの一覧）
function addTOC(pptx, items, title = "本日のアジェンダ") {
  const s = pptx.addSlide();
  rect(s, 0, 0, W, H, C.white);
  line(s, title, M, M, usableW, 0.7, { size: 30, color: C.navy });
  const top = 1.6, rowH = Math.min(0.7, (H - top - M) / items.length);
  items.forEach((it, i) => {
    const y = top + i * rowH;
    line(s, String(i + 1).padStart(2, "0"), M, y, 0.7, rowH, { color: C.accent, size: 22, align: "center" });
    line(s, it, M + 0.9, y, usableW - 0.9, rowH, { size: 18, color: C.ink, bold: false });
    if (i < items.length - 1) rect(s, M + 0.9, y + rowH - 0.02, usableW - 0.9, 0.012, C.line);
  });
  return s;
}

// パンくず（右上に現在の章を小さく。各コンテンツスライドで呼ぶ）
function breadcrumb(slide, partTitle) {
  line(slide, partTitle, W - M - 3.0, 0.22, 3.0, 0.3, { align: "right", color: C.muted, size: 10, bold: false });
}
```

---

## 3. 汎用レイアウト7種

各関数は `slide-plan.md` の1行（Action title＋メッセージ＋証拠指定）を1スライドに刷る。

```javascript
// (1) 表紙
function slideTitle(pptx, title, subtitle, footer) {
  const s = pptx.addSlide();
  rect(s, 0, 0, W, H, C.navy);
  rect(s, M, H - 1.4, 1.4, 0.08, C.accent);     // タイトル“下”でなく左下のモチーフ
  line(s, title, M, 1.7, usableW, 1.6, { size: 40, color: C.white });
  if (subtitle) body(s, subtitle, M, 3.4, usableW, 0.8, { size: 18, color: C.sky });
  if (footer) line(s, footer, M, H - 0.7, usableW, 0.3, { size: 11, color: C.sky, bold: false });
  return s;
}

// (2) アジェンダ → addTOC を使う（上記）

// (3) 章扉 → addSectionHeader を使う（上記）

// (4) 単一メッセージ（1枚1主張。KPIを特大に）
function slideSingleMessage(pptx, title, bigNumber, caption) {
  const s = pptx.addSlide();
  rect(s, 0, 0, W, H, C.white);
  line(s, title, M, M, usableW, 1.0, { size: 30, color: C.navy });
  line(s, bigNumber, M, 1.9, usableW, 1.8, { size: 80, color: C.accent, align: "left" });
  if (caption) body(s, caption, M, 3.9, usableW, 1.0, { size: 16, color: C.muted });
  return s;
}

// (5) 2カラム（左に主張、右に証拠/図）
function slideTwoCol(pptx, title, leftRuns, rightDraw) {
  const s = pptx.addSlide();
  rect(s, 0, 0, W, H, C.white);
  line(s, title, M, M, usableW, 0.8, { size: 28, color: C.navy });
  const top = 1.5, colW = (usableW - 0.4) / 2;
  body(s, leftRuns, M, top, colW, H - top - M, { size: 16 });
  if (rightDraw) rightDraw(s, M + colW + 0.4, top, colW, H - top - M); // 図/画像はコールバックで
  return s;
}

// (6) 比較/3カード横並び（MECEな3本柱の証拠提示）
function slideCards(pptx, title, cards) {
  const s = pptx.addSlide();
  rect(s, 0, 0, W, H, C.white);
  line(s, title, M, M, usableW, 0.8, { size: 28, color: C.navy });
  const N = cards.length, gap = 0.3, top = 1.6;
  const itemW = (usableW - (N - 1) * gap) / N, h = 3.0;
  cards.forEach((c, i) => card(s, M + i * (itemW + gap), top, itemW, h, c.title, c.lines, { headFill: c.color || C.navy }));
  return s;
}

// (7) 締め/CTA（ダーク地で次アクションを1つ）
function slideClosing(pptx, headline, cta) {
  const s = pptx.addSlide();
  rect(s, 0, 0, W, H, C.navy);
  line(s, headline, M, 1.8, usableW, 1.4, { size: 36, color: C.white });
  if (cta) {
    rect(s, M, 3.6, 3.2, 0.7, C.accent, { radius: 0.08 });
    line(s, cta, M, 3.6, 3.2, 0.7, { align: "center", color: C.white, size: 18 });
  }
  return s;
}
```

---

## 4. 仕上げ

```javascript
await pptx.writeFile({ fileName: "/tmp/deck.pptx" });
```

生成後は必ず `pptx-custom` の SKILL.md「QA (Required)」のループ（画像化→バグ狩り→修正→再検証）を回す。ヘルパーで組んでも、テキスト溢れ・カードのスライド端超え・パンくず衝突は出る。

> 設計原則（Action title / Pyramid / タイポ / パレット）の解説は [exec-deck-patterns.md](exec-deck-patterns.md)。
