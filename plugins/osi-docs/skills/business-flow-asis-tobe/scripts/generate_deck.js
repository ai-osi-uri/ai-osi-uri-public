#!/usr/bin/env node
//
// Business AS-IS / TO-BE deck generator.
// Reads a config.json describing the business and produces a pptx with swimlanes.
//
// Usage:
//   node generate_deck.js <config.json> <output.pptx>
//

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const FA = require("react-icons/fa");

// ============== Color Palette: Consulting Ink ==============
// Restrained, deep colors with semantic meaning. Each color is used for one
// thing only so the reader builds a stable mental model.
//   NAVY   = 利用者操作（手動）          人 lanes
//   AMBER  = AI / 自動実行              AI Agent lane
//   SLATE  = 外部システム（パッシブ）    External system lane
//   OXBLOOD = AS-IS (現状の不便さ)       section accent / arrows
//   FOREST = TO-BE (改善後)              section accent / arrows
// Background is warm off-white (PAPER) to feel like printed report stock
// rather than a screen. All colors are darker / less saturated than the
// previous palette so the deck reads as a consulting document rather than
// a marketing slide.
const C = {
  // Primary inks (人 / 手動)
  NAVY:    "1B2A4E",      // primary cell fill, lane axis bg
  NAVY_DK: "0F1B33",      // text on AMBER cells, accent strokes
  NAVY_LT: "5C6B8A",      // muted secondary

  // Surface
  WHITE:   "FFFFFF",
  PAPER:   "FAFAF7",      // page background (warm off-white)
  CREAM:   "FAFAF7",      // alias for backward compat
  ICE:     "E6EBF2",      // very subtle highlight

  // Accent inks (kept dark/saturated, never bright)
  AMBER:   "B8860B",      // AI / 自動 (was GOLD F5B700 — too bright)
  GOLD:    "B8860B",      // alias for backward compat
  OXBLOOD: "7B2D26",      // AS-IS accent (was RED C73E1D)
  RED:     "7B2D26",      // alias
  FOREST:  "2C5F4E",      // TO-BE accent (was GREEN 2E8B57)
  GREEN:   "2C5F4E",      // alias

  // Neutrals
  SLATE:    "5B6B7C",     // 外部システム fill
  SLATE_LT: "8A95A5",     // muted text
  BORDER:   "DCDCD3",     // hairline borders (subtle, warm)
  BORDER_LT:"E8E8E0",     // even softer

  // Text
  TEXT:      "1A1A2E",    // primary text on light bg
  TEXT_MUTED:"6B7280"     // secondary text
};

const ICON_MAP = {
  users: FA.FaUsers,
  building: FA.FaBuilding,
  userTie: FA.FaUserTie,
  userCog: FA.FaUserCog,
  user: FA.FaUser,
  robot: FA.FaRobot,
  click: FA.FaHandPointer,
  db: FA.FaDatabase,
  envelope: FA.FaEnvelope,
  warn: FA.FaExclamationTriangle,
  tools: FA.FaTools,
  pin: FA.FaMapMarkerAlt,
  server: FA.FaServer,
  sync: FA.FaSyncAlt,
  arrowRight: FA.FaArrowRight,
};

function renderIconSvg(IconComponent, color, size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}
async function iconToPng(name, color, size = 256) {
  const Cmp = ICON_MAP[name];
  if (!Cmp) throw new Error("Unknown icon: " + name);
  const svg = renderIconSvg(Cmp, color, size);
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
// Shadows are intentionally disabled in the consulting palette. Returns
// undefined so existing call sites don't have to change.
const makeShadow = () => undefined;

// Resolve a fill name (e.g., "RED") or hex string to a 6-char hex color.
function resolveColor(v, fallback) {
  if (!v) return fallback || C.NAVY;
  if (C[v] !== undefined) return C[v];
  if (/^[0-9A-Fa-f]{6}$/.test(v)) return v;
  return fallback || C.NAVY;
}

// =====================================================================
async function main() {
  const configPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!configPath || !outputPath) {
    console.error("Usage: node generate_deck.js <config.json> <output.pptx>");
    process.exit(2);
  }
  const cfg = JSON.parse(fs.readFileSync(configPath, "utf8"));

  // Pre-render commonly used icons
  const ICONS = {
    arrowGold: await iconToPng("arrowRight", "#" + C.GOLD, 256),
    arrowWhite: await iconToPng("arrowRight", "#" + C.WHITE, 256),
  };

  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = (cfg.meta && cfg.meta.client) || "";
  pres.title = (cfg.meta && cfg.meta.title) || "業務 AS-IS / TO-BE";

  // ---- Slide 1: Title ----
  await buildTitleSlide(pres, cfg.meta || {});
  // ---- Slide 2: 1行サマリ ----
  buildSummarySlide(pres, cfg.summary || {}, ICONS, 2);
  // ---- Slide 3: 登場人物 ----
  await buildPeopleSlide(pres, cfg.people || [], cfg.peopleNote, 3);
  // ---- Slide 4: AS-IS 全体像 ----
  await buildAsIsOverviewSlide(pres, cfg.asisOverview || {}, ICONS, 4);
  // ---- Slide 5: TO-BE 全体像 ----
  await buildToBeOverviewSlide(pres, cfg.tobeOverview || {}, ICONS, 5);
  // ---- Optional overview swimlanes (AS-IS / TO-BE) ----
  // cfg.overview = { phases, lanes, asis: {...}, tobe: {...}, position?: "before-steps" | "after-steps" }
  // When defined, generates 2 slides spanning all phases.
  const overview = cfg.overview;
  const overviewPos = (overview && overview.position) || "before-steps";

  let page = 6;
  function addOverviewSlides() {
    if (!overview) return;
    const phases = overview.phases || [];
    // Page splitting strategy:
    //   1. overview.splits = [[s,e],[s,e],...]  -> render exactly those ranges
    //      (most explicit; recommended when authors want to group phases
    //       semantically, e.g. [[0,2],[3,4],[5,6]] = 3 + 2 + 2)
    //   2. overview.splitPhases = true/false  -> manual override of auto-split
    //   3. otherwise auto-split into 2 halves when phases.length > 5
    let ranges;
    if (Array.isArray(overview.splits) && overview.splits.length > 0) {
      ranges = overview.splits.map(([s, e]) => [s, e]);
    } else {
      const autoSplit = phases.length > 5;
      const split = overview.splitPhases != null ? overview.splitPhases : autoSplit;
      if (split && phases.length > 1) {
        const cut = Math.ceil(phases.length / 2);
        ranges = [[0, cut - 1], [cut, phases.length - 1]];
      } else {
        ranges = null;  // single page, no split
      }
    }
    function partLabel(i, n) {
      if (n === 1) return "";
      if (n === 2) return i === 0 ? "前半" : "後半";
      return `${i + 1}/${n}`;
    }
    if (ranges) {
      ranges.forEach((r, i) => {
        buildOverviewSwimlaneSlide(pres, overview, "AS-IS", page, { phaseRange: r, partLabel: partLabel(i, ranges.length) });
        page += 1;
      });
      ranges.forEach((r, i) => {
        buildOverviewSwimlaneSlide(pres, overview, "TO-BE", page, { phaseRange: r, partLabel: partLabel(i, ranges.length) });
        page += 1;
      });
    } else {
      buildOverviewSwimlaneSlide(pres, overview, "AS-IS", page); page += 1;
      buildOverviewSwimlaneSlide(pres, overview, "TO-BE", page); page += 1;
    }
  }

  if (overviewPos === "before-steps") addOverviewSlides();

  // ---- Step swimlanes ----
  // Each step is rendered as either ONE combined slide (default) or TWO split slides
  // (AS-IS / TO-BE) when step.layout === "split".
  const steps = cfg.steps || [];
  steps.forEach((step) => {
    const layout = step.layout || "combined";
    if (layout === "split") {
      buildSplitStepSlide(pres, step, "AS-IS", page); page += 1;
      buildSplitStepSlide(pres, step, "TO-BE", page); page += 1;
    } else {
      buildStepSwimlaneSlide(pres, step, page); page += 1;
    }
  });

  if (overviewPos === "after-steps") addOverviewSlides();

  // ---- 横軸の構造変化 ----
  buildStructureSlide(pres, cfg.structure || { items: [] }, page); page += 1;
  // ---- まとめ ----
  buildEndSummarySlide(pres, cfg.summaryEnd || {}, page);

  await pres.writeFile({ fileName: outputPath });
  console.log("WROTE", outputPath);
}

