#!/usr/bin/env python3
"""伏せて比べるための道具。
  組む: python3 blind.py assemble --answers <答えのフォルダ> --questions <問い.json> --out <比べる資料.md> --key <対応表.json>
        答えのフォルダの形:  <やり方の名前>/<問いの番号>.txt   （本文だけ）
        問い.json の形:      {"1": "相談の文面", "2": "..."}
  数える: python3 blind.py tally --key <対応表.json> --ranks <順位.json>
        順位.json の形:      {"採点者の名前": {"1": "B>A>C", "2": "..."}}   （ラベルで書く）
"""
import argparse, json, os, random, string, sys

def assemble(a):
    qs = json.load(open(a.questions, encoding="utf-8"))
    arms = sorted(d for d in os.listdir(a.answers) if os.path.isdir(os.path.join(a.answers, d)))
    if len(arms) < 2: sys.exit("やり方が二つ以上要ります")
    rnd = random.Random(a.seed); key = {}; out = ["# 答え比べ\n\nどの答えがどのやり方かは伏せてある。先に自分で順位を付けてから、対応表を見る。\n"]
    for q in sorted(qs, key=lambda x: int(x)):
        order = arms[:]; rnd.shuffle(order); labels = list(string.ascii_uppercase[:len(order)])
        key[q] = dict(zip(labels, order))
        out.append(f"---\n\n## 相談{q}\n\n{qs[q]}\n")
        for lab, arm in zip(labels, order):
            p = os.path.join(a.answers, arm, f"{q}.txt")
            if not os.path.exists(p): sys.exit(f"答えがありません: {p}")
            out.append(f"### {q}-{lab}\n\n{open(p, encoding='utf-8').read().strip()}\n")
    open(a.out, "w", encoding="utf-8").write("\n".join(out))
    json.dump(key, open(a.key, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"問い": len(qs), "やり方": arms, "資料": a.out, "対応表": a.key}, ensure_ascii=False))

def tally(a):
    key = json.load(open(a.key, encoding="utf-8")); ranks = json.load(open(a.ranks, encoding="utf-8"))
    tot, first, n, per_q = {}, {}, {}, {}
    for judge, rs in ranks.items():
        for q, line in rs.items():
            labs = [x.strip() for x in line.split(">")]
            for i, lab in enumerate(labs, 1):
                arm = key[q][lab]; tot[arm] = tot.get(arm, 0) + i; n[arm] = n.get(arm, 0) + 1
                if i == 1: first[arm] = first.get(arm, 0) + 1
            per_q.setdefault(q, {})[judge] = ">".join(key[q][l] for l in labs)
    res = {arm: {"順位の平均": round(tot[arm] / n[arm], 2), "1位の数": first.get(arm, 0), "のべ": n[arm]} for arm in tot}
    print(json.dumps({"やり方ごと": dict(sorted(res.items(), key=lambda x: x[1]["順位の平均"])), "相談ごと": per_q}, ensure_ascii=False, indent=1))

ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("assemble"); s.add_argument("--answers", required=True); s.add_argument("--questions", required=True); s.add_argument("--out", required=True); s.add_argument("--key", required=True); s.add_argument("--seed", type=int, default=None)
s = sub.add_parser("tally"); s.add_argument("--key", required=True); s.add_argument("--ranks", required=True)
a = ap.parse_args(); assemble(a) if a.cmd == "assemble" else tally(a)
