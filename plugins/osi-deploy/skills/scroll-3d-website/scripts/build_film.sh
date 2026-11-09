#!/bin/bash
# references/08-one-take-cinematic.md §3
# Joins start/end-frame-chained clips into one film (1280x712, 24fps).
# Each clip is assumed to be 5s/121 frames whose last frame equals the next clip's first frame;
# trim=end_frame=120 drops that duplicate so the cut is invisible. Change 120 if your clips differ.
# usage: build_film.sh clip1 clip2 ... -> film.mp4 ; each clip: drop its last frame (== next clip's first frame)
set -e
inputs=(); filt=""; n=0
for c in "$@"; do inputs+=(-i "$c"); filt+="[$n:v]fps=24,scale=1280:712:flags=lanczos,setsar=1,trim=end_frame=120,setpts=PTS-STARTPTS[v$n];"; n=$((n+1)); done
cat=""; for ((i=0;i<n;i++)); do cat+="[v$i]"; done
ffmpeg -loglevel error -y "${inputs[@]}" -filter_complex "${filt}${cat}concat=n=$n:v=1:a=0,format=yuv420p[out]" -map "[out]" -an -c:v libx264 -preset veryfast -crf 27 -g 48 -movflags +faststart film.mp4
ffprobe -v error -show_entries format=duration,size -of csv=p=0 film.mp4
