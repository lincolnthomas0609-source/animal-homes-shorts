#!/bin/zsh
# Encode a folder of frame_0001.png... into an H.264 MP4 that YouTube accepts.
#
#   tools/encode.sh <frames_dir> <out.mp4> [crf] [fps]
set -e
frames_dir="${1:?frames dir}"
out="${2:?output mp4}"
crf="${3:-18}"
fps="${4:-30}"
first=$(ls "$frames_dir"/frame_*.png | head -1)
start_number=$(basename "$first" .png | sed 's/frame_0*//')

ffmpeg -hide_banner -loglevel error -y \
  -framerate "$fps" -start_number "${start_number:-0}" -i "$frames_dir/frame_%04d.png" \
  -c:v libx264 -preset slow -crf "$crf" -pix_fmt yuv420p -movflags +faststart \
  "$out"
echo "Wrote $out ($(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,nb_frames -of csv=p=0 "$out"))"
