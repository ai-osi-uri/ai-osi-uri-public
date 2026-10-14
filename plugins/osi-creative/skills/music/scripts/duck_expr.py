#!/usr/bin/env python3
# Copyright (c) 2026 FinShinjuku, MIT License, from threads-video-studio
# （移植元: threads-video-studio の scripts/assemble.py の duck_windows / duck_expr。
#   ナレ区間を音声ファイルの無音検出からも取れるようにし、単体の CLI にした。）
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
# OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""BGM をナレの区間だけ下げる（ダッキング）ための ffmpeg volume 式を出す。

  python3 duck_expr.py --windows "2.0-5.0,7.0-9.0"     # ナレの区間（秒）を手で渡す
  python3 duck_expr.py --from-audio narration.wav       # ナレ音声の無音検出から区間を取る（ffmpeg が要る）

出力は1行の式。BGM 側に次のように掛ける:
  ffmpeg -i bgm.mp3 -af "volume='pow(10,(<式>)/20)':eval=frame" bgm_ducked.wav

既定: ナレの間 -20dB、前後 0.1秒の余白、0.7秒より近い区間はまとめる（音楽が上下に揺れない）、
0.15秒で下げて 0.3秒で戻す。
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys


def parse_windows(text: str) -> list[tuple[float, float]]:
    out = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        s, e = (float(x) for x in part.split("-", 1))
        if e <= s:
            raise ValueError(f"区間の終わりが始まり以前: {part}")
        out.append((s, e))
    return out


def windows_from_audio(path: str, noise_db: float, min_silence: float) -> list[tuple[float, float]]:
    """silencedetect で無音区間を取り、その補集合＝声のある区間を返す。"""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg / ffprobe が見つからない")
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                 capture_output=True, text=True, check=True).stdout.strip())
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"silencedetect が失敗: {r.stderr.strip()[-300:]}")
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[0-9.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", r.stderr)]
    silences = []
    for i, s in enumerate(starts):
        silences.append((max(0.0, s), ends[i] if i < len(ends) else total))
    voiced, t = [], 0.0
    for s, e in silences:
        if s - t > 0.05:
            voiced.append((t, s))
        t = max(t, e)
    if total - t > 0.05:
        voiced.append((t, total))
    return voiced


def merge(wins: list[tuple[float, float]], pad: float, gap: float) -> list[list[float]]:
    merged: list[list[float]] = []
    for s, e in sorted(wins):
        s, e = max(0.0, s - pad), e + pad
        if merged and s - merged[-1][1] < gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


def duck_expr(wins: list[list[float]], duck_db: float, down: float = 0.15, up: float = 0.3) -> str:
    expr = "0"
    for s, e in reversed(wins):
        s0 = max(s - down, 0.0)
        ramp_down = f"{duck_db}*(t-{s0:.3f})/{max(s - s0, 1e-3):.3f}"
        expr = (f"if(between(t,{s0:.3f},{s:.3f}),{ramp_down},"
                f"if(between(t,{s:.3f},{e:.3f}),{duck_db},"
                f"if(between(t,{e:.3f},{e + up:.3f}),{duck_db}*(1-(t-{e:.3f})/{up}),{expr})))")
    return expr


def main() -> int:
    ap = argparse.ArgumentParser(description="ナレの区間だけ BGM を下げる ffmpeg volume 式を出す。")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--windows", help='ナレの区間。例 "2.0-5.0,7.0-9.0"（秒）')
    g.add_argument("--from-audio", metavar="FILE", help="ナレ音声（全体を1本にしたもの）。無音検出で区間を取る")
    ap.add_argument("--duck-db", type=float, default=-20.0, help="ナレの間に下げる量（dB。既定 -20）")
    ap.add_argument("--pad", type=float, default=0.1, help="区間の前後に足す余白（秒。既定 0.1）")
    ap.add_argument("--gap", type=float, default=0.7, help="これより近い区間はまとめる（秒。既定 0.7）")
    ap.add_argument("--noise-db", type=float, default=-35.0, help="--from-audio の無音とみなす音量（既定 -35dB）")
    ap.add_argument("--min-silence", type=float, default=0.3, help="--from-audio の無音とみなす最短の長さ（既定 0.3秒）")
    ap.add_argument("--show-windows", action="store_true", help="式の代わりに、まとめた後の区間を表示する")
    a = ap.parse_args()

    raw = parse_windows(a.windows) if a.windows else windows_from_audio(a.from_audio, a.noise_db, a.min_silence)
    wins = merge(raw, a.pad, a.gap)
    if a.show_windows:
        print(", ".join(f"{s:.2f}-{e:.2f}" for s, e in wins) or "（ナレの区間なし）")
    else:
        print(duck_expr(wins, a.duck_db))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as e:
        print(f"エラー: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
