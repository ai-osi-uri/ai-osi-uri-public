#!/usr/bin/env python3
"""osi-finance-settings.md を、setup の質問の答えと osi-profile.md から生成する（osi-finance-setup ステップ1）

使い方:
    python3 make_settings.py --profile <連結フォルダ>/osi-profile.md --answers answers.json [--dry-run]
    python3 make_settings.py --profile ... --answers ... --out <経理フォルダ>/osi-finance-settings.md

    --answers を省くと、すべて既定値で作る（あとでファイルを直せばよい）。
    出力先の既定は <osi-profile.md のあるフォルダ>/<paths.finance>/osi-finance-settings.md。

answers.json（setup が普通の言葉で聞いた答えを入れる。無いキーは既定値）:
    {
      "accounting":   "mf" | "freee" | "none",      # 会計ソフト（マネーフォワード／freee／使っていない）
      "invoice_tool": "mf" | "freee" | "none",      # 請求書を作っているソフト（無ければ同梱の雛形で作る）
      "confirm_before_write": true | false,         # 台帳に書く前に毎回確認するか
      "mail": "gmail" | "outlook" | "none",         # 請求書を送るメール
      "read_only": false,                           # 見るだけの導入か（経営者・税理士向け）
      "esign": false,                               # 電子署名（DocuSign）を使うか
      "bank_csv": false,                            # 銀行の明細CSVで入金を確かめるか
      "operator": "",                               # 台帳の作成者・更新者に入れる名前（任意）
      "members": ["山田太郎"]                       # レシートを出す人（任意）
    }

守ること
--------
* 既にある osi-finance-settings.md は上書きしない（exit 1）。直したいときは人がファイルを直す。
* 機微値（インボイス登録番号・口座）は空欄で出す。本人がファイルに書く。この道具は受け取らない。
* 雛形（config/osi-finance-settings.example.md）の「例」の行（支払先マッピング・定期支払先など）は空にして出す。
  例の社名や ○○ が残ると、本物の設定と区別できない。
* 出力に `{{` や `○○` が残ったら書かずに止める（雛形が変わったのに道具が追いついていない印）。

終了コード: 0=作った（dry-run なら作れる） / 1=作らなかった（既存・エラー）
最後の行に JSON 1 行（path / blanks_for_person / defaults_used）を出す。
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML が必要です: pip3 install pyyaml")

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent.parent
EXAMPLE = PLUGIN / "config" / "osi-finance-settings.example.md"
SETTINGS_NAME = "osi-finance-settings.md"

# 本人がファイルに書く値（道具は受け取らない・空欄で出す）
SENSITIVE = ["ISSUER_INVOICE_REG_NO", "BANK_NAME", "BANK_BRANCH", "ACCOUNT_TYPE", "ACCOUNT_NUMBER", "ACCOUNT_HOLDER"]
SENSITIVE_LABEL = {"ISSUER_INVOICE_REG_NO": "§1 インボイス登録番号（T＋13桁）", "BANK_NAME": "§2 銀行",
                   "BANK_BRANCH": "§2 支店", "ACCOUNT_TYPE": "§2 預金種別", "ACCOUNT_NUMBER": "§2 口座番号",
                   "ACCOUNT_HOLDER": "§2 口座名義"}
# §7 の表（例の行だけの表）は空行で出す
EXAMPLE_ONLY_SECTIONS = ("7-1.", "7-2.", "7-3.")


def unfilled(v):
    s = str(v if v is not None else "").strip()
    return not s or "{{" in s or "○○" in s


def load_profile(path):
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    data = yaml.safe_load(m.group(1) if m else text) or {}
    return data


def build_values(profile, ans, finance_rel):
    company = profile.get("company") or {}
    g = lambda k: "" if unfilled(company.get(k)) else str(company.get(k)).strip()  # noqa: E731
    acc = str(ans.get("accounting") or "none").lower()
    acc = acc if acc in ("mf", "freee", "none") else "none"
    tool = str(ans.get("invoice_tool") or "none").lower()
    engine = {"mf": "mf", "freee": "freee"}.get(tool, "local")
    mail = str(ans.get("mail") or "gmail").lower()
    members = ans.get("members") or []
    fin = finance_rel.rstrip("/") or "."
    return {
        "OPERATION_MODE": "参照専用" if ans.get("read_only") else "編集可",
        "GMAIL_INTAKE": "OFF" if mail == "none" else "ON",
        "ACCOUNTING_SYNC": acc,
        "BANK_RECON": "ON" if ans.get("bank_csv") else "OFF",
        "ESIGN": "docusign" if ans.get("esign") else "none",
        "INVOICE_ENGINE": engine,
        "AUTO_SEND": "OFF",
        "OPERATOR_EMAIL": str(ans.get("operator") or ""),
        "AUDIT_LOG": "off",
        "WRITE_CONFIRMATION": "事後確認" if ans.get("confirm_before_write") is False else "事前確認",
        "AUTO_POST_ROUTINE": "off",
        "ISSUER_NAME": g("name"),
        "ISSUER_POSTAL_CODE": g("postal_code"),
        "ISSUER_ADDRESS": g("address"),
        "TRANSFER_FEE_BEARER": "お客様負担",
        "CONSUMPTION_TAX_RATE": "10%",
        "AR_NUMBERING": "INV-YYYY-MM-連番3桁",
        "AP_PAYEE_ID_FORMAT": "V-連番3桁",
        "PARTNER_ID_FORMAT": "P-連番3桁",
        "CONTRACT_ID_FORMAT": "AR-C-連番3桁（受注）／AP-C-連番3桁（発注）",
        "AR_PAYMENT_TERMS": "月末締め翌月末払い（請求日=対象月翌月1日／支払期限=翌月末）",
        "BILLING_PATTERNS": "月額固定=monthly; 一括=lump; 都度=variable",
        "PREPAID_TERM_MONTHS": "",
        "PREPAID_NOTICE_DAYS": "",
        "PARTNER_MASTER_LOCATION": "共通マスタ.xlsx の「取引先マスタ」タブ（経理フォルダ）",
        "PARTNER_ID_SPACE": "P-連番3桁（顧客・支払先で共通。1社1ID）",
        "AR_SALES_ACCOUNT": "売上高",
        "AR_OUTPUT_TAX_ACCOUNT": "仮受消費税",
        "AR_ACCOUNTS_RECEIVABLE": "売掛金",
        "AR_TAX_CLASS": "課税売上 10%",
        "AR_DEPOSIT_ACCOUNT": "普通預金",
        "AR_BANK_LINK_HANDLING": "台帳から消込",
        "DRIVE_ROOT_LOCATION": f"経理フォルダ（{fin}）",
        "DRIVE_BILLING_ROOT": fin,
        "DRIVE_CONTRACTS": "00.契約書",
        "DRIVE_RECEIVED_INVOICES": "01.受領請求書",
        "DRIVE_SENT_INVOICES": "02.送付請求書",
        "DRIVE_EXPENSE_ROOT": f"{fin}/03.経費管理",
        "DRIVE_CARD_SAAS_EVIDENCE": "カードSaaS証憑",
        "LEDGER_BILLING_FILE": "請求管理台帳.xlsx",
        "LEDGER_PAYMENT_FILE": "支払管理台帳.xlsx",
        "LEDGER_JOURNAL_FILE": "仕訳台帳.xlsx",
        "DRIVE_RECEIPT_INBOX": f"{fin}/03.経費管理/レシート未処理/{{氏名}}",
        "DRIVE_RECEIPT_EVIDENCE": f"{fin}/03.経費管理/レシート証憑/{{YYYY年度}}/{{氏名}}",
        "MEMBERS": ", ".join(members),
        "PERSON_CARD_MAP": "",
        "CASH_ACCOUNT": "現金",
        "EMPLOYEE_PAYABLE_ACCOUNT": "未払金（従業員立替）",
        "SMALL_AMOUNT_SPECIAL": "",
        "EBOOK_RECORDKEEPING_RULE": "",
        "CARD_FEED_SOURCE": "",
        **{k: "" for k in SENSITIVE},
    }


def key_of_cell(cell, row_cells, vals):
    """セル中の {{KEY …}} の KEY。無ければ同じ行の他のセルに出てくる既知のキー。"""
    m = re.search(r"\{\{\s*([A-Z][A-Z0-9_]+)", cell)
    if m and m.group(1) in vals:
        return m.group(1)
    for c in row_cells:
        for k in re.findall(r"\b([A-Z][A-Z0-9_]{3,})\b", c):
            if k in vals:
                return k
    return None


def render(example_text, vals, finance_rel):
    out, sec, blanked = [], "", set()
    unknown = []
    for line in example_text.splitlines():
        h = re.match(r"^#{2,3}\s+([\d]+(?:-[\d]+)*\.)", line)
        if h:
            sec = h.group(1)
        if line.lstrip().startswith("|") and "{{" in line:
            cells = line.strip().strip("|").split("|")
            if sec.startswith(EXAMPLE_ONLY_SECTIONS):
                if sec not in blanked:  # 例の行は消し、空の行を1つだけ残す
                    out.append("|" + "|".join(" " for _ in cells) + "|")
                    blanked.add(sec)
                continue
            new = []
            for c in cells:
                if "{{" in c:
                    k = key_of_cell(c, cells, vals)
                    if k is None:
                        unknown.append(c.strip())
                        new.append(" ")
                    else:
                        new.append(f" {vals[k]} " if vals[k] else " ")
                else:
                    new.append(c)
            out.append("|" + "|".join(new) + "|")
            continue
        if sec.startswith(EXAMPLE_ONLY_SECTIONS) and line.lstrip().startswith("| …"):
            continue
        out.append(line)
    text = "\n".join(out) + "\n"
    text = text.replace("{{paths.finance}}", finance_rel)
    text = text.replace("{{DRIVE_EXPENSE_ROOT}}", vals["DRIVE_EXPENSE_ROOT"])
    text = text.replace("{{DRIVE_CARD_SAAS_EVIDENCE}}", vals["DRIVE_CARD_SAAS_EVIDENCE"])
    return text, unknown


HEADER = """# osi-finance-settings（{name}）

