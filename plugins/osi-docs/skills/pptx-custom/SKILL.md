---
name: pptx-custom
description: "Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file (even if the extracted content will be used elsewhere, like in an email or summary); editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates, layouts, speaker notes, or comments. Trigger whenever the user mentions \"deck,\" \"slides,\" \"presentation,\" or references a .pptx filename, regardless of what they plan to do with the content afterward. If a .pptx file needs to be opened, created, or touched, use this skill."
license: Proprietary. LICENSE.txt has complete terms
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_image]

---

# PPTX Skill

## Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `python -m markitdown presentation.pptx` |
| Edit or create from template | Read [editing.md](editing.md) |
| Create from scratch (JS) | Read [pptxgenjs.md](pptxgenjs.md) |
| Create from scratch (Python) | Read [python-pptx.md](python-pptx.md) |
| **Executive deck (内部合意・経営層向け)** | Read [exec-deck-patterns.md](exec-deck-patterns.md) + [exec-deck-code.md](exec-deck-code.md) |

**Which creation tool?** Try pptxgenjs first (`npm install -g pptxgenjs`). If npm fails (403 errors, network issues), fall back to python-pptx (`pip install python-pptx`). Both produce valid .pptx files; the guides contain equivalent design patterns.

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

**Read [pptxgenjs.md](pptxgenjs.md) or [python-pptx.md](python-pptx.md) for full details.**

Use when no template or reference presentation is available.

## Executive Deck Patterns (内部合意・経営層向け)

経営層への提案・内部合意取りのデッキは、専用のパターンを使う。詳細は別ファイル:

- **[exec-deck-patterns.md](exec-deck-patterns.md)** — 設計原則 (Action title, Message-not-description, WHY/HOW critique, One message per slide, タイポグラフィルール、パレット、Pyramid principle)
- **[exec-deck-code.md](exec-deck-code.md)** — pptxgenjs の ready-to-use コードパターン集 (helper 関数、7 種類の汎用レイアウト)

### When to apply

ユーザーから以下のような依頼があった時に適用:

- 「経営層向けの資料」「内部共有用」「合意取り」「方針提示」
- 「短く、要点だけ」「枚数少なく」「論点を明確に」
- 「ぬるっと」「マネジメント」「フレームワーク」を語る資料
- 「営業フロー」「業務フロー」「組織課題」のような戦略レベルの内部議論

逆に、以下では使わない（既存の pptx 一般パターンで足りる）:
- 営業先への外部提案 (initial-proposal / proposal-package を使う)
- 商品紹介・カタログ的な資料
- ピッチデック (投資家向けは別の最適化が必要)

### Core 原則 (1 行サマリ)

1. **Action title** — タイトルは結論を 1 文で言い切る (論点ラベルにしない)
2. **Subtitle = メッセージ** — 言いたいことを書く。説明ではない
3. **WHY/HOW 2 列は多くの場合 redundant** — subtitle と二重になっていないか必ず確認
4. **1 スライド 1 メッセージ** — 詰め込まない。枚数増やしてでも breathe させる
5. **アクセント色は 1 種類** — 状態色はドット・ストライプの小アクセントのみ
6. **タイトル ≤ 21 文字** (日本語 at 24pt メイリオ) — 1 行に収める

詳細とコード例は [exec-deck-patterns.md](exec-deck-patterns.md) と [exec-deck-code.md](exec-deck-code.md) を参照。

### Reference Implementation

AI OSI URI 営業フロー再設計 v3 (8 スライド) が完全実装の working example として残っている。同種の依頼が来たら、まずそのパターンを再利用する。


---

## Layout Architecture

Before placing any elements, establish a layout system. The most common cause of visual bugs (overlapping text, overflowing boxes, inconsistent spacing) is ad-hoc coordinate placement. A layout system prevents these issues structurally.

### Define Reusable Helper Functions

Every from-scratch presentation should start with helper functions — not raw shape calls. This is the single most impactful thing you can do to prevent layout bugs. See the creation guides ([pptxgenjs.md](pptxgenjs.md) or [python-pptx.md](python-pptx.md)) for ready-made helper code.

