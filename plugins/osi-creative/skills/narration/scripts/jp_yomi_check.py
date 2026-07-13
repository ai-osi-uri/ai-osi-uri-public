#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jp_yomi_check.py — 日本語ナレ原稿の読みチェック & ElevenLabs 発音辞書(.pls)生成
=============================================================================
案B（G2P前処理）の中核。pyopenjtalk で読みを機械推定し、誤読しやすい箇所を自動検出。
既知の正読み辞書(CSV)と突き合わせて ElevenLabs Pronunciation Dictionary(.pls) を出力する。

【思想】ナレ原稿そのものは壊さない（クリーンな漢字かな混じりのまま＝字幕と共用）。
読みの補正は「外部辞書(.pls)」に外出しし、案件横断で蓄積・再利用する。
これにより v1〜v24 の手作業ハック（デエタ／々（ふりがな）等）を機械化・資産化する。

使い方:
  python3 jp_yomi_check.py narration.txt \
      --glossary dict-company.csv \
      --out-pls  dict-company.pls \
      --report   review.md

引数:
  narration.txt         クリーンなナレ原稿（[calm] 等の感情タグ行も可。タグは無視して解析）
  --glossary  CSV       既知の正読み辞書: surface,yomi[,ipa]  （社名・製品名・人名 等）
  --out-pls   PATH      生成する ElevenLabs 発音辞書(.pls XML)
  --report    PATH      人が確認する読みレビュー(Markdown)
  --merge-common PATH   共通辞書(dict-common.pls)を取り込んでマージ（任意）

依存: pip install pyopenjtalk
"""
import sys, os, re, csv, argparse, html
from xml.sax.saxutils import escape

try:
    import pyopenjtalk
except ImportError:
    sys.stderr.write("ERROR: pyopenjtalk が必要です。 pip install pyopenjtalk\n")
    sys.exit(2)

# --- カタカナ→ひらがな（aliasはかなで書く方が安定） ---
def kata2hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)

EMOTION_TAG = re.compile(r"^\s*\[[^\]]+\]\s*")           # 行頭の感情タグ [calm] など
ASCII_WORD  = re.compile(r"[A-Za-z][A-Za-z0-9]*")        # 英字トークン（英字読み化しやすい）
HAS_KANJI   = re.compile(r"[一-鿿]")

def load_glossary(path):
    """surface,yomi[,ipa] の CSV を読む。空・コメント(#)行は無視。"""
    gloss = {}
    if not path or not os.path.exists(path):
        return gloss
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or row[0].strip().startswith("#"):
                continue
            surface = row[0].strip()
            yomi = row[1].strip() if len(row) > 1 else ""
            ipa = row[2].strip() if len(row) > 2 else ""
            if surface:
                gloss[surface] = {"yomi": yomi, "ipa": ipa}
    return gloss

def analyze(text):
    """pyopenjtalk で per-word 解析。誤読しやすい箇所を flag 付きで返す。"""
    feats = pyopenjtalk.run_frontend(text)
    if isinstance(feats, tuple):   # バージョン差吸収
        feats = feats[0]
    rows = []
    for f in feats:
        surface = f.get("string", "") or f.get("orig", "")
        read = f.get("read", "")
        pos = f.get("pos", "")
        flags = []
        # 1) 英字 → アルファベット読み化（OKWEB→オーケーダブリューイービー）
        if ASCII_WORD.search(surface):
            flags.append("英字読み")
        # 2) 固有名詞 → 読みが独自判定されがち（要正読み確認）
        if "固有名詞" in pos:
            flags.append("固有名詞")
        # 3) 漢字を含む名詞 → 同音異義/複数読みの可能性（glossaryで上書き候補）
        if HAS_KANJI.search(surface) and "名詞" in pos:
            flags.append("漢字読み")
        # 4) 読み不明（pyopenjtalkが読めず surface=read）
        if read in ("", "＊", "*"):
            flags.append("読み不明")
        rows.append({"surface": surface, "read": read, "pos": pos, "flags": flags})
    return rows

def build_rules(text, gloss):
    """
    辞書ルールを組む。
    - glossary に載っている surface はそのまま alias(かな) / phoneme(IPA) ルール化
    - 英字トークンは glossary 優先、無ければ「要レビュー」に積む
    返り値: (rules, need_review)
      rules = [{"grapheme":..,"type":"alias"/"phoneme","value":..,"alphabet":"ipa"?}]
    """
    rules = []
    seen = set()
    need_review = []

    # 4-1) glossary を最優先で登録（surfaceが本文に出現するものだけ）
    for surface, info in gloss.items():
        if surface in seen or surface not in text:
            continue
        if info.get("ipa"):
            rules.append({"grapheme": surface, "type": "phoneme",
                          "value": info["ipa"], "alphabet": "ipa"})
        elif info.get("yomi"):
            rules.append({"grapheme": surface, "type": "alias",
                          "value": kata2hira(info["yomi"])})
        seen.add(surface)

    # 4-2) 本文の英字トークンで glossary 未登録のものを「要レビュー」に
    for m in ASCII_WORD.finditer(text):
        tok = m.group(0)
        if tok in seen:
            continue
        need_review.append({"surface": tok, "reason": "英字（アルファベット読み化の恐れ）",
                            "guess": pyopenjtalk.g2p(tok, kana=True)})
        seen.add(tok)

    # 4-3) 固有名詞で glossary 未登録のものも「要レビュー」に
    for r in analyze(text):
        if "固有名詞" in r["flags"] and r["surface"] not in seen:
            need_review.append({"surface": r["surface"], "reason": "固有名詞（読み要確認）",
                                "guess": r["read"]})
            seen.add(r["surface"])

    return rules, need_review

PLS_HEADER = ('<?xml version="1.0" encoding="UTF-8"?>\n'
              '<lexicon version="1.0"\n'
              '         xmlns="http://www.w3.org/2005/01/pronunciation-lexicon"\n'
              '         alphabet="ipa" xml:lang="ja-JP">\n')
PLS_FOOTER = "</lexicon>\n"

def write_pls(rules, path):
    """ElevenLabs Pronunciation Dictionary(.pls / PLS XML)を出力。"""
    out = [PLS_HEADER]
    for r in rules:
        g = escape(r["grapheme"])
        if r["type"] == "phoneme":
            out.append(f'  <lexeme>\n    <grapheme>{g}</grapheme>\n'
                       f'    <phoneme>{escape(r["value"])}</phoneme>\n  </lexeme>\n')
        else:  # alias
            out.append(f'  <lexeme>\n    <grapheme>{g}</grapheme>\n'
                       f'    <alias>{escape(r["value"])}</alias>\n  </lexeme>\n')
    out.append(PLS_FOOTER)
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(out))

