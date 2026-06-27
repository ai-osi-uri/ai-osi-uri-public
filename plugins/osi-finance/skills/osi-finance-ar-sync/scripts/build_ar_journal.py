#!/usr/bin/env python3
"""請求管理台帳の行から、MF postJournals 形式の AR 仕訳案を生成する。

入力: JSON 配列（ファイル引数 or 標準入力）。各行は台帳の1請求。
  各行に "kind" を持たせる: "sale"（売上計上）/ "collection"（入金消込）。
  省略時は status（請求済→sale / 入金済→collection）から推定する。
出力: 仕訳案の JSON 配列（標準出力）。各案は摘要(remark)に請求書ID(INV-…)＋区分を必ず含む。

MF仕様に合わせ、消費税は税区分で自動計算される前提（仮受消費税の別行は作らない）。
売上行の金額は税込。借方合計(税込)＝貸方合計。
勘定科目ID・税区分ID・取引先コードは実行時に Claude がマスタ突合で解決する
（ここでは osi-finance-settings の AR 会計設定の名称をそのまま account/tax_class に入れる）。
売掛金科目・売上高科目・課税売上税区分・入金普通預金科目は osi-finance-settings から渡す。
"""
import sys, json

# osi-finance-settings の AR 会計設定（既定名称。実行時に実値で上書き可）
ACC_AR = "売掛金"        # AR_ACCOUNTS_RECEIVABLE
ACC_SALES = "売上高"      # AR_SALES_ACCOUNT
ACC_DEPOSIT = "普通預金"  # AR_DEPOSIT_ACCOUNT
TAX_SALES = "課税売上10%"  # AR_TAX_CLASS


def g(row, *aliases, default=None):
    for a in aliases:
        if a in row and row[a] not in (None, ""):
            return row[a]
    return default


def yen(v):
    if v in (None, ""):
        return 0
    if isinstance(v, (int, float)):
        return int(round(v))
    s = str(v).replace(",", "").replace("¥", "").replace("円", "").strip()
    if s in ("", "-"):
        return 0
    return int(round(float(s)))


def infer_kind(row):
    k = g(row, "kind", default="")
    if k:
        return k
    st = str(g(row, "status", "請求ステータス", "状態", default=""))
    if "入金" in st:
        return "collection"
    return "sale"


def build(row, settings):
    acc_ar = settings.get("ar_account", ACC_AR)
    acc_sales = settings.get("sales_account", ACC_SALES)
    acc_deposit = settings.get("deposit_account", ACC_DEPOSIT)
    tax_sales = settings.get("tax_class", TAX_SALES)

    key = g(row, "id", "請求書ID", "請求書番号", default="")
    partner = g(row, "partner", "取引先名", "請求先", "宛名", default="")
    period = g(row, "period", "対象月", default="")
    kind = infer_kind(row)

    incl = yen(g(row, "incl", "金額(税込)", "税込", "請求額", default=0))
    if not incl:
        excl = yen(g(row, "excl", "金額(税抜)", "税抜"))
        tax = yen(g(row, "tax", "消費税額", "消費税"))
        incl = excl + tax

    if kind == "collection":
        date = g(row, "collection_date", "入金日", "date", default="")
        amt = yen(g(row, "deposit", "入金額", default=incl))
        branches = [
            {"debitor": {"account": acc_deposit, "value": amt}},
            {"creditor": {"account": acc_ar, "value": amt}},
        ]
        kind_label = "入金消込"
    else:  # sale
        date = g(row, "sale_date", "計上日", "対象月末", "date", default="")
        amt = incl
        branches = [
            {"debitor": {"account": acc_ar, "value": amt}},
            {"creditor": {"account": acc_sales, "tax_class": tax_sales, "value": amt}},
        ]
        kind_label = "売上計上"

    remark = " / ".join(x for x in [str(key), str(partner), str(period), kind_label] if x)

    dtot = sum(b["debitor"]["value"] for b in branches if "debitor" in b)
    ctot = sum(b["creditor"]["value"] for b in branches if "creditor" in b)

    warnings = []
    if not key:
        warnings.append("請求書ID(INV-…)が空（摘要・重複チェックに必須）")
    if amt <= 0:
        warnings.append("金額が0以下（台帳の請求額/入金額を確認）")
    if dtot != ctot:
        warnings.append(f"借貸不一致 借{dtot}≠貸{ctot}")

    return {
        "key": key,
        "kind": kind,
        "kind_label": kind_label,
        "transaction_date": date,
        "remark": remark,
        "partner": partner,
        "journal_type": "journal_entry",
        "branches": branches,
        "debit_total": dtot,
        "credit_total": ctot,
        "balanced": dtot == ctot and dtot > 0,
        "warnings": warnings,
        "_note": "account/tax_class/trade_partner は実行時に account_id/tax_id/trade_partner_code へ解決する",
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    raw = open(args[0], encoding="utf-8").read() if args else sys.stdin.read()
    data = json.loads(raw)
    settings = {}
    if isinstance(data, dict) and "rows" in data:
        settings = data.get("settings", {}) or {}
        data = data["rows"]
    if isinstance(data, dict):
        data = [data]
    out = [build(r, settings) for r in data]
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()
    bad = sum(1 for o in out if not o["balanced"] or o["warnings"])
    if bad:
        sys.stderr.write(f"[warn] 要確認 {bad}/{len(out)} 件（warnings 参照）\n")


if __name__ == "__main__":
    main()