At minimum, define helpers for: rectangle shapes, single-line text, multi-line text, card components (header bar + body), and badge-title pairs. Then build every slide from these helpers, never from raw API calls.

The reason this matters: when you place elements with raw API calls, each call is independent and unaware of its neighbors. A helper function encapsulates the spatial relationship between elements (e.g., "title starts after badge ends") so the relationship is defined once and guaranteed everywhere.

### Collision Prevention

These are the four most frequent layout bugs, ranked by how often they cause user complaints:

**1. Badge/label overlapping title text.** When placing a badge (like "Priority" or "Step 1") next to a title, the title's x-position must start AFTER the badge ends, not at the same x. Calculate: `title_x = badge_x + badge_width + gap`. Never place both at the same x coordinate. This seems obvious but is the #1 source of visual bugs in programmatic slides.

**2. Text overflowing its container box.** Neither pptxgenjs nor python-pptx auto-shrinks text. If your text is longer than the box can display, it overflows silently (pptxgenjs) or wraps and gets clipped (python-pptx). For variable-length text (prices, summaries, descriptions), either use near-full-width boxes (8-9" on a 10" slide) or calculate the needed width from character count. Japanese text at 14pt is roughly 0.23" per character; Latin text is roughly 0.12" per character.

**3. Cards or columns extending past slide edge.** Before placing N items in a row, calculate: `item_width = (usable_width - (N-1) * gap) / N`. Verify that `start_x + N * (item_width + gap) - gap + margin <= slide_width`.

**4. Vertical content exceeding slide height.** On a 5.625" slide with 0.5" top margin and 0.06" accent bar, usable height is ~5.0". Track cumulative y-position as you add elements. If content exceeds the slide, split into two slides rather than shrinking everything.

### Consistent Spacing System

