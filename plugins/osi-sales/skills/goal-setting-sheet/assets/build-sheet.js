// 目標設定シート（Word）の雛形。node build-sheet.js sheet.json out.docx
// sheet.json の形は references/sheet-json.md を参照。
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, ShadingType, BorderStyle, LevelFormat, Header, Footer, PageNumber,
  VerticalAlign, TableLayoutType,
} = require("docx");

const FONT = "Yu Gothic";
const NAVY = "1F3A6E";      // 青寄りの濃紺（強調）
const INK = "222222";
const SUB = "555555";
const LINE = "C9D1DF";
const LABEL_BG = "EEF2F8";
const HEAD_BG = "1F3A6E";
const BLANK = "＿＿＿＿＿＿";

const W = 9638; // A4 本文幅（左右 20mm 余白）

// ---------- helpers ----------
const run = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || 21, bold: !!o.bold, color: o.color || INK });
const p = (children, o = {}) => new Paragraph({
  children: Array.isArray(children) ? children : [run(children, o)],
  spacing: { before: o.before ?? 0, after: o.after ?? 80, line: o.line || 320 },
  alignment: o.align,
  indent: o.indent,
  keepNext: o.keepNext,
});
// 「**強調**」を濃紺太字にする
const rich = (text, o = {}) => {
  const parts = text.split(/(\*\*[^*]+\*\*)/).filter(Boolean);
  return parts.map((t) => t.startsWith("**") ? run(t.slice(2, -2), { ...o, bold: true, color: NAVY }) : run(t, o));
};
const rp = (text, o = {}) => p(rich(text, o), o);
const bullet = (text, o = {}) => new Paragraph({
  children: rich(text, o), numbering: { reference: "dot", level: 0 },
  spacing: { after: o.after ?? 40, line: 300 },
});
const num = (text, ref = "num1") => new Paragraph({
  children: rich(text), numbering: { reference: ref, level: 0 }, spacing: { after: 60, line: 300 },
});

const border = { style: BorderStyle.SINGLE, size: 6, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
const cell = (children, width, o = {}) => new TableCell({
  children: Array.isArray(children) ? children : [p(children, o)],
  width: { size: width, type: WidthType.DXA },
  shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
  margins: { top: 90, bottom: 90, left: 140, right: 140 },
  verticalAlign: o.valign || VerticalAlign.TOP,
  borders,
  columnSpan: o.span,
});
const table = (widths, rows) => new Table({
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  columnWidths: widths, layout: TableLayoutType.FIXED, rows,
});
const headRow = (labels, widths) => new TableRow({
  tableHeader: true,
  children: labels.map((l, i) => cell([p([run(l, { bold: true, color: "FFFFFF" })], { after: 0 })], widths[i], { fill: HEAD_BG, valign: VerticalAlign.CENTER })),
});
const labelCell = (l, w) => cell([p([run(l, { bold: true, color: NAVY })], { after: 0 })], w, { fill: LABEL_BG });

// 見出し（章）
const h1 = (no, text) => new Paragraph({
  children: [run(`${no}　`, { bold: true, color: NAVY, size: 28 }), run(text, { bold: true, color: NAVY, size: 28 })],
  spacing: { before: 360, after: 140 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: NAVY, space: 4 } },
  keepNext: true,
});
const h2 = (text) => new Paragraph({
  children: [run(text, { bold: true, color: INK, size: 24 })],
  spacing: { before: 240, after: 100 }, keepNext: true,
});


// ---------- カード（元の形：左に項目・右に中身） ----------
const card = (tag, title, rows, o = {}) => {
  const wL = 2300, wR = W - wL;
  const trs = [
    new TableRow({ cantSplit: true, children: [cell([p([run(`${tag}　`, { bold: true, color: "FFFFFF", size: 22 }), run(title, { bold: true, color: "FFFFFF", size: 22 })], { after: 0 })], W, { fill: HEAD_BG, span: 2 })] }),
    ...rows.map(([label, body]) => new TableRow({
      cantSplit: true,
      children: [labelCell(label, wL), cell(body.map((b) => typeof b === "string" ? rp(b, { after: 40 }) : b), wR)],
    })),
  ];
  return [new Paragraph({ children: [], pageBreakBefore: !!o.newPage, spacing: { after: 120 } }), table([wL, wR], trs)];
};

const brk = () => new Paragraph({ children: [], pageBreakBefore: true, spacing: { after: 0 } });
const toCell = (b) => typeof b === "string" ? rp(b, { after: 40 }) : bullet(b.bullet);

const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const children = [];
children.push(
  p([run(`${data.client}　御中`, { bold: true, size: 24 })], { after: 200 }),
  p([run("AIコンシェルジュ", { bold: true, color: NAVY, size: 26 })], { after: 60, line: 400 }),
  p([run("目標設定シート", { bold: true, color: NAVY, size: 44 })], { after: 160, line: 640 }),
  rp(data.note, { after: 120 }),
);
data.sections.forEach((sec, i) => {
  children.push(h1(String(i + 1), sec.title));
  if (sec.lead) children.push(rp(sec.lead));
  (sec.bullets || []).forEach((b) => children.push(bullet(b)));
});
children.push(brk(), h1(String(data.sections.length + 1), "弊社のご提案"), rp(data.proposalLead));
data.proposals.forEach((pr, i) => {
  children.push(...card(`ご提案 ${i + 1}`, pr.title, pr.rows.map(([l, body]) => [l, body.map(toCell)]), { newPage: i > 0 }));
});
children.push(brk(), h2("ご提案するプラン"), rp(data.plan.lead));
children.push(...card("プラン", data.plan.name, data.plan.rows.map(([l, body]) => [l, body.map(toCell)])));
if (data.plan.note) children.push(h2(data.plan.note.title), rp(data.plan.note.body));

const doc = new Document({
  creator: data.author,
  title: `${data.client} AIコンシェルジュ 目標設定シート`,
  styles: { default: { document: { run: { font: FONT, size: 21, color: INK } } } },
  numbering: { config: [
    { reference: "dot", levels: [{ level: 0, format: LevelFormat.BULLET, text: "・", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [run(`${data.client}　AIコンシェルジュ 目標設定シート（下書き）`, { size: 16, color: SUB })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: SUB }), run(` ／ ${data.author}`, { size: 16, color: SUB })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[3], b); console.log("wrote", process.argv[3]); });