// =====================================================================
// Section header — consulting-report style.
// Page number is a small monospace-ish label on the left (no filled badge),
// the title sits next to it in dark ink, and a single hairline rule sits
// just below. Avoids the heavier "filled square + colored number + thick
// underline" look of the previous design.
function addSectionHeader(s, num, title, opts) {
  opts = opts || {};
  const titleW = opts.shortTitle ? 5.55 : 8.4;
  // Section number in muted ink — small, set in the same family as body
  // text so it reads as a quiet meta label rather than a bright badge.
  s.addText(num, {
    x: 0.5, y: 0.55, w: 0.6, h: 0.42,
    fontSize: 11, color: C.TEXT_MUTED, bold: true,
    align: "left", valign: "middle", fontFace: "Calibri",
    charSpacing: 4, margin: 0
  });
  s.addText(title, {
    x: 1.10, y: 0.55, w: titleW, h: 0.42,
    fontSize: 19, color: C.TEXT, bold: true,
    valign: "middle", fontFace: "Calibri", margin: 0
  });
  // Hairline rule (very thin, full-width, light ink). Replaces the previous
  // navy bar — gives separation without visual weight.
  s.addShape("rect", {
    x: 0.5, y: 1.10, w: 9.0, h: 0.012,
    fill: { color: C.BORDER }, line: { type: "none" }
  });
}
function addFooter(s, page, label) {
  // Footer = thin top rule + small left/right meta in muted ink.
  s.addShape("rect", {
    x: 0.5, y: 5.30, w: 9.0, h: 0.008,
    fill: { color: C.BORDER_LT }, line: { type: "none" }
  });
  s.addText(label || "業務 AS-IS / TO-BE", {
    x: 0.5, y: 5.36, w: 6, h: 0.22,
    fontSize: 8.5, color: C.TEXT_MUTED, fontFace: "Calibri",
    charSpacing: 2, margin: 0
  });
  s.addText(String(page), {
    x: 8.5, y: 5.36, w: 1.0, h: 0.22,
    fontSize: 8.5, color: C.TEXT_MUTED, fontFace: "Calibri",
    align: "right", margin: 0
  });
}

// =====================================================================
// Swimlane legend (upper right). Renders a small chip box explaining the
// cell color scheme: 利用者 (NAVY) / AI Agent (GOLD) / 外部 (SLATE), plus
// a ▤ indicator for documents listed inside cells. Place this on every
// swimlane slide so the reader doesn't have to remember the convention.
function addSwimlaneLegend(s) {
  // Inline legend on a single line, right-aligned. Compact labels keep the
  // legend small enough to coexist with the slide title in the same row.
  const y = 0.62;
  const items = [
    { label: "手動",   fill: C.NAVY  },
    { label: "自動",   fill: C.AMBER },
    { label: "外部",   fill: C.SLATE }
  ];
  const labelW = 0.45;
  const chipW  = 0.14;
  const gap    = 0.04;
  const pad    = 0.22;
  const itemW  = chipW + gap + labelW + pad;
  const total  = items.length * itemW;
  let x = 9.50 - total;
  items.forEach((it) => {
    s.addShape("rect", {
      x, y: y + 0.04, w: chipW, h: chipW,
      fill: { color: it.fill }, line: { type: "none" }
    });
    s.addText(it.label, {
      x: x + chipW + gap, y, w: labelW, h: 0.22,
      fontSize: 9, color: C.TEXT, bold: false,
      align: "left", valign: "middle", fontFace: "Calibri", margin: 0
    });
    x += itemW;
  });
  // Doc indicator on a smaller second line, right-aligned and very muted.
  s.addText("▤ 細字 = 該当工程で更新/作成するドキュメント", {
    x: 5.5, y: 0.93, w: 4.0, h: 0.18,
    fontSize: 7.5, color: C.TEXT_MUTED, italic: true,
    align: "right", valign: "middle", fontFace: "Calibri", margin: 0
  });
}

