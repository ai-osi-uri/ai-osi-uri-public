#!/usr/bin/env python3
"""台帳から請求書の data.json を作る（osi-finance-invoice / 発行元③ ローカル生成の前段）

    python3 make_invoice_data.py <経理フォルダ> --out-dir <作業フォルダ> [--month YYYY-MM]
    python3 make_invoice_data.py <経理フォルダ> --out-dir <作業フォルダ> --inv INV-2026-09-001      # 単票（採番済み）
    python3 make_invoice_data.py <経理フォルダ> --out-dir <作業フォルダ> --contract AR-C-001 --target 2026-08  # 単票（未採番）

何を拾うか（「今月の請求書を作って」の定義）
------------------------------------------
月次請求スケジュールのうち **請求月 = --month（既定は今月）かつ 請求ステータス = 未請求** の行。
請求月＝請求日の年月。請求日が空の行は「対象月の翌月」を請求月とみなす（既定の支払サイト）。
9月に実行すると、対象月8月分（請求日 9/1）の行が拾われ、番号は INV-2026-09-… になる。

やること（台帳には書かない。書くのは PDF が verify_invoice.py に合格したあと、ledger_io.py か拡張で）
----------------------------------------------------------------------------------------------
1. 行を「請求書番号」（採番済み）または「取引先ID × 請求月」（未採番）でまとめて1通にする（合算請求＝1請求書 N 行）。
2. 未採番のグループに番号を振る：INV-{請求月}-{その請求月の既存最大連番+1}（3桁）。振るだけで台帳には書かない。
3. 宛名は 契約マスタの取引先ID → 共通マスタ「取引先マスタ」の正式名称。無ければそのグループは作らない。
4. 発行者情報は「発行者設定」タブ → settings の順。必須が欠けていれば1通も作らず exit 1。
5. 送付請求書フォルダに同じ番号のPDFが既にあればそのグループは作らない（冪等）。
6. <out-dir>/<INV>.json を書き、計画（行番号・PDFの保存先）を JSON で出す。
7. 請求月が過去なのに未請求のまま残っている行は past_unbilled に並べる（黙って捨てない。--month でその月を指定して出す）。

終了コード: 0=作った（0件も含む） / 1=止めた（発行者情報の欠け・エラー）
"""
import argparse
import calendar
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent.parent.parent / "assets" / "scripts"
sys.path.insert(0, str(ASSETS))
sys.path.insert(0, str(HERE))
from ledger_io import Book, LedgerError, num  # noqa: E402
from fill_issuer_settings import ITEMS, is_placeholder, parse_settings, normalize  # noqa: E402

SENT_DIR = "02.送付請求書"
STATUS_OK = {"未請求"}


def ym_add(ym, k):
    y, m = map(int, ym.split("-"))
    m2 = m - 1 + k
    return f"{y + m2 // 12:04d}-{m2 % 12 + 1:02d}"


def billing_month(row):
    b = (row.get("請求日") or "").replace("/", "-")
    if re.match(r"^\d{4}-\d{2}", b):
        return b[:7]
    t = (row.get("対象月") or "").replace("/", "-")[:7]
    return ym_add(t, 1) if re.match(r"^\d{4}-\d{2}$", t) else ""


def jdate(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.year}年{d.month}月{d.day}日"


def safe(sname, n=24):
    return re.sub(r'[\\/:*?"<>|\s]+', "", sname)[:n]


