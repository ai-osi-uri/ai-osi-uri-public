#!/bin/bash
# 動画ビルドパイプライン
#
# 入力：scenes.tsv（タブ区切り、各行：scene_index<TAB>video_file<TAB>video_dur<TAB>narration_file<TAB>narration_dur）
#       bgm_file（必須、wav/mp3）
#       srt_file（オプション、字幕焼き込み用）
# 出力：composite_no_bgm.mp4 / final_no_subs.mp4 / final.mp4
#
# 環境変数：
#   WORK         作業ディレクトリ（デフォルト /tmp/video_build）
#   FONTS_DIR    日本語フォントのディレクトリ（デフォルト /tmp/fonts）
#   FAL_OUTPUT_DIR  最終ファイルの転送先（デフォルト ./fal-outputs）
#
# 使い方：
#   bash build_video.sh scenes.tsv bgm.wav subtitles.srt
#
# 注意：
#   - すべての ffmpeg 出力は /tmp で行い、最後に cp で FAL_OUTPUT_DIR にコピー
#     （Drive 直接書き込みは sync 干渉でファイル破損する）
#   - 長時間処理は nohup でバックグラウンド実行
#   - 字幕焼き込み時に /tmp/fonts に Noto Sans JP TTF が必要

set -e

SCENES_TSV="${1:?Usage: build_video.sh scenes.tsv bgm.wav [subtitles.srt]}"
BGM="${2:?BGM file required}"
SRT="${3:-}"

WORK="${WORK:-/tmp/video_build}"
FONTS_DIR="${FONTS_DIR:-/tmp/fonts}"
OUT_DIR="${FAL_OUTPUT_DIR:-./fal-outputs}"

mkdir -p "$WORK" "$OUT_DIR"

# ────────────────────────────────────────────────────
# 0. 日本語フォント確認・取得
# ────────────────────────────────────────────────────
if [ -n "$SRT" ] && [ ! -f "$FONTS_DIR/NotoSansJP-Regular.ttf" ]; then
    echo "=== Fetching Noto Sans JP ==="
    mkdir -p "$FONTS_DIR"
    curl -sSL -A "Mozilla/5.0" -o "$FONTS_DIR/NotoSansJP-Regular.ttf" \
      "https://fonts.gstatic.com/s/notosansjp/v56/-F6jfjtqLzI2JPCgQBnw7HFyzSD-AsregP8VFBEj75s.ttf"
    curl -sSL -A "Mozilla/5.0" -o "$FONTS_DIR/NotoSansJP-Bold.ttf" \
      "https://fonts.gstatic.com/s/notosansjp/v56/-F6jfjtqLzI2JPCgQBnw7HFyzSD-AsregP8VFPYk75s.ttf"
fi

# ────────────────────────────────────────────────────
# 1. シーン別合成（動画＋ナレ、PTS伸縮）
# ────────────────────────────────────────────────────
echo "=== Phase 1: Per-scene composition ==="

# scenes.tsv 例：
#   01<TAB>scene_01.mp4<TAB>8.00<TAB>narration_01.mp3<TAB>11.42
#   02<TAB>scene_02.mp4<TAB>5.04<TAB>narration_02.mp3<TAB>23.72
while IFS=$'\t' read -r idx vfile vdur afile adur; do
  [ -z "$idx" ] && continue
  target=$(awk -v n="$adur" -v vd="$vdur" 'BEGIN{ if(n<vd) n=vd; printf "%.3f", n+0.3 }')
  pts=$(awk -v t="$target" -v vd="$vdur" 'BEGIN{ printf "%.4f", t/vd }')
  out="$WORK/scene_${idx}.mp4"
  echo ">> scene $idx: TARGET=${target}s PTS=${pts}x"
  ffmpeg -y -loglevel error \
    -i "$vfile" -i "$afile" \
    -filter_complex "[0:v]setpts=${pts}*PTS,scale=1920:1080:flags=lanczos[v];[1:a]apad,atrim=0:${target},asetpts=PTS-STARTPTS[a]" \
    -map "[v]" -map "[a]" \
    -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p -r 24 \
    -c:a aac -b:a 192k -ar 44100 \
    -t "$target" -movflags +faststart \
    "$out"
