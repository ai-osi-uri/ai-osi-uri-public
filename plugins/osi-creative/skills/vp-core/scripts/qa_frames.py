#!/usr/bin/env python3
# Copyright (c) 2026 FinShinjuku, MIT License, from threads-video-studio
# （移植元: threads-video-studio の scripts/qa_frames.py。プロジェクト構成・設定ファイルへの依存を外し、
#   動画ファイルの単体指定とフォルダ一括に一般化した。）
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
"""生成したクリップ・完成動画の「全コマ QA」。ffmpeg / ffprobe だけで動く（API は使わない）。

  python3 qa_frames.py --video clips/c01.mp4                 # 1本（0.25秒ごと＝4fps のコンタクトシート）
  python3 qa_frames.py --video c01.mp4 --video c02.mp4       # 複数本（並べた順につなぎ目の差も測る）
  python3 qa_frames.py --dir clips                           # フォルダ内の *.mp4 を名前順に一括
  python3 qa_frames.py --video final.mp4 --fps 2             # 完成動画は 0.5秒ごとで足りる

チェック
  freeze : ffmpeg の freezedetect（n=0.003, d=0.4）。0.4秒より長く止まった絵は死んで見える
  motion : 続けて抜き出したコマ同士の平均絶対差（0-1。ほぼ 0 = 動きなし）
  seams  : 前のクリップの最後のコマと次のクリップの最初のコマの平均絶対差（0-1）。
           普通のカット切り替えなら大きいのが普通。続きのショット（連鎖生成）で大きいと、跳びが目に見える。

出力: <out>/<名前>-sheet.jpg（コンタクトシート）と <out>/qa.json（数値）。要約を標準出力に出す。
<out> の既定は、--dir ならそのフォルダの qa/、--video なら最初の動画と同じフォルダの qa/。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

FREEZE_NOISE = 0.003
FREEZE_MIN = 0.4
SEAM_JUMP = 0.25
COLS = 8


# --- 小さな道具（移植元 common.py から必要な分だけ内包） -------------------------------------

def run(*cmd: str) -> str:
    r = subprocess.run(list(cmd), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} が失敗: {r.stderr.strip()[:400]}")
    return r.stdout.strip()


def duration(path: Path) -> float:
    return float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)))


def save_json(path: Path, data) -> None:
    """JSON を原子的に書く（UTF-8、日本語はエスケープしない）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# --- 解析と計算 --------------------------------------------------------------------------------

def parse_freezedetect(log: str, clip_duration: float | None = None) -> list[dict]:
    """ffmpeg freezedetect のログ行から静止区間を取り出す。終わりの無い区間はクリップの最後までとする。"""
    spans: list[dict] = []
    cur: dict | None = None
    for m in re.finditer(r"lavfi\.freezedetect\.freeze_(start|duration|end):\s*([0-9.]+)", log):
        kind, val = m.group(1), float(m.group(2))
        if kind == "start":
            cur = {"start": val, "end": None, "dur": None}
            spans.append(cur)
        elif cur is not None and kind == "duration":
            cur["dur"] = val
        elif cur is not None and kind == "end":
            cur["end"] = val
            if cur["dur"] is None:
                cur["dur"] = round(val - cur["start"], 3)
            cur = None
    for s in spans:
        if s["end"] is None:
            s["end"] = clip_duration
            s["dur"] = round(clip_duration - s["start"], 3) if clip_duration is not None else None
    return spans


def read_ppm(data: bytes) -> tuple[int, int, bytes]:
    """バイナリ PPM（P6、maxval 255）を読む。(幅, 高さ, RGB のバイト列) を返す。"""
    if not data.startswith(b"P6"):
        raise ValueError("P6 形式の PPM ではない")
    fields, pos = [], 2
    while len(fields) < 3:
        while data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b"#":
            pos = data.index(b"\n", pos) + 1
            continue
        start = pos
        while not data[pos:pos + 1].isspace():
            pos += 1
        fields.append(int(data[start:pos]))
    pos += 1  # maxval の後の空白1文字
    w, h, maxval = fields
    if maxval != 255:
        raise ValueError("maxval は 255 だけに対応")
    pix = data[pos:pos + w * h * 3]
    if len(pix) != w * h * 3:
        raise ValueError("PPM が途中で切れている")
    return w, h, pix


def mean_abs_diff(a: bytes, b: bytes) -> float:
    """バイトごとの平均絶対差（0-1 に正規化）。"""
    if len(a) != len(b) or not a:
        raise ValueError("2つのバッファは同じ大きさで、空でないこと")
    return sum(abs(x - y) for x, y in zip(a, b)) / (255.0 * len(a))


# --- ffmpeg ------------------------------------------------------------------------------------

def _ffmpeg_bytes(*args: str) -> bytes:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg が失敗した: {r.stderr.decode(errors='replace').strip()[:300]}")
    return r.stdout


def contact_sheet(video: Path, out: Path, fps: float, dur: float) -> None:
    rows = max(1, math.ceil(dur * fps / COLS))
    out.parent.mkdir(parents=True, exist_ok=True)
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
        "-vf", f"fps={fps},scale=240:-2,tile={COLS}x{rows}:padding=4:margin=4",
        "-frames:v", "1", "-q:v", "3", str(out))