// =====================================================================
async function buildTitleSlide(pres, meta) {
  const s = pres.addSlide();
  s.background = { color: C.NAVY_DK };
  s.addShape("rect", { x: 0.5, y: 0.6, w: 0.08, h: 4.4, fill: { color: C.GOLD }, line: { type: "none" } });
  if (meta.eyebrow) {
    s.addText(meta.eyebrow, { x: 0.8, y: 0.6, w: 8, h: 0.4, fontSize: 14, fontFace: "Arial", color: C.GOLD, bold: true, charSpacing: 6, margin: 0 });
  }
  s.addText(meta.title || "業務 AS-IS / TO-BE", {
    x: 0.8, y: 1.1, w: 9, h: 1.4, fontSize: 56, fontFace: "Georgia", color: C.WHITE, bold: true, margin: 0
  });
  if (meta.subtitle) {
    s.addText(meta.subtitle, { x: 0.8, y: 2.55, w: 9, h: 0.8, fontSize: 18, fontFace: "Calibri", color: C.ICE, margin: 0 });
  }
  s.addShape("rect", { x: 0.8, y: 3.5, w: 1.2, h: 0.04, fill: { color: C.GOLD }, line: { type: "none" } });
  if (meta.audience) {
    s.addText([
      { text: "想定読者", options: { color: C.SLATE_LT, fontSize: 11, breakLine: true } },
      { text: meta.audience, options: { color: C.WHITE, fontSize: 14, bold: true } }
    ], { x: 0.8, y: 3.7, w: 7, h: 0.8, fontFace: "Calibri", margin: 0 });
  }
  if (meta.date) {
    s.addText("最終更新: " + meta.date, { x: 0.8, y: 5.0, w: 4, h: 0.3, fontSize: 11, color: C.SLATE_LT, fontFace: "Calibri", margin: 0 });
  }
  if (meta.client) {
    s.addText(meta.client, { x: 7.5, y: 5.0, w: 2, h: 0.3, fontSize: 11, color: C.GOLD, fontFace: "Calibri", bold: true, align: "right", margin: 0 });
  }
}

function buildSummarySlide(pres, sum, ICONS, page) {
  const s = pres.addSlide();
  s.background = { color: C.CREAM };
  addSectionHeader(s, "01", "1行サマリ");

  s.addShape("rect", { x: 0.5, y: 1.5, w: 4.4, h: 3.6, fill: { color: C.WHITE }, line: { type: "none" }, shadow: makeShadow() });
  s.addShape("rect", { x: 0.5, y: 1.5, w: 4.4, h: 0.08, fill: { color: C.RED }, line: { type: "none" } });
  s.addText("AS-IS", { x: 0.7, y: 1.7, w: 2, h: 0.4, fontSize: 14, color: C.RED, bold: true, charSpacing: 4, fontFace: "Arial", margin: 0 });
  s.addText(sum.asisHeadline || "", { x: 0.7, y: 2.15, w: 4, h: 1.3, fontSize: 24, fontFace: "Georgia", color: C.NAVY, bold: true, margin: 0 });
  s.addText(sum.asisDetail || "", { x: 0.7, y: 3.55, w: 4, h: 1.4, fontSize: 12, color: C.SLATE, fontFace: "Calibri", margin: 0 });

  s.addImage({ data: ICONS.arrowGold, x: 4.6, y: 3.0, w: 0.8, h: 0.8 });

  s.addShape("rect", { x: 5.1, y: 1.5, w: 4.4, h: 3.6, fill: { color: C.NAVY }, line: { type: "none" }, shadow: makeShadow() });
  s.addShape("rect", { x: 5.1, y: 1.5, w: 4.4, h: 0.08, fill: { color: C.GOLD }, line: { type: "none" } });
  s.addText("TO-BE", { x: 5.3, y: 1.7, w: 2, h: 0.4, fontSize: 14, color: C.GOLD, bold: true, charSpacing: 4, fontFace: "Arial", margin: 0 });
  s.addText(sum.tobeHeadline || "", { x: 5.3, y: 2.15, w: 4, h: 1.3, fontSize: 24, fontFace: "Georgia", color: C.WHITE, bold: true, margin: 0 });
  s.addText(sum.tobeDetail || "", { x: 5.3, y: 3.55, w: 4, h: 1.4, fontSize: 12, color: C.ICE, fontFace: "Calibri", margin: 0 });

  addFooter(s, page);
}

async function buildPeopleSlide(pres, people, note, page) {
  const s = pres.addSlide();
  s.background = { color: C.CREAM };
  addSectionHeader(s, "02", "登場人物");
  const n = Math.min(people.length, 4);
  const cardW = 2.15, cardH = 3.3, gap = 0.13;
  const totalW = cardW * n + gap * (n - 1);
  const startX = (10 - totalW) / 2;
  for (let i = 0; i < n; i++) {
    const c = people[i];
    const x = startX + i * (cardW + gap);
    s.addShape("rect", { x, y: 1.5, w: cardW, h: cardH, fill: { color: C.WHITE }, line: { color: C.BORDER, width: 1 }, shadow: makeShadow() });
    s.addShape("rect", { x, y: 1.5, w: cardW, h: 1.0, fill: { color: C.NAVY }, line: { type: "none" } });
    if (c.icon && ICON_MAP[c.icon]) {
      const data = await iconToPng(c.icon, "#" + C.WHITE, 256);
      s.addImage({ data, x: x + (cardW - 0.6) / 2, y: 1.7, w: 0.6, h: 0.6 });
    }
    s.addText(c.title || "", { x, y: 2.55, w: cardW, h: 0.35, fontSize: 13, color: C.NAVY, bold: true, align: "center", fontFace: "Calibri", margin: 0 });
    s.addText(c.num || "", { x, y: 2.95, w: cardW, h: 0.7, fontSize: 32, color: C.GOLD, bold: true, align: "center", fontFace: "Georgia", margin: 0 });
    s.addText(c.desc || "", { x: x + 0.15, y: 3.7, w: cardW - 0.3, h: 0.95, fontSize: 10, color: C.SLATE, fontFace: "Calibri", align: "center", margin: 0 });
  }
  if (note) {
    s.addShape("rect", { x: 0.5, y: 5.0, w: 9, h: 0.4, fill: { color: C.ICE, transparency: 50 }, line: { type: "none" } });
    s.addText(note, { x: 0.5, y: 5.0, w: 9, h: 0.4, fontSize: 11, color: C.NAVY, italic: true, align: "center", fontFace: "Calibri", margin: 0 });
  }
  addFooter(s, page);
}