done < "$SCENES_TSV"

# ────────────────────────────────────────────────────
# 2. 連結（concat demuxer + 再エンコード）
# ────────────────────────────────────────────────────
echo "=== Phase 2: Concat scenes ==="
> "$WORK/concat.txt"
while IFS=$'\t' read -r idx _; do
  [ -z "$idx" ] && continue
  echo "file 'scene_${idx}.mp4'" >> "$WORK/concat.txt"
done < "$SCENES_TSV"

ffmpeg -y -loglevel error -f concat -safe 0 -i "$WORK/concat.txt" \
  -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p -r 24 \
  -c:a aac -b:a 192k -ar 44100 \
  -movflags +faststart \
  "$WORK/composite_no_bgm.mp4"

DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$WORK/composite_no_bgm.mp4")
echo "Composite duration: ${DUR}s"

# ────────────────────────────────────────────────────
# 3. BGMミックス（loop, fade, -15dB）
# ────────────────────────────────────────────────────
echo "=== Phase 3: BGM mixing ==="
FADE_OUT=$(awk -v d="$DUR" 'BEGIN{ printf "%.3f", d-3 }')
ffmpeg -y -loglevel error \
  -i "$WORK/composite_no_bgm.mp4" \
  -stream_loop -1 -i "$BGM" \
  -filter_complex "[1:a]atrim=0:${DUR},afade=t=in:st=0:d=1.5,afade=t=out:st=${FADE_OUT}:d=3,volume=0.18[bgm];[0:a][bgm]amix=inputs=2:duration=first:normalize=0[mixed]" \
  -map 0:v -map "[mixed]" \
  -c:v copy -c:a aac -b:a 192k -ar 44100 \
  "$WORK/final_no_subs.mp4"

# ────────────────────────────────────────────────────
# 4. 字幕焼き込み（オプション、長時間処理）
# ────────────────────────────────────────────────────
if [ -n "$SRT" ]; then
    echo "=== Phase 4: Subtitle burning (background) ==="
    LOG="$WORK/sub_burn.log"
    nohup ffmpeg -y -loglevel error \
      -i "$WORK/final_no_subs.mp4" \
      -vf "subtitles='${SRT}':fontsdir=${FONTS_DIR}:force_style='FontName=Noto Sans JP,Fontsize=22,PrimaryColour=&H00000000,OutlineColour=&H00FFFFFF,BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=35'" \
      -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p \
      -c:a copy -movflags +faststart -threads 0 \
      "$WORK/final.mp4" > "$LOG" 2>&1 &
    PID=$!
    echo "Subtitle ffmpeg PID=$PID, polling..."
    while ps -p $PID >/dev/null 2>&1; do
        sleep 5
        size=$(stat -c%s "$WORK/final.mp4" 2>/dev/null || echo 0)
        echo "  ... still running, output ${size} bytes"
    done
    echo "Subtitle burn done."
fi

# ────────────────────────────────────────────────────
# 5. /tmp → 最終出力先へコピー
# ────────────────────────────────────────────────────
echo "=== Phase 5: Copy to output dir ==="
cp "$WORK/composite_no_bgm.mp4" "$OUT_DIR/composite_no_bgm.mp4"
cp "$WORK/final_no_subs.mp4"    "$OUT_DIR/final_no_subs.mp4"
[ -f "$WORK/final.mp4" ] && cp "$WORK/final.mp4" "$OUT_DIR/final.mp4"
sync
sleep 2

echo ""
echo "=== Done ==="
ls -lah "$OUT_DIR/composite_no_bgm.mp4" "$OUT_DIR/final_no_subs.mp4" "$OUT_DIR/final.mp4" 2>&1
