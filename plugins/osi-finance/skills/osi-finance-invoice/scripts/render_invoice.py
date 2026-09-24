#!/usr/bin/env python3
"""固定テンプレートから請求書PDFを生成する（osi-finance-invoice / 発行元③ ローカル生成）

    python3 render_invoice.py <data.json> <out.pdf>

原則:
  - 雛形は ../references/invoice-template.html の1本だけ。案件ごとに複製・手直ししない。
  - 生成器は weasyprint に固定。**reportlab は使わない**
    （非埋め込みCIDフォントで英数字・金額が □ 化して読めなくなる）。
  - 生成後は必ず verify_invoice.py を通す。exit 1 なら Gmail に添付しない。

依存: jinja2, weasyprint, Noto Sans CJK JP

data.json の形（必須キー）:
{
  "issuer_name": "...", "issuer_reg_no": "T…", "issuer_zip": "...", "issuer_address": "...",
  "issuer_rep": "代表取締役　…",                     # 任意
  "customer_name": "...", "customer_honorific": "御中",
  "customer_contact": "… 様",                        # 任意（無ければ会社名宛）
  "invoice_no": "INV-YYYY-MM-001",
  "billing_date": "YYYY年M月D日", "due_date": "YYYY年M月D日",
  "subject": "件名",
  "items": [{"delivery_date": "YYYY/MM/DD", "name": "...", "description": "...",
             "unit_price": 200000, "qty": 1, "unit": "式", "tax_rate": 10}],
  "bank_name": "...", "bank_branch": "...", "bank_account_type": "普通",
  "bank_account_no": "...", "bank_account_holder": "..."
}
税率ごとの小計・消費税額・合計は items から自動計算する（適格請求書の必須記載事項）。

生成の前に data.json を検査し、次のどれかがあれば**作らずに exit 1** で止める：
  - 発行者・振込先の必須キーが空
  - 「（自社名を入力）」「（口座番号）」「{{ }}」などテンプレートの埋め残し
  - issuer_reg_no が T＋13桁 でない
台帳「発行者設定」が未記入のまま流れてきたときに、社名・口座の無い請求書を作らないため。
"""
import json
import pathlib
import sys

from jinja2 import Environment, FileSystemLoader

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE_DIR = HERE.parent / "references"
TEMPLATE_NAME = "invoice-template.html"


def yen(v):
    try:
        return f"￥{int(round(float(v))):,}"
    except (TypeError, ValueError):
        return v


def build_tax_summary(items):
    """税率ごとに区分した対価の額と消費税額（適格請求書の必須記載事項）"""
    buckets = {}
    for it in items:
        rate = int(it.get("tax_rate", 10))
        buckets[rate] = buckets.get(rate, 0) + int(it["amount"])
    return [
        {"rate": r, "taxable": buckets[r], "tax": int(round(buckets[r] * r / 100))}
        for r in sorted(buckets, reverse=True)
    ]


REQUIRED = ["issuer_name", "issuer_reg_no", "issuer_zip", "issuer_address", "customer_name", "invoice_no",
            "billing_date", "due_date", "bank_name", "bank_branch", "bank_account_type",
            "bank_account_no", "bank_account_holder"]


def precheck(data):
    """埋め残し・形式の検査。問題を文字列の list で返す（verify_invoice.py と同じ判定を使う）。"""
    sys.path.insert(0, str(HERE))
    from verify_invoice import check_reg_format, norm, placeholders

    probs = [f"{k} が空" for k in REQUIRED if not str(data.get(k) or "").strip()]
    if str(data.get("issuer_reg_no") or "").strip():
        bad = check_reg_format(str(data["issuer_reg_no"]))
        if bad:
            probs.append(bad)
    for k, v in data.items():
        if isinstance(v, str):
            for s, kind in placeholders(norm(v)):
                probs.append(f"{k} に埋め残し（{kind}）: {s}")
    return probs


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)

    data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    probs = precheck(data)
    if probs:
        for p in probs:
            print(f"[NG] {p}")
        sys.exit("=> 生成しない。台帳「発行者設定」または osi-finance-settings.md を埋めてから作り直す。")

    items = data["items"]
    for it in items:
        it.setdefault("qty", 1)
        it.setdefault("unit", "式")
        it.setdefault("tax_rate", 10)
        it.setdefault("amount", int(it["unit_price"]) * int(it["qty"]))

    summary = build_tax_summary(items)
    data["tax_summary"] = summary
    data["total_excl"] = sum(s["taxable"] for s in summary)
    data["total_tax"] = sum(s["tax"] for s in summary)
    data["total_incl"] = data["total_excl"] + data["total_tax"]
    data["has_reduced"] = any(int(i.get("tax_rate", 10)) == 8 for i in items)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    env.filters["yen"] = yen
    html = env.get_template(TEMPLATE_NAME).render(**data)

    from weasyprint import HTML  # 遅延 import（未導入時のエラーを分かりやすく）

    HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf(sys.argv[2])
    print(f"{sys.argv[2]}  合計(税込)={data['total_incl']:,}")
    print("次に verify_invoice.py を通すこと。落ちたら添付しない。")


if __name__ == "__main__":
    main()