async function buildAsIsOverviewSlide(pres, ov, ICONS, page) {
  const s = pres.addSlide();
  s.background = { color: C.CREAM };
  addSectionHeader(s, "03", "業務全体像 ── AS-IS");
  if (ov.tagline) {
    s.addShape("rect", { x: 0.5, y: 1.4, w: 9, h: 0.45, fill: { color: C.RED, transparency: 85 }, line: { type: "none" } });
    s.addText(ov.tagline, { x: 0.5, y: 1.4, w: 9, h: 0.45, fontSize: 14, color: C.RED, bold: true, italic: true, align: "center", fontFace: "Calibri", margin: 0 });
  }
  if (ov.topBox) {
    s.addShape("roundRect", { x: 1.5, y: 2.05, w: 7, h: 0.7, fill: { color: C.WHITE }, line: { color: C.SLATE_LT, width: 1 }, rectRadius: 0.08 });
    s.addText(ov.topBox, { x: 1.5, y: 2.05, w: 7, h: 0.7, fontSize: 13, color: C.NAVY, bold: true, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
  }
  if (ov.topToMid) {
    s.addShape("line", { x: 5, y: 2.78, w: 0.001, h: 0.35, line: { color: C.RED, width: 2, endArrowType: "triangle" } });
    s.addText(ov.topToMid, { x: 5.1, y: 2.78, w: 4, h: 0.35, fontSize: 10, color: C.RED, italic: true, fontFace: "Calibri", margin: 0 });
  }
  s.addShape("rect", { x: 0.7, y: 3.2, w: 8.6, h: 1.45, fill: { color: C.NAVY }, line: { type: "none" } });
  if (ov.midTitle) {
    s.addText(ov.midTitle, { x: 0.7, y: 3.25, w: 8.6, h: 0.35, fontSize: 12, color: C.GOLD, bold: true, align: "center", fontFace: "Calibri", margin: 0 });
  }
  const tools = ov.midTools || [];
  const tn = tools.length;
  if (tn > 0) {
    const totalW = 8.6 - 0.6;
    const tw = totalW / tn - 0.05;
    tools.forEach((t, i) => {
      const tx = 1.0 + i * (tw + 0.2);
      s.addShape("rect", { x: tx, y: 3.7, w: tw, h: 0.85, fill: { color: C.WHITE, transparency: 85 }, line: { color: C.ICE, width: 1 } });
      s.addText([
        { text: t.name || "", options: { fontSize: 12, color: C.WHITE, bold: true, breakLine: true } },
        { text: t.note || "", options: { fontSize: 9, color: C.ICE, italic: true } }
      ], { x: tx, y: 3.7, w: tw, h: 0.85, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
      if (i < tn - 1) {
        s.addText("⇄", { x: tx + tw, y: 3.85, w: 0.2, h: 0.5, fontSize: 14, color: C.GOLD, bold: true, align: "center", margin: 0 });
      }
    });
  }
  const exts = ov.extSystems || [];
  const en = exts.length;
  if (en > 0) {
    const ew = (9.2 - (en - 1) * 0.2) / en;
    for (let i = 0; i < en; i++) {
      const e = exts[i];
      const ex = 0.4 + i * (ew + 0.2);
      s.addShape("rect", { x: ex, y: 4.75, w: ew, h: 0.5, fill: { color: C.WHITE }, line: { color: C.RED, width: 1 } });
      if (e.icon && ICON_MAP[e.icon]) {
        const data = await iconToPng(e.icon, "#" + C.RED, 128);
        s.addImage({ data, x: ex + 0.1, y: 4.83, w: 0.32, h: 0.32 });
      }
      s.addText([
        { text: e.name || "", options: { fontSize: 11, color: C.NAVY, bold: true, breakLine: true } },
        { text: e.note || "", options: { fontSize: 9, color: C.RED, italic: true } }
      ], { x: ex + 0.5, y: 4.75, w: ew - 0.55, h: 0.5, valign: "middle", fontFace: "Calibri", margin: 0 });
    }
  }
  addFooter(s, page);
}

async function buildToBeOverviewSlide(pres, ov, ICONS, page) {
  const s = pres.addSlide();
  s.background = { color: C.CREAM };
  addSectionHeader(s, "04", "業務全体像 ── TO-BE");
  if (ov.tagline) {
    s.addShape("rect", { x: 0.5, y: 1.4, w: 9, h: 0.45, fill: { color: C.GREEN, transparency: 85 }, line: { type: "none" } });
    s.addText(ov.tagline, { x: 0.5, y: 1.4, w: 9, h: 0.45, fontSize: 14, color: C.GREEN, bold: true, italic: true, align: "center", fontFace: "Calibri", margin: 0 });
  }
  if (ov.topBox) {
    s.addShape("roundRect", { x: 1.5, y: 2.05, w: 7, h: 0.7, fill: { color: C.WHITE }, line: { color: C.SLATE_LT, width: 1 }, rectRadius: 0.08 });
    s.addText(ov.topBox, { x: 1.5, y: 2.05, w: 7, h: 0.7, fontSize: 13, color: C.NAVY, bold: true, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
  }
  if (ov.topToMid) {
    s.addShape("line", { x: 5, y: 2.78, w: 0.001, h: 0.35, line: { color: C.GREEN, width: 2, endArrowType: "triangle" } });
    s.addText(ov.topToMid, { x: 5.1, y: 2.78, w: 4, h: 0.35, fontSize: 10, color: C.GREEN, italic: true, fontFace: "Calibri", margin: 0 });
  }
  s.addShape("rect", { x: 0.7, y: 3.15, w: 8.6, h: 1.45, fill: { color: C.NAVY }, line: { type: "none" } });
  if (ov.midTitle) {
    s.addText(ov.midTitle, { x: 0.7, y: 3.18, w: 8.6, h: 0.3, fontSize: 12, color: C.GOLD, bold: true, align: "center", fontFace: "Calibri", margin: 0 });
  }
  const stages = ov.stages || [];
  const sn = stages.length;
  if (sn > 0) {
    const totalW = 8.6 - 0.6;
    const sw = (totalW - (sn - 1) * 0.35) / sn;
    for (let i = 0; i < sn; i++) {
      const st = stages[i];
      const sx = 1.0 + i * (sw + 0.35);
      s.addShape("roundRect", { x: sx, y: 3.55, w: sw, h: 0.95, fill: { color: C.WHITE, transparency: 88 }, line: { color: C.ICE, width: 1 }, rectRadius: 0.08 });
      if (st.icon && ICON_MAP[st.icon]) {
        const data = await iconToPng(st.icon, "#" + C.WHITE, 256);
        s.addImage({ data, x: sx + 0.15, y: 3.75, w: 0.5, h: 0.5 });
      }
      s.addText([
        { text: st.label || "", options: { fontSize: 12, color: C.WHITE, bold: true, breakLine: true } },
        { text: st.desc || "", options: { fontSize: 9, color: C.ICE } }
      ], { x: sx + 0.75, y: 3.6, w: sw - 0.8, h: 0.85, valign: "middle", fontFace: "Calibri", margin: 0 });
      if (i < sn - 1) {
        const ag = await iconToPng("arrowRight", "#" + C.GOLD, 256);
        s.addImage({ data: ag, x: sx + sw + 0.05, y: 3.85, w: 0.25, h: 0.35 });
      }
    }
  }
  const exts = ov.extSystems || [];
  const en = exts.length;
  if (en > 0) {
    const ew = (9.2 - (en - 1) * 0.2) / en;
    for (let i = 0; i < en; i++) {
      const e = exts[i];
      const ex = 0.4 + i * (ew + 0.2);
      const tone = e.tone === "muted" ? C.SLATE : C.GREEN;
      s.addShape("rect", { x: ex, y: 4.75, w: ew, h: 0.5, fill: { color: C.WHITE }, line: { color: tone, width: 1 } });
      s.addText([
        { text: e.name || "", options: { fontSize: 11, color: C.NAVY, bold: true, breakLine: true } },
        { text: e.note || "", options: { fontSize: 9, color: tone, italic: true } }
      ], { x: ex, y: 4.75, w: ew, h: 0.5, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
    }
  }
  addFooter(s, page);
}

// =========== Step Swimlane Slide ===========
function buildStepSwimlaneSlide(pres, step, page) {
  const s = pres.addSlide();
  s.background = { color: C.CREAM };
  addSectionHeader(s, step.num || "##", "ステップ詳細 ── " + (step.title || ""), { shortTitle: true });
  addSwimlaneLegend(s);

  drawSubSwimlane(s, pres, {
    y0: 1.30, h: 1.85,
    mode: "AS-IS",
    headerColor: C.RED,
    lanes: (step.asis && step.asis.lanes) || [],
    slots: (step.asis && step.asis.slots) || 5,
    actions: (step.asis && step.asis.actions) || [],
    flows: (step.asis && step.asis.flows) || [],
  });
  drawSubSwimlane(s, pres, {
    y0: 3.25, h: 1.95,
    mode: "TO-BE",
    headerColor: C.GREEN,
    lanes: (step.tobe && step.tobe.lanes) || [],
    slots: (step.tobe && step.tobe.slots) || 5,
    actions: (step.tobe && step.tobe.actions) || [],
    flows: (step.tobe && step.tobe.flows) || [],
  });
  s.addShape("rect", { x: 0.45, y: 3.18, w: 9.25, h: 0.06, fill: { color: C.GOLD }, line: { type: "none" } });

  if (step.effect) {
    s.addShape("roundRect", { x: 6.5, y: 5.27, w: 3.2, h: 0.32, fill: { color: C.GOLD }, line: { type: "none" }, rectRadius: 0.04 });
    s.addText("効果: " + step.effect, { x: 6.5, y: 5.27, w: 3.2, h: 0.32, fontSize: 10, color: C.NAVY_DK, bold: true, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
  }
  addFooter(s, page);
}

// =========== Split Step Slide (single section, AS-IS or TO-BE only) ===========
// Used when step.layout === "split". The whole slide is dedicated to one section
// so cells get more vertical room and a docs legend can sit at the bottom.
//
// step.<asis|tobe> may include:
//   - subtitle: string shown italic under the title
//   - lanes / slots / actions / flows (same as before; actions may carry `doc`)
//   - docs: [{ name, where }, ...] shown as a legend at the bottom
function buildSplitStepSlide(pres, step, mode, page) {
  const s = pres.addSlide();
  s.background = { color: C.CREAM };
  const sec = (mode === "AS-IS" ? step.asis : step.tobe) || {};
  const accent = mode === "AS-IS" ? C.RED : C.GREEN;
  addSectionHeader(s, step.num || "##", `${step.title || ""} ── ${mode}`, { shortTitle: true });
  addSwimlaneLegend(s);
  if (sec.subtitle) {
    s.addText(sec.subtitle, { x: 0.5, y: 1.18, w: 9.0, h: 0.22, fontSize: 10, color: accent, italic: true, valign: "middle", fontFace: "Calibri", margin: 0 });
  }
  // Section height adapts to lane count so 5-lane configs get enough room
  // for each cell's "label + doc" content. Capped at 3.40 to leave a clean
  // 0.8"+ band at the bottom for the doc legend without overlap.
  const nLanes = (sec.lanes || []).length || 4;
  const sectionH = Math.min(3.40, 2.85 + Math.max(0, nLanes - 4) * 0.45);
  drawSubSwimlane(s, pres, {
    y0: 1.45, h: sectionH,
    mode,
    headerColor: accent,
    lanes: sec.lanes || [],
    slots: sec.slots || 5,
    actions: sec.actions || [],
    flows: sec.flows || [],
  });
  // Bottom band: doc legend OR a small "効果" line — but never both, to
  // avoid the visual overlap and "two callouts at the bottom" feel that
  // looked cluttered in the previous design. The subtitle already conveys
  // the high-level effect, so we drop the gold "効果:" pill entirely.
  if (sec.docs && sec.docs.length > 0) {
    const legY = 1.45 + sectionH + 0.12;
    addDocLegend(s, sec.docs, accent, legY, 5.26);
  }
  addFooter(s, page);
}

// =========== Overview Swimlane Slide ===========
// Renders one full-page swimlane that spans all phases of the workflow on the
// horizontal axis. Useful as a "single map" before drilling into per-step
// detail. Generates one slide per mode (AS-IS / TO-BE).
//
// overview = {
//   phases: ["①商談", "②契約", ...],   // 4-6 phase names (column headers)
//   asis:  { lanes, actions, flows, docs?, subtitle? },
//   tobe:  { lanes, actions, flows, docs?, subtitle? },
//   position?: "before-steps" | "after-steps"   // default before-steps
// }
//
// Each action is positioned by `phase` (column index) instead of `slot`.
//
// Optional opts:
//   - phaseRange: [startIdx, endIdx]  (inclusive). When set, only the given
//     phase columns are rendered, and actions/flows are filtered + re-indexed
//     so the remaining phases fill the slide width. Used to split a wide
//     overview into 前半 / 後半 pages so each cell can show "label + doc"
//     without the columns getting too narrow.
//   - partLabel: short suffix appended to the title (e.g. "前半" / "後半").
function buildOverviewSwimlaneSlide(pres, overview, mode, page, opts) {
  opts = opts || {};
  const s = pres.addSlide();
  s.background = { color: C.CREAM };
  const sec = (mode === "AS-IS" ? overview.asis : overview.tobe) || {};
  const accent = mode === "AS-IS" ? C.RED : C.GREEN;
  let phases = overview.phases || [];
  let actionsRaw = sec.actions || [];
  let flowsRaw = sec.flows || [];

  // If a phaseRange is given, slice the phases and re-index actions/flows.
  let phaseOffset = 0;
  if (opts.phaseRange) {
    const [a0, a1] = opts.phaseRange;
    phaseOffset = a0;
    phases = phases.slice(a0, a1 + 1);
    actionsRaw = actionsRaw.filter(act => {
      const p = act.phase != null ? act.phase : act.slot;
      return p >= a0 && p <= a1;
    });
    flowsRaw = flowsRaw
      .map(f => Object.assign({}, f, { path: (f.path || []).filter(([l, p]) => p >= a0 && p <= a1) }))
      .filter(f => f.path.length >= 2);
  }
  const titleSuffix = opts.partLabel ? `（${opts.partLabel}）` : "";
  addSectionHeader(s, sec.num || (mode === "AS-IS" ? "05" : "06"),
                   `全体スイムレーン ── ${mode}${titleSuffix}`,
                   { shortTitle: true });
  addSwimlaneLegend(s);
  if (sec.subtitle) {
    s.addText(sec.subtitle, { x: 0.5, y: 1.18, w: 9.0, h: 0.22, fontSize: 10, color: accent, italic: true, valign: "middle", fontFace: "Calibri", margin: 0 });
  }
  // The drawSubSwimlane helper accepts `slots` as an integer column count
  // and positions actions by `slot`. Map phase → slot, re-indexing for the
  // current phaseRange so the visible columns start at 0.
  // When the overview is split (phaseRange given) each cell has more room,
  // so we keep the `doc` field and let cells render "label + doc". When the
  // overview is rendered as a single full slide (no phaseRange), columns are
  // very narrow (5-7 phases) so we strip `doc` to keep cells legible — the
  // full document list still lives in the bottom legend.
  const stripDoc = !opts.phaseRange;
  const actions = actionsRaw.map(a => {
    const p = a.phase != null ? a.phase : a.slot;
    const out = Object.assign({}, a, { slot: p - phaseOffset });
    if (stripDoc) delete out.doc;
    return out;
  });
  const flows = flowsRaw.map(f => Object.assign({}, f, {
    path: (f.path || []).map(([l, p]) => [l, p - phaseOffset]),
  }));
  // Section height: with phaseRange, cells need to fit "label + doc", so make
  // the section taller (similar to split-step). Without phaseRange, cells are
  // label-only and the section can be more compact.
  const lanes = sec.lanes || overview.lanes || [];
  const nLanes = lanes.length || 4;
  const sectionH = opts.phaseRange
    ? Math.min(3.85, 2.85 + Math.max(0, nLanes - 4) * 0.55)
    : Math.min(3.10, 2.70 + Math.max(0, nLanes - 4) * 0.20);
  drawSubSwimlane(s, pres, {
    y0: 1.45, h: sectionH,
    mode,
    headerColor: accent,
    lanes,
    slots: phases.length || 5,
    actions,
    flows,
    phaseLabels: phases,   // when provided, drawn in the title bar instead
  });
  // In split mode the section is tall (cells carry "label + doc"), so we
  // skip the bottom-band doc list — the right-top legend already explains
  // the ▤ convention and per-step slides cover the per-step documents in
  // detail. In single-page (compact) mode we keep the bottom band so the
  // reader sees what data the workflow touches without leaving the slide.
  if (!opts.phaseRange && sec.docs && sec.docs.length > 0) {
    const legY = 1.45 + sectionH + 0.10;
    addDocLegend(s, sec.docs, accent, legY, 5.36);
  }
  addFooter(s, page);
}

// =========== Document Legend (bottom band) ===========
// Consulting-style: a thin top rule in the section accent color, a small
// caps label, and a quiet grid of items in dark text on the page background.
// Avoids the heavy "filled colored band + white text" look.
function addDocLegend(s, docs, accent, yTop, yBottom) {
  // Thin accent rule at the top to anchor the band
  s.addShape("rect", {
    x: 0.5, y: yTop, w: 9.1, h: 0.025,
    fill: { color: accent }, line: { type: "none" }
  });
  // Small caps label
  s.addText(`このフローで必要なドキュメント (${docs.length})`, {
    x: 0.5, y: yTop + 0.04, w: 9.1, h: 0.20,
    fontSize: 9, color: accent, bold: true, charSpacing: 3,
    align: "left", valign: "middle", fontFace: "Calibri", margin: 0
  });
  const bodyY = yTop + 0.28;
  const bodyH = yBottom - bodyY;
  const n = docs.length;
  // For >9 items use 4 columns so 10-12 items fit in 3 rows; otherwise 3.
  const cols = n > 9 ? 4 : (n > 4 ? 3 : n);
  const rows = Math.ceil(n / cols);
  const itemW = 9.1 / cols;
  const itemH = bodyH / rows;
  docs.forEach((d, idx) => {
    const c = idx % cols;
    const r = Math.floor(idx / cols);
    const x = 0.5 + itemW * c;
    const y = bodyY + itemH * r;
    // Tiny dot bullet in the accent color
    s.addShape("ellipse", {
      x: x + 0.04, y: y + (itemH / 2) - 0.045, w: 0.09, h: 0.09,
      fill: { color: accent }, line: { type: "none" }
    });
    s.addText(`${d.name || ""}`, {
      x: x + 0.18, y, w: itemW - 0.20, h: itemH * 0.55,
      fontSize: 9, color: C.TEXT, bold: true,
      align: "left", valign: "bottom", fontFace: "Calibri", margin: 0
    });
    if (d.where) {
      s.addText(d.where, {
        x: x + 0.18, y: y + itemH * 0.45, w: itemW - 0.20, h: itemH * 0.55,
        fontSize: 8, color: C.TEXT_MUTED, italic: true,
        align: "left", valign: "top", fontFace: "Calibri", margin: 0
      });
    }
  });
}

function drawSubSwimlane(s, pres, opts) {
  const { y0, h, mode, lanes, slots, actions, flows, headerColor, phaseLabels } = opts;
  const titleH = 0.32;
  const lanesY = y0 + titleH;
  const lanesH = h - titleH;
  const labelX = 0.45;
  const labelW = 1.45;
  const colsX = labelX + labelW;
  const colsRight = 9.7;
  const colsW = colsRight - colsX;
  const cellW = colsW / slots;
  const laneH = lanesH / lanes.length;

  // Section header — restrained "consultant" style.
  // - Thin colored accent bar on the LEFT only (1/8" wide)
  // - Mode label and phase columns sit on white with hairline bottom rule
  // - Phase labels are dark text with letter-spacing (no white-on-color)
  s.addShape("rect", {
    x: labelX, y: y0, w: 0.06, h: titleH,
    fill: { color: headerColor }, line: { type: "none" }
  });
  s.addShape("rect", {
    x: labelX + 0.06, y: y0, w: colsRight - labelX - 0.06, h: titleH,
    fill: { color: C.PAPER }, line: { type: "none" }
  });
  s.addText(mode, {
    x: labelX + 0.20, y: y0, w: 1.3, h: titleH,
    fontSize: 11, color: headerColor, bold: true,
    charSpacing: 5, valign: "middle", fontFace: "Calibri", margin: 0
  });
  if (Array.isArray(phaseLabels) && phaseLabels.length > 0) {
    phaseLabels.forEach((p, j) => {
      const px = colsX + j * cellW;
      s.addText(p, {
        x: px, y: y0, w: cellW, h: titleH,
        fontSize: 10, color: C.TEXT, bold: true,
        align: "center", valign: "middle", fontFace: "Calibri",
        charSpacing: 2, margin: 0
      });
    });
  } else {
    s.addText("時系列  →", {
      x: colsRight - 1.5, y: y0, w: 1.4, h: titleH,
      fontSize: 9, color: C.TEXT_MUTED, italic: true,
      align: "right", valign: "middle", fontFace: "Calibri", margin: 0
    });
  }
  // Hairline rule under the header band so it reads as a clear strip.
  s.addShape("rect", {
    x: labelX, y: y0 + titleH - 0.012, w: colsRight - labelX, h: 0.012,
    fill: { color: C.BORDER }, line: { type: "none" }
  });

  // Lane axis — flat, light cream column with dark text. Replaces the
  // heavy white-on-NAVY_DK block from the previous design.
  lanes.forEach((ln, i) => {
    const ly = lanesY + i * laneH;
    s.addShape("rect", {
      x: labelX, y: ly, w: labelW, h: laneH,
      fill: { color: C.PAPER }, line: { color: C.BORDER, width: 0.5 }
    });
    s.addText([
      { text: ln.name || "", options: { fontSize: 10, color: C.TEXT, bold: true, breakLine: !!ln.sub } },
      ...(ln.sub ? [{ text: ln.sub, options: { fontSize: 8, color: C.TEXT_MUTED } }] : [])
    ], {
      x: labelX + 0.05, y: ly, w: labelW - 0.1, h: laneH,
      align: "center", valign: "middle", fontFace: "Calibri", margin: 0
    });
    // Cell area — pure white with hairline grid (no zebra-striping).
    s.addShape("rect", {
      x: colsX, y: ly, w: colsW, h: laneH,
      fill: { color: C.WHITE }, line: { color: C.BORDER_LT, width: 0.4 }
    });
  });

  function cardRect(laneIdx, slotIdx) {
    const padX = 0.06, padY = 0.06;
    const cx = colsX + slotIdx * cellW + padX;
    const cy = lanesY + laneIdx * laneH + padY;
    return { x: cx, y: cy, w: cellW - padX * 2, h: laneH - padY * 2 };
  }
  function cardCenter(laneIdx, slotIdx) {
    const r = cardRect(laneIdx, slotIdx);
    return { cx: r.x + r.w / 2, cy: r.y + r.h / 2 };
  }

  actions.forEach(a => {
    const r = cardRect(a.lane, a.slot);
    const fill = resolveColor(a.fill, C.NAVY);
    const fontColor = resolveColor(a.color, C.WHITE);
    if (a.disabled) {
      s.addShape("rect", { x: r.x, y: r.y, w: r.w, h: r.h, fill: { color: "FFFFFF", transparency: 50 }, line: { color: C.SLATE_LT, width: 0.7, dashType: "dash" } });
      s.addText(a.label || "", { x: r.x, y: r.y, w: r.w, h: r.h, fontSize: 8, color: C.SLATE_LT, italic: true, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
    } else {
      // Crisp rectangle (no rounded corners, no shadow). Cells share the
      // same flat geometric language as the lane axis so the swimlane reads
      // as a single grid rather than a collection of "buttons".
      s.addShape("rect", {
        x: r.x, y: r.y, w: r.w, h: r.h,
        fill: { color: fill }, line: { type: "none" }
      });
      const labelRuns = [
        { text: a.label || "", options: { fontSize: 9, color: fontColor, bold: true, breakLine: !!a.doc } }
      ];
      if (a.doc) {
        const docLines = String(a.doc).split("\n");
        docLines.forEach((line, k) => {
          const text = (k === 0 ? "▤ " : "    ") + line;
          labelRuns.push({
            text,
            options: { fontSize: 7.5, color: fontColor, italic: true, breakLine: k < docLines.length - 1 }
          });
        });
      }
      s.addText(labelRuns, { x: r.x + 0.05, y: r.y + 0.03, w: r.w - 0.10, h: r.h - 0.06, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
      if (a.tag) {
        // Tag rendered as a small caps-styled annotation just outside the
        // cell, in the section accent color. Avoids overlap with adjacent
        // cells by placing it above for non-top lanes and below for the top.
        const isTopLane = a.lane === 0;
        const tagY = isTopLane ? r.y + r.h + 0.005 : r.y - 0.16;
        const tagColor = headerColor || C.TEXT_MUTED;
        s.addText(a.tag, {
          x: r.x, y: tagY, w: r.w, h: 0.14,
          fontSize: 7, color: tagColor, italic: false, bold: true,
          align: "center", fontFace: "Calibri", charSpacing: 1, margin: 0
        });
      }
    }
  });

  flows.forEach(flow => {
    const color = resolveColor(flow.color, C.GOLD);
    for (let i = 0; i < flow.path.length - 1; i++) {
      const [fl, fs] = flow.path[i];
      const [tl, ts] = flow.path[i + 1];
      drawArrow(s, fl, fs, tl, ts, cardRect, cardCenter, color, !!flow.bidir, flow.labels && flow.labels[i]);
    }
  });
}

// 4-direction arrow drawing — uses positive w/h with flipH/flipV.
function drawArrow(s, fl, fs, tl, ts, cardRect, cardCenter, color, bidir, label) {
  const fr = cardRect(fl, fs);
  const tr = cardRect(tl, ts);
  const fc = cardCenter(fl, fs);
  const tc = cardCenter(tl, ts);
  let x1, y1, x2, y2;
  if (fs === ts) {
    if (tl > fl) { x1 = fc.cx; y1 = fr.y + fr.h; x2 = tc.cx; y2 = tr.y; }
    else { x1 = fc.cx; y1 = fr.y; x2 = tc.cx; y2 = tr.y + tr.h; }
  } else if (fl === tl) {
    if (ts > fs) { x1 = fr.x + fr.w; y1 = fc.cy; x2 = tr.x; y2 = tc.cy; }
    else { x1 = fr.x; y1 = fc.cy; x2 = tr.x + tr.w; y2 = tc.cy; }
  } else {
    if (ts > fs) { x1 = fr.x + fr.w; y1 = fc.cy; x2 = tr.x; y2 = tc.cy; }
    else { x1 = fr.x; y1 = fc.cy; x2 = tr.x + tr.w; y2 = tc.cy; }
  }

  const xMin = Math.min(x1, x2);
  const yMin = Math.min(y1, y2);
  const w = Math.max(Math.abs(x2 - x1), 0.001);
  const h = Math.max(Math.abs(y2 - y1), 0.001);
  const flipH = x1 > x2;
  const flipV = y1 > y2;

  s.addShape("line", {
    x: xMin, y: yMin, w, h, flipH, flipV,
    line: {
      color, width: 0.9,                // thinner, more refined
      endArrowType: "triangle",
      beginArrowType: bidir ? "triangle" : "none"
    }
  });

  if (label) {
    const isVertical = Math.abs(x2 - x1) < 0.05;
    if (isVertical) {
      s.addText(label, {
        x: x1 + 0.04, y: (y1 + y2) / 2 - 0.08, w: 0.8, h: 0.16,
        fontSize: 7, italic: true, color, align: "left",
        fontFace: "Calibri", charSpacing: 0, margin: 0
      });
    } else {
      s.addText(label, {
        x: (x1 + x2) / 2 - 0.4, y: Math.min(y1, y2) - 0.18, w: 0.8, h: 0.16,
        fontSize: 7, italic: true, color, align: "center",
        fontFace: "Calibri", charSpacing: 0, margin: 0
      });
    }
  }
}

function buildStructureSlide(pres, st, page) {
  const s = pres.addSlide();
  s.background = { color: C.CREAM };
  const items = st.items || [];
  addSectionHeader(s, st.num || String(page - 5).padStart(2, "0"), st.title || "横軸の構造変化");
  s.addShape("rect", { x: 0.5, y: 1.4, w: 2.5, h: 0.5, fill: { color: C.NAVY }, line: { type: "none" } });
  s.addText("観点", { x: 0.5, y: 1.4, w: 2.5, h: 0.5, fontSize: 13, color: C.WHITE, bold: true, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
  s.addShape("rect", { x: 3.05, y: 1.4, w: 3.4, h: 0.5, fill: { color: C.RED, transparency: 30 }, line: { type: "none" } });
  s.addText("AS-IS", { x: 3.05, y: 1.4, w: 3.4, h: 0.5, fontSize: 13, color: C.WHITE, bold: true, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
  s.addShape("rect", { x: 6.5, y: 1.4, w: 3.0, h: 0.5, fill: { color: C.GREEN, transparency: 30 }, line: { type: "none" } });
  s.addText("TO-BE", { x: 6.5, y: 1.4, w: 3.0, h: 0.5, fontSize: 13, color: C.WHITE, bold: true, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });

  let yy = 1.95;
  const rowsAvail = items.length || 1;
  const rowH = Math.min(1.45, (5.30 - 1.95) / rowsAvail);
  items.forEach((it, i) => {
    if (i % 2 === 0) {
      s.addShape("rect", { x: 0.5, y: yy, w: 9, h: rowH, fill: { color: C.WHITE }, line: { color: C.BORDER, width: 1 } });
    } else {
      s.addShape("rect", { x: 0.5, y: yy, w: 9, h: rowH, fill: { color: C.ICE, transparency: 70 }, line: { color: C.BORDER, width: 1 } });
    }
    s.addText(it.label || "", { x: 0.5, y: yy, w: 2.5, h: rowH, fontSize: 14, color: C.NAVY, bold: true, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
    s.addText(it.asisStat || "", { x: 3.05, y: yy + 0.05, w: 3.4, h: 0.5, fontSize: 26, color: C.RED, bold: true, align: "center", fontFace: "Georgia", margin: 0 });
    s.addText(it.asis || "", { x: 3.15, y: yy + 0.6, w: 3.2, h: rowH - 0.65, fontSize: 9.5, color: C.SLATE, fontFace: "Calibri", margin: 0 });
    s.addText(it.tobeStat || "", { x: 6.5, y: yy + 0.05, w: 3.0, h: 0.5, fontSize: 26, color: C.GREEN, bold: true, align: "center", fontFace: "Georgia", margin: 0 });
    s.addText(it.tobe || "", { x: 6.6, y: yy + 0.6, w: 2.8, h: rowH - 0.65, fontSize: 9.5, color: C.SLATE, fontFace: "Calibri", margin: 0 });
    yy += rowH + 0.05;
  });
  addFooter(s, page);
}

function buildEndSummarySlide(pres, end, page) {
  const s = pres.addSlide();
  s.background = { color: C.NAVY_DK };
  s.addText(end.eyebrow || "SUMMARY", { x: 0.5, y: 0.6, w: 4, h: 0.4, fontSize: 13, color: C.GOLD, bold: true, charSpacing: 6, fontFace: "Arial", margin: 0 });
  s.addText(end.headline || "導入で何が起きるか", { x: 0.5, y: 1.0, w: 9, h: 0.8, fontSize: 36, color: C.WHITE, bold: true, fontFace: "Georgia", margin: 0 });
  s.addShape("rect", { x: 0.5, y: 1.85, w: 0.8, h: 0.04, fill: { color: C.GOLD }, line: { type: "none" } });
  const stats = (end.stats || []).slice(0, 3);
  const sn = stats.length;
  if (sn > 0) {
    const tw = 9 / sn - 0.15;
    stats.forEach((st, i) => {
      const sx = 0.5 + i * (tw + 0.15);
      s.addShape("rect", { x: sx, y: 2.3, w: tw, h: 1.95, fill: { color: C.NAVY }, line: { color: C.GOLD, width: 1 } });
      s.addShape("rect", { x: sx, y: 2.3, w: tw, h: 0.06, fill: { color: C.GOLD }, line: { type: "none" } });
      s.addText(st.num || "", { x: sx + 0.1, y: 2.45, w: tw - 0.2, h: 0.7, fontSize: 26, color: C.GOLD, bold: true, align: "center", fontFace: "Georgia", margin: 0 });
      s.addText(st.label || "", { x: sx + 0.1, y: 3.15, w: tw - 0.2, h: 0.35, fontSize: 12, color: C.WHITE, bold: true, align: "center", fontFace: "Calibri", charSpacing: 3, margin: 0 });
      s.addText(st.desc || "", { x: sx + 0.2, y: 3.55, w: tw - 0.4, h: 0.65, fontSize: 10, color: C.ICE, align: "center", fontFace: "Calibri", margin: 0 });
    });
  }
  if (end.closingBanner) {
    s.addShape("rect", { x: 0.5, y: 4.45, w: 9, h: 0.7, fill: { color: C.GOLD }, line: { type: "none" } });
    s.addText(end.closingBanner, { x: 0.5, y: 4.45, w: 9, h: 0.7, fontSize: 16, color: C.NAVY_DK, bold: true, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
  }
  if (end.footer) {
    s.addText(end.footer, { x: 0.5, y: 5.25, w: 9, h: 0.3, fontSize: 9, color: C.SLATE_LT, italic: true, align: "center", fontFace: "Calibri", margin: 0 });
  }
}

// =====================================================================
main().catch(e => { console.error(e); process.exit(1); });
