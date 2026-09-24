#!/usr/bin/env python3
"""請求書PDFの必須項目チェック（osi-finance-invoice / 手順5 送信ゲートの前段）

    python3 verify_invoice.py <PDF> --inv INV-2026-09-001 --total 220000 \
        --customer "株式会社サンプル" --reg T0000000000000

終了コード 0 = 合格（添付・送信してよい） / 1 = 不合格（**添付しない**）

見ているのは「適格請求書の記載事項」と「台帳との一致」、それと「テンプレートの埋め残し」。
見た目が問題なさそうでも、落ちたものを例外にしない。

埋め残しの検査を足した理由（2026-09-24）：導入手順どおりに進めると台帳「発行者設定」が
「（自社名を入力）」「（口座番号）」のまま残り、それが請求書に印字されても合格していた。
登録番号も T＋13桁 かどうかを見ていなかった。どちらも不合格にする。

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


REG_RE = re.compile(r"^T\d{13}$")

# テンプレート・settings 雛形の埋め残し。norm() 後（NFKC で全角括弧→半角、空白除去）の文字列に当てる。
PLACEHOLDER_PATTERNS = [
    (re.compile(r"\{\{[^}]*\}\}"), "{{ }} の差し込み変数"),
    (re.compile(r"\([^()]{0,40}(?:を入力|T\+13桁|例[:：])[^()]{0,40}\)"), "括弧書きの入力指示"),
    (re.compile(r"\((?:自社名|会社名|社名|銀行名|支店名|支店名・店番|口座番号|口座名義|預金種別|本店所在地|住所|郵便番号|登録番号)\)"),
     "括弧書きの項目名"),
    (re.compile(r"○○"), "○○"),
    (re.compile(r"T0{13}"), "ダミーの登録番号 T0000000000000"),
]


def placeholders(text: str):
    """埋め残しを [(見つかった文字列, 種類)] で返す。text は norm() 済みを渡す。"""
    hits = []
    for rx, kind in PLACEHOLDER_PATTERNS:
        for m in rx.finditer(text):
            hits.append((m.group(0), kind))
    return hits


def check_reg_format(reg: str):
    """登録番号の形式（T＋13桁）。合わなければ理由を返す。"""
    r = norm(reg)
    if not REG_RE.match(r):
        return f"登録番号 {reg!r} が T＋13桁 の形式ではない（settings / 発行者設定を直す）"
    if r == "T" + "0" * 13:
        return "登録番号がダミー（T0000000000000）のまま"
    return None


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
    bad = check_reg_format(a.reg)
    if bad:
        fails.append(bad)
    if norm(a.reg) not in t:
        fails.append(f"登録番号 {a.reg} が印字されていない")
    # 「登録番号」の横に印字された値の形式（行単位で読む。空白を詰めると後続の数字とつながるため）
    wrong = []
    for line in unicodedata.normalize("NFKC", raw).splitlines():
        for m in re.finditer(r"登録番号[ \t]*[:：]?[ \t]*([A-Za-z]?[0-9][0-9 \-]*)", line):
            v = re.sub(r"[ \-]", "", m.group(1))
            if not REG_RE.match(v):
                wrong.append(v)
    if wrong:
        fails.append(f"T＋13桁 でない登録番号らしき印字がある: {', '.join(wrong)}")
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

    # テンプレートの埋め残し（社名・口座が「（自社名を入力）」のまま出る事故）
    for s, kind in placeholders(t):
        fails.append(f"埋め残し（{kind}）: 『{s}』— 発行者設定／settings を埋めてから作り直す")

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
