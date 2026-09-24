#!/usr/bin/env python3
"""請求管理台帳「発行者設定」タブを osi-finance-settings.md の値で埋める（osi-finance-setup ステップ3）

使い方:
    python3 fill_issuer_settings.py <台帳フォルダ>                     # 台帳フォルダ直下の settings を読む
    python3 fill_issuer_settings.py <台帳フォルダ> --settings <path>   # settings の場所を指定
    python3 fill_issuer_settings.py <請求管理台帳.xlsx> --settings <path>
    オプション: --dry-run（書かずに差分だけ） / --overwrite（台帳に入っている別の値も settings で上書き）

終了コード: 0=必須項目がすべて埋まった / 2=settings が未記入の必須項目が残った / 1=エラー（書いていない）

なぜこれがあるか
----------------
osi-finance-invoice は発行者情報を「発行者設定」タブから最優先で読む。setup の手順にこのタブを埋める
ステップが無かったため、手順どおりに導入すると請求書の社名・口座が「（自社名を入力）」のまま出た
（別環境で実際に起きた）。settings が正本、タブはコンソールと invoice のための写し。

守ること
--------
* 口座番号・登録番号などの値は画面に出さない（「記入」「未記入」だけを出す）。
* 書く前にバックアップを取る。Excel で開かれている（~$ ロックファイルがある）ときは書かない。
* 台帳に既に本物の値が入っていて settings と違うときは、--overwrite が無ければ上書きせず報告する。
"""
import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl が必要です: pip3 install openpyxl")

SETTINGS_NAME = "osi-finance-settings.md"
DEFAULT_LEDGER = "請求管理台帳.xlsx"
TAB = "発行者設定"

# 発行者設定の項目 → settings の (節番号, 表の左列) と 表示名。data-layout.yaml 発行者設定 items と同じ並び
ITEMS = [
    # (項目, settings キー, 節, 表の左列, 必須)
    ("発行者名義", "ISSUER_NAME", "1", "発行者名義", True),
    ("登録番号", "ISSUER_INVOICE_REG_NO", "1", "インボイス登録番号", True),
    ("郵便番号", "ISSUER_POSTAL_CODE", "1", "郵便番号", True),
    ("住所", "ISSUER_ADDRESS", "1", "住所", True),
    ("振込先 銀行", "BANK_NAME", "2", "銀行", True),
    ("振込先 支店", "BANK_BRANCH", "2", "支店", True),
    ("預金種別", "ACCOUNT_TYPE", "2", "預金種別", True),
    ("口座番号", "ACCOUNT_NUMBER", "2", "口座番号", True),
    ("口座名義", "ACCOUNT_HOLDER", "2", "口座名義", True),
    ("振込手数料", "TRANSFER_FEE_BEARER", "2", "振込手数料", False),
    ("消費税率", "CONSUMPTION_TAX_RATE", "3", "標準消費税率", False),
    ("採番ルール", "AR_NUMBERING", "4", "AR（送付請求書番号）", False),
    ("支払サイト", "AR_PAYMENT_TERMS", "4", "支払サイト（AR）", False),
    ("電子署名", "ESIGN", "0-2", "ESIGN", False),
    ("会計SaaS", "ACCOUNTING_SYNC", "0-2", "ACCOUNTING_SYNC", False),
    ("銀行明細突合", "BANK_RECON", "0-2", "BANK_RECON", False),
    ("金額区分", "BILLING_PATTERNS", "4-4", "BILLING_PATTERNS", False),
    ("前受の有効期限", "PREPAID_TERM_MONTHS", "4-4", "PREPAID_TERM_MONTHS", False),
    ("失効前通知", "PREPAID_NOTICE_DAYS", "4-4", "PREPAID_NOTICE_DAYS", False),
]
SECRET = {"登録番号", "口座番号", "口座名義"}
# 連携トグルと金額区分は settings が正本で、タブは写し。台帳側の値に関係なく settings に揃える
SYNC_ALWAYS = {"電子署名", "会計SaaS", "銀行明細突合", "金額区分", "前受の有効期限", "失効前通知"}
# テンプレートの既定値。これが入っているだけなら「未設定」と同じく settings で埋めてよい
TEMPLATE_DEFAULTS = {"消費税率": "10%", "採番ルール": "INV-YYYY-MM-連番3桁"}
REG_RE = re.compile(r"^T\d{13}$")


def is_placeholder(v):
    """空欄・テンプレートの括弧書き・{{ }} を「未設定」とみなす（invoice / verify_invoice と同じ判定）"""
    s = str(v if v is not None else "").strip()
    if not s:
        return True
    if "{{" in s or "}}" in s or "○○" in s or "選択:" in s:
        return True
    if s in ("T0000000000000", "000-0000", "0000000"):
        return True
    if re.fullmatch(r"[（(].*[）)]", s):  # 「（自社名を入力）」「（口座番号）」など
        return True
    return False


def clean(v):
    s = str(v).strip()
    s = re.sub(r"^\*\*(.*)\*\*$", r"\1", s).strip()
    return s.strip("`").strip()


