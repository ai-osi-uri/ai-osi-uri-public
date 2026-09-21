#!/usr/bin/env python3
"""型のノートから、題・結論・なぜ成り立つか・親の本質を抜き出して一覧にする（読むだけ）。
  python3 list_types.py --dir <型のフォルダ> [--max 400]
"""
import argparse, json, os, re, unicodedata
N = lambda s: unicodedata.normalize("NFC", s)

def section(t, name):
    m = re.search(r"^#+\s*" + name + r"[^\n]*\n(.*?)(?=^#+\s|\Z)", t, re.S | re.M)
    return m.group(1).strip() if m else ""

ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--max", type=int, default=400)
a = ap.parse_args(); out = []
for f in sorted(os.listdir(a.dir)):
    if not f.endswith(".md"): continue
    t = N(open(os.path.join(a.dir, f), encoding="utf-8").read())
    why = section(t, "なぜ成り立つか")
    parent = re.search(r"^本質：(.*)$", t, re.M)
    out.append({"題": N(f[:-3]), "結論": section(t, "結論")[:a.max], "なぜ": why[:a.max],
                "なぜが空": (why == "" or "語られていない" in why[:40]),
                "親": re.findall(r"\[\[([^\]|]+)", parent.group(1)) if parent else [],
                "字数": len(t)})
print(json.dumps({"本数": len(out), "なぜが空の本数": sum(x["なぜが空"] for x in out), "型": out}, ensure_ascii=False, indent=1))
