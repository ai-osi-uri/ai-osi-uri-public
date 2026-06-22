#!/usr/bin/env python3
"""支払管理台帳の行から、MF postJournals 形式の仕訳案を生成する。

入力: JSON 配列（ファイル引数 or 標準入力）。各行は台帳の1取引。
出力: 仕訳案の JSON 配列（標準出力）。各案は摘要(remark)に請求書ID/経費IDを必ず含む。

MF仕様に合わせ、消費税は税区分で自動計算される前提（仮払消費税の別行は作らない）。
費用行の金額は税込。借方合計(税込)＝貸方合計(振込額＋源泉)。
勘定科目ID・税区分ID・取引先コードは実行時に Claude がマスタ突合で解決する
（ここでは台帳上の名称をそのまま account/tax_class に入れる）。
"""
import sys, json

ACC_BANK = "普通預金"
ACC_WHT = "預り金"
SUB_WHT = "所得税"


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


def build(row):
    key = g(row, "id", "請求書ID", "経費ID", default="")
    partner = g(row, "partner", "取引先名", "支払先名", default="")
    account = g(row, "account", "勘定科目", default="")
    tax_class = g(row, "tax_class", "税区分", "税区分(MF)", default="")
    date = g(row, "date", "支払日", "発生日", default="")
    period = g(row, "period", "対象月", "発生月", default="")

    excl = yen(g(row, "excl", "金額(税抜)", "税抜", "報酬額(税抜)"))
    tax = yen(g(row, "tax", "消費税額", "消費税"))
    incl = yen(g(row, "incl", "金額(税込)", "税込", default=excl + tax))
    wht = yen(g(row, "withholding", "源泉徴収税額", "源泉"))
    net = yen(g(row, "net", "振込額", default=incl - wht))

    remark = " / ".join(x for x in [str(key), str(partner), str(period)] if x)

    branches = [
        {"debitor": {"account": account, "tax_class": tax_class,
                     "trade_partner": partner, "value": incl}},
        {"creditor": {"account": ACC_BANK, "value": net}},
    ]
    if wht > 0:
        branches.append({"creditor": {"account": ACC_WHT, "sub_account": SUB_WHT, "value": wht}})

    dtot = sum(b["debitor"]["value"] for b in branches if "debitor" in b)
    ctot = sum(b["creditor"]["value"] for b in branches if "creditor" in b)

    warnings = []
    if not key:
        warnings.append("請求書ID/経費IDが空（摘要・重複チェックに必須）")
    if not account:
        warnings.append("勘定科目が空（getAccountsで実在科目に要解決）")
    if dtot != ctot:
        warnings.append(f"借貸不一致 借{dtot}≠貸{ctot}")
    if incl and dtot != incl:
        warnings.append(f"税込と借方が不一致 {incl}≠{dtot}")

    return {
        "key": key,
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
    raw = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    out = [build(r) for r in data]
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()
    bad = sum(1 for o in out if not o["balanced"] or o["warnings"])
    if bad:
        sys.stderr.write(f"[warn] 要確認 {bad}/{len(out)} 件（warnings 参照）\n")


if __name__ == "__main__":
    main()