def parse_settings(path):
    """{(節, 左列): 値} を返す。節は `## 1.` `## 0-2.` の番号。"""
    out, sec = {}, ""
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+([\d]+(?:-[\d]+)*)\.", line)
        if m:
            sec = m.group(1)
            continue
        if not line.lstrip().startswith("|"):
            continue
        cells = [clean(c) for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        out.setdefault((sec, cells[0]), cells[1])
    return out


def normalize(item, v):
    s = clean(v)
    if item == "電子署名":
        return {"docusign": "docusign", "none": "なし", "なし": "なし"}.get(s.lower(), s)
    if item == "会計SaaS":
        return {"mf": "mf", "freee": "freee", "none": "なし", "なし": "なし"}.get(s.lower(), s)
    if item == "銀行明細突合":
        return s.upper() if s.upper() in ("ON", "OFF") else s
    if item == "前受の有効期限" and re.fullmatch(r"\d+", s):
        return f"{s}ヶ月"
    if item == "失効前通知" and re.fullmatch(r"\d+", s):
        return f"{s}日"
    if item == "登録番号":
        return re.sub(r"[\s‐－-]", "", s).replace("Ｔ", "T")
    return s


def ledger_name_from_settings(conf):
    for (sec, key), v in conf.items():
        if sec == "6" and key.startswith("請求管理台帳") and not is_placeholder(v):
            v = clean(v)
            return v if v.lower().endswith(".xlsx") else v + ".xlsx"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ledger", help="台帳フォルダ、または請求管理台帳の xlsx")
    ap.add_argument("--settings", help=f"{SETTINGS_NAME} のパス（省略時は台帳フォルダ直下）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--backup-dir", help="バックアップ先（既定: 台帳フォルダ/_backup）")
    a = ap.parse_args()

    target = Path(a.ledger).expanduser()
    base = target if target.is_dir() else target.parent
    spath = Path(a.settings).expanduser() if a.settings else base / SETTINGS_NAME
    if not spath.exists():
        print(f"✗ settings がありません: {spath}（osi-finance-setup ステップ1で作る）")
        return 1
    conf = parse_settings(spath)
    xlsx = target if target.is_file() else base / (ledger_name_from_settings(conf) or DEFAULT_LEDGER)
    if not xlsx.exists():
        print(f"✗ 請求管理台帳がありません: {xlsx}")
        return 1
    if (xlsx.parent / f"~${xlsx.name}").exists():
        print(f"✗ {xlsx.name} が Excel で開かれています（~$ ロックファイルあり）。閉じてから再実行してください")
        return 1

    wb = openpyxl.load_workbook(xlsx)
    if TAB not in wb.sheetnames:
        print(f"✗ {xlsx.name} に「{TAB}」タブがありません（テンプレートから作り直すか、タブを足す）")
        return 1
    ws = wb[TAB]
    hdr = [str(c.value or "").strip() for c in ws[1]]
    if "項目" not in hdr or "値" not in hdr:
        print(f"✗ 「{TAB}」の1行目に 項目／値 の見出しがありません")
        return 1
    ck, cv = hdr.index("項目") + 1, hdr.index("値") + 1
    cn = hdr.index("備考") + 1 if "備考" in hdr else None
    rows = {}
    last = 1
    for r in range(2, ws.max_row + 1):
        k = str(ws.cell(row=r, column=ck).value or "").strip()
        if k:
            rows.setdefault(k, r)
            last = r

    changes, kept, missing, errors = [], [], [], []
    for item, key, sec, label, required in ITEMS:
        raw = conf.get((sec, label))
        if raw is None:  # 表の左列にキー名そのものを書いた settings も受ける
            raw = next((v for (s, k), v in conf.items() if k == key), None)
        new = None if raw is None or is_placeholder(raw) else normalize(item, raw)
        if item == "登録番号" and new and not REG_RE.match(new):
            errors.append(f"登録番号が T＋13桁 の形式ではありません（settings の {key} を直す）")
            new = None
        r = rows.get(item)
        cur = ws.cell(row=r, column=cv).value if r else None
        if new is None:
            if required and is_placeholder(cur):
                missing.append(f"{item}（settings の {key}）")
            continue
        protected = item not in SYNC_ALWAYS and str(cur or "").strip() != TEMPLATE_DEFAULTS.get(item)
        if r and protected and not is_placeholder(cur) and str(cur).strip() != new:
            if not a.overwrite:
                kept.append(item)
                continue
        if r and str(cur or "").strip() == new:
            continue
        if not r:
            last += 1
            r = last
            ws.cell(row=r, column=ck, value=item)
            if cn:
                ws.cell(row=r, column=cn, value=f"settings の {key} から記入")
            rows[item] = r
        ws.cell(row=r, column=cv, value=new)
        changes.append(item)

    shown = lambda it: f"{it}（値は非表示）" if it in SECRET else it  # noqa: E731
    for e in errors:
        print(f"✗ {e}")
    for it in changes:
        print(f"{'（dry-run）' if a.dry_run else ''}記入: {shown(it)}")
    for it in kept:
        print(f"! 台帳の値が settings と違うため上書きしなかった: {shown(it)}（--overwrite で settings に揃える）")
    for it in missing:
        print(f"✗ 未記入（必須）: {it}")

    if changes and not a.dry_run:
        bdir = Path(a.backup_dir).expanduser() if a.backup_dir else xlsx.parent / "_backup"
        bdir.mkdir(parents=True, exist_ok=True)
        bak = bdir / f"{xlsx.stem}_{dt.datetime.now():%Y%m%d-%H%M%S}.xlsx"
        shutil.copy2(xlsx, bak)
        wb.save(xlsx)
        print(f"保存: {xlsx.name}（バックアップ: {bak}）")
    elif not changes:
        print("変更なし")

    if errors:
        return 1
    return 2 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
