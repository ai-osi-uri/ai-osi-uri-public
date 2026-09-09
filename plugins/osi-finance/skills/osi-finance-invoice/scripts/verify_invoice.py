#!/usr/bin/env python3
"""請求書PDFの必須項目チェック（osi-finance-invoice / 手順5 送信ゲートの前段）

    python3 verify_invoice.py <PDF> --inv INV-2026-09-001 --total 220000 \
        --customer "株式会社サンプル" --reg T0000000000000

終了コード 0 = 合格（添付・送信してよい） / 1 = 不合格（**添付しない**）

見ているのは「適格請求書の記載事項」と「台帳との一致」。
見た目が問題なさそうでも、落ちたものを例外にしない。

依存: pdftotext（poppler）。無ければ pypdf にフォールバック。
"""
import argparse
import re
import subprocess
import sys
import unicodedata


def extract(pdf: str) -> str:
    try:
        return subprocess.run(
            ["pdftotext", "-layout", pdf, "-"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        try:
            from pypdf import PdfReader
            return "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
        except Exception as e:  # noqa: BLE001
            sys.exit(f"FATAL: PDFからテキストを抽出できません: {e}")


def norm(s: str) -> str:
    return re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", s))


def yen_values(text: str):
    return {int(m.replace(",", "")) for m in re.findall(r"[\d][\d,]{2,}", text)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--inv", required=True, help="台帳の請求書番号")
    ap.add_argument("--total", required=True, type=int, help="台帳の請求額（税込）")
    ap.add_argument("--customer", required=True, help="取引先マスタの正式名称")
    ap.add_argument("--reg", required=True, help="発行者の登録番号（osi-finance-settings）")
    a = ap.parse_args()

    raw = extract(a.pdf)
    t = norm(raw)
    fails, warns = [], []

    # 適格請求書の記載事項
    if norm(a.reg) not in t:
        fails.append(f"登録番号 {a.reg} が印字されていない")
    if norm(a.customer) not in t:
        fails.append(f"宛名『{a.customer}』が印字されていない（改行で割れている可能性）")
    if not re.search(r"(10|8)%", t):
        fails.append("適用税率（10% / 8%）の記載がない")
    if "消費税" not in t:
        fails.append("税率ごとの消費税額の記載がない")

    # 台帳との一致
    if norm(a.inv) not in t:
        fails.append(f"請求書番号 {a.inv} が印字されていない（台帳と不一致）")
    if a.total not in yen_values(raw):
        fails.append(f"合計額 {a.total:,} 円が本文に見当たらない（台帳と不一致の疑い）")

    # 体裁・生成経路
    if "振込" not in t and "振替" not in t:
        warns.append("振込先の記載が見当たらない")
    if raw.count("�") or raw.count("□") > 2:
        fails.append("文字化けの疑い（□ / 置換文字を検出）— 非埋め込みフォントの可能性")
    try:
        if b"ReportLab" in open(a.pdf, "rb").read(4096):
            fails.append("reportlab で生成されている（禁止。render_invoice.py で作り直す）")
    except OSError:
        pass

    print(f"=== {a.pdf}")
    for w in warns:
        print(f"  [WARN] {w}")
    if fails:
        for f in fails:
            print(f"  [NG]   {f}")
        print("  => 不合格。Gmailに添付しない。")
        sys.exit(1)
    print("  => 合格。添付してよい。")


if __name__ == "__main__":
    main()