`make_settings.py` が {today} に生成した実値版。**このファイルはコミットしない。**
値を変えたら `python3 assets/scripts/fill_issuer_settings.py <経理フォルダ>` で台帳「発行者設定」に写し直す。

> **本人が書く欄（空欄で出している）**：{blanks}。
> 口座番号・登録番号はチャットに貼らず、このファイルを開いて直接書く。
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True, help="osi-profile.md のパス")
    ap.add_argument("--answers", help="setup の答え（JSON ファイル）。省略時は既定値")
    ap.add_argument("--out", help=f"出力先（既定: <profile のフォルダ>/<paths.finance>/{SETTINGS_NAME}）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    ppath = Path(a.profile).expanduser()
    if not ppath.exists():
        print(f"✗ osi-profile.md がありません: {ppath}（osi-core の getting-started で先に作る）")
        return 1
    profile = load_profile(ppath)
    ans = json.loads(Path(a.answers).expanduser().read_text(encoding="utf-8")) if a.answers else {}
    finance_rel = str(((profile.get("paths") or {}).get("finance")) or "経理")
    if unfilled(finance_rel):
        finance_rel = "経理"
    out = Path(a.out).expanduser() if a.out else ppath.parent / finance_rel / SETTINGS_NAME
    if out.exists():
        print(f"✗ 既にあります（上書きしない）: {out}")
        return 1

    vals = build_values(profile, ans, finance_rel)
    body, unknown = render(EXAMPLE.read_text(encoding="utf-8"), vals, finance_rel)
    # 雛形の冒頭（配布用の説明）を実値版の見出しに差し替える
    body = body.split("\n---\n", 1)[1] if "\n---\n" in body else body
    blanks = [SENSITIVE_LABEL[k] for k in SENSITIVE if not vals[k]]
    for k, label in (("ISSUER_NAME", "§1 発行者名義"), ("ISSUER_POSTAL_CODE", "§1 郵便番号"), ("ISSUER_ADDRESS", "§1 住所")):
        if not vals[k]:
            blanks.insert(0, label + "（osi-profile.md に無かった）")
    name = vals["ISSUER_NAME"] or "自社"
    text = HEADER.format(name=name, today=dt.date.today().isoformat(), blanks="、".join(blanks) or "なし") + "\n---\n" + body

    left = [m for m in re.findall(r"\{\{[^\n]*?\}\}", text)]
    if unknown or left or "○○" in text:
        print("✗ 雛形に道具の知らない差し込みが残った（make_settings.py を雛形に合わせて直す）")
        for u in unknown + left:
            print(f"    {u}")
        if "○○" in text:
            print("    ○○ が残っている")
        return 1

    defaults = sorted(k for k in vals if k not in ans and vals[k])
    result = {"path": str(out), "dry_run": a.dry_run, "blanks_for_person": blanks, "defaults_used": len(defaults)}
    if a.dry_run:
        print(f"（dry-run）作成予定: {out}")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"作成: {out}")
    for b in blanks:
        print(f"  本人が書く: {b}")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
