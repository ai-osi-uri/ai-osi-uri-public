#!/usr/bin/env python3
"""ノートのフォルダに、知識の置き場の形を作る。既にあるものは上書きしない。

  python3 init_vault.py --root <ノートのフォルダ> --status   # いまの状態を見る
  python3 init_vault.py --root <ノートのフォルダ> --dry      # 何が作られるかだけ見る
  python3 init_vault.py --root <ノートのフォルダ>            # 作る
"""
import argparse, datetime, json, os, shutil, sys

DIRS = ["00_受け箱", "10_記録", "20_事例", "30_型", "40_本質", "50_人", "90_決まり/ひな形", "見本"]
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "..", "assets", "vault")


def status(root):
    out = {"root": root, "exists": os.path.isdir(root), "dirs": {}, "counts": {}, "has_rules": False, "other_top": []}
    if not out["exists"]:
        return out
    for d in DIRS:
        out["dirs"][d] = os.path.isdir(os.path.join(root, d))
    for d in ["10_記録", "20_事例", "30_型", "40_本質"]:
        p = os.path.join(root, d)
        out["counts"][d] = len([f for f in os.listdir(p) if f.endswith(".md")]) if os.path.isdir(p) else 0
    out["has_rules"] = os.path.exists(os.path.join(root, "90_決まり", "決まり.md"))
    known = {d.split("/")[0] for d in DIRS} | {"入口.md", ".obsidian"}
    out["other_top"] = sorted(x for x in os.listdir(root) if x not in known and not x.startswith("."))[:30]
    out["obsidian_opened"] = os.path.isdir(os.path.join(root, ".obsidian"))
    return out


def build(root, dry):
    created, skipped = [], []
    today = datetime.date.today().isoformat()
    for d in DIRS:
        p = os.path.join(root, d)
        if os.path.isdir(p):
            skipped.append(d + "/")
        else:
            created.append(d + "/")
            if not dry:
                os.makedirs(p, exist_ok=True)
    for base, _, files in os.walk(SEED):
        for f in files:
            src = os.path.join(base, f)
            rel = os.path.relpath(src, SEED)
            dst = os.path.join(root, rel)
            if os.path.exists(dst):
                skipped.append(rel)
                continue
            created.append(rel)
            if not dry:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                text = open(src, encoding="utf-8").read().replace("{{today}}", today)
                open(dst, "w", encoding="utf-8").write(text)
    return {"created": created, "skipped": skipped, "dry": dry}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(a.root))
    if a.status:
        print(json.dumps(status(root), ensure_ascii=False, indent=1)); sys.exit(0)
    if not os.path.isdir(root):
        print(json.dumps({"error": "フォルダがありません", "root": root}, ensure_ascii=False)); sys.exit(1)
    print(json.dumps(build(root, a.dry), ensure_ascii=False, indent=1))