def freeze_spans(video: Path, dur: float) -> list[dict]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-map", "0:v:0",
                        "-vf", f"freezedetect=n={FREEZE_NOISE}:d={FREEZE_MIN}", "-f", "null", "-"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"freezedetect が失敗した: {r.stderr.strip()[-300:]}")
    return parse_freezedetect(r.stderr, dur)


def motion_score(video: Path, fps: float) -> float | None:
    w, h = 64, 64
    raw = _ffmpeg_bytes("-i", str(video), "-vf", f"fps={fps},scale={w}:{h},format=gray",
                        "-f", "rawvideo", "-")
    n = len(raw) // (w * h)
    if n < 2:
        return None
    frames = [raw[i * w * h:(i + 1) * w * h] for i in range(n)]
    return round(sum(mean_abs_diff(frames[i], frames[i + 1]) for i in range(n - 1)) / (n - 1), 4)


def edge_frame(video: Path, last: bool, tmpdir: Path) -> bytes:
    # 縦横比の違う動画どうしでも比べられるよう、同じ大きさにそろえてから比べる
    out = tmpdir / ("last.ppm" if last else "first.ppm")
    pre = ["-sseof", "-0.5"] if last else []
    post = ["-update", "1"] if last else ["-frames:v", "1"]
    _ffmpeg_bytes("-y", *pre, "-i", str(video), "-vf", "scale=144:144", *post, "-c:v", "ppm", str(out))
    return read_ppm(out.read_bytes())[2]


def seam_diff(a: Path, b: Path) -> float:
    with tempfile.TemporaryDirectory() as d:
        return round(mean_abs_diff(edge_frame(a, True, Path(d)), edge_frame(b, False, Path(d))), 4)


# --- main --------------------------------------------------------------------------------------

def check_video(video: Path, name: str, qa_dir: Path, fps: float) -> dict:
    dur = duration(video)
    sheet = qa_dir / f"{name}-sheet.jpg"
    contact_sheet(video, sheet, fps, dur)
    spans = freeze_spans(video, dur)
    return {"file": str(video), "duration": round(dur, 3), "sheet": str(sheet), "fps": fps,
            "freeze_spans": spans, "flag_freeze": bool(spans), "motion": motion_score(video, fps)}


def summary(name: str, r: dict) -> str:
    s = f"{name}: {r['duration']:.2f}秒 動き {r['motion'] if r['motion'] is not None else '測定不可'}"
    if r["freeze_spans"]:
        spans = ", ".join(f"{x['start']:.2f}-{x['end']:.2f}s" if x["end"] is not None else f"{x['start']:.2f}s-"
                          for x in r["freeze_spans"])
        s += f"  静止(0.4秒超) {spans}"
    return s + f"  シート {Path(r['sheet']).name}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="動画のコンタクトシート（既定 0.25秒ごと）を作り、0.4秒超の静止・動きの量・つなぎ目の差を数値で出す。"
                    "ffmpeg / ffprobe が要る。")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--video", action="append", metavar="MP4",
                   help="確認する動画（複数回指定できる。2本以上なら指定した順につなぎ目も測る）")
    g.add_argument("--dir", metavar="DIR", help="このフォルダの *.mp4 を名前順に全部確認し、隣どうしのつなぎ目も測る")
    ap.add_argument("--fps", type=float, default=4.0, help="コマを抜き出す fps（既定 4＝0.25秒ごと。完成動画は 2 で足りる）")
    ap.add_argument("--out", metavar="DIR", help="シートと qa.json の書き出し先（既定は <対象フォルダ>/qa）")
    ap.add_argument("--no-seams", action="store_true", help="つなぎ目の差を測らない")
    a = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise RuntimeError(f"{tool} が見つからない。ffmpeg を入れてから実行する")

    if a.dir:
        base = Path(a.dir).expanduser()
        if not base.is_dir():
            raise FileNotFoundError(f"フォルダが無い: {base}")
        videos = sorted(p for p in base.glob("*.mp4") if p.is_file())
        if not videos:
            raise FileNotFoundError(f"{base} に *.mp4 が無い")
    else:
        videos = [Path(v).expanduser() for v in a.video]
        for v in videos:
            if not v.is_file():
                raise FileNotFoundError(f"動画が無い: {v}")
        base = videos[0].parent

    qa_dir = Path(a.out).expanduser() if a.out else base / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    qa_path = qa_dir / "qa.json"
    qa = load_json(qa_path)
    qa.setdefault("clips", {})
    lines: list[str] = []

    for v in videos:
        r = check_video(v, v.stem, qa_dir, a.fps)
        qa["clips"][v.stem] = r
        lines.append(summary(v.stem, r))

    if len(videos) > 1 and not a.no_seams:
        seams = []
        for x, y in zip(videos, videos[1:]):
            d = seam_diff(x, y)
            seams.append({"from": x.stem, "to": y.stem, "diff": d, "jump": d > SEAM_JUMP})
            lines.append(f"つなぎ目 {x.stem}->{y.stem}: 差 {d:.3f}" + (
                "  （大きい: 普通のカット切り替えなら問題なし、続きのショットなら跳んで見える）" if d > SEAM_JUMP else ""))
        qa["seams"] = seams

    qa["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save_json(qa_path, qa)
    for ln in lines:
        print(ln)
    print(f"書き出した: {qa_path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("エラー: 中断した", file=sys.stderr)
        sys.exit(130)
    except (RuntimeError, OSError, ValueError) as e:
        print(f"エラー: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
