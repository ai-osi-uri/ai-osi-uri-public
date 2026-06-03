# scripts/ 使い方

## make_subs.py

SRT字幕ジェネレータ。

### 入力ファイル例（scenes.json）

```json
[
  {
    "narration_duration": 11.42,
    "chunks": [
      "人の価値は、正しく評価されているでしょうか。",
      "組織を支える「見えない貢献」や、",
      "人と人の「つながり」は、",
      "今もなお、評価から外れたままです。"
    ]
  },
  {
    "narration_duration": 23.72,
    "chunks": [
      "今、世界は大きく動き始めています。",
      "..."
    ]
  }
]
```

### 実行

```bash
python3 make_subs.py scenes.json > subtitles.srt
```

### オプション

- `--video-dur 8` で標準動画尺を変更（デフォルト 8.0秒）

---

## build_video.sh

ffmpeg統合パイプライン。シーン合成→連結→BGMミックス→字幕焼き込みを一気に実行。

### 入力ファイル例（scenes.tsv）

タブ区切り。各行に1シーン分の情報：

```
01	/path/to/scene_01.mp4	8.00	/path/to/narration_01.mp3	11.42
02	/path/to/scene_02.mp4	5.04	/path/to/narration_02.mp3	23.72
03	/path/to/scene_03.mp4	8.00	/path/to/narration_03.mp3	26.41
...
```

カラム：
1. シーン番号（2桁ゼロ埋め）
2. 動画ファイルのフルパス
3. 動画の長さ（秒、ffprobeで計測）
4. ナレーションのフルパス
5. ナレーションの長さ

### 実行

```bash
# 環境変数
export WORK=/tmp/video_build
export FAL_OUTPUT_DIR=/path/to/output

# 字幕付き
bash build_video.sh scenes.tsv bgm.wav subtitles.srt

# 字幕なし
bash build_video.sh scenes.tsv bgm.wav
```

### 出力

`$FAL_OUTPUT_DIR` に：
- `composite_no_bgm.mp4` — BGMもなし
- `final_no_subs.mp4` — BGMあり字幕なし
- `final.mp4` — 全部入り（subtitles.srt 指定時のみ）

### 重要な注意

- **/tmp で全処理し、最後に cp**：Drive sync干渉によるファイル破損を防ぐため
- **長時間処理は nohup で BG 実行**：bash 45秒制限を回避
- **/tmp/fonts に Noto Sans JP TTF が自動DL**される（初回のみ）

---

## ヘルパー：ナレーション尺の計測

```bash
for f in narration_*.mp3; do
  d=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
  printf "%s: %.2fs\n" "$f" "$d"
done
```

## ヘルパー：動画尺の計測

```bash
for f in scene_*.mp4; do
  d=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
  printf "%s: %.2fs\n" "$f" "$d"
done
```

これらの結果を組み合わせて scenes.tsv を作る。