def issuer(d):
    """発行者設定 → settings の順で値を取る。{項目: 値}"""
    tab = {}
    try:
        tab = {r.get("項目", ""): r.get("値", "") for r in Book(d, "発行者設定").rows()}
    except LedgerError:
        pass
    sp = d / "osi-finance-settings.md"
    conf = parse_settings(sp) if sp.exists() else {}
    out, missing, from_settings = {}, [], []
    for item, key, sec, label, required in ITEMS:
        v = tab.get(item, "")
        if is_placeholder(v):
            raw = conf.get((sec, label))
            if raw is not None and not is_placeholder(raw):
                v = normalize(item, raw)
                from_settings.append(item)
            else:
                v = ""
        out[item] = v
        if required and not v:
            missing.append(item)
    if out.get("登録番号") and not re.fullmatch(r"T\d{13}", out["登録番号"]):
        missing.append("登録番号（T＋13桁でない）")
    return out, missing, from_settings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ledger_dir")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--month", help="請求月 YYYY-MM（既定: 今月）")
    ap.add_argument("--inv")
    ap.add_argument("--contract")
    ap.add_argument("--target", help="--contract と組で対象月 YYYY-MM")
    a = ap.parse_args()
    d = Path(a.ledger_dir).expanduser()
    out_dir = Path(a.out_dir).expanduser()
    month = a.month or dt.date.today().strftime("%Y-%m")

    iss, missing, from_settings = issuer(d)
    if missing:
        print(json.dumps({"error": "発行者情報が未記入。1通も作らない（osi-finance-setup ステップ3-2 / fill_issuer_settings.py）",
                          "missing": missing}, ensure_ascii=False, indent=1))
        return 1

    sched = Book(d, "月次請求スケジュール").rows()
    contracts = {r["契約ID"]: r for r in Book(d, "契約マスタ").rows() if r.get("契約ID")}
    partners = {r["取引先ID"]: r for r in Book(d, "取引先マスタ").rows() if r.get("取引先ID")}

    if a.inv:
        rows = [r for r in sched if r.get("請求書番号") == a.inv]
        month = a.inv[4:11]
    elif a.contract:
        rows = [r for r in sched if r.get("契約ID") == a.contract and r.get("対象月", "").replace("/", "-")[:7] == a.target]
        month = billing_month(rows[0]) if rows else month
    else:
        rows = [r for r in sched if billing_month(r) == month]
    rows = [r for r in rows if (r.get("請求ステータス") or "") in STATUS_OK]
    # 請求月が過ぎたのに未請求のまま残っている行（月初の発火漏れなど）。黙って捨てず、別立てで知らせる
    past = [] if (a.inv or a.contract) else [
        {"row": r["__row"], "契約ID": r.get("契約ID", ""), "対象月": r.get("対象月", ""), "請求月": billing_month(r)}
        for r in sched if (r.get("請求ステータス") or "") in STATUS_OK and billing_month(r) and billing_month(r) < month]

    skipped, groups = [], {}
    for r in rows:
        c = contracts.get(r.get("契約ID", ""))
        if "記入例" in (r.get("取引先") or ""):
            skipped.append({"row": r["__row"], "reason": "記入例の行"})
            continue
        if not c or not c.get("取引先ID"):
            skipped.append({"row": r["__row"], "reason": "契約マスタに無い／取引先ID が空（宛名を引けない）"})
            continue
        inv = r.get("請求書番号", "")
        key = inv if inv and not inv.startswith("(") else ("未採番", c["取引先ID"])
        groups.setdefault(key, []).append((r, c))

    rx = re.compile(r"^INV-" + re.escape(month) + r"-(\d+)$")
    seq = max([int(m.group(1)) for r in sched for m in [rx.match(r.get("請求書番号", ""))] if m] or [0])
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = []
    for key, members in groups.items():
        c0 = members[0][1]
        p = partners.get(c0["取引先ID"])
        if not p or not p.get("正式名称"):
            skipped.append({"rows": [m[0]["__row"] for m in members], "reason": f"取引先マスタに {c0['取引先ID']} の正式名称が無い（止めて人に聞く）"})
            continue
        if isinstance(key, tuple):
            seq += 1
            inv = f"INV-{month}-{seq:03d}"
        else:
            inv = key
        if list((d / SENT_DIR / month).glob(f"{inv}_*.pdf")):
            skipped.append({"inv": inv, "reason": "同じ番号のPDFが送付請求書フォルダに既にある（冪等ガード）"})
            continue
        items, total = [], 0
        for r, c in members:
            incl = int(round(num(r.get("請求額(税込)"))))
            rate = int(re.sub(r"\D", "", c.get("税率") or iss.get("消費税率") or "10") or 10)
            price = int(round(incl / (1 + rate / 100)))
            items.append({"delivery_date": r.get("対象月", ""), "name": r.get("件名") or c.get("契約内容") or "業務委託",
                          "description": f"対象月 {r.get('対象月', '')}", "unit_price": price, "qty": 1, "unit": "式",
                          "tax_rate": rate})
            total += incl
        calc = sum(round(sum(i["unit_price"] for i in items if i["tax_rate"] == t) * (1 + t / 100))
                   for t in {i["tax_rate"] for i in items})
        bill = next((r.get("請求日") for r, _ in members if r.get("請求日")), f"{month}-01").replace("/", "-")[:10]
        y, m = map(int, month.split("-"))
        due = next((r.get("支払期限") for r, _ in members if r.get("支払期限")),
                   dt.date(y, m, calendar.monthrange(y, m)[1]).isoformat()).replace("/", "-")[:10]
        subject = items[0]["name"] + (" ほか" if len(items) > 1 else "")
        data = {
            "issuer_name": iss["発行者名義"], "issuer_reg_no": iss["登録番号"], "issuer_zip": iss["郵便番号"],
            "issuer_address": iss["住所"],
            "customer_name": p["正式名称"], "customer_honorific": "御中",
            "customer_zip": p.get("郵便番号", ""), "customer_address": p.get("住所", ""),
            "invoice_no": inv, "billing_date": jdate(bill), "due_date": jdate(due), "subject": subject, "items": items,
            "bank_name": iss["振込先 銀行"], "bank_branch": iss["振込先 支店"], "bank_account_type": iss["預金種別"],
            "bank_account_no": iss["口座番号"], "bank_account_holder": iss["口座名義"],
        }
        if p.get("請求先To"):
            data["customer_contact"] = f"{p['請求先To']} 様"
        if iss.get("振込手数料") and "当社" in iss["振込手数料"]:
            data["notes"] = "お振込手数料は当社にて負担いたします。"
        jpath = out_dir / f"{inv}.json"
        jpath.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        pdf_rel = f"{SENT_DIR}/{month}/{inv}_{safe(p['正式名称'])}_{safe(subject, 16)}.pdf"
        (d / pdf_rel).parent.mkdir(parents=True, exist_ok=True)  # 保存先は必ず経理フォルダ起点（ドライブ直下に作らない）
        plan.append({
            "inv": inv, "customer": p["正式名称"], "total": total, "to": p.get("Toアドレス", ""),
            "rows": [r["__row"] for r, _ in members], "targets": [r.get("対象月", "") for r, _ in members],
            "data_json": str(jpath), "pdf_rel": pdf_rel, "pdf_path": str(d / pdf_rel), "billing_date": bill, "due_date": due,
            "tax_check": "ok" if calc == total else f"税込 {total:,} と税抜単価からの再計算 {calc:,} が一致しない（端数。金額を確認）",
        })
    print(json.dumps({"month": month, "issuer_from_settings": from_settings, "invoices": plan, "skipped": skipped,
                      "past_unbilled": past},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
