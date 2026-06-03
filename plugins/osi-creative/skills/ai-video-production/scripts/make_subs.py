#!/usr/bin/env python3
"""
SRT字幕ジェネレータ（汎用）

入力：scenes.json（シーン定義）
出力：subtitles.srt（タイミング付き字幕）

各シーンの narration_duration をベースに、
chunks（字幕分割テキスト）を文字数比例でタイミング配分する。

使い方：
    python3 make_subs.py scenes.json > subtitles.srt

scenes.json フォーマット：
    [
      {
        "narration_duration": 11.42,
        "chunks": [
          "人の価値は、正しく評価されているでしょうか。",
          "組織を支える「見えない貢献」や、",
          "..."
        ]
      },
      ...
    ]

ターゲット duration（動画への合成時間）：
    target = max(narration_duration, video_duration) + 0.3秒
    ※ video_duration はスクリプト外で決まる前提（標準8s）
"""

import json
import sys
from typing import List, Tuple


def fmt_time(t: float) -> str:
    """SRT形式のタイムスタンプ：HH:MM:SS,mmm"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')


def generate_srt(
    scenes: List[dict],
    video_duration: float = 8.0,
    buffer: float = 0.3,
) -> str:
    """
    SRT文字列を生成。

    各シーンの target_duration = max(narration_duration, video_duration) + buffer
    chunks の dur 配分は、各 chunk の文字数比例。
    """
    starts = [0.0]
    for sc in scenes:
        narr = sc["narration_duration"]
        target = max(narr, video_duration) + buffer
        starts.append(starts[-1] + target)

    entries = []
    idx = 1
    for i, sc in enumerate(scenes):
        chunks = sc["chunks"]
        narr = sc["narration_duration"]
        total_chars = sum(len(c) for c in chunks)
        cur = starts[i]
        for chunk in chunks:
            ratio = len(chunk) / total_chars
            dur = narr * ratio
            entries.append(
                f"{idx}\n{fmt_time(cur)} --> {fmt_time(cur + dur)}\n{chunk}\n"
            )
            idx += 1
            cur += dur

    return "\n".join(entries) + "\n"


def main():
    if len(sys.argv) < 2:
        print("Usage: make_subs.py scenes.json [--video-dur 8] > subtitles.srt", file=sys.stderr)
        sys.exit(1)
    scenes_path = sys.argv[1]
    video_dur = 8.0
    if "--video-dur" in sys.argv:
        idx = sys.argv.index("--video-dur")
        video_dur = float(sys.argv[idx + 1])

    with open(scenes_path, encoding="utf-8") as f:
        scenes = json.load(f)

    print(generate_srt(scenes, video_duration=video_dur))


if __name__ == "__main__":
    main()