def write_report(text, rows_by_line, rules, need_review, path):
    L = ["# ナレ原稿 読みレビュー（jp_yomi_check）\n",
         "ナレ原稿は壊しません。下記の推定読みを確認し、誤読は glossary CSV に正読みを追記して再実行してください。\n"]
    L.append("\n## 1. 行ごとの推定読み\n")
    for i, (line, rows) in enumerate(rows_by_line, 1):
        kana = "".join(r["read"] for r in rows)
        L.append(f"\n**L{i}** `{line}`\n\n→ 推定読み: {kana}\n")
        # ⚠は actionable な flag のみ（漢字読みは推定読み行で目視できるので除外しノイズを抑制）
        actionable = {"英字読み", "固有名詞", "読み不明"}
        flagged = [f'{r["surface"]}→{r["read"]}({"/".join(r["flags"])})'
                   for r in rows if actionable & set(r["flags"])]
        if flagged:
            L.append("\n  - ⚠ 要注意: " + " 、 ".join(flagged) + "\n")
    L.append("\n## 2. 自動生成した辞書ルール（.pls に出力済み）\n")
    if rules:
        for r in rules:
            kind = "IPA音素" if r["type"] == "phoneme" else "別読み(alias)"
            L.append(f"- `{r['surface' if 'surface' in r else 'grapheme']}` → {r['value']}（{kind}）\n")
    else:
        L.append("（glossary 該当なし。CSV に正読みを追記すると自動生成されます）\n")
    L.append("\n## 3. 要レビュー（辞書未登録・誤読の恐れ）\n")
    if need_review:
        L.append("\n| 表記 | 推定読み | 理由 | 対応 |\n|---|---|---|---|\n")
        for n in need_review:
            L.append(f"| {n['surface']} | {n['guess']} | {n['reason']} | glossary に正読み追記 |\n")
    else:
        L.append("なし。\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(L))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("textfile")
    ap.add_argument("--glossary", default=None)
    ap.add_argument("--out-pls", default="pronunciation.pls")
    ap.add_argument("--report", default="review.md")
    args = ap.parse_args()

    with open(args.textfile, encoding="utf-8") as f:
        raw_lines = [EMOTION_TAG.sub("", ln.rstrip("\n")) for ln in f]
    raw_lines = [ln for ln in raw_lines if ln.strip()]
    full = "".join(raw_lines)

    gloss = load_glossary(args.glossary)
    rows_by_line = [(ln, analyze(ln)) for ln in raw_lines]
    rules, need_review = build_rules(full, gloss)
    # rules に surface を持たせて report 用に
    for r in rules:
        r["surface"] = r["grapheme"]

    write_pls(rules, args.out_pls)
    write_report(full, rows_by_line, rules, need_review, args.report)
    print(f"[OK] {len(rules)} 辞書ルール → {args.out_pls}")
    print(f"[OK] レビュー → {args.report}  （要レビュー {len(need_review)} 件）")

if __name__ == "__main__":
    main()