Pick a spacing unit (e.g., 0.25") and use multiples of it everywhere. This creates visual rhythm. Suggested system for 16:9 slides (10" x 5.625"):

- Outer margins: 0.5-0.6" (all sides)
- Title y-position: 0.25" from top accent bar
- Content starts: 1.0-1.1" from top
- Gap between cards/columns: 0.2-0.3"
- Internal card padding: 0.1-0.15"
- Accent bar height: 0.05-0.06"

---

## Visual-First Design Principles

Presentations are a visual medium. A slide with a compelling image and one focused message is far more effective than a slide packed with bullet points. When building image-heavy presentations, follow these principles:

### One Message Per Slide

Instead of cramming multiple points onto a single slide, give each key message its own page. This is especially effective for persona introductions, scenario descriptions, and key benefit statements. More slides at a comfortable reading pace beats fewer slides that overwhelm.

### Split-Page Layout (Image + Content)

A proven pattern for combining imagery with text: place the image on one half (typically left) and a dark or colored content panel on the other half, separated by a thin accent line.

```
┌─────────────┬──┬─────────────┐
│             │  │             │
│   Image     │▎ │  Content    │
│   (50%)     │▎ │  Panel      │
│             │▎ │  (50%)      │
│             │  │             │
└─────────────┴──┴─────────────┘
```

This layout keeps the image prominent while giving text enough breathing room to be readable. Pre-crop images to match the container dimensions (see Image Layout Patterns below) to avoid distortion.

### Full-Bleed Divider Slides

For section transitions, use a full-bleed background image with a semi-transparent overlay and centered title text. This creates visual rhythm and breaks up content-heavy sequences.

```
┌─────────────────────────────┐
│  ████████████████████████   │  ← Full-bleed image
│  ████████████████████████   │
│  ████ Section Title ████    │  ← Semi-transparent overlay + centered text
│  ████████████████████████   │
│  ████████████████████████   │
└─────────────────────────────┘
```

Use 30-50% transparency on the overlay so the image shows through while text remains readable.

---

## Speech-Driven Design (For Presentation Decks)

Most decks are designed visually but performed verbally. If a deck will be presented aloud (not just emailed or read), every slide must hold together as a sequence of speech, not just a sequence of pictures. A visually beautiful deck that no one can talk over fluently is a failed deck.

This section applies when the deck is intended for live presentation. Skip if the deck is a static handout, report, or template.

### Test by Reading the Deck Aloud

Before declaring a presentation deck done, read every slide's title and subtitle aloud in order, as if presenting. The deck is finished when the aloud read flows naturally from slide to slide without manufacturing bridge phrases ("uh, so next...", "now this is about..."). If you find yourself inventing transition language that isn't on the slide, the slide is incomplete.

This is the single most important QA step for presentation decks — more important than visual inspection. Visual bugs annoy the audience; speech bugs make the speaker look unprepared.

### Subtitles Are Transitions, Not Labels

The most impactful change to any presentation deck is rewriting subtitles. Most subtitles describe the slide's content. Better subtitles are transition phrases that connect to the previous slide and set up the current one — they answer the audience's silent question "why are we looking at this now?"

Compare:

- ❌ "Core Business Description" — describes content
- ✅ "Now let's look at the core CAIO business — how it works, pricing, current state" — transitions and previews

- ❌ "Market Size" — descriptive
- ✅ "By the way, the market we're targeting is different from everyone else's" — transitional

The descriptive subtitle leaves the audience flat. The transitional subtitle pulls them forward.

### Define Concepts Before Using Them

If a term will appear on multiple slides, define it the first time it appears — not five slides later. The most common bug: introducing an acronym (CAIO, ARR, NPS, MRR) in slide 3 but not defining it until slide 8. The audience spends those slides confused, missing the actual argument.

Two solutions:

1. **Inline definition in the subtitle** when the term first appears: `"CAIO (= a monthly retainer that teaches companies to use AI) as our entry point"`
2. **Dedicated definition slide** placed BEFORE the term gets used in detail

Avoid: a "What is X?" slide buried mid-deck after X has been mentioned five times.

### Where-Are-We Navigation

Decks longer than ~15 slides need explicit navigation so the speaker and the audience can answer "where are we in the flow?" at any moment. Use three devices together:

1. **Table of contents slide** near the front, listing major sections with slide numbers
2. **Section divider slides** between major parts — full-bleed dark background, large section letter, a brief preview list of slides in that section
3. **Breadcrumb on each content slide** — a small label above the section header showing the current part, e.g., `PART C · How We Execute`

The TOC sets expectations. Dividers signal gear changes. Breadcrumbs prevent mid-presentation disorientation. Together they make a 25-slide deck feel as navigable as a 5-slide deck.

### Anchor Slides for Repeated Reference

If a deck contains a central diagram (a 2x2 matrix, structure chart, value chain) that subsequent slides expand on, make that diagram a deliberate "anchor." Then explicitly position each detail slide as "we are now zooming into cell X of the anchor."

Pattern in subtitles: `"Zooming into the upper-left cell of the matrix — B2B × Sell"` — this tells the audience "we are looking at one specific part of the diagram you saw earlier." Without anchor references, deep-dive slides feel disconnected from each other. With them, the deck becomes one coherent map being explored, slide by slide.

### Vocabulary Consistency

If you call something `Central Asset` on one slide and `Cross-Cutting Asset` on another, the audience will think they are different things and spend mental cycles trying to reconcile them — missing your actual point. Pick one term per concept and use it across the entire deck.

Before final QA, run a synonym check on the rendered text:

```bash
python -m markitdown output.pptx | grep -iE "term1|synonym1|synonym2"
```

The aloud-reading test catches most of these naturally — you will hesitate when the words don't match what you said two slides ago.

### Don't End the Body With Open Questions

If the deck has a "Remaining Issues" / "Open Questions" / "TBD" slide, never place it immediately before the closing slide. Ending the body of the talk with "here are 19 things we haven't figured out yet" undercuts every persuasive point that came before. Move open questions to an appendix slide after the closing, or to a separate internal-only deck.

### Helper Functions to Encode These Patterns

When creating presentation decks from scratch, define these helpers up front so the patterns above are followed by construction rather than by remembering:

- `addSectionHeader(slide, num, title, subtitle, partLabel)` — section number + title + subtitle + optional breadcrumb above
- `addPartDivider(letter, title, slidesPreview, pageNum)` — full-bleed dark divider with PART letter and content preview
- `addTOC(slide, parts)` — multi-column TOC where each column is a PART with its slide list

The creation guides ([pptxgenjs.md](pptxgenjs.md), [python-pptx.md](python-pptx.md)) include reference implementations of these helpers. Use them on every presentation-style deck.

---

## Image Layout Patterns

When using images (whether AI-generated or supplied), correct sizing is critical. Distorted images are the fastest way to make a presentation look unprofessional.

### Pre-Cropping for Non-Standard Containers

AI image generators and stock photos typically produce 16:9 images (1024×576 or similar). When placing these into containers that aren't 16:9 — such as a half-slide panel (5.0" × 5.625") — the image will stretch and distort if placed directly.

The solution is to pre-crop before embedding. Use `sharp` (Node.js) to center-crop images to match the target container's aspect ratio:

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

#### Common Aspect Ratios

| Container | Dimensions | Ratio |
|-----------|-----------|-------|
| Full slide | 10.0" × 5.625" | 16:9 (no crop needed) |
| Half-slide (left/right) | 5.0" × 5.625" | ~0.89:1 (nearly square) |
| Wide panel | 5.5" × 5.625" | ~0.98:1 |
| Two-thirds | 6.67" × 5.625" | ~1.19:1 |

### Why Not `sizing: { type: "cover" }`?

PptxGenJS offers `sizing: { type: "cover" }` which promises CSS-like cover behavior. However, LibreOffice (used in the QA pipeline for PDF conversion) does not render this correctly — images appear stretched or mispositioned. Always pre-crop instead. This guarantees consistent rendering in both PowerPoint and LibreOffice QA.

### Python (python-pptx) Equivalent

For python-pptx, use Pillow for the same pre-crop approach:

```python
from PIL import Image
import io, base64

def crop_for_cover(image_path, target_w, target_h):
    img = Image.open(image_path)
    src_ratio = img.width / img.height
    tgt_ratio = target_w / target_h
    if src_ratio > tgt_ratio:
        crop_h = img.height
        crop_w = round(img.height * tgt_ratio)
        left = (img.width - crop_w) // 2
        box = (left, 0, left + crop_w, crop_h)
    else:
        crop_w = img.width
        crop_h = round(img.width / tgt_ratio)
        top = (img.height - crop_h) // 2
        box = (0, top, crop_w, top + crop_h)
    cropped = img.crop(box)
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    return buf.getvalue()
```

---

## AI-Generated Images

When using AI image generation (e.g., nano-banana, DALL-E, Midjourney) for slide visuals, follow these guidelines:

### Always Request No Text

AI image generators produce garbled, unreadable text — especially in non-Latin scripts like Japanese. Always include explicit instructions to suppress text:

- In the prompt: add "no text, no words, no letters, no writing, no captions"
- In negative_prompt (if supported): add "text, words, letters, writing, captions, speech bubbles, signs with text, watermark"
- If the generated image still contains text artifacts, regenerate with stronger negative prompts

### Prompt Tips for Presentation Images

- Be specific about the scene, mood, and visual style (e.g., "photorealistic", "flat illustration", "isometric")
- Mention lighting and color tone to match your slide palette
- For persona images, describe the person's context (desk, office, meeting) rather than just their appearance
- For concept images (data, AI, technology), describe the visual metaphor concretely (e.g., "holographic data dashboard floating above a desk" rather than just "data visualization")

### Image Generation Workflow

1. Generate images early — they take time and may need regeneration
2. Review each image for text artifacts before embedding
3. Pre-crop to target container dimensions (see Image Layout Patterns above)
4. Use base64 embedding for reliability — file paths can break across environments

---

## Design Ideas

**Don't create boring slides.** Plain bullets on a white background won't impress anyone. Consider ideas from this list for each slide.

### Before Starting

- **Pick a bold, content-informed color palette**: The palette should feel designed for THIS topic. If swapping your colors into a completely different presentation would still "work," you haven't made specific enough choices.
- **Dominance over equality**: One color should dominate (60-70% visual weight), with 1-2 supporting tones and one sharp accent. Never give all colors equal weight.
- **Dark/light contrast**: Dark backgrounds for title + conclusion slides, light for content ("sandwich" structure). Or commit to dark throughout for a premium feel.
- **Commit to a visual motif**: Pick ONE distinctive element and repeat it — rounded image frames, icons in colored circles, thick single-side borders. Carry it across every slide.
- **Define all colors as named constants at the top of your script.** Never use raw hex strings inline. This prevents typos and makes palette changes trivial.

### Color Palettes

Choose colors that match your topic — don't default to generic blue. Use these palettes as inspiration:

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| **Midnight Executive** | `1E2761` (navy) | `CADCFC` (ice blue) | `FFFFFF` (white) |
| **Forest & Moss** | `2C5F2D` (forest) | `97BC62` (moss) | `F5F5F5` (cream) |
| **Coral Energy** | `F96167` (coral) | `F9E795` (gold) | `2F3C7E` (navy) |
| **Warm Terracotta** | `B85042` (terracotta) | `E7E8D1` (sand) | `A7BEAE` (sage) |
| **Ocean Gradient** | `065A82` (deep blue) | `1C7293` (teal) | `21295C` (midnight) |
| **Charcoal Minimal** | `36454F` (charcoal) | `F2F2F2` (off-white) | `212121` (black) |
| **Teal Trust** | `028090` (teal) | `00A896` (seafoam) | `02C39A` (mint) |
| **Berry & Cream** | `6D2E46` (berry) | `A26769` (dusty rose) | `ECE2D0` (cream) |
| **Sage Calm** | `84B59F` (sage) | `69A297` (eucalyptus) | `50808E` (slate) |
| **Cherry Bold** | `990011` (cherry) | `FCF6F5` (off-white) | `2F3C7E` (navy) |

### For Each Slide

**Every slide needs a visual element** — image, chart, icon, or shape. Text-only slides are forgettable.

**Layout options:**
- Two-column (text left, illustration on right)
- Icon + text rows (icon in colored circle, bold header, description below)
- 2x2 or 2x3 grid (image on one side, grid of content blocks on other)
- Half-bleed image (full left or right side) with content overlay
- Card grid — colored header bar + body text blocks arranged in rows

**Data display:**
- Large stat callouts (big numbers 60-72pt with small labels below)
- Comparison columns (before/after, pros/cons, side-by-side options)
- Timeline or process flow (numbered steps, arrows)
- Programmatic Gantt charts (colored bars on a time grid — see creation guides)

**Visual polish:**
- Icons in small colored circles next to section headers
- Italic accent text for key stats or taglines
- Numbered badge + title pairs for table-of-contents slides
- Thin accent bars at the top of cards or stat boxes (0.05" colored strip)

### Typography

**Choose an interesting font pairing** — don't default to Arial. Pick a header font with personality and pair it with a clean body font.

| Header Font | Body Font |
|-------------|-----------|
| Georgia | Calibri |
| Arial Black | Arial |
| Calibri | Calibri Light |
| Cambria | Calibri |
| Trebuchet MS | Calibri |
| Impact | Arial |
| Palatino | Garamond |
| Consolas | Calibri |

| Element | Size |
|---------|------|
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt muted |

### Spacing

- 0.5" minimum margins
- 0.3-0.5" between content blocks
- Leave breathing room—don't fill every inch

### Avoid (Common Mistakes)

- **Don't repeat the same layout** — vary columns, cards, and callouts across slides
- **Don't center body text** — left-align paragraphs and lists; center only titles
- **Don't skimp on size contrast** — titles need 36pt+ to stand out from 14-16pt body
- **Don't default to blue** — pick colors that reflect the specific topic
- **Don't mix spacing randomly** — choose 0.3" or 0.5" gaps and use consistently
- **Don't style one slide and leave the rest plain** — commit fully or keep it simple throughout
- **Don't create text-only slides** — add images, icons, charts, or visual elements; avoid plain title + bullets
- **Don't forget text box padding** — when aligning lines or shapes with text edges, set `margin: 0` on the text box or offset the shape to account for padding
- **Don't use low-contrast elements** — icons AND text need strong contrast against the background; avoid light text on light backgrounds or dark text on dark backgrounds
- **NEVER use accent lines under titles** — these are a hallmark of AI-generated slides; use whitespace or background color instead
- **Don't hardcode sibling positions independently** — when two elements sit next to each other (badge + title, icon + label), always derive the second element's position from the first's bounds plus a gap

---

## QA (Required)

**Assume there are problems. Your job is to find them.**

Your first render is almost never correct. Approach QA as a bug hunt, not a confirmation step. If you found zero issues on first inspection, you weren't looking hard enough.

### Content QA

```bash
python -m markitdown output.pptx
```

Check for missing content, typos, wrong order.

**When using templates, check for leftover placeholder text:**

```bash
python -m markitdown output.pptx | grep -iE "\bx{3,}\b|lorem|ipsum|\bTODO|\[insert|this.*(page|slide).*layout"
```

If grep returns results, fix them before declaring success.

### Visual QA

**USE SUBAGENTS** — even for 2-3 slides. You've been staring at the code and will see what you expect, not what's there. Subagents have fresh eyes.

Convert slides to images (see [Converting to Images](#converting-to-images)), then use this prompt:

```
Visually inspect these slides. Assume there are issues — find them.

Look for:
- Overlapping elements (text through shapes, lines through words, stacked elements)
- Text overflow or cut off at edges/box boundaries
- Decorative lines positioned for single-line text but title wrapped to two lines
- Source citations or footers colliding with content above
- Elements too close (< 0.3" gaps) or cards/sections nearly touching
- Uneven gaps (large empty area in one place, cramped in another)
- Insufficient margin from slide edges (< 0.5")
- Columns or similar elements not aligned consistently
- Low-contrast text (e.g., light gray text on cream-colored background)
- Low-contrast icons (e.g., dark icons on dark backgrounds without a contrasting circle)
- Text boxes too narrow causing excessive wrapping
- Leftover placeholder content
- Badges or labels overlapping adjacent text
- Images that appear stretched or distorted (wrong aspect ratio)
- AI-generated text artifacts in images (garbled letters, nonsense words)

For each slide, list issues or areas of concern, even if minor.

Read and analyze these images — run `ls -1 "$PWD"/slide-*.jpg` and use the exact absolute paths it prints:
1. <absolute-path>/slide-N.jpg — (Expected: [brief description])
2. <absolute-path>/slide-N.jpg — (Expected: [brief description])
...

Report ALL issues found, including minor ones.
```

### Verification Loop

1. Generate slides → Convert to images → Inspect
2. **List issues found** (if none found, look again more critically)
3. Fix issues
4. **Re-verify affected slides** — one fix often creates another problem
5. Repeat until a full pass reveals no new issues

**Do not declare success until you've completed at least one fix-and-verify cycle.**

---

## Converting to Images

Convert presentations to individual slide images for visual inspection:

```bash
python scripts/office/soffice.py --headless --convert-to pdf output.pptx
rm -f slide-*.jpg
pdftoppm -jpeg -r 150 output.pdf slide
ls -1 "$PWD"/slide-*.jpg
```

**Pass the absolute paths printed above directly to the view tool.** The `rm` clears stale images from prior runs. `pdftoppm` zero-pads based on page count: `slide-1.jpg` for decks under 10 pages, `slide-01.jpg` for 10-99, `slide-001.jpg` for 100+.

**After fixes, rerun all four commands above** — the PDF must be regenerated from the edited `.pptx` before `pdftoppm` can reflect your changes.

---

## Dependencies

- `pip install "markitdown[pptx]"` - text extraction
- `pip install Pillow` - thumbnail grids + image pre-cropping (Python)
- `npm install pptxgenjs` - creating from scratch (JS)
- `npm install sharp` - image pre-cropping (JS, for non-16:9 containers)
- `pip install python-pptx` - creating from scratch (Python, fallback)
- LibreOffice (`soffice`) - PDF conversion (auto-configured for sandboxed environments via `scripts/office/soffice.py`)
- Poppler (`pdftoppm`) - PDF to images
